//! Start-up and shutdown (Controller.init / shutdown / updateConfigSettings): the weights, every
//! engine's status, the services the settings turn on, then all /get/data/* values to the UI.
use super::engines::{update_transcription_engine, update_translation_engine_and_engine_list};
use super::features::{self, add_keywords, ctranslate2_weight_ok, whisper_weight_ok};
use super::{audio, routes, App};
use crate::asr;
use crate::ipc;
use crate::logs;
use crate::platform;
use crate::translate::llm::{Engine, LlmClient};
use anyhow::{anyhow, Result};
use serde_json::{json, Map, Value};
use std::collections::HashMap;
use std::sync::mpsc;
use std::time::{Duration, Instant};

const WATCHDOG_TIMEOUT: Duration = Duration::from_secs(60);
const WATCHDOG_INTERVAL: Duration = Duration::from_secs(20);
const WEIGHT_DOWNLOAD_WAIT: Duration = Duration::from_secs(1800);
const SERVICE_STOP_WAIT: Duration = Duration::from_secs(5);

fn progress(app: &App, step: i64) -> Result<()> {
    app.run(200, "initialization_progress", json!(step))
}

/// isConnectedNetwork: www.google.com answers 200 within 3 s
fn connected_network(app: &App) -> bool {
    app.model.http.get("http://www.google.com", &[], Some(Duration::from_secs(3))).is_ok_and(|r| r.status() == 200)
}

/// downloadXWeight(weight_type, False) on its own thread; the receiver hears when it ended
fn download_in_background(app: &App, whisper: bool, weight_type: String) -> mpsc::Receiver<()> {
    let (done, rx) = mpsc::channel();
    let me = app.me();
    std::thread::spawn(move || {
        if let Some(app) = me.upgrade() {
            features::download_weight(&app, whisper, &weight_type, true);
        }
        let _ = done.send(());
    });
    rx
}

fn wait_download(rx: Option<mpsc::Receiver<()>>, title: &str) -> bool {
    let Some(rx) = rx else { return false };
    if rx.recv_timeout(WEIGHT_DOWNLOAD_WAIT) == Err(mpsc::RecvTimeoutError::Timeout) {
        ipc::log(format!("{title} weight download did not finish within {}s; continuing initialization without waiting \
                          further (download continues in the background)", WEIGHT_DOWNLOAD_WAIT.as_secs()));
    }
    true
}

/// The weights: downloaded when missing (online), then checked; a weight still missing is
/// downloaded once more. Returns (CTranslate2, Whisper) available.
fn prepare_weights(app: &App, online: bool) -> (bool, bool) {
    let ct2_type = || app.config.get_str("CTRANSLATE2_WEIGHT_TYPE");
    let whisper_type = || app.config.get_str("WHISPER_WEIGHT_TYPE");
    let (mut ct2_pre, mut whisper_pre) = (None, None);
    if online {
        // the weight folders' names before v3.6 are not renamed any more (only v3.6.x is supported)
        ipc::log("Download CTranslate2 Model Weight");
        ct2_pre = Some(ctranslate2_weight_ok(app, &ct2_type()));
        let ct2_job = (ct2_pre == Some(false)).then(|| download_in_background(app, false, ct2_type()));
        ipc::log("Download Whisper Model Weight");
        whisper_pre = Some(whisper_weight_ok(app, &whisper_type()));
        let whisper_job = (whisper_pre == Some(false)).then(|| download_in_background(app, true, whisper_type()));
        // a download changes the answer: checked again below
        if wait_download(ct2_job, "CTranslate2") {
            ct2_pre = None;
        }
        if wait_download(whisper_job, "Whisper") {
            whisper_pre = None;
        }
    }
    let (mut ct2, mut whisper) = std::thread::scope(|s| {
        let c = s.spawn(|| ct2_pre == Some(true) || ctranslate2_weight_ok(app, &ct2_type()));
        let w = s.spawn(|| whisper_pre == Some(true) || whisper_weight_ok(app, &whisper_type()));
        (c.join().unwrap_or(false), w.join().unwrap_or(false))
    });
    if online && !(ct2 && whisper) {
        if !ct2 {
            ipc::log("CTranslate2 weight unavailable after first download; retrying once");
            features::download_weight(app, false, &ct2_type(), true);
        }
        if !whisper {
            ipc::log("Whisper weight unavailable after first download; retrying once");
            features::download_weight(app, true, &whisper_type(), true);
        }
        (ct2, whisper) = std::thread::scope(|s| {
            let c = s.spawn(|| ct2 || ctranslate2_weight_ok(app, &ct2_type()));
            let w = s.spawn(|| whisper || whisper_weight_ok(app, &whisper_type()));
            (c.join().unwrap_or(false), w.join().unwrap_or(false))
        });
    }
    (ct2, whisper)
}

