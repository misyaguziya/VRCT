//! The message pipeline (controller.py's _processMessage with message_pipeline.py's specs): a
//! message from the microphone, the speaker, OCR or the chat box goes through the word filter,
//! translation and transliteration, then to VRChat (OSC), the overlays, the clipboard, the UI, the
//! WebSocket clients and the chat log.
use super::engines::change_to_ctranslate2_process;
use super::features::start_transliteration;
use super::{current, overlay, App};
use crate::ipc::{self, Reply};
use crate::logs;
use crate::translate::ctranslate2::Ct2Translator;
use crate::translate::llm::HistoryItem;
use crate::translate::Translation;
use crate::translit;
use anyhow::{anyhow, Result};
use serde_json::{json, Map, Value};
use std::sync::atomic::Ordering;
use std::time::{Duration, Instant};

const HISTORY_MAX_ITEMS: usize = 20;

/// MessageDirectionSpec: how one source of messages differs
pub struct Spec {
    kind: &'static str,
    word_filter: bool,
    /// detectRepeatSendMessage (true) / detectRepeatReceiveMessage (false)
    repeat: Option<bool>,
    /// getInputTranslate (your language to the targets) or getOutputTranslate (to your language)
    input: bool,
    own_from_your_language: bool,
    feature_gate: Option<&'static str>,
    osc_gate: Option<&'static str>,
    format: &'static str,
    overlay_direction: &'static str,
    overlay_small_log: bool,
    clipboard: bool,
    ws_type: &'static str,
    ws_src: &'static str,
    ws_dst: &'static str,
    logger_prefix: &'static str,
    /// pushed to this run_mapping name; None: returned (the chat box)
    push: Option<&'static str>,
    source: Option<&'static str>,
}

pub const MIC: Spec = Spec { kind: "mic", word_filter: true, repeat: Some(true), input: true, own_from_your_language: true,
    feature_gate: Some("ENABLE_TRANSCRIPTION_SEND"), osc_gate: Some("SEND_MESSAGE_TO_VRC"), format: "SEND",
    overlay_direction: "send", overlay_small_log: false, clipboard: true, ws_type: "SENT", ws_src: "SELECTED_YOUR_LANGUAGES",
    ws_dst: "SELECTED_TARGET_LANGUAGES", logger_prefix: "[SENT]", push: Some("transcription_mic"), source: None };
pub const SPEAKER: Spec = Spec { kind: "speaker", word_filter: true, repeat: Some(false), input: false, own_from_your_language: false,
    feature_gate: Some("ENABLE_TRANSCRIPTION_RECEIVE"), osc_gate: Some("SEND_RECEIVED_MESSAGE_TO_VRC"), format: "RECEIVED",
    overlay_direction: "receive", overlay_small_log: true, clipboard: false, ws_type: "RECEIVED",
    ws_src: "SELECTED_TARGET_LANGUAGES", ws_dst: "SELECTED_YOUR_LANGUAGES", logger_prefix: "[RECEIVED]",
    push: Some("transcription_speaker"), source: None };
pub const OCR: Spec = Spec { kind: "ocr", word_filter: true, repeat: None, input: false, own_from_your_language: false,
    feature_gate: Some("ENABLE_OCR_CAPTURE"), osc_gate: None, format: "RECEIVED", overlay_direction: "receive",
    overlay_small_log: false, clipboard: false, ws_type: "RECEIVED", ws_src: "SELECTED_TARGET_LANGUAGES",
    ws_dst: "SELECTED_YOUR_LANGUAGES", logger_prefix: "[OCR]", push: Some("transcription_ocr"), source: Some("ocr") };
pub const CHAT: Spec = Spec { kind: "chat", word_filter: false, repeat: None, input: true, own_from_your_language: true,
    feature_gate: None, osc_gate: Some("SEND_MESSAGE_TO_VRC"), format: "SEND", overlay_direction: "send",
    overlay_small_log: false, clipboard: false, ws_type: "CHAT", ws_src: "SELECTED_YOUR_LANGUAGES",
    ws_dst: "SELECTED_TARGET_LANGUAGES", logger_prefix: "[CHAT]", push: None, source: None };

