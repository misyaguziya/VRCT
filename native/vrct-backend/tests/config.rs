//! The settings against the Python version: the schema (native/data/config_schema.json) and the
//! checks of every property for many values, in the same order (native/testdata/config/checks.json,
//! written by native/reference/export_config_checks.py)
use serde_json::{json, Value};
use std::sync::Arc;
use vrct_backend::config::{props, Config, DeviceLists, Env};

fn read(path: &str) -> Value {
    let p = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join(path);
    serde_json::from_slice(&std::fs::read(p).unwrap()).unwrap()
}

#[test]
fn checks_match_python() {
    let checks = read("../testdata/config/checks.json");
    let dir = std::env::temp_dir().join(format!("vrct-config-checks-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let config = Config::new(Env {
        path_local: dir.clone(),
        compute_devices: checks["env"]["SELECTABLE_COMPUTE_DEVICE_LIST"].as_array().unwrap().clone(),
        default_mic: ("NoHost".into(), "NoDevice".into()),
        default_speaker: "NoDevice".into(),
        devices: Arc::new(DeviceLists::default),
        transcription_lang: read("../data/transcription_languages.json"),
        new_token: || "token".into(),
    });
    let mut differences = vec![];
    for case in checks["cases"].as_array().unwrap() {
        let name = case["name"].as_str().unwrap();
        let result = config.set(name, case["value"].clone());
        let ok = match (&result, case.get("stored")) {
            (Err(_), None) => true,
            (Ok(()), Some(stored)) => config.get(name) == *stored,
            _ => false,
        };
        if !ok {
            differences.push(format!("{name} = {}: python {}, rust {:?} -> {}", case["value"],
                                     case.get("stored").map_or("rejected".into(), |s| s.to_string()), result, config.get(name)));
        }
    }
    let _ = std::fs::remove_dir_all(&dir);
    assert!(differences.is_empty(), "{} of {}:\n{}", differences.len(), checks["cases"].as_array().unwrap().len(),
            differences.iter().take(30).cloned().collect::<Vec<_>>().join("\n"));
}

#[test]
fn saved_in_python_order() {
    let schema = read("../data/config_schema.json");
    let order: Vec<&str> = schema["serialized_order"].as_array().unwrap().iter().map(|v| v.as_str().unwrap()).collect();
    let ours: Vec<&str> = props().iter().filter(|p| p.serialize && !p.readonly).map(|p| p.name.as_str()).collect();
    assert_eq!(ours, order);
    let _ = json!(null);
}
