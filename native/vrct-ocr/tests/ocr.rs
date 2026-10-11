//! Bubble detection + RapidOCR against the Python backend (native/reference/export_ocr.py): the
//! boxes and every line (text, confidence, left / right / top) must be identical.
//!
//! VRCT_RAPIDOCR_MODELS: rapidocr's models folder (the venv's site-packages/rapidocr/models); the
//! test is skipped (and says so) without it. VRCT_OCR_DATASET_REF: the JSON export_ocr.py writes for
//! the real screenshots (tmp/ocr-dataset-cpu.json), compared too when set.
use serde_json::Value;
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use vrct_ocr::cv::Img;
use vrct_ocr::detector::BubbleDetector;
use vrct_ocr::engine::{readtext_bgr, reader, resolve_model_spec};
use vrct_ocr::rapidocr::RapidOcr;

fn native() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("..")
}

fn read_bgr(path: &Path) -> Img {
    let rgb = image::open(path).unwrap().to_rgb8();
    let (w, h) = (rgb.width() as usize, rgb.height() as usize);
    Img { w, h, c: 3, data: rgb.pixels().flat_map(|p| [p[2], p[1], p[0]]).collect() }
}

struct Ocr {
    models: PathBuf,
    readers: HashMap<String, RapidOcr>,
}

impl Ocr {
    fn lines(&mut self, language: &str, crop: &Img) -> Value {
        let models = &self.models;
        let r = self
            .readers
            .entry(language.to_string())
            .or_insert_with(|| reader(models, resolve_model_spec(language).unwrap()).unwrap());
        serde_json::to_value(readtext_bgr(r, crop, 0.0).unwrap()).unwrap()
    }
}

fn check(data: &Value, image_dir: Option<&Path>, ocr: &mut Ocr, detector: &mut BubbleDetector) -> Vec<String> {
    let path = |name: &str| match image_dir {
        Some(dir) => dir.join(format!("{name}.png")),
        None => PathBuf::from(name),
    };
    let mut problems = vec![];
    for case in data["frames"].as_array().unwrap() {
        let name = case["image"].as_str().unwrap();
        let found = detector.detect(&read_bgr(&path(name))).unwrap();
        let boxes: Vec<Value> = found.iter().map(|(b, _)| serde_json::json!(b)).collect();
        if boxes != case["boxes"].as_array().unwrap().as_slice() {
            problems.push(format!("{name}: boxes {boxes:?} != {}", case["boxes"]));
            continue;
        }
        for (i, (_, crop)) in found.iter().enumerate() {
            let got = ocr.lines("auto", crop);
            if got != case["lines"][i] {
                problems.push(format!("{name} #{i}: {got} != {}", case["lines"][i]));
            }
        }
    }
    for case in data["crops"].as_array().unwrap() {
        let name = case["image"].as_str().unwrap();
        let crop = read_bgr(&path(name));
        for (language, key) in [(case["language"].as_str().unwrap(), "lines"), ("auto", "auto_lines")] {
            let got = ocr.lines(language, &crop);
            if got != case[key] {
                problems.push(format!("{name} {language}: {got} != {}", case[key]));
            }
        }
    }
    problems
}

#[test]
fn ocr_matches_python() {
    let Some(models) = std::env::var_os("VRCT_RAPIDOCR_MODELS").map(PathBuf::from) else {
        eprintln!("SKIPPED: VRCT_RAPIDOCR_MODELS is not set");
        return;
    };
    let mut detector =
        BubbleDetector::new(&native().join("../src-python/models/ocr/onnx/chatbox_yolox_tiny.onnx")).unwrap();
    let mut ocr = Ocr { models, readers: HashMap::new() };
    let testdata = native().join("testdata/ocr");
    let data: Value = serde_json::from_slice(&std::fs::read(testdata.join("ocr-cpu.json")).unwrap()).unwrap();
    let mut problems = check(&data, Some(&testdata.join("images")), &mut ocr, &mut detector);
    eprintln!("synthetic: {} frames, {} crops, problems {}", data["frames"].as_array().unwrap().len(),
              data["crops"].as_array().unwrap().len(), problems.len());
    if let Some(reference) = std::env::var_os("VRCT_OCR_DATASET_REF") {
        let data: Value = serde_json::from_slice(&std::fs::read(reference).unwrap()).unwrap();
        let p = check(&data, None, &mut ocr, &mut detector);
        let bubbles: usize = data["frames"].as_array().unwrap().iter().map(|f| f["boxes"].as_array().unwrap().len()).sum();
        eprintln!("dataset: {} frames, {bubbles} bubbles, problems {}", data["frames"].as_array().unwrap().len(), p.len());
        problems.extend(p);
    }
    for p in problems.iter().take(20) {
        eprintln!("{p}");
    }
    assert!(problems.is_empty(), "{} problems", problems.len());
}