fn tab(app: &App) -> String {
    crate::pyjson::py_str(&app.config.get("SELECTED_TAB_NO"))
}

/// config.X[config.SELECTED_TAB_NO]
fn of_tab(app: &App, name: &str) -> Value {
    app.config.get(name).get(tab(app)).cloned().unwrap_or(Value::Null)
}

fn your_language(app: &App) -> Value {
    of_tab(app, "SELECTED_YOUR_LANGUAGES")["1"].clone()
}

// ---------------------------------------------------------------------------------- history

/// datetime.now().isoformat(): microseconds unless they are 0
fn isoformat_now() -> String {
    let now = chrono::Local::now();
    if now.timestamp_subsec_micros() == 0 {
        now.format("%Y-%m-%dT%H:%M:%S").to_string()
    } else {
        now.format("%Y-%m-%dT%H:%M:%S%.6f").to_string()
    }
}

/// addTranslationHistory: the last 20 messages, the context of the LLM engines
pub fn add_history(app: &App, source: &str, text: &str) {
    let text = text.trim();
    if text.is_empty() {
        return;
    }
    let mut history = app.model.translation_history.lock().unwrap();
    history.push(HistoryItem { source: source.into(), text: text.into(), timestamp: Some(isoformat_now()) });
    let excess = history.len().saturating_sub(HISTORY_MAX_ITEMS);
    history.drain(..excess);
}

// ------------------------------------------------------------------------------ translation

/// changeTranslatorCTranslate2Model: the selected weight on the selected device
pub fn load_ctranslate2(app: &App) -> Result<()> {
    let device = app.config.get("SELECTED_TRANSLATION_COMPUTE_DEVICE");
    let (name, index) = (device["device"].as_str().unwrap_or("cpu").to_string(), device["device_index"].as_i64().unwrap_or(0));
    let mut compute_type = app.config.get_str("SELECTED_TRANSLATION_COMPUTE_TYPE");
    if compute_type == "auto" {
        compute_type = crate::compute::best_compute_type(&name, index as usize);
    }
    let mut translator = app.model.translator.write().unwrap();
    translator.ctranslate2 = None;
    translator.ctranslate2 = Some(Ct2Translator::load(&app.config.env().path_local, &app.config.get_str("CTRANSLATE2_WEIGHT_TYPE"),
                                                      &name, index as i32, &compute_type)?);
    Ok(())
}

/// getTranslate: the engine, else CTranslate2 (retried 2 s while it fails with a model loaded).
/// A language pair neither knows gives the message back; (text, false) when CTranslate2 failed too.
fn translate_one(app: &App, engine: &str, source: &str, target: &str, country: &str, message: &str) -> (String, bool) {
    let weight_type = app.config.get_str("CTRANSLATE2_WEIGHT_TYPE");
    let history = app.model.translation_history.lock().unwrap().clone();
    let first = app.model.translator.read().unwrap().translate(engine, &weight_type, source, target, country, message, &history);
    if let Translation::Text(text) = first {
        return (text, true);
    }
    let mut result = first;
    for _ in 0..20 {
        let translator = app.model.translator.read().unwrap();
        result = translator.translate("CTranslate2", &weight_type, source, target, country, message, &[]);
        match &result {
            Translation::Text(_) | Translation::Unsupported => break,
            Translation::Failed(_) if translator.ctranslate2.is_none() => break,
            Translation::Failed(_) => {}
        }
        drop(translator);
        std::thread::sleep(Duration::from_millis(100));
    }
    match result {
        Translation::Text(text) => (text, true),
        Translation::Unsupported => (message.to_string(), true),
        Translation::Failed(reason) => {
            logs::error("translate", &reason);
            (message.to_string(), false)
        }
    }
}

