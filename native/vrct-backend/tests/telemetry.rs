//! Telemetry against the Python backend (native/testdata/telemetry/telemetry.json, written by
//! native/reference/export_telemetry.py): the events sent and the state file after each app run.
mod support;

use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU16, Ordering};
use std::sync::Arc;
use support::{compare_requests, Mock};
use vrct_backend::net::Http;
use vrct_backend::telemetry::{today, Telemetry};

fn native() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("..")
}

fn yesterday() -> String {
    let t = today();
    let (mut y, mut m, mut d): (u32, u32, u32) = (t[0..4].parse().unwrap(), t[5..7].parse().unwrap(), t[8..10].parse().unwrap());
    if d > 1 {
        d -= 1;
    } else {
        if m > 1 { m -= 1 } else { m = 12; y -= 1 }
        let leap = y % 4 == 0 && (y % 100 != 0 || y % 400 == 0);
        d = [31, if leap { 29 } else { 28 }, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m as usize - 1];
    }
    format!("{y:04}-{m:02}-{d:02}")
}

/// export_telemetry.normalize_request
fn normalize_request(mut record: Value) -> Value {
    let timestamp = regex::Regex::new(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d{6})?Z$").unwrap();
    for event in record["body"]["json"].as_array_mut().into_iter().flatten() {
        assert!(timestamp.is_match(event["timestamp"].as_str().unwrap()), "{}", event["timestamp"]);
        assert!(event["sessionId"].as_str().unwrap().bytes().all(|b| b.is_ascii_digit()));
        event["timestamp"] = json!("<timestamp>");
        event["sessionId"] = json!("<session>");
    }
    record
}

#[test]
fn telemetry_matches_python() {
    let data: Value = serde_json::from_slice(&std::fs::read(native().join("testdata/telemetry/telemetry.json")).unwrap()).unwrap();
    let status = Arc::new(AtomicU16::new(200));
    let s = status.clone();
    let mock = Mock::start(Box::new(move |_: &Value| {
        let status = s.load(Ordering::SeqCst);
        (status, vec![], if status == 200 { b"{}".to_vec() } else { br#"{"error": "server"}"#.to_vec() })
    }));
    let http = Http::redirected(&mock.root).unwrap();
    let temp = std::env::temp_dir().join(format!("vrct-telemetry-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&temp);
    let storage = temp.join("sub").join("telemetry_state.json");
    let (today, yesterday) = (today(), yesterday());
    let mut problems = vec![];
    for step in data["steps"].as_array().unwrap() {
        let label = step["step"].as_str().unwrap();
        status.store(step["status"].as_u64().unwrap() as u16, Ordering::SeqCst);
        if let Some(before) = step["before"].as_str() {
            std::fs::create_dir_all(storage.parent().unwrap()).unwrap();
            std::fs::write(&storage, before.replace("<today>", &today).replace("<yesterday>", &yesterday)).unwrap();
        }
        let t = Telemetry::new(http.clone(), Some(data["app_key"].as_str().unwrap().into()));
        for call in step["calls"].as_array().unwrap() {
            match call[0].as_str().unwrap() {
                "init" => t.init(call[1].as_bool().unwrap(), "3.6.0", Some(&storage)),
                "track_error" => t.track_error(call[1].as_str().unwrap()),
                "shutdown" => t.shutdown(),
                other => panic!("{other}"),
            }
        }
        let file = std::fs::read_to_string(&storage).ok().map(|f| f.replace(&today, "<today>").replace(&yesterday, "<yesterday>"));
        if json!(file) != step["state_file"] {
            problems.push(format!("{label}: state file {file:?} != {}", step["state_file"]));
        }
        let rust: Vec<Value> = mock.take().into_iter().map(normalize_request).collect();
        problems.extend(compare_requests(label, step["requests"].as_array().unwrap(), &rust));
    }
    let _ = std::fs::remove_dir_all(&temp);
    for p in &problems {
        eprintln!("{p}");
    }
    assert!(problems.is_empty(), "{} problems", problems.len());
}

#[test]
fn no_key_sends_nothing_but_still_dedups() {
    let mock = Mock::start(Box::new(|_: &Value| (200, vec![], b"{}".to_vec())));
    let http = Http::redirected(&mock.root).unwrap();
    let storage = std::env::temp_dir().join(format!("vrct-telemetry-nokey-{}.json", std::process::id()));
    let _ = std::fs::remove_file(&storage);
    for key in [None, Some("A-SH-123".to_string()), Some("bad".to_string())] {
        let t = Telemetry::new(http.clone(), key);
        t.init(true, "3.6.0", Some(&storage));
        t.track_error("E1");
        t.shutdown();
    }
    assert!(mock.take().is_empty());
    let state: Value = serde_json::from_slice(&std::fs::read(&storage).unwrap()).unwrap();
    assert_eq!(state, json!({"last_app_started_date": today(), "errors_sent": {today(): ["E1"]}}));
    let _ = std::fs::remove_file(&storage);
}
