//! The VR overlays (controller.py / model.py with vrct-overlay): the small and large logs, the VR
//! UI (launcher, log window, temporary window), and what moving them in VR saves.
use super::{current, App};
use crate::errors;
use crate::ipc::{self, Reply};
use crate::logs;
use crate::pyjson::py_float;
use anyhow::{anyhow, Result};
use serde_json::{json, Map, Value};
use std::sync::Mutex;
use vrct_overlay::image::{Image, OverlayImage, Token};
use vrct_overlay::layout::{validate_tooltip, Layout, Region};
use vrct_overlay::overlay::{Event, Overlay, Settings};
use vrct_overlay::pose::{launcher_nearest_in_reach, launcher_out_of_reach};

type Data = Option<Value>;

const SMALL: &str = "small";
const LARGE: &str = "large";
const PANEL: &str = "panel";
const LAUNCHER: &str = "launcher";
const POPUP: &str = "popup";
const POSITION_KEYS: [&str; 6] = ["x_pos", "y_pos", "z_pos", "x_rotation", "y_rotation", "z_rotation"];
const PANEL_ANCHORS: [&str; 4] = ["Playspace", "LeftHand", "RightHand", "HMD"];
/// the large log's overlay is this part of its setting's width (Model.init)
const LARGE_SCALE: f64 = 0.25;

/// DEFAULT_OVERLAY_VR_LAUNCHER_SETTINGS: the setting's default (native/data/config_schema.json), where
/// "reset the launcher" also goes back to
fn default_launcher() -> Value {
    crate::config::default_of("OVERLAY_VR_LAUNCHER_SETTINGS").cloned().expect("OVERLAY_VR_LAUNCHER_SETTINGS has a default")
}

fn num(v: &Value, key: &str) -> f64 {
    v.get(key).and_then(Value::as_f64).unwrap_or_default()
}

/// An overlay settings dict as the overlay takes it
fn settings_of(v: &Value) -> Settings {
    let mut position = [0.0; 6];
    for (p, key) in position.iter_mut().zip(POSITION_KEYS) {
        *p = num(v, key);
    }
    let panel_size = match (v.get("width").and_then(Value::as_f64), v.get("height").and_then(Value::as_f64)) {
        (Some(w), Some(h)) => Some((w.round_ties_even() as u32, h.round_ties_even() as u32)),
        _ => None,
    };
    Settings {
        position,
        tracker: v.get("tracker").and_then(Value::as_str).unwrap_or("HMD").into(),
        opacity: num(v, "opacity"),
        ui_scaling: num(v, "ui_scaling"),
        display_duration: num(v, "display_duration"),
        fadeout_duration: num(v, "fadeout_duration"),
        panel_size,
    }
}

/// The position a move in VR reports (settings_dict without the opacity and durations)
fn position_of(s: &Settings) -> Map<String, Value> {
    let mut m = Map::new();
    for (p, key) in s.position.iter().zip(POSITION_KEYS) {
        m.insert(key.into(), json!(p));
    }
    m.insert("ui_scaling".into(), json!(s.ui_scaling));
    m.insert("tracker".into(), json!(s.tracker));
    if let Some((w, h)) = s.panel_size {
        m.insert("width".into(), json!(w));
        m.insert("height".into(), json!(h));
    }
    m
}

/// vrLayoutToJson
fn layout_json(layout: &Layout, tooltip_epoch: u64) -> Value {
    let regions: Map<String, Value> = Region::ALL.iter().map(|r| (r.name().to_string(), json!(layout.region(*r)))).collect();
    json!({"atlas": [layout.atlas.0, layout.atlas.1], "regions": regions, "tooltip_epoch": tooltip_epoch})
}

/// The overlay and the log images (Model.init's part)
pub struct Overlays {
    pub overlay: Mutex<Overlay>,
    pub image: Mutex<OverlayImage>,
    fonts: std::path::PathBuf,
}