/// getInputTranslate / getOutputTranslate: (translations, each succeeded)
fn translate(app: &App, input: bool, message: &str, source: Option<&str>) -> (Vec<String>, Vec<bool>) {
    let engine = crate::pyjson::py_str(&of_tab(app, "SELECTED_TRANSLATION_ENGINES"));
    let text = |v: &Value| v.as_str().unwrap_or_default().to_string();
    let (source, targets) = if input {
        let source = source.map_or_else(|| text(&your_language(app)["language"]), String::from);
        let targets: Vec<(String, String)> = of_tab(app, "SELECTED_TARGET_LANGUAGES").as_object().into_iter().flatten()
            .map(|(_, v)| v)
            .filter(|v| v["enable"] == json!(true) && (!v["language"].is_null() || !v["country"].is_null()))
            .map(|v| (text(&v["language"]), text(&v["country"])))
            .collect();
        (source, targets)
    } else {
        let source = source.map_or_else(|| text(&of_tab(app, "SELECTED_TARGET_LANGUAGES")["1"]["language"]), String::from);
        let your = your_language(app);
        (source, vec![(text(&your["language"]), text(&your["country"]))])
    };
    if targets.len() <= 1 {
        return targets.iter().map(|(language, country)| translate_one(app, &engine, &source, language, country, message)).unzip();
    }
    // the targets at once, as Python's pool (a cloud engine is mostly waiting on the network); the
    // results in the targets' order
    std::thread::scope(|s| {
        let running: Vec<_> = targets.iter()
            .map(|(language, country)| s.spawn(|| translate_one(app, &engine, &source, language, country, message)))
            .collect();
        running.into_iter().map(|t| t.join().unwrap_or_else(|_| (message.to_string(), false))).unzip()
    })
}

fn transliterate(app: &App, text: &str) -> Result<Value> {
    let (hiragana, romaji) = (app.config.get_bool("CONVERT_MESSAGE_TO_HIRAGANA"), app.config.get_bool("CONVERT_MESSAGE_TO_ROMAJI"));
    if !hiragana && !romaji {
        return Ok(json!([]));
    }
    start_transliteration(app)?;
    let t = app.model.transliterator.lock().unwrap();
    let t = t.as_ref().ok_or_else(|| anyhow!("no transliterator"))?;
    Ok(json!(translit::convert_message(t, text, hiragana, romaji)?))
}

/// messageFormatter: the message and the translations as the format parts say
pub fn format_message(app: &App, format: &str, translation: &[String], message: &str) -> String {
    let parts = app.config.get(if format == "RECEIVED" { "RECEIVED_MESSAGE_FORMAT_PARTS" } else { "SEND_MESSAGE_FORMAT_PARTS" });
    let s = |v: &Value| v.as_str().unwrap_or_default().to_string();
    let message_part = s(&parts["message"]["prefix"]) + message + &s(&parts["message"]["suffix"]);
    let translation_part = s(&parts["translation"]["prefix"]) + &translation.join(&s(&parts["translation"]["separator"]))
        + &s(&parts["translation"]["suffix"]);
    if !translation.is_empty() && !message.is_empty() {
        if parts["translation_first"] == json!(true) {
            translation_part + &s(&parts["separator"]) + &message_part
        } else {
            message_part + &s(&parts["separator"]) + &translation_part
        }
    } else if !translation.is_empty() {
        translation_part
    } else {
        message_part
    }
}

// --------------------------------------------------------------------------------- pipeline

fn detect_repeat(app: &App, send: bool, message: &str) -> bool {
    let previous = if send { &app.model.previous_send_message } else { &app.model.previous_receive_message };
    let mut previous = previous.lock().unwrap();
    let repeated = *previous == message;
    *previous = message.to_string();
    repeated
}

