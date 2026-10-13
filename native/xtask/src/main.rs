//! cargo xtask fetch-native [--cuda]
//! cargo xtask stage-sidecar --out <dir> [--release] [--cuda] [--exe-name <name>] [--weights <src-python/weights>]
//!   (the installed layout; --weights makes a junction: the sidecar reads the weights from beside it)
//!
//! native/third_party.toml の wheel (PyPI)・単体のファイル (`url`)・ヘッダー (GitHub のタグ) を取ってきて
//! SHA-256 を照合し、指定のファイルだけを native/third_party/<name>/ に取り出す。ダウンロードは
//! native/third_party/.cache/ に残し、次回は照合だけする。
use anyhow::{bail, Context, Result};
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::fs;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

#[derive(Deserialize)]
struct Entry {
    version: String,
    /// a wheel on PyPI and the files to take out of it ...
    #[serde(default)]
    wheel: String,
    #[serde(default)]
    files: Vec<String>,
    /// ... or one file to download as it is (`file` is its name in third_party/<name>/), or a zip
    /// archive to take `files` out of (no `file`)
    url: Option<String>,
    file: Option<String>,
    sha256: String,
    #[serde(default)]
    cuda: bool,
    headers_url: Option<String>,
    headers_sha256: Option<String>,
    headers_dir: Option<String>,
    /// license files to take out of the wheel / zip into third_party/<name>/licenses/ ...
    #[serde(default)]
    licenses: Vec<String>,
    /// ... or one license file to download (when the package has none)
    license_url: Option<String>,
    license_sha256: Option<String>,
}

fn native_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().to_path_buf()
}

fn sha256_file(path: &Path) -> Result<String> {
    let mut f = fs::File::open(path)?;
    let mut h = Sha256::new();
    let mut buf = vec![0u8; 1 << 20];
    loop {
        let n = f.read(&mut buf)?;
        if n == 0 {
            break;
        }
        h.update(&buf[..n]);
    }
    Ok(format!("{:x}", h.finalize()))
}

/// Downloads `url` into the cache (once) and checks its SHA-256.
fn fetch(url: &str, name: &str, sha256: &str, cache: &Path) -> Result<PathBuf> {
    let path = cache.join(name);
    if path.exists() && sha256_file(&path)? == sha256 {
        return Ok(path);
    }
    println!("  download {url}");
    let tmp = cache.join(format!("{name}.part"));
    let mut reader = ureq::get(url).call().with_context(|| format!("GET {url}"))?.into_reader();
    let mut out = fs::File::create(&tmp)?;
    std::io::copy(&mut reader, &mut out)?;
    out.flush()?;
    drop(out);
    let actual = sha256_file(&tmp)?;
    if actual != sha256 {
        fs::remove_file(&tmp).ok();
        bail!("{name}: sha256 mismatch (expected {sha256}, got {actual})");
    }
    fs::rename(&tmp, &path)?;
    Ok(path)
}

/// PyPI's download URL for a wheel file of a project version.
fn wheel_url(project: &str, version: &str, wheel: &str) -> Result<String> {
    let meta: serde_json_lite::Value = ureq::get(&format!("https://pypi.org/pypi/{project}/{version}/json"))
        .call()?
        .into_json()?;
    meta.find_url(wheel).with_context(|| format!("{wheel} is not a file of {project} {version}"))
}

fn matches(pattern: &str, name: &str) -> bool {
    match pattern.strip_suffix('*') {
        Some(prefix) => name.starts_with(prefix),
        None => name == pattern,
    }
}

fn extract_wheel(wheel: &Path, files: &[String], dest: &Path) -> Result<()> {
    let mut zip = zip::ZipArchive::new(fs::File::open(wheel)?)?;
    let mut found = vec![false; files.len()];
    for i in 0..zip.len() {
        let mut member = zip.by_index(i)?;
        let name = member.name().to_string();
        let Some(k) = files.iter().position(|p| matches(p, &name)) else { continue };
        found[k] = true;
        let out = dest.join(Path::new(&name).file_name().unwrap());
        let mut f = fs::File::create(&out)?;
        std::io::copy(&mut member, &mut f)?;
        println!("  {}", out.display());
    }
    if let Some(k) = found.iter().position(|f| !f) {
        bail!("{} has no {}", wheel.display(), files[k]);
    }
    Ok(())
}

fn extract_headers(tarball: &Path, dir: &str, dest: &Path) -> Result<()> {
    let mut archive = tar::Archive::new(flate2::read::GzDecoder::new(fs::File::open(tarball)?));
    let include = dest.join("include");
    let mut count = 0;
    for entry in archive.entries()? {
        let mut entry = entry?;
        let path = entry.path()?.to_string_lossy().replace('\\', "/");
        let Some(rel) = path.strip_prefix(dir) else { continue };
        if rel.is_empty() || entry.header().entry_type().is_dir() {
            continue;
        }
        let out = include.join(rel);
        fs::create_dir_all(out.parent().unwrap())?;
        entry.unpack(&out)?;
        count += 1;
    }
    if count == 0 {
        bail!("{} has nothing under {dir}", tarball.display());
    }
    println!("  {} headers -> {}", count, include.display());
    Ok(())
}

