//! The VR overlays (controller.py / model.py's Overlay): the small and large logs and the VR UI.
use super::App;
use anyhow::Result;
use serde_json::Value;

/// syncOverlayRunning: the overlay runs while a log or the VR panel is on
pub fn sync_overlay_running(_app: &App) -> Result<()> {
    // P4-3d
    Ok(())
}

/// shutdownOverlay
pub fn shutdown(_app: &App) {
    // P4-3d
}

/// _is_overlay_available: the overlay runs (SteamVR is up)
pub fn is_available(_app: &App) -> bool {
    // P4-3d
    false
}

/// createOverlayImageSmallLog + updateOverlaySmallLog (`message` None: the translations only)
#[allow(clippy::too_many_arguments)]
pub fn small_log(_app: &App, _message: Option<&str>, _language: Option<&str>, _translation: &[String], _your_languages: &Value,
                 _translit_message: &Value, _translit_translation: &Value) -> Result<()> {
    // P4-3d
    Ok(())
}

/// createOverlayImageLargeLog + updateOverlayLargeLog
#[allow(clippy::too_many_arguments)]
pub fn large_log(_app: &App, _direction: &str, _message: Option<&str>, _own_language: Option<&str>, _translation: &[String],
                 _languages: &Value, _translit_message: &Value, _translit_translation: &Value) -> Result<()> {
    // P4-3d
    Ok(())
}
