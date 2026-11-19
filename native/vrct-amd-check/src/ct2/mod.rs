pub mod cache;
mod ffi;
mod input;

use crate::config::Config;
use crate::report::{may_run, Check, Report, Status};
use anyhow::{ensure, Context, Result};
use serde_json::{json, Value};
use std::sync::Barrier;
use std::time::Instant;

pub const BUILT: bool = cfg!(ct2_49_adapter);
pub const WITHOUT_ADAPTER: &str = "skipped: built without the 4.9.0 adapter";
pub const COMPUTE_CHECK: &str = "Stage B: get_supported_compute_types('cuda')";
pub const C_CHECK: &str = "Stage C: Whisper, NLLB and concurrent use";

fn compute_names(mask: i32) -> Vec<&'static str> {
    let mut names = vec!["float32"];
    for (bit, name) in [(1, "bfloat16"), (2, "float16"), (4, "int16")] {
        if mask & bit != 0 {
            names.push(name);
        }
    }
    if mask & 8 != 0 {
        names.extend(["int8", "int8_float32"]);
        if mask & 2 != 0 {
            names.push("int8_float16");
        }
        if mask & 1 != 0 {
            names.push("int8_bfloat16");
        }
    }
    names
}

pub fn worker(c: &Config, operation: &str) -> Result<Check> {
    ensure!(BUILT, "{WITHOUT_ADAPTER}");
    let adapter = ffi::Adapter::load(&c.base)?;
    if operation == "ct2-compute" {
        let (count, mask) = adapter.capabilities("cuda")?;
        return Ok(Check::new(
            COMPUTE_CHECK,
            Status::Ok,
            "CTranslate2 4.9 adapter queried cuda device 0; inference is checked separately.",
            json!({"device":"cuda", "device_index":0, "device_count":count,
                "compute_types":compute_names(mask), "executed":true, "allow_non_rocm":c.allow_non_rocm}),
        ));
    }
    let op = operation
        .strip_prefix("ct2-")
        .context("invalid CT2 operation")?;
    let (op, concurrent) = op
        .strip_suffix("-concurrent")
        .map_or((op, false), |s| (s, true));
    let (kind, mode) = op.split_once('-').context("missing CT2 mode")?;
    ensure!(
        matches!(kind, "whisper" | "nllb"),
        "unknown CT2 model family"
    );
    let (device, compute) = match mode {
        "float16" => ("cuda", "float16"),
        "int8_float16" => ("cuda", "int8_float16"),
        "cpu-int8" => ("cpu", "int8"),
        "cpu-float32" => ("cpu", "float32"),
        _ => anyhow::bail!("unknown CT2 mode"),
    };
    let whisper = kind == "whisper";
    let path = if whisper {
        &c.ct2_whisper_model
    } else {
        &c.nllb_model
    };
    let start = Instant::now();
    let model = adapter.model(path, device, compute, whisper)?;
    let load_seconds = start.elapsed().as_secs_f64();
    let model_info = model.info()?;
    let start = Instant::now();
    let input = if whisper {
        input::Input::whisper(&model, path, &c.audio)?
    } else {
        input::Input::nllb(
            &c.nllb_tokenizer
                .clone()
                .unwrap_or_else(|| path.join("tokenizer.json")),
        )?
    };
    let preprocess_seconds = start.elapsed().as_secs_f64();
    let input_features = input.feature_metadata();
    let infer = || -> Result<Value> {
        let start = Instant::now();
        let mut output = input.infer(&model)?;
        output["seconds"] = json!(start.elapsed().as_secs_f64());
        Ok(output)
    };
    let warmup = infer()?;
    let samples = if concurrent {
        // Both threads enter at once; each submits two requests to the SAME
        // loaded pool (one replica), with private features/encoder outputs.
        let barrier = Barrier::new(2);
        std::thread::scope(|scope| -> Result<Vec<Value>> {
            let spawn = |thread_index| {
                scope.spawn({
                    let infer = &infer;
                    let barrier = &barrier;
                    move || -> Result<Vec<Value>> {
                        barrier.wait();
                        (0..2)
                            .map(|iteration| {
                                let mut value = infer()?;
                                value["thread"] = json!(thread_index);
                                value["iteration"] = json!(iteration);
                                Ok(value)
                            })
                            .collect()
                    }
                })
            };
            let first = spawn(0);
            let second = spawn(1);
            // Join both even if one fails; no handle/model destruction during inference.
            let first = first.join();
            let second = second.join();
            let mut all = first.map_err(|_| anyhow::anyhow!("first CT2 thread panicked"))??;
            all.extend(second.map_err(|_| anyhow::anyhow!("second CT2 thread panicked"))??);
            Ok(all)
        })?
    } else {
        (0..c.runs).map(|_| infer()).collect::<Result<Vec<_>>>()?
    };
    let best = samples
        .iter()
        .filter_map(|v| v["seconds"].as_f64())
        .reduce(f64::min);
    let stats = crate::benchmark::statistics(&samples)?;
    Ok(Check::new(
        &format!(
            "Stage C: {kind} {device} {compute}{}",
            if concurrent { " concurrent" } else { "" }
        ),
        Status::Ok,
        "Inference completed; inspect the transcript/translation before judging quality.",
        json!({"executed":true, "model":path, "device":device, "device_index":0,
            "requested_compute_type":compute, "allow_non_rocm":c.allow_non_rocm,
            "load_seconds":load_seconds, "preprocess_seconds":preprocess_seconds,"model_info":model_info,
            "warmup":warmup, "samples":samples, "best_seconds":best,
            "median_seconds":stats["median_seconds"],
            "input_features":input_features,
            "benchmark_contract":if whisper {crate::benchmark::contract(&crate::benchmark::sha256(&c.audio)?)} else {Value::Null},
            "concurrent":concurrent, "caller_threads":if concurrent {2} else {1},
            "model_instances":1, "replicas":1, "cpu_threads":4,
            "timing":if whisper {crate::benchmark::SCOPE} else {"resident tokenized input to UTF-8; load, preprocessing and warmup excluded"},
            "quality":"nonempty output only; semantic correctness requires manual review"}),
    ))
}