impl Overlays {
    /// The overlays from the settings (not started). A launcher saved out of the wrist's reach is
    /// pulled in first.
    pub fn new(config: &crate::config::Config, fonts: std::path::PathBuf, app: std::sync::Arc<std::sync::OnceLock<std::sync::Weak<App>>>) -> Self {
        let mut launcher = config.get("OVERLAY_VR_LAUNCHER_SETTINGS");
        let xyz = [num(&launcher, "x_pos"), num(&launcher, "y_pos"), num(&launcher, "z_pos")];
        if launcher_out_of_reach(xyz, num(&launcher, "ui_scaling")) {
            ipc::log("overlay: ランチャーの位置か大きさが範囲の外だったので、手首の近くへ寄せます");
            let (p, width) = launcher_nearest_in_reach(xyz, num(&launcher, "ui_scaling"));
            for (key, v) in ["x_pos", "y_pos", "z_pos"].iter().zip(p) {
                launcher[key] = json!(v);
            }
            launcher["ui_scaling"] = json!(width);
            if let Err(e) = config.set("OVERLAY_VR_LAUNCHER_SETTINGS", launcher.clone()) {
                logs::error("launcher settings", &e);
            }
        }
        let mut large = settings_of(&config.get("OVERLAY_LARGE_LOG_SETTINGS"));
        large.ui_scaling *= LARGE_SCALE;
        let popup = Settings { position: [0.0; 6], tracker: "Playspace".into(), opacity: 1.0, ui_scaling: 0.36,
                               display_duration: 5.0, fadeout_duration: 0.0, panel_size: None };
        let sizes = vec![
            (SMALL.into(), settings_of(&config.get("OVERLAY_SMALL_LOG_SETTINGS"))),
            (LARGE.into(), large),
            (PANEL.into(), settings_of(&config.get("OVERLAY_VR_PANEL_SETTINGS"))),
            (LAUNCHER.into(), settings_of(&launcher)),
            (POPUP.into(), popup),
        ];
        let events = move |event: Event| {
            if let Some(app) = app.get().and_then(|w| w.upgrade()) {
                if let Err(e) = on_event(&app, event) {
                    logs::error("overlay event", &format!("{e:#}"));
                }
            }
        };
        let overlay = Overlay::new(sizes, std::sync::Arc::new(ipc::log), std::sync::Arc::new(events));
        overlay.set_launcher_defaults(settings_of(&default_launcher()));
        Self { overlay: Mutex::new(overlay), image: Mutex::new(OverlayImage::new(&fonts)), fonts }
    }
}

fn overlay(app: &App) -> std::sync::MutexGuard<'_, Overlay> {
    app.model.overlays.overlay.lock().unwrap()
}

/// The overlay's callbacks (from its thread)
fn on_event(app: &App, event: Event) -> Result<()> {
    match event {
        Event::Layout { layout, tooltip_epoch } => app.run(200, "vr_panel_layout", layout_json(&layout, tooltip_epoch)),
        Event::Pointer(xy) => app.run(200, "vr_panel_pointer", xy.map_or(Value::Null, |(x, y)| json!({"x": x, "y": y}))),
        Event::PanelOutOfView(out) => app.run(200, "vr_panel_log_out_of_view", json!(out)),
        Event::LauncherIntro(intro) => app.run(200, "vr_panel_launcher_intro", json!(intro.name())),
        Event::Position { size, settings } => position_changed(app, &size, position_of(&settings)),
    }
}

/// round(min(max(value, 0.4), 2.0), 2): the settings screen's 40–200 %
fn clamp_scaling(value: f64) -> f64 {
    vrct_overlay::pose::round_to(value.clamp(0.4, 2.0), 2)
}

fn merged(app: &App, name: &str, position: &Map<String, Value>) -> Value {
    let mut settings = app.config.get(name);
    if let Some(m) = settings.as_object_mut() {
        m.extend(position.clone());
    }
    settings
}

