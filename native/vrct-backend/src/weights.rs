//! Weight files: the download from Hugging Face (transcription_whisper.downloadWhisperWeight,
//! translation_utils.downloadCTranslate2Weight) and the verified marker (utils.py
//! isWeightVerifiedCache / writeWeightVerifiedCache), whose format v3.6.x already wrote.
//!
//! No Hugging Face token is sent (the Python backend's huggingface_hub sent a stored one implicitly;
//! these repos are public).
use crate::net::{DownloadError, Http};
use anyhow::{bail, Result};
use serde_json::{json, Map, Value};
use std::io::Write;
use std::path::{Component, Path, PathBuf};
use std::time::{Duration, UNIX_EPOCH};

pub const MARKER: &str = ".weight_verified.json";
const ATTEMPTS: u32 = 3;
/// Multiplied by the attempt number (2 s, 4 s)
const BACKOFF: Duration = Duration::from_secs(2);

pub const WHISPER_MODELS: [(&str, &str); 9] = [
    ("tiny", "Systran/faster-whisper-tiny"),
    ("base", "Systran/faster-whisper-base"),
    ("small", "Systran/faster-whisper-small"),
    ("medium", "Systran/faster-whisper-medium"),
    ("large-v1", "Systran/faster-whisper-large-v1"),
    ("large-v2", "Systran/faster-whisper-large-v2"),
    ("large-v3", "Systran/faster-whisper-large-v3"),
    ("large-v3-turbo-int8", "Zoont/faster-whisper-large-v3-turbo-int8-ct2"),
    ("large-v3-turbo", "deepdml/faster-whisper-large-v3-turbo-ct2"),
];

/// The union of the files of the converted repos (each has only some of them)
const WHISPER_FILES: [&str; 6] =
    ["config.json", "preprocessor_config.json", "model.bin", "tokenizer.json", "vocabulary.txt", "vocabulary.json"];

/// {relative path: {size, mtime}} of the files under `root`, mtime as Python's round(st_mtime, 3)
fn file_stats(root: &Path) -> Map<String, Value> {
    fn walk(root: &Path, dir: &Path, out: &mut Map<String, Value>) {
        let Ok(entries) = std::fs::read_dir(dir) else { return };
        let mut dirs = vec![];
        for entry in entries.flatten() {
            let path = entry.path();
            let Ok(kind) = entry.file_type() else { continue };
            // os.walk lists a linked directory but does not go into it
            if kind.is_dir() || (kind.is_symlink() && path.is_dir()) {
                if kind.is_dir() {
                    dirs.push(path);
                }
                continue;
            }
            if entry.file_name() == MARKER {
                continue;
            }
            let Ok(meta) = std::fs::metadata(&path) else { continue };
            let Some(mtime) = meta.modified().ok().and_then(|t| t.duration_since(UNIX_EPOCH).ok()) else { continue };
            // st_mtime is sec + nsec * 1e-9; "{:.3}" rounds the exact value half to even, as round() does
            let mtime = mtime.as_secs() as f64 + mtime.subsec_nanos() as f64 * 1e-9;
            let mtime: f64 = format!("{mtime:.3}").parse().unwrap();
            let rel = path.strip_prefix(root).unwrap().to_string_lossy().replace('\\', "/");
            out.insert(rel, json!({"size": meta.len(), "mtime": mtime}));
        }
        for d in dirs {
            walk(root, &d, out);
        }
    }
    let mut out = Map::new();
    walk(root, root, &mut out);
    out
}

/// The files under `root` are the ones recorded when they last loaded (same set, sizes and mtimes)
pub fn is_verified(root: &Path) -> bool {
    let Ok(text) = std::fs::read(root.join(MARKER)) else { return false };
    let Ok(marker) = serde_json::from_slice::<Value>(&text) else { return false };
    let Some(recorded) = marker.get("verified_files").and_then(Value::as_object).filter(|r| !r.is_empty()) else {
        return false;
    };
    let current = file_stats(root);
    // compared as numbers: Python reads 1700000000.0 and 1700000000 as equal
    let same = |a: &Value, b: &Value| ["size", "mtime"].iter().all(|k| {
        a.get(k).and_then(Value::as_f64).is_some_and(|x| b.get(k).and_then(Value::as_f64) == Some(x))
    }) && a.as_object().map(|o| o.len()) == b.as_object().map(|o| o.len());
    current.len() == recorded.len() && current.iter().all(|(k, v)| recorded.get(k).is_some_and(|r| same(v, r)))
}

