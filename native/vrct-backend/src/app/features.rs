//! The handlers of the features that are not the pipeline (controller.py): OSC, the WebSocket
//! and OBS browser source servers, the word filter, the chat log, transliteration, telemetry, the
//! folders, software updates and weight downloads.
use super::{current, App};
use crate::config::py_eq;
use crate::errors;
use crate::ipc::{self, Reply};
use crate::logs::{self, LogFile};
use crate::platform::{self, ip_address};
use crate::pyfmt;
use crate::pyjson::{py_int, py_str};
use crate::update::{self, Updater};
use crate::weights;
use anyhow::{anyhow, bail, Result};
use serde_json::{json, Value};
use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

type Data = Option<Value>;

fn data_or_null(data: Data) -> Value {
    data.unwrap_or(Value::Null)
}

fn int_of(app: &App, name: &str) -> i64 {
    app.config.get(name).as_i64().unwrap_or_default()
}

pub fn feed_watchdog(app: &App, _: Data) -> Result<Reply> {
    app.model.watchdog.feed();
    Ok(Reply::ok(true))
}

// ---------------------------------------------------------------------------------------- OSC

/// enableOscQuery / disableOscQuery
pub fn push_osc_query(app: &App, enabled: bool, mute_sync_disabled: bool) -> Result<()> {
    let disabled: Vec<&str> = if mute_sync_disabled { vec!["vrc_mic_mute_sync"] } else { vec![] };
    app.run(200, "enable_osc_query", json!({"data": enabled, "disabled_functions": disabled}))
}

/// After the OSC address changed or OSC started: without OSCQuery, mic mute sync goes off
pub fn sync_osc_query(app: &App) -> Result<()> {
    if app.model.osc.is_osc_query_enabled() {
        return push_osc_query(app, true, false);
    }
    let mute_sync = app.config.get_bool("VRC_MIC_MUTE_SYNC");
    if mute_sync {
        super::audio::set_disable_vrc_mic_mute_sync(app, None)?;
    }
    push_osc_query(app, false, mute_sync)
}

pub fn set_osc_ip_address(app: &App, data: Data) -> Result<Reply> {
    let data = data_or_null(data);
    if ip_address(&data).is_none() {
        return Ok(errors::error("VALIDATION_INVALID_IP", app.config.get("OSC_IP_ADDRESS")));
    }
    let attempt = || -> Result<()> {
        let ip = data.as_str().ok_or_else(|| anyhow!("OSC address {data} is not a string"))?;
        app.model.osc.set_ip(ip)?;
        app.config.set("OSC_IP_ADDRESS", data.clone())?;
        sync_osc_query(app)
    };
    match attempt() {
        Ok(()) => current(app, "OSC_IP_ADDRESS"),
        Err(e) => {
            logs::error("set OSC IP address", &format!("{e:#}"));
            let _ = app.model.osc.set_ip(&app.config.get_str("OSC_IP_ADDRESS"));
            Ok(errors::error("VALIDATION_CANNOT_SET_IP", app.config.get("OSC_IP_ADDRESS")))
        }
    }
}

pub fn set_osc_port(app: &App, data: Data) -> Result<Reply> {
    let Some(port) = data.as_ref().and_then(py_int) else {
        return Ok(errors::error_response("VALIDATION_OSC_PORT_INVALID", app.config.get("OSC_PORT"), None,
                                         Some("OSC port must be a number".into())));
    };
    app.config.set("OSC_PORT", json!(port))?;
    app.model.osc.set_port(int_of(app, "OSC_PORT"))?;
    current(app, "OSC_PORT")
}

pub fn typing_message_box(app: &App, _: Data) -> Result<Reply> {
    if app.config.get_bool("SEND_MESSAGE_TO_VRC") {
        app.model.osc.send_typing(true)?;
    }
    Ok(Reply::ok(true))
}

pub fn stop_typing_message_box(app: &App, _: Data) -> Result<Reply> {
    if app.config.get_bool("SEND_MESSAGE_TO_VRC") {
        app.model.osc.send_typing(false)?;
    }
    Ok(Reply::ok(true))
}

// -------------------------------------------------------------------------- WebSocket and OBS

fn host(app: &App) -> String {
    app.config.get_str("WEBSOCKET_HOST")
}

/// isAvailableWebSocketServer for a value from the UI (only a string can be bound)
fn available(host: &Value, port: i64) -> bool {
    host.as_str().is_some_and(|h| platform::is_available_server(h, port))
}

pub fn set_web_socket_host(app: &App, data: Data) -> Result<Reply> {
    let data = data_or_null(data);
    let attempt = || -> Result<Reply> {
        if ip_address(&data).is_none_or(|ip| ip.is_unspecified()) {
            return Ok(errors::error("VALIDATION_INVALID_IP", app.config.get("WEBSOCKET_HOST")));
        }
        let servers = &app.model.servers;
        if !servers.websocket_alive() {
            app.config.set("WEBSOCKET_HOST", data.clone())?;
        } else if py_eq(&data, &app.config.get("WEBSOCKET_HOST")) {
        } else if available(&data, int_of(app, "WEBSOCKET_PORT")) {
            let new_host = data.as_str().unwrap_or_default();
            servers.stop_websocket();
            servers.start_websocket(&app.config, new_host, int_of(app, "WEBSOCKET_PORT"));
            app.config.set("WEBSOCKET_HOST", data.clone())?;
            // the OBS page's server stays on the host the WebSocket server listens on
            if app.config.get_bool("OBS_BROWSER_SOURCE") {
                servers.stop_obs();
                servers.start_obs(&app.config, new_host, int_of(app, "OBS_BROWSER_SOURCE_PORT"));
            }
        } else {
            return Ok(errors::error("WEBSOCKET_HOST_INVALID", app.config.get("WEBSOCKET_HOST")));
        }
        current(app, "WEBSOCKET_HOST")
    };
    Ok(attempt().unwrap_or_else(|e| {
        logs::error("set WebSocket host", &format!("{e:#}"));
        errors::error("WEBSOCKET_HOST_INVALID", app.config.get("WEBSOCKET_HOST"))
    }))
}