fn skip(name: &str, reason: &str) -> Check {
    Check::new(name, Status::Skip, reason, json!({"executed":false}))
}

/// Injectable supervisor keeps gating testable without loading any vendor DLL.
pub fn stages(
    c: &Config,
    r: &mut Report,
    imports_ok: bool,
    audio_ok: bool,
    built: bool,
    mut supervise: impl FnMut(&Config, &str) -> Check,
) {
    if !built {
        r.checks.push(skip(COMPUTE_CHECK, WITHOUT_ADAPTER));
        r.checks.push(skip(C_CHECK, WITHOUT_ADAPTER));
        return;
    }
    if !imports_ok || c.stage == "a" {
        r.checks.push(skip(
            COMPUTE_CHECK,
            "Earlier prerequisite did not pass, or --stage a was requested.",
        ));
        r.checks.push(skip(
            C_CHECK,
            "Earlier prerequisite did not pass, or --stage a was requested.",
        ));
        return;
    }
    let query = supervise(c, "ct2-compute");
    let query_ok = may_run(query.status);
    // A failed query is not permission to guess support. Once the query passes,
    // probe each requested mode even if its capabilities are absent: an explicit
    // CT2 error is useful evidence, and CPU/other precision workers stay independent.
    r.checks.push(query);
    if !query_ok || c.stage != "abc" {
        r.checks.push(skip(
            C_CHECK,
            "Compute-type query failed, or --stage ab was requested.",
        ));
        return;
    }
    for (kind, path) in [("whisper", &c.ct2_whisper_model), ("nllb", &c.nllb_model)] {
        if !path.join("model.bin").is_file() || (kind == "whisper" && !audio_ok) {
            r.checks.push(skip(
                &format!("Stage C: {kind}"),
                "Local model.bin or valid audio is missing.",
            ));
            continue;
        }
        let mut best = [None; 3];
        for (i, mode) in ["float16", "int8_float16", "cpu-int8"].iter().enumerate() {
            let result = supervise(c, &format!("ct2-{kind}-{mode}"));
            if may_run(result.status) {
                best[i] = result
                    .data
                    .pointer("/result/best_seconds")
                    .and_then(Value::as_f64);
            }
            r.checks.push(result);
        }
        if kind == "whisper" {
            r.checks.push(supervise(c, "ct2-whisper-cpu-float32"));
        }
        for mode in ["float16", "int8_float16"] {
            r.checks
                .push(supervise(c, &format!("ct2-{kind}-{mode}-concurrent")));
        }
        for (i, mode) in ["float16", "int8_float16"].iter().enumerate() {
            let ratio = best[i]
                .zip(best[2])
                .filter(|(gpu, _)| *gpu > 0.0)
                .map(|(gpu, cpu)| cpu / gpu);
            r.checks.push(Check::new(&format!("Stage C: {kind} {mode} / CPU int8 comparison"),
                if ratio.is_some() { Status::Ok } else { Status::Warn },
                "CPU/GPU best resident inference ratio for the same model/input; review output quality.",
                json!({"gpu_best_seconds":best[i], "cpu_int8_best_seconds":best[2],
                    "cpu_over_gpu":ratio, "excludes":"model load, preprocessing, warmup"})));
        }
    }
}