// ------------------------------------------------------------------------------ engine checks

/// What a check found (status, the key failed, the model list, the model to select)
#[derive(Default)]
struct Found {
    status: bool,
    key_invalid: bool,
    models: Option<Vec<String>>,
    selected: Option<String>,
    /// Deepgram: model -> its languages
    languages: Map<String, Value>,
    /// the translator's client for the engine, ready with the selected model
    client: Option<(Engine, LlmClient)>,
}

/// config.SELECTED_X_MODEL if listed, else the first (IndexError on an empty list)
fn pick(app: &App, x: &str, models: &[String]) -> Result<String> {
    let selected = app.config.get(&format!("SELECTED_{x}_MODEL"));
    if let Some(s) = selected.as_str().filter(|s| models.iter().any(|m| m == s)) {
        return Ok(s.to_string());
    }
    models.first().cloned().ok_or_else(|| anyhow!("IndexError: list index out of range"))
}

fn key_of(app: &App, setting: &str, engine: &str) -> Option<String> {
    app.config.get(setting).get(engine).and_then(Value::as_str).map(String::from)
}

const REGISTRY: [(Engine, &str); 5] = [(Engine::Plamo, "PLAMO"), (Engine::Gemini, "GEMINI"), (Engine::OpenAi, "OPENAI"),
                                       (Engine::Groq, "GROQ"), (Engine::OpenRouter, "OPENROUTER")];

fn check_translation_engine(app: &App, engine: &str, ct2: bool, online: bool) -> Result<Found> {
    let mut f = Found::default();
    let settings = app.model.translator.lock().unwrap().settings_dir().to_path_buf();
    let http = app.model.http.clone();
    // a client with the models listed and the selected one set (models empty: no selection)
    let with_models = |f: &mut Found, engine: Engine, x: &str, mut client: LlmClient, need_models: bool| -> Result<()> {
        let models = client.get_model_list()?;
        if need_models && models.is_empty() {
            f.models = Some(models);
            return Ok(());
        }
        let selected = pick(app, x, &models)?;
        client.set_model(&selected)?;
        f.status = true;
        f.models = Some(models);
        f.selected = Some(selected);
        f.client = Some((engine, client));
        Ok(())
    };
    match engine {
        "CTranslate2" => f.status = ct2,
        "DeepL_API" => {
            if let Some(key) = key_of(app, "AUTH_KEYS", engine) {
                // ponytail: under the translator's lock (one request), a client outside it if this slows the start
                match app.model.translator.lock().unwrap().authenticate_deepl(&key) {
                    Ok(true) => f.status = true,
                    _ => f.key_invalid = true,
                }
            }
        }
        "LMStudio" => {
            let url = app.config.get("LMSTUDIO_URL");
            if let Some(url) = url.as_str() {
                let mut client = LlmClient::new(Engine::LmStudio, http, &settings, Some(url))?;
                if client.set_base_url(Some(url)) {
                    with_models(&mut f, Engine::LmStudio, "LMSTUDIO", client, true)?;
                }
            }
        }
        "OpenAI_Compatible" => {
            let url = app.config.get_str("OPENAI_COMPATIBLE_URL");
            if let Some(key) = key_of(app, "AUTH_KEYS", engine).filter(|k| !k.is_empty()).filter(|_| !url.is_empty()) {
                let mut client = LlmClient::new(Engine::OpenAiCompatible, http, &settings, Some(&url))?;
                if client.set_auth_key(&key)? {
                    with_models(&mut f, Engine::OpenAiCompatible, "OPENAI_COMPATIBLE", client, true)?;
                } else {
                    f.key_invalid = true;
                }
            }
        }
        "Ollama" => {
            let client = LlmClient::new(Engine::Ollama, http, &settings, None)?;
            if client.authentication_check() {
                with_models(&mut f, Engine::Ollama, "OLLAMA", client, true)?;
            }
        }
        _ => match REGISTRY.iter().find(|(e, _)| e.key() == engine) {
            Some(&(e, x)) => {
                if let Some(key) = key_of(app, "AUTH_KEYS", engine) {
                    let mut client = LlmClient::new(e, http, &settings, None)?;
                    if client.set_auth_key(&key)? {
                        with_models(&mut f, e, x, client, false)?;
                    } else {
                        f.key_invalid = true;
                    }
                }
            }
            None => f.status = online,
        },
    }
    Ok(f)
}

