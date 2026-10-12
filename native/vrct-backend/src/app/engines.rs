//! Choosing the translation and transcription engines (controller.py): the engines a tab's
//! languages allow, falling back to CTranslate2 / Whisper when the chosen one cannot be used, and
//! the languages falling back to ones the engine speaks.
use super::{current, App};
use crate::ipc::{self, Reply};
use crate::pyjson::py_str;
use anyhow::{anyhow, Result};
use serde_json::{json, Value};

type Data = Option<Value>;

/// `value[key]`, a KeyError when missing (the handler answers 500)
pub fn at<'a>(value: &'a Value, key: &str) -> Result<&'a Value> {
    value.get(key).ok_or_else(|| anyhow!("KeyError: {key:?}"))
}

fn tab(app: &App) -> String {
    app.config.get_str("SELECTED_TAB_NO")
}

/// The enabled slots' languages of a tab's language slots
fn enabled_languages(slots: &Value) -> Vec<String> {
    slots.as_object().into_iter().flat_map(|m| m.values()).filter(|e| e["enable"] == json!(true))
        .filter_map(|e| e["language"].as_str().map(String::from)).collect()
}

/// getTranslationEngines: the engines for the tab's languages; CTranslate2 only (if available)
/// when a target is the source language
pub fn translation_engines(app: &App) -> Result<Vec<String>> {
    let tab = tab(app);
    let your = app.config.get("SELECTED_YOUR_LANGUAGES");
    let target = app.config.get("SELECTED_TARGET_LANGUAGES");
    let status = app.config.get("SELECTABLE_TRANSLATION_ENGINE_STATUS");
    let (your, target) = (at(&your, &tab)?, at(&target, &tab)?);
    let mut engines = app.model.find_translation_engines(&app.config, your, target, &status);
    let your_language = at(your, "1")?;
    for t in target.as_object().into_iter().flat_map(|m| m.values()) {
        if your_language["language"] == t["language"] && t["enable"] == json!(true) {
            engines = if at(&status, "CTranslate2")? == &json!(true) { vec!["CTranslate2".into()] } else { vec![] };
        }
    }
    Ok(engines)
}

pub fn get_translation_engines(app: &App, _: Data) -> Result<Reply> {
    Ok(Reply::ok(json!(translation_engines(app)?)))
}

pub fn get_list_language_and_country(app: &App, _: Data) -> Result<Reply> {
    Ok(Reply::ok(app.model.list_language_and_country(&app.config)))
}

/// updateTranslationEngineAndEngineList: the tab's engine kept if available (else CTranslate2,
/// also when a target is the source language), the languages the engine cannot speak reset; both
/// told to the UI
pub fn update_translation_engine_and_engine_list(app: &App) -> Result<()> {
    let tab = tab(app);
    let mut engines = app.config.get("SELECTED_TRANSLATION_ENGINES");
    let mut engine = at(&engines, &tab)?.clone();
    let mut selectable = translation_engines(app)?;
    if !engine.as_str().is_some_and(|e| selectable.iter().any(|s| s == e)) {
        engine = json!("CTranslate2");
    }
    engines[&tab] = engine.clone();
    app.config.set("SELECTED_TRANSLATION_ENGINES", engines.clone())?;
    let your = app.config.get("SELECTED_YOUR_LANGUAGES");
    let your_language = at(at(&your, &tab)?, "1")?.clone();
    let targets = app.config.get("SELECTED_TARGET_LANGUAGES");
    for t in at(&targets, &tab)?.as_object().into_iter().flat_map(|m| m.values()) {
        if your_language["language"] == t["language"] && t["enable"] == json!(true) {
            engine = json!("CTranslate2");
            engines[&tab] = engine.clone();
            app.config.set("SELECTED_TRANSLATION_ENGINES", engines.clone())?;
            break;
        }
    }
    // even CTranslate2 may not speak the languages: they are reset instead
    if fallback_unsupported_languages_for_engine(app, &tab, &py_str(&engine))? {
        selectable = translation_engines(app)?;
    }
    app.run(200, "selected_translation_engines", app.config.get("SELECTED_TRANSLATION_ENGINES"))?;
    app.run(200, "translation_engines", json!(selectable))
}