pub fn set_web_socket_port(app: &App, data: Data) -> Result<Reply> {
    let Some(port) = data.as_ref().and_then(py_int) else {
        return Ok(errors::error_response("WEBSOCKET_PORT_INVALID", app.config.get("WEBSOCKET_PORT"), None,
                                         Some("WebSocket port must be a number".into())));
    };
    let attempt = || -> Result<Reply> {
        let servers = &app.model.servers;
        if !servers.websocket_alive() {
            app.config.set("WEBSOCKET_PORT", json!(port))?;
        } else if port == int_of(app, "WEBSOCKET_PORT") {
        } else if platform::is_available_server(&host(app), port) {
            servers.stop_websocket();
            servers.start_websocket(&app.config, &host(app), port);
            app.config.set("WEBSOCKET_PORT", json!(port))?;
        } else {
            return Ok(errors::error("WEBSOCKET_PORT_UNAVAILABLE", app.config.get("WEBSOCKET_PORT")));
        }
        current(app, "WEBSOCKET_PORT")
    };
    Ok(attempt().unwrap_or_else(|e| {
        logs::error("set WebSocket port", &format!("{e:#}"));
        errors::error("WEBSOCKET_PORT_UNAVAILABLE", app.config.get("WEBSOCKET_PORT"))
    }))
}

pub fn get_web_socket_auth_token(app: &App, _: Data) -> Result<Reply> {
    current(app, "WEBSOCKET_AUTH_TOKEN")
}

pub fn set_enable_web_socket_server(app: &App, _: Data) -> Result<Reply> {
    let attempt = || -> Result<Reply> {
        if app.config.get("WEBSOCKET_SERVER") == json!(false) {
            if !platform::is_available_server(&host(app), int_of(app, "WEBSOCKET_PORT")) {
                return Ok(errors::error("WEBSOCKET_SERVER_UNAVAILABLE", app.config.get("WEBSOCKET_SERVER")));
            }
            app.model.servers.start_websocket(&app.config, &host(app), int_of(app, "WEBSOCKET_PORT"));
            app.config.set("WEBSOCKET_SERVER", json!(true))?;
        }
        current(app, "WEBSOCKET_SERVER")
    };
    Ok(attempt().unwrap_or_else(|e| {
        logs::error("enable WebSocket server", &format!("{e:#}"));
        errors::error("WEBSOCKET_SERVER_UNAVAILABLE", app.config.get("WEBSOCKET_SERVER"))
    }))
}

pub fn set_disable_web_socket_server(app: &App, _: Data) -> Result<Reply> {
    if app.config.get_bool("WEBSOCKET_SERVER") {
        // the OBS page gets its messages through this server: it goes off too
        if app.config.get_bool("OBS_BROWSER_SOURCE") {
            app.config.set("OBS_BROWSER_SOURCE", json!(false))?;
            app.model.servers.stop_obs();
        }
        app.config.set("WEBSOCKET_SERVER", json!(false))?;
        app.model.servers.stop_websocket();
    }
    current(app, "WEBSOCKET_SERVER")
}

pub fn set_enable_obs_browser_source(app: &App, _: Data) -> Result<Reply> {
    if app.config.get_bool("OBS_BROWSER_SOURCE") {
        return current(app, "OBS_BROWSER_SOURCE");
    }
    let servers = &app.model.servers;
    if !servers.websocket_alive() {
        if !platform::is_available_server(&host(app), int_of(app, "WEBSOCKET_PORT")) {
            return Ok(errors::error_response("OBS_BROWSER_SOURCE_SERVER_UNAVAILABLE", app.config.get("OBS_BROWSER_SOURCE"),
                                             None, Some("WebSocket server host or port is not available".into())));
        }
        servers.start_websocket(&app.config, &host(app), int_of(app, "WEBSOCKET_PORT"));
        app.config.set("WEBSOCKET_SERVER", json!(true))?;
    }
    let port = py_int(&app.config.get("OBS_BROWSER_SOURCE_PORT")).ok_or_else(|| anyhow!("OBS_BROWSER_SOURCE_PORT"))?;
    if !platform::is_available_server(&host(app), port) {
        return Ok(errors::error("OBS_BROWSER_SOURCE_PORT_UNAVAILABLE", app.config.get("OBS_BROWSER_SOURCE_PORT")));
    }
    servers.start_obs(&app.config, &host(app), port);
    if !servers.obs_alive() {
        return Ok(errors::error("OBS_BROWSER_SOURCE_SERVER_UNAVAILABLE", app.config.get("OBS_BROWSER_SOURCE")));
    }
    app.config.set("OBS_BROWSER_SOURCE", json!(true))?;
    current(app, "OBS_BROWSER_SOURCE")
}

pub fn set_disable_obs_browser_source(app: &App, _: Data) -> Result<Reply> {
    if app.config.get_bool("OBS_BROWSER_SOURCE") {
        app.config.set("OBS_BROWSER_SOURCE", json!(false))?;
        app.model.servers.stop_obs();
    }
    current(app, "OBS_BROWSER_SOURCE")
}

pub fn set_obs_browser_source_port(app: &App, data: Data) -> Result<Reply> {
    let Some(port) = data.as_ref().and_then(py_int) else {
        return Ok(errors::error_response("OBS_BROWSER_SOURCE_PORT_UNAVAILABLE", app.config.get("OBS_BROWSER_SOURCE_PORT"),
                                         None, Some("OBS Browser Source port must be a number".into())));
    };
    let servers = &app.model.servers;
    if !servers.obs_alive() {
        app.config.set("OBS_BROWSER_SOURCE_PORT", json!(port))?;
        return current(app, "OBS_BROWSER_SOURCE_PORT");
    }
    if py_eq(&json!(port), &app.config.get("OBS_BROWSER_SOURCE_PORT")) {
        return current(app, "OBS_BROWSER_SOURCE_PORT");
    }
    if !platform::is_available_server(&host(app), port) {
        return Ok(errors::error("OBS_BROWSER_SOURCE_PORT_UNAVAILABLE", app.config.get("OBS_BROWSER_SOURCE_PORT")));
    }
    servers.stop_obs();
    servers.start_obs(&app.config, &host(app), port);
    if !servers.obs_alive() {
        app.config.set("OBS_BROWSER_SOURCE", json!(false))?;
        return Ok(errors::error("OBS_BROWSER_SOURCE_SERVER_UNAVAILABLE", app.config.get("OBS_BROWSER_SOURCE")));
    }
    app.config.set("OBS_BROWSER_SOURCE_PORT", json!(port))?;
    current(app, "OBS_BROWSER_SOURCE_PORT")
}

