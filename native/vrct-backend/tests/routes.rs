//! The endpoints against the Python version's mainloop.py (native/testdata/ipc/routes.json, written
//! by native/reference/export_routes.py): the same endpoints in the same order, the same ones
//! answered while initializing, and the same push names (run_mapping).
use serde_json::Value;
use vrct_backend::app::routes::{routes, RUN_MAPPING};

fn python() -> Value {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../testdata/ipc/routes.json");
    serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap()
}

#[test]
fn endpoints_match_python() {
    let python = python();
    let expected: Vec<(String, bool)> = python["routes"].as_array().unwrap().iter()
        .map(|r| (r["endpoint"].as_str().unwrap().to_string(), r["during_init"].as_bool().unwrap()))
        .collect();
    let actual: Vec<(String, bool)> = routes().into_iter().map(|(e, r)| (e.to_string(), r.during_init)).collect();
    assert_eq!(actual, expected);
}

#[test]
fn run_mapping_matches_python() {
    let python = python();
    let expected: Vec<(String, String)> = python["run_mapping"].as_object().unwrap().iter()
        .map(|(k, v)| (k.clone(), v.as_str().unwrap().to_string()))
        .collect();
    let actual: Vec<(String, String)> = RUN_MAPPING.iter().map(|(k, v)| (k.to_string(), v.to_string())).collect();
    assert_eq!(actual, expected);
}