/// fallbackUnsupportedLanguagesForEngine: the tab's languages `engine` cannot speak back to a
/// default it can, avoiding the tab's other enabled languages; told when anything changed
fn fallback_unsupported_languages_for_engine(app: &App, tab: &str, engine: &str) -> Result<bool> {
    let mut changed = false;
    let mut your_languages = app.config.get("SELECTED_YOUR_LANGUAGES");
    let mut target_languages = app.config.get("SELECTED_TARGET_LANGUAGES");
    let mut your_language = at(at(&your_languages, tab)?, "1")?.clone();
    let enabled_targets = enabled_languages(at(&target_languages, tab)?);
    let unsupported = !app.model.is_language_supported_by_engine(&app.config, engine, your_language["language"].as_str().unwrap_or_default());
    if let Some(default) = unsupported.then(|| app.model.pick_default_language_for_engine(&app.config, engine, &enabled_targets)).flatten() {
        let mut slot = default;
        slot["enable"] = json!(true);
        your_languages[tab]["1"] = slot.clone();
        app.config.set("SELECTED_YOUR_LANGUAGES", your_languages.clone())?;
        changed = true;
        your_language = slot;
    }
    let mut target_changed = false;
    // languages taken as we go: two unsupported targets do not get the same default
    let mut taken = vec![py_str(&your_language["language"])];
    if let Some(slots) = target_languages.get_mut(tab).and_then(Value::as_object_mut) {
        for t in slots.values_mut() {
            if t["enable"] != json!(true) {
                continue;
            }
            let language = py_str(&t["language"]);
            if app.model.is_language_supported_by_engine(&app.config, engine, &language) {
                taken.push(language);
                continue;
            }
            if let Some(default) = app.model.pick_default_language_for_engine(&app.config, engine, &taken) {
                t["language"] = default["language"].clone();
                t["country"] = default["country"].clone();
                target_changed = true;
            }
            taken.push(py_str(&t["language"]));
        }
    }
    if target_changed {
        app.config.set("SELECTED_TARGET_LANGUAGES", target_languages)?;
        changed = true;
    }
    if changed {
        app.run(200, "selected_your_languages", app.config.get("SELECTED_YOUR_LANGUAGES"))?;
        app.run(200, "selected_target_languages", app.config.get("SELECTED_TARGET_LANGUAGES"))?;
    }
    Ok(changed)
}

pub fn set_selected_tab_no(app: &App, data: Data) -> Result<Reply> {
    let data = data.unwrap_or(Value::Null);
    ipc::print_log("setSelectedTabNo", &data);
    app.config.set("SELECTED_TAB_NO", data)?;
    update_translation_engine_and_engine_list(app)?;
    current(app, "SELECTED_TAB_NO")
}

pub fn set_selected_translation_engines(app: &App, data: Data) -> Result<Reply> {
    app.config.set("SELECTED_TRANSLATION_ENGINES", data.unwrap_or(Value::Null))?;
    update_translation_engine_and_engine_list(app)?;
    current(app, "SELECTED_TRANSLATION_ENGINES")
}

pub fn set_selected_your_languages(app: &App, data: Data) -> Result<Reply> {
    app.config.set("SELECTED_YOUR_LANGUAGES", data.unwrap_or(Value::Null))?;
    update_translation_engine_and_engine_list(app)?;
    current(app, "SELECTED_YOUR_LANGUAGES")
}