/// _onOverlayPositionChanged: a window moved / resized in VR is saved and told to the UI
fn position_changed(app: &App, size: &str, mut position: Map<String, Value>) -> Result<()> {
    let scaling = position.get("ui_scaling").and_then(Value::as_f64).unwrap_or_default();
    match size {
        SMALL | LARGE => {
            let (name, push) = if size == SMALL { ("OVERLAY_SMALL_LOG_SETTINGS", "overlay_small_log_settings") }
                               else { ("OVERLAY_LARGE_LOG_SETTINGS", "overlay_large_log_settings") };
            let scaling = if size == SMALL { scaling } else { scaling / LARGE_SCALE };
            position.insert("ui_scaling".into(), json!(clamp_scaling(scaling)));
            app.config.set(name, merged(app, name, &position))?;
            update_log_settings(app, size);
            app.run(200, push, app.config.get(name))
        }
        PANEL => {
            app.config.set("OVERLAY_VR_PANEL_SETTINGS", merged(app, "OVERLAY_VR_PANEL_SETTINGS", &position))?;
            app.run(200, "overlay_vr_panel_anchor", position.get("tracker").cloned().unwrap_or(Value::Null))
        }
        LAUNCHER => {
            app.config.set("OVERLAY_VR_LAUNCHER_SETTINGS", merged(app, "OVERLAY_VR_LAUNCHER_SETTINGS", &position))?;
            app.run(200, "overlay_vr_launcher_hand", position.get("tracker").cloned().unwrap_or(Value::Null))
        }
        _ => Ok(()),
    }
}

/// updateOverlaySmallLogSettings / LargeLogSettings: what differs from the overlay is sent to it
fn update_log_settings(app: &App, size: &str) {
    let config = app.config.get(if size == SMALL { "OVERLAY_SMALL_LOG_SETTINGS" } else { "OVERLAY_LARGE_LOG_SETTINGS" });
    let o = overlay(app);
    let Some(now) = o.shared().settings.into_iter().find(|(n, _)| n == size).map(|(_, s)| s) else { return };
    let wanted = settings_of(&config);
    if now.position != wanted.position || now.tracker != wanted.tracker {
        o.update_position(size, wanted.position, &wanted.tracker);
    }
    if now.display_duration != wanted.display_duration {
        o.update_display_duration(size, wanted.display_duration);
    }
    if now.fadeout_duration != wanted.fadeout_duration {
        o.update_fadeout_duration(size, wanted.fadeout_duration);
    }
    if now.opacity != wanted.opacity {
        o.update_opacity(size, wanted.opacity, true);
    }
    // the large log's overlay holds a quarter of the setting, so it always differs (as in Python)
    if now.ui_scaling != wanted.ui_scaling {
        o.update_ui_scaling(size, if size == SMALL { wanted.ui_scaling } else { wanted.ui_scaling * LARGE_SCALE });
    }
}

/// syncOverlayRunning: the overlay runs while a log or the VR UI is on
pub fn sync_overlay_running(app: &App) -> Result<()> {
    let mut o = overlay(app);
    o.set_vr_panel_enabled(app.config.get_bool("OVERLAY_VR_PANEL"));
    o.set_panel_locked(app.config.get_bool("OVERLAY_VR_PANEL_LOCKED"));
    o.set_launcher_auto_hide(app.config.get_bool("OVERLAY_VR_LAUNCHER_AUTO_HIDE"));
    if app.config.get_bool("OVERLAY_SMALL_LOG") || app.config.get_bool("OVERLAY_LARGE_LOG") || app.config.get_bool("OVERLAY_VR_PANEL") {
        o.start();
    } else {
        o.stop();
    }
    Ok(())
}

/// _bootstrapModel's callbacks told their state at once (the VR view's layout, the launcher's intro)
pub fn push_initial_state(app: &App) -> Result<()> {
    let shared = overlay(app).shared();
    app.run(200, "vr_panel_layout", layout_json(&shared.layout, shared.tooltip_epoch))?;
    app.run(200, "vr_panel_launcher_intro", json!(shared.intro.name()))
}

