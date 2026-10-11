//! The OBS browser source page against the Python backend (native/testdata/obs/obs.json, written by
//! native/reference/export_obs.py): the page for each config, and the answer for each path.
use serde_json::{json, Value};
use std::path::Path;
use vrct_backend::obs::{build_overlay_html, ObsServer};

fn data() -> Value {
    let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("../testdata/obs/obs.json");
    serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap()
}

#[test]
fn page_matches_python() {
    for case in data()["pages"].as_array().unwrap() {
        let html = build_overlay_html(case["config"].as_object().unwrap(), case["ws_token"].as_str().unwrap());
        assert!(html == case["html"].as_str().unwrap(), "config {} token {}", case["config"], case["ws_token"]);
    }
}

#[test]
fn server_answers_like_python() {
    let data = data();
    let config = data["pages"][2]["config"].as_object().unwrap().clone();
    let server = ObsServer::start("127.0.0.1", 0, move || build_overlay_html(&config, "tok")).unwrap();
    let port = server.port();
    let client = reqwest::blocking::Client::new();
    for expected in data["responses"].as_array().unwrap() {
        let method: reqwest::Method = expected["method"].as_str().unwrap().parse().unwrap();
        let path = expected["path"].as_str().unwrap();
        let r = client.request(method.clone(), format!("http://127.0.0.1:{port}{path}")).send().unwrap();
        let header = |name: &str| r.headers().get(name).map(|v| v.to_str().unwrap().to_string());
        let mut got = json!({"method": method.as_str(), "path": path, "status": r.status().as_u16(),
                             "content_type": header("content-type"), "cache_control": header("cache-control")});
        let body = r.text().unwrap();
        got["body"] = if got["status"] == 200 && method != reqwest::Method::HEAD { json!(body) } else { Value::Null };
        // Python's error pages carry its own HTML; only the status is part of the contract
        if expected["status"] != 200 {
            got["content_type"] = expected["content_type"].clone();
        }
        assert!(got == *expected, "{path}: {} != {}", got.to_string().chars().take(300).collect::<String>(),
                expected.to_string().chars().take(300).collect::<String>());
    }
    drop(server);
    // stopped: the port is free again
    drop(ObsServer::start("127.0.0.1", port, String::new).unwrap());
}
