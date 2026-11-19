use crate::config::{Config, PROMPT};
use crate::process::{external, offline_command};
use crate::report::{Check, Status};
use anyhow::{ensure, Result};
use regex::Regex;
use serde_json::json;
use std::path::PathBuf;

pub fn binary(c: &Config, engine: &str) -> PathBuf {
    if engine == "whisper" {
        c.base.join("whisper-vulkan/whisper-cli.exe")
    } else {
        c.base.join("llama-vulkan/llama-cli.exe")
    }
}

pub fn required_flags(engine: &str) -> &'static [&'static str] {
    if engine == "whisper" {
        &[
            "--model",
            "--file",
            "--language",
            "--beam-size",
            "--no-gpu",
            "--device",
        ]
    } else {
        &[
            "--model",
            "--offline",
            "--single-turn",
            "--prompt",
            "--device",
            "--gpu-layers",
            "--n-predict",
            "--seed",
            "--temp",
            "--verbosity",
            "--list-devices",
        ]
    }
}

pub fn compatible_help(engine: &str, text: &str) -> bool {
    required_flags(engine)
        .iter()
        .all(|flag| text.contains(flag))
}

pub fn backend_verified(engine: &str, gpu: bool, stderr: &str, index: usize) -> bool {
    let text = stderr.to_lowercase();
    if text.contains("failed to initialize") {
        return false;
    }
    if engine == "whisper" {
        if gpu {
            text.contains(&format!("using vulkan{index} backend"))
        } else {
            Regex::new(r"use gpu\s*=\s*0\b").unwrap().is_match(&text)
        }
    } else {
        let offload = Regex::new(r"offloaded ([1-9][0-9]*)/[0-9]+ layers to gpu")
            .unwrap()
            .is_match(&text);
        if gpu {
            offload
                && text.lines().any(|line| {
                    line.contains(&format!("vulkan{index}")) && line.contains("model buffer size")
                })
        } else {
            !offload
                && text
                    .lines()
                    .any(|line| line.contains("cpu") && line.contains("model buffer size"))
        }
    }
}

pub fn run(c: &Config, engine: &str, mode: &str) -> Result<Check> {
    ensure!(["whisper", "llama"].contains(&engine), "unknown engine");
    ensure!(
        ["help", "devices", "gpu", "cpu"].contains(&mode),
        "unknown Vulkan operation"
    );
    let exe = binary(c, engine);
    ensure!(exe.is_file(), "missing {}", exe.display());
    let mut cmd = offline_command(&exe, exe.parent().unwrap());
    // llama のユーザー設定やキャッシュを本物のプロファイルから分離する。
    let scratch = c.base.join("vrct_amd_check_runtime");
    std::fs::create_dir_all(&scratch)?;
    for key in [
        "APPDATA",
        "LOCALAPPDATA",
        "PROGRAMDATA",
        "HOME",
        "USERPROFILE",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
    ] {
        cmd.env(key, &scratch);
    }
    if engine == "llama" {
        cmd.arg("--offline");
    }
    match mode {
        "help" => {
            cmd.arg("--help");
        }
        "devices" => {
            cmd.arg("--list-devices");
        }
        _ if engine == "whisper" => {
            ensure!(c.whisper_model.is_file(), "missing local whisper.cpp model");
            ensure!(c.audio.is_file(), "missing local WAV");
            cmd.arg("-m")
                .arg(&c.whisper_model)
                .arg("-f")
                .arg(&c.audio)
                .args(["-l", "en", "-bs", "1", "-t", "4"]);
            if mode == "gpu" {
                cmd.arg("-dev").arg(c.vulkan_device.to_string());
            } else {
                cmd.arg("-ng");
            }
        }
        _ => {
            ensure!(c.llama_model.is_file(), "missing local llama.cpp model");
            cmd.arg("-m").arg(&c.llama_model).args([
                "--single-turn",
                "--prompt",
                PROMPT,
                "-n",
                "128",
                "--temp",
                "0",
                "--seed",
                "1",
                "-t",
                "4",
                "--verbosity",
                "3",
                "--device",
            ]);
            if mode == "gpu" {
                cmd.arg(format!("Vulkan{}", c.vulkan_device))
                    .args(["-ngl", "999"]);
            } else {
                cmd.args(["none", "-ngl", "0"]);
            }
        }
    }
    let args: Vec<_> = cmd
        .get_args()
        .map(|s| s.to_string_lossy().into_owned())
        .collect();
    let result = external(&mut cmd)?;
    let verified = match mode {
        "help" => compatible_help(engine, &format!("{}\n{}", result.stdout, result.stderr)),
        "devices" => result.stdout.contains("Vulkan") || result.stderr.contains("Vulkan"),
        _ => backend_verified(engine, mode == "gpu", &result.stderr, c.vulkan_device),
    };
    let status = if !result.success() {
        Status::Fail
    } else if verified {
        Status::Ok
    } else {
        Status::Warn
    };
    let detail = if !result.success() {
        "The upstream process failed. Please include the exact error text below."
    } else if !verified {
        "Process exited successfully, but the requested backend/CLI capabilities were not verified. This is not a GPU PASS."
    } else {
        "Process completed and the requested backend/CLI capabilities were verified."
    };
    let lines: Vec<_> = result
        .stderr
        .lines()
        .filter(|line| {
            let line = line.to_ascii_lowercase();
            [
                "vulkan",
                "device",
                "offload",
                "time",
                "tokens per second",
                "model buffer",
            ]
            .iter()
            .any(|s| line.contains(s))
        })
        .map(str::to_string)
        .collect();
    Ok(Check::new(
        &format!("Part 2: {engine}.cpp {mode}"),
        status,
        detail,
        json!({"program":exe, "arguments":args, "backend_verified":verified,
            "device_and_timing_lines":lines, "process":result,
            "timing_scope":"Fresh process wall time includes startup, model load and inference. Engine-reported timings are preserved separately; not a warmed persistent-server latency."}),
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn does_not_accept_vulkan_enumeration_or_silent_cpu_fallback_as_gpu_success() {
        let enumeration =
            "ggml_vulkan: Found 1 Vulkan devices:\nggml_vulkan: 0 = Radeon RX 9070 XT";
        assert!(!backend_verified("whisper", true, enumeration, 0));
        assert!(!backend_verified("llama", true, enumeration, 0));
        assert!(backend_verified(
            "whisper",
            true,
            "whisper_backend_init_gpu: using Vulkan0 backend",
            0
        ));
        assert!(!backend_verified(
            "whisper",
            true,
            "using Vulkan0 backend\nfailed to initialize Vulkan0",
            0
        ));
        assert!(!backend_verified(
            "whisper",
            true,
            "using Vulkan1 backend",
            0
        ));
        assert!(backend_verified(
            "llama",
            true,
            "Vulkan0 model buffer size = 100 MiB\noffloaded 25/25 layers to GPU",
            0
        ));
        assert!(!backend_verified(
            "llama",
            true,
            "Vulkan0 model buffer size = 0 MiB\noffloaded 0/25 layers to GPU",
            0
        ));
        assert!(backend_verified(
            "llama",
            false,
            "CPU model buffer size = 100 MiB",
            0
        ));
    }
}
