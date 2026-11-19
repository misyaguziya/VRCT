use anyhow::{bail, ensure, Context, Result};
use std::ffi::OsString;
use std::path::{Path, PathBuf};

pub const SENTENCE: &str = "Hello, how are you today?";
pub const PROMPT: &str = "Translate this English sentence into Japanese. Output only the translation.\nHello, how are you today?";

#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct Config {
    pub base: PathBuf,
    pub audio: PathBuf,
    pub whisper_model: PathBuf,
    pub llama_model: PathBuf,
    pub ct2_whisper_model: PathBuf,
    pub nllb_model: PathBuf,
    pub nllb_tokenizer: Option<PathBuf>,
    pub allow_non_rocm: bool,
    pub runs: usize,
    pub timeout: u64,
    pub stage: String,
    pub vulkan_device: usize,
    pub custom_audio: bool,
}

impl Config {
    pub fn parse(base: PathBuf, args: Vec<OsString>) -> Result<Self> {
        let mut out = Self {
            audio: base.join("vrct_amd_check_utterance.wav"),
            whisper_model: base.join("models/ggml-large-v3-turbo.bin"),
            llama_model: base.join("models/translation.gguf"),
            ct2_whisper_model: base.join("models/whisper-ct2-fp16"),
            nllb_model: base.join("models/nllb-ct2"),
            nllb_tokenizer: None,
            allow_non_rocm: false,
            runs: 3,
            timeout: 900,
            stage: "abc".into(),
            vulkan_device: 0,
            custom_audio: false,
            base,
        };
        let mut args = args.into_iter();
        while let Some(key) = args.next() {
            let key = key.to_str().context("option must be UTF-8")?;
            if key == "--allow-non-rocm" {
                out.allow_non_rocm = true;
                continue;
            }
            let value = args
                .next()
                .with_context(|| format!("missing value for {key}"))?;
            let number = || value.to_str().context("number must be UTF-8");
            match key {
                "--audio" => {
                    out.audio = local_path(&out.base, &value)?;
                    out.custom_audio = true;
                }
                "--whisper-model" => out.whisper_model = local_path(&out.base, &value)?,
                "--llama-model" => out.llama_model = local_path(&out.base, &value)?,
                "--ct2-whisper-model" => out.ct2_whisper_model = local_path(&out.base, &value)?,
                "--nllb-model" => out.nllb_model = local_path(&out.base, &value)?,
                "--nllb-tokenizer" => out.nllb_tokenizer = Some(local_path(&out.base, &value)?),
                "--runs" => out.runs = number()?.parse()?,
                "--timeout" => out.timeout = number()?.parse()?,
                "--stage" => out.stage = number()?.to_string(),
                "--vulkan-device" => out.vulkan_device = number()?.parse()?,
                _ => bail!("unknown option {key}; use --help"),
            }
        }
        ensure!((1..=10).contains(&out.runs), "--runs must be 1..10");
        ensure!(
            (1..=3600).contains(&out.timeout),
            "--timeout must be 1..3600 seconds"
        );
        ensure!(out.vulkan_device <= 63, "--vulkan-device must be 0..63");
        ensure!(
            ["a", "ab", "abc"].contains(&out.stage.as_str()),
            "--stage must be a, ab, or abc"
        );
        Ok(out)
    }
}

// URI と UNC はモデル名として受け付けない。全て exe 基準のローカルファイル。
fn local_path(base: &Path, value: &std::ffi::OsStr) -> Result<PathBuf> {
    let text = value.to_string_lossy();
    ensure!(
        !text.contains("://") && !text.starts_with("\\\\") && !text.starts_with("//"),
        "only local paths are accepted"
    );
    let p = PathBuf::from(value);
    ensure!(
        !p.components()
            .any(|c| matches!(c, std::path::Component::Prefix(prefix)
        if !matches!(prefix.kind(), std::path::Prefix::Disk(_)))),
        "unsupported path prefix"
    );
    ensure!(
        !p.components()
            .any(|c| matches!(c, std::path::Component::Prefix(_)))
            || p.is_absolute(),
        "drive-relative paths are not accepted"
    );
    let resolved = if p.is_absolute() { p } else { base.join(p) };
    ensure!(
        is_local_disk(&resolved),
        "network or unavailable drive is not accepted"
    );
    Ok(resolved)
}

