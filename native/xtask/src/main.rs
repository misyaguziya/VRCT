//! cargo xtask fetch-native [--cuda]
//! cargo xtask stage-sidecar --out <dir> [--release] [--sudachi-dict <system.dic>] [--silero <faster_whisper/assets>]
//!   [--weights <src-python/weights>]  (a junction: the sidecar reads the weights from beside it)
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
    /// ... or one file to download as it is (`file` is its name in third_party/<name>/)
    url: Option<String>,
    file: Option<String>,
    sha256: String,
    #[serde(default)]
    cuda: bool,
    headers_url: Option<String>,
    headers_sha256: Option<String>,
    headers_dir: Option<String>,
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
        if let (Some(url), Some(file)) = (&e.url, &e.file) {
            let cached = fetch(url, &format!("{name}-{}-{file}", e.version), &e.sha256, &cache)?;
            fs::copy(&cached, dest.join(file))?;
            println!("  {}", dest.join(file).display());
        } else {
            let url = wheel_url(name, &e.version, &e.wheel)?;
            let wheel = fetch(&url, &e.wheel, &e.sha256, &cache)?;
            extract_wheel(&wheel, &e.files, &dest)?;
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

/// The sidecar with what it reads beside it: the DLLs of the build, the translators' settings,
/// SudachiPy's resources with SudachiDict-full's system.dic, the overlay's fonts, Silero VAD
fn stage_sidecar(out: &Path, release: bool, sudachi_dict: Option<PathBuf>, silero: Option<PathBuf>, weights: Option<PathBuf>) -> Result<()> {
    let native = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().to_path_buf();
    let built = native.join("target").join(if release { "release" } else { "debug" });
    let models = native.join("../src-python/models");
    fs::create_dir_all(out)?;
    fs::copy(built.join("VRCT-sidecar.exe"), out.join("VRCT-sidecar.exe")).context("build VRCT-sidecar first")?;
    for entry in fs::read_dir(&built)? {
        let path = entry?.path();
        if path.extension().is_some_and(|e| e.eq_ignore_ascii_case("dll")) {
            fs::copy(&path, out.join(path.file_name().unwrap()))?;
        }
    }
    copy_dir(&models.join("translation/translation_settings"), &out.join("translation_settings"))?;
    copy_dir(&models.join("overlay/fonts"), &out.join("fonts"))?;
    copy_dir(&native.join("data/sudachi"), &out.join("sudachi"))?;
    let dict = sudachi_dict.or_else(|| std::env::var_os("VRCT_SUDACHI_DICT").map(PathBuf::from))
        .context("--sudachi-dict or VRCT_SUDACHI_DICT: SudachiDict-full's system.dic")?;
    fs::copy(&dict, out.join("sudachi/system.dic")).with_context(|| dict.display().to_string())?;
    let silero = silero.or_else(|| std::env::var_os("VRCT_SILERO_ASSETS").map(PathBuf::from))
        .context("--silero or VRCT_SILERO_ASSETS: faster_whisper's assets (silero_*_v5.onnx)")?;
    fs::create_dir_all(out.join("silero"))?;
    for name in ["silero_encoder_v5.onnx", "silero_decoder_v5.onnx"] {
        fs::copy(silero.join(name), out.join("silero").join(name)).with_context(|| silero.join(name).display().to_string())?;
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
                                               arg(&args, "--sudachi-dict").map(PathBuf::from),
                                               arg(&args, "--silero").map(PathBuf::from),
                                               arg(&args, "--weights").map(PathBuf::from)),
        _ => bail!("usage: cargo xtask fetch-native [--cuda] | stage-sidecar --out <dir> [--release] [--sudachi-dict <system.dic>] [--silero <dir>] [--weights <dir>]"),
    }
}