pub fn write_verified(root: &Path) {
    let stats = file_stats(root);
    if !stats.is_empty() {
        let _ = std::fs::write(root.join(MARKER), serde_json::to_vec(&json!({"verified_files": stats})).unwrap());
    }
}

/// checkWhisperWeight / checkCTranslate2Weight: the marker, else whether the model loads (then the marker is written)
pub fn check(path: &Path, loads: &dyn Fn(&Path) -> bool) -> bool {
    if is_verified(path) {
        return true;
    }
    let ok = loads(path);
    if ok {
        write_verified(path);
    }
    ok
}

/// huggingface_hub.list_repo_files: the files of the main branch.
/// ponytail: the first page of the tree only (1000 entries), follow the Link header for bigger repos.
pub fn list_repo_files(http: &Http, repo: &str) -> Result<Vec<String>> {
    let url = format!("https://huggingface.co/api/models/{repo}/tree/main?recursive=True&expand=False");
    let response = http.get(&url, &[], None)?;
    if !response.status().is_success() {
        bail!("{url}: {}", response.status());
    }
    let tree: Value = response.json()?;
    Ok(tree.as_array().into_iter().flatten()
        .filter(|e| e["type"] == "file")
        .filter_map(|e| e["path"].as_str().map(String::from))
        .collect())
}

/// huggingface_hub.hf_hub_url (the file name quoted with "/" kept, as urllib.parse.quote)
pub fn hf_hub_url(repo: &str, filename: &str) -> String {
    let quoted: String = filename.bytes().map(|b| match b {
        b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'_' | b'.' | b'-' | b'~' | b'/' => (b as char).to_string(),
        _ => format!("%{b:02X}"),
    }).collect();
    format!("https://huggingface.co/{repo}/resolve/main/{quoted}")
}

/// downloadFile: up to 3 attempts, none more after a 4xx other than 429; a failed attempt's file is removed
fn download_file(http: &Http, url: &str, path: &Path, progress: Option<&dyn Fn(f64)>, what: &str,
                 log: &dyn Fn(&str, &str)) -> bool {
    for attempt in 1..=ATTEMPTS {
        let result = (|| {
            if let Some(parent) = path.parent() {
                std::fs::create_dir_all(parent)?;
            }
            let mut file = std::fs::File::create(path)?;
            let mut total = 0u64;
            http.download(url, &mut |chunk, length| {
                file.write_all(chunk)?;
                total += chunk.len() as u64;
                if let (Some(f), Some(length @ 1..)) = (progress, length) {
                    f(total as f64 / length as f64);
                }
                Ok(())
            })
        })();
        match result {
            Ok(()) => return true,
            Err(e) => {
                let _ = std::fs::remove_file(path);
                if let DownloadError::Status(status @ 400..=499) = e {
                    if status != 429 {
                        return false;
                    }
                }
                if attempt < ATTEMPTS {
                    log(&format!("{what} file download failed, retrying ({attempt}/{})", ATTEMPTS - 1), url);
                    std::thread::sleep(BACKOFF * attempt);
                }
            }
        }
    }
    false
}

/// downloadWhisperWeight: the files of `weight_type` that are missing, unless the weights already load.
/// `end` is called in every case.
pub fn download_whisper(http: &Http, root: &Path, weight_type: &str, loads: &dyn Fn(&Path) -> bool,
                        progress: &dyn Fn(f64), end: &dyn Fn(), log: &dyn Fn(&str, &str)) -> Result<()> {
    let Some(&(_, repo)) = WHISPER_MODELS.iter().find(|(t, _)| *t == weight_type) else {
        bail!("unknown whisper weight type {weight_type}");
    };
    let path = root.join("weights").join("whisper").join(weight_type);
    std::fs::create_dir_all(&path)?;
    if !check(&path, loads) {
        // when the listing fails every file is tried (the load check rejects an incomplete set later)
        let available = list_repo_files(http, repo).unwrap_or_else(|_| WHISPER_FILES.map(String::from).to_vec());
        for name in WHISPER_FILES.iter().filter(|n| available.iter().any(|a| a == *n)) {
            let progress = (*name == "model.bin").then_some(progress);
            download_file(http, &hf_hub_url(repo, name), &path.join(name), progress, "Whisper", log);
        }
    }
    end();
    Ok(())
}

