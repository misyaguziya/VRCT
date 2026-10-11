//! ocr_languages.py (which models a VRCT language needs) and ocr_engine_rapidocr.py (the reader
//! and readtext_bgr's filtering).
use crate::R;
use crate::cv::Img;
use crate::rapidocr::{Params, RapidOcr, Stages, py_isspace};
use std::path::Path;

/// OcrModelSpec: (ocr_version, model_type, lang_rec)
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct ModelSpec {
    pub ocr_version: &'static str,
    pub model_type: &'static str,
    pub lang_rec: Option<&'static str>,
}

const MULTILINGUAL: ModelSpec = ModelSpec { ocr_version: "PP-OCRv6", model_type: "small", lang_rec: None };

const fn v5(lang: &'static str) -> ModelSpec {
    ModelSpec { ocr_version: "PP-OCRv5", model_type: "mobile", lang_rec: Some(lang) }
}

/// The languages PP-OCRv6 small reads with its one model (accepted as settings, same as "auto")
const COVERED_BY_MULTILINGUAL: [&str; 14] = [
    "Japanese", "English", "Chinese Simplified", "Chinese Traditional", "French", "German", "Spanish", "Italian",
    "Portuguese", "Dutch", "Polish", "Turkish", "Vietnamese", "Indonesian",
];

/// resolveModelSpec: None for unsupported or empty settings.
pub fn resolve_model_spec(language: &str) -> Option<ModelSpec> {
    match language {
        "auto" => Some(MULTILINGUAL),
        "Korean" => Some(v5("korean")),
        "Russian" | "Ukrainian" => Some(v5("cyrillic")),
        "Thai" => Some(v5("th")),
        "Arabic" => Some(v5("arabic")),
        "Hindi" => Some(v5("devanagari")),
        l if COVERED_BY_MULTILINGUAL.contains(&l) => Some(MULTILINGUAL),
        _ => None,
    }
}

/// The files RapidOCR 3.9.2 picks for a spec (det / cls / rec in its models folder).
fn model_files(spec: ModelSpec) -> (String, &'static str, String) {
    let cls = "ch_ppocr_mobile_v2.0_cls_mobile.onnx";
    match spec.lang_rec {
        None => (format!("{}_det_{}.onnx", spec.ocr_version, spec.model_type), cls,
                 format!("{}_rec_{}.onnx", spec.ocr_version, spec.model_type)),
        Some(lang) => (format!("ch_{}_det_{}.onnx", spec.ocr_version, spec.model_type), cls,
                       format!("{lang}_{}_rec_{}.onnx", spec.ocr_version, spec.model_type)),
    }
}

/// getReader(spec): RapidOCR with Det.limit_side_len 320 and the right-to-left reordering of its
/// rec for Arabic.
pub fn reader(models_dir: &Path, spec: ModelSpec) -> R<RapidOcr> {
    let (det, cls, rec) = model_files(spec);
    let open = |name: &str| crate::cpu_session(&models_dir.join(name));
    let params = Params { rtl: spec.lang_rec == Some("arabic"), ..Params::default() };
    RapidOcr::new(open(&det)?, open(cls)?, open(&rec)?, params)
}

/// One line readtext_bgr returns.
#[derive(Clone, Debug, PartialEq, serde::Serialize)]
pub struct Line {
    pub text: String,
    pub confidence: f64,
    pub left: f64,
    pub right: f64,
    pub top: f64,
}

/// readtext_bgr(reader, crop, min_confidence): stripped, non-empty lines at or above the confidence,
/// with their horizontal extent and top.
pub fn readtext_bgr(reader: &mut RapidOcr, crop: &Img, min_confidence: f64) -> R<Vec<Line>> {
    if crop.data.is_empty() {
        return Ok(vec![]);
    }
    let result = reader.run(crop, &mut Stages::default())?;
    let mut out = vec![];
    for (i, text) in result.txts.iter().enumerate() {
        let text = text.trim_matches(py_isspace);
        if text.is_empty() {
            continue;
        }
        let confidence = result.scores.get(i).copied().unwrap_or(0.0);
        if confidence < min_confidence {
            continue;
        }
        let points = result.boxes[i];
        let xs = points.map(|p| p[0] as f64);
        let ys = points.map(|p| p[1] as f64);
        out.push(Line {
            text: text.to_string(),
            confidence,
            left: xs.iter().cloned().fold(f64::INFINITY, f64::min),
            right: xs.iter().cloned().fold(f64::NEG_INFINITY, f64::max),
            top: ys.iter().cloned().fold(f64::INFINITY, f64::min),
        });
    }
    Ok(out)
}