/// shutdownOverlay
pub fn shutdown(app: &App) {
    overlay(app).stop();
}

/// _is_overlay_available: connected to SteamVR with the overlays made
pub fn is_available(app: &App) -> bool {
    overlay(app).shared().initialized
}

fn tokens(v: &Value) -> Vec<Token> {
    v.as_array().into_iter().flatten().map(|t| Token {
        orig: t["orig"].as_str().unwrap_or_default().into(),
        hira: t["hira"].as_str().unwrap_or_default().into(),
        hepburn: t["hepburn"].as_str().unwrap_or_default().into(),
    }).collect()
}

/// The enabled languages of a languages dict
fn enabled_languages(languages: &Value) -> Vec<String> {
    languages.as_object().into_iter().flatten()
        .filter(|(_, v)| v["enable"] == json!(true))
        .filter_map(|(_, v)| v["language"].as_str().map(String::from)).collect()
}

fn show(app: &App, size: &str, image: std::io::Result<Image>) -> Result<()> {
    overlay(app).update_image(size, image?);
    Ok(())
}

/// createOverlayImageSmallLog + updateOverlaySmallLog (`message` None: the translations only)
#[allow(clippy::too_many_arguments)]
pub fn small_log(app: &App, message: Option<&str>, language: Option<&str>, translation: &[String], your_languages: &Value,
                 translit_message: &Value, translit_translation: &Value) -> Result<()> {
    let translit_translation: Vec<Vec<Token>> = match translit_translation.as_array() {
        Some(a) => a.iter().map(tokens).collect(),
        None => vec![vec![]; translation.len()],
    };
    let image = app.model.overlays.image.lock().unwrap().small_log(message.unwrap_or_default(), language.unwrap_or_default(),
        translation, &enabled_languages(your_languages), &tokens(translit_message), &translit_translation);
    show(app, SMALL, image)
}

/// createOverlayImageLargeLog + updateOverlayLargeLog
#[allow(clippy::too_many_arguments)]
pub fn large_log(app: &App, direction: &str, message: Option<&str>, own_language: Option<&str>, translation: &[String],
                 languages: &Value, translit_message: &Value, translit_translation: &Value) -> Result<()> {
    let translit_translation: Vec<Vec<Token>> = translit_translation.as_array().into_iter().flatten().map(tokens).collect();
    let image = app.model.overlays.image.lock().unwrap().large_log(direction, message, own_language.unwrap_or_default(),
        translation, &enabled_languages(languages), &tokens(translit_message), &translit_translation);
    show(app, LARGE, image)
}

/// The UI language's font for a message from the UI (createOverlayImageSmallMessage)
fn ui_font_language(app: &App) -> &'static str {
    match app.config.get_str("UI_LANGUAGE").as_str() {
        "jp" => "Japanese",
        "ko" => "Korean",
        "zh-Hans" => "Chinese Simplified",
        "zh-Hant" => "Chinese Traditional",
        _ => "Default",
    }
}

// ---------------------------------------------------------------------------------- handlers

/// sendTextOverlay: a message from the UI on the logs that are on
pub fn send_text_overlay(app: &App, data: Data) -> Result<Reply> {
    let data = data.unwrap_or(Value::Null);
    let message = data.as_str().ok_or_else(|| anyhow!("the overlay text is not a string"))?;
    let language = ui_font_language(app);
    if app.config.get_bool("OVERLAY_SMALL_LOG") && is_available(app) {
        let image = app.model.overlays.image.lock().unwrap().small_log(message, language, &[], &[], &[], &[]);
        show(app, SMALL, image)?;
    }
    if app.config.get_bool("OVERLAY_LARGE_LOG") && is_available(app) {
        // createOverlayImageLargeMessage: on its own image, the message five times over
        let mut image = OverlayImage::new(&app.model.overlays.fonts);
        for _ in 0..2 {
            image.large_log("send", Some(message), language, &[], &[], &[], &[])?;
            image.large_log("receive", Some(message), language, &[], &[], &[], &[])?;
        }
        show(app, LARGE, image.large_log("send", Some(message), language, &[], &[], &[], &[]))?;
    }
    Ok(Reply::ok(data))
}

