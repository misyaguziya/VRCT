//! Software updates against the Python backend (native/testdata/update/update.json, written by
//! native/reference/export_update.py): results, installer arguments, the written setup file,
//! requests, and packaging.version's comparisons.
mod support;

use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::cell::RefCell;
use std::path::{Path, PathBuf};
use support::{compare_requests, Mock};
use vrct_backend::net::Http;
use vrct_backend::update::{channel_for_version, is_version_supported, Settings, Updater, Version};

fn native() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("..")
}

/// export_update.make_setup
fn make_setup(size: usize) -> Vec<u8> {
    (0..size).map(|i| ((i * 7 + 3) % 251) as u8).collect()
}

#[test]
fn update_matches_python() {
    let data: Value = serde_json::from_slice(&std::fs::read(native().join("testdata/update/update.json")).unwrap()).unwrap();
    let setup = make_setup(data["setup_size"].as_u64().unwrap() as usize);
    let sha: String = Sha256::digest(&setup).iter().map(|b| format!("{b:02x}")).collect();
    assert_eq!(sha, data["setup_sha256"].as_str().unwrap());
    let releases = data["releases"].clone();
    let latest = releases[2].clone();
    let (setup_body, sha_body) = (setup.clone(), sha.clone());
    // export_update.responder
    let mock = Mock::start(Box::new(move |entry: &Value| {
        let url = entry["url"].as_str().unwrap();
        let text = |status, t: String| (status, vec![("content-type", "text/plain".to_string())], t.into_bytes());
        if url.ends_with("/releases/latest") {
            return (200, vec![], serde_json::to_vec(&latest).unwrap());
        }
        if url.ends_with("/releases") {
            return (200, vec![], serde_json::to_vec(&releases).unwrap());
        }
        if url.ends_with("ok.sha256") {
            return text(200, format!("{}  VRCT_setup.exe\n", sha_body.to_uppercase()));
        }
        if url.ends_with("beta2.sha256") {
            return text(200, sha_body.clone());
        }
        if url.ends_with("bad.sha256") {
            return text(200, "0".repeat(64));
        }
        if url.ends_with("broken.sha256") {
            return text(500, "error".into());
        }
        if url.ends_with("VRCT_setup.exe") {
            if url.contains("/v3.4.0/") || url.contains("/v3.6.1-rc.1/") {
                return text(404, "not found".into());
            }
            return (200, vec![("content-type", "application/octet-stream".into())], setup_body.clone());
        }
        (404, vec![], br#"{"error": "not found"}"#.to_vec())
    }));
    let http = Http::redirected(&mock.root).unwrap();
    let temp = std::env::temp_dir().join(format!("vrct-update-test-{}", std::process::id()));
    std::fs::create_dir_all(&temp).unwrap();
    let mut problems = vec![];
    for step in data["steps"].as_array().unwrap() {
        let label = step["step"].as_str().unwrap();
        let settings = Settings {
            channel: step["settings"]["SELECTED_RELEASE_CHANNEL"].as_str().unwrap().into(),
            version: step["settings"]["VERSION"].as_str().unwrap().into(),
            ui_language: "ja".into(),
            path_local: temp.clone(),
        };
        let _ = std::fs::remove_file(temp.join("VRCT_setup.exe"));
        let updater = Updater { http: &http, settings, log: &|_| {} };
        let launched = RefCell::new(vec![]);
        let launch = |args: &[String], cwd: &Path| launched.borrow_mut().push(json!({"args": args, "cwd_is_local": cwd == temp.as_path()}));
        let result = if label.starts_with("check") {
            let (update, version) = updater.check_software_updated();
            json!({"is_update_available": update, "new_version": version})
        } else if label == "list releases" {
            json!(updater.list_available_releases().into_iter().map(|r| json!({"tag": r.tag, "version": r.version,
                "is_prerelease": r.is_prerelease, "published_at": r.published_at})).collect::<Vec<_>>())
        } else {
            let mut words = label.split(' ').skip(1);
            let edition = words.next().unwrap();
            let target = words.nth(1).filter(|t| *t != "None");
            let r = updater.update(edition, target, &launch);
            if r == "launched" {
                launched.borrow_mut().push(json!("quit"));
            }
            json!(r)
        };
        if result != step["result"] {
            problems.push(format!("{label}: result {result} != {}", step["result"]));
        }
        if json!(*launched.borrow()) != step["launched"] {
            problems.push(format!("{label}: launched {:?} != {}", launched.borrow(), step["launched"]));
        }
        let written = std::fs::read(temp.join("VRCT_setup.exe")).is_ok_and(|b| b == setup);
        if json!(written) != step["setup_written"] {
            problems.push(format!("{label}: setup written {written} != {}", step["setup_written"]));
        }
        problems.extend(compare_requests(label, step["requests"].as_array().unwrap(), &mock.take()));
    }
    for case in data["compare"].as_array().unwrap() {
        let (a, b) = (case["a"].as_str().unwrap(), case["b"].as_str().unwrap());
        let got = match (Version::parse(a), Version::parse(b)) {
            (Some(x), Some(y)) => (json!(x > y), json!(x == y)),
            _ => (Value::Null, Value::Null),
        };
        if got != (case["gt"].clone(), case["eq"].clone()) {
            problems.push(format!("compare {a:?} {b:?}: {got:?} != {} {}", case["gt"], case["eq"]));
        }
    }
    for (v, expected) in data["supported"].as_object().unwrap() {
        if json!(is_version_supported(v)) != *expected {
            problems.push(format!("supported {v:?} != {expected}"));
        }
    }
    for (v, expected) in data["channel"].as_object().unwrap() {
        if channel_for_version(v) != expected.as_str().unwrap() {
            problems.push(format!("channel {v:?} != {expected}"));
        }
    }
    let _ = std::fs::remove_dir_all(&temp);
    eprintln!("{} steps, {} comparisons, problems {}", data["steps"].as_array().unwrap().len(),
              data["compare"].as_array().unwrap().len(), problems.len());
    for p in problems.iter().take(30) {
        eprintln!("{p}");
    }
    assert!(problems.is_empty(), "{} problems", problems.len());
}
