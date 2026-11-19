//! 両エンジンの比較契約。プロセス総時間や推定の差し引き時間は使用しない。
use crate::config::Config;
use crate::report::{Check, Report, Status};
use anyhow::{ensure, Context, Result};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::io::Read;
use std::path::Path;

pub const SCOPE: &str = "resident_common_mel_to_utf8_v2";
pub const THREADS: usize = 4;
pub const MAX_NEW_TOKENS: usize = 128;
pub const MIN_AUDIO_SAMPLES: usize = 3200;
pub const MAX_AUDIO_SAMPLES: usize = 30 * 16000;
pub const CT2_MODEL_SHA: &str = "e76620f83d5f5b69efd3d87e3dc180c1bd21df9fbebacfd4335e5e1efcc018da";
pub const GGML_MODEL_SHA: &str = "1fc70f774d38eb169993ac391eea357ef47c88757ef72ee5943879b7e8e2bc69";
pub const CT2_TOKENIZER_SHA: &str =
    "297b13372ac43916285644fb9687add3cc62ee2a1adb60da3dc25cc94c1871fd";
pub const CT2_CONFIG_SHA: &str = "b0253ea6c0d3bea6b1e19e91a02acfd3b53f4467362efcb5a3e6b16c9b3a9b7e";

pub fn sha256(path: &Path) -> Result<String> {
    let mut file = std::fs::File::open(path).with_context(|| format!("open {}", path.display()))?;
    let mut hash = Sha256::new();
    let mut buffer = vec![0u8; 1024 * 1024];
    loop {
        let n = file.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        hash.update(&buffer[..n]);
    }
    Ok(format!("{:x}", hash.finalize()))
}

pub fn audio(path: &Path) -> Result<Vec<f32>> {
    crate::validate_wav(path)?;
    let mut reader = hound::WavReader::open(path)?;
    let samples = reader
        .samples::<i16>()
        .map(|s| s.map(|s| f32::from(s) / 32768.0))
        .collect::<std::result::Result<Vec<_>, _>>()?;
    validate_sample_count(samples.len())?;
    Ok(samples)
}

pub fn validate_sample_count(count: usize) -> Result<()> {
    ensure!((MIN_AUDIO_SAMPLES..=MAX_AUDIO_SAMPLES).contains(&count),
        "comparison audio must be 0.2..30 seconds (3200..480000 samples at 16 kHz); no implicit padding or truncation");
    Ok(())
}

pub fn contract(audio_sha256: &str) -> Value {
    json!({"scope":SCOPE,"audio_sha256":audio_sha256,"threads":THREADS,
        "warmup_runs":1,"model_instances":1,"language":"en","task":"transcribe",
        "decoder":"greedy","beam_size":1,"best_of":1,"temperature":0,
        "max_new_tokens":MAX_NEW_TOKENS,"timestamps":false,"context":false,
        "vad":false,"temperature_fallback":false,"flash_attention":false,
        "suppress_blank":true,"suppress_non_speech_tokens":true,
        "min_audio_seconds":0.2,"max_audio_seconds":30,
        "ct2_comgr_cache":"disabled_before_vendor_load",
        "frontend":crate::mel::FRONTEND_ID,"feature_shape":[crate::mel::N_MELS,crate::mel::N_FRAMES],
        "included":["encoder","decoder","synchronization","UTF-8 text retrieval"],
        "excluded":["process startup","DLL/model/tokenizer load","WAV decoding",
            "mel preparation","warmup","model destruction"]})
}

pub fn statistics(samples: &[Value]) -> Result<Value> {
    ensure!(!samples.is_empty(), "no timed samples");
    let mut times = samples
        .iter()
        .map(|s| {
            let seconds = s["seconds"].as_f64().context("missing sample time")?;
            ensure!(seconds.is_finite() && seconds > 0.0, "invalid sample time");
            ensure!(
                s["text"].as_str().is_some_and(|s| !s.trim().is_empty()),
                "empty output"
            );
            Ok(seconds)
        })
        .collect::<Result<Vec<_>>>()?;
    times.sort_by(f64::total_cmp);
    let n = times.len();
    let median = if n % 2 == 0 {
        (times[n / 2 - 1] + times[n / 2]) / 2.0
    } else {
        times[n / 2]
    };
    Ok(json!({"best_seconds":times[0],"median_seconds":median,"timed_runs":n}))
}

