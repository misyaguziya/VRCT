//! The VRChat chat-bubble OCR (controller.py / model.py): on / off and its settings, which a
//! running capture takes at once.
use super::basic::validated;
use super::{current, pipeline, App};
use crate::ipc::{self, Reply};
use crate::logs;
use crate::ocr_pipeline::{self, OcrPipeline, Settings};
use crate::pyfmt;
use crate::pyjson::py_str;
use anyhow::Result;
use serde_json::{json, Value};
use std::sync::Arc;

type Data = Option<Value>;

fn settings(app: &App) -> Settings {
    let c = &app.config;
    Settings {
        source_language: c.get_str("OCR_SOURCE_LANGUAGE"),
        window_title: c.get_str("OCR_WINDOW_TITLE"),
        poll_interval_ms: c.get("OCR_POLL_INTERVAL_MS").as_i64().unwrap_or(750),
        min_confidence: c.get("OCR_MIN_CONFIDENCE").as_f64().unwrap_or(0.85),
        min_text_length: c.get("OCR_BUBBLE_MIN_TEXT_LENGTH").as_i64().unwrap_or(2),
    }
}

/// updateOCRCaptureSettings: the running capture takes the settings (nothing when stopped)
fn apply_settings(app: &App) {
    if let Some(ocr) = &*app.model.ocr.lock().unwrap() {
        ocr.apply(settings(app));
    }
}

/// ocrMessage: a bubble read goes the way of a received message (not to the chatbox)
fn ocr_message(app: &App, text: String, language: Option<String>) {
    if !app.config.get_bool("ENABLE_OCR_CAPTURE") || text.is_empty() {
        return;
    }
    let mut id = [0u8; 16];
    let _ = getrandom::getrandom(&mut id);
    let id: String = id.iter().map(|b| format!("{b:02x}")).collect();
    if let Err(e) = pipeline::process(app, &pipeline::OCR, &text, language.as_deref(), Some(json!(format!("transcription-ocr-{id}"))), None) {
        logs::error("OCR message", &format!("{e:#}"));
    }
}

/// startOcrCapture: running once the models loaded; when it cannot start, the reason
/// (OCR_DISABLED_*) goes to /run/enable_ocr_capture and it stays off
fn start(app: &App) -> Result<bool> {
    let mut ocr = app.model.ocr.lock().unwrap();
    if ocr.is_some() {
        return Ok(true);
    }
    let me = app.me();
    let on_text = Box::new(move |text: String, language: Option<String>| {
        if let Some(app) = me.upgrade() {
            ocr_message(&app, text, language);
        }
    });
    match OcrPipeline::start(ocr_pipeline::models(&app.model.resources.dir), settings(app), on_text, Arc::new(|l| ipc::log(l))) {
        Ok(pipeline) => {
            *ocr = Some(pipeline);
            Ok(true)
        }
        Err(code) => {
            app.run_error("enable_ocr_capture", code, json!(false))?;
            Ok(false)
        }
    }
}

pub fn set_enable_ocr_capture(app: &App, _: Data) -> Result<Reply> {
    if app.config.get("ENABLE_OCR_CAPTURE") == json!(false) {
        let started = start(app)?;
        app.config.set("ENABLE_OCR_CAPTURE", json!(started))?;
    }
    current(app, "ENABLE_OCR_CAPTURE")
}

pub fn set_disable_ocr_capture(app: &App, _: Data) -> Result<Reply> {
    if app.config.get_bool("ENABLE_OCR_CAPTURE") {
        if let Some(ocr) = app.model.ocr.lock().unwrap().take() {
            ocr.stop();
        }
        app.config.set("ENABLE_OCR_CAPTURE", json!(false))?;
    }
    current(app, "ENABLE_OCR_CAPTURE")
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
