//! Weight files: the models of the catalog (native/data/model_catalog.json), their download from
//! Hugging Face (or a mirror, HF_ENDPOINT) checked file by file against the catalog's SHA-256 and
//! resumed from a `.part`, and the verified marker (utils.py isWeightVerifiedCache /
//! writeWeightVerifiedCache), whose format v3.6.x already wrote.
//!
//! No Hugging Face token is sent (the Python backend's huggingface_hub sent a stored one implicitly;
//! these repos are public).
use crate::net::{DownloadError, Http};
use anyhow::{bail, Result};
use serde_json::{json, Map, Value};
use std::io::{Read, Seek, SeekFrom, Write};
use std::path::{Component, Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{Duration, UNIX_EPOCH};

pub const MARKER: &str = ".weight_verified.json";
const ATTEMPTS: u32 = 3;
/// Multiplied by the attempt number (2 s, 4 s)
const BACKOFF: Duration = Duration::from_secs(2);

// --------------------------------------------------------------------------------- the catalog

/// The models VRCT has checked (native/data/model_catalog.json, `cargo xtask model-catalog-files`):
/// each at a fixed commit, with every file's size and SHA-256. Nothing else is downloaded.
const CATALOG: &str = include_str!("../../data/model_catalog.json");

/// What a model is: the settings and folder it belongs to and the tokenizer it is read with
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Family {
    Whisper,
    M2m100,
    Nllb,
}

impl Family {
    /// The weights folder (`weights/<kind>/<id>`) and the settings' name (`<KIND>_WEIGHT_TYPE`)
    pub fn kind(self) -> &'static str {
        if self == Family::Whisper { "whisper" } else { "ctranslate2" }
    }

    pub fn name(self) -> &'static str {
        match self {
            Family::Whisper => "whisper",
            Family::M2m100 => "m2m100",
            Family::Nllb => "nllb",
        }
    }
}

#[derive(Debug)]
pub struct CatalogFile {
    pub path: String,
    pub size: u64,
    pub sha256: String,
}

#[derive(Debug)]
pub struct CatalogRepo {
    pub repo: String,
    /// a commit (40 hex digits)
    pub revision: String,
    pub files: Vec<CatalogFile>,
}

#[derive(Debug)]
pub struct CatalogModel {
    /// the weight type: the settings' value, the folder's name and the push's weight_type
    pub id: String,
    pub family: Family,
    /// CTranslate2: the key of languages.yml["CTranslate2"]
    pub languages: Option<String>,
    pub license: String,
    pub weights: CatalogRepo,
    /// CTranslate2: the tokenizer, kept in the Hugging Face cache layout under `tokenizer/`
    pub tokenizer: Option<CatalogRepo>,
}

impl CatalogModel {
    /// The bytes of every file, the tokenizer's too
    pub fn size(&self) -> u64 {
        self.weights.files.iter().chain(self.tokenizer.iter().flat_map(|t| &t.files)).map(|f| f.size).sum()
    }

    /// `<root>/weights/<kind>/<id>`
    pub fn dir(&self, root: &Path) -> PathBuf {
        root.join("weights").join(self.family.kind()).join(&self.id)
    }
}

/// A file path of the catalog: plain names under the folder only, no pickles (only model.bin of the
/// .bin files, which is CTranslate2's own format)
fn safe_path(path: &str) -> bool {
    let p = Path::new(path);
    let ext = p.extension().and_then(|e| e.to_str()).unwrap_or("").to_ascii_lowercase();
    let pickle = ["pt", "pth", "pkl", "pickle", "ckpt"].contains(&ext.as_str()) || (ext == "bin" && path != "model.bin");
    !path.is_empty() && !path.contains([':', '\\']) && !pickle && p.components().all(|c| matches!(c, Component::Normal(_)))
}

