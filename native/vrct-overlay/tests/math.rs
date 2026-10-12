//! Overlay positions against the Python version (native/testdata/overlay/math.json, written by
//! native/reference/export_overlay_math.py)
use serde_json::Value;
use vrct_overlay::math::{position_transform, Mat34, Tracker};

fn mat(v: &Value) -> Mat34 {
    let rows: Vec<[f64; 4]> = v.as_array().unwrap().iter()
        .map(|r| r.as_array().unwrap().iter().map(|x| x.as_f64().unwrap()).collect::<Vec<_>>().try_into().unwrap()).collect();
    rows.try_into().unwrap()
}

#[test]
fn positions_match_python() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../testdata/overlay/math.json");
    let data: Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    let mut worst = 0.0f64;
    let mut compare = |got: &Mat34, expected: &Mat34| {
        for i in 0..3 {
            for j in 0..4 {
                worst = worst.max((got[i][j] - expected[i][j]).abs());
            }
        }
    };
    for (name, base) in data["bases"].as_object().unwrap() {
        compare(&Tracker::from_name(name).base(), &mat(base));
    }
    for c in data["cases"].as_array().unwrap() {
        let p: Vec<f64> = c["position"].as_array().unwrap().iter().map(|x| x.as_f64().unwrap()).collect();
        compare(&position_transform(Tracker::from_name(c["tracker"].as_str().unwrap()), p.try_into().unwrap()), &mat(&c["matrix"]));
    }
    // numpy's dot can sum in another order; what SteamVR gets is f32
    eprintln!("largest difference {worst:e}");
    assert!(worst < 1e-12, "{worst}");
}
