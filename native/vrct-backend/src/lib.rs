//! VRCT backend (docs/rust_backend_design_2026-10-11.md). The modules are filled in phase by phase.
pub mod asr;
pub mod hf_cache;
pub mod net;
pub mod obs;
pub mod openai;
pub mod pyfmt;
pub mod translate;
pub mod telemetry;
pub mod translit;
pub mod update;
pub mod websocket;
pub mod weights;

/// A number in [0, 1) for retry jitter (no RNG crate for this)
pub(crate) fn rand_unit() -> f64 {
    let nanos = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.subsec_nanos()).unwrap_or(0);
    (nanos % 1000) as f64 / 1000.0
}