pub fn decision(c: &Config) -> &'static str {
    if c.allow_non_rocm {
        "Non-ROCm self-test (--allow-non-rocm): these results do not validate AMD/ROCm support. Review each worker result and output; AMD hardware verification remains required."
    } else if !BUILT {
        "Inconclusive for an AMD edition: built without the 4.9.0 adapter; Stage B compute types and Stage C were skipped. Vulkan results are independent."
    } else {
        "No automatic AMD shipping verdict: review each CT2/Vulkan result, transcripts/translations, precision errors, concurrency and CPU comparisons on AMD hardware. Enumeration/imports alone do not prove inference works."
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[test]
    fn compute_types_preserve_mixed_precision_requirements() {
        assert_eq!(compute_names(0), ["float32"]);
        assert!(compute_names(8).contains(&"int8_float32"));
        assert!(!compute_names(8).contains(&"int8_float16"));
        assert!(compute_names(10).contains(&"int8_float16"));
        assert!(compute_names(9).contains(&"int8_bfloat16"));
    }

    #[test]
    fn absent_adapter_and_stage_limits_never_launch_inference() {
        let mut c = Config::parse(PathBuf::from(r"C:\diagnostic"), vec![]).unwrap();
        let mut r = Report::new();
        stages(&c, &mut r, true, true, false, |_, _| {
            panic!("must not launch")
        });
        assert_eq!(r.checks.len(), 2);
        assert!(r
            .checks
            .iter()
            .all(|v| v.status == Status::Skip && v.detail == WITHOUT_ADAPTER));
        c.stage = "a".into();
        stages(&c, &mut r, true, true, true, |_, _| {
            panic!("stage a must not launch")
        });
        c.stage = "ab".into();
        let mut operations = vec![];
        stages(&c, &mut r, true, true, true, |_, op| {
            operations.push(op.to_owned());
            Check::new(COMPUTE_CHECK, Status::Ok, "", Value::Null)
        });
        assert_eq!(operations, ["ct2-compute"]);
        c.stage = "abc".into();
        operations.clear();
        stages(&c, &mut r, true, true, true, |_, op| {
            operations.push(op.to_owned());
            Check::new(COMPUTE_CHECK, Status::Fail, "", Value::Null)
        });
        assert_eq!(operations, ["ct2-compute"]);
    }

    #[test]
    fn gpu_failure_preserves_cpu_other_precision_and_concurrent_workers() {
        let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("target")
            .join(format!("ct2-planning-test-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join("model.bin"), []).unwrap();
        let mut c = Config::parse(PathBuf::from(r"C:\diagnostic"), vec![]).unwrap();
        c.ct2_whisper_model = dir.clone();
        c.nllb_model = dir.clone();
        let mut r = Report::new();
        let mut operations = vec![];
        stages(&c, &mut r, true, true, true, |_, op| {
            operations.push(op.to_owned());
            let status = if op == "ct2-whisper-float16" {
                Status::Fail
            } else {
                Status::Ok
            };
            Check::new(op, status, "", json!({"result":{"best_seconds":2.0}}))
        });
        std::fs::remove_file(dir.join("model.bin")).unwrap();
        std::fs::remove_dir(dir).unwrap();
        assert_eq!(
            operations,
            [
                "ct2-compute",
                "ct2-whisper-float16",
                "ct2-whisper-int8_float16",
                "ct2-whisper-cpu-int8",
                "ct2-whisper-cpu-float32",
                "ct2-whisper-float16-concurrent",
                "ct2-whisper-int8_float16-concurrent",
                "ct2-nllb-float16",
                "ct2-nllb-int8_float16",
                "ct2-nllb-cpu-int8",
                "ct2-nllb-float16-concurrent",
                "ct2-nllb-int8_float16-concurrent",
            ]
        );
        let comparisons: Vec<_> = r
            .checks
            .iter()
            .filter(|c| c.name.contains("comparison"))
            .collect();
        assert!(comparisons[0].data["cpu_over_gpu"].is_null());
        assert_eq!(comparisons[1].data["cpu_over_gpu"], 1.0);
    }
}
