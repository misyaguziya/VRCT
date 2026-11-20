//! cargo xtask fetch-native [--cuda | --amd]
//! cargo xtask stage-sidecar --out <dir> [--release] [--cuda | --amd] [--exe-name <name>] [--weights <weights folder>]
//!   (the installed layout; --weights makes a junction: the sidecar reads the weights from beside it)
//! cargo xtask release-zip --out <zip>
//!   (VRCT.exe, VRCT-sidecar.exe and _internal/ of src-tauri/target/release, for the updater: the layout of the installed folder)
//! cargo xtask model-catalog-files <repo> [--revision <branch or commit>] [--only a,b]
//!   (a repo's files with their sizes and SHA-256 at a commit, for native/data/model_catalog.json)
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
    #[serde(default)]
    amd: bool,
    /// A wheel inside the downloaded zip (ROCm CT2).
    nested_wheel: Option<String>,
    /// Keep file paths relative to this wheel directory (ROCm BLAS kernels).
    relative_to: Option<String>,
    headers_url: Option<String>,
    headers_sha256: Option<String>,
    headers_dir: Option<String>,
    /// license files to take out of the wheel / zip into third_party/<name>/licenses/ ...
    #[serde(default)]
    licenses: Vec<String>,
    /// ... or one license file to download (when the package has none)
    license_url: Option<String>,
    license_sha256: Option<String>,
    /// Component notices when a binary package omits the license texts.
    #[serde(default)]
    notices: Vec<Notice>,
}