fn check_transcription_engine(app: &App, engine: &str, whisper: bool, online: bool) -> Result<Found> {
    let mut f = Found::default();
    let http = &app.model.http;
    let key = key_of(app, "TRANSCRIPTION_AUTH_KEYS", engine).filter(|k| !k.is_empty());
    let mut take = |f: &mut Found, x: &str, models: Vec<String>| -> Result<()> {
        if !models.is_empty() {
            f.selected = Some(pick(app, x, &models)?);
            f.status = true;
        }
        f.models = Some(models);
        Ok(())
    };
    let whisper_api = |f: &mut Found, take: &mut dyn FnMut(&mut Found, &str, Vec<String>) -> Result<()>, key: &str, url: &str,
                       x: &str, filter: bool| -> Result<()> {
        if asr::check_whisper_api_key(http, key, url) {
            let keywords = filter.then_some(&asr::TRANSCRIPTION_MODEL_KEYWORDS[..]);
            take(f, x, asr::whisper_api_models(http, key, url, keywords)?)
        } else {
            f.key_invalid = true;
            Ok(())
        }
    };
    match engine {
        "Whisper" => f.status = whisper,
        "Groq_Whisper" | "OpenAI_Whisper" => {
            if let Some(key) = key {
                let (url, x) = if engine == "Groq_Whisper" {
                    ("https://api.groq.com/openai/v1", "GROQ_WHISPER")
                } else {
                    ("https://api.openai.com/v1", "OPENAI_WHISPER")
                };
                whisper_api(&mut f, &mut take, &key, url, x, true)?;
            }
        }
        "Custom_Whisper" => {
            let url = app.config.get_str("TRANSCRIPTION_CUSTOM_URL");
            if let Some(key) = key.filter(|_| !url.is_empty()) {
                whisper_api(&mut f, &mut take, &key, &url, "CUSTOM_WHISPER", false)?;
            }
        }
        "Deepgram" => {
            if let Some(key) = key {
                if asr::check_deepgram_key(http, &key) {
                    let detailed = asr::deepgram_models(http, &key);
                    f.languages = detailed.iter().map(|(n, l)| (n.clone(), json!(l))).collect();
                    take(&mut f, "DEEPGRAM", detailed.into_iter().map(|(n, _)| n).collect())?;
                } else {
                    f.key_invalid = true;
                }
            }
        }
        _ => f.status = online,
    }
    Ok(f)
}

/// Every engine of `list` checked at the same time (each waits on the network); a failed check
/// is an unavailable engine
fn check_all(app: &App, list: &str, check: &(dyn Fn(&str) -> Result<Found> + Sync), what: &str) -> (Vec<String>, HashMap<String, (Found, f64)>) {
    let engines: Vec<String> = app.config.get(list).as_array().into_iter().flatten().filter_map(|e| e.as_str().map(String::from)).collect();
    let results = std::thread::scope(|s| {
        let handles: Vec<_> = engines.iter().map(|engine| (engine.clone(), s.spawn(move || {
            let started = Instant::now();
            let found = check(engine).unwrap_or_else(|e| {
                ipc::log(format!("Error checking {what}{engine}: {e:#}"));
                logs::error(&format!("check {engine}"), &format!("{e:#}"));
                Found::default()
            });
            (found, started.elapsed().as_secs_f64())
        }))).collect();
        handles.into_iter().filter_map(|(e, h)| h.join().ok().map(|r| (e, r))).collect::<HashMap<_, _>>()
    });
    (engines, results)
}

fn set_or_log(app: &App, name: &str, value: Value) {
    if let Err(e) = app.config.set(name, value) {
        logs::error(&format!("set {name}"), &e);
    }
}

fn clear_models(app: &App, x: &str) {
    set_or_log(app, &format!("SELECTABLE_{x}_MODEL_LIST"), json!([]));
    set_or_log(app, &format!("SELECTED_{x}_MODEL"), Value::Null);
}

fn apply_models(app: &App, x: &str, f: &Found) {
    set_or_log(app, &format!("SELECTABLE_{x}_MODEL_LIST"), json!(f.models));
    set_or_log(app, &format!("SELECTED_{x}_MODEL"), json!(f.selected));
}