pub fn model_identity(c: &Config) -> Result<Value> {
    let ct2_sha = sha256(&c.ct2_whisper_model.join("model.bin"))?;
    let ggml_sha = sha256(&c.whisper_model)?;
    let tokenizer_sha = sha256(&c.ct2_whisper_model.join("tokenizer.json"))?;
    let config_sha = sha256(&c.ct2_whisper_model.join("config.json"))?;
    let matched = ct2_sha == CT2_MODEL_SHA
        && ggml_sha == GGML_MODEL_SHA
        && tokenizer_sha == CT2_TOKENIZER_SHA
        && config_sha == CT2_CONFIG_SHA;
    Ok(
        json!({"matched_fp16_pair":matched,"model_family":"openai/whisper-large-v3-turbo",
        "storage_precision":if matched {"float16 (unquantized)"} else {"unverified"},
        "ct2_model_sha256":ct2_sha,"ggml_model_sha256":ggml_sha,
        "ct2_tokenizer_sha256":tokenizer_sha,"ct2_config_sha256":config_sha,
        "ct2_source":"deepdml/faster-whisper-large-v3-turbo-ct2@4df90f75321148c3a29a9e2351b7ddf8f5b115a8",
        "ggml_source":"ggerganov/whisper.cpp@98aa99a0a9db05ae2342309f5096248665f7cba3",
        "note":"Same model family and verified FP16 artifacts; formats and engine kernels differ, not a bitwise arithmetic equivalence claim."}),
    )
}

fn normalized(text: &str) -> String {
    text.chars()
        .filter(|c| c.is_alphanumeric())
        .flat_map(char::to_lowercase)
        .collect()
}

fn measurement(
    check: &Check,
    expected: &Value,
    expected_features: &Value,
    runs: usize,
) -> Result<Value> {
    ensure!(check.status == Status::Ok, "{} did not pass", check.name);
    ensure!(
        check.data["isolation"]["exit_code"] == 0 && check.data["isolation"]["timed_out"] == false,
        "worker did not exit normally"
    );
    let result = &check.data["result"];
    ensure!(
        result["benchmark_contract"] == *expected,
        "measurement contracts differ"
    );
    ensure!(
        result["input_features"] == *expected_features,
        "measured input features do not match the supervisor's common mel buffer"
    );
    ensure!(
        result["concurrent"] == false,
        "concurrent samples are not latency comparisons"
    );
    let samples = result["samples"]
        .as_array()
        .context("missing timed samples")?;
    ensure!(samples.len() == runs, "incomplete timed samples");
    ensure!(
        result["warmup"]["text"]
            .as_str()
            .is_some_and(|t| !t.trim().is_empty()),
        "missing warmup"
    );
    statistics(&[result["warmup"].clone()])?;
    let stats = statistics(samples)?;
    ensure!(
        result["best_seconds"] == stats["best_seconds"]
            && result["median_seconds"] == stats["median_seconds"],
        "invalid reported statistics"
    );
    Ok(stats)
}

