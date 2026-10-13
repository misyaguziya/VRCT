//! The translation engines with a key, a server or a model list (controller.py's
//! TRANSLATION_PROVIDER_REGISTRY / CONNECTION_PROVIDER_REGISTRY handlers, DeepL, OpenAI-compatible):
//! a key or server is kept only when it works; a failed key is cleared with its model list.
use super::engines::update_translation_engine_and_engine_list;
use super::{current, App};
use crate::config::Rejected;
use crate::errors;
use crate::ipc::{self, Reply};
use crate::logs;
use crate::pyjson::py_str;
use crate::translate::llm::Engine;
use anyhow::{anyhow, Result};
use serde_json::{json, Value};

type Data = Option<Value>;

/// An engine of the key + model list registry (translation_providers.py's TranslationEngineSpec)
struct KeySpec {
    engine: Engine,
    min_length: usize,
    prefix: &'static str,
    error_auth_invalid: &'static str,
    error_auth_failed: &'static str,
    error_model_invalid: &'static str,
    list: &'static str,
    selected: &'static str,
}

/// An engine reached by a server (ConnectionEngineSpec)
struct ServerSpec {
    engine: Engine,
    error_connection_failed: &'static str,
    error_model_invalid: &'static str,
    list: &'static str,
    selected: &'static str,
}

const PLAMO: KeySpec = KeySpec { engine: Engine::Plamo, min_length: 72, prefix: "", error_auth_invalid: "AUTH_PLAMO_LENGTH",
    error_auth_failed: "AUTH_PLAMO_FAILED", error_model_invalid: "MODEL_PLAMO_INVALID", list: "PLAMO", selected: "PLAMO" };
const GEMINI: KeySpec = KeySpec { engine: Engine::Gemini, min_length: 39, prefix: "", error_auth_invalid: "AUTH_GEMINI_LENGTH",
    error_auth_failed: "AUTH_GEMINI_FAILED", error_model_invalid: "MODEL_GEMINI_INVALID", list: "GEMINI", selected: "GEMINI" };
const OPENAI: KeySpec = KeySpec { engine: Engine::OpenAi, min_length: 164, prefix: "sk-", error_auth_invalid: "AUTH_OPENAI_INVALID",
    error_auth_failed: "AUTH_OPENAI_FAILED", error_model_invalid: "MODEL_OPENAI_INVALID", list: "OPENAI", selected: "OPENAI" };
const GROQ: KeySpec = KeySpec { engine: Engine::Groq, min_length: 40, prefix: "gsk", error_auth_invalid: "AUTH_GROQ_INVALID",
    error_auth_failed: "AUTH_GROQ_FAILED", error_model_invalid: "MODEL_GROQ_INVALID", list: "GROQ", selected: "GROQ" };
const OPENROUTER: KeySpec = KeySpec { engine: Engine::OpenRouter, min_length: 20, prefix: "", error_auth_invalid: "AUTH_OPENROUTER_INVALID",
    error_auth_failed: "AUTH_OPENROUTER_FAILED", error_model_invalid: "MODEL_OPENROUTER_INVALID", list: "OPENROUTER", selected: "OPENROUTER" };
const LMSTUDIO: ServerSpec = ServerSpec { engine: Engine::LmStudio, error_connection_failed: "CONNECTION_LMSTUDIO_FAILED",
    error_model_invalid: "MODEL_LMSTUDIO_INVALID", list: "LMSTUDIO", selected: "LMSTUDIO" };
const OLLAMA: ServerSpec = ServerSpec { engine: Engine::Ollama, error_connection_failed: "CONNECTION_OLLAMA_FAILED",
    error_model_invalid: "MODEL_OLLAMA_INVALID", list: "OLLAMA", selected: "OLLAMA" };

/// SELECTABLE_X_MODEL_LIST / SELECTED_X_MODEL and their pushes (selectable_x_model_list / selected_x_model)
fn list_name(x: &str) -> String {
    format!("SELECTABLE_{x}_MODEL_LIST")
}

