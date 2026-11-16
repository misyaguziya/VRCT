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
use vrct_overlay::overlay::{Event, Overlay, Settings, PANEL_FORM_HISTORY as HISTORY};
use vrct_overlay::pose::{launcher_nearest_in_reach, launcher_out_of_reach};
use vrct_overlay::shortcut::Shortcut;

type Data = Option<Value>;

const SMALL: &str = "small";
const LARGE: &str = "large";
const PANEL: &str = "panel";
const LAUNCHER: &str = "launcher";
const POPUP: &str = "popup";
const KEYBOARD: &str = "keyboard";
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
        locked: v.get("locked").and_then(Value::as_bool).unwrap_or_default(),
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

/// The log window's form now (OVERLAY_VR_PANEL_FORM)
fn panel_form(config: &crate::config::Config) -> String {
    config.get_str("OVERLAY_VR_PANEL_FORM")
}

/// A form's settings with its lock: the history's are OVERLAY_VR_PANEL_SETTINGS and _LOCKED, a
/// subtitle's its part of OVERLAY_VR_SUBTITLE_SETTINGS
fn form_settings(config: &crate::config::Config, form: &str) -> Value {
    if form == HISTORY {
        let mut settings = config.get("OVERLAY_VR_PANEL_SETTINGS");
        settings["locked"] = json!(config.get_bool("OVERLAY_VR_PANEL_LOCKED"));
        settings
    } else {
        config.get("OVERLAY_VR_SUBTITLE_SETTINGS")[form].clone()
    }
}

/// Some of a form's settings saved (the rest kept); a subtitle's are told to the UI
fn save_form_settings(app: &App, form: &str, mut values: Map<String, Value>) -> Result<()> {
    if form != HISTORY {
        app.config.set("OVERLAY_VR_SUBTITLE_SETTINGS", json!({form: values}))?;
        return app.run(200, "overlay_vr_subtitle_settings", app.config.get("OVERLAY_VR_SUBTITLE_SETTINGS"));
    }
    if let Some(locked) = values.remove("locked") {
        app.config.set("OVERLAY_VR_PANEL_LOCKED", locked)?;
    }
    if !values.is_empty() {
        app.config.set("OVERLAY_VR_PANEL_SETTINGS", merged(app, "OVERLAY_VR_PANEL_SETTINGS", &values))?;
    }
    Ok(())
}