#[derive(Deserialize)]
struct Notice {
    name: String,
    url: String,
    sha256: String,
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

fn extract_wheel(wheel: &Path, files: &[String], dest: &Path, relative_to: Option<&str>) -> Result<()> {
    let mut zip = zip::ZipArchive::new(fs::File::open(wheel)?)?;
    let mut found = vec![false; files.len()];
    for i in 0..zip.len() {
        let mut member = zip.by_index(i)?;
        if member.is_dir() {
            continue;
        }
        let name = member.name().to_string();
        let Some(k) = files.iter().position(|p| matches(p, &name)) else { continue };
        found[k] = true;
        let path = member.enclosed_name().context("invalid archive path")?;
        let out = match relative_to {
            Some(prefix) => dest.join(path.strip_prefix(prefix)?),
            None => dest.join(path.file_name().context("missing archive filename")?),
        };
        fs::create_dir_all(out.parent().unwrap())?;
        let mut f = fs::File::create(&out)?;
        std::io::copy(&mut member, &mut f)?;
        println!("  {}", out.display());
    }
    if let Some(k) = found.iter().position(|f| !f) {
        bail!("{} has no {}", wheel.display(), files[k]);
    }
    Ok(())
}

/// The `files` of a 7z archive (librime's releases) into `dest`, by Windows' own tar (bsdtar reads 7z)
fn extract_7z(archive: &Path, files: &[String], dest: &Path) -> Result<()> {
    let unpacked = archive.with_extension("d");
    if !unpacked.is_dir() {
        let tmp = archive.with_extension("d.part");
        if tmp.exists() {
            fs::remove_dir_all(&tmp)?;
        }
        fs::create_dir_all(&tmp)?;
        let tar = Path::new(&std::env::var("SystemRoot").unwrap_or_else(|_| r"C:\Windows".into())).join(r"System32\tar.exe");
        let ok = std::process::Command::new(&tar).arg("-xf").arg(archive).arg("-C").arg(&tmp).status()
            .with_context(|| format!("run {}", tar.display()))?.success();
        if !ok {
            bail!("{} could not unpack {}", tar.display(), archive.display());
        }
        fs::rename(&tmp, &unpacked)?;
    }
    for pattern in files {
        let (dir, name) = pattern.rsplit_once('/').unwrap_or(("", pattern));
        let mut found = false;
        for entry in fs::read_dir(unpacked.join(dir)).with_context(|| format!("{} has no {dir}", archive.display()))? {
            let path = entry?.path();
            let file = path.file_name().unwrap().to_string_lossy().to_string();
            if path.is_file() && matches(name, &file) {
                fs::copy(&path, dest.join(&file))?;
                println!("  {}", dest.join(&file).display());
                found = true;
            }
        }
        if !found {
            bail!("{} has no {pattern}", archive.display());
        }
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

fn fetch_native(cuda: bool, amd: bool) -> Result<()> {
    let native = native_dir();
    let table: BTreeMap<String, Entry> = toml::from_str(&fs::read_to_string(native.join("third_party.toml"))?)?;
    let root = native.join("third_party");
    let cache = root.join(".cache");
    fs::create_dir_all(&cache)?;
    for (name, e) in &table {
        if (e.cuda && !cuda) || (e.amd && !amd) {
            continue;
        }
        println!("{name} {}", e.version);
        // A failed notice download must not leave a half-fetched AMD package available to stage.
        let installed = root.join(name);
        let dest = if e.amd { cache.join(format!("{name}.unpacking")) } else { installed.clone() };
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
            let mut cached = fetch(url, &format!("{name}-{}-{archive}", e.version), &e.sha256, &cache)?;
            if let Some(member) = &e.nested_wheel {
                let mut zip = zip::ZipArchive::new(fs::File::open(&cached)?)?;
                let mut wheel = zip.by_name(member)?;
                cached = cache.join(format!("{name}-{}.whl", e.version));
                std::io::copy(&mut wheel, &mut fs::File::create(&cached)?)?;
            }
            if archive.ends_with(".7z") {
                extract_7z(&cached, &e.files, &dest)?;
            } else {
                extract_wheel(&cached, &e.files, &dest, e.relative_to.as_deref())?;
            }
            Some(cached)
        } else {
            let url = wheel_url(name, &e.version, &e.wheel)?;
            let wheel = fetch(&url, &e.wheel, &e.sha256, &cache)?;
            extract_wheel(&wheel, &e.files, &dest, None)?;
            Some(wheel)
        };
        if !e.licenses.is_empty() || e.license_url.is_some() || !e.notices.is_empty() {
            fs::create_dir_all(dest.join("licenses"))?;
        }
        if !e.licenses.is_empty() {
            extract_wheel(archive.as_deref().context("licenses need a wheel or zip")?, &e.licenses, &dest.join("licenses"), None)?;
        }
        if let (Some(url), Some(sha)) = (&e.license_url, &e.license_sha256) {
            let cached = fetch(url, &format!("{name}-{}-LICENSE", e.version), sha, &cache)?;
            fs::copy(&cached, dest.join("licenses").join("LICENSE"))?;
        }
        for notice in &e.notices {
            let cached = fetch(&notice.url, &format!("{name}-{}-{}", e.version, notice.name), &notice.sha256, &cache)?;
            fs::copy(cached, dest.join("licenses").join(&notice.name))?;
        }
        if let (Some(url), Some(sha), Some(dir)) = (&e.headers_url, &e.headers_sha256, &e.headers_dir) {
            let tarball = fetch(url, &format!("{name}-{}-headers.tar.gz", e.version), sha, &cache)?;
            extract_headers(&tarball, dir, &dest)?;
        }
        if e.amd {
            if installed.exists() {
                fs::remove_dir_all(&installed)?;
            }
            fs::rename(dest, installed)?;
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

/// The sidecar as installed: `<exe_name>` and `_internal` (CUDA DLLs with --cuda, ct2-rocm/ with --amd),
/// the translators' settings, SudachiPy's resources and dictionary, the overlay's fonts, Silero VAD
/// and the OCR models. Everything but the repository's files comes from fetch-native.
fn stage_sidecar(out: &Path, release: bool, cuda: bool, amd: bool, exe_name: &str, weights: Option<PathBuf>) -> Result<()> {
    let native = native_dir();
    let built = native.join("target").join(if release { "release" } else { "debug" });
    let third_party = native.join("third_party");
    let data = native.join("data");
    if amd {
        for file in ["ctranslate2-rocm/ctranslate2.dll", "rocm-libraries/hipblas.dll", "rocm-libraries/rocsolver.dll",
                     "rocm-libraries/rocblas.dll", "rocm-libraries/libhipblaslt.dll"] {
            if !third_party.join(file).is_file() {
                bail!("missing {file}: run cargo xtask fetch-native --amd");
            }
        }
        for dir in ["rocm-libraries/rocblas/library", "rocm-libraries/hipblaslt/library"] {
            if !third_party.join(dir).is_dir() {
                bail!("missing {dir}: run cargo xtask fetch-native --amd");
            }
        }
    }
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
    let mut dll_dirs = vec!["ctranslate2", "numpy", "onnxruntime", "openvr", "librime"];
    if cuda {
        dll_dirs.extend(["nvidia-cublas-cu12", "nvidia-cudnn-cu12"]);
    }
    for dir in dll_dirs {
        copy_dlls(&third_party.join(dir), &internal)?;
    }
    if amd {
        let rocm = internal.join("ct2-rocm");
        fs::create_dir_all(&rocm)?;
        let libraries = third_party.join("rocm-libraries");
        copy_dlls(&third_party.join("ctranslate2-rocm"), &rocm)?;
        copy_dlls(&libraries, &rocm)?;
        for dir in ["rocblas", "hipblaslt"] {
            copy_dir(&libraries.join(dir), &rocm.join(dir))?;
        }
    }
    copy_dir(&data.join("translation_settings"), &internal.join("translation_settings"))?;
    copy_dir(&data.join("fonts"), &internal.join("fonts"))?;
    copy_dir(&data.join("sudachi"), &internal.join("sudachi"))?;
    fs::copy(third_party.join("sudachidict-full/system_full.dic"), internal.join("sudachi/system.dic"))
        .context("sudachidict-full: run fetch-native")?;
    fs::create_dir_all(internal.join("silero"))?;
    for name in ["silero_encoder_v5.onnx", "silero_decoder_v5.onnx"] {
        fs::copy(third_party.join("faster-whisper").join(name), internal.join("silero").join(name))?;
    }
    // the VR keyboard: OpenCC's data (Traditional / Simplified Chinese) beside rime.dll; the
    // dictionaries are downloaded when the VR UI is first on
    copy_dir(&third_party.join("librime-opencc"), &internal.join("rime").join("opencc")).context("librime-opencc: run fetch-native")?;
    // OCR: the bubble detector (with its notices) and RapidOCR's models
    copy_dir(&data.join("ocr"), &internal.join("ocr"))?;
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
        if (!cuda && name.starts_with("nvidia-")) || (!amd && matches!(name.as_str(), "ctranslate2-rocm" | "rocm-libraries")) {
            continue;
        }
        if path.join("licenses").is_dir() {
            copy_dir(&path.join("licenses"), &licenses.join(&name))?;
        }
    }
    fs::create_dir_all(&licenses)?;
    for (from, to) in [("vrct-backend/THIRD_PARTY_LICENSES.txt", "rust-crates.txt"),
                       ("vrct-audio/SPEECH_RECOGNITION_LICENSE.txt", "speech_recognition.txt"),
                       ("vrct-backend/GOOGLE_SPEECH_LICENSE.txt", "google_speech.txt"),
                       ("vrct-ocr/LICENSE-APACHE-2.0", "rapidocr-port-apache-2.0.txt"),
                       ("vrct-ime/RIME_THIRD_PARTY_NOTICES.txt", "rime.txt")] {
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

/// A release zip of src-tauri/target/release: the two exes at the top, _internal/ with its files (no directory entries).
fn release_zip(out: &Path) -> Result<()> {
    fn collect(dir: &Path, prefix: &str, files: &mut Vec<(PathBuf, String)>) -> Result<()> {
        let mut entries = fs::read_dir(dir)?.collect::<std::io::Result<Vec<_>>>()?;
        entries.sort_by_key(|e| e.file_name());
        for e in entries {
            let name = format!("{prefix}/{}", e.file_name().to_string_lossy());
            if e.file_type()?.is_dir() { collect(&e.path(), &name, files)?; } else { files.push((e.path(), name)); }
        }
        Ok(())
    }
    let release = native_dir().parent().context("repo root")?.join("src-tauri/target/release");
    let mut files = Vec::new();
    for exe in ["VRCT.exe", "VRCT-sidecar.exe"] {
        files.push((release.join(exe), exe.to_string()));
    }
    collect(&release.join("_internal"), "_internal", &mut files)?;
    let mut total = 0u64;
    for (p, _) in &files {
        total += fs::metadata(p).with_context(|| format!("{}", p.display()))?.len();
    }
    let mut zip = zip::ZipWriter::new(std::io::BufWriter::new(fs::File::create(out)?));
    let opts = zip::write::SimpleFileOptions::default().compression_method(zip::CompressionMethod::Deflated);
    let (mut done, mut shown, mut buf) = (0u64, u64::MAX, vec![0u8; 1 << 20]);
    for (path, name) in &files {
        let mut f = fs::File::open(path)?;
        zip.start_file(name.as_str(), opts.large_file(f.metadata()?.len() >= 1 << 32))?;
        loop {
            let n = f.read(&mut buf)?;
            if n == 0 { break; }
            zip.write_all(&buf[..n])?;
            done += n as u64;
            if done * 100 / total.max(1) != shown {
                shown = done * 100 / total.max(1);
                eprint!("\r{} {shown:3}% ({} / {} MB)", out.display(), done >> 20, total >> 20);
            }
        }
    }
    zip.finish()?;
    eprintln!("\n{} files -> {}", files.len(), out.display());
    Ok(())
}

#[derive(Deserialize)]
struct HfRevision {
    sha: String,
}

#[derive(Deserialize)]
struct HfTreeEntry {
    #[serde(rename = "type")]
    kind: String,
    path: String,
    size: u64,
    lfs: Option<HfLfs>,
}

#[derive(Deserialize)]
struct HfLfs {
    oid: String,
}

/// The files of a Hugging Face repo at a commit, for native/data/model_catalog.json: `revision`
/// (a branch or a commit) is resolved to its commit; a large file's SHA-256 is the LFS oid, a small
/// one is downloaded and hashed. `only`: those of these files the repo has, else every file but README.md,
/// .gitattributes and pickles. Printed as JSON.
/// ponytail: the tree's first page only (1000 entries), refused beyond it.
fn model_catalog_files(repo: &str, revision: &str, only: Option<Vec<String>>) -> Result<()> {
    let hf = "https://huggingface.co";
    let commit = ureq::get(&format!("{hf}/api/models/{repo}/revision/{revision}")).call()?.into_json::<HfRevision>()?.sha;
    if commit.len() != 40 || !commit.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b)) {
        bail!("{repo}@{revision}: unexpected commit {commit}");
    }
    let tree: Vec<HfTreeEntry> = ureq::get(&format!("{hf}/api/models/{repo}/tree/{commit}?recursive=true")).call()?.into_json()?;
    if tree.len() >= 1000 {
        bail!("{repo}: 1000 entries or more, the tree is paged");
    }
    let pickle = |p: &str| {
        let ext = Path::new(p).extension().and_then(|e| e.to_str()).unwrap_or("").to_ascii_lowercase();
        ["pt", "pth", "pkl", "pickle", "ckpt"].contains(&ext.as_str()) || (ext == "bin" && p != "model.bin")
    };
    let mut files = vec![];
    for e in tree.iter().filter(|e| e.kind == "file") {
        let wanted = match &only {
            Some(only) => only.contains(&e.path),
            None => !matches!(e.path.as_str(), "README.md" | ".gitattributes") && !pickle(&e.path),
        };
        if !wanted {
            continue;
        }
        // written into JSON as it is
        if !e.path.bytes().all(|b| b.is_ascii_graphic() && b != b'"' && b != b'\\') {
            bail!("{repo}: unexpected file name {:?}", e.path);
        }
        let sha256 = match &e.lfs {
            Some(lfs) => lfs.oid.clone(),
            None => {
                let mut body = vec![];
                ureq::get(&format!("{hf}/{repo}/resolve/{commit}/{}", e.path)).call()?.into_reader().read_to_end(&mut body)?;
                if body.len() as u64 != e.size {
                    bail!("{repo}/{}: {} bytes, the tree says {}", e.path, body.len(), e.size);
                }
                format!("{:x}", Sha256::digest(&body))
            }
        };
        files.push(format!("{{\"path\": \"{}\", \"size\": {}, \"sha256\": \"{sha256}\"}}", e.path, e.size));
    }
    println!("{{\"repo\": \"{repo}\", \"revision\": \"{commit}\", \"files\": [{}]}}", files.join(", "));
    Ok(())
}

fn arg(args: &[String], flag: &str) -> Option<String> {
    args.iter().position(|a| a == flag).and_then(|i| args.get(i + 1)).cloned()
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let cuda = args.iter().any(|a| a == "--cuda");
    let amd = args.iter().any(|a| a == "--amd");
    if cuda && amd {
        bail!("--cuda and --amd are mutually exclusive");
    }
    match args.first().map(String::as_str) {
        Some("fetch-native") => fetch_native(cuda, amd),
        Some("stage-sidecar") => stage_sidecar(&PathBuf::from(arg(&args, "--out").context("--out <dir>")?),
                                               args.iter().any(|a| a == "--release"),
                                               cuda, amd,
                                               &arg(&args, "--exe-name").unwrap_or_else(|| "VRCT-sidecar.exe".into()),
                                               arg(&args, "--weights").map(PathBuf::from)),
        Some("release-zip") => {
            let out = PathBuf::from(arg(&args, "--out").context("--out <zip>")?);
            // a zip that stopped half way is not left behind (never shipped with files missing)
            release_zip(&out).inspect_err(|_| { let _ = fs::remove_file(&out); })
        }
        Some("model-catalog-files") => model_catalog_files(
            args.get(1).context("<repo>")?,
            &arg(&args, "--revision").unwrap_or_else(|| "main".into()),
            arg(&args, "--only").map(|o| o.split(',').map(String::from).collect())),
        _ => bail!("usage: cargo xtask fetch-native [--cuda | --amd] | stage-sidecar --out <dir> [--release] [--cuda | --amd] [--exe-name <name>] [--weights <dir>] | release-zip --out <zip> | model-catalog-files <repo> [--revision <rev>] [--only a,b]"),
    }
}
