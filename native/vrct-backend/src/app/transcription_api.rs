//! The transcription APIs (controller.py: Groq / OpenAI Whisper, a custom server, Deepgram): a key
//! is kept only when it lists models (Groq / OpenAI filtered to transcription models); a failed key
//! is cleared with its model list. No client is kept: each recording session builds its provider.
use super::engines::{fallback_unsupported_languages_for_transcription_engine, update_transcription_engine};
use super::translation_api::exception;
use super::{current, App};
use crate::asr;
use crate::errors;
use crate::ipc::{self, Reply};
use crate::logs;
use crate::pyjson::py_str;
use anyhow::Result;
use serde_json::{json, Map, Value};

type Data = Option<Value>;

const GROQ_WHISPER_BASE_URL: &str = "https://api.groq.com/openai/v1";
const OPENAI_WHISPER_BASE_URL: &str = "https://api.openai.com/v1";

#[derive(Clone, Copy, PartialEq)]
enum Api {
    Groq,
    OpenAi,
    Custom,
    Deepgram,
}

impl Api {
    fn key(self) -> &'static str {
        match self {
            Api::Groq => "Groq_Whisper",
            Api::OpenAi => "OpenAI_Whisper",
            Api::Custom => "Custom_Whisper",
            Api::Deepgram => "Deepgram",
        }
    }

    fn display(self) -> &'static str {
        match self {
            Api::Groq => "Groq Whisper",
            Api::OpenAi => "OpenAI Whisper",
            Api::Custom => "Custom Whisper",
            Api::Deepgram => "Deepgram",
        }
    }

    /// The X of SELECTABLE_X_MODEL_LIST / SELECTED_X_MODEL
    fn x(self) -> &'static str {
        match self {
            Api::Groq => "GROQ_WHISPER",
            Api::OpenAi => "OPENAI_WHISPER",
            Api::Custom => "CUSTOM_WHISPER",
            Api::Deepgram => "DEEPGRAM",
        }
    }
}

fn list_name(api: Api) -> String {
    format!("SELECTABLE_{}_MODEL_LIST", api.x())
}

fn selected_name(api: Api) -> String {
    format!("SELECTED_{}_MODEL", api.x())
}

fn push_list(app: &App, api: Api) -> Result<()> {
    app.run(200, &format!("selectable_{}_model_list", api.x().to_lowercase()), app.config.get(&list_name(api)))
}

fn push_selected(app: &App, api: Api) -> Result<()> {
    app.run(200, &format!("selected_{}_model", api.x().to_lowercase()), app.config.get(&selected_name(api)))
}

fn set_key(app: &App, api: Api, value: Value) -> Result<()> {
    let mut keys = app.config.get("TRANSCRIPTION_AUTH_KEYS");
    keys[api.key()] = value;
    app.config.set("TRANSCRIPTION_AUTH_KEYS", keys)?;
    Ok(())
}

fn key(app: &App, api: Api) -> Value {
    app.config.get("TRANSCRIPTION_AUTH_KEYS").get(api.key()).cloned().unwrap_or(Value::Null)
}

fn status(app: &App, api: Api, available: bool) {
    app.config.put_item("SELECTABLE_TRANSCRIPTION_ENGINE_STATUS", api.key(), json!(available));
}

/// The key checked at `base_url` (Deepgram: its own API) and its models (name, languages)
fn models(app: &App, api: Api, api_key: &str, base_url: &str) -> Result<Option<Vec<(String, Vec<String>)>>> {
    let http = &app.model.http;
    if api == Api::Deepgram {
        if !asr::check_deepgram_key(http, api_key) {
            return Ok(None);
        }
        return Ok(Some(asr::deepgram_models(http, api_key)));
    }
    if !asr::check_whisper_api_key(http, api_key, base_url) {
        return Ok(None);
    }
    // a custom server's model names are unknown: not filtered
    let keywords = (api != Api::Custom).then_some(&asr::TRANSCRIPTION_MODEL_KEYWORDS[..]);
    Ok(Some(asr::whisper_api_models(http, api_key, base_url, keywords)?.into_iter().map(|m| (m, vec![])).collect()))
}

fn base_url(app: &App, api: Api) -> String {
    match api {
        Api::Groq => GROQ_WHISPER_BASE_URL.into(),
        Api::OpenAi => OPENAI_WHISPER_BASE_URL.into(),
        Api::Custom => app.config.get_str("TRANSCRIPTION_CUSTOM_URL"),
        Api::Deepgram => String::new(),
    }
}

/// The models in the settings (Deepgram: with their languages), the selected one kept if listed
fn take_models(app: &App, api: Api, models: Vec<(String, Vec<String>)>) -> Result<()> {
    let names: Vec<&String> = models.iter().map(|(n, _)| n).collect();
    app.config.set(&list_name(api), json!(names))?;
    if api == Api::Deepgram {
        let languages: Map<String, Value> = models.iter().map(|(n, l)| (n.clone(), json!(l))).collect();
        app.config.set("DEEPGRAM_MODEL_LANGUAGES", Value::Object(languages))?;
    }
    push_list(app, api)?;
    let selected = app.config.get(&selected_name(api));
    if !names.iter().any(|n| json!(n) == selected) {
        app.config.set(&selected_name(api), json!(names[0]))?;
    }
    push_selected(app, api)
}