/// _pushObsBrowserSourceSettings: open OBS pages apply the display settings at once
fn push_obs_settings(app: &App) {
    if !app.config.get_bool("OBS_BROWSER_SOURCE") || !app.model.servers.websocket_alive() {
        return;
    }
    let c = |name: &str| app.config.get(name);
    app.model.servers.websocket_send(&json!({
        "type": "SETTINGS_UPDATED",
        "settings": {
            "maxMessages": c("OBS_BROWSER_SOURCE_MAX_MESSAGES"),
            "displayDuration": c("OBS_BROWSER_SOURCE_DISPLAY_DURATION"),
            "fadeoutDuration": c("OBS_BROWSER_SOURCE_FADEOUT_DURATION"),
            "fontSize": c("OBS_BROWSER_SOURCE_FONT_SIZE"),
            "fontColor": c("OBS_BROWSER_SOURCE_FONT_COLOR"),
            "outlineThickness": c("OBS_BROWSER_SOURCE_FONT_OUTLINE_THICKNESS"),
            "outlineColor": c("OBS_BROWSER_SOURCE_FONT_OUTLINE_COLOR"),
        },
    }));
}

fn obs_int(app: &App, data: Data, name: &str, code: &str, message: &str) -> Result<Reply> {
    let Some(value) = data.as_ref().and_then(py_int) else {
        return Ok(errors::error_response(code, app.config.get(name), None, Some(message.into())));
    };
    app.config.set(name, json!(value))?;
    push_obs_settings(app);
    current(app, name)
}

/// _HEX_COLOR_RE on str(data).strip(), kept upper-case
fn obs_color(app: &App, data: Data, name: &str, code: &str) -> Result<Reply> {
    let color = pyfmt::strip(&py_str(&data_or_null(data))).to_string();
    let b = color.as_bytes();
    if !(b.len() == 7 && b[0] == b'#' && b[1..].iter().all(u8::is_ascii_hexdigit)) {
        return Ok(errors::error(code, app.config.get(name)));
    }
    app.config.set(name, json!(color.to_uppercase()))?;
    push_obs_settings(app);
    current(app, name)
}

pub fn set_obs_browser_source_max_messages(app: &App, data: Data) -> Result<Reply> {
    obs_int(app, data, "OBS_BROWSER_SOURCE_MAX_MESSAGES", "OBS_BROWSER_SOURCE_MAX_MESSAGES_INVALID",
            "OBS Browser Source max messages must be a number")
}

pub fn set_obs_browser_source_display_duration(app: &App, data: Data) -> Result<Reply> {
    obs_int(app, data, "OBS_BROWSER_SOURCE_DISPLAY_DURATION", "OBS_BROWSER_SOURCE_DISPLAY_DURATION_INVALID",
            "OBS Browser Source display duration must be a number")
}

pub fn set_obs_browser_source_fadeout_duration(app: &App, data: Data) -> Result<Reply> {
    obs_int(app, data, "OBS_BROWSER_SOURCE_FADEOUT_DURATION", "OBS_BROWSER_SOURCE_FADEOUT_DURATION_INVALID",
            "OBS Browser Source fadeout duration must be a number")
}

pub fn set_obs_browser_source_font_size(app: &App, data: Data) -> Result<Reply> {
    obs_int(app, data, "OBS_BROWSER_SOURCE_FONT_SIZE", "OBS_BROWSER_SOURCE_FONT_SIZE_INVALID",
            "OBS Browser Source font size must be a number")
}

pub fn set_obs_browser_source_font_outline_thickness(app: &App, data: Data) -> Result<Reply> {
    obs_int(app, data, "OBS_BROWSER_SOURCE_FONT_OUTLINE_THICKNESS", "OBS_BROWSER_SOURCE_FONT_OUTLINE_THICKNESS_INVALID",
            "OBS Browser Source outline thickness must be a number")
}

pub fn set_obs_browser_source_font_color(app: &App, data: Data) -> Result<Reply> {
    obs_color(app, data, "OBS_BROWSER_SOURCE_FONT_COLOR", "OBS_BROWSER_SOURCE_FONT_COLOR_INVALID")
}

pub fn set_obs_browser_source_font_outline_color(app: &App, data: Data) -> Result<Reply> {
    obs_color(app, data, "OBS_BROWSER_SOURCE_FONT_OUTLINE_COLOR", "OBS_BROWSER_SOURCE_FONT_OUTLINE_COLOR_INVALID")
}

// ------------------------------------------------------------------------ simple service toggles

pub fn set_enable_clipboard(app: &App, _: Data) -> Result<Reply> {
    if app.config.get("ENABLE_CLIPBOARD") == json!(false) {
        app.config.set("ENABLE_CLIPBOARD", json!(true))?;
    }
    current(app, "ENABLE_CLIPBOARD")
}

pub fn set_disable_clipboard(app: &App, _: Data) -> Result<Reply> {
    if app.config.get_bool("ENABLE_CLIPBOARD") {
        app.config.set("ENABLE_CLIPBOARD", json!(false))?;
    }
    current(app, "ENABLE_CLIPBOARD")
}

/// startTransliteration: the dictionary loads once (until both conversions are off)
pub fn start_transliteration(app: &App) -> Result<()> {
    let mut t = app.model.transliterator.lock().unwrap();
    if t.is_none() {
        let dir = app.model.resources.sudachi();
        *t = Some(crate::translit::Transliterator::new(&dir, &dir.join("system.dic"))?);
    }
    Ok(())
}