fn selected_name(x: &str) -> String {
    format!("SELECTED_{x}_MODEL")
}

fn push_list(app: &App, x: &str) -> Result<()> {
    app.run(200, &format!("selectable_{}_model_list", x.to_lowercase()), app.config.get(&list_name(x)))
}

fn push_selected(app: &App, x: &str) -> Result<()> {
    app.run(200, &format!("selected_{}_model", x.to_lowercase()), app.config.get(&selected_name(x)))
}

fn display_name(engine: Engine) -> &'static str {
    let key = engine.key();
    key.strip_suffix("_API").unwrap_or(key)
}

/// AUTH_KEYS[key] = value (through the setting's check)
fn set_auth_key(app: &App, key: &str, value: Value) -> Result<()> {
    let mut keys = app.config.get("AUTH_KEYS");
    keys[key] = value;
    app.config.set("AUTH_KEYS", keys)?;
    Ok(())
}

fn auth_key(app: &App, key: &str) -> Value {
    app.config.get("AUTH_KEYS").get(key).cloned().unwrap_or(Value::Null)
}

fn status(app: &App, key: &str, available: bool) {
    app.config.put_item("SELECTABLE_TRANSLATION_ENGINE_STATUS", key, json!(available));
}

/// The model list in the settings; the selected model kept if in it, else the first (an empty
/// list fails: IndexError)
fn take_models(app: &App, x: &str, models: Vec<String>) -> Result<()> {
    app.config.set(&list_name(x), json!(models))?;
    push_list(app, x)?;
    let selected = app.config.get(&selected_name(x));
    if !models.iter().any(|m| json!(m) == selected) {
        let first = models.first().ok_or_else(|| anyhow!("IndexError: list index out of range"))?;
        app.config.set(&selected_name(x), json!(first))?;
    }
    Ok(())
}

/// The selected model on the engine's client (setXModel)
fn use_selected_model(app: &App, engine: Engine, x: &str) -> Result<bool> {
    let model = app.config.get_str(&selected_name(x));
    app.model.translator.write().unwrap().set_model(engine, &model)
}

/// create_exception_error_response: "Error: {e}", the exception's type
pub fn exception(error: &anyhow::Error, data: Value) -> Reply {
    let kind = if error.downcast_ref::<Rejected>().is_some() { "ConfigValidationError" } else { "Exception" };
    errors::exception_response(error, kind, data, "GENERAL_EXCEPTION")
}

// ------------------------------------------------------------------------------------- the key + model list engines

fn set_registry_auth_key(app: &App, spec: &KeySpec, data: Data) -> Result<Reply> {
    let key = spec.engine.key();
    ipc::log(format!("Set {} Auth Key", display_name(spec.engine)));
    let data = py_str(&data.unwrap_or(Value::Null));
    let attempt = || -> Result<Reply> {
        if !(data.starts_with(spec.prefix) && data.chars().count() >= spec.min_length) {
            return Ok(errors::error(spec.error_auth_invalid, Value::Null));
        }
        if !app.model.translator.write().unwrap().authenticate_llm(spec.engine, &data, None)? {
            return Ok(errors::error(spec.error_auth_failed, Value::Null));
        }
        set_auth_key(app, key, json!(data))?;
        status(app, key, true);
        let models = app.model.translator.write().unwrap().get_model_list(spec.engine)?;
        take_models(app, spec.list, models)?;
        use_selected_model(app, spec.engine, spec.selected)?;
        push_selected(app, spec.selected)?;
        update_translation_engine_and_engine_list(app)?;
        Ok(Reply::ok(auth_key(app, key)))
    };
    // the SDK's errors may hold the key: logged only, the UI gets the failure
    let reply = attempt().unwrap_or_else(|e| {
        logs::error(&format!("set {key} auth key"), &format!("{e:#}"));
        errors::error(spec.error_auth_failed, Value::Null)
    });
    if reply.status == 400 {
        del_registry_auth_key(app, spec)?;
    }
    Ok(reply)
}