// UNC と割り当て済みネットワークドライブは、存在確認の前に除外する。
pub fn is_local_disk(path: &Path) -> bool {
    use std::path::{Component, Prefix};
    if !path.is_absolute() {
        return false;
    }
    let Some(Component::Prefix(prefix)) = path.components().next() else {
        return false;
    };
    let Prefix::Disk(letter) = prefix.kind() else {
        return false;
    };
    let root = [u16::from(letter), b':' as u16, b'\\' as u16, 0];
    // Win32: REMOVABLE=2, FIXED=3, CDROM=5, RAMDISK=6。REMOTE=4 は除外。
    matches!(
        unsafe { windows_sys::Win32::Storage::FileSystem::GetDriveTypeW(root.as_ptr()) },
        2 | 3 | 5 | 6
    )
}

pub fn help() -> &'static str {
    "VRCT -- AMD GPU check (offline, Windows x64)\n\
     Usage: vrct-amd-check.exe [options]\n\
     --audio PATH                 Local 16 kHz mono PCM16 WAV (default: bundled speech)\n\
     --whisper-model PATH         whisper.cpp GGML model\n\
     --llama-model PATH           llama.cpp GGUF translation model\n\
     --ct2-whisper-model PATH     Local Whisper CT2 model directory\n\
     --nllb-model PATH            Local NLLB CT2 model directory\n\
     --nllb-tokenizer PATH        tokenizer.json (default: NLLB model directory)\n\
     --allow-non-rocm            Permit non-ROCm 4.9.0 self-test (no AMD verdict)\n\
     --runs N                    Timed runs per CPU/GPU mode (default 3)\n\
     --timeout SECONDS           Per child deadline (default 900, maximum 3600)\n\
     --vulkan-device N           Vulkan device index (default 0)\n\
     --stage a|ab|abc            Limit ROCm stages only; Vulkan still runs\n\
     All relative paths are relative to this exe, not the current directory.\n\
     Nothing is downloaded. Reports are written next to this exe.\n\
     CT2 requires an adapter-enabled build and packaged 4.9.0 DLLs.\n\
     Without VRCT_CT2_49_INCLUDE at build time, CT2 stages are skipped.\n"
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn refuses_network_models_and_invalid_budgets() {
        let base = PathBuf::from(r"C:\diagnostic");
        for args in [
            vec!["--llama-model", "https://example.org/model"],
            vec!["--audio", r"\\host\share\audio.wav"],
            vec!["--audio", r"C:audio.wav"],
            vec!["--runs", "0"],
            vec!["--timeout", "0"],
            vec!["--stage", "c"],
        ] {
            assert!(
                Config::parse(base.clone(), args.into_iter().map(OsString::from).collect())
                    .is_err()
            );
        }
        assert_eq!(Config::parse(base.clone(), vec![]).unwrap().base, base);
    }

    #[test]
    fn non_rocm_flag_is_valueless_and_does_not_consume_model_arguments() {
        let base = PathBuf::from(r"C:\diagnostic");
        for args in [
            vec![
                "--allow-non-rocm",
                "--ct2-whisper-model",
                "whisper",
                "--nllb-model",
                "nllb",
                "--nllb-tokenizer",
                "tokenizer.json",
            ],
            vec![
                "--ct2-whisper-model",
                "whisper",
                "--nllb-model",
                "nllb",
                "--nllb-tokenizer",
                "tokenizer.json",
                "--allow-non-rocm",
            ],
        ] {
            let c = Config::parse(base.clone(), args.into_iter().map(OsString::from).collect())
                .unwrap();
            assert!(c.allow_non_rocm);
            assert_eq!(c.ct2_whisper_model, base.join("whisper"));
            assert_eq!(c.nllb_model, base.join("nllb"));
            assert_eq!(c.nllb_tokenizer, Some(base.join("tokenizer.json")));
            let round_trip: Config =
                serde_json::from_str(&serde_json::to_string(&c).unwrap()).unwrap();
            assert!(round_trip.allow_non_rocm);
        }
        assert!(!Config::parse(base, vec![]).unwrap().allow_non_rocm);
    }
}