fn transliteration(app: &App, name: &str, other: &str, on: bool) -> Result<Reply> {
    if app.config.get(name) == json!(!on) {
        if app.config.get(other) == json!(false) {
            if on {
                start_transliteration(app)?;
            } else {
                *app.model.transliterator.lock().unwrap() = None;
            }
        }
        app.config.set(name, json!(on))?;
    }
    current(app, name)
}

pub fn set_enable_convert_message_to_romaji(app: &App, _: Data) -> Result<Reply> {
    transliteration(app, "CONVERT_MESSAGE_TO_ROMAJI", "CONVERT_MESSAGE_TO_HIRAGANA", true)
}

pub fn set_disable_convert_message_to_romaji(app: &App, _: Data) -> Result<Reply> {
    transliteration(app, "CONVERT_MESSAGE_TO_ROMAJI", "CONVERT_MESSAGE_TO_HIRAGANA", false)
}

pub fn set_enable_convert_message_to_hiragana(app: &App, _: Data) -> Result<Reply> {
    transliteration(app, "CONVERT_MESSAGE_TO_HIRAGANA", "CONVERT_MESSAGE_TO_ROMAJI", true)
}

pub fn set_disable_convert_message_to_hiragana(app: &App, _: Data) -> Result<Reply> {
    transliteration(app, "CONVERT_MESSAGE_TO_HIRAGANA", "CONVERT_MESSAGE_TO_ROMAJI", false)
}

/// addKeywords: MIC_WORD_FILTER's words into the filter
pub fn add_keywords(app: &App) {
    let mut keywords = app.model.keywords.lock().unwrap();
    for word in app.config.get("MIC_WORD_FILTER").as_array().into_iter().flatten() {
        // flashtext adds what `in` and `lower()` accept; config keeps strings only
        if let Some(word) = word.as_str() {
            keywords.add(word);
        }
    }
}

/// sorted(set(data), key=data.index): the first of each equal value, in order. A string gives
/// its characters; anything else that is not a list of hashable values fails (500).
fn unique(data: &Value) -> Result<Vec<Value>> {
    let items: Vec<Value> = match data {
        Value::Array(a) => a.clone(),
        Value::String(s) => s.chars().map(|c| json!(c.to_string())).collect(),
        other => bail!("TypeError: {other} is not a list"),
    };
    let mut out: Vec<Value> = vec![];
    for item in items {
        if matches!(item, Value::Array(_) | Value::Object(_)) {
            bail!("TypeError: unhashable type");
        }
        if !out.iter().any(|o| py_eq(o, &item)) {
            out.push(item);
        }
    }
    Ok(out)
}

pub fn set_mic_word_filter(app: &App, data: Data) -> Result<Reply> {
    app.config.set("MIC_WORD_FILTER", json!(unique(&data_or_null(data))?))?;
    *app.model.keywords.lock().unwrap() = Default::default();
    add_keywords(app);
    current(app, "MIC_WORD_FILTER")
}

/// startLogger: logs/<start time>.log
pub fn start_logger(app: &App) -> Result<()> {
    let dir = app.config.env().path_local.join("logs");
    std::fs::create_dir_all(&dir)?;
    let file = dir.join(format!("{}.log", chrono::Local::now().format("%Y-%m-%d_%H-%M-%S")));
    *app.model.logger.lock().unwrap() = Some(LogFile::at(file.to_string_lossy().into_owned(), "log", "INFO"));
    Ok(())
}

pub fn set_enable_logger_feature(app: &App, _: Data) -> Result<Reply> {
    if app.config.get("LOGGER_FEATURE") == json!(false) {
        start_logger(app)?;
        app.config.set("LOGGER_FEATURE", json!(true))?;
    }
    current(app, "LOGGER_FEATURE")
}

pub fn set_disable_logger_feature(app: &App, _: Data) -> Result<Reply> {
    if app.config.get_bool("LOGGER_FEATURE") {
        *app.model.logger.lock().unwrap() = None;
        app.config.set("LOGGER_FEATURE", json!(false))?;
    }
    current(app, "LOGGER_FEATURE")
}

/// telemetryInit: the state is kept beside config.json
pub fn telemetry_init(app: &App, enabled: bool) {
    let path = app.config.env().path_local.join("telemetry_state.json");
    app.model.telemetry.init(enabled, &app.config.get_str("VERSION"), Some(&path));
}

pub fn set_enable_telemetry(app: &App, _: Data) -> Result<Reply> {
    if app.config.get("ENABLE_TELEMETRY") == json!(false) {
        app.config.set("ENABLE_TELEMETRY", json!(true))?;
        telemetry_init(app, true);
    }
    current(app, "ENABLE_TELEMETRY")
}

pub fn set_disable_telemetry(app: &App, _: Data) -> Result<Reply> {
    if app.config.get_bool("ENABLE_TELEMETRY") {
        app.config.set("ENABLE_TELEMETRY", json!(false))?;
        app.model.telemetry.shutdown();
    }
    current(app, "ENABLE_TELEMETRY")
}

fn explorer(path: &std::path::Path) -> Result<Reply> {
    std::process::Command::new("explorer").arg(path).spawn()?;
    Ok(Reply::ok(true))
}

pub fn open_filepath_logs(app: &App, _: Data) -> Result<Reply> {
    explorer(&app.config.env().path_local.join("logs"))
}

pub fn open_filepath_config_file(app: &App, _: Data) -> Result<Reply> {
    explorer(&app.config.env().path_local)
}

// ------------------------------------------------------------------------------------ updates

fn updater<'a>(app: &'a App, log: &'a dyn Fn(&str)) -> Updater<'a> {
    let settings = update::Settings {
        channel: app.config.get_str("SELECTED_RELEASE_CHANNEL"),
        version: app.config.get_str("VERSION"),
        ui_language: app.config.get_str("UI_LANGUAGE"),
        path_local: app.config.env().path_local.clone(),
    };
    Updater { http: &app.model.http, settings, log }
}

fn print_log(line: &str) {
    ipc::log(line);
}