fn hex(s: &str, len: usize) -> bool {
    s.len() == len && s.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

fn parse_repo(v: &Value) -> Result<CatalogRepo> {
    let str_of = |key: &str| v[key].as_str().map(String::from).ok_or_else(|| anyhow::anyhow!("no {key}"));
    let (repo, revision) = (str_of("repo")?, str_of("revision")?);
    let name_ok = |s: &str| !s.is_empty() && !s.starts_with('.') && s.bytes().all(|b| b.is_ascii_alphanumeric() || b"._-".contains(&b));
    if repo.split('/').count() != 2 || !repo.split('/').all(name_ok) {
        bail!("bad repo {repo}");
    }
    if !hex(&revision, 40) {
        bail!("{repo}: revision {revision} is not a commit");
    }
    let mut files = vec![];
    for f in v["files"].as_array().into_iter().flatten() {
        let file = CatalogFile {
            path: f["path"].as_str().unwrap_or("").to_string(),
            size: f["size"].as_u64().unwrap_or(0),
            sha256: f["sha256"].as_str().unwrap_or("").to_string(),
        };
        if !safe_path(&file.path) || file.size == 0 || !hex(&file.sha256, 64) {
            bail!("{repo}: bad file {f}");
        }
        if files.iter().any(|g: &CatalogFile| g.path == file.path) {
            bail!("{repo}: {} twice", file.path);
        }
        files.push(file);
    }
    if files.is_empty() {
        bail!("{repo}: no files");
    }
    Ok(CatalogRepo { repo, revision, files })
}

/// model_catalog.json, every entry checked (a bad one is refused, not skipped)
pub fn parse_catalog(text: &str) -> Result<Vec<CatalogModel>> {
    let v: Value = serde_json::from_str(text)?;
    if v["version"] != 1 {
        bail!("catalog version {}", v["version"]);
    }
    let mut models: Vec<CatalogModel> = vec![];
    for m in v["models"].as_array().into_iter().flatten() {
        let id = m["id"].as_str().unwrap_or("").to_string();
        let id_ok = !id.is_empty() && !id.starts_with('.') && id.bytes().all(|b| b.is_ascii_alphanumeric() || b"._-".contains(&b));
        if !id_ok || models.iter().any(|o| o.id == id) {
            bail!("bad or repeated id {id:?}");
        }
        let family = match m["family"].as_str() {
            Some("whisper") => Family::Whisper,
            Some("m2m100") => Family::M2m100,
            Some("nllb") => Family::Nllb,
            other => bail!("{id}: unknown family {other:?}"),
        };
        let languages = m["languages"].as_str().map(String::from);
        let tokenizer = if m["tokenizer"].is_null() { None } else { Some(parse_repo(&m["tokenizer"]).map_err(|e| e.context(id.clone()))?) };
        if (family == Family::Whisper) != (languages.is_none() && tokenizer.is_none()) {
            bail!("{id}: CTranslate2 models (only) have languages and a tokenizer");
        }
        models.push(CatalogModel {
            license: m["license"].as_str().unwrap_or("").to_string(),
            weights: parse_repo(m).map_err(|e| e.context(id.clone()))?,
            id,
            family,
            languages,
            tokenizer,
        });
    }
    Ok(models)
}

pub fn catalog() -> &'static [CatalogModel] {
    static MODELS: std::sync::OnceLock<Vec<CatalogModel>> = std::sync::OnceLock::new();
    MODELS.get_or_init(|| parse_catalog(CATALOG).expect("model_catalog.json"))
}

/// The catalog's model `id`
pub fn model(id: &str) -> Option<&'static CatalogModel> {
    catalog().iter().find(|m| m.id == id)
}

/// The catalog's CTranslate2 model `id`
pub fn ctranslate2_model(id: &str) -> Result<&'static CatalogModel> {
    model(id).filter(|m| m.family != Family::Whisper).ok_or_else(|| anyhow::anyhow!("unknown weight type {id}"))
}

/// The key of languages.yml["CTranslate2"] for a weight type (a name not in the catalog as it is)
pub fn languages_key(weight_type: &str) -> &str {
    model(weight_type).and_then(|m| m.languages.as_deref()).unwrap_or(weight_type)
}

// ------------------------------------------------------------------------ the verified marker

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

/// `{endpoint}/{repo}/resolve/{revision}/{path}`, the path quoted as huggingface_hub.hf_hub_url does
/// (urllib.parse.quote: letters, digits and "_.-~/" kept)
pub fn resolve_url(endpoint: &str, repo: &str, revision: &str, path: &str) -> String {
    use percent_encoding::{utf8_percent_encode, NON_ALPHANUMERIC};
    const QUOTE: &percent_encoding::AsciiSet = &NON_ALPHANUMERIC.remove(b'_').remove(b'.').remove(b'-').remove(b'~').remove(b'/');
    format!("{endpoint}/{repo}/resolve/{revision}/{}", utf8_percent_encode(path, QUOTE))
}

