//! The handlers that only read and write settings (controller.py): on / off switches, numbers
//! checked as Python's int() / float() and a range, values checked by the settings themselves.
use super::{current, App};
use crate::errors;
use crate::ipc::{self, Reply};
use crate::pyjson::{py_float, py_int, py_str};
use anyhow::{anyhow, Result};
use serde_json::{json, Value};
use std::sync::atomic::Ordering;

type Data = Option<Value>;

fn data_or_null(data: Data) -> Value {
    data.unwrap_or(Value::Null)
}

/// `if config.X is False: config.X = True` and back
macro_rules! switches {
    ($($enable:ident, $disable:ident => $name:literal;)*) => {$(
        pub fn $enable(app: &App, _: Data) -> Result<Reply> {
            if app.config.get($name) == json!(false) {
                app.config.set($name, json!(true))?;
            }
            current(app, $name)
        }
        pub fn $disable(app: &App, _: Data) -> Result<Reply> {
            if app.config.get($name) == json!(true) {
                app.config.set($name, json!(false))?;
            }
            current(app, $name)
        }
    )*};
}

switches! {
    set_enable_foreground, set_disable_foreground => "ENABLE_FOREGROUND";
    set_enable_main_window_sidebar_compact_mode, set_disable_main_window_sidebar_compact_mode => "MAIN_WINDOW_SIDEBAR_COMPACT_MODE";
    set_enable_show_resend_button, set_disable_show_resend_button => "SHOW_RESEND_BUTTON";
    set_enable_mic_automatic_threshold, set_disable_mic_automatic_threshold => "MIC_AUTOMATIC_THRESHOLD";
    set_enable_speaker_automatic_threshold, set_disable_speaker_automatic_threshold => "SPEAKER_AUTOMATIC_THRESHOLD";
    // VAD: the recorder is chosen when recording starts, so it applies from the next start (the
    // settings page stops transcription while open)
    set_enable_mic_vad_filter, set_disable_mic_vad_filter => "MIC_ENABLE_VAD";
    set_enable_speaker_vad_filter, set_disable_speaker_vad_filter => "SPEAKER_ENABLE_VAD";
    set_enable_notification_vrc_sfx, set_disable_notification_vrc_sfx => "NOTIFICATION_VRC_SFX";
    set_enable_auto_clear_message_box, set_disable_auto_clear_message_box => "AUTO_CLEAR_MESSAGE_BOX";
    set_enable_send_only_translated_messages, set_disable_send_only_translated_messages => "SEND_ONLY_TRANSLATED_MESSAGES";
    set_enable_overlay_show_only_translated_messages, set_disable_overlay_show_only_translated_messages => "OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES";
    set_enable_send_message_to_vrc, set_disable_send_message_to_vrc => "SEND_MESSAGE_TO_VRC";
    set_enable_send_received_message_to_vrc, set_disable_send_received_message_to_vrc => "SEND_RECEIVED_MESSAGE_TO_VRC";
}

pub fn set_disable_translation(app: &App, _: Data) -> Result<Reply> {
    if app.config.get_bool("ENABLE_TRANSLATION") {
        app.config.set("ENABLE_TRANSLATION", json!(false))?;
    }
    current(app, "ENABLE_TRANSLATION")
}

/// int(data), else GENERAL_EXCEPTION with the current value and `message`
fn int_setting(app: &App, data: Data, name: &str, message: &str) -> Result<Reply> {
    match data.as_ref().and_then(py_int) {
        None => Ok(errors::error_response("GENERAL_EXCEPTION", app.config.get(name), None, Some(message.into()))),
        Some(v) => {
            app.config.set(name, json!(v))?;
            current(app, name)
        }
    }
}

/// float(data), else GENERAL_EXCEPTION with the current value and `message`
fn float_setting(app: &App, data: Data, name: &str, message: &str) -> Result<Reply> {
    match data.as_ref().and_then(py_float) {
        None => Ok(errors::error_response("GENERAL_EXCEPTION", app.config.get(name), None, Some(message.into()))),
        Some(v) => {
            app.config.set(name, json!(v))?;
            current(app, name)
        }
    }
}

pub fn set_transparency(app: &App, data: Data) -> Result<Reply> {
    int_setting(app, data, "TRANSPARENCY", "Transparency must be a number")
}

