//! VR UI image path on the GPU (docs/rust_backend_migration_plan_2026-10-07.md, stage 2):
//! capture a window into a Rust-owned D3D11 texture, compose it with the overlay mask,
//! and hand the texture pointer to Python, which submits it to SteamVR.
//! OpenVR stays in Python; this module never initializes or shuts it down.
//! Without the `python` feature only `capture` (the Rust overlay uses it).
pub mod capture;
#[cfg(feature = "python")]
mod python;
