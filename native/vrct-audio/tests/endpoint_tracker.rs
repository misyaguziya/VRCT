//! The active-endpoint decision against active_endpoint_tracker.py
//! (native/testdata/audio/endpoint_tracker.json, written by native/reference/export_endpoint_tracker.py).
#![cfg(feature = "devices")]
use serde_json::Value;
use vrct_audio::endpoints::Selector;

#[test]
fn selection_matches_python() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../testdata/audio/endpoint_tracker.json");
    let data: Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    let mut problems = 0;
    for (n, polls) in data["scenarios"].as_array().unwrap().iter().enumerate() {
        let mut selector = Selector::default();
        for (i, poll) in polls.as_array().unwrap().iter().enumerate() {
            let peaks: Vec<(String, f64)> = poll["peaks"].as_object().unwrap().iter()
                .map(|(k, v)| (k.clone(), v.as_f64().unwrap())).collect();
            let got = selector.update(&peaks, poll["now"].as_f64().unwrap());
            if got.as_deref() != poll["selected"].as_str() {
                eprintln!("scenario {n} poll {i}: {got:?} != {}", poll["selected"]);
                problems += 1;
                break;
            }
        }
    }
    assert_eq!(problems, 0);
}