fn log_switch(app: &App, name: &str, size: &str, on: bool) -> Result<Reply> {
    if app.config.get(name) == json!(!on) {
        if !on {
            overlay(app).clear_image(size);
        }
        app.config.set(name, json!(on))?;
        sync_overlay_running(app)?;
    }
    current(app, name)
}

pub fn set_enable_overlay_small_log(app: &App, _: Data) -> Result<Reply> {
    log_switch(app, "OVERLAY_SMALL_LOG", SMALL, true)
}

pub fn set_disable_overlay_small_log(app: &App, _: Data) -> Result<Reply> {
    log_switch(app, "OVERLAY_SMALL_LOG", SMALL, false)
}

pub fn set_enable_overlay_large_log(app: &App, _: Data) -> Result<Reply> {
    log_switch(app, "OVERLAY_LARGE_LOG", LARGE, true)
}

pub fn set_disable_overlay_large_log(app: &App, _: Data) -> Result<Reply> {
    log_switch(app, "OVERLAY_LARGE_LOG", LARGE, false)
}

fn panel_switch(app: &App, on: bool) -> Result<Reply> {
    if app.config.get("OVERLAY_VR_PANEL") == json!(!on) {
        app.config.set("OVERLAY_VR_PANEL", json!(on))?;
        sync_overlay_running(app)?;
    }
    current(app, "OVERLAY_VR_PANEL")
}

pub fn set_enable_overlay_vr_panel(app: &App, _: Data) -> Result<Reply> {
    panel_switch(app, true)
}

pub fn set_disable_overlay_vr_panel(app: &App, _: Data) -> Result<Reply> {
    panel_switch(app, false)
}

fn log_settings(app: &App, name: &str, size: &str, data: Data) -> Result<Reply> {
    app.config.set(name, data.unwrap_or(Value::Null))?;
    update_log_settings(app, size);
    current(app, name)
}

pub fn set_overlay_small_log_settings(app: &App, data: Data) -> Result<Reply> {
    log_settings(app, "OVERLAY_SMALL_LOG_SETTINGS", SMALL, data)
}

pub fn set_overlay_large_log_settings(app: &App, data: Data) -> Result<Reply> {
    log_settings(app, "OVERLAY_LARGE_LOG_SETTINGS", LARGE, data)
}

pub fn set_enable_overlay_vr_panel_locked(app: &App, _: Data) -> Result<Reply> {
    app.config.set("OVERLAY_VR_PANEL_LOCKED", json!(true))?;
    overlay(app).set_panel_locked(true);
    current(app, "OVERLAY_VR_PANEL_LOCKED")
}

pub fn set_disable_overlay_vr_panel_locked(app: &App, _: Data) -> Result<Reply> {
    app.config.set("OVERLAY_VR_PANEL_LOCKED", json!(false))?;
    overlay(app).set_panel_locked(false);
    current(app, "OVERLAY_VR_PANEL_LOCKED")
}

pub fn set_enable_overlay_vr_launcher_auto_hide(app: &App, _: Data) -> Result<Reply> {
    app.config.set("OVERLAY_VR_LAUNCHER_AUTO_HIDE", json!(true))?;
    overlay(app).set_launcher_auto_hide(true);
    current(app, "OVERLAY_VR_LAUNCHER_AUTO_HIDE")
}

pub fn set_disable_overlay_vr_launcher_auto_hide(app: &App, _: Data) -> Result<Reply> {
    app.config.set("OVERLAY_VR_LAUNCHER_AUTO_HIDE", json!(false))?;
    overlay(app).set_launcher_auto_hide(false);
    current(app, "OVERLAY_VR_LAUNCHER_AUTO_HIDE")
}