/// checkSoftwareUpdated: pushed to the UI
pub fn check_software_updated(app: &App) -> Result<()> {
    let (available, version) = updater(app, &print_log).check_software_updated();
    app.run(200, "software_update_info", json!({"is_update_available": available, "new_version": version}))
}

pub fn list_available_releases(app: &App, _: Data) -> Result<Reply> {
    let releases = updater(app, &print_log).list_available_releases();
    Ok(Reply::ok(releases.iter().map(|r| json!({
        "tag": r.tag, "version": r.version, "is_prerelease": r.is_prerelease, "published_at": r.published_at,
    })).collect::<Vec<_>>()))
}

/// _runSoftwareUpdate on its own thread: the installer starts and the app (UI and backend) quits;
/// back here means it failed, which the UI is told
fn run_update(app: &App, edition: &'static str, endpoint: &'static str, data: Data) -> Result<Reply> {
    let target = data.filter(super::engines::truthy).map(|d| py_str(&d));
    let me = app.me();
    std::thread::spawn(move || {
        let Some(app) = me.upgrade() else { return };
        let launch = |args: &[String], cwd: &std::path::Path| {
            match std::process::Command::new(cwd.join(&args[0])).args(&args[1..]).current_dir(cwd).spawn() {
                Ok(_) => {
                    platform::terminate_parent();
                    std::process::exit(0);
                }
                Err(e) => logs::error("start the installer", &e),
            }
        };
        let result = updater(&app, &print_log).update(edition, target.as_deref(), &launch);
        if result == update::SETUP_LAUNCHED {
            return;
        }
        let code = if result == update::SETUP_VERIFY_FAILED { "UPDATE_SOFTWARE_VERIFY" } else { "UPDATE_SOFTWARE_DOWNLOAD" };
        let _ = app.run_error(endpoint, code, json!(target));
    });
    Ok(Reply::ok(true))
}

pub fn update_software(app: &App, data: Data) -> Result<Reply> {
    run_update(app, "cpu", "update_software", data)
}

pub fn update_cuda_software(app: &App, data: Data) -> Result<Reply> {
    run_update(app, "gpu", "update_cuda_software", data)
}

// ------------------------------------------------------------------------------------ weights

/// ctranslate2.Translator(path, compute_type=getBestComputeType("cpu", 0)) loads
fn ct2_loads(path: &std::path::Path) -> bool {
    let config = vrct_ct2::ModelConfig { device: "cpu".into(), device_index: 0,
                                         compute_type: crate::compute::best_compute_type("cpu", 0),
                                         inter_threads: 1, intra_threads: 0 };
    vrct_ct2::Translator::new(path, &config).is_ok()
}

/// WhisperModel(path, "cpu", 0, "int8") loads
fn whisper_loads(path: &std::path::Path) -> bool {
    vrct_whisper::WhisperModel::new(path, "cpu", 0, "int8").is_ok()
}

/// checkCTranslate2Weight: the verified marker, else whether it loads on the CPU
pub fn ctranslate2_weight_ok(app: &App, weight_type: &str) -> bool {
    let Ok(m) = weights::ctranslate2_model(weight_type) else { return false };
    weights::check(&m.dir(&app.config.env().path_local), &ct2_loads)
}

/// checkWhisperWeight
pub fn whisper_weight_ok(app: &App, weight_type: &str) -> bool {
    weights::check(&app.config.env().path_local.join("weights").join("whisper").join(weight_type), &whisper_loads)
}

/// DownloadCTranslate2 / DownloadWhisper.progressBar's throttle: at 100 %, 1 % more, or 0.5 s later
struct Progress {
    last: Mutex<(f64, Option<Instant>)>,
}

impl Progress {
    fn due(&self, progress: f64) -> bool {
        let mut last = self.last.lock().unwrap();
        let due = progress >= 1.0 || progress - last.0 >= 0.01 || last.1.is_none_or(|t| t.elapsed() >= Duration::from_millis(500));
        if due {
            *last = (progress, Some(Instant::now()));
        }
        due
    }
}

type Downloads = Mutex<HashMap<String, Arc<AtomicBool>>>;

/// A download in `Model::downloads`, taken out when it ends (a panic too); only its own entry
struct Registered<'a>(&'a Downloads, &'a str, Arc<AtomicBool>);

impl Drop for Registered<'_> {
    fn drop(&mut self) {
        let mut downloads = self.0.lock().unwrap_or_else(|e| e.into_inner());
        if downloads.get(self.1).is_some_and(|c| Arc::ptr_eq(c, &self.2)) {
            downloads.remove(self.1);
        }
    }
}

/// `run` (one download) once more while a cancel was taken back by a new request; a cancel that
/// stands takes the download out of `downloads` under the same lock (so a request after it starts
/// a new one, a request before it takes the cancel back)
fn run_until_settled(downloads: &Downloads, id: &str, cancel: &Arc<AtomicBool>,
                     mut run: impl FnMut() -> weights::Outcome) -> weights::Outcome {
    loop {
        let outcome = run();
        if outcome != weights::Outcome::Cancelled {
            return outcome;
        }
        let mut downloads = downloads.lock().unwrap();
        if cancel.load(Ordering::SeqCst) {
            if downloads.get(id).is_some_and(|c| Arc::ptr_eq(c, cancel)) {
                downloads.remove(id);
            }
            return outcome;
        }
    }
}

