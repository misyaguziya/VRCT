#![cfg_attr(not(all(windows, target_arch = "x86_64")), allow(unused))]
#[cfg(not(all(windows, target_arch = "x86_64")))]
compile_error!("vrct-amd-check targets Windows x64 only");

mod benchmark;
mod config;
mod ct2;
mod hip;
mod hip_abi;
mod mel;
mod pe;
mod process;
mod report;
mod vulkan;
mod whisper_resident;

use anyhow::{ensure, Context, Result};
use config::Config;
use report::{may_run, Check, Report, Status};
use serde_json::{json, Value};
use std::ffi::OsString;
use std::io::Write;
use std::path::Path;
use std::time::Duration;

// 合成音声の en00.wav（リポジトリの照合コーパス）を埋め込み、初回だけ展開する。
const UTTERANCE: &[u8] = include_bytes!("../assets/utterance.wav");

fn supervise(c: &Config, operation: &str) -> Check {
    println!("Running {operation} (deadline {} seconds)...", c.timeout);
    let _ = std::io::stdout().flush();
    let attempt = (|| -> Result<Check> {
        let exe = std::env::current_exe()?;
        let mut command = process::offline_command(&exe, &c.base);
        command
            .arg("--child")
            .arg(operation)
            .arg(serde_json::to_string(c)?);
        ct2::cache::configure(&mut command, operation);
        let mut capture = process::isolated(&mut command, Duration::from_secs(c.timeout))?;
        if !capture.success() {
            return Ok(Check::new(
                operation,
                Status::Fail,
                if capture.timed_out {
                    "Child timed out; its process tree was terminated. Please report this hang."
                } else {
                    "Child crashed or exited unsuccessfully. Please report the exact exit code and error text."
                },
                json!({"isolation":capture}),
            ));
        }
        let Some(line) = capture
            .stdout
            .lines()
            .rev()
            .find_map(|l| l.strip_prefix(process::RESULT_MARKER))
        else {
            return Ok(Check::new(
                operation,
                Status::Fail,
                "Child produced no result; see raw output.",
                json!({"isolation":capture}),
            ));
        };
        let parsed = serde_json::from_str::<Check>(line);
        match parsed {
            Ok(mut check) => {
                capture.stdout = capture
                    .stdout
                    .lines()
                    .filter(|l| !l.starts_with(process::RESULT_MARKER))
                    .collect::<Vec<_>>()
                    .join("\n");
                check.data = json!({"result":check.data, "isolation":capture});
                Ok(check)
            }
            Err(e) => Ok(Check::new(
                operation,
                Status::Fail,
                format!("Invalid child result: {e}"),
                json!({"isolation":capture}),
            )),
        }
    })();
    let mut check = attempt
        .unwrap_or_else(|e| Check::new(operation, Status::Fail, format!("{e:#}"), Value::Null));
    ct2::cache::record(&mut check, operation);
    check
}

fn ct2_imports(c: &Config) -> Result<Check> {
    let path = c.base.join("ctranslate2.dll");
    ensure!(
        path.is_file(),
        "No ctranslate2.dll next to this exe. Supply the intended ROCm build."
    );
    let imports = pe::read(&path)?;
    let family = imports.family();
    let (status, detail) = if imports.machine != 0x8664 {
        (Status::Fail, "ctranslate2.dll is not a Windows x64 image.")
    } else {
        match family {
            "cuda" | "unknown" if c.allow_non_rocm => (Status::Ok, "Non-ROCm 4.9.0 self-test explicitly allowed; this is not ROCm evidence."),
            "rocm" => (Status::Ok, "This looks like the ROCm/HIP build. Imports alone do not prove inference works."),
            "cuda" => (Status::Fail, "This looks like the NVIDIA/CUDA build. It links against CUDA, not HIP."),
            "mixed" => (Status::Fail, "Both HIP and CUDA imports were found. Build identity is ambiguous; do not treat it as ROCm."),
            _ => (Status::Blocked, "Could not prove a ROCm build from the import table. Libraries may be loaded lazily; no GPU PASS."),
        }
    };
    Ok(Check::new(
        "Stage B: CTranslate2 PE imports",
        status,
        detail,
        json!({"path":path,"size_bytes":std::fs::metadata(&path)?.len(),"build_family":family,
            "imports":imports,"version":"not inferred from PE imports; maintainer must supply matching build provenance",
            "note":"A non-zero device count on its own does NOT prove the ROCm build works."}),
    ))
}