fn del_registry_auth_key(app: &App, spec: &KeySpec) -> Result<Reply> {
    let key = spec.engine.key();
    set_auth_key(app, key, Value::Null)?;
    app.config.set(&list_name(spec.list), json!([]))?;
    app.config.set(&selected_name(spec.selected), Value::Null)?;
    push_list(app, spec.list)?;
    push_selected(app, spec.selected)?;
    status(app, key, false);
    update_translation_engine_and_engine_list(app)?;
    Ok(Reply::ok(auth_key(app, key)))
}

/// _setTranslationEngineModel (the registry and the server engines)
fn set_engine_model(app: &App, engine: Engine, x: &str, error_model_invalid: &str, data: Data) -> Result<Reply> {
    let data = data.unwrap_or(Value::Null);
    ipc::print_log(&format!("Set {} Model", display_name(engine)), &data);
    let data = py_str(&data);
    let attempt = || -> Result<Reply> {
        if !app.model.translator.write().unwrap().set_model(engine, &data)? {
            return Ok(errors::error(error_model_invalid, app.config.get(&selected_name(x))));
        }
        app.config.set(&selected_name(x), json!(data))?;
        use_selected_model(app, engine, x)?;
        current(app, &selected_name(x))
    };
    Ok(attempt().unwrap_or_else(|e| {
        logs::error(&format!("set {} model", engine.key()), &format!("{e:#}"));
        errors::error(error_model_invalid, app.config.get(&selected_name(x)))
    }))
}

macro_rules! registry {
    ($($spec:ident: $set_key:ident, $del_key:ident, $set_model:ident;)*) => {$(
        pub fn $set_key(app: &App, data: Data) -> Result<Reply> {
            set_registry_auth_key(app, &$spec, data)
        }
        pub fn $del_key(app: &App, _: Data) -> Result<Reply> {
            del_registry_auth_key(app, &$spec)
        }
        pub fn $set_model(app: &App, data: Data) -> Result<Reply> {
            set_engine_model(app, $spec.engine, $spec.selected, $spec.error_model_invalid, data)
        }
    )*};
}

registry! {
    PLAMO: set_plamo_auth_key, del_plamo_auth_key, set_plamo_model;
    GEMINI: set_gemini_auth_key, del_gemini_auth_key, set_gemini_model;
    OPENAI: set_open_ai_auth_key, del_open_ai_auth_key, set_open_ai_model;
    GROQ: set_groq_auth_key, del_groq_auth_key, set_groq_model;
    OPENROUTER: set_open_router_auth_key, del_open_router_auth_key, set_open_router_model;
}

// ------------------------------------------------------------------------------------- the server engines

/// The server engine unavailable: no models, told to the UI
fn server_unavailable(app: &App, spec: &ServerSpec) -> Result<()> {
    status(app, spec.engine.key(), false);
    app.config.set(&list_name(spec.list), json!([]))?;
    app.config.set(&selected_name(spec.selected), Value::Null)?;
    push_list(app, spec.list)?;
    push_selected(app, spec.selected)?;
    update_translation_engine_and_engine_list(app)
}

/// The server answered: its models, the selected one on the client, the engines updated
fn server_available(app: &App, spec: &ServerSpec) -> Result<()> {
    status(app, spec.engine.key(), true);
    let models = app.model.translator.write().unwrap().get_model_list(spec.engine)?;
    app.config.set(&list_name(spec.list), json!(models))?;
    push_list(app, spec.list)?;
    if models.is_empty() {
        return Err(anyhow!("No {} models available", spec.engine.key()));
    }
    take_models(app, spec.list, models)?;
    use_selected_model(app, spec.engine, spec.selected)?;
    push_selected(app, spec.selected)?;
    update_translation_engine_and_engine_list(app)
}