pub fn comparison(
    c: &Config,
    report: &Report,
    identity: Value,
    expected_features: &Value,
    gpu: bool,
) -> Check {
    let result = (|| -> Result<Value> {
        ensure!(identity["matched_fp16_pair"] == true,
            "model files are not the verified unquantized FP16 pair; quantized/unknown models cannot be ranked");
        ensure!(
            expected_features["frontend"] == crate::mel::FRONTEND_ID
                && expected_features["shape"] == json!([crate::mel::N_MELS, crate::mel::N_FRAMES])
                && expected_features["dtype"] == "float32_le"
                && expected_features["layout"] == "mel_major",
            "supervisor could not prepare the common 128x3000 mel input"
        );
        ensure!(
            expected_features["sha256"]
                .as_str()
                .is_some_and(|s| s.len() == 64 && s.bytes().all(|c| c.is_ascii_hexdigit())),
            "invalid common feature digest"
        );
        let count = expected_features["original_samples"]
            .as_u64()
            .context("missing original sample count")?;
        validate_sample_count(usize::try_from(count)?)?;
        let expected = contract(&sha256(&c.audio)?);
        let find = |name| {
            report
                .checks
                .iter()
                .find(|check| check.name == name)
                .context("missing resident measurement")
        };
        let ct2 = find(if gpu {
            "Stage C: whisper cuda float16"
        } else {
            "Stage C: whisper cpu float32"
        })?;
        let vulkan = find(if gpu {
            "Part 2: whisper.cpp gpu resident"
        } else {
            "Part 2: whisper.cpp cpu resident"
        })?;
        let ct2_stats = measurement(ct2, &expected, expected_features, c.runs)?;
        let vulkan_stats = measurement(vulkan, &expected, expected_features, c.runs)?;
        ensure!(
            crate::ct2::cache::verified(ct2),
            "CT2 COMGR cache workaround was not verified"
        );
        ensure!(
            ct2.data["result"]["model_info"]["effective_compute_type"]
                == if gpu { "float16" } else { "float32" }
                && ct2.data["result"]["model_info"]["device"] == if gpu { "cuda" } else { "cpu" },
            "CT2 did not use the required compute type/device"
        );
        ensure!(
            vulkan.data["result"]["backend_verified"] == true
                && vulkan.data["result"]["device"] == if gpu { "vulkan" } else { "cpu" },
            "whisper.cpp backend was not verified"
        );
        if gpu {
            let hip = find("Stage A: HIP runtime")?;
            ensure!(hip.status == Status::Ok, "HIP inventory did not pass");
            let devices = hip.data["result"]["devices"]
                .as_array()
                .context("HIP GPU identity is unavailable")?;
            ensure!(
                devices.len() == 1,
                "cross-engine GPU identity requires exactly one HIP GPU"
            );
            let hip_name = devices[0]["name"]
                .as_str()
                .context("missing HIP GPU name")?;
            let stderr = vulkan.data["isolation"]["stderr"]
                .as_str()
                .context("missing Vulkan device log")?;
            let pattern = regex::Regex::new(r"(?m)^ggml_vulkan:\s*(\d+)\s*=\s*(.+?)\s*\(").unwrap();
            let device_names: Vec<_> = pattern.captures_iter(stderr).collect();
            let selected = device_names
                .iter()
                .find(|m| m[1].parse::<usize>().ok() == Some(c.vulkan_device))
                .context("selected Vulkan GPU name was not reported")?;
            ensure!(
                normalized(&selected[2]) == normalized(hip_name)
                    && device_names
                        .iter()
                        .filter(|m| normalized(&m[2]) == normalized(hip_name))
                        .count()
                        == 1,
                "CT2/HIP and Vulkan are not proven to use the same physical GPU"
            );
        }
        let mut texts = Vec::new();
        for check in [ct2, vulkan] {
            let r = &check.data["result"];
            texts.push(normalized(r["warmup"]["text"].as_str().unwrap()));
            for s in r["samples"].as_array().unwrap() {
                texts.push(normalized(s["text"].as_str().unwrap()));
            }
        }
        ensure!(
            texts.iter().all(|t| !t.is_empty() && t == &texts[0]),
            "transcripts differ between runs/engines; review quality before ranking speed"
        );
        if !c.custom_audio {
            ensure!(
                texts[0] == normalized(crate::config::SENTENCE),
                "bundled transcript is incorrect"
            );
        }
        Ok(
            json!({"comparable":true,"benchmark_contract":expected,"input_features":expected_features,"model_identity":identity.clone(),
            "ct2":ct2_stats,"vulkan":vulkan_stats,
            "vulkan_over_ct2_median":vulkan_stats["median_seconds"].as_f64().unwrap()/ct2_stats["median_seconds"].as_f64().unwrap(),
            "ratio_definition":"Vulkan latency / CT2 latency; >1 means CT2 was faster",
            "quality":"matching normalized transcripts; semantic quality still requires manual review"}),
        )
    })();
    let name = if gpu {
        "Matched Whisper GPU comparison"
    } else {
        "Matched Whisper CPU comparison"
    };
    match result {
        Ok(value) => Check::new(name, Status::Ok,
            "Same resident timing contract, greedy settings and verified FP16 model pair. Compare median latency and output quality.", value),
        Err(error) => Check::new(name, Status::Blocked,
            format!("No cross-engine ranking: {error:#}"), json!({"comparable":false,"model_identity":identity})),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn statistics_exclude_warmup_and_keep_best_and_median_distinct() {
        let stats = statistics(&[
            json!({"seconds":0.3,"text":"ok"}),
            json!({"seconds":0.1,"text":"ok"}),
            json!({"seconds":0.2,"text":"ok"}),
        ])
        .unwrap();
        assert_eq!(stats["best_seconds"], 0.1);
        assert_eq!(stats["median_seconds"], 0.2);
        assert_eq!(stats["timed_runs"], 3);
        assert!(statistics(&[]).is_err());
        assert!(statistics(&[json!({"seconds":0.1,"text":""})]).is_err());
        assert!(statistics(&[json!({"seconds":-1.0,"text":"ok"})]).is_err());
    }
    #[test]
    fn rejects_cli_wall_times_incomplete_runs_and_different_contracts() {
        let expected = contract("same-audio");
        let features = json!({"sha256":"test feature buffer"});
        let mut r = json!({"benchmark_contract":expected,"concurrent":false,
            "input_features":features,
            "warmup":{"text":"Hello","seconds":1.0},"samples":[{"seconds":0.1,"text":"Hello"}],
            "best_seconds":0.1,"median_seconds":0.1});
        let make = |r| {
            Check::new(
                "resident",
                Status::Ok,
                "",
                json!({"isolation":{"exit_code":0,"timed_out":false},"result":r}),
            )
        };
        assert!(measurement(&make(r.clone()), &expected, &features, 1).is_ok());
        assert!(measurement(&make(r.clone()), &expected, &features, 3).is_err());
        r["benchmark_contract"]["scope"] = json!("process_wall_seconds");
        assert!(measurement(&make(r), &expected, &features, 1).is_err());
    }

    #[test]
    fn cross_engine_ranking_requires_matching_models_quality_device_and_complete_measurements() {
        let dir = std::env::temp_dir().join(format!("vrct-amd-comparison-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let mut c = Config::parse(dir.clone(), vec![]).unwrap();
        c.runs = 1;
        std::fs::write(&c.audio, crate::UTTERANCE).unwrap();
        let expected = contract(&sha256(&c.audio).unwrap());
        let features = crate::mel::PreparedMel::from_audio(&c.audio)
            .unwrap()
            .metadata();
        let fixture = |gpu| {
            let mut r = Report::new();
            r.checks.push(Check::new(
                "Stage A: HIP runtime",
                Status::Ok,
                "",
                json!({"result":{"devices":[{"name":"AMD Radeon RX 7800 XT"}]}}),
            ));
            for ct2 in [true, false] {
                let name = match (ct2, gpu) {
                    (true, true) => "Stage C: whisper cuda float16",
                    (true, false) => "Stage C: whisper cpu float32",
                    (false, true) => "Part 2: whisper.cpp gpu resident",
                    (false, false) => "Part 2: whisper.cpp cpu resident",
                };
                let seconds = if ct2 { 0.1 } else { 0.2 };
                r.checks.push(Check::new(name,Status::Ok,"",json!({
                    "ct2_comgr_cache":if ct2 {json!({"environment_variable":"AMD_COMGR_CACHE","configured_value":"0","observed_disabled":true,"verified_before_vendor_load":true})} else {Value::Null},
                    "isolation":{"exit_code":0,"timed_out":false,"stderr":"ggml_vulkan: 0 = AMD Radeon RX 7800 XT (AMD proprietary driver)"},
                    "result":{"benchmark_contract":expected,"concurrent":false,
                        "input_features":features,
                        "warmup":{"text":crate::config::SENTENCE,"seconds":5.0},
                        "samples":[{"text":crate::config::SENTENCE,"seconds":seconds}],
                        "best_seconds":seconds,"median_seconds":seconds,"backend_verified":true,
                        "device":if gpu {"vulkan"} else {"cpu"},
                        "model_info":{"effective_compute_type":if gpu {"float16"} else {"float32"},"device":if gpu {"cuda"} else {"cpu"}}}})));
            }
            r
        };
        let matched = json!({"matched_fp16_pair":true});
        for gpu in [true, false] {
            let ok = comparison(&c, &fixture(gpu), matched.clone(), &features, gpu);
            assert_eq!(ok.status, Status::Ok);
            assert_eq!(ok.data["vulkan_over_ct2_median"], 2.0);
        }
        for case in 0..20 {
            let mut r = fixture(true);
            let mut identity = matched.clone();
            match case {
                0 => identity["matched_fp16_pair"] = json!(false),
                1 => r.checks[2].data["result"]["benchmark_contract"]["beam_size"] = json!(5),
                2 => r.checks[2].data["result"]["backend_verified"] = json!(false),
                3 => r.checks[2].data["result"]["samples"][0]["text"] = json!("wrong transcript"),
                4 => r.checks[1].data["isolation"]["timed_out"] = json!(true),
                5 => {
                    r.checks[1].data["result"]["model_info"]["effective_compute_type"] =
                        json!("int8_float16")
                }
                6 => {
                    r.checks[2].data["isolation"]["stderr"] =
                        json!("ggml_vulkan: 0 = NVIDIA GeForce RTX (driver)")
                }
                7 => r.checks[2].status = Status::Fail,
                8 => {
                    r.checks[2].data["result"]["input_features"]["sha256"] =
                        json!("different buffer")
                }
                9 => r.checks[1].data["result"]["input_features"]["shape"] = json!([128, 2999]),
                10 => {
                    r.checks[2].data["result"]["input_features"]["original_samples"] = json!(3200)
                }
                11 => {
                    r.checks[1].data["result"]["input_features"]["frontend"] =
                        json!("native_pcm_to_mel")
                }
                12 => r.checks[2].data["result"]["input_features"] = Value::Null,
                13 => {
                    r.checks[1].data["result"]["benchmark_contract"]["scope"] =
                        json!("resident_precomputed_features_to_utf8_v1")
                }
                14 => {
                    for i in [1, 2] {
                        r.checks[i].data["result"]["input_features"]["sha256"] =
                            json!("same wrong digest");
                    }
                }
                15 => {
                    r.checks[1].data["result"]["input_features"]["original_samples"] = Value::Null
                }
                16 => r.checks[2].data["result"]["input_features"]["dtype"] = json!("float16_le"),
                17 => r.checks[1].data["ct2_comgr_cache"] = Value::Null,
                18 => r.checks[1].data["ct2_comgr_cache"]["observed_disabled"] = json!(false),
                19 => r.checks[1].data["ct2_comgr_cache"]["configured_value"] = json!("1"),
                _ => unreachable!(),
            }
            let blocked = comparison(&c, &r, identity, &features, true);
            assert_eq!(blocked.status, Status::Blocked, "case {case}");
            assert!(blocked.data.get("vulkan_over_ct2_median").is_none());
        }
        std::fs::remove_file(&c.audio).unwrap();
        std::fs::remove_dir(&dir).unwrap();
    }

    #[test]
    fn wav_and_decoded_samples_enforce_the_same_duration_boundaries() {
        let dir =
            std::env::temp_dir().join(format!("vrct-amd-audio-boundaries-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        for count in [0, 1, 200, 1600, 3199, 3200, 3201, 480000, 480001] {
            let path = dir.join(format!("{count}.wav"));
            let spec = hound::WavSpec {
                channels: 1,
                sample_rate: 16000,
                bits_per_sample: 16,
                sample_format: hound::SampleFormat::Int,
            };
            let mut writer = hound::WavWriter::create(&path, spec).unwrap();
            for _ in 0..count {
                writer.write_sample(0i16).unwrap();
            }
            writer.finalize().unwrap();
            let valid = (3200..=480000).contains(&count);
            assert_eq!(
                crate::validate_wav(&path).is_ok(),
                valid,
                "RIFF count={count}"
            );
            assert_eq!(audio(&path).is_ok(), valid, "decoded count={count}");
            assert_eq!(validate_sample_count(count).is_ok(), valid);
            std::fs::remove_file(path).unwrap();
        }
        std::fs::remove_dir(dir).unwrap();
    }
}