pub fn set_ui_scaling(app: &App, data: Data) -> Result<Reply> {
    int_setting(app, data, "UI_SCALING", "UI scaling must be a number")
}

pub fn set_textbox_ui_scaling(app: &App, data: Data) -> Result<Reply> {
    int_setting(app, data, "TEXTBOX_UI_SCALING", "Textbox UI scaling must be a number")
}

pub fn set_mic_avg_logprob(app: &App, data: Data) -> Result<Reply> {
    float_setting(app, data, "MIC_AVG_LOGPROB", "Mic average logprob must be a number")
}

pub fn set_mic_no_speech_prob(app: &App, data: Data) -> Result<Reply> {
    float_setting(app, data, "MIC_NO_SPEECH_PROB", "Mic no-speech probability must be a number")
}

pub fn set_speaker_avg_logprob(app: &App, data: Data) -> Result<Reply> {
    float_setting(app, data, "SPEAKER_AVG_LOGPROB", "Speaker average logprob must be a number")
}

pub fn set_speaker_no_speech_prob(app: &App, data: Data) -> Result<Reply> {
    float_setting(app, data, "SPEAKER_NO_SPEECH_PROB", "Speaker no-speech probability must be a number")
}

/// int(data) within `ok`, else `code` with the current value (the setting's own rejection too)
fn ranged(app: &App, data: Data, name: &str, code: &str, ok: impl Fn(i64) -> bool) -> Result<Reply> {
    match data.as_ref().and_then(py_int).filter(|v| ok(*v)) {
        Some(v) if app.config.set(name, json!(v)).is_ok() => current(app, name),
        _ => Ok(errors::error(code, app.config.get(name))),
    }
}

fn int_of(app: &App, name: &str) -> i64 {
    app.config.get(name).as_i64().unwrap_or(0)
}

pub fn set_mic_threshold(app: &App, data: Data) -> Result<Reply> {
    let max = int_of(app, "MAX_MIC_THRESHOLD");
    ranged(app, data, "MIC_THRESHOLD", "VALIDATION_MIC_THRESHOLD", |v| (0..=max).contains(&v))
}

pub fn set_mic_record_timeout(app: &App, data: Data) -> Result<Reply> {
    ipc::print_log("Set Mic Record Timeout", data.as_ref().unwrap_or(&Value::Null));
    let phrase = int_of(app, "MIC_PHRASE_TIMEOUT");
    ranged(app, data, "MIC_RECORD_TIMEOUT", "VALIDATION_MIC_RECORD_TIMEOUT", |v| (0..=phrase).contains(&v))
}

pub fn set_mic_phrase_timeout(app: &App, data: Data) -> Result<Reply> {
    let record = int_of(app, "MIC_RECORD_TIMEOUT");
    ranged(app, data, "MIC_PHRASE_TIMEOUT", "VALIDATION_MIC_PHRASE_TIMEOUT", |v| v >= record)
}

pub fn set_mic_max_phrases(app: &App, data: Data) -> Result<Reply> {
    ranged(app, data, "MIC_MAX_PHRASES", "VALIDATION_MIC_MAX_PHRASES", |v| v >= 0)
}

pub fn set_speaker_threshold(app: &App, data: Data) -> Result<Reply> {
    ipc::print_log("Set Speaker Energy Threshold", data.as_ref().unwrap_or(&Value::Null));
    let max = int_of(app, "MAX_SPEAKER_THRESHOLD");
    ranged(app, data, "SPEAKER_THRESHOLD", "VALIDATION_SPEAKER_THRESHOLD", |v| (0..=max).contains(&v))
}

pub fn set_speaker_record_timeout(app: &App, data: Data) -> Result<Reply> {
    let phrase = int_of(app, "SPEAKER_PHRASE_TIMEOUT");
    ranged(app, data, "SPEAKER_RECORD_TIMEOUT", "VALIDATION_SPEAKER_RECORD_TIMEOUT", |v| (0..=phrase).contains(&v))
}

pub fn set_speaker_phrase_timeout(app: &App, data: Data) -> Result<Reply> {
    let record = int_of(app, "SPEAKER_RECORD_TIMEOUT");
    ranged(app, data, "SPEAKER_PHRASE_TIMEOUT", "VALIDATION_SPEAKER_PHRASE_TIMEOUT", |v| v >= 0 && v >= record)
}