pub fn set_selected_target_languages(app: &App, data: Data) -> Result<Reply> {
    app.config.set("SELECTED_TARGET_LANGUAGES", data.unwrap_or(Value::Null))?;
    update_translation_engine_and_engine_list(app)?;
    current(app, "SELECTED_TARGET_LANGUAGES")
}

/// The tab's source and first target swapped
pub fn swap_your_language_and_target_language(app: &App, _: Data) -> Result<Reply> {
    let tab = tab(app);
    let mut your = app.config.get("SELECTED_YOUR_LANGUAGES");
    let mut target = app.config.get("SELECTED_TARGET_LANGUAGES");
    let your_first = at(at(&your, &tab)?, "1")?.clone();
    let target_first = at(at(&target, &tab)?, "1")?.clone();
    your[&tab]["1"] = target_first;
    target[&tab]["1"] = your_first;
    set_selected_your_languages(app, Some(your))?;
    set_selected_target_languages(app, Some(target))?;
    Ok(Reply::ok(json!({"your": app.config.get("SELECTED_YOUR_LANGUAGES"), "target": app.config.get("SELECTED_TARGET_LANGUAGES")})))
}

/// changeToCTranslate2Process: the tab's failing engine marked unavailable, CTranslate2 instead
pub fn change_to_ctranslate2_process(app: &App) -> Result<()> {
    let tab = tab(app);
    let mut engines = app.config.get("SELECTED_TRANSLATION_ENGINES");
    let selected = py_str(at(&engines, &tab)?);
    app.config.put_item("SELECTABLE_TRANSLATION_ENGINE_STATUS", &selected, json!(false));
    engines[&tab] = json!("CTranslate2");
    app.config.set("SELECTED_TRANSLATION_ENGINES", engines)?;
    let selectable = translation_engines(app)?;
    app.run(200, "selected_translation_engines", app.config.get("SELECTED_TRANSLATION_ENGINES"))?;
    app.run(200, "translation_engines", json!(selectable))
}

// ------------------------------------------------------------------------------------- transcription

const TRANSCRIPTION_API_ENGINES: [&str; 3] = ["Groq_Whisper", "OpenAI_Whisper", "Custom_Whisper"];

/// updateTranscriptionEngine: `requested` first (setSelectedTranscriptionEngine), then kept if
/// available: Whisper / Google fall back to each other (or Whisper without its weights), the API
/// engines to Whisper. A change resets the languages it cannot recognize and sends the list.
pub fn update_transcription_engine(app: &App, requested: Option<String>) -> Result<()> {
    let previous = app.config.get("SELECTED_TRANSCRIPTION_ENGINE");
    if let Some(engine) = requested {
        app.config.set("SELECTED_TRANSCRIPTION_ENGINE", json!(engine))?;
    }
    let weight_type = app.config.get_str("WHISPER_WEIGHT_TYPE");
    let weight_available = app.config.get("SELECTABLE_WHISPER_WEIGHT_TYPE_DICT").get(&weight_type).is_some_and(truthy);
    let current_engine = app.config.get_str("SELECTED_TRANSCRIPTION_ENGINE");
    let status = app.config.get("SELECTABLE_TRANSCRIPTION_ENGINE_STATUS");
    let selected: Vec<&String> = status.as_object().into_iter().flatten().filter(|(_, v)| **v == json!(true)).map(|(k, _)| k).collect();
    let available = |e: &str| selected.iter().any(|s| *s == e);
    let engine_value = app.config.get("SELECTED_TRANSCRIPTION_ENGINE");
    if engine_value.is_string() && ["Whisper", "Google"].contains(&current_engine.as_str()) {
        if !available(&current_engine) {
            if weight_available {
                let alternate = if current_engine == "Whisper" { "Google" } else { "Whisper" };
                app.config.set("SELECTED_TRANSCRIPTION_ENGINE", if available(alternate) { json!(alternate) } else { Value::Null })?;
            } else {
                app.config.set("SELECTED_TRANSCRIPTION_ENGINE", json!("Whisper"))?;
            }
        }
    } else if engine_value.is_string() && (TRANSCRIPTION_API_ENGINES.contains(&current_engine.as_str()) || current_engine == "Deepgram") {
        if !available(&current_engine) {
            app.config.set("SELECTED_TRANSCRIPTION_ENGINE", json!("Whisper"))?;
        }
    } else {
        app.config.set("SELECTED_TRANSCRIPTION_ENGINE", json!("Whisper"))?;
    }
    if app.config.get("SELECTED_TRANSCRIPTION_ENGINE") != previous {
        let engine = app.config.get_str("SELECTED_TRANSCRIPTION_ENGINE");
        fallback_unsupported_languages_for_transcription_engine(app, &engine)?;
        app.run(200, "selectable_language_list", app.model.list_language_and_country(&app.config))?;
    }
    Ok(())
}