/// `filename` from the repo listing under `base`, or None when it would leave it (os.path.normpath + abspath)
fn inside(base: &Path, filename: &str) -> Option<PathBuf> {
    let mut parts: Vec<&str> = vec![];
    for c in Path::new(filename).components() {
        match c {
            Component::Normal(p) => parts.push(p.to_str()?),
            Component::CurDir => {}
            Component::ParentDir => {
                parts.pop()?;
            }
            Component::Prefix(_) | Component::RootDir => return None,
        }
    }
    Some(parts.iter().fold(base.to_path_buf(), |p, part| p.join(part)))
}

/// downloadCTranslate2Weight: every file of the repo, unless the weights already load. False when the
/// listing fails 3 times or a file fails. `end` is called only after the files were tried.
pub fn download_ctranslate2(http: &Http, root: &Path, weight_type: &str, loads: &dyn Fn(&Path) -> bool,
                            progress: &dyn Fn(f64), end: &dyn Fn(), log: &dyn Fn(&str, &str)) -> Result<bool> {
    let w = crate::translate::ctranslate2::weight(weight_type)?;
    let path = root.join("weights").join("ctranslate2").join(w.directory_name);
    if check(&path, loads) {
        return Ok(true);
    }
    let mut files = None;
    for attempt in 1..=ATTEMPTS {
        match list_repo_files(http, w.hf_repo) {
            Ok(f) => {
                files = Some(f);
                break;
            }
            Err(_) if attempt < ATTEMPTS => {
                log(&format!("CTranslate2 repo listing failed, retrying ({attempt}/{})", ATTEMPTS - 1), w.hf_repo);
                std::thread::sleep(BACKOFF * attempt);
            }
            Err(_) => {}
        }
    }
    let Some(files) = files else { return Ok(false) };
    std::fs::create_dir_all(&path)?;
    let mut all = true;
    for name in &files {
        let Some(file) = inside(&path, name) else {
            all = false;
            continue;
        };
        let progress = (name == "model.bin").then_some(progress);
        all &= download_file(http, &hf_hub_url(w.hf_repo, name), &file, progress, "CTranslate2", log);
    }
    end();
    Ok(all)
}

/// downloadCTranslate2Tokenizer: the tokenizer files the translator reads, in the Hugging Face cache
/// layout v3.6.x's transformers wrote (`tokenizer/models--org--name/snapshots/<commit>/`, `refs/main`).
/// Nothing is fetched when they are there (transformers asked the Hub for a newer revision every time).
pub fn download_tokenizer(http: &Http, root: &Path, weight_type: &str, log: &dyn Fn(&str, &str)) -> Result<()> {
    let w = crate::translate::ctranslate2::weight(weight_type)?;
    let cache = root.join("weights").join("ctranslate2").join(w.directory_name).join("tokenizer");
    let files = w.tokenizer_files();
    if crate::hf_cache::snapshot_dir(&cache, w.tokenizer).is_ok_and(|s| files.iter().all(|f| s.join(f).is_file())) {
        return Ok(());
    }
    let url = format!("https://huggingface.co/api/models/{}/revision/main", w.tokenizer);
    let response = http.get(&url, &[], Some(Duration::from_secs(10)))?;
    if !response.status().is_success() {
        bail!("{url}: {}", response.status());
    }
    let info: Value = response.json()?;
    let Some(commit) = info["sha"].as_str().filter(|c| !c.is_empty() && c.chars().all(|c| c.is_ascii_alphanumeric())) else {
        bail!("{url}: no commit");
    };
    let repo = cache.join(format!("models--{}", w.tokenizer.replace('/', "--")));
    for name in files {
        let url = format!("https://huggingface.co/{}/resolve/{commit}/{name}", w.tokenizer);
        if !download_file(http, &url, &repo.join("snapshots").join(commit).join(name), None, "Tokenizer", log) {
            bail!("{url}: download failed");
        }
    }
    // the snapshot is named only once it is complete
    std::fs::create_dir_all(repo.join("refs"))?;
    std::fs::write(repo.join("refs").join("main"), commit)?;
    Ok(())
}
