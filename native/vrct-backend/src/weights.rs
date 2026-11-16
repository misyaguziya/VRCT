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

/// huggingface_hub.hf_hub_url: the file name quoted as urllib.parse.quote (letters, digits and
/// "_.-~/" kept)
pub fn hf_hub_url(repo: &str, filename: &str) -> String {
    use percent_encoding::{utf8_percent_encode, NON_ALPHANUMERIC};
    const QUOTE: &percent_encoding::AsciiSet = &NON_ALPHANUMERIC.remove(b'_').remove(b'.').remove(b'-').remove(b'~').remove(b'/');
    format!("https://huggingface.co/{repo}/resolve/main/{}", utf8_percent_encode(filename, QUOTE))
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
            download_file(http, &hf_hub_url(repo, name), &path.join(name), progress, None, "Whisper", log);
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
    let m = ctranslate2_model(weight_type)?;
    let path = m.dir(root);
    if check(&path, loads) {
        return Ok(true);
    }
    let mut files = None;
    for attempt in 1..=ATTEMPTS {
        match list_repo_files(http, &m.weights.repo) {
            Ok(f) => {
                files = Some(f);
                break;
            }
            Err(_) if attempt < ATTEMPTS => {
                log(&format!("CTranslate2 repo listing failed, retrying ({attempt}/{})", ATTEMPTS - 1), &m.weights.repo);
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
        all &= download_file(http, &hf_hub_url(&m.weights.repo, name), &file, progress, None, "CTranslate2", log);
    }
    end();
    Ok(all)
}

/// downloadCTranslate2Tokenizer: the tokenizer files the translator reads, in the Hugging Face cache
/// layout v3.6.x's transformers wrote (`tokenizer/models--org--name/snapshots/<commit>/`, `refs/main`).
/// Nothing is fetched when they are there (transformers asked the Hub for a newer revision every time).
pub fn download_tokenizer(http: &Http, root: &Path, weight_type: &str, log: &dyn Fn(&str, &str)) -> Result<()> {
    let m = ctranslate2_model(weight_type)?;
    let cache = m.dir(root).join("tokenizer");
    let tokenizer = m.tokenizer.as_ref().unwrap();
    let files: Vec<&str> = tokenizer.files.iter().map(|f| f.path.as_str()).collect();
    if crate::hf_cache::snapshot_dir(&cache, &tokenizer.repo).is_ok_and(|s| files.iter().all(|f| s.join(f).is_file())) {
        return Ok(());
    }
    let url = format!("https://huggingface.co/api/models/{}/revision/main", tokenizer.repo);
    let response = http.get(&url, &[], Some(Duration::from_secs(10)))?;
    if !response.status().is_success() {
        bail!("{url}: {}", response.status());
    }
    let info: Value = response.json()?;
    let Some(commit) = info["sha"].as_str().filter(|c| !c.is_empty() && c.chars().all(|c| c.is_ascii_alphanumeric())) else {
        bail!("{url}: no commit");
    };
    let repo = cache.join(format!("models--{}", tokenizer.repo.replace('/', "--")));
    for name in files {
        let url = format!("https://huggingface.co/{}/resolve/{commit}/{name}", tokenizer.repo);
        if !download_file(http, &url, &repo.join("snapshots").join(commit).join(name), None, None, "Tokenizer", log) {
            bail!("{url}: download failed");
        }
    }
    // the snapshot is named only once it is complete
    std::fs::create_dir_all(repo.join("refs"))?;
    std::fs::write(repo.join("refs").join("main"), commit)?;
    Ok(())
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

    // ponytail: the bridge to the tables the catalog replaces, removed with them
    #[test]
    fn the_catalog_has_the_repos_of_the_old_tables() {
        for (id, repo) in WHISPER_MODELS {
            assert_eq!(model(id).unwrap().weights.repo, repo);
        }
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