fn set_auth_key(app: &App, api: Api, data: Data) -> Result<Reply> {
    ipc::log(format!("Set {} Auth Key", api.display()));
    let data = crate::pyfmt::strip(&py_str(&data.unwrap_or(Value::Null))).to_string();
    let attempt = || -> Result<Reply> {
        if data.is_empty() {
            return Ok(errors::error("TRANSCRIPTION_API_AUTH_FAILED", Value::Null));
        }
        let Some(models) = models(app, api, &data, &base_url(app, api))?.filter(|m| !m.is_empty()) else {
            return Ok(errors::error("TRANSCRIPTION_API_AUTH_FAILED", Value::Null));
        };
        set_key(app, api, json!(data))?;
        status(app, api, true);
        take_models(app, api, models)?;
        update_transcription_engine(app, None)?;
        Ok(Reply::ok(key(app, api)))
    };
    let reply = attempt().unwrap_or_else(|e| {
        logs::error(&format!("set {} auth key", api.key()), &format!("{e:#}"));
        exception(&e, Value::Null)
    });
    if reply.status == 400 {
        del_auth_key(app, api)?;
    }
    Ok(reply)
}

fn del_auth_key(app: &App, api: Api) -> Result<Reply> {
    set_key(app, api, Value::Null)?;
    app.config.set(&list_name(api), json!([]))?;
    if api == Api::Deepgram {
        app.config.set("DEEPGRAM_MODEL_LANGUAGES", json!({}))?;
    }
    app.config.set(&selected_name(api), Value::Null)?;
    push_list(app, api)?;
    push_selected(app, api)?;
    status(app, api, false);
    update_transcription_engine(app, None)?;
    Ok(Reply::ok(key(app, api)))
}

/// A model of the saved list, else MODEL_TRANSCRIPTION_INVALID
fn set_model(app: &App, api: Api, data: Data) -> Result<Reply> {
    let data = data.unwrap_or(Value::Null);
    ipc::print_log(&format!("Set {} Model", api.display()), &data);
    let data = json!(py_str(&data));
    if !app.config.get(&list_name(api)).as_array().is_some_and(|l| l.contains(&data)) {
        return Ok(errors::error("MODEL_TRANSCRIPTION_INVALID", app.config.get(&selected_name(api))));
    }
    app.config.set(&selected_name(api), data)?;
    // Deepgram's languages differ by model: the selection and the list follow when it is in use
    if api == Api::Deepgram && app.config.get_str("SELECTED_TRANSCRIPTION_ENGINE") == "Deepgram" {
        fallback_unsupported_languages_for_transcription_engine(app, "Deepgram")?;
        app.run(200, "selectable_language_list", app.model.list_language_and_country(&app.config))?;
    }
    current(app, &selected_name(api))
}

macro_rules! apis {
    ($($api:ident: $set_key:ident, $del_key:ident, $set_model:ident;)*) => {$(
        pub fn $set_key(app: &App, data: Data) -> Result<Reply> {
            set_auth_key(app, Api::$api, data)
        }
        pub fn $del_key(app: &App, _: Data) -> Result<Reply> {
            del_auth_key(app, Api::$api)
        }
        pub fn $set_model(app: &App, data: Data) -> Result<Reply> {
            set_model(app, Api::$api, data)
        }
    )*};
}

apis! {
    Groq: set_groq_whisper_auth_key, del_groq_whisper_auth_key, set_groq_whisper_model;
    OpenAi: set_open_ai_whisper_auth_key, del_open_ai_whisper_auth_key, set_open_ai_whisper_model;
    Custom: set_custom_whisper_auth_key, del_custom_whisper_auth_key, set_custom_whisper_model;
    Deepgram: set_deepgram_auth_key, del_deepgram_auth_key, set_deepgram_model;
}

/// setCustomWhisperURL: without a key only kept; with one, kept once it lists models
pub fn set_custom_whisper_url(app: &App, data: Data) -> Result<Reply> {
    let data = data.unwrap_or(Value::Null);
    ipc::print_log("Set Custom Whisper URL", &data);
    let data = crate::pyfmt::strip(&py_str(&data)).to_string();
    let api = Api::Custom;
    let unavailable = || -> Result<Reply> {
        status(app, api, false);
        app.config.set(&list_name(api), json!([]))?;
        app.config.set(&selected_name(api), Value::Null)?;
        push_list(app, api)?;
        push_selected(app, api)?;
        update_transcription_engine(app, None)?;
        Ok(errors::error("CONNECTION_TRANSCRIPTION_CUSTOM_URL_INVALID", app.config.get("TRANSCRIPTION_CUSTOM_URL")))
    };
    let attempt = || -> Result<Reply> {
        let key = key(app, api);
        let Some(key) = key.as_str().filter(|k| !k.is_empty()) else {
            app.config.set("TRANSCRIPTION_CUSTOM_URL", json!(data))?;
            return current(app, "TRANSCRIPTION_CUSTOM_URL");
        };
        match models(app, api, key, &data)? {
            Some(models) if !models.is_empty() => {
                app.config.set("TRANSCRIPTION_CUSTOM_URL", json!(data))?;
                status(app, api, true);
                take_models(app, api, models)?;
                update_transcription_engine(app, None)?;
                current(app, "TRANSCRIPTION_CUSTOM_URL")
            }
            _ => unavailable(),
        }
    };
    Ok(attempt().unwrap_or_else(|e| {
        logs::error("set custom whisper URL", &format!("{e:#}"));
        exception(&e, app.config.get("TRANSCRIPTION_CUSTOM_URL"))
    }))
}
