//! Weight downloads and the verified marker against the Python backend
//! (native/testdata/weights/weights.json, written by native/reference/export_weights.py): results,
//! progress, the written files, requests, and the marker's content and checks.
mod support;

use serde_json::{json, Value};
use std::cell::RefCell;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, AtomicU32, Ordering};
use std::sync::Arc;
use std::time::{Duration, UNIX_EPOCH};
use support::{compare_requests, Mock};
use vrct_backend::net::Http;
use vrct_backend::weights;

fn native() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("..")
}

/// export_weights.files_under: {relative path: the first 40 characters}
fn files_under(root: &Path) -> Value {
    fn walk(root: &Path, dir: &Path, out: &mut std::collections::BTreeMap<String, Value>) {
        for entry in std::fs::read_dir(dir).unwrap().flatten() {
            let path = entry.path();
            if path.is_dir() {
                walk(root, &path, out);
            } else {
                let text: String = String::from_utf8_lossy(&std::fs::read(&path).unwrap()).chars().take(40).collect();
                out.insert(path.strip_prefix(root).unwrap().to_string_lossy().replace('\\', "/"), json!(text));
            }
        }
    }
    let mut out = Default::default();
    walk(root, root, &mut out);
    json!(out)
}

fn temp_dir(name: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("vrct-weights-{name}-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    dir
}

#[test]
fn downloads_match_python() {
    let data: Value = serde_json::from_slice(&std::fs::read(native().join("testdata/weights/weights.json")).unwrap()).unwrap();
    let trees = data["trees"].clone();
    let (flaky, tree_fail) = (Arc::new(AtomicU32::new(0)), Arc::new(AtomicBool::new(false)));
    let (f, t) = (flaky.clone(), tree_fail.clone());
    // export_weights.responder
    let mock = Mock::start(Box::new(move |entry: &Value| {
        let url = entry["url"].as_str().unwrap();
        let text = |status, s: &str| (status, vec![("content-type", "text/plain".to_string())], s.as_bytes().to_vec());
        if let Some(rest) = url.split_once("/api/models/").map(|x| x.1) {
            if t.load(Ordering::SeqCst) {
                return (500, vec![], br#"{"error": "server"}"#.to_vec());
            }
            let repo = rest.split("/tree/").next().unwrap();
            let tree: Vec<Value> = trees[repo].as_array().unwrap().iter().enumerate()
                .map(|(i, p)| json!({"type": "file", "oid": format!("oid{i}"), "size": 10, "path": p})).collect();
            return (200, vec![], serde_json::to_vec(&tree).unwrap());
        }
        if let Some(name) = url.split_once("/resolve/main/").map(|x| x.1) {
            if name.ends_with("missing.txt") || name == "preprocessor_config.json" || name == "vocabulary.json" {
                return text(404, "not found");
            }
            if name.ends_with("flaky.txt") && f.load(Ordering::SeqCst) < 1 {
                f.fetch_add(1, Ordering::SeqCst);
                return text(500, "busy");
            }
            let body = format!("content of {name}").repeat(if name.ends_with("model.bin") { 3000 } else { 1 });
            return (200, vec![("content-type", "application/octet-stream".into())], body.into_bytes());
        }
        (404, vec![], br#"{"error": "not found"}"#.to_vec())
    }));
    let http = Http::redirected(&mock.root).unwrap();
    let mut problems = vec![];
    for step in data["steps"].as_array().unwrap() {
        let label = step["step"].as_str().unwrap();
        tree_fail.store(label.ends_with("tree fails"), Ordering::SeqCst);
        let root = temp_dir("download");
        let progress = RefCell::new(vec![]);
        let (on_progress, on_end) = (|p: f64| progress.borrow_mut().push(json!(p)), || progress.borrow_mut().push(json!("end")));
        // the files are not a real model, so they never load (as in the Python run)
        let loads = |_: &Path| false;
        let result = if label.starts_with("whisper") {
            weights::download_whisper(&http, &root, "base", &loads, &on_progress, &on_end, &|_, _| {}).map(|()| Value::Null)
        } else {
            weights::download_ctranslate2(&http, &root, "m2m100_418M-ct2-int8", &loads, &on_progress, &on_end, &|_, _| {})
                .map(Value::Bool)
        }.unwrap();
        if result != step["result"] {
            problems.push(format!("{label}: result {result} != {}", step["result"]));
        }
        let last = progress.borrow().last().cloned().unwrap_or(Value::Null);
        if last != step["progress_last"] {
            problems.push(format!("{label}: progress {last} != {}", step["progress_last"]));
        }
        let files = files_under(&root);
        if files != step["files"] {
            problems.push(format!("{label}: files {files} != {}", step["files"]));
        }
        problems.extend(compare_requests(label, step["requests"].as_array().unwrap(), &mock.take()));
        let _ = std::fs::remove_dir_all(&root);
    }
    for p in &problems {
        eprintln!("{p}");
    }
    assert!(problems.is_empty(), "{} problems", problems.len());
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

/// The tokenizer (B level: transformers' own requests are not reproduced, only the cache it leaves)
#[test]
fn tokenizer_download() {
    let missing = Arc::new(AtomicBool::new(false));
    let m = missing.clone();
    let mock = Mock::start(Box::new(move |entry: &Value| {
        let url = entry["url"].as_str().unwrap();
        if url.ends_with("/api/models/facebook/m2m100_418M/revision/main") {
            return (200, vec![], br#"{"id": "facebook/m2m100_418M", "sha": "abc123"}"#.to_vec());
        }
        if m.load(Ordering::SeqCst) && url.ends_with("vocab.json") {
            return (404, vec![], b"not found".to_vec());
        }
        match url.split_once("/facebook/m2m100_418M/resolve/abc123/") {
            Some((_, name)) => (200, vec![], format!("content of {name}").into_bytes()),
            None => (404, vec![], b"not found".to_vec()),
        }
    }));
    let http = Http::redirected(&mock.root).unwrap();
    let root = temp_dir("tokenizer");
    let cache = root.join("weights/ctranslate2/m2m100_418M-ct2-int8/tokenizer");

    missing.store(true, Ordering::SeqCst);
    assert!(weights::download_tokenizer(&http, &root, "m2m100_418M-ct2-int8", &|_, _| {}).is_err());
    assert!(vrct_backend::hf_cache::snapshot_dir(&cache, "facebook/m2m100_418M").is_err(), "no ref to an incomplete snapshot");
    mock.take();

    missing.store(false, Ordering::SeqCst);
    weights::download_tokenizer(&http, &root, "m2m100_418M-ct2-int8", &|_, _| {}).unwrap();
    let urls: Vec<Value> = mock.take().iter().map(|r| r["url"].clone()).collect();
    assert_eq!(urls, [
        "https://huggingface.co/api/models/facebook/m2m100_418M/revision/main",
        "https://huggingface.co/facebook/m2m100_418M/resolve/abc123/sentencepiece.bpe.model",
        "https://huggingface.co/facebook/m2m100_418M/resolve/abc123/vocab.json",
    ]);
    let snapshot = vrct_backend::hf_cache::snapshot_dir(&cache, "facebook/m2m100_418M").unwrap();
    assert_eq!(std::fs::read_to_string(snapshot.join("vocab.json")).unwrap(), "content of vocab.json");

    weights::download_tokenizer(&http, &root, "m2m100_418M-ct2-int8", &|_, _| {}).unwrap();
    assert!(mock.take().is_empty(), "nothing is fetched when the files are there");
    let _ = std::fs::remove_dir_all(&root);
}