fn init_translation_engines(app: &App, ct2: bool, online: bool) {
    ipc::log("Init Translation Engine Status");
    let started = Instant::now();
    let check = |engine: &str| check_translation_engine(app, engine, ct2, online);
    let (engines, mut results) = check_all(app, "SELECTABLE_TRANSLATION_ENGINE_LIST", &check, "engine ");
    for engine in &engines {
        let Some((mut f, elapsed)) = results.remove(engine) else { continue };
        let applying = Instant::now();
        ipc::log(format!("Start check {engine}"));
        if let Some((e, client)) = f.client.take() {
            app.model.translator.lock().unwrap().put_client(e, f.status.then_some(client));
        }
        app.config.put_item("SELECTABLE_TRANSLATION_ENGINE_STATUS", engine, json!(f.status));
        if f.key_invalid {
            let mut keys = app.config.get("AUTH_KEYS");
            keys[engine.as_str()] = Value::Null;
            set_or_log(app, "AUTH_KEYS", keys);
            ipc::log(format!("{engine} auth key is invalid"));
        } else if f.status {
            ipc::log(format!("{engine} is valid/available"));
        }
        let x = match engine.as_str() {
            "LMStudio" => Some("LMSTUDIO"),
            "OpenAI_Compatible" => Some("OPENAI_COMPATIBLE"),
            "Ollama" => Some("OLLAMA"),
            _ => None,
        };
        if let (Some(x), false) = (x, f.status) {
            clear_models(app, x);
        }
        let x = x.or_else(|| REGISTRY.iter().find(|(e, _)| e.key() == engine).map(|(_, x)| *x));
        if let (Some(x), true, true) = (x, f.models.is_some(), f.status) {
            apply_models(app, x, &f);
        }
        ipc::log(format!("{engine} check completed (check {elapsed:.2}s, apply {:.2}s)", applying.elapsed().as_secs_f64()));
    }
    ipc::log(format!("Translation Engine Status Init completed ({:.2}s)", started.elapsed().as_secs_f64()));
}

fn init_transcription_engines(app: &App, whisper: bool, online: bool) {
    ipc::log("Init Transcription Engine Status");
    let started = Instant::now();
    let check = |engine: &str| check_transcription_engine(app, engine, whisper, online);
    let (engines, mut results) = check_all(app, "SELECTABLE_TRANSCRIPTION_ENGINE_LIST", &check, "transcription engine ");
    for engine in &engines {
        let Some((f, elapsed)) = results.remove(engine) else { continue };
        app.config.put_item("SELECTABLE_TRANSCRIPTION_ENGINE_STATUS", engine, json!(f.status));
        if f.key_invalid {
            let mut keys = app.config.get("TRANSCRIPTION_AUTH_KEYS");
            keys[engine.as_str()] = Value::Null;
            set_or_log(app, "TRANSCRIPTION_AUTH_KEYS", keys);
            ipc::log(format!("{engine} transcription auth key is invalid"));
        } else if f.status {
            ipc::log(format!("{engine} transcription engine is valid/available (check {elapsed:.2}s)"));
        }
        let x = match engine.as_str() {
            "Groq_Whisper" => "GROQ_WHISPER",
            "OpenAI_Whisper" => "OPENAI_WHISPER",
            "Custom_Whisper" => "CUSTOM_WHISPER",
            "Deepgram" => "DEEPGRAM",
            _ => continue,
        };
        if !f.status {
            set_or_log(app, &format!("SELECTABLE_{x}_MODEL_LIST"), json!([]));
            if x == "DEEPGRAM" {
                set_or_log(app, "DEEPGRAM_MODEL_LANGUAGES", json!({}));
            }
            set_or_log(app, &format!("SELECTED_{x}_MODEL"), Value::Null);
        } else if f.models.is_some() {
            set_or_log(app, &format!("SELECTABLE_{x}_MODEL_LIST"), json!(f.models));
            if x == "DEEPGRAM" {
                set_or_log(app, "DEEPGRAM_MODEL_LANGUAGES", Value::Object(f.languages.clone()));
            }
            set_or_log(app, &format!("SELECTED_{x}_MODEL"), json!(f.selected));
        }
    }
    ipc::log(format!("Transcription Engine Status Init completed ({:.2}s)", started.elapsed().as_secs_f64()));
}