fn child(operation: &str, c: &Config) -> Result<Check> {
    match operation {
        "hip" => hip::runtime(&c.base),
        "hipblas.dll" | "libhipblas.dll" => hip::blas(&c.base, operation),
        "ct2-imports" => ct2_imports(c),
        "whisper-resident-gpu" => whisper_resident::worker(c, true),
        "whisper-resident-cpu" => whisper_resident::worker(c, false),
        op if op.starts_with("ct2-") => ct2::worker(c, op),
        "environment" => Ok(Check::new(
            "Environment and local package",
            Status::Ok,
            "Standalone diagnostic inventory.",
            inventory(c),
        )),
        "gpu-inventory" => {
            let root = std::env::var_os("SystemRoot").context("SystemRoot missing")?;
            let exe = Path::new(&root).join("System32/WindowsPowerShell/v1.0/powershell.exe");
            let mut command = process::offline_command(&exe, &c.base);
            command.args(["-NoProfile", "-NonInteractive", "-Command",
                "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion | ConvertTo-Json -Compress"]);
            let out = process::external(&mut command)?;
            let status = if out.success() && !out.stdout.trim().is_empty() {
                Status::Ok
            } else {
                Status::Warn
            };
            Ok(Check::new(
                "GPU inventory (optional)",
                status,
                "Windows video controllers and driver versions.",
                json!(out),
            ))
        }
        _ => {
            let (engine, mode) = operation.split_once('-').context("unknown worker")?;
            vulkan::run(c, engine, mode)
        }
    }
}

fn prepare_audio(c: &Config) -> Result<()> {
    if !c.custom_audio {
        if c.audio.exists() {
            ensure!(std::fs::read(&c.audio)? == UTTERANCE,
                "The default WAV already exists with different content; use --audio or restore the bundled utterance.");
        } else {
            // 既存ファイルは上書きしない。
            let mut file = std::fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&c.audio)?;
            file.write_all(UTTERANCE)?;
        }
    }
    validate_wav(&c.audio)
}

fn validate_wav(path: &Path) -> Result<()> {
    ensure!(
        std::fs::metadata(path)?.len() <= 10 * 1024 * 1024,
        "WAV exceeds 10 MiB"
    );
    let data = std::fs::read(path)?;
    ensure!(
        data.len() >= 12 && &data[..4] == b"RIFF" && &data[8..12] == b"WAVE",
        "not a RIFF WAV"
    );
    let mut offset = 12usize;
    let (mut format, mut samples) = (false, false);
    while offset + 8 <= data.len() {
        let size = u32::from_le_bytes(data[offset + 4..offset + 8].try_into()?) as usize;
        let end = offset
            .checked_add(8)
            .and_then(|o| o.checked_add(size))
            .context("WAV chunk overflow")?;
        ensure!(end <= data.len(), "truncated WAV chunk");
        let chunk = &data[offset + 8..end];
        match &data[offset..offset + 4] {
            b"fmt " => {
                ensure!(chunk.len() >= 16, "short WAV format");
                let number = |i| u16::from_le_bytes([chunk[i], chunk[i + 1]]);
                ensure!(
                    number(0) == 1
                        && number(2) == 1
                        && number(14) == 16
                        && u32::from_le_bytes(chunk[4..8].try_into()?) == 16000,
                    "expected 16 kHz mono PCM16 WAV"
                );
                format = true;
            }
            b"data" => {
                ensure!(
                    chunk.len() % 2 == 0,
                    "audio data must contain complete mono PCM16 samples"
                );
                benchmark::validate_sample_count(chunk.len() / 2)?;
                samples = true;
            }
            _ => {}
        }
        offset = end + size % 2;
    }
    ensure!(format && samples, "WAV format or samples missing");
    Ok(())
}

fn inventory(c: &Config) -> Value {
    let mut files = Vec::new();
    for dir in [&c.base, &c.base.join("hip")] {
        if let Ok(entries) = std::fs::read_dir(dir) {
            for entry in entries.flatten().take(1024) {
                let path = entry.path();
                if path
                    .extension()
                    .is_some_and(|ext| ext.eq_ignore_ascii_case("dll"))
                {
                    files.push(
                        json!({"file":path, "size_bytes":entry.metadata().ok().map(|m| m.len())}),
                    );
                }
            }
        }
    }
    json!({"environment":hip::environment(&c.base),"packaged_dlls":files,
        "note":"Top-level DLL inventory only; PE imports do not enumerate lazily loaded dependencies or all rocBLAS/Tensile kernel assets.",
        "ct2_whisper_model":c.ct2_whisper_model,"nllb_model":c.nllb_model,
        "whisper_cpp_model":c.whisper_model,"llama_cpp_model":c.llama_model,
        "sentence":config::SENTENCE,"translation_target":"Japanese","audio":c.audio,
        "ct2_49_adapter_built":ct2::BUILT,"whisper_184_adapter_built":whisper_resident::BUILT,
        "allow_non_rocm":c.allow_non_rocm})
}

