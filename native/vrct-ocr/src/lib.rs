//! OCR of VRChat chat bubbles, as models/ocr does it: the YOLOX bubble detector
//! (ocr_bubble_detector.py) and RapidOCR 3.9.2 with VRCT's settings (ocr_engine_rapidocr.py,
//! ocr_languages.py). OpenCV / numpy / RapidOCR are ported so the results match bit for bit; the
//! Apache-2.0 notices are in cv.rs and rapidocr.rs (LICENSE-APACHE-2.0). Also the other ONNX model of
//! the backend, Silero VAD (silero.rs), on the same onnxruntime.
pub mod cv;
pub mod detector;
pub mod engine;
pub mod npy;
pub mod rapidocr;
pub mod silero;

use ort::session::Session;
use std::path::Path;
use std::sync::OnceLock;

pub type R<T> = Result<T, Box<dyn std::error::Error + Send + Sync>>;

/// Loads onnxruntime.dll from the executable's folder or its `_internal` (the installed layout),
/// once per process; every session shares it.
pub fn init_ort() -> R<()> {
    static INIT: OnceLock<Result<(), String>> = OnceLock::new();
    INIT.get_or_init(|| {
        let exe = std::env::current_exe().map_err(|e| e.to_string())?;
        let dir = exe.parent().ok_or("no exe dir")?;
        let dll = [dir.join("onnxruntime.dll"), dir.join("_internal").join("onnxruntime.dll")]
            .into_iter().find(|p| p.is_file()).unwrap_or_else(|| dir.join("onnxruntime.dll"));
        let builder = ort::init_from(&dll).map_err(|e| format!("{}: {e}", dll.display()))?;
        builder.with_name("vrct").commit();
        Ok(())
    })
    .clone()
    .map_err(Into::into)
}

/// ocr_languages.ocr_onnx_threads: half the cores, at most 4, so VRChat / SteamVR keep the rest.
pub fn onnx_threads() -> usize {
    (std::thread::available_parallelism().map_or(2, |n| n.get()) / 2).clamp(1, 4)
}

/// A CPU session as VRCT opens them (intra = onnx_threads(), inter = 1).
pub fn cpu_session(path: &Path) -> R<Session> {
    init_ort()?;
    fn open(path: &Path) -> ort::Result<Session> {
        Session::builder()?.with_intra_threads(onnx_threads())?.with_inter_threads(1)?.commit_from_file(path)
    }
    Ok(open(path)?)
}
