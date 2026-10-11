//! DeepL against the Python backend (native/testdata/deepl/deepl.json, written by
//! native/reference/export_deepl.py) through Translator: results (text / None / False) and requests.
mod support;

use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use support::{compare_requests, Mock};
use vrct_backend::net::Http;
use vrct_backend::translate::{Translation, Translator};

fn native() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("..")
}

#[test]
fn deepl_matches_python() {
    let data: Value = serde_json::from_slice(&std::fs::read(native().join("testdata/deepl/deepl.json")).unwrap()).unwrap();
    let busy = AtomicUsize::new(0);
    // export_deepl.responder
    let mock = Mock::start(Box::new(move |entry: &Value| {
        let auth = entry["headers"]["authorization"].as_str().unwrap_or("");
        let reply = |status, v: Value| (status, vec![], serde_json::to_vec(&v).unwrap());
        if auth.contains("bad") {
            return reply(403, json!({"message": "Wrong endpoint"}));
        }
        if auth.contains("quota") {
            return reply(456, json!({"message": "Quota exceeded"}));
        }
        if auth.contains("busy") && busy.fetch_add(1, Ordering::SeqCst) < 1 {
            return reply(429, json!({"message": "Too many requests"}));
        }
        let body = &entry["body"]["json"];
        let target = body["target_lang"].as_str().unwrap_or("");
        let translations: Vec<Value> = body["text"].as_array().unwrap().iter().map(|t| {
            let t = t.as_str().unwrap();
            json!({"detected_source_language": "JA", "text": format!("[{target}] {t}"), "billed_characters": t.chars().count()})
        }).collect();
        reply(200, json!({"translations": translations}))
    }));
    let settings = native().join("../src-python/models/translation/translation_settings");
    let mut t = Translator::new(Http::redirected(&mock.root).unwrap(), &settings).unwrap();
    let message = "こんにちは、\n世界！ & <tag>";
    let mut problems = vec![];
    for step in data["steps"].as_array().unwrap() {
        let label = step["step"].as_str().unwrap();
        let result = if let Some(key) = label.strip_prefix("auth_") {
            let key = match key { "bad" => "bad-key:fx", "free" => "free-key:fx", "pro" => "pro-key", k => &format!("{k}-key") };
            json!(t.authenticate_deepl(key).unwrap_or(false))
        } else {
            let (source, target, country, text) = match label.strip_prefix("translate ") {
                Some(rest) => {
                    let (pair, country) = rest.split_once(" (").unwrap();
                    let (s, g) = pair.split_once("->").unwrap();
                    (s.to_string(), g.to_string(), country.trim_end_matches(')').to_string(), message)
                }
                None => ("Japanese".into(), "English".into(), "Japan".into(), "テスト"),
            };
            match t.translate("DeepL_API", "", &source, &target, &country, text, &[]) {
                Translation::Text(s) => json!(s),
                Translation::Unsupported => Value::Null,
                Translation::Failed(_) => json!(false),
            }
        };
        if result != step["result"] {
            problems.push(format!("{label}: result {result} != {}", step["result"]));
        }
        problems.extend(compare_requests(label, step["requests"].as_array().unwrap(), &mock.take()));
    }
    for p in &problems {
        eprintln!("{p}");
    }
    assert!(problems.is_empty(), "{} problems", problems.len());
}