fn rocm(c: &Config, r: &mut Report, audio_ok: bool) {
    let a_ok =
        if c.allow_non_rocm {
            r.checks.push(Check::new(
            "Stage A: HIP runtime", Status::Skip,
            "--allow-non-rocm: HIP prerequisite bypassed for a non-ROCm self-test; no AMD verdict.",
            Value::Null));
            false
        } else {
            let a = supervise(c, "hip");
            let ok = may_run(a.status);
            r.checks.push(a);
            ok
        };
    if a_ok {
        for name in ["hipblas.dll", "libhipblas.dll"] {
            r.checks.push(supervise(c, name));
        }
    } else {
        r.checks.push(Check::new(
            "Stage A: hipBLAS",
            Status::Skip,
            "HIP prerequisite failed or was bypassed for a non-ROCm self-test.",
            Value::Null,
        ));
    }
    let b_ok = if (a_ok || c.allow_non_rocm) && c.stage != "a" {
        let b = supervise(c, "ct2-imports");
        let ok = may_run(b.status);
        r.checks.push(b);
        ok
    } else {
        r.checks.push(Check::new(
            "Stage B: CTranslate2 PE imports",
            Status::Skip,
            "Stage A did not pass, or --stage a was requested.",
            json!({"dll_present_next_to_exe":c.base.join("ctranslate2.dll").is_file()}),
        ));
        false
    };
    ct2::stages(c, r, b_ok, audio_ok, ct2::BUILT, supervise);
}

fn vulkan_part(c: &Config, r: &mut Report, audio_ok: bool) {
    for engine in ["whisper", "llama"] {
        if engine == "whisper" {
            if audio_ok {
                whisper_resident::stages(c, r, supervise);
            } else {
                r.checks.push(Check::new(
                    "Part 2: whisper.cpp resident",
                    Status::Skip,
                    "Valid local audio is required.",
                    Value::Null,
                ));
            }
            continue;
        }
        if !vulkan::binary(c, engine).is_file() {
            r.checks.push(Check::new(
                &format!("Part 2: {engine}.cpp"),
                Status::Skip,
                "Upstream Vulkan binary is absent. Nothing was downloaded.",
                json!({"expected":vulkan::binary(c, engine)}),
            ));
            continue;
        }
        let help = supervise(c, &format!("{engine}-help"));
        let help_ok = may_run(help.status);
        r.checks.push(help);
        if !help_ok {
            r.checks.push(Check::new(
                &format!("Part 2: {engine}.cpp inference"),
                Status::Skip,
                "CLI capabilities could not be verified; choose a compatible upstream release.",
                Value::Null,
            ));
            continue;
        }
        if engine == "llama" {
            r.checks.push(supervise(c, "llama-devices"));
        }
        let model = if engine == "whisper" {
            &c.whisper_model
        } else {
            &c.llama_model
        };
        if !model.is_file() || (engine == "whisper" && !audio_ok) {
            r.checks.push(Check::new(
                &format!("Part 2: {engine}.cpp inference"),
                Status::Skip,
                "The local model or valid utterance is missing. Nothing was downloaded.",
                json!({"model":model}),
            ));
            continue;
        }
        let mut best = [None, None];
        // GPU 失敗時も CPU 比較を行う。各モード内は最初の失敗で打ち切る。
        for (i, mode) in ["gpu", "cpu"].into_iter().enumerate() {
            for run in 0..=c.runs {
                let mut check = supervise(c, &format!("{engine}-{mode}"));
                let ok = may_run(check.status);
                if ok && run > 0 {
                    if let Some(seconds) = check
                        .data
                        .pointer("/result/process/wall_seconds")
                        .and_then(Value::as_f64)
                    {
                        best[i] = Some(best[i].map_or(seconds, |prior: f64| prior.min(seconds)));
                    }
                }
                check.name = format!(
                    "Part 2: {engine}.cpp {mode} / {}",
                    if run == 0 {
                        "preliminary run (not included in ratio)".into()
                    } else {
                        format!("timed run {run}")
                    }
                );
                r.checks.push(check);
                if !ok {
                    // 不完全な繰り返しから速度比を作らない。
                    best[i] = None;
                    break;
                }
            }
        }
        let ratio = best[0]
            .zip(best[1])
            .filter(|(gpu, _)| *gpu > 0.0)
            .map(|(gpu, cpu)| cpu / gpu);
        r.checks.push(Check::new(&format!("Part 2: {engine}.cpp comparison"),
            if ratio.is_some() { Status::Ok } else { Status::Warn },
            "CPU/GPU best process-wall-time ratio; includes model load. Read transcripts/translations and engine timings before deciding.",
            json!({"gpu_best_seconds":best[0],"cpu_best_seconds":best[1],"cpu_over_gpu":ratio,
                "barely_faster_threshold_from_python_spike":1.2,
                "interpretation":ratio.map(|v| if v < 1.2 { "The GPU is barely faster than the CPU here. Please report it as-is." }
                    else { "GPU process wall time improved; this is not a quality or persistent-server benchmark." })})));
    }
}