/// _checkTranslationEngineConnection: LM Studio at its URL, Ollama on this PC
fn check_server(app: &App, spec: &ServerSpec) -> Result<Reply> {
    ipc::log(format!("Check Translator {} Connection", spec.engine.key()));
    let attempt = || -> Result<bool> {
        let connected = match spec.engine {
            Engine::LmStudio => {
                let url = app.config.get("LMSTUDIO_URL");
                app.model.translator.write().unwrap().set_lmstudio_url(url.as_str())?
            }
            _ => app.model.translator.write().unwrap().check_ollama()?,
        };
        if connected {
            server_available(app, spec)?;
        }
        Ok(connected)
    };
    match attempt() {
        Ok(true) => Ok(Reply::ok(true)),
        Ok(false) => {
            server_unavailable(app, spec)?;
            Ok(errors::error(spec.error_connection_failed, json!(false)))
        }
        Err(e) => {
            logs::error(&format!("check {}", spec.engine.key()), &format!("{e:#}"));
            server_unavailable(app, spec)?;
            Ok(errors::error(spec.error_connection_failed, json!(false)))
        }
    }
}

pub fn check_translator_lm_studio_connection(app: &App, _: Data) -> Result<Reply> {
    check_server(app, &LMSTUDIO)
}

pub fn check_translator_ollama_connection(app: &App, _: Data) -> Result<Reply> {
    check_server(app, &OLLAMA)
}

pub fn get_translator_lm_studio_connection(app: &App, _: Data) -> Result<Reply> {
    Ok(Reply::ok(app.model.translator.write().unwrap().lmstudio_connected))
}

pub fn get_translator_ollama_connection(app: &App, _: Data) -> Result<Reply> {
    Ok(Reply::ok(app.model.translator.write().unwrap().ollama_connected))
}

/// The server's models now (not the saved list: local servers add and remove models)
pub fn get_translator_lm_studio_model_list(app: &App, _: Data) -> Result<Reply> {
    Ok(Reply::ok(json!(app.model.translator.write().unwrap().get_model_list(Engine::LmStudio)?)))
}

pub fn get_translator_ollama_model_list(app: &App, _: Data) -> Result<Reply> {
    Ok(Reply::ok(json!(app.model.translator.write().unwrap().get_model_list(Engine::Ollama)?)))
}

pub fn set_translator_lm_studio_model(app: &App, data: Data) -> Result<Reply> {
    set_engine_model(app, Engine::LmStudio, LMSTUDIO.selected, LMSTUDIO.error_model_invalid, data)
}

pub fn set_translator_ollama_model(app: &App, data: Data) -> Result<Reply> {
    set_engine_model(app, Engine::Ollama, OLLAMA.selected, OLLAMA.error_model_invalid, data)
}

/// setTranslatorLMStudioURL: kept only when the server answers with models
pub fn set_translator_lm_studio_url(app: &App, data: Data) -> Result<Reply> {
    let data = data.unwrap_or(Value::Null);
    ipc::print_log("Set Translator LMStudio URL", &data);
    let data = py_str(&data);
    let attempt = || -> Result<bool> {
        if !app.model.translator.write().unwrap().set_lmstudio_url(Some(&data))? {
            return Ok(false);
        }
        app.config.set("LMSTUDIO_URL", json!(data))?;
        server_available(app, &LMSTUDIO)?;
        Ok(true)
    };
    let ok = attempt().unwrap_or_else(|e| {
        logs::error("set LMStudio URL", &format!("{e:#}"));
        false
    });
    if ok {
        return current(app, "LMSTUDIO_URL");
    }
    server_unavailable(app, &LMSTUDIO)?;
    Ok(errors::error("CONNECTION_LMSTUDIO_URL_INVALID", app.config.get("LMSTUDIO_URL")))
}