/// downloadCTranslate2Weight / downloadWhisperWeight of the catalog's model `weight_type`, on its
/// own thread (`wait`: on this one, at start-up, which gets how it ended).
/// Done means: finished (`wait`), started (not `wait`), or already downloading: that download goes
/// on (a cancel asked for it is taken back) and tells its end by push.
pub fn download_weight(app: &App, whisper: bool, weight_type: &str, wait: bool) -> weights::Outcome {
    let (kind, title) = if whisper { ("whisper", "Whisper") } else { ("ctranslate2", "CTranslate2") };
    let Some(m) = weights::model(weight_type).filter(|m| (m.family == weights::Family::Whisper) == whisper) else {
        logs::error(&format!("download {title} weight"), &format!("unknown weight type {weight_type}"));
        return weights::Outcome::Failed("unknown");
    };
    let cancel = Arc::new(AtomicBool::new(false));
    {
        let mut downloads = app.model.downloads.lock().unwrap();
        if let Some(running) = downloads.get(&m.id) {
            running.store(false, Ordering::SeqCst);
            return weights::Outcome::Done;
        }
        downloads.insert(m.id.clone(), cancel.clone());
    }
    let me = app.me();
    let job = move || {
        let Some(app) = me.upgrade() else { return weights::Outcome::Cancelled };
        let _registered = Registered(&app.model.downloads, &m.id, cancel.clone());
        let progress = Progress { last: Mutex::new((-1.0, None)) };
        let on_progress = |p: f64| {
            if progress.due(p) {
                ipc::print_log(&format!("{title} Weight Download Progress"), &json!(p));
                let _ = app.run(200, &format!("download_progress_{kind}_weight"), json!({"weight_type": m.id, "progress": p}));
            }
        };
        let failed = |reason: Option<&str>| {
            let code = if whisper { "WEIGHT_WHISPER_DOWNLOAD" } else { "WEIGHT_CTRANSLATE2_DOWNLOAD" };
            let mut details = json!({"weight_type": m.id});
            if let Some(reason) = reason {
                details["reason"] = json!(reason);
            }
            let reply = errors::error_response(code, Value::Null, Some(details), None);
            let _ = app.run(reply.status, &format!("error_{kind}_weight"), reply.result);
        };
        let log = |message: &str, detail: &str| ipc::print_log(message, &json!(detail));
        let endpoint = app.config.get_str("HF_ENDPOINT");
        let loads = if whisper { whisper_loads } else { ct2_loads };
        let outcome = run_until_settled(&app.model.downloads, &m.id, &cancel, || {
            weights::download_model(&app.model.http, endpoint.trim_end_matches('/'), &app.config.env().path_local, m,
                                    &loads, &cancel, &on_progress, &log)
        });
        match outcome {
            weights::Outcome::Done => {
                let ok = if whisper { whisper_weight_ok(&app, &m.id) } else { ctranslate2_weight_ok(&app, &m.id) };
                if ok {
                    let dict = format!("SELECTABLE_{}_WEIGHT_TYPE_DICT", kind.to_uppercase());
                    app.config.put_item(&dict, &m.id, json!(true));
                    let _ = app.run(200, &format!("downloaded_{kind}_weight"), json!(m.id));
                } else {
                    // the catalog's files that do not load
                    failed(None);
                }
            }
            weights::Outcome::Failed(reason) => failed(Some(reason)),
            weights::Outcome::Cancelled => ipc::log(format!("{title} weight download cancelled: {}", m.id)),
        }
        outcome
    };
    if wait {
        job()
    } else {
        std::thread::spawn(job);
        weights::Outcome::Done
    }
}

pub fn download_ctranslate2_weight(app: &App, data: Data) -> Result<Reply> {
    download_weight(app, false, &py_str(&data_or_null(data)), false);
    Ok(Reply::ok(true))
}

pub fn download_whisper_weight(app: &App, data: Data) -> Result<Reply> {
    download_weight(app, true, &py_str(&data_or_null(data)), false);
    Ok(Reply::ok(true))
}

/// The catalog: the models that can be downloaded (`size`: the bytes of all their files)
pub fn get_model_catalog(_: &App, _: Data) -> Result<Reply> {
    Ok(Reply::ok(weights::catalog().iter().map(|m| json!({
        "id": m.id, "family": m.family.name(), "size": m.size(), "license": m.license, "repo": m.weights.repo,
    })).collect::<Vec<_>>()))
}

/// (the bytes of the files under `dir`, whether one is a `.part`): a linked folder is not entered
fn folder_usage(dir: &std::path::Path) -> (u64, bool) {
    let (mut bytes, mut partial) = (0, false);
    for entry in std::fs::read_dir(dir).into_iter().flatten().flatten() {
        let Ok(kind) = entry.file_type() else { continue };
        if kind.is_dir() {
            let (b, p) = folder_usage(&entry.path());
            bytes += b;
            partial |= p;
        } else if kind.is_file() {
            bytes += entry.metadata().map(|m| m.len()).unwrap_or(0);
            partial |= entry.file_name().to_string_lossy().ends_with(".part");
        }
    }
    (bytes, partial)
}

/// The catalog's models on this PC: the bytes of their folders, installed (SELECTABLE_*_DICT),
/// a download left part way, selected, downloading
fn model_list(app: &App) -> Value {
    let root = &app.config.env().path_local;
    let downloads = app.model.downloads.lock().unwrap();
    Value::Array(weights::catalog().iter().map(|m| {
        let upper = m.family.kind().to_uppercase();
        let (bytes, partial) = folder_usage(&m.dir(root));
        json!({
            "id": m.id, "family": m.family.name(), "bytes": bytes,
            "installed": app.config.get(&format!("SELECTABLE_{upper}_WEIGHT_TYPE_DICT"))[&m.id] == json!(true),
            "partial": partial,
            "in_use": app.config.get_str(&format!("{upper}_WEIGHT_TYPE")) == m.id,
            "downloading": downloads.contains_key(&m.id),
        })
    }).collect())
}

pub fn get_model_list(app: &App, _: Data) -> Result<Reply> {
    Ok(Reply::ok(model_list(app)))
}