pub fn set_enable_overlay_vr_tooltip(app: &App, _: Data) -> Result<Reply> {
    app.config.set("OVERLAY_VR_TOOLTIP", json!(true))?;
    current(app, "OVERLAY_VR_TOOLTIP")
}

pub fn set_disable_overlay_vr_tooltip(app: &App, _: Data) -> Result<Reply> {
    app.config.set("OVERLAY_VR_TOOLTIP", json!(false))?;
    current(app, "OVERLAY_VR_TOOLTIP")
}

/// setVrPanelWindows: {"log", "popup"}, anything but true is false
pub fn set_vr_panel_windows(app: &App, data: Data) -> Result<Reply> {
    let data = data.unwrap_or(Value::Null);
    let (log, popup) = (data.get("log") == Some(&json!(true)), data.get("popup") == Some(&json!(true)));
    overlay(app).set_vr_windows(log, popup);
    Ok(Reply::ok(json!({"log": log, "popup": popup})))
}

pub fn recall_vr_panel_log(app: &App, _: Data) -> Result<Reply> {
    overlay(app).recall_panel();
    Ok(Reply::ok(true))
}

/// resetVrLauncher: the launcher back to its defaults (to the wrist when in VR)
pub fn reset_vr_launcher(app: &App, _: Data) -> Result<Reply> {
    app.config.set("OVERLAY_VR_LAUNCHER_SETTINGS", default_launcher())?;
    overlay(app).reset_launcher(false);
    app.run(200, "overlay_vr_launcher_hand", app.config.get("OVERLAY_VR_LAUNCHER_SETTINGS")["tracker"].clone())?;
    Ok(Reply::ok(true))
}

fn setting_of(app: &App, name: &str, key: &str) -> Value {
    app.config.get(name).get(key).cloned().unwrap_or(Value::Null)
}

pub fn get_overlay_vr_panel_anchor(app: &App, _: Data) -> Result<Reply> {
    Ok(Reply::ok(setting_of(app, "OVERLAY_VR_PANEL_SETTINGS", "tracker")))
}

/// setOverlayVrPanelAnchor: moved on the overlay's thread; the result comes as overlay_vr_panel_anchor
pub fn set_overlay_vr_panel_anchor(app: &App, data: Data) -> Result<Reply> {
    let data = data.unwrap_or(Value::Null);
    let Some(anchor) = data.as_str().filter(|a| PANEL_ANCHORS.contains(a)) else {
        return Ok(errors::error("VALIDATION_CONFIG_VALUE_INVALID", setting_of(app, "OVERLAY_VR_PANEL_SETTINGS", "tracker")));
    };
    overlay(app).request_anchor(anchor);
    Ok(Reply::ok(data))
}

pub fn get_overlay_vr_launcher_hand(app: &App, _: Data) -> Result<Reply> {
    Ok(Reply::ok(setting_of(app, "OVERLAY_VR_LAUNCHER_SETTINGS", "tracker")))
}

/// setOverlayVrLauncherHand: the position mirrored for the other hand (mirrorHandPosition)
pub fn set_overlay_vr_launcher_hand(app: &App, data: Data) -> Result<Reply> {
    let data = data.unwrap_or(Value::Null);
    let Some(hand) = data.as_str().filter(|h| ["LeftHand", "RightHand"].contains(h)) else {
        return Ok(errors::error("VALIDATION_CONFIG_VALUE_INVALID", setting_of(app, "OVERLAY_VR_LAUNCHER_SETTINGS", "tracker")));
    };
    let mut launcher = app.config.get("OVERLAY_VR_LAUNCHER_SETTINGS");
    if launcher["tracker"] != json!(hand) {
        for key in ["x_pos", "y_rotation", "z_rotation"] {
            launcher[key] = json!(-num(&launcher, key));
        }
        launcher["tracker"] = json!(hand);
        app.config.set("OVERLAY_VR_LAUNCHER_SETTINGS", launcher)?;
        let s = settings_of(&app.config.get("OVERLAY_VR_LAUNCHER_SETTINGS"));
        overlay(app).update_position(LAUNCHER, s.position, &s.tracker);
    }
    Ok(Reply::ok(setting_of(app, "OVERLAY_VR_LAUNCHER_SETTINGS", "tracker")))
}