/// A value of the current form's settings
fn form_value(app: &App, key: &str) -> Value {
    form_settings(&app.config, &panel_form(&app.config)).get(key).cloned().unwrap_or(Value::Null)
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
                               display_duration: 5.0, fadeout_duration: 0.0, panel_size: None, locked: false };
        // the keyboard: as wide as it was last made in VR (0.6 m at first: its keys about 3.6 cm wide, 72 px of
        // 1200: 15 keys a row, the arrows in the bottom one). Its place is in front of the eyes each time it opens
        let keyboard = Settings { ui_scaling: config.get("KEYBOARD_WIDTH").as_f64().unwrap_or(0.6), opacity: config.get("KEYBOARD_OPACITY").as_f64().unwrap_or(1.0), ..popup.clone() };
        // the log window at its form's place and size (its lock is panel_locked, not the settings')
        let form = panel_form(config);
        let panel = settings_of(&form_settings(config, &form));
        let sizes = vec![
            (SMALL.into(), settings_of(&config.get("OVERLAY_SMALL_LOG_SETTINGS"))),
            (LARGE.into(), large),
            (PANEL.into(), Settings { locked: false, ..panel.clone() }),
            (LAUNCHER.into(), settings_of(&launcher)),
            (POPUP.into(), popup),
            (KEYBOARD.into(), keyboard),
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
        let locked = panel.locked;
        overlay.set_panel_form(&form, panel, locked);
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
        // {"x", "y", "second": the other hand's {"x", "y"} or null}; null when none points at it
        Event::Pointer(xy, second) => app.run(200, "vr_panel_pointer", xy.map_or(Value::Null, |(x, y)| {
            json!({"x": x, "y": y, "second": second.map(|(x, y)| json!({"x": x, "y": y}))})
        })),
        Event::PanelOutOfView(out) => app.run(200, "vr_panel_log_out_of_view", json!(out)),
        Event::LauncherIntro(intro) => app.run(200, "vr_panel_launcher_intro", json!(intro.name())),
        Event::Position { size, settings, form } => position_changed(app, &size, form.as_deref(), position_of(&settings)),
        // when it was made (ms): the VR view opens / closes the keyboard, and ignores an old one
        // sent again when it opens anew
        Event::Shortcut => app.run(200, "vr_panel_keyboard_shortcut", json!(chrono_ms())),
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

/// _onOverlayPositionChanged: a window moved / resized in VR is saved and told to the UI (the log
/// window to the form it was moved in, told only if that is still the form shown)
fn position_changed(app: &App, size: &str, form: Option<&str>, mut position: Map<String, Value>) -> Result<()> {
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
            let current = panel_form(&app.config);
            let form = form.unwrap_or(current.as_str());
            let tracker = position.get("tracker").cloned().unwrap_or(Value::Null);
            save_form_settings(app, form, position)?;
            if form != current {
                return Ok(());
            }
            app.run(200, "overlay_vr_panel_anchor", tracker)
        }
        LAUNCHER => {
            app.config.set("OVERLAY_VR_LAUNCHER_SETTINGS", merged(app, "OVERLAY_VR_LAUNCHER_SETTINGS", &position))?;
            app.run(200, "overlay_vr_launcher_hand", position.get("tracker").cloned().unwrap_or(Value::Null))
        }
        // the keyboard: its width kept for the next start
        KEYBOARD if scaling > 0.0 => app.config.set("KEYBOARD_WIDTH", json!(vrct_overlay::pose::round_to(scaling, 3))).map_err(Into::into),
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
    // always sent (idempotent): `now` is the overlay's last published copy, which lags behind queued
    // commands (stopped overlay, or a toggle back within one frame), so a difference test could drop the OFF
    o.update_locked(size, wanted.locked);
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
    o.set_panel_locked(form_value(app, "locked") == json!(true));
    o.set_keyboard_locked(app.config.get_bool("KEYBOARD_LOCKED"));
    o.set_laser_pitch(app.config.get("OVERLAY_VR_LASER_PITCH").as_f64().unwrap_or(vrct_overlay::overlay::LASER_PITCH_UP_DEG));
    o.set_shortcut(shortcut_of(app));
    o.set_launcher_auto_hide(app.config.get_bool("OVERLAY_VR_LAUNCHER_AUTO_HIDE"));
    // the VR UI's keyboard: its dictionaries made ready (once; not stopped when it goes off)
    if app.config.get_bool("OVERLAY_VR_PANEL") {
        super::keyboard::start(app);
    }
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
        // the VR UI gone: its keyboard with it
        if !on {
            super::keyboard::hidden(app);
        }
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

/// The current form's lock
pub fn get_overlay_vr_panel_locked(app: &App, _: Data) -> Result<Reply> {
    Ok(Reply::ok(form_value(app, "locked")))
}

fn set_panel_locked(app: &App, locked: bool) -> Result<Reply> {
    let mut values = Map::new();
    values.insert("locked".into(), json!(locked));
    save_form_settings(app, &panel_form(&app.config), values)?;
    overlay(app).set_panel_locked(locked);
    get_overlay_vr_panel_locked(app, None)
}

pub fn set_enable_overlay_vr_panel_locked(app: &App, _: Data) -> Result<Reply> {
    set_panel_locked(app, true)
}

pub fn set_disable_overlay_vr_panel_locked(app: &App, _: Data) -> Result<Reply> {
    set_panel_locked(app, false)
}

/// The log window's form: "history" (the log) or a subtitle ("multi_line", "single_line"). Changed:
/// the window goes to that form's place, size and lock, and its anchor, lock and opacity are told
pub fn set_overlay_vr_panel_form(app: &App, data: Data) -> Result<Reply> {
    let before = panel_form(&app.config);
    let reply = super::basic::validated(app, "OVERLAY_VR_PANEL_FORM", data.unwrap_or(Value::Null))?;
    let form = panel_form(&app.config);
    if form != before {
        let settings = settings_of(&form_settings(&app.config, &form));
        let locked = settings.locked;
        overlay(app).set_panel_form(&form, settings, locked);
        app.run(200, "overlay_vr_panel_anchor", form_value(app, "tracker"))?;
        app.run(200, "overlay_vr_panel_locked", form_value(app, "locked"))?;
        app.run(200, "overlay_vr_panel_opacity", form_value(app, "opacity"))?;
    }
    Ok(reply)
}

/// The subtitle forms' settings, some forms and keys at a time. The shown form's display time,
/// fade, opacity and lock go to the overlay at once (its place and size when it is shown again)
pub fn set_overlay_vr_subtitle_settings(app: &App, data: Data) -> Result<Reply> {
    let reply = super::basic::validated(app, "OVERLAY_VR_SUBTITLE_SETTINGS", data.unwrap_or(Value::Null))?;
    let form = panel_form(&app.config);
    if form != HISTORY && reply.status == 200 {
        let s = settings_of(&form_settings(&app.config, &form));
        let o = overlay(app);
        o.update_display_duration(PANEL, s.display_duration);
        o.update_fadeout_duration(PANEL, s.fadeout_duration);
        o.update_opacity(PANEL, s.opacity, true);
        o.set_panel_locked(s.locked);
        drop(o);
        app.run(200, "overlay_vr_panel_locked", json!(s.locked))?;
        app.run(200, "overlay_vr_panel_opacity", json!(s.opacity))?;
    }
    Ok(reply)
}

/// The VR view drew the log window's new content: shown once captured (a subtitle's display time starts)
pub fn vr_panel_log_rendered(app: &App, _: Data) -> Result<Reply> {
    overlay(app).reveal_panel();
    Ok(Reply::ok(true))
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

/// setVrPanelWindows: {"log", "popup", "keyboard"}, anything but true is false
pub fn set_vr_panel_windows(app: &App, data: Data) -> Result<Reply> {
    let data = data.unwrap_or(Value::Null);
    let on = |key: &str| data.get(key) == Some(&json!(true));
    let (log, popup, keyboard) = (on("log"), on("popup"), on("keyboard"));
    overlay(app).set_vr_windows(log, popup, keyboard);
    if !keyboard {
        super::keyboard::hidden(app);
    }
    Ok(Reply::ok(json!({"log": log, "popup": popup, "keyboard": keyboard})))
}

pub fn recall_vr_panel_log(app: &App, _: Data) -> Result<Reply> {
    overlay(app).recall_panel();
    Ok(Reply::ok(true))
}

/// The keyboard in front of the eyes (the launcher's keyboard button held)
pub fn recall_vr_panel_keyboard(app: &App, _: Data) -> Result<Reply> {
    overlay(app).recall_keyboard();
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

/// What the current form follows
pub fn get_overlay_vr_panel_anchor(app: &App, _: Data) -> Result<Reply> {
    Ok(Reply::ok(form_value(app, "tracker")))
}

/// setOverlayVrPanelAnchor: moved on the overlay's thread; the result comes as overlay_vr_panel_anchor
pub fn set_overlay_vr_panel_anchor(app: &App, data: Data) -> Result<Reply> {
    let data = data.unwrap_or(Value::Null);
    let Some(anchor) = data.as_str().filter(|a| PANEL_ANCHORS.contains(a)) else {
        return Ok(errors::error("VALIDATION_CONFIG_VALUE_INVALID", form_value(app, "tracker")));
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

/// The current form's opacity
pub fn get_overlay_vr_panel_opacity(app: &App, _: Data) -> Result<Reply> {
    Ok(Reply::ok(form_value(app, "opacity")))
}

/// setOverlayVrPanelOpacity: 0.2–1.0 (below it the window could not be found again in VR), the
/// current form's (a subtitle's as far as it has faded)
pub fn set_overlay_vr_panel_opacity(app: &App, data: Data) -> Result<Reply> {
    let (low, high) = vrct_overlay::layout::PANEL_OPACITY_RANGE;
    let Some(opacity) = data.as_ref().and_then(py_float).filter(|o| (low..=high).contains(o)) else {
        return Ok(errors::error("VALIDATION_CONFIG_VALUE_INVALID", form_value(app, "opacity")));
    };
    let form = panel_form(&app.config);
    let mut values = Map::new();
    values.insert("opacity".into(), json!(vrct_overlay::pose::round_to(opacity, 2)));
    save_form_settings(app, &form, values)?;
    overlay(app).update_opacity(PANEL, form_value(app, "opacity").as_f64().unwrap_or(1.0), form != HISTORY);
    Ok(Reply::ok(form_value(app, "opacity")))
}

pub fn get_keyboard_opacity(app: &App, _: Data) -> Result<Reply> {
    current(app, "KEYBOARD_OPACITY")
}

/// The VR keyboard's opacity: 0.2–1.0 (as the log window's)
pub fn set_keyboard_opacity(app: &App, data: Data) -> Result<Reply> {
    let rounded = data.as_ref().and_then(py_float).map_or(Value::Null, |o| json!(vrct_overlay::pose::round_to(o, 2)));
    let reply = super::basic::validated(app, "KEYBOARD_OPACITY", rounded)?;
    overlay(app).update_opacity(KEYBOARD, app.config.get("KEYBOARD_OPACITY").as_f64().unwrap_or(1.0), false);
    Ok(reply)
}

pub fn get_keyboard_locked(app: &App, _: Data) -> Result<Reply> {
    current(app, "KEYBOARD_LOCKED")
}

/// The keyboard pinned: not grabbed (moved) in VR
fn set_keyboard_locked(app: &App, locked: bool) -> Result<Reply> {
    app.config.set("KEYBOARD_LOCKED", json!(locked))?;
    overlay(app).set_keyboard_locked(locked);
    current(app, "KEYBOARD_LOCKED")
}

pub fn set_enable_keyboard_locked(app: &App, _: Data) -> Result<Reply> {
    set_keyboard_locked(app, true)
}

pub fn set_disable_keyboard_locked(app: &App, _: Data) -> Result<Reply> {
    set_keyboard_locked(app, false)
}

pub fn get_overlay_vr_laser_pitch(app: &App, _: Data) -> Result<Reply> {
    current(app, "OVERLAY_VR_LASER_PITCH")
}

/// The lasers' tilt up from the controllers' tips: -30–30 degrees (applied at once)
pub fn set_overlay_vr_laser_pitch(app: &App, data: Data) -> Result<Reply> {
    let rounded = data.as_ref().and_then(py_float).map_or(Value::Null, |d| json!(vrct_overlay::pose::round_to(d, 1)));
    let reply = super::basic::validated(app, "OVERLAY_VR_LASER_PITCH", rounded)?;
    overlay(app).set_laser_pitch(app.config.get("OVERLAY_VR_LASER_PITCH").as_f64().unwrap_or(vrct_overlay::overlay::LASER_PITCH_UP_DEG));
    Ok(reply)
}

fn shortcut_of(app: &App) -> Shortcut {
    Shortcut::from_name(&app.config.get_str("KEYBOARD_SHORTCUT")).unwrap_or_default()
}

pub fn get_keyboard_shortcut(app: &App, _: Data) -> Result<Reply> {
    current(app, "KEYBOARD_SHORTCUT")
}

/// The controller shortcut that opens / closes the keyboard: "off", "stick_double", "menu_long" or
/// "menu_double" (applied at once)
pub fn set_keyboard_shortcut(app: &App, data: Data) -> Result<Reply> {
    let reply = super::basic::validated(app, "KEYBOARD_SHORTCUT", data.unwrap_or(Value::Null))?;
    overlay(app).set_shortcut(shortcut_of(app));
    Ok(reply)
}

/// The time now in ms since 1970
fn chrono_ms() -> u64 {
    std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map_or(0, |d| d.as_millis() as u64)
}

/// The controller bindings of VRCT's VR UI opened in SteamVR on the desktop (to change them, or for a
/// controller without default bindings). {"status": "requested" / "not_running" / "not_ready" (the VR
/// UI has not set up its actions) / "failed"}. Never starts SteamVR
pub fn steamvr_bindings(_: &App, _: Data) -> Result<Reply> {
    Ok(Reply::ok(json!({"status": binding_status(vrct_openvr::is_steamvr_running(), open_bindings)})))
}

fn binding_status(running: bool, open: impl FnOnce() -> Result<bool>) -> &'static str {
    if !running {
        return "not_running";
    }
    match open() {
        Ok(true) => "requested",
        Ok(false) => "not_ready",
        Err(e) => {
            logs::error("SteamVR bindings", &format!("{e:#}"));
            "failed"
        }
    }
}

/// Through the overlay's session, once it has set up its actions (else SteamVR would open bindings
/// of an app without them)
fn open_bindings() -> Result<bool> {
    let Some(session) = vrct_openvr::acquire_existing() else { return Ok(false) };
    let input = session.input()?;
    if input.action_set_handle("/actions/main").unwrap_or(0) == 0 {
        return Ok(false);
    }
    input.open_binding_ui()?;
    Ok(true)
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


#[cfg(test)]
mod bindings_tests {
    #[test]
    fn bindings_do_not_start_steamvr_and_tell_readiness() {
        assert_eq!(super::binding_status(false, || panic!("SteamVR must not be started")), "not_running");
        assert_eq!(super::binding_status(true, || Ok(false)), "not_ready");
        assert_eq!(super::binding_status(true, || Ok(true)), "requested");
        assert_eq!(super::binding_status(true, || Err(anyhow::anyhow!("disconnected"))), "failed");
    }
    #[test]
    fn the_keyboard_width_made_in_vr_is_kept() {
        let app = super::super::test_app(0);
        let position = |w: f64| serde_json::json!({"ui_scaling": w, "tracker": "Playspace"}).as_object().unwrap().clone();
        super::position_changed(&app, super::KEYBOARD, None, position(0.84567)).unwrap();
        assert_eq!(app.config.get("KEYBOARD_WIDTH"), serde_json::json!(0.846));
        // outside the widths a grab can make: refused, kept as it was
        assert!(super::position_changed(&app, super::KEYBOARD, None, position(5.0)).is_err());
        assert_eq!(app.config.get("KEYBOARD_WIDTH"), serde_json::json!(0.846));
    }
}

#[cfg(test)]
mod panel_form_tests {
    use super::*;
    use crate::ipc::take_printed;

    /// The pushes printed since the last call: (name after /run/, result)
    fn pushes() -> Vec<(String, Value)> {
        take_printed().into_iter().filter_map(|p| {
            let endpoint = p["endpoint"].as_str()?.strip_prefix("/run/")?.to_string();
            Some((endpoint, p["result"].clone()))
        }).collect()
    }

    #[test]
    fn the_history_answers_as_before() {
        let app = super::super::test_app(0);
        let panel = app.config.get("OVERLAY_VR_PANEL_SETTINGS");
        assert_eq!(get_overlay_vr_panel_anchor(&app, None).unwrap().result, panel["tracker"]);
        assert_eq!(get_overlay_vr_panel_opacity(&app, None).unwrap().result, panel["opacity"]);
        assert_eq!(get_overlay_vr_panel_locked(&app, None).unwrap().result, json!(false));
        assert_eq!(set_enable_overlay_vr_panel_locked(&app, None).unwrap().result, json!(true));
        assert_eq!(app.config.get("OVERLAY_VR_PANEL_LOCKED"), json!(true));
        assert_eq!(set_overlay_vr_panel_opacity(&app, Some(json!(0.5))).unwrap().result, json!(0.5));
        assert_eq!(app.config.get("OVERLAY_VR_PANEL_SETTINGS")["opacity"], json!(0.5));
        // the subtitles untouched
        assert_eq!(app.config.get("OVERLAY_VR_SUBTITLE_SETTINGS"), *crate::config::default_of("OVERLAY_VR_SUBTITLE_SETTINGS").unwrap());
    }

    #[test]
    fn each_form_keeps_its_own_opacity_lock_and_place() {
        let app = super::super::test_app(0);
        take_printed();
        assert_eq!(set_overlay_vr_panel_form(&app, Some(json!("single_line"))).unwrap().result, json!("single_line"));
        assert_eq!(pushes(), vec![("overlay_vr_panel_anchor".into(), json!("HMD")), ("overlay_vr_panel_locked".into(), json!(true)),
                                  ("overlay_vr_panel_opacity".into(), json!(1.0))]);
        // the same form again: nothing told
        set_overlay_vr_panel_form(&app, Some(json!("single_line"))).unwrap();
        assert!(pushes().is_empty());
        // saved to a subtitle form: the subtitle settings told each time
        set_overlay_vr_panel_opacity(&app, Some(json!(0.6))).unwrap();
        assert_eq!(set_disable_overlay_vr_panel_locked(&app, None).unwrap().result, json!(false));
        let told: Vec<String> = pushes().into_iter().map(|(name, _)| name).collect();
        assert_eq!(told, vec!["overlay_vr_subtitle_settings", "overlay_vr_subtitle_settings"]);
        let subtitles = app.config.get("OVERLAY_VR_SUBTITLE_SETTINGS");
        assert_eq!((subtitles["single_line"]["opacity"].clone(), subtitles["single_line"]["locked"].clone()), (json!(0.6), json!(false)));
        assert_eq!(subtitles["multi_line"]["locked"], json!(true));
        assert_eq!((app.config.get("OVERLAY_VR_PANEL_SETTINGS")["opacity"].clone(), app.config.get("OVERLAY_VR_PANEL_LOCKED")),
                   (json!(1.0), json!(false)));
        // moved in VR as single_line: saved there and told
        let moved = json!({"x_pos": 0.1, "y_pos": 0.2, "z_pos": 0.3, "x_rotation": 0.0, "y_rotation": 0.0, "z_rotation": 0.0,
                           "ui_scaling": 1.2, "tracker": "HMD", "width": 1200, "height": 400});
        take_printed();
        position_changed(&app, PANEL, Some("single_line"), moved.as_object().unwrap().clone()).unwrap();
        let told: Vec<String> = pushes().into_iter().map(|(name, _)| name).collect();
        assert_eq!(told, vec!["overlay_vr_subtitle_settings", "overlay_vr_panel_anchor"]);
        assert_eq!(app.config.get("OVERLAY_VR_SUBTITLE_SETTINGS")["single_line"]["x_pos"], json!(0.1));
        // a move made in the form before the change: saved to that form, its anchor not told
        position_changed(&app, PANEL, Some("history"), moved.as_object().unwrap().clone()).unwrap();
        assert!(pushes().is_empty());
        assert_eq!(app.config.get("OVERLAY_VR_PANEL_SETTINGS")["x_pos"], json!(0.1));
        position_changed(&app, PANEL, Some("multi_line"), moved.as_object().unwrap().clone()).unwrap();
        let told: Vec<String> = pushes().into_iter().map(|(name, _)| name).collect();
        assert_eq!(told, vec!["overlay_vr_subtitle_settings"]);
        // back to the history: its own values
        set_overlay_vr_panel_form(&app, Some(json!("history"))).unwrap();
        assert_eq!(get_overlay_vr_panel_opacity(&app, None).unwrap().result, json!(1.0));
        assert_eq!(get_overlay_vr_panel_anchor(&app, None).unwrap().result, json!("HMD"));
    }

    #[test]
    fn a_part_of_the_subtitle_settings_keeps_the_rest() {
        let app = super::super::test_app(0);
        set_overlay_vr_subtitle_settings(&app, Some(json!({"single_line": {"x_pos": 0.4}}))).unwrap();
        let reply = set_overlay_vr_subtitle_settings(&app, Some(json!({"single_line": {"fadeout_duration": 0}}))).unwrap();
        assert_eq!((reply.result["single_line"]["x_pos"].clone(), reply.result["single_line"]["fadeout_duration"].clone()),
                   (json!(0.4), json!(0)));
        assert_eq!(reply.result["multi_line"], crate::config::default_of("OVERLAY_VR_SUBTITLE_SETTINGS").unwrap()["multi_line"]);
        // out of range: kept as it was (as a value of another type), the rest taken
        let reply = set_overlay_vr_subtitle_settings(&app, Some(json!({"single_line": {
            "opacity": 0.1, "display_duration": -1, "ui_scaling": 5.0, "width": 2000, "height": 100, "y_pos": 0.3}}))).unwrap();
        let s = &reply.result["single_line"];
        assert_eq!((s["opacity"].clone(), s["display_duration"].clone(), s["ui_scaling"].clone(), s["width"].clone(), s["height"].clone(), s["y_pos"].clone()),
                   (json!(1.0), json!(5), json!(1.0), json!(1200), json!(180), json!(0.3)));
        let reply = set_overlay_vr_subtitle_settings(&app, Some(json!({"single_line": {"opacity": 0.2, "height": 120, "ui_scaling": 3}}))).unwrap();
        let s = &reply.result["single_line"];
        assert_eq!((s["opacity"].clone(), s["height"].clone(), s["ui_scaling"].clone()), (json!(0.2), json!(120), json!(3.0)));
        // an unknown form or key is refused
        assert_ne!(set_overlay_vr_subtitle_settings(&app, Some(json!({"triple_line": {}}))).unwrap().status, 200);
        assert_ne!(set_overlay_vr_subtitle_settings(&app, Some(json!({"single_line": {"colour": 1}}))).unwrap().status, 200);
    }

    #[test]
    fn an_unknown_form_is_refused() {
        let app = super::super::test_app(0);
        let reply = set_overlay_vr_panel_form(&app, Some(json!("triple_line"))).unwrap();
        assert_eq!(reply, crate::errors::error("VALIDATION_CONFIG_VALUE_INVALID", json!("triple_line")));
        assert_eq!(app.config.get("OVERLAY_VR_PANEL_FORM"), json!("history"));
    }
}