/// updateDownloadedXModelWeight: the selected weight from the start-up check, the others loaded
fn update_weight_dict(app: &App, dict: &str, selected: &str, available: bool, ok: &dyn Fn(&str) -> bool) {
    let types: Vec<String> = app.config.get(dict).as_object().map(|m| m.keys().cloned().collect()).unwrap_or_default();
    for t in types {
        let value = if t == selected { available } else { ok(&t) };
        app.config.put_item(dict, &t, json!(value));
    }
}

// --------------------------------------------------------------------------------------- OSC

/// The OSC events (MuteSelf, avatar change) go to the microphone's mute sync
fn start_osc(app: &App) {
    let me = app.me();
    app.model.osc.start_receive(move |event| {
        if let Some(app) = me.upgrade() {
            audio::on_osc_event(&app, event);
        }
    });
}

/// init_osc_receive_background
fn init_osc(app: &App) -> Result<()> {
    start_osc(app);
    if app.model.osc.is_osc_query_enabled() {
        features::push_osc_query(app, true, false)?;
        if app.config.get_bool("VRC_MIC_MUTE_SYNC") {
            audio::init_vrc_mic_mute_sync(app)?;
        }
    } else {
        features::sync_osc_query(app)?;
    }
    Ok(())
}

fn background(app: &App, label: &'static str, job: fn(&App) -> Result<()>) {
    let me = app.me();
    std::thread::spawn(move || {
        let Some(app) = me.upgrade() else { return };
        match job(&app) {
            Ok(()) => ipc::log(format!("[Background] {label} completed")),
            Err(e) => {
                logs::error(label, &format!("{e:#}"));
                ipc::log(format!("[Background] {label} failed"));
            }
        }
    });
}

// ------------------------------------------------------------------------------------- init

/// Controller.init: `escalate` runs when the UI stops feeding the watchdog
pub fn init(app: &App, escalate: impl Fn() + Send + 'static) -> Result<()> {
    logs::PROCESS.clear();
    ipc::log("Start Initialization");
    let started = Instant::now();
    // _bootstrapModel: the overlay's callbacks tell their state at once
    super::overlay::push_initial_state(app)?;
    app.model.watchdog.start(WATCHDOG_TIMEOUT, WATCHDOG_INTERVAL, escalate);

    let online = connected_network(app);
    app.run(200, "connected_network", json!(online))?;
    ipc::log(format!("Connected Network: {}", if online { "True" } else { "False" }));
    progress(app, 1)?;

    let (ct2, whisper) = prepare_weights(app, online);
    app.run(200, "enable_ai_models", json!(ct2 && whisper))?;

    init_translation_engines(app, ct2, online);
    init_transcription_engines(app, whisper, online);
    progress(app, 2)?;

    ipc::log("Set Translation Engine");
    update_weight_dict(app, "SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT", &app.config.get_str("CTRANSLATE2_WEIGHT_TYPE"), ct2,
                       &|t| ctranslate2_weight_ok(app, t));
    update_translation_engine_and_engine_list(app)?;
    ipc::log("Set Transcription Engine");
    update_weight_dict(app, "SELECTABLE_WHISPER_WEIGHT_TYPE_DICT", &app.config.get_str("WHISPER_WEIGHT_TYPE"), whisper,
                       &|t| whisper_weight_ok(app, t));
    update_transcription_engine(app, None)?;

    ipc::log("Set Transliteration");
    if app.config.get_bool("CONVERT_MESSAGE_TO_ROMAJI") || app.config.get_bool("CONVERT_MESSAGE_TO_HIRAGANA") {
        features::start_transliteration(app)?;
    }
    progress(app, 3)?;

    ipc::log("Set Word Filter");
    add_keywords(app);

    ipc::log("Check Software Updated (Background)");
    background(app, "Software update check", features::check_software_updated);

    ipc::log("Init Logger");
    if app.config.get_bool("LOGGER_FEATURE") {
        features::start_logger(app)?;
    }
    progress(app, 4)?;

    ipc::log("Init OSC Receive (Background)");
    background(app, "OSC Receive initialization", init_osc);

    ipc::log("Init Device Manager");
    audio::init_devices(app)?;

    ipc::log("Init Overlay");
    super::overlay::sync_overlay_running(app)?;

    ipc::log("Init WebSocket Server");
    init_servers(app)?;

    ipc::log("Revalidate Selected Models");
    app.config.revalidate_selected_models();

    ipc::log("Telemetry Init");
    if app.config.get_bool("ENABLE_TELEMETRY") {
        features::telemetry_init(app, true);
    }

    ipc::log("Update settings");
    update_config_settings(app);
    ipc::log(format!("End Initialization ({:.2}s)", started.elapsed().as_secs_f64()));
    Ok(())
}