/// setOverlayVrPanelFontSize: an int 14–28 (only the VR view uses it)
pub fn set_overlay_vr_panel_font_size(app: &App, data: Data) -> Result<Reply> {
    match data.as_ref().and_then(Value::as_i64).filter(|v| (14..=28).contains(v)) {
        Some(size) if data.as_ref().is_some_and(|d| !d.is_boolean()) => {
            app.config.set("OVERLAY_VR_PANEL_FONT_SIZE", json!(size))?;
            current(app, "OVERLAY_VR_PANEL_FONT_SIZE")
        }
        _ => Ok(errors::error("VALIDATION_CONFIG_VALUE_INVALID", app.config.get("OVERLAY_VR_PANEL_FONT_SIZE"))),
    }
}

pub fn get_overlay_vr_panel_opacity(app: &App, _: Data) -> Result<Reply> {
    Ok(Reply::ok(setting_of(app, "OVERLAY_VR_PANEL_SETTINGS", "opacity")))
}

/// setOverlayVrPanelOpacity: 0.2–1.0 (below it the window could not be found again in VR)
pub fn set_overlay_vr_panel_opacity(app: &App, data: Data) -> Result<Reply> {
    let Some(opacity) = data.as_ref().and_then(py_float).filter(|o| (0.2..=1.0).contains(o)) else {
        return Ok(errors::error("VALIDATION_CONFIG_VALUE_INVALID", setting_of(app, "OVERLAY_VR_PANEL_SETTINGS", "opacity")));
    };
    let mut panel = app.config.get("OVERLAY_VR_PANEL_SETTINGS");
    panel["opacity"] = json!(vrct_overlay::pose::round_to(opacity, 2));
    app.config.set("OVERLAY_VR_PANEL_SETTINGS", panel)?;
    overlay(app).update_opacity(PANEL, num(&app.config.get("OVERLAY_VR_PANEL_SETTINGS"), "opacity"), false);
    Ok(Reply::ok(setting_of(app, "OVERLAY_VR_PANEL_SETTINGS", "opacity")))
}

/// getVrPanelLayout: the layout the VR view draws (the overlay's)
pub fn get_vr_panel_layout(app: &App, _: Data) -> Result<Reply> {
    let shared = overlay(app).shared();
    Ok(Reply::ok(layout_json(&shared.layout, shared.tooltip_epoch)))
}

/// setVrPanelTooltip: a checked tooltip request from the VR view
pub fn set_vr_panel_tooltip(app: &App, data: Data) -> Result<Reply> {
    let data = data.unwrap_or(Value::Null);
    match validate_tooltip(&data) {
        Ok(tooltip) => {
            overlay(app).set_tooltip(tooltip);
            Ok(Reply::ok(data))
        }
        Err(_) => Ok(errors::error("VALIDATION_CONFIG_VALUE_INVALID", Value::Null)),
    }
}

/// setVrPanelLayoutRendered: [width, height] of the log the VR view drew the new layout with
pub fn set_vr_panel_layout_rendered(app: &App, data: Data) -> Result<Reply> {
    let data = data.unwrap_or(Value::Null);
    let size = data.as_array().filter(|a| a.len() == 2 && a.iter().all(|v| v.is_i64() || v.is_u64())).map(|a| (a[0].as_i64(), a[1].as_i64()));
    let Some((Some(w), Some(h))) = size else {
        return Ok(errors::error("VALIDATION_CONFIG_VALUE_INVALID", Value::Null));
    };
    let (w, h) = (u32::try_from(w)?, u32::try_from(h)?);
    overlay(app).set_layout_rendered((w, h));
    Ok(Reply::ok(data))
}