pub fn set_speaker_max_phrases(app: &App, data: Data) -> Result<Reply> {
    ipc::print_log("Set Speaker Max Phrases", data.as_ref().unwrap_or(&Value::Null));
    ranged(app, data, "SPEAKER_MAX_PHRASES", "VALIDATION_SPEAKER_MAX_PHRASES", |v| v >= 0)
}

/// _configValidationErrorResponse(VALIDATION_CONFIG_VALUE_INVALID): a rejected value answers that
/// error with the value
pub fn validated(app: &App, name: &str, value: Value) -> Result<Reply> {
    match app.config.set(name, value) {
        Ok(()) => current(app, name),
        Err(rejected) => Ok(errors::error("VALIDATION_CONFIG_VALUE_INVALID", rejected.value)),
    }
}

/// dict(data): a dict as it is; anything else fails (500), as dict() raises
fn dict_of(data: Data) -> Result<Value> {
    match data {
        Some(v @ Value::Object(_)) => Ok(v),
        other => Err(anyhow!("dict() of {}", py_str(&data_or_null(other)))),
    }
}

pub fn set_message_box_ratio(app: &App, data: Data) -> Result<Reply> {
    validated(app, "MESSAGE_BOX_RATIO", data_or_null(data))
}

pub fn set_send_message_button_type(app: &App, data: Data) -> Result<Reply> {
    validated(app, "SEND_MESSAGE_BUTTON_TYPE", data_or_null(data))
}

pub fn set_font_family(app: &App, data: Data) -> Result<Reply> {
    validated(app, "FONT_FAMILY", data_or_null(data))
}

pub fn set_ui_language(app: &App, data: Data) -> Result<Reply> {
    validated(app, "UI_LANGUAGE", data_or_null(data))
}

pub fn set_main_window_geometry(app: &App, data: Data) -> Result<Reply> {
    validated(app, "MAIN_WINDOW_GEOMETRY", data_or_null(data))
}

pub fn set_hotkeys(app: &App, data: Data) -> Result<Reply> {
    validated(app, "HOTKEYS", data_or_null(data))
}

pub fn set_selected_release_channel(app: &App, data: Data) -> Result<Reply> {
    validated(app, "SELECTED_RELEASE_CHANNEL", json!(py_str(&data_or_null(data))))
}

pub fn set_whisper_weight_type(app: &App, data: Data) -> Result<Reply> {
    validated(app, "WHISPER_WEIGHT_TYPE", json!(py_str(&data_or_null(data))))
}

pub fn set_selected_transcription_compute_type(app: &App, data: Data) -> Result<Reply> {
    validated(app, "SELECTED_TRANSCRIPTION_COMPUTE_TYPE", json!(py_str(&data_or_null(data))))
}

pub fn set_send_message_format_parts(app: &App, data: Data) -> Result<Reply> {
    validated(app, "SEND_MESSAGE_FORMAT_PARTS", dict_of(data)?)
}

pub fn set_received_message_format_parts(app: &App, data: Data) -> Result<Reply> {
    validated(app, "RECEIVED_MESSAGE_FORMAT_PARTS", dict_of(data)?)
}

/// The settings that make the CTranslate2 model load again on the next use
fn translator_setting(app: &App, name: &str, data: Data) -> Result<Reply> {
    app.config.set(name, json!(py_str(&data_or_null(data))))?;
    app.model.translator_changed.store(true, Ordering::SeqCst);
    current(app, name)
}

pub fn set_ctranslate2_weight_type(app: &App, data: Data) -> Result<Reply> {
    translator_setting(app, "CTRANSLATE2_WEIGHT_TYPE", data)
}

pub fn set_selected_translation_compute_type(app: &App, data: Data) -> Result<Reply> {
    translator_setting(app, "SELECTED_TRANSLATION_COMPUTE_TYPE", data)
}

/// The compute device; its type back to "auto" (told to the UI)
fn compute_device(app: &App, device: &str, kind: &str, data: Data) -> Result<Reply> {
    let device_name = format!("SELECTED_{kind}_COMPUTE_DEVICE");
    let type_name = format!("SELECTED_{kind}_COMPUTE_TYPE");
    ipc::print_log(device, data.as_ref().unwrap_or(&Value::Null));
    app.config.set(&device_name, data_or_null(data))?;
    app.config.set(&type_name, json!("auto"))?;
    app.run(200, &format!("selected_{}_compute_type", kind.to_lowercase()), app.config.get(&type_name))?;
    current(app, &device_name)
}