fn write_report(c: &Config, r: &Report) -> Result<()> {
    let home = std::env::var("USERPROFILE")
        .or_else(|_| std::env::var("HOME"))
        .unwrap_or_default();
    let user = std::env::var("USERNAME")
        .or_else(|_| std::env::var("USER"))
        .unwrap_or_default();
    let text = report::redact(&r.text(), &home, &user);
    let mut value = serde_json::to_value(r)?;
    report::redact_value(&mut value, &home, &user);
    println!("{text}");
    // 最後に全体へ伏せ字を掛ける。ログを含め、生の診断データはディスクに書かない。
    let txt = c.base.join("vrct_amd_check_report.txt");
    let json_path = c.base.join("vrct_amd_check_report.json");
    std::fs::write(&txt, text).with_context(|| format!("write {}", txt.display()))?;
    std::fs::write(&json_path, serde_json::to_string_pretty(&value)?)
        .with_context(|| format!("write {}", json_path.display()))?;
    println!("Reports written next to this exe. Please read both before sharing.");
    Ok(())
}

fn run() -> Result<()> {
    let args: Vec<OsString> = std::env::args_os().skip(1).collect();
    if args.first().is_some_and(|s| s == "--child") {
        process::child_handshake()?;
        let op = args
            .get(1)
            .and_then(|s| s.to_str())
            .context("missing worker operation")?;
        let config: Config = serde_json::from_str(
            args.get(2)
                .and_then(|s| s.to_str())
                .context("missing worker config")?,
        )?;
        let check = match std::panic::catch_unwind(|| {
            ct2::cache::verify_before_load(op)?;
            child(op, &config)
        }) {
            Ok(Ok(check)) => check,
            Ok(Err(error)) => Check::new(op, Status::Fail, format!("{error:#}"), Value::Null),
            Err(_) => Check::new(
                op,
                Status::Fail,
                "Rust worker panicked; see captured stderr.",
                Value::Null,
            ),
        };
        println!(
            "\n{}{}",
            process::RESULT_MARKER,
            serde_json::to_string(&check)?
        );
        return Ok(());
    }
    if args.iter().any(|a| a == "--help" || a == "-h") {
        print!("{}", config::help());
        return Ok(());
    }
    let exe = std::env::current_exe()?;
    let c = Config::parse(exe.parent().context("exe parent")?.to_owned(), args)?;
    ensure!(
        config::is_local_disk(&c.base),
        "run this diagnostic from a local disk"
    );
    let mut r = Report::new();
    println!("VRCT -- AMD GPU check (issue #88)\nNo downloads. No data is sent anywhere.");
    r.checks.push(supervise(&c, "environment"));
    r.checks.push(supervise(&c, "gpu-inventory"));
    let audio = prepare_audio(&c);
    let audio_ok = audio.is_ok();
    r.checks.push(Check::new(
        "Bundled utterance",
        if audio_ok { Status::Ok } else { Status::Fail },
        audio
            .map(|_| {
                if c.custom_audio {
                    "Using supplied WAV; sentence equivalence must be checked manually.".into()
                } else {
                    format!("Synthetic speech: {}", config::SENTENCE)
                }
            })
            .unwrap_or_else(|e| format!("{e:#}")),
        json!({"path":c.audio,"format":"16 kHz mono PCM16","same_input_for_both_engines":true}),
    ));
    rocm(&c, &mut r, audio_ok);
    vulkan_part(&c, &mut r, audio_ok);
    let identity = benchmark::model_identity(&c)
        .unwrap_or_else(|error| json!({"matched_fp16_pair":false,"error":format!("{error:#}")}));
    // 比較の期待値を計測外で一度だけ生成する。worker同士の自己申告一致だけでは通さない。
    let expected_features = mel::PreparedMel::from_audio(&c.audio)
        .map(|mel| mel.metadata())
        .unwrap_or_else(|error| json!({"error":format!("{error:#}")}));
    for gpu in [true, false] {
        r.checks.push(benchmark::comparison(
            &c,
            &r,
            identity.clone(),
            &expected_features,
            gpu,
        ));
    }
    r.decision = ct2::decision(&c).into();
    write_report(&c, &r)
}

fn main() {
    if let Err(error) = run() {
        eprintln!("Diagnostic could not finish: {error:#}\nIf report files could not be written, copy this console output.");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn bundled_utterance_is_real_pcm_speech() {
        let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("assets/utterance.wav");
        validate_wav(&path).unwrap();
        assert!(UTTERANCE.len() > 16000 * 2);
    }
}