/// Deletes a model of the catalog (its folder, named from the catalog only): not the selected one
/// nor one downloading. Answers the model list.
pub fn delete_model(app: &App, data: Data) -> Result<Reply> {
    let data = data_or_null(data);
    let Some(m) = data.as_str().and_then(weights::model) else {
        return Ok(errors::error("WEIGHT_UNKNOWN", data));
    };
    let upper = m.family.kind().to_uppercase();
    {
        // held while deleting: no download of it starts meanwhile
        let downloads = app.model.downloads.lock().unwrap();
        if downloads.contains_key(&m.id) || app.config.get_str(&format!("{upper}_WEIGHT_TYPE")) == m.id {
            return Ok(errors::error("WEIGHT_IN_USE", data));
        }
        let dir = m.dir(&app.config.env().path_local);
        let removed = if dir.exists() { std::fs::remove_dir_all(&dir) } else { Ok(()) };
        // part of it may be gone: not installed either way
        app.config.put_item(&format!("SELECTABLE_{upper}_WEIGHT_TYPE_DICT"), &m.id, json!(false));
        if let Err(e) = removed {
            logs::error("delete weight", &format!("{}: {e}", dir.display()));
            return Ok(errors::error_response("WEIGHT_DELETE_FAILED", data, Some(json!({"error": e.to_string()})), None));
        }
    }
    ipc::log(format!("Weight deleted: {}", m.id));
    Ok(Reply::ok(model_list(app)))
}

/// Stops the download of a model (at its next chunk; the .part is kept): false when none runs
pub fn cancel_weight_download(app: &App, data: Data) -> Result<Reply> {
    let id = py_str(&data_or_null(data));
    let downloads = app.model.downloads.lock().unwrap();
    let Some(cancel) = downloads.get(&id) else { return Ok(Reply::ok(false)) };
    cancel.store(true, Ordering::SeqCst);
    Ok(Reply::ok(true))
}