/// _processMessage: None when filtered out or pushed; the chat box's answer otherwise
pub fn process(app: &App, spec: &Spec, message: &str, language: Option<&str>, msg_id: Option<Value>, asr_ms: Option<i64>)
               -> Result<Option<Value>> {
    if spec.word_filter && !app.model.keywords.lock().unwrap().extract(message).is_empty() {
        app.run(200, "word_filter", json!({"message": format!("Detected by word filter: {message}")}))?;
        return Ok(None);
    }
    if spec.repeat.is_some_and(|send| detect_repeat(app, send, message)) {
        return Ok(None);
    }
    let started = Instant::now();
    let mut translate_ms = 0;
    let mut translation = vec![];
    if app.config.get_bool("ENABLE_TRANSLATION") {
        let t = Instant::now();
        let success;
        (translation, success) = translate(app, spec.input, message, language);
        if !success.iter().all(|s| *s) {
            change_to_ctranslate2_process(app)?;
            app.run_error("error_translation_engine", "TRANSLATION_ENGINE_LIMIT", Value::Null)?;
        }
        translate_ms = t.elapsed().as_millis();
    }

    let translit_on = app.config.get_bool("CONVERT_MESSAGE_TO_HIRAGANA") || app.config.get_bool("CONVERT_MESSAGE_TO_ROMAJI");
    let translation_on = app.config.get_bool("ENABLE_TRANSLATION");
    let slots: Vec<String> = app.config.get("SELECTED_TAB_TARGET_LANGUAGES_NO_LIST").as_array().into_iter().flatten()
        .map(crate::pyjson::py_str).collect();
    let mut translit_message = json!([]);
    let mut translit_translation: Vec<Value> = vec![];
    let at = |i: usize| translation.get(i).ok_or_else(|| anyhow!("IndexError: list index out of range"));
    if translit_on {
        let own_japanese = if spec.own_from_your_language {
            your_language(app)["language"] == json!("Japanese")
        } else {
            language == Some("Japanese")
        };
        if own_japanese {
            translit_message = transliterate(app, message)?;
        }
        if spec.input {
            let targets = of_tab(app, "SELECTED_TARGET_LANGUAGES");
            for (i, no) in slots.iter().enumerate() {
                let target = &targets[no.as_str()];
                translit_translation.push(if translation_on && target["language"] == json!("Japanese") && target["enable"] == json!(true) {
                    transliterate(app, at(i)?)?
                } else {
                    json!([])
                });
            }
        } else {
            translit_translation.push(if translation_on && your_language(app)["language"] == json!("Japanese") {
                transliterate(app, at(0)?)?
            } else {
                json!([])
            });
        }
    } else {
        translit_translation = vec![json!([]); if spec.input { slots.len() } else { 1 }];
    }

    let mut payload = Map::new();
    if let Some(id) = &msg_id {
        payload.insert("id".into(), id.clone());
    }
    payload.insert("original".into(), json!({"message": message, "transliteration": translit_message}));
    payload.insert("translations".into(), json!(translation.iter().zip(&translit_translation)
        .map(|(m, t)| json!({"message": m, "transliteration": t})).collect::<Vec<_>>()));
    if let Some(source) = spec.source {
        payload.insert("source".into(), json!(source));
    }

    if spec.feature_gate.is_none_or(|gate| app.config.get_bool(gate)) {
        if spec.osc_gate.is_some_and(|gate| app.config.get_bool(gate)) {
            let osc_message = if !app.config.get_bool("SEND_ONLY_TRANSLATED_MESSAGES") {
                format_message(app, spec.format, &translation, message)
            } else if !translation_on {
                format_message(app, spec.format, &[], message)
            } else {
                format_message(app, spec.format, &translation, "")
            };
            app.model.osc.send_message(&osc_message, app.config.get_bool("NOTIFICATION_VRC_SFX"))?;
        }
        let translit_translation = json!(translit_translation);
        let only_translated = app.config.get_bool("OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES");
        fn shown(only_translated: bool, own: Option<&str>) -> Option<&str> {
            own.filter(|_| !only_translated)
        }
        if spec.overlay_small_log && app.config.get_bool("OVERLAY_SMALL_LOG") && overlay::is_available(app)
            && (!only_translated || !translation.is_empty()) {
            overlay::small_log(app, shown(only_translated, Some(message)), shown(only_translated, language), &translation, &of_tab(app, "SELECTED_YOUR_LANGUAGES"),
                               &translit_message, &translit_translation)?;
        }
        if app.config.get_bool("OVERLAY_LARGE_LOG") && overlay::is_available(app) && (!only_translated || !translation.is_empty()) {
            let (own, list) = if spec.overlay_direction == "send" {
                (your_language(app)["language"].as_str().map(String::from), of_tab(app, "SELECTED_TARGET_LANGUAGES"))
            } else {
                (language.map(String::from), of_tab(app, "SELECTED_YOUR_LANGUAGES"))
            };
            overlay::large_log(app, spec.overlay_direction, shown(only_translated, Some(message)), shown(only_translated, own.as_deref()), &translation, &list,
                               &translit_message, &translit_translation)?;
        }
        if spec.clipboard && app.config.get_bool("ENABLE_CLIPBOARD") {
            let text = format_message(app, spec.format, &translation, message);
            let window = app.model.app_name.get();
            crate::clipboard::copy_and_paste(&text, window.as_deref(), &|line| ipc::log(line));
        }
        if let Some(name) = spec.push {
            app.run(200, name, Value::Object(payload.clone()))?;
        }
        if app.model.servers.websocket_alive() {
            app.model.servers.websocket_send(&json!({
                "type": spec.ws_type,
                "src_languages": of_tab(app, spec.ws_src),
                "dst_languages": of_tab(app, spec.ws_dst),
                "message": message,
                "translation": translation,
                "transliteration": translit_translation,
            }));
        }
        if app.config.get_bool("LOGGER_FEATURE") {
            if let Some(logger) = &*app.model.logger.lock().unwrap() {
                let joined = if translation.is_empty() { String::new() } else { format!(" ({})", translation.join("/")) };
                logger.write(&format!("{} {message}{joined}", spec.logger_prefix));
            }
        }
    }
    add_history(app, spec.kind, message);

    let elapsed = started.elapsed().as_millis();
    let asr = asr_ms.map(|ms| format!("asr={ms}ms ")).unwrap_or_default();
    ipc::log(format!("[latency][{}] {asr}translate={translate_ms}ms output={}ms total={}ms", spec.kind,
                     elapsed - translate_ms, elapsed as i64 + asr_ms.unwrap_or(0)));
    Ok(spec.push.is_none().then(|| {
        let mut out = Map::new();
        out.insert("id".into(), msg_id.unwrap_or(Value::Null));
        out.extend(payload.into_iter().filter(|(k, _)| k != "id"));
        Value::Object(out)
    }))
}

