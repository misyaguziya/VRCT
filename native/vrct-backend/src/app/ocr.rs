//! The VRChat chat-bubble OCR (controller.py / model.py): on / off and its settings, which a
//! running capture takes at once.
use super::basic::validated;
use super::App;
use crate::ipc::Reply;
use crate::pyfmt;
use crate::pyjson::py_str;
use anyhow::Result;
use serde_json::{json, Value};

type Data = Option<Value>;

/// updateOCRCaptureSettings: the running capture takes the settings (nothing when stopped)
fn apply_settings(_app: &App) {
    // P4-3c
}

fn setting(app: &App, name: &str, value: Value) -> Result<Reply> {
    let reply = validated(app, name, value)?;
    if reply.status == 200 {
        apply_settings(app);
    }
    Ok(reply)
}

pub fn set_ocr_source_language(app: &App, data: Data) -> Result<Reply> {
    setting(app, "OCR_SOURCE_LANGUAGE", json!(py_str(&data.unwrap_or(Value::Null))))
}

pub fn set_ocr_window_title(app: &App, data: Data) -> Result<Reply> {
    setting(app, "OCR_WINDOW_TITLE", json!(pyfmt::strip(&py_str(&data.unwrap_or(Value::Null)))))
}

pub fn set_ocr_poll_interval_ms(app: &App, data: Data) -> Result<Reply> {
    setting(app, "OCR_POLL_INTERVAL_MS", data.unwrap_or(Value::Null))
}

pub fn set_ocr_min_confidence(app: &App, data: Data) -> Result<Reply> {
    setting(app, "OCR_MIN_CONFIDENCE", data.unwrap_or(Value::Null))
}

pub fn set_ocr_bubble_min_text_length(app: &App, data: Data) -> Result<Reply> {
    setting(app, "OCR_BUBBLE_MIN_TEXT_LENGTH", data.unwrap_or(Value::Null))
}