/// Where the weights come from: an https origin, kept as read back (no spaces around, no "/" at
/// the end, the host in lower case)
pub fn set_hf_endpoint(app: &App, data: Data) -> Result<Reply> {
    let value = match data_or_null(data) {
        Value::String(s) => match reqwest::Url::parse(s.trim()) {
            Ok(url) if url.path() == "/" && url.query().is_none() && url.fragment().is_none() && url.username().is_empty() => {
                json!(url.origin().ascii_serialization())
            }
            _ => json!(s),
        },
        other => other,
    };
    super::basic::validated(app, "HF_ENDPOINT", value)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_model_already_downloading_or_unknown_is_not_started() {
        let app = super::super::test_app(9);
        // one running, asked to stop: asked again, the stop is taken back
        let running = Arc::new(AtomicBool::new(true));
        app.model.downloads.lock().unwrap().insert("nllb-200-distilled-600M-ct2-int8".into(), running.clone());
        assert_eq!(download_weight(&app, false, "nllb-200-distilled-600M-ct2-int8", true), weights::Outcome::Done);
        assert!(Arc::ptr_eq(&app.model.downloads.lock().unwrap()["nllb-200-distilled-600M-ct2-int8"], &running), "the running one kept");
        assert!(!running.load(Ordering::SeqCst), "its cancel taken back");
        // a Whisper model is not a CTranslate2 one
        assert_eq!(download_weight(&app, false, "base", true), weights::Outcome::Failed("unknown"));
        assert_eq!(download_weight(&app, true, "nope", true), weights::Outcome::Failed("unknown"));
        assert_eq!(app.model.downloads.lock().unwrap().len(), 1);
        ipc::take_printed();
    }

    #[test]
    fn a_model_is_deleted_only_when_known_not_selected_and_not_downloading() {
        let app = super::super::test_app(9);
        let root = app.config.env().path_local.clone();
        let reply = |r: Reply| (r.status, r.result.get("error_code").cloned());
        assert_eq!(reply(delete_model(&app, Some(json!("../weights"))).unwrap()), (400, Some(json!("WEIGHT_UNKNOWN"))));
        assert_eq!(reply(delete_model(&app, Some(json!(1))).unwrap()), (400, Some(json!("WEIGHT_UNKNOWN"))));
        // selected
        assert_eq!(reply(delete_model(&app, Some(json!("base"))).unwrap()), (400, Some(json!("WEIGHT_IN_USE"))));
        // downloading
        app.model.downloads.lock().unwrap().insert("tiny".into(), Arc::default());
        assert_eq!(reply(delete_model(&app, Some(json!("tiny"))).unwrap()), (400, Some(json!("WEIGHT_IN_USE"))));
        assert!(cancel_weight_download(&app, Some(json!("tiny"))).unwrap().result == json!(true));
        assert!(app.model.downloads.lock().unwrap()["tiny"].load(std::sync::atomic::Ordering::SeqCst));
        assert!(cancel_weight_download(&app, Some(json!("small"))).unwrap().result == json!(false));
        app.model.downloads.lock().unwrap().clear();
        // a model there and not selected: its folder goes, the dict says false
        let dir = root.join("weights/whisper/tiny");
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join("model.bin.part"), b"xx").unwrap();
        app.config.put_item("SELECTABLE_WHISPER_WEIGHT_TYPE_DICT", "tiny", json!(true));
        let tiny = |list: &Value| list.as_array().unwrap().iter().find(|m| m["id"] == "tiny").unwrap().clone();
        let before = model_list(&app);
        assert_eq!(tiny(&before), json!({"id": "tiny", "family": "whisper", "bytes": 2, "installed": true, "partial": true,
                                         "in_use": false, "downloading": false}));
        let after = delete_model(&app, Some(json!("tiny"))).unwrap();
        assert_eq!(after.status, 200);
        assert_eq!((tiny(&after.result)["installed"].clone(), tiny(&after.result)["bytes"].clone()), (json!(false), json!(0)));
        assert!(!dir.exists() && root.join("weights/whisper").exists());
        // not there: fine
        assert_eq!(delete_model(&app, Some(json!("tiny"))).unwrap().status, 200);
        // a file that cannot go (held open without sharing): an error with the OS's, not installed any more
        let small = root.join("weights/whisper/small");
        std::fs::create_dir_all(&small).unwrap();
        use std::os::windows::fs::OpenOptionsExt;
        let held = std::fs::File::options().create(true).write(true).truncate(true).share_mode(0).open(small.join("model.bin")).unwrap();
        app.config.put_item("SELECTABLE_WHISPER_WEIGHT_TYPE_DICT", "small", json!(true));
        let failed = delete_model(&app, Some(json!("small"))).unwrap();
        assert_eq!((failed.status, failed.result["error_code"].clone()), (400, json!("WEIGHT_DELETE_FAILED")));
        assert!(failed.result["details"]["error"].as_str().is_some_and(|e| !e.is_empty()), "{}", failed.result);
        assert_eq!(app.config.get("SELECTABLE_WHISPER_WEIGHT_TYPE_DICT")["small"], json!(false));
        drop(held);
        ipc::take_printed();
    }

    #[test]
    fn a_cancel_taken_back_runs_the_download_again_and_one_that_stands_takes_it_out() {
        let downloads: Downloads = Mutex::default();
        let cancel = Arc::new(AtomicBool::new(false));
        downloads.lock().unwrap().insert("tiny".into(), cancel.clone());
        // stopped, then asked again before it ended: once more
        let mut runs = 0;
        let outcome = run_until_settled(&downloads, "tiny", &cancel, || {
            runs += 1;
            if runs == 1 {
                cancel.store(true, Ordering::SeqCst);
                cancel.store(false, Ordering::SeqCst);
                weights::Outcome::Cancelled
            } else {
                weights::Outcome::Done
            }
        });
        assert_eq!((outcome, runs), (weights::Outcome::Done, 2));
        assert!(downloads.lock().unwrap().contains_key("tiny"), "taken out by its Registered, not here");
        // a cancel that stands: out of the table at once
        cancel.store(true, Ordering::SeqCst);
        assert_eq!(run_until_settled(&downloads, "tiny", &cancel, || weights::Outcome::Cancelled), weights::Outcome::Cancelled);
        assert!(downloads.lock().unwrap().is_empty());
        // another download of the same model in the table is not taken out
        let other = Arc::new(AtomicBool::new(false));
        downloads.lock().unwrap().insert("tiny".into(), other.clone());
        run_until_settled(&downloads, "tiny", &cancel, || weights::Outcome::Cancelled);
        assert!(Arc::ptr_eq(&downloads.lock().unwrap()["tiny"], &other));
    }

    #[test]
    fn after_a_cancel_a_new_request_downloads_again_and_tells_its_end() {
        let app_cell: Arc<std::sync::OnceLock<std::sync::Weak<App>>> = Arc::default();
        let (cell, requests) = (app_cell.clone(), Arc::new(std::sync::atomic::AtomicUsize::new(0)));
        let counted = requests.clone();
        let root = super::super::test_server(move |_| {
            // the first request is cancelled while it comes, the next one is not found
            if counted.fetch_add(1, Ordering::SeqCst) == 0 {
                let app = cell.get().unwrap().upgrade().unwrap();
                assert_eq!(cancel_weight_download(&app, Some(json!("tiny"))).unwrap().result, json!(true));
                return (200, vec![b'x'; 10]);
            }
            (404, b"not found".to_vec())
        });
        let app = super::super::test_app_with(9, crate::net::Http::redirected(&root).unwrap());
        app_cell.set(app.me()).unwrap();
        ipc::take_printed();
        assert_eq!(download_weight(&app, true, "tiny", true), weights::Outcome::Cancelled);
        let printed = ipc::take_printed();
        assert!(!printed.iter().any(|p| p["endpoint"].as_str().is_some_and(|e| e.contains("weight") && !e.contains("progress"))),
                "a cancel tells nothing: {printed:?}");
        assert!(app.model.downloads.lock().unwrap().is_empty());
        // asked again: it runs, and its end comes (here the failure, with the model and why)
        assert_eq!(download_weight(&app, true, "tiny", true), weights::Outcome::Failed("network"));
        let printed = ipc::take_printed();
        let error = printed.iter().find(|p| p["endpoint"] == "/run/error_whisper_weight").unwrap_or_else(|| panic!("{printed:?}"));
        assert_eq!(error["status"], json!(400));
        assert_eq!(error["result"]["error_code"], json!("WEIGHT_WHISPER_DOWNLOAD"));
        assert_eq!(error["result"]["data"], Value::Null);
        assert_eq!(error["result"]["details"], json!({"weight_type": "tiny", "reason": "network"}));
        assert_eq!(requests.load(Ordering::SeqCst), 2);
    }

    #[test]
    fn hf_endpoint_is_kept_as_read_back() {
        let app = super::super::test_app(9);
        assert_eq!(set_hf_endpoint(&app, Some(json!("  https://HF-Mirror.com/  "))).unwrap().result, json!("https://hf-mirror.com"));
        assert_eq!(set_hf_endpoint(&app, Some(json!("https://example.com:443"))).unwrap().result, json!("https://example.com"));
        let bad = set_hf_endpoint(&app, Some(json!("https://example.com/x"))).unwrap();
        assert_eq!((bad.status, bad.result["data"].clone()), (400, json!("https://example.com/x")));
        assert_eq!(app.config.get("HF_ENDPOINT"), json!("https://example.com"));
        ipc::take_printed();
    }

    #[test]
    fn the_catalog_answers_the_sizes_and_licenses() {
        let catalog = get_model_catalog(&super::super::test_app(9), None).unwrap().result;
        let nllb = catalog.as_array().unwrap().iter().find(|m| m["id"] == "nllb-200-distilled-600M-ct2-int8").unwrap();
        assert_eq!((nllb["family"].clone(), nllb["license"].clone()), (json!("nllb"), json!("CC-BY-NC-4.0")));
        // the weights and the tokenizer
        assert!(nllb["size"].as_u64().unwrap() > 622_595_991 + 17_331_176);
        assert_eq!(catalog.as_array().unwrap().len(), 14);
    }

    #[test]
    fn unique_as_python() {
        assert_eq!(unique(&json!(["test", "テスト", "test"])).unwrap(), [json!("test"), json!("テスト")]);
        assert_eq!(unique(&json!("aba")).unwrap(), [json!("a"), json!("b")]);
        assert_eq!(unique(&json!([1, true, 1.0, 2])).unwrap(), [json!(1), json!(2)]);
        assert!(unique(&json!([[1]])).is_err());
        assert!(unique(&json!(null)).is_err());
        assert!(unique(&json!({"a": 1})).is_err());
    }
}