fn fetch_native(cuda: bool) -> Result<()> {
    let native = native_dir();
    let table: BTreeMap<String, Entry> = toml::from_str(&fs::read_to_string(native.join("third_party.toml"))?)?;
    let root = native.join("third_party");
    let cache = root.join(".cache");
    fs::create_dir_all(&cache)?;
    for (name, e) in &table {
        if e.cuda && !cuda {
            continue;
        }
        println!("{name} {}", e.version);
        let dest = root.join(name);
        if dest.exists() {
            fs::remove_dir_all(&dest)?; // stale files of an older version must not stay
        }
        fs::create_dir_all(&dest)?;
        let archive = if let (Some(url), Some(file)) = (&e.url, &e.file) {
            let cached = fetch(url, &format!("{name}-{}-{file}", e.version), &e.sha256, &cache)?;
            fs::copy(&cached, dest.join(file))?;
            println!("  {}", dest.join(file).display());
            None
        } else if let Some(url) = &e.url {
            let archive = url.rsplit('/').next().unwrap_or("archive.zip");
            let cached = fetch(url, &format!("{name}-{}-{archive}", e.version), &e.sha256, &cache)?;
            extract_wheel(&cached, &e.files, &dest)?;
            Some(cached)
        } else {
            let url = wheel_url(name, &e.version, &e.wheel)?;
            let wheel = fetch(&url, &e.wheel, &e.sha256, &cache)?;
            extract_wheel(&wheel, &e.files, &dest)?;
            Some(wheel)
        };
        if !e.licenses.is_empty() || e.license_url.is_some() {
            fs::create_dir_all(dest.join("licenses"))?;
        }
        if !e.licenses.is_empty() {
            extract_wheel(archive.as_deref().context("licenses need a wheel or zip")?, &e.licenses, &dest.join("licenses"))?;
        }
        if let (Some(url), Some(sha)) = (&e.license_url, &e.license_sha256) {
            let cached = fetch(url, &format!("{name}-{}-LICENSE", e.version), sha, &cache)?;
            fs::copy(&cached, dest.join("licenses").join("LICENSE"))?;
        }
        if let (Some(url), Some(sha), Some(dir)) = (&e.headers_url, &e.headers_sha256, &e.headers_dir) {
            let tarball = fetch(url, &format!("{name}-{}-headers.tar.gz", e.version), sha, &cache)?;
            extract_headers(&tarball, dir, &dest)?;
        }
    }
    Ok(())
}

/// The few lines of PyPI's JSON this needs, without a JSON dependency of its own.
mod serde_json_lite {
    use serde::Deserialize;

    #[derive(Deserialize)]
    pub struct Value {
        urls: Vec<Url>,
    }

    #[derive(Deserialize)]
    struct Url {
        filename: String,
        url: String,
    }

    impl Value {
        pub fn find_url(&self, filename: &str) -> Option<String> {
            self.urls.iter().find(|u| u.filename == filename).map(|u| u.url.clone())
        }
    }
}

fn copy_dir(src: &Path, dst: &Path) -> Result<()> {
    fs::create_dir_all(dst)?;
    for entry in fs::read_dir(src).with_context(|| src.display().to_string())? {
        let entry = entry?;
        let to = dst.join(entry.file_name());
        if entry.file_type()?.is_dir() {
            if entry.file_name() != "__pycache__" {
                copy_dir(&entry.path(), &to)?;
            }
        } else {
            fs::copy(entry.path(), &to)?;
        }
    }
    Ok(())
}

/// Copies the DLLs of a third_party folder (fetch-native's) into `dest`
fn copy_dlls(from: &Path, dest: &Path) -> Result<()> {
    for entry in fs::read_dir(from).with_context(|| format!("{}: run `cargo xtask fetch-native` first", from.display()))? {
        let path = entry?.path();
        if path.extension().is_some_and(|e| e.eq_ignore_ascii_case("dll")) {
            fs::copy(&path, dest.join(path.file_name().unwrap()))?;
        }
    }
    Ok(())
}