/// Python's bool()
pub fn truthy(v: &Value) -> bool {
    match v {
        Value::Null => false,
        Value::Bool(b) => *b,
        Value::Number(n) => n.as_f64() != Some(0.0),
        Value::String(s) => !s.is_empty(),
        Value::Array(a) => !a.is_empty(),
        Value::Object(o) => !o.is_empty(),
    }
}

/// fallbackUnsupportedLanguagesForTranscriptionEngine: on every tab (the engine is global)
pub fn fallback_unsupported_languages_for_transcription_engine(app: &App, engine: &str) -> Result<bool> {
    let mut changed = false;
    let mut your_languages = app.config.get("SELECTED_YOUR_LANGUAGES");
    let mut target_languages = app.config.get("SELECTED_TARGET_LANGUAGES");
    let tabs: Vec<String> = your_languages.as_object().map(|m| m.keys().cloned().collect()).unwrap_or_default();
    let supported = |l: &Value| app.model.is_language_supported_by_transcription_engine(&app.config, engine, &py_str(&l["language"]),
                                                                                          &py_str(&l["country"]));
    for tab in tabs {
        let mut your_language = at(at(&your_languages, &tab)?, "1")?.clone();
        let enabled_targets = target_languages.get(&tab).map(enabled_languages).unwrap_or_default();
        let unsupported = !supported(&your_language);
        if let Some(default) = unsupported.then(|| app.model.pick_default_language_for_transcription_engine(&app.config, engine, &enabled_targets)).flatten() {
            let mut slot = default;
            slot["enable"] = json!(true);
            your_languages[&tab]["1"] = slot.clone();
            changed = true;
            your_language = slot;
        }
        let mut taken = vec![py_str(&your_language["language"])];
        if let Some(slots) = target_languages.get_mut(&tab).and_then(Value::as_object_mut) {
            for t in slots.values_mut() {
                if t["enable"] != json!(true) {
                    continue;
                }
                if supported(t) {
                    taken.push(py_str(&t["language"]));
                    continue;
                }
                if let Some(default) = app.model.pick_default_language_for_transcription_engine(&app.config, engine, &taken) {
                    t["language"] = default["language"].clone();
                    t["country"] = default["country"].clone();
                    changed = true;
                }
                taken.push(py_str(&t["language"]));
            }
        }
    }
    if changed {
        app.config.set("SELECTED_YOUR_LANGUAGES", your_languages)?;
        app.config.set("SELECTED_TARGET_LANGUAGES", target_languages)?;
        app.run(200, "selected_your_languages", app.config.get("SELECTED_YOUR_LANGUAGES"))?;
        app.run(200, "selected_target_languages", app.config.get("SELECTED_TARGET_LANGUAGES"))?;
    }
    Ok(changed)
}

pub fn set_selected_transcription_engine(app: &App, data: Data) -> Result<Reply> {
    update_transcription_engine(app, Some(py_str(&data.unwrap_or(Value::Null))))?;
    current(app, "SELECTED_TRANSCRIPTION_ENGINE")
}