pub fn set_selected_translation_compute_device(app: &App, data: Data) -> Result<Reply> {
    let reply = compute_device(app, "setSelectedTranslationComputeDevice", "TRANSLATION", data)?;
    app.model.translator_changed.store(true, Ordering::SeqCst);
    Ok(reply)
}

pub fn set_selected_transcription_compute_device(app: &App, data: Data) -> Result<Reply> {
    compute_device(app, "setSelectedTranscriptionComputeDevice", "TRANSCRIPTION", data)
}

pub fn get_selectable_whisper_weight_type_dict(app: &App, _: Data) -> Result<Reply> {
    current(app, "SELECTABLE_WHISPER_WEIGHT_TYPE_DICT")
}

/// The transcription engines that are available
pub fn get_transcription_engines(app: &App, _: Data) -> Result<Reply> {
    let status = app.config.get("SELECTABLE_TRANSCRIPTION_ENGINE_STATUS");
    let engines: Vec<&String> = status.as_object().map(|m| m.iter().filter(|(_, v)| **v == json!(true)).map(|(k, _)| k).collect())
        .unwrap_or_default();
    Ok(Reply::ok(json!(engines)))
}

/// config.AUTH_KEYS[key] / TRANSCRIPTION_AUTH_KEYS[key]
fn key_of(app: &App, setting: &str, key: &str) -> Result<Reply> {
    Ok(Reply::ok(app.config.get(setting).get(key).cloned().ok_or_else(|| anyhow!("KeyError: {key:?}"))?))
}

macro_rules! keys {
    ($($name:ident => $setting:literal, $key:literal;)*) => {$(
        pub fn $name(app: &App, _: Data) -> Result<Reply> {
            key_of(app, $setting, $key)
        }
    )*};
}

keys! {
    get_deep_l_auth_key => "AUTH_KEYS", "DeepL_API";
    get_plamo_auth_key => "AUTH_KEYS", "Plamo_API";
    get_gemini_auth_key => "AUTH_KEYS", "Gemini_API";
    get_open_ai_auth_key => "AUTH_KEYS", "OpenAI_API";
    get_groq_auth_key => "AUTH_KEYS", "Groq_API";
    get_open_router_auth_key => "AUTH_KEYS", "OpenRouter_API";
    get_open_ai_compatible_auth_key => "AUTH_KEYS", "OpenAI_Compatible";
    get_groq_whisper_auth_key => "TRANSCRIPTION_AUTH_KEYS", "Groq_Whisper";
    get_open_ai_whisper_auth_key => "TRANSCRIPTION_AUTH_KEYS", "OpenAI_Whisper";
    get_custom_whisper_auth_key => "TRANSCRIPTION_AUTH_KEYS", "Custom_Whisper";
    get_deepgram_auth_key => "TRANSCRIPTION_AUTH_KEYS", "Deepgram";
}

macro_rules! settings {
    ($($name:ident => $setting:literal;)*) => {$(
        pub fn $name(app: &App, _: Data) -> Result<Reply> {
            current(app, $setting)
        }
    )*};
}

// the registry engines' model getters (_getTranslationEngineModelList / _getTranslationEngineModel)
settings! {
    get_plamo_model_list => "SELECTABLE_PLAMO_MODEL_LIST";
    get_plamo_model => "SELECTED_PLAMO_MODEL";
    get_gemini_model_list => "SELECTABLE_GEMINI_MODEL_LIST";
    get_gemini_model => "SELECTED_GEMINI_MODEL";
    get_open_ai_model_list => "SELECTABLE_OPENAI_MODEL_LIST";
    get_open_ai_model => "SELECTED_OPENAI_MODEL";
    get_groq_model_list => "SELECTABLE_GROQ_MODEL_LIST";
    get_groq_model => "SELECTED_GROQ_MODEL";
    get_open_router_model_list => "SELECTABLE_OPENROUTER_MODEL_LIST";
    get_open_router_model => "SELECTED_OPENROUTER_MODEL";
    get_translator_lm_studio_model => "SELECTED_LMSTUDIO_MODEL";
    get_translator_ollama_model => "SELECTED_OLLAMA_MODEL";
}