// ------------------------------------------------------------------------------------- DeepL

pub fn set_deepl_auth_key(app: &App, data: Data) -> Result<Reply> {
    ipc::log("Set DeepL Auth Key");
    let key = "DeepL_API";
    let data = py_str(&data.unwrap_or(Value::Null));
    let attempt = || -> Result<Reply> {
        // the free (":fx", 39) and pro (36) keys
        if ![36, 39].contains(&data.chars().count()) {
            return Ok(errors::error("AUTH_DEEPL_LENGTH", auth_key(app, key)));
        }
        if app.model.translator.write().unwrap().authenticate_deepl(&data).is_err() {
            return Ok(errors::error("AUTH_DEEPL_FAILED", auth_key(app, key)));
        }
        set_auth_key(app, key, json!(data))?;
        status(app, key, true);
        update_translation_engine_and_engine_list(app)?;
        Ok(Reply::ok(auth_key(app, key)))
    };
    Ok(attempt().unwrap_or_else(|e| {
        logs::error("set DeepL auth key", &format!("{e:#}"));
        exception(&e, auth_key(app, key))
    }))
}

pub fn del_deepl_auth_key(app: &App, _: Data) -> Result<Reply> {
    let key = "DeepL_API";
    set_auth_key(app, key, Value::Null)?;
    status(app, key, false);
    update_translation_engine_and_engine_list(app)?;
    Ok(Reply::ok(auth_key(app, key)))
}

// ------------------------------------------------------------------------------------- OpenAI-compatible

const COMPATIBLE: &str = "OpenAI_Compatible";
const COMPATIBLE_X: &str = "OPENAI_COMPATIBLE";

pub fn set_open_ai_compatible_auth_key(app: &App, data: Data) -> Result<Reply> {
    ipc::log("Set OpenAI Compatible Auth Key");
    let data = crate::pyfmt::strip(&py_str(&data.unwrap_or(Value::Null))).to_string();
    let attempt = || -> Result<Reply> {
        if data.is_empty() {
            return Ok(errors::error("AUTH_OPENAI_COMPATIBLE_INVALID", Value::Null));
        }
        let url = app.config.get("OPENAI_COMPATIBLE_URL");
        if !app.model.translator.write().unwrap().authenticate_llm(Engine::OpenAiCompatible, &data, url.as_str())? {
            return Ok(errors::error("AUTH_OPENAI_COMPATIBLE_FAILED", Value::Null));
        }
        let models = app.model.translator.write().unwrap().get_model_list(Engine::OpenAiCompatible)?;
        if models.is_empty() {
            return Ok(errors::error("AUTH_OPENAI_COMPATIBLE_FAILED", Value::Null));
        }
        set_auth_key(app, COMPATIBLE, json!(data))?;
        status(app, COMPATIBLE, true);
        take_models(app, COMPATIBLE_X, models)?;
        use_selected_model(app, Engine::OpenAiCompatible, COMPATIBLE_X)?;
        push_selected(app, COMPATIBLE_X)?;
        update_translation_engine_and_engine_list(app)?;
        Ok(Reply::ok(auth_key(app, COMPATIBLE)))
    };
    let reply = attempt().unwrap_or_else(|e| {
        logs::error("set OpenAI compatible auth key", &format!("{e:#}"));
        exception(&e, Value::Null)
    });
    if reply.status == 400 {
        del_open_ai_compatible_auth_key(app, None)?;
    }
    Ok(reply)
}

pub fn del_open_ai_compatible_auth_key(app: &App, _: Data) -> Result<Reply> {
    set_auth_key(app, COMPATIBLE, Value::Null)?;
    app.config.set(&list_name(COMPATIBLE_X), json!([]))?;
    app.config.set(&selected_name(COMPATIBLE_X), Value::Null)?;
    push_list(app, COMPATIBLE_X)?;
    push_selected(app, COMPATIBLE_X)?;
    status(app, COMPATIBLE, false);
    update_translation_engine_and_engine_list(app)?;
    Ok(Reply::ok(auth_key(app, COMPATIBLE)))
}