/// downloadFile: up to 3 attempts, none more after a 4xx other than 429; a failed attempt's file is removed.
/// `expected`: the size to count `progress` against when the server does not tell it (GitHub's
/// archives come chunked); up to 0.99 then, as it is only about
pub(crate) fn download_file(http: &Http, url: &str, path: &Path, progress: Option<&dyn Fn(f64)>, expected: Option<u64>,
                 what: &str, log: &dyn Fn(&str, &str)) -> bool {
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
                match (progress, length, expected) {
                    (Some(f), Some(length @ 1..), _) => f(total as f64 / length as f64),
                    (Some(f), _, Some(expected @ 1..)) => f((total as f64 / expected as f64).min(0.99)),
                    _ => {}
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

/// How a model's download ended
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Outcome {
    Done,
    /// why, for the UI: "network" (not got: the connection, the server or writing the file),
    /// "sha256" (got, but not the catalog's file) or "disk_space" (not started)
    Failed(&'static str),
    /// stopped (`cancel`): the `.part` files are kept for the next time
    Cancelled,
}

/// left free on the drive beside the files
const DISK_MARGIN: u64 = 64 << 20;

/// `path` + ".part": the file while it comes
fn part_of(path: &Path) -> PathBuf {
    let mut name = path.as_os_str().to_owned();
    name.push(".part");
    name.into()
}

fn size_of(path: &Path) -> u64 {
    std::fs::metadata(path).map(|m| m.len()).unwrap_or(0)
}

fn sha256_of(path: &Path) -> std::io::Result<String> {
    use sha2::{Digest, Sha256};
    let mut file = std::fs::File::open(path)?;
    let mut hash = Sha256::new();
    let mut buf = vec![0u8; 1 << 20];
    loop {
        let n = file.read(&mut buf)?;
        if n == 0 {
            return Ok(format!("{:x}", hash.finalize()));
        }
        hash.update(&buf[..n]);
    }
}

/// The rest of `url` into `part` (`size` bytes in all): from the bytes it has, or from the start
/// when the server cannot resume. `on_bytes` gets the bytes the part has. Ok(true): the part keeps
/// bytes from before this call (resumed), Ok(false): all of it came now.
fn get_part(http: &Http, url: &str, part: &Path, size: u64, cancel: &AtomicBool, on_bytes: &dyn Fn(u64))
            -> std::result::Result<bool, DownloadError> {
    if let Some(parent) = part.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let have = size_of(part);
    if have == size {
        return Ok(true);
    }
    let mut file = std::fs::File::options().create(true).write(true).truncate(false).open(part)?;
    let mut get = |from: u64| {
        file.set_len(from)?;
        file.seek(SeekFrom::Start(from))?;
        let mut got = from;
        http.download_from(url, from, &mut |chunk, _| {
            if cancel.load(Ordering::SeqCst) {
                return Err(std::io::Error::new(std::io::ErrorKind::Interrupted, "cancelled"));
            }
            file.write_all(chunk)?;
            got += chunk.len() as u64;
            on_bytes(got);
            Ok(())
        })
    };
    let from = if have > size { 0 } else { have };
    match get(from) {
        Err(DownloadError::RangeIgnored | DownloadError::Status(416)) if from > 0 => get(0).map(|()| false),
        result => result.map(|()| from > 0),
    }
}

/// The complete `part`: its SHA-256 checked, then named `path` (an older file there is replaced).
/// false: not the file (the part is removed)
fn finish(part: &Path, path: &Path, sha256: &str) -> std::io::Result<bool> {
    if sha256_of(part)? != sha256 {
        let _ = std::fs::remove_file(part);
        return Ok(false);
    }
    if path.exists() {
        std::fs::remove_file(path)?;
    }
    std::fs::rename(part, path)?;
    Ok(true)
}

/// downloadWhisperWeight / downloadCTranslate2Weight for a model of the catalog, unless it already
/// loads: its files at the catalog's commit from `endpoint` (no "/" at the end), then the
/// tokenizer's in the Hugging Face cache layout v3.6.x's transformers wrote
/// (`tokenizer/models--org--name/snapshots/<commit>/`, `refs/main` once they are all there). A file
/// of the catalog's size is not fetched again. Up to 3 attempts a file, each resuming its `.part`;
/// none more after a 4xx other than 429, nor after a file got whole in one attempt that is not the
/// catalog's. `progress`: the bytes of the whole model there, 0 to 1.
#[allow(clippy::too_many_arguments)]
pub fn download_model(http: &Http, endpoint: &str, root: &Path, m: &CatalogModel, loads: &dyn Fn(&Path) -> bool,
                      cancel: &AtomicBool, progress: &dyn Fn(f64), log: &dyn Fn(&str, &str)) -> Outcome {
    let dir = m.dir(root);
    let tokenizer = m.tokenizer.as_ref().map(|t| (t, dir.join("tokenizer").join(format!("models--{}", t.repo.replace('/', "--")))));
    let tokenizer_there = m.tokenizer.as_ref().is_none_or(|t| {
        crate::hf_cache::snapshot_dir(&dir.join("tokenizer"), &t.repo).is_ok_and(|s| t.files.iter().all(|f| s.join(&f.path).is_file()))
    });
    if tokenizer_there && check(&dir, loads) {
        progress(1.0);
        return Outcome::Done;
    }
    let mut files: Vec<(String, PathBuf, &CatalogFile)> = vec![];
    for (repo, base) in std::iter::once((&m.weights, dir.clone()))
        .chain(tokenizer.iter().map(|(t, cache)| (*t, cache.join("snapshots").join(&t.revision)))) {
        for f in &repo.files {
            let path = f.path.split('/').fold(base.clone(), |p, part| p.join(part));
            files.push((resolve_url(endpoint, &repo.repo, &repo.revision, &f.path), path, f));
        }
    }
    let there = |path: &Path, f: &CatalogFile| path.is_file() && size_of(path) == f.size;
    let todo: Vec<_> = files.iter().filter(|(_, path, f)| !there(path, f)).collect();
    let mut done: u64 = files.iter().filter(|(_, path, f)| there(path, f)).map(|(_, _, f)| f.size).sum();
    if !todo.is_empty() {
        if let Err(e) = std::fs::create_dir_all(&dir) {
            log(&format!("cannot make the weights folder: {e}"), &m.id);
            return Outcome::Failed("network");
        }
        let need = todo.iter().map(|(_, path, f)| f.size.saturating_sub(size_of(&part_of(path)))).sum::<u64>() + DISK_MARGIN;
        if let Some(free) = crate::platform::free_space(&dir) {
            if free < need {
                log(&format!("not enough disk space ({free} bytes free, {need} needed)"), &m.id);
                return Outcome::Failed("disk_space");
            }
        }
    }
    let total = m.size().max(1) as f64;
    for (url, path, f) in todo {
        let part = part_of(path);
        let mut reason = None;
        for attempt in 1..=ATTEMPTS {
            if cancel.load(Ordering::SeqCst) {
                return Outcome::Cancelled;
            }
            let result = get_part(http, url, &part, f.size, cancel, &|got| progress(((done + got) as f64 / total).min(1.0)));
            if cancel.load(Ordering::SeqCst) {
                return Outcome::Cancelled;
            }
            reason = match result {
                Ok(resumed) => match finish(&part, path, &f.sha256) {
                    Ok(true) => None,
                    // the bytes from an earlier attempt may be the wrong ones: once more from the start
                    Ok(false) if resumed => Some("sha256"),
                    // all of it came now and is not the catalog's file: getting it again gives the same
                    Ok(false) => {
                        log("weight file is not the catalog's (sha256)", url);
                        return Outcome::Failed("sha256");
                    }
                    Err(e) => {
                        log(&format!("cannot keep the downloaded file: {e}"), url);
                        Some("network")
                    }
                },
                Err(DownloadError::Status(status @ 400..=499)) if status != 429 => {
                    log(&format!("weight file download failed ({status})"), url);
                    return Outcome::Failed("network");
                }
                Err(_) => Some("network"),
            };
            let Some(why) = reason else { break };
            if attempt < ATTEMPTS {
                log(&format!("weight file download failed ({why}), retrying ({attempt}/{})", ATTEMPTS - 1), url);
                std::thread::sleep(BACKOFF * attempt);
            }
        }
        if let Some(reason) = reason {
            return Outcome::Failed(reason);
        }
        done += f.size;
    }
    // the snapshot is named only once it is complete
    if let Some((t, cache)) = &tokenizer {
        let named = std::fs::create_dir_all(cache.join("refs")).and_then(|()| std::fs::write(cache.join("refs").join("main"), &t.revision));
        if let Err(e) = named {
            log(&format!("cannot name the tokenizer snapshot: {e}"), &t.repo);
            return Outcome::Failed("network");
        }
    }
    progress(1.0);
    Outcome::Done
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ids(list: &Value) -> Vec<&str> {
        list.as_array().unwrap().iter().map(|v| v.as_str().unwrap()).collect()
    }

    #[test]
    fn the_catalog_is_the_selectable_weight_types_in_their_order() {
        for kind in ["whisper", "ctranslate2"] {
            let upper = kind.to_uppercase();
            let catalog: Vec<&str> = catalog().iter().filter(|m| m.family.kind() == kind).map(|m| m.id.as_str()).collect();
            let list = crate::config::default_of(&format!("SELECTABLE_{upper}_WEIGHT_TYPE_LIST")).unwrap();
            let dict = crate::config::default_of(&format!("SELECTABLE_{upper}_WEIGHT_TYPE_DICT")).unwrap();
            assert_eq!(catalog, ids(list), "{kind}");
            assert_eq!(catalog, dict.as_object().unwrap().keys().map(String::as_str).collect::<Vec<_>>(), "{kind}");
        }
    }

    #[test]
    fn every_ctranslate2_model_has_a_language_table_and_its_tokenizer() {
        let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("../data/translation_settings/languages/languages.yml");
        let yaml: serde_yaml::Value = serde_yaml::from_slice(&std::fs::read(path).unwrap()).unwrap();
        for m in catalog().iter().filter(|m| m.family != Family::Whisper) {
            let key = m.languages.as_deref().unwrap();
            assert!(yaml["CTranslate2"][key]["source"].is_mapping(), "{}: {key}", m.id);
            let files: Vec<&str> = m.tokenizer.as_ref().unwrap().files.iter().map(|f| f.path.as_str()).collect();
            let expected: &[&str] = if m.family == Family::M2m100 { &["sentencepiece.bpe.model", "vocab.json"] } else { &["tokenizer.json"] };
            assert_eq!(files, expected, "{}", m.id);
        }
        assert_eq!(languages_key("nllb-200-3.3B-ct2-int8"), "nllb-200-3.3B-ct2-int8");
        assert_eq!(languages_key("not-in-the-catalog"), "not-in-the-catalog");
    }

    #[test]
    fn a_bad_catalog_entry_is_refused() {
        let file = r#"{"path": "model.bin", "size": 1, "sha256": "0000000000000000000000000000000000000000000000000000000000000000"}"#;
        let rev = "0123456789abcdef0123456789abcdef01234567";
        let catalog = |model: &str| format!(r#"{{"version": 1, "models": [{model}]}}"#);
        let whisper = |id: &str, rev: &str, file: &str| catalog(&format!(
            r#"{{"id": "{id}", "family": "whisper", "license": "MIT", "repo": "a/b", "revision": "{rev}", "files": [{file}]}}"#));
        assert_eq!(parse_catalog(&whisper("tiny", rev, file)).unwrap()[0].size(), 1);
        for bad_id in ["", ".x", "a/b", "a b", "..", r"a\\b"] {
            assert!(parse_catalog(&whisper(bad_id, rev, file)).is_err(), "{bad_id}");
        }
        assert!(parse_catalog(&whisper("tiny", "main", file)).is_err());
        assert!(parse_catalog(&whisper("tiny", &rev.to_uppercase(), file)).is_err());
        for path in ["../model.bin", "/model.bin", "C:/model.bin", "C:model.bin", "a/../../b", "model.bin:x", r"a\\b", "",
                     "pytorch_model.bin", "x.pt", "x.PTH", "x.pkl", "x.pickle", "x.ckpt", "./config.json"] {
            let f = file.replace("model.bin", path);
            assert!(parse_catalog(&whisper("tiny", rev, &f)).is_err(), "{path}");
        }
        assert!(parse_catalog(&whisper("tiny", rev, "")).is_err(), "no files");
        assert!(parse_catalog(&whisper("tiny", rev, &file.replace("\"size\": 1", "\"size\": 0"))).is_err());
        assert!(parse_catalog(&whisper("tiny", rev, &file.replace("000\"", "00\""))).is_err(), "short sha256");
        assert!(parse_catalog(&whisper("tiny", rev, &format!("{file}, {file}"))).is_err(), "the same file twice");
        let one = whisper("tiny", rev, file);
        let inner = &one[r#"{"version": 1, "models": ["#.len()..one.len() - 2];
        assert!(parse_catalog(&catalog(&format!("{inner}, {inner}"))).is_err(), "the same id twice");
        assert!(parse_catalog(&one.replace("\"whisper\"", "\"gguf\"")).is_err(), "unknown family");
        assert!(parse_catalog(&one.replace("\"whisper\"", "\"nllb\"")).is_err(), "CTranslate2 without languages");
        assert!(parse_catalog(&one.replace("\"a/b\"", "\"../b\"")).is_err());
        assert!(parse_catalog(&one.replace("\"version\": 1", "\"version\": 2")).is_err());
    }
}
