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
use std::sync::Mutex;
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
    let Ok(w) = crate::translate::ctranslate2::weight(weight_type) else { return false };
    weights::check(&app.config.env().path_local.join("weights").join("ctranslate2").join(w.directory_name), &ct2_loads)
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

/// downloadCTranslate2Weight / downloadWhisperWeight (`wait`: on this thread, at start-up)
pub fn download_weight(app: &App, whisper: bool, weight_type: &str, wait: bool) {
    let me = app.me();
    let tokenizer_weight_type = weight_type.to_string();
    let weight_type = weight_type.to_string();
    let job = move || {
        let Some(app) = me.upgrade() else { return };
        let (kind, title) = if whisper { ("whisper", "Whisper") } else { ("ctranslate2", "CTranslate2") };
        let progress = Progress { last: Mutex::new((-1.0, None)) };
        let on_progress = |p: f64| {
            if progress.due(p) {
                ipc::print_log(&format!("{title} Weight Download Progress"), &json!(p));
                let _ = app.run(200, &format!("download_progress_{kind}_weight"), json!({"weight_type": weight_type, "progress": p}));
            }
        };
        let downloaded = || {
            let ok = if whisper { whisper_weight_ok(&app, &weight_type) } else { ctranslate2_weight_ok(&app, &weight_type) };
            if ok {
                let dict = format!("SELECTABLE_{}_WEIGHT_TYPE_DICT", kind.to_uppercase());
                app.config.put_item(&dict, &weight_type, json!(true));
                let _ = app.run(200, &format!("downloaded_{kind}_weight"), json!(weight_type));
            } else {
                let code = if whisper { "WEIGHT_WHISPER_DOWNLOAD" } else { "WEIGHT_CTRANSLATE2_DOWNLOAD" };
                let _ = app.run_error(&format!("error_{kind}_weight"), code, Value::Null);
            }
        };
        let log = |message: &str, detail: &str| ipc::print_log(message, &json!(detail));
        let root = app.config.env().path_local.clone();
        let result = if whisper {
            weights::download_whisper(&app.model.http, &root, &weight_type, &whisper_loads, &on_progress, &downloaded, &log)
        } else {
            weights::download_ctranslate2(&app.model.http, &root, &weight_type, &ct2_loads, &on_progress, &downloaded, &log).map(|_| ())
        };
        if let Err(e) = result {
            logs::error(&format!("download {title} weight"), &format!("{e:#}"));
        }
    };
    if wait {
        job();
    } else {
        std::thread::spawn(job);
    }
    // the tokenizer comes with the weight (synchronously, as in Python)
    if !whisper {
        if let Err(e) = weights::download_tokenizer(&app.model.http, &app.config.env().path_local, &tokenizer_weight_type,
                                                    &|m, d| ipc::print_log(m, &json!(d))) {
            logs::error("download CTranslate2 tokenizer", &format!("{e:#}"));
        }
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

#[cfg(test)]
mod tests {
    use super::*;

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