/// setOpenAICompatibleURL: without a key only kept; with one, kept once it answers with models
pub fn set_open_ai_compatible_url(app: &App, data: Data) -> Result<Reply> {
    let data = data.unwrap_or(Value::Null);
    ipc::print_log("Set OpenAI Compatible URL", &data);
    let data = crate::pyfmt::strip(&py_str(&data)).to_string();
    let unavailable = || -> Result<()> {
        status(app, COMPATIBLE, false);
        app.config.set(&list_name(COMPATIBLE_X), json!([]))?;
        app.config.set(&selected_name(COMPATIBLE_X), Value::Null)?;
        push_list(app, COMPATIBLE_X)?;
        push_selected(app, COMPATIBLE_X)?;
        update_translation_engine_and_engine_list(app)
    };
    let attempt = || -> Result<Reply> {
        if data.is_empty() {
            return Ok(errors::error("CONNECTION_OPENAI_COMPATIBLE_URL_INVALID", app.config.get("OPENAI_COMPATIBLE_URL")));
        }
        let key = auth_key(app, COMPATIBLE);
        let key = key.as_str().filter(|k| !k.is_empty());
        let Some(key) = key else {
            app.config.set("OPENAI_COMPATIBLE_URL", json!(data))?;
            return current(app, "OPENAI_COMPATIBLE_URL");
        };
        if !app.model.translator.write().unwrap().authenticate_llm(Engine::OpenAiCompatible, key, Some(&data))? {
            unavailable()?;
            return Ok(errors::error("CONNECTION_OPENAI_COMPATIBLE_URL_INVALID", app.config.get("OPENAI_COMPATIBLE_URL")));
        }
        let models = app.model.translator.write().unwrap().get_model_list(Engine::OpenAiCompatible)?;
        if models.is_empty() {
            // the URL answers but has no model to translate with
            unavailable()?;
            return Ok(errors::error("AUTH_OPENAI_COMPATIBLE_FAILED", app.config.get("OPENAI_COMPATIBLE_URL")));
        }
        app.config.set("OPENAI_COMPATIBLE_URL", json!(data))?;
        status(app, COMPATIBLE, true);
        take_models(app, COMPATIBLE_X, models)?;
        use_selected_model(app, Engine::OpenAiCompatible, COMPATIBLE_X)?;
        push_selected(app, COMPATIBLE_X)?;
        update_translation_engine_and_engine_list(app)?;
        current(app, "OPENAI_COMPATIBLE_URL")
    };
    Ok(attempt().unwrap_or_else(|e| {
        logs::error("set OpenAI compatible URL", &format!("{e:#}"));
        exception(&e, app.config.get("OPENAI_COMPATIBLE_URL"))
    }))
}

pub fn set_open_ai_compatible_model(app: &App, data: Data) -> Result<Reply> {
    let data = data.unwrap_or(Value::Null);
    ipc::print_log("Set OpenAI Compatible Model", &data);
    let data = py_str(&data);
    let selected = selected_name(COMPATIBLE_X);
    let attempt = || -> Result<Reply> {
        if !app.model.translator.write().unwrap().set_model(Engine::OpenAiCompatible, &data)? {
            return Ok(errors::error("MODEL_OPENAI_COMPATIBLE_INVALID", app.config.get(&selected)));
        }
        app.config.set(&selected, json!(data))?;
        use_selected_model(app, Engine::OpenAiCompatible, COMPATIBLE_X)?;
        current(app, &selected)
    };
    Ok(attempt().unwrap_or_else(|e| {
        logs::error("set OpenAI compatible model", &format!("{e:#}"));
        exception(&e, app.config.get(&selected))
    }))
}
