//! VRCT backend (docs/rust_backend_design_2026-10-11.md). The modules are filled in phase by phase.
pub mod app;
pub mod asr;
pub mod clipboard;
pub mod compute;
pub mod config;
pub mod devices;
pub mod errors;
pub mod hf_cache;
pub mod ipc;
pub mod keywords;
pub mod logs;
pub mod net;
pub mod obs;
pub mod ocr_capture;
pub mod openai;
pub mod osc;
pub mod platform;
pub mod recorder;
pub mod pyfmt;
pub mod pyjson;
pub mod translate;
pub mod telemetry;
pub mod transcriber;
pub mod translit;
pub mod update;
pub mod websocket;
pub mod weights;

/// A number in [0, 1) for retry jitter (no RNG crate for this)
pub(crate) fn rand_unit() -> f64 {
    let nanos = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.subsec_nanos()).unwrap_or(0);
    (nanos % 1000) as f64 / 1000.0
}