/// The WebSocket server (needed by the OBS page) and the OBS page's server, when on and their ports are free
fn init_servers(app: &App) -> Result<()> {
    let (host, ws_port) = (app.config.get_str("WEBSOCKET_HOST"), app.config.get("WEBSOCKET_PORT").as_i64().unwrap_or(-1));
    let servers = &app.model.servers;
    if app.config.get_bool("OBS_BROWSER_SOURCE") && app.config.get("WEBSOCKET_SERVER") == json!(false) {
        app.config.set("WEBSOCKET_SERVER", json!(true))?;
    }
    if app.config.get_bool("WEBSOCKET_SERVER") {
        if platform::is_available_server(&host, ws_port) {
            servers.start_websocket(&app.config, &host, ws_port);
        } else {
            app.config.set("WEBSOCKET_SERVER", json!(false))?;
            servers.stop_websocket();
            ipc::log("WebSocket server host or port is not available");
        }
    }
    ipc::log("Init OBS Browser Source Server");
    if app.config.get_bool("OBS_BROWSER_SOURCE") {
        let obs_port = app.config.get("OBS_BROWSER_SOURCE_PORT").as_i64().unwrap_or(-1);
        if !app.config.get_bool("WEBSOCKET_SERVER") {
            app.config.set("OBS_BROWSER_SOURCE", json!(false))?;
            servers.stop_obs();
            ipc::log("OBS Browser Source requires WebSocket Server");
        } else if platform::is_available_server(&host, obs_port) {
            servers.start_obs(&app.config, &host, obs_port);
        } else {
            app.config.set("OBS_BROWSER_SOURCE", json!(false))?;
            servers.stop_obs();
            ipc::log("OBS Browser Source server host or port is not available");
        }
    }
    Ok(())
}

/// updateConfigSettings: every /get/data/* (but the releases, a slow GitHub request) to the UI
/// at once; a getter that fails gives null
pub fn update_config_settings(app: &App) {
    let mut settings = Map::new();
    for (endpoint, route) in routes::routes() {
        if !endpoint.starts_with("/get/data/") || endpoint == "/get/data/available_releases" {
            continue;
        }
        let result = match (route.handler)(app, None) {
            Ok(reply) => reply.result,
            Err(e) => {
                logs::error(&format!("updateConfigSettings {endpoint}"), &format!("{e:#}"));
                ipc::log(format!("updateConfigSettings: failed to collect {endpoint}"));
                Value::Null
            }
        };
        settings.insert(endpoint.to_string(), result);
    }
    let _ = app.run(200, "initialization_complete", Value::Object(settings));
}

// ----------------------------------------------------------------------------------- shutdown

/// _stopServiceForShutdown: on its own thread, given up after 5 s (the process ends anyway)
fn stop_service(app: &App, label: &str, stop: fn(&App)) {
    let (done, rx) = mpsc::channel();
    let me = app.me();
    std::thread::spawn(move || {
        if let Some(app) = me.upgrade() {
            stop(&app);
        }
        let _ = done.send(());
    });
    if rx.recv_timeout(SERVICE_STOP_WAIT) == Err(mpsc::RecvTimeoutError::Timeout) {
        ipc::log(format!("shutdown: {label} の停止が {}s でタイムアウトしました(プロセス終了時に破棄されます)",
                         SERVICE_STOP_WAIT.as_secs()));
    }
}

/// Controller.shutdown (/run/shutdown, and before the process ends): the audio, the services,
/// config.json saved, telemetry sent. The UI ends the process 2 s after /run/shutdown.
pub fn shutdown(app: &App, _: Option<Value>) -> Result<ipc::Reply> {
    audio::shutdown(app);
    stop_service(app, "OSC receive server", |a| a.model.osc.stop_receive());
    stop_service(app, "OBS browser source server", |a| a.model.servers.stop_obs());
    stop_service(app, "WebSocket server", |a| a.model.servers.stop_websocket());
    stop_service(app, "Overlay", super::overlay::shutdown);
    stop_service(app, "watchdog", |a| a.model.watchdog.stop());
    if let Err(e) = app.config.save_to_file() {
        logs::error("save config", &e);
    }
    app.model.telemetry.shutdown();
    Ok(ipc::Reply::ok(true))
}