/// The sidecar as it is installed: `<exe_name>` and `_internal` with the DLLs (CUDA's with --cuda),
/// the translators' settings, SudachiPy's resources and dictionary, the overlay's fonts, Silero VAD
/// and the OCR models. Everything but the repository's files comes from fetch-native.
fn stage_sidecar(out: &Path, release: bool, cuda: bool, exe_name: &str, weights: Option<PathBuf>) -> Result<()> {
    let native = native_dir();
    let built = native.join("target").join(if release { "release" } else { "debug" });
    let third_party = native.join("third_party");
    let models = native.join("../src-python/models");
    fs::create_dir_all(out)?;
    // a fresh _internal; the files of the flat layout staged before go too (config.json, the logs
    // and the weights stay)
    let internal = out.join("_internal");
    for old in ["_internal", "translation_settings", "fonts", "sudachi", "silero", "ocr"] {
        let path = out.join(old);
        if path.is_dir() {
            fs::remove_dir_all(&path)?;
        }
    }
    for entry in fs::read_dir(out)? {
        let path = entry?.path();
        if path.extension().is_some_and(|e| e.eq_ignore_ascii_case("dll")) {
            fs::remove_file(&path)?;
        }
    }
    fs::create_dir_all(&internal)?;
    fs::copy(built.join("VRCT-sidecar.exe"), out.join(exe_name)).context("build VRCT-sidecar first")?;
    let mut dll_dirs = vec!["ctranslate2", "numpy", "onnxruntime", "openvr"];
    if cuda {
        dll_dirs.extend(["nvidia-cublas-cu12", "nvidia-cudnn-cu12"]);
    }
    for dir in dll_dirs {
        copy_dlls(&third_party.join(dir), &internal)?;
    }
    copy_dir(&models.join("translation/translation_settings"), &internal.join("translation_settings"))?;
    copy_dir(&models.join("overlay/fonts"), &internal.join("fonts"))?;
    copy_dir(&native.join("data/sudachi"), &internal.join("sudachi"))?;
    fs::copy(third_party.join("sudachidict-full/system_full.dic"), internal.join("sudachi/system.dic"))
        .context("sudachidict-full: run fetch-native")?;
    fs::create_dir_all(internal.join("silero"))?;
    for name in ["silero_encoder_v5.onnx", "silero_decoder_v5.onnx"] {
        fs::copy(third_party.join("faster-whisper").join(name), internal.join("silero").join(name))?;
    }
    // OCR: the bubble detector (with its notices) and RapidOCR's models
    copy_dir(&models.join("ocr/onnx"), &internal.join("ocr"))?;
    let rapidocr = internal.join("ocr").join("rapidocr");
    fs::create_dir_all(&rapidocr)?;
    for dir in ["rapidocr", "rapidocr-ch-det-v5", "rapidocr-korean-rec-v5", "rapidocr-cyrillic-rec-v5", "rapidocr-th-rec-v5",
                "rapidocr-arabic-rec-v5", "rapidocr-devanagari-rec-v5"] {
        for entry in fs::read_dir(third_party.join(dir)).with_context(|| format!("{dir}: run fetch-native"))? {
            let path = entry?.path();
            if path.extension().is_some_and(|e| e == "onnx") {
                fs::copy(&path, rapidocr.join(path.file_name().unwrap()))?;
            }
        }
    }
    // the notices: each third_party entry's licenses, the Rust crates', and those of the code ported
    let licenses = internal.join("licenses");
    for entry in fs::read_dir(&third_party)? {
        let path = entry?.path();
        let name = path.file_name().unwrap().to_string_lossy().to_string();
        if !cuda && name.starts_with("nvidia-") {
            continue;
        }
        if path.join("licenses").is_dir() {
            copy_dir(&path.join("licenses"), &licenses.join(&name))?;
        }
    }
    fs::create_dir_all(&licenses)?;
    for (from, to) in [("vrct-backend/THIRD_PARTY_LICENSES.txt", "rust-crates.txt"),
                       ("vrct-audio/SPEECH_RECOGNITION_LICENSE.txt", "speech_recognition.txt"),
                       ("../src-python/models/transcription/google_speech_LICENSE.txt", "google_speech.txt"),
                       ("vrct-ocr/LICENSE-APACHE-2.0", "rapidocr-port-apache-2.0.txt")] {
        fs::copy(native.join(from), licenses.join(to)).with_context(|| from.to_string())?;
    }
    if let Some(weights) = weights {
        let link = out.join("weights");
        if !link.exists() {
            let ok = std::process::Command::new("cmd").args(["/C", "mklink", "/J"]).arg(&link)
                .arg(if weights.is_absolute() { weights.clone() } else { std::env::current_dir()?.join(&weights) })
                .stdout(std::process::Stdio::null()).status()?.success();
            if !ok {
                bail!("mklink /J {} failed", link.display());
            }
        }
    }
    println!("staged {}", out.display());
    Ok(())
}

fn arg(args: &[String], flag: &str) -> Option<String> {
    args.iter().position(|a| a == flag).and_then(|i| args.get(i + 1)).cloned()
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match args.first().map(String::as_str) {
        Some("fetch-native") => fetch_native(args.iter().any(|a| a == "--cuda")),
        Some("stage-sidecar") => stage_sidecar(&PathBuf::from(arg(&args, "--out").context("--out <dir>")?),
                                               args.iter().any(|a| a == "--release"),
                                               args.iter().any(|a| a == "--cuda"),
                                               &arg(&args, "--exe-name").unwrap_or_else(|| "VRCT-sidecar.exe".into()),
                                               arg(&args, "--weights").map(PathBuf::from)),
        _ => bail!("usage: cargo xtask fetch-native [--cuda] | stage-sidecar --out <dir> [--release] [--cuda] [--exe-name <name>] [--weights <dir>]"),
    }
}
