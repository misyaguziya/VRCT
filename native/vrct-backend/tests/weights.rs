//! Weight downloads of the catalog's models against a local mock of the Hub (resume, SHA-256,
//! cancel, mirror), and the verified marker against the Python backend
//! (native/testdata/weights/weights.json, written by the Python backend's export_weights.py, removed
//! with it: kept as it is, not written again).
mod support;

use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::cell::RefCell;
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, UNIX_EPOCH};
use support::Mock;
use vrct_backend::net::Http;
use vrct_backend::weights::{self, CatalogModel, Outcome};

fn native() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("..")
}

fn temp_dir(name: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("vrct-weights-{name}-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    dir
}

const WEIGHTS_REV: &str = "1111111111111111111111111111111111111111";
const TOKENIZER_REV: &str = "2222222222222222222222222222222222222222";

/// The files the mock serves, by URL path
fn served() -> HashMap<String, Vec<u8>> {
    let model: Vec<u8> = (0..100_000u32).map(|i| (i % 251) as u8).collect();
    HashMap::from([
        (format!("/org/weights/resolve/{WEIGHTS_REV}/config.json"), b"{\"a\": 1}".to_vec()),
        (format!("/org/weights/resolve/{WEIGHTS_REV}/model.bin"), model),
        (format!("/org/tok/resolve/{TOKENIZER_REV}/tokenizer.json"), b"{\"tokenizer\": true}".to_vec()),
    ])
}

/// A CTranslate2 model of the served files
fn model() -> CatalogModel {
    let files = served();
    let entry = |path: &str| {
        let body = &files[path];
        json!({"path": path.rsplit('/').next().unwrap(), "size": body.len(), "sha256": format!("{:x}", Sha256::digest(body))})
    };
    let catalog = json!({"version": 1, "models": [{
        "id": "test-nllb", "family": "nllb", "languages": "x", "license": "MIT", "repo": "org/weights", "revision": WEIGHTS_REV,
        "files": [entry(&format!("/org/weights/resolve/{WEIGHTS_REV}/config.json")), entry(&format!("/org/weights/resolve/{WEIGHTS_REV}/model.bin"))],
        "tokenizer": {"repo": "org/tok", "revision": TOKENIZER_REV, "files": [entry(&format!("/org/tok/resolve/{TOKENIZER_REV}/tokenizer.json"))]},
    }]});
    weights::parse_catalog(&catalog.to_string()).unwrap().remove(0)
}

#[derive(Default)]
struct Mode {
    ignore_range: bool,
    corrupt: bool,
    /// model.bin is a relative redirect to /cdn/model.bin
    redirect: bool,
    missing: bool,
}

/// The mock Hub: Range answered with 206 (unless `ignore_range`); `cancel` is raised when model.bin is asked for
fn hub(mode: Arc<Mutex<Mode>>, cancel: Option<Arc<AtomicBool>>) -> Mock {
    let files = served();
    Mock::start(Box::new(move |entry: &Value| {
        let url = entry["url"].as_str().unwrap();
        // the origin is missing when a redirect dropped the header
        let mut path = match url.split_once("://") {
            Some((_, rest)) => rest[rest.find('/').unwrap()..].to_string(),
            None => url.to_string(),
        };
        let mode = mode.lock().unwrap();
        if path.ends_with("/model.bin") {
            if let Some(c) = &cancel {
                c.store(true, Ordering::SeqCst);
            }
            if mode.missing {
                return (404, vec![], b"not found".to_vec());
            }
            if mode.redirect && path != "/cdn/model.bin" {
                return (302, vec![("location", "/cdn/model.bin".into())], vec![]);
            }
            if path == "/cdn/model.bin" {
                path = format!("/org/weights/resolve/{WEIGHTS_REV}/model.bin");
            }
        }
        let Some(body) = files.get(&path) else { return (404, vec![], b"not found".to_vec()) };
        let mut body = body.clone();
        if mode.corrupt && path.ends_with("/model.bin") {
            body[10] ^= 1;
        }
        let octet = ("content-type", "application/octet-stream".to_string());
        match entry["headers"]["range"].as_str().and_then(|r| r.strip_prefix("bytes=")?.strip_suffix('-')?.parse::<usize>().ok()) {
            Some(from) if !mode.ignore_range && from < body.len() => {
                let range = format!("bytes {from}-{}/{}", body.len() - 1, body.len());
                (206, vec![octet, ("content-range", range)], body[from..].to_vec())
            }
            Some(_) if !mode.ignore_range => (416, vec![], vec![]),
            _ => (200, vec![octet], body),
        }
    }))
}

struct Run {
    outcome: Outcome,
    progress: Vec<f64>,
    /// (url, range header)
    requests: Vec<(String, Option<String>)>,
}

fn run(mock: &Mock, root: &Path, endpoint: &str, cancel: &AtomicBool, loads: bool) -> Run {
    let http = Http::redirected(&mock.root).unwrap();
    let progress = RefCell::new(vec![]);
    let outcome = weights::download_model(&http, endpoint, root, &model(), &|_| loads, cancel,
                                          &|p| progress.borrow_mut().push(p), &|_, _| {});
    let requests = mock.take().iter()
        .map(|r| (r["url"].as_str().unwrap().to_string(), r["headers"]["range"].as_str().map(String::from)))
        .collect();
    Run { outcome, progress: progress.into_inner(), requests }
}

fn model_bin(root: &Path) -> PathBuf {
    root.join("weights/ctranslate2/test-nllb/model.bin")
}

fn part(root: &Path) -> PathBuf {
    root.join("weights/ctranslate2/test-nllb/model.bin.part")
}

fn model_bytes() -> Vec<u8> {
    served()[&format!("/org/weights/resolve/{WEIGHTS_REV}/model.bin")].clone()
}

#[test]
fn a_new_download_asks_for_the_catalogs_files_only_and_names_the_tokenizer_snapshot() {
    let mock = hub(Arc::default(), None);
    let root = temp_dir("new");
    let r = run(&mock, &root, "https://huggingface.co", &AtomicBool::new(false), false);
    assert_eq!(r.outcome, Outcome::Done);
    let urls: Vec<&str> = r.requests.iter().map(|(u, _)| u.as_str()).collect();
    assert_eq!(urls, [
        format!("https://huggingface.co/org/weights/resolve/{WEIGHTS_REV}/config.json"),
        format!("https://huggingface.co/org/weights/resolve/{WEIGHTS_REV}/model.bin"),
        format!("https://huggingface.co/org/tok/resolve/{TOKENIZER_REV}/tokenizer.json"),
    ]);
    assert!(r.requests.iter().all(|(_, range)| range.is_none()));
    assert_eq!(r.progress.last(), Some(&1.0));
    assert!(r.progress.windows(2).all(|w| w[0] <= w[1]), "{:?}", r.progress);
    assert_eq!(std::fs::read(model_bin(&root)).unwrap(), model_bytes());
    assert!(!part(&root).exists());
    let cache = root.join("weights/ctranslate2/test-nllb/tokenizer");
    let snapshot = vrct_backend::hf_cache::snapshot_dir(&cache, "org/tok").unwrap();
    assert!(snapshot.ends_with(TOKENIZER_REV));
    assert_eq!(std::fs::read(snapshot.join("tokenizer.json")).unwrap(), b"{\"tokenizer\": true}");

    // the files there and loading: nothing is asked for
    let r = run(&mock, &root, "https://huggingface.co", &AtomicBool::new(false), true);
    assert_eq!((r.outcome, r.requests.len()), (Outcome::Done, 0));
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn a_part_is_resumed_with_a_range() {
    let mock = hub(Arc::default(), None);
    let root = temp_dir("resume");
    std::fs::create_dir_all(part(&root).parent().unwrap()).unwrap();
    std::fs::write(part(&root), &model_bytes()[..1000]).unwrap();
    let r = run(&mock, &root, "https://huggingface.co", &AtomicBool::new(false), false);
    assert_eq!(r.outcome, Outcome::Done);
    let model: Vec<_> = r.requests.iter().filter(|(u, _)| u.ends_with("model.bin")).collect();
    assert_eq!(model.len(), 1);
    assert_eq!(model[0].1.as_deref(), Some("bytes=1000-"));
    assert_eq!(r.progress.last(), Some(&1.0));
    assert_eq!(std::fs::read(model_bin(&root)).unwrap(), model_bytes());
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn a_server_that_ignores_the_range_is_read_again_from_the_start() {
    let mode = Arc::new(Mutex::new(Mode { ignore_range: true, ..Default::default() }));
    let mock = hub(mode, None);
    let root = temp_dir("ignored");
    std::fs::create_dir_all(part(&root).parent().unwrap()).unwrap();
    std::fs::write(part(&root), &model_bytes()[..1000]).unwrap();
    let r = run(&mock, &root, "https://huggingface.co", &AtomicBool::new(false), false);
    assert_eq!(r.outcome, Outcome::Done);
    let ranges: Vec<_> = r.requests.iter().filter(|(u, _)| u.ends_with("model.bin")).map(|(_, r)| r.clone()).collect();
    assert_eq!(ranges, [Some("bytes=1000-".to_string()), None]);
    assert_eq!(std::fs::read(model_bin(&root)).unwrap(), model_bytes());
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn a_relative_redirect_keeps_the_range() {
    let mode = Arc::new(Mutex::new(Mode { redirect: true, ..Default::default() }));
    let mock = hub(mode, None);
    let root = temp_dir("redirect");
    std::fs::create_dir_all(part(&root).parent().unwrap()).unwrap();
    std::fs::write(part(&root), &model_bytes()[..1000]).unwrap();
    let r = run(&mock, &root, "https://huggingface.co", &AtomicBool::new(false), false);
    assert_eq!(r.outcome, Outcome::Done);
    let cdn: Vec<_> = r.requests.iter().filter(|(u, _)| u.ends_with("/cdn/model.bin")).collect();
    assert_eq!(cdn.len(), 1, "{:?}", r.requests);
    assert_eq!(cdn[0].1.as_deref(), Some("bytes=1000-"));
    assert_eq!(std::fs::read(model_bin(&root)).unwrap(), model_bytes());
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn a_file_that_is_not_the_catalogs_is_removed_and_fails() {
    let mode = Arc::new(Mutex::new(Mode { corrupt: true, ..Default::default() }));
    let mock = hub(mode, None);
    let root = temp_dir("sha");
    let r = run(&mock, &root, "https://huggingface.co", &AtomicBool::new(false), false);
    assert_eq!(r.outcome, Outcome::Failed("sha256"));
    assert_eq!(r.requests.iter().filter(|(u, _)| u.ends_with("model.bin")).count(), 3, "3 attempts");
    assert!(!model_bin(&root).exists() && !part(&root).exists());
    assert!(vrct_backend::hf_cache::snapshot_dir(&root.join("weights/ctranslate2/test-nllb/tokenizer"), "org/tok").is_err());
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn a_404_is_not_tried_again_and_the_part_is_kept() {
    let mode = Arc::new(Mutex::new(Mode { missing: true, ..Default::default() }));
    let mock = hub(mode, None);
    let root = temp_dir("missing");
    std::fs::create_dir_all(part(&root).parent().unwrap()).unwrap();
    std::fs::write(part(&root), &model_bytes()[..1000]).unwrap();
    let r = run(&mock, &root, "https://huggingface.co", &AtomicBool::new(false), false);
    assert_eq!(r.outcome, Outcome::Failed("network"));
    assert_eq!(r.requests.iter().filter(|(u, _)| u.ends_with("model.bin")).count(), 1);
    assert_eq!(std::fs::metadata(part(&root)).unwrap().len(), 1000);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn a_cancelled_download_keeps_its_part() {
    let cancel = Arc::new(AtomicBool::new(false));
    let mock = hub(Arc::default(), Some(cancel.clone()));
    let root = temp_dir("cancel");
    std::fs::create_dir_all(part(&root).parent().unwrap()).unwrap();
    std::fs::write(part(&root), &model_bytes()[..1000]).unwrap();
    let r = run(&mock, &root, "https://huggingface.co", &cancel, false);
    assert_eq!(r.outcome, Outcome::Cancelled);
    assert_eq!(std::fs::read(part(&root)).unwrap(), &model_bytes()[..1000]);
    assert!(!model_bin(&root).exists());
    assert!(!r.requests.iter().any(|(u, _)| u.ends_with("tokenizer.json")), "nothing after the cancel");
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn a_mirror_gets_every_request() {
    let mock = hub(Arc::default(), None);
    let root = temp_dir("mirror");
    let r = run(&mock, &root, "https://hf-mirror.com", &AtomicBool::new(false), false);
    assert_eq!(r.outcome, Outcome::Done);
    assert_eq!(r.requests.len(), 3);
    assert!(r.requests.iter().all(|(u, _)| u.starts_with("https://hf-mirror.com/")), "{:?}", r.requests);
    let _ = std::fs::remove_dir_all(&root);
}

fn set_mtime(path: &Path, ns: u64) {
    std::fs::File::options().write(true).open(path).unwrap()
        .set_modified(UNIX_EPOCH + Duration::from_nanos(ns)).unwrap();
}

#[test]
fn marker_matches_python() {
    let data: Value = serde_json::from_slice(&std::fs::read(native().join("testdata/weights/weights.json")).unwrap()).unwrap();
    let marker = &data["marker"];
    let root = temp_dir("marker");
    for (name, content) in marker["files"].as_object().unwrap() {
        let path = root.join(name);
        std::fs::create_dir_all(path.parent().unwrap()).unwrap();
        std::fs::write(&path, content.as_str().unwrap()).unwrap();
        set_mtime(&path, marker["mtime_ns"][name].as_u64().unwrap());
    }
    assert!(!weights::is_verified(&root));
    weights::write_verified(&root);
    let written: Value = serde_json::from_slice(&std::fs::read(root.join(weights::MARKER)).unwrap()).unwrap();
    let expected = &marker["written"]["verified_files"];
    for (name, stat) in written["verified_files"].as_object().unwrap() {
        for key in ["size", "mtime"] {
            assert_eq!(stat[key].as_f64(), expected[name][key].as_f64(), "{name} {key}");
        }
    }
    assert_eq!(written["verified_files"].as_object().unwrap().len(), expected.as_object().unwrap().len());
    assert_eq!(json!(weights::is_verified(&root)), marker["verified"]);
    // the marker v3.6.x wrote is accepted
    std::fs::write(root.join(weights::MARKER), serde_json::to_vec(&marker["written"]).unwrap()).unwrap();
    assert_eq!(json!(weights::is_verified(&root)), marker["verified"]);
    let config_ns = marker["mtime_ns"]["config.json"].as_u64().unwrap();
    set_mtime(&root.join("config.json"), config_ns + 10_000_000);
    assert_eq!(json!(weights::is_verified(&root)), marker["verified_after_touch"]);
    // check(): a load that succeeds writes the marker again
    assert!(weights::check(&root, &|_| true));
    assert!(weights::is_verified(&root));
    std::fs::write(root.join("extra.bin"), b"x").unwrap();
    assert!(!weights::check(&root, &|_| false));
    let _ = std::fs::remove_dir_all(&root);
}