// --------------------------------------------------------------------------------- handlers

/// chatMessage (/run/send_message_box)
pub fn send_message_box(app: &App, data: Option<Value>) -> Result<Reply> {
    let data = data.unwrap_or(Value::Null);
    let field = |key: &str| data.get(key).cloned().ok_or_else(|| anyhow!("KeyError: {key:?}"));
    let (id, message) = (field("id")?, field("message")?);
    let message = message.as_str().ok_or_else(|| anyhow!("message is not a string"))?;
    if message.is_empty() {
        add_history(app, "chat", message);
        return Ok(Reply::ok(json!({"id": id, "original": {"message": message, "transliteration": []}, "translations": []})));
    }
    Ok(Reply::ok(process(app, &CHAT, message, None, Some(id), None)?.unwrap_or(Value::Null)))
}

/// detectVRAMError's message checks (a CUDA allocation that failed)
fn vram_error(error: &anyhow::Error) -> Option<String> {
    let text = format!("{error:#}");
    (text.contains("CUDA out of memory") || text.contains("CUBLAS_STATUS_ALLOC_FAILED")).then_some(text)
}

/// setEnableTranslation: the CTranslate2 model loads first when none is loaded or its settings changed
pub fn set_enable_translation(app: &App, _: Option<Value>) -> Result<Reply> {
    if app.config.get("ENABLE_TRANSLATION") != json!(false) {
        return current(app, "ENABLE_TRANSLATION");
    }
    let loaded = app.model.translator.read().unwrap().ctranslate2.is_some();
    if loaded && !app.model.translator_changed.load(Ordering::SeqCst) {
        app.config.set("ENABLE_TRANSLATION", json!(true))?;
        return current(app, "ENABLE_TRANSLATION");
    }
    match load_ctranslate2(app) {
        Ok(()) => {
            app.model.translator_changed.store(false, Ordering::SeqCst);
            app.config.set("ENABLE_TRANSLATION", json!(true))?;
        }
        Err(e) => match vram_error(&e) {
            Some(message) => {
                ipc::log("VRAM error detected, reverting device setting");
                // run_mapping has no "error_translation_enable_vram_overflow": this fails as the KeyError did
                app.run_error("error_translation_enable_vram_overflow", "TRANSLATION_VRAM_ENABLE", json!(message))?;
            }
            None => logs::error("load CTranslate2", &format!("{e:#}")),
        },
    }
    current(app, "ENABLE_TRANSLATION")
}
