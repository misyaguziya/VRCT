//! cargo xtask fetch-native [--cuda]
//!
//! native/third_party.toml の wheel (PyPI) とヘッダー (GitHub のタグ) を取ってきて SHA-256 を照合し、
//! 指定のファイルだけを native/third_party/<name>/ に取り出す。ダウンロードは
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
    wheel: String,
    sha256: String,
    files: Vec<String>,
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
        let url = wheel_url(name, &e.version, &e.wheel)?;
        let wheel = fetch(&url, &e.wheel, &e.sha256, &cache)?;
        extract_wheel(&wheel, &e.files, &dest)?;
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

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match args.first().map(String::as_str) {
        Some("fetch-native") => fetch_native(args.iter().any(|a| a == "--cuda")),
        _ => bail!("usage: cargo xtask fetch-native [--cuda]"),
    }
}
