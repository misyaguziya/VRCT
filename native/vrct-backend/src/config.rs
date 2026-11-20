//! The settings (config.py: Config; docs/rust_backend_design_2026-10-11.md §4.2).
//!
//! The 156 properties, their order, kinds, types, how they are saved and their defaults come from
//! native/data/config_schema.json (written from config.py by native/reference/export_config_schema.py);
//! only the checks are here, by property name. Values are kept as the JSON the UI and config.json
//! use, with Python's semantics: an `int` property takes a bool too (isinstance), None passes the
//! type check, a check that raises rejects.
//!
//! config.json: the serialized properties in their declared order, json.dump(indent=4,
//! ensure_ascii=False), written to a temporary file then renamed. A change is saved 2 s after the
//! last one (debounce) or at once (immediate_save).
use crate::{logs, pyjson};
use serde_json::{json, Map, Value};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Condvar, Mutex, OnceLock};
use std::time::{Duration, Instant};

const SCHEMA: &str = include_str!("../../data/config_schema.json");
const DEBOUNCE: Duration = Duration::from_secs(2);
/// The suffixes a beta / release-candidate version has (the installer's .onInit decides the same way)
const BETA_MARKERS: [&str; 2] = ["-beta", "-rc"];
/// The audio hosts of the Python backend's PortAudio: the Rust backend has WASAPI only, they move there
const PORTAUDIO_HOSTS: [&str; 4] = ["MME", "Windows DirectSound", "Windows WDM-KS", "Windows WASAPI"];
pub const RUST_HOST_NAME: &str = "Windows WASAPI";

#[derive(Clone, Copy, Debug, PartialEq)]
enum Type {
    Bool,
    Int,
    Float,
    Str,
    Dict,
    List,
}

/// A property of the schema
#[derive(Debug)]
pub struct Prop {
    pub name: String,
    validated: bool,
    types: Vec<Type>,
    /// a fixed list of allowed values, or a check (by name, in `allowed`)
    allowed_list: Option<Vec<Value>>,
    has_allowed: bool,
    pub readonly: bool,
    pub serialize: bool,
    pub immediate_save: bool,
    /// None: depends on the PC (Env)
    default: Option<Value>,
}

fn schema() -> &'static (Vec<Prop>, HashMap<String, usize>) {
    static SCHEMA_PROPS: OnceLock<(Vec<Prop>, HashMap<String, usize>)> = OnceLock::new();
    SCHEMA_PROPS.get_or_init(|| {
        let v: Value = serde_json::from_str(SCHEMA).expect("config_schema.json");
        let props: Vec<Prop> = v["properties"].as_array().unwrap().iter().map(|p| {
            let types = p["type"].as_array().map(|t| t.iter().map(|n| match n.as_str().unwrap() {
                "bool" => Type::Bool,
                "int" => Type::Int,
                "float" => Type::Float,
                "str" => Type::Str,
                "dict" => Type::Dict,
                "list" => Type::List,
                other => panic!("config_schema.json: type {other}"),
            }).collect()).unwrap_or_default();
            Prop {
                name: p["name"].as_str().unwrap().into(),
                validated: p["kind"] == "validated",
                types,
                allowed_list: p["allowed"].as_array().cloned(),
                has_allowed: p["allowed"] == "callable",
                readonly: p["readonly"].as_bool().unwrap_or(false),
                serialize: p["serialize"].as_bool().unwrap_or(true),
                immediate_save: p["immediate_save"].as_bool().unwrap_or(false),
                default: p.get("default").cloned(),
            }
        }).collect();
        let index = props.iter().enumerate().map(|(i, p)| (p.name.clone(), i)).collect();
        (props, index)
    })
}

pub fn props() -> &'static [Prop] {
    &schema().0
}

/// The schema's default of `name` (None: no such property, or the default depends on the PC)
pub fn default_of(name: &str) -> Option<&'static Value> {
    let (props, index) = schema();
    props[*index.get(name)?].default.as_ref()
}

/// The microphones by host and the speakers, for the device checks (the device manager's lists)
#[derive(Clone, Debug, Default)]
pub struct DeviceLists {
    pub mic: Vec<(String, Vec<String>)>,
    pub speaker: Vec<String>,
}

/// What the defaults and checks need from the PC
pub struct Env {
    /// config.json, logs/ and the weights are here (the executable's folder)
    pub path_local: PathBuf,
    /// getComputeDeviceList(): CPU first
    pub compute_devices: Vec<Value>,
    /// the default microphone (host, device) and speaker
    pub default_mic: (String, String),
    pub default_speaker: String,
    pub devices: Arc<dyn Fn() -> DeviceLists + Send + Sync>,
    /// transcription_lang (language -> country -> engine -> code), for the language checks
    pub transcription_lang: Value,
    /// a new WEBSOCKET_AUTH_TOKEN (secrets.token_urlsafe(32))
    pub new_token: fn() -> String,
}

/// A value the check rejected (ConfigValidationError): which property and the value
#[derive(Clone, Debug, PartialEq)]
pub struct Rejected {
    pub name: String,
    pub value: Value,
}

impl std::fmt::Display for Rejected {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "Invalid value for {}: {}", self.name, pyjson::repr(&self.value))
    }
}

impl std::error::Error for Rejected {}

struct Inner {
    env: Env,
    values: Mutex<Vec<Value>>,
    /// when the debounced save is due
    save_at: Mutex<Option<Instant>>,
    save_due: Condvar,
    file_lock: Mutex<()>,
}

/// The settings (cheap to clone, shared)
#[derive(Clone)]
pub struct Config(Arc<Inner>);

// ------------------------------------------------------------------------------------- Python semantics

/// isinstance(value, types): a bool is an int too; None always passes (ManagedProperty)
fn is_instance(value: &Value, types: &[Type]) -> bool {
    types.iter().any(|t| match t {
        Type::Bool => value.is_boolean(),
        Type::Int => value.is_boolean() || value.as_number().is_some_and(|n| !n.is_f64()),
        Type::Float => value.as_number().is_some_and(|n| n.is_f64()),
        Type::Str => value.is_string(),
        Type::Dict => value.is_object(),
        Type::List => value.is_array(),
    })
}

/// A number as Python compares it (True == 1)
fn py_number(v: &Value) -> Option<f64> {
    match v {
        Value::Bool(b) => Some(if *b { 1.0 } else { 0.0 }),
        Value::Number(n) => n.as_f64(),
        _ => None,
    }
}

/// Python's ==
pub fn py_eq(a: &Value, b: &Value) -> bool {
    match (a, b) {
        (Value::Array(x), Value::Array(y)) => x.len() == y.len() && x.iter().zip(y).all(|(a, b)| py_eq(a, b)),
        (Value::Object(x), Value::Object(y)) => x.len() == y.len() && x.iter().all(|(k, v)| y.get(k).is_some_and(|w| py_eq(v, w))),
        _ => match (py_number(a), py_number(b)) {
            (Some(x), Some(y)) => x == y,
            _ => a == b,
        },
    }
}

fn contains(list: &Value, value: &Value) -> bool {
    match list {
        Value::Array(items) => items.iter().any(|i| py_eq(i, value)),
        // `in` a dict's keys
        Value::Object(map) => value.as_str().is_some_and(|k| map.contains_key(k)),
        _ => false,
    }
}

fn is_int(v: &Value) -> bool {
    is_instance(v, &[Type::Int])
}

fn is_number(v: &Value) -> bool {
    is_instance(v, &[Type::Int, Type::Float])
}

/// float(v)
fn to_float(v: &Value) -> Value {
    json!(py_number(v).unwrap_or(0.0))
}

// ------------------------------------------------------------------------------------- the checks

/// The values the checks read (`inst.X`)
pub struct View<'a> {
    values: &'a [Value],
    env: &'a Env,
}

impl View<'_> {
    pub fn get(&self, name: &str) -> &Value {
        &self.values[schema().1[name]]
    }
}

/// The allowed-values checks (ManagedProperty's `allowed` callables). None: no such check.
fn allowed(name: &str, v: &Value, c: &View) -> Option<bool> {
    let in_list = |list: &str| contains(c.get(list), v);
    // _allowed_in_populated: an empty / unset list allows anything, as does None
    let in_populated = |list: &str| {
        let l = c.get(list);
        l.as_array().is_none_or(|a| a.is_empty()) || v.is_null() || contains(l, v)
    };
    let number_in = |low: f64, high: f64| py_number(v).is_some_and(|n| low <= n && n <= high);
    Some(match name {
        "SEND_MESSAGE_BUTTON_TYPE" => in_list("SEND_MESSAGE_BUTTON_TYPE_LIST"),
        "UI_LANGUAGE" => in_list("SELECTABLE_UI_LANGUAGE_LIST"),
        "WEBSOCKET_HOST" => v.as_str().and_then(|s| s.parse::<std::net::IpAddr>().ok()).is_some_and(|ip| !ip.is_unspecified()),
        "SELECTED_TAB_NO" => in_list("SELECTABLE_TAB_NO_LIST"),
        "SELECTED_TRANSCRIPTION_ENGINE" => in_list("SELECTABLE_TRANSCRIPTION_ENGINE_LIST"),
        "SELECTED_RELEASE_CHANNEL" => in_list("SELECTABLE_RELEASE_CHANNEL_LIST"),
        "CTRANSLATE2_WEIGHT_TYPE" => in_list("SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_LIST"),
        "WHISPER_WEIGHT_TYPE" => in_list("SELECTABLE_WHISPER_WEIGHT_TYPE_LIST"),
        "SELECTED_PLAMO_MODEL" => in_populated("SELECTABLE_PLAMO_MODEL_LIST"),
        "SELECTED_GEMINI_MODEL" => in_populated("SELECTABLE_GEMINI_MODEL_LIST"),
        "SELECTED_OPENAI_MODEL" => in_populated("SELECTABLE_OPENAI_MODEL_LIST"),
        "SELECTED_GROQ_MODEL" => in_populated("SELECTABLE_GROQ_MODEL_LIST"),
        "SELECTED_OPENROUTER_MODEL" => in_populated("SELECTABLE_OPENROUTER_MODEL_LIST"),
        "SELECTED_LMSTUDIO_MODEL" => in_populated("SELECTABLE_LMSTUDIO_MODEL_LIST"),
        "SELECTED_OPENAI_COMPATIBLE_MODEL" => in_populated("SELECTABLE_OPENAI_COMPATIBLE_MODEL_LIST"),
        "SELECTED_OLLAMA_MODEL" => in_populated("SELECTABLE_OLLAMA_MODEL_LIST"),
        "SELECTED_GROQ_WHISPER_MODEL" => in_populated("SELECTABLE_GROQ_WHISPER_MODEL_LIST"),
        "SELECTED_OPENAI_WHISPER_MODEL" => in_populated("SELECTABLE_OPENAI_WHISPER_MODEL_LIST"),
        "SELECTED_CUSTOM_WHISPER_MODEL" => in_populated("SELECTABLE_CUSTOM_WHISPER_MODEL_LIST"),
        "SELECTED_DEEPGRAM_MODEL" => in_populated("SELECTABLE_DEEPGRAM_MODEL_LIST"),
        "OCR_SOURCE_LANGUAGE" => in_list("SELECTABLE_OCR_SOURCE_LANGUAGE_LIST"),
        // len(None) raises: rejected
        "OCR_WINDOW_TITLE" => v.as_str().is_some_and(|s| !s.is_empty()),
        "OCR_POLL_INTERVAL_MS" => number_in(100.0, 5000.0),
        "OCR_MIN_CONFIDENCE" => number_in(0.1, 0.99),
        "OCR_BUBBLE_MIN_TEXT_LENGTH" => number_in(1.0, 50.0),
        // the VR keyboard (below it, it could not be found again in VR)
        "KEYBOARD_OPACITY" => number_in(0.2, 1.0),
        // the keyboard's width (m) as last made in VR: the widths a grab can make (vrct-overlay)
        "KEYBOARD_WIDTH" => number_in(0.05, 3.0),
        // percent of the keys' own sound
        "KEYBOARD_KEY_SOUND_VOLUME" => number_in(0.0, 100.0),
        // the lasers tilted up from the controllers' tips (degrees), to point where VRChat's do
        "OVERLAY_VR_LASER_PITCH" => number_in(-30.0, 30.0),
        // where the weights come from (a mirror of the Hub): https only, an origin (a "/" after it is dropped where used)
        "HF_ENDPOINT" => v.as_str().and_then(|s| reqwest::Url::parse(s).ok()).is_some_and(|u| {
            u.scheme() == "https" && u.host_str().is_some() && u.username().is_empty() && u.password().is_none()
                && u.path() == "/" && u.query().is_none() && u.fragment().is_none()
        }),
        _ => return None,
    })
}

const POSITION_KEYS: [&str; 6] = ["x_pos", "y_pos", "z_pos", "x_rotation", "y_rotation", "z_rotation"];

/// _overlay_small_validator / _overlay_large_validator: the same keys; a bad entry keeps its value
fn overlay_log_settings(v: &Value, current: &Value) -> Option<Value> {
    let (map, cur) = (v.as_object()?, current.as_object()?);
    // locked was added later: a setting saved without it keeps its position, locked off
    let mut map = map.clone();
    map.entry("locked").or_insert(json!(false));
    if map.len() != cur.len() || !map.keys().all(|k| cur.contains_key(k)) {
        return None;
    }
    let mut new = cur.clone();
    for (k, x) in &map {
        let k = k.as_str();
        if (k == "locked" && x.is_boolean()) || (k == "tracker" && x.as_str().is_some_and(|t| ["HMD", "LeftHand", "RightHand"].contains(&t))) {
            new.insert(k.into(), x.clone());
        } else if (POSITION_KEYS.contains(&k) || k == "opacity" || k == "ui_scaling") && is_number(x) {
            new.insert(k.into(), to_float(x));
        } else if (k == "display_duration" || k == "fadeout_duration") && is_int(x) {
            new.insert(k.into(), x.clone());
        }
    }
    Some(Value::Object(new))
}

/// _validate_overlay_vr_window: known keys only (missing ones keep their value); Playspace too
fn overlay_vr_window(v: &Value, current: &Value) -> Option<Value> {
    let (map, cur) = (v.as_object()?, current.as_object()?);
    if !map.keys().all(|k| cur.contains_key(k)) {
        return None;
    }
    let mut new = cur.clone();
    for (k, x) in map {
        let k = k.as_str();
        if (k == "tracker" && x.as_str().is_some_and(|t| ["HMD", "LeftHand", "RightHand", "Playspace"].contains(&t)))
            || ((k == "locked" || k == "placed") && x.is_boolean())
        {
            new.insert(k.into(), x.clone());
        } else if (POSITION_KEYS.contains(&k) || k == "opacity" || k == "ui_scaling") && is_number(x) {
            new.insert(k.into(), to_float(x));
        } else if ["display_duration", "fadeout_duration", "width", "height", "font_size"].contains(&k) && is_int(x) && !x.is_boolean() {
            new.insert(k.into(), x.clone());
        }
    }
    Some(Value::Object(new))
}

/// The log window's subtitle forms: some of the forms, each with some of its keys (the others keep
/// their value: a move in VR is not undone by a change made elsewhere)
fn overlay_vr_subtitles(v: &Value, current: &Value) -> Option<Value> {
    use vrct_overlay::layout::{PANEL_OPACITY_RANGE, PANEL_SIZE_RANGE, SUBTITLE_FONT_SIZE_RANGE, SUBTITLE_MIN_HEIGHT, WIDTH_RANGE_M};
    let (map, cur) = (v.as_object()?, current.as_object()?);
    // a value out of its range keeps the old one, as one of another type does
    let in_range = |k: &str, x: &Value| {
        let Some(n) = py_number(x) else { return true };
        let ((min_w, _), (max_w, max_h)) = PANEL_SIZE_RANGE;
        match k {
            "opacity" => (PANEL_OPACITY_RANGE.0..=PANEL_OPACITY_RANGE.1).contains(&n),
            "display_duration" | "fadeout_duration" => n >= 0.0,
            // the widths a grab can make
            "ui_scaling" => (WIDTH_RANGE_M.0..=WIDTH_RANGE_M.1).contains(&n),
            "width" => (min_w as f64..=max_w as f64).contains(&n),
            "height" => (SUBTITLE_MIN_HEIGHT as f64..=max_h as f64).contains(&n),
            "font_size" => (SUBTITLE_FONT_SIZE_RANGE.0 as f64..=SUBTITLE_FONT_SIZE_RANGE.1 as f64).contains(&n),
            _ => true,
        }
    };
    let mut new = cur.clone();
    for (form, x) in map {
        let x = x.as_object()?.iter().filter(|(k, x)| in_range(k, x)).map(|(k, x)| (k.clone(), x.clone())).collect();
        new.insert(form.clone(), overlay_vr_window(&Value::Object(x), cur.get(form)?)?);
    }
    Some(Value::Object(new))
}

/// validateDictStructure: the same keys all the way down, each value of its type
fn dict_structure(v: &Value, structure: &Value) -> bool {
    let (Some(map), Some(st)) = (v.as_object(), structure.as_object()) else { return false };
    if map.len() != st.len() || !map.keys().all(|k| st.contains_key(k)) {
        return false;
    }
    st.iter().all(|(k, t)| match t {
        Value::Object(_) => dict_structure(&map[k], t),
        Value::String(t) => match t.as_str() {
            "str" => map[k].is_string(),
            "bool" => map[k].is_boolean(),
            _ => false,
        },
        _ => false,
    })
}

/// The selected languages (_selected_your_languages_validator / _selected_target_languages_validator):
/// an entry with an unknown language / country or a non-bool enable keeps its old value
fn selected_languages(v: &Value, old: &Value, lang: &Value) -> Option<Value> {
    let map = v.as_object()?;
    let mut new = Map::new();
    for (k0, v0) in map {
        // v0.items() on a non-dict raises: rejected
        let entries = v0.as_object()?;
        let mut inner = Map::new();
        for (k1, v1) in entries {
            let get = |key: &str| v1.as_object().and_then(|o| o.get(key)).cloned().unwrap_or(Value::Null);
            if !v1.is_object() {
                return None;
            }
            let (language, country, enable) = (get("language"), get("country"), get("enable"));
            let known = language.as_str().and_then(|l| lang.get(l)).is_some_and(|countries| country.as_str().is_some_and(|c| countries.get(c).is_some()));
            let entry = if known && enable.is_boolean() {
                json!({"language": language, "country": country, "enable": enable})
            } else {
                old.get(k0).and_then(|o| o.get(k1)).cloned().unwrap_or(Value::Null)
            };
            inner.insert(k1.clone(), entry);
        }
        new.insert(k0.clone(), Value::Object(inner));
    }
    Some(Value::Object(new))
}

/// The ValidatedProperty checks: the value to keep (normalized), None to reject
fn validate(name: &str, v: &Value, c: &View) -> Option<Value> {
    let current = c.get(name);
    match name {
        "MAIN_WINDOW_GEOMETRY" => {
            let (map, cur) = (v.as_object()?, current.as_object()?);
            if map.len() != cur.len() || !map.keys().all(|k| cur.contains_key(k)) {
                return None;
            }
            Some(Value::Object(map.iter().map(|(k, x)| (k.clone(), if is_int(x) { x.clone() } else { cur[k].clone() })).collect()))
        }
        "HOTKEYS" => {
            let (map, cur) = (v.as_object()?, current.as_object()?);
            if map.len() != cur.len() || !map.keys().all(|k| cur.contains_key(k)) {
                return None;
            }
            Some(Value::Object(map.iter().map(|(k, x)| {
                (k.clone(), if x.is_array() || x.is_null() { x.clone() } else { cur.get(k).cloned().unwrap_or(Value::Null) })
            }).collect()))
        }
        // the current keys only; a missing or non-str / None value keeps its value
        "AUTH_KEYS" | "TRANSCRIPTION_AUTH_KEYS" => {
            let (map, cur) = (v.as_object()?, current.as_object()?);
            Some(Value::Object(cur.iter().map(|(k, old)| {
                let x = map.get(k).filter(|x| x.is_string() || x.is_null());
                (k.clone(), x.unwrap_or(old).clone())
            }).collect()))
        }
        "SELECTED_TRANSCRIPTION_COMPUTE_TYPE" | "SELECTED_TRANSLATION_COMPUTE_TYPE" => {
            let device = if name == "SELECTED_TRANSCRIPTION_COMPUTE_TYPE" { "SELECTED_TRANSCRIPTION_COMPUTE_DEVICE" } else { "SELECTED_TRANSLATION_COMPUTE_DEVICE" };
            v.is_string().then_some(())?;
            contains(c.get(device).get("compute_types").unwrap_or(&json!([])), v).then(|| v.clone())
        }
        "OVERLAY_SMALL_LOG_SETTINGS" | "OVERLAY_LARGE_LOG_SETTINGS" => overlay_log_settings(v, current),
        "OVERLAY_VR_PANEL_SETTINGS" | "OVERLAY_VR_LAUNCHER_SETTINGS" => overlay_vr_window(v, current),
        "OVERLAY_VR_SUBTITLE_SETTINGS" => overlay_vr_subtitles(v, current),
        "SEND_MESSAGE_FORMAT_PARTS" | "RECEIVED_MESSAGE_FORMAT_PARTS" => {
            let structure = json!({"message": {"prefix": "str", "suffix": "str"}, "separator": "str",
                                   "translation": {"prefix": "str", "separator": "str", "suffix": "str"}, "translation_first": "bool"});
            dict_structure(v, &structure).then(|| v.clone())
        }
        "MIC_WORD_FILTER" => {
            let mut seen = Vec::<&str>::new();
            for s in v.as_array()?.iter().filter_map(Value::as_str) {
                if !seen.contains(&s) {
                    seen.push(s);
                }
            }
            Some(json!(seen))
        }
        "SELECTED_TRANSLATION_ENGINES" => {
            let map = v.as_object()?;
            // the list is dict_keys: `in` hashes the value, a list / dict raises
            if map.values().any(|x| x.is_array() || x.is_object()) {
                return None;
            }
            let engines = c.get("SELECTABLE_TRANSLATION_ENGINE_LIST");
            Some(Value::Object(map.iter().map(|(k, x)| {
                (k.clone(), if contains(engines, x) { x.clone() } else { current.get(k).cloned().unwrap_or(Value::Null) })
            }).collect()))
        }
        "SELECTED_YOUR_LANGUAGES" | "SELECTED_TARGET_LANGUAGES" => selected_languages(v, current, &c.env.transcription_lang),
        "SELECTED_MIC_HOST" => {
            let host = v.as_str()?;
            // the device-less state kept across a removal
            if host == "NoHost" {
                return Some(v.clone());
            }
            let hosts: Vec<String> = (c.env.devices)().mic.into_iter().map(|(h, _)| h).collect();
            if PORTAUDIO_HOSTS.contains(&host) && hosts.iter().any(|h| h == RUST_HOST_NAME) {
                return Some(json!(RUST_HOST_NAME));
            }
            hosts.iter().any(|h| h == host).then(|| v.clone())
        }
        "SELECTED_MIC_DEVICE" => {
            let device = v.as_str()?;
            if device == "NoDevice" {
                return Some(v.clone());
            }
            let host = c.get("SELECTED_MIC_HOST").as_str().unwrap_or_default().to_string();
            let names = (c.env.devices)().mic.into_iter().find(|(h, _)| *h == host).map(|(_, n)| n).unwrap_or_default();
            if names.iter().any(|n| n == device) {
                return Some(v.clone());
            }
            // an MME name is cut at 31 characters: the WASAPI device it starts
            names.into_iter().find(|n| n.starts_with(device)).map(Value::String)
        }
        "SELECTED_SPEAKER_DEVICE" => {
            let device = v.as_str()?;
            if device == "NoDevice" || (c.env.devices)().speaker.iter().any(|n| n == device) { Some(v.clone()) } else { None }
        }
        "SELECTED_TRANSLATION_COMPUTE_DEVICE" | "SELECTED_TRANSCRIPTION_COMPUTE_DEVICE" => {
            let mut device = v.clone();
            // Saved GPU selections before the vendor field were all NVIDIA.
            if device["device"] == "cuda" && device.get("vendor").is_none() {
                device["vendor"] = json!("nvidia");
            }
            c.env.compute_devices.iter().find(|d| py_eq(d, v) || py_eq(d, &device)).cloned()
        }
        _ => panic!("no check for {name}"),
    }
}

fn channel_for_version(version: &str) -> &'static str {
    if BETA_MARKERS.iter().any(|m| version.contains(m)) { "beta" } else { "stable" }
}

// ------------------------------------------------------------------------------------- the store

impl Config {
    /// init_config(): the defaults (the PC's from `env`)
    pub fn new(env: Env) -> Config {
        let token = (env.new_token)();
        let values = props().iter().map(|p| {
            // the version of this build (package.json), not the schema's copy from config.py
            if p.name == "VERSION" {
                return json!(env!("VRCT_VERSION"));
            }
            if let Some(d) = &p.default {
                return d.clone();
            }
            let local = env.path_local.to_string_lossy().into_owned();
            match p.name.as_str() {
                "PATH_LOCAL" => json!(local),
                "PATH_CONFIG" => json!(env.path_local.join("config.json").to_string_lossy()),
                "PATH_LOGS" => json!(env.path_local.join("logs").to_string_lossy()),
                "SELECTABLE_COMPUTE_DEVICE_LIST" => json!(env.compute_devices),
                "COMPUTE_MODE" => json!(match env.compute_devices.iter().find(|d| d["device"] == "cuda") {
                    Some(d) if d["vendor"] == "amd" => "amd",
                    Some(_) => "cuda",
                    None => "cpu",
                }),
                "SELECTED_TRANSLATION_COMPUTE_DEVICE" | "SELECTED_TRANSCRIPTION_COMPUTE_DEVICE" => env.compute_devices[0].clone(),
                "SELECTED_MIC_HOST" => json!(env.default_mic.0),
                "SELECTED_MIC_DEVICE" => json!(env.default_mic.1),
                "SELECTED_SPEAKER_DEVICE" => json!(env.default_speaker),
                "WEBSOCKET_AUTH_TOKEN" => json!(token),
                other => panic!("config_schema.json: no default for {other}"),
            }
        }).collect();
        let _ = std::fs::create_dir_all(env.path_local.join("logs"));
        let config = Config(Arc::new(Inner {
            env,
            values: Mutex::new(values),
            save_at: Mutex::new(None),
            save_due: Condvar::new(),
            file_lock: Mutex::new(()),
        }));
        let weak = Arc::downgrade(&config.0);
        std::thread::Builder::new().name("config_save".into()).spawn(move || Config::saver(weak)).expect("config saver");
        config
    }

    /// The debounced saves (threading.Timer)
    fn saver(inner: std::sync::Weak<Inner>) {
        loop {
            let Some(inner) = inner.upgrade() else { return };
            let mut at = inner.save_at.lock().unwrap();
            match *at {
                Some(due) if Instant::now() >= due => {
                    *at = None;
                    drop(at);
                    if let Err(e) = Config(inner).save_to_file() {
                        logs::error("saveConfigToFile", &e);
                    }
                }
                Some(due) => drop(inner.save_due.wait_timeout(at, due - Instant::now()).unwrap()),
                // woken by a save request (or once a second to notice the end)
                None => drop(inner.save_due.wait_timeout(at, Duration::from_secs(1)).unwrap()),
            }
        }
    }

    pub fn env(&self) -> &Env {
        &self.0.env
    }

    /// The value (a copy)
    pub fn get(&self, name: &str) -> Value {
        self.0.values.lock().unwrap()[schema().1[name]].clone()
    }

    pub fn get_bool(&self, name: &str) -> bool {
        self.get(name).as_bool().unwrap_or(false)
    }

    pub fn get_str(&self, name: &str) -> String {
        self.get(name).as_str().unwrap_or_default().to_string()
    }

    /// `config.NAME = value`: checked as config.py does, then saved (debounced or at once)
    pub fn set(&self, name: &str, value: Value) -> Result<(), Rejected> {
        let index = schema().1[name];
        let prop = &props()[index];
        let rejected = || Rejected { name: name.into(), value: value.clone() };
        assert!(!prop.readonly, "read-only property {name}");
        let mut values = self.0.values.lock().unwrap();
        let view = View { values: &values, env: &self.0.env };
        let stored = if prop.validated {
            validate(name, &value, &view).ok_or_else(rejected)?
        } else {
            if !prop.types.is_empty() && !value.is_null() && !is_instance(&value, &prop.types) {
                return Err(rejected());
            }
            let ok = match &prop.allowed_list {
                Some(list) => list.iter().any(|a| py_eq(a, &value)),
                None if prop.has_allowed => allowed(name, &value, &view).expect("a check for every callable allowed"),
                None => true,
            };
            if !ok {
                return Err(rejected());
            }
            value.clone()
        };
        values[index] = stored;
        drop(values);
        if prop.serialize {
            self.request_save(prop.immediate_save);
        }
        Ok(())
    }

    /// Internal state not checked (the dynamically built lists and statuses: SELECTABLE_*)
    pub fn put(&self, name: &str, value: Value) {
        self.0.values.lock().unwrap()[schema().1[name]] = value;
    }

    /// `config.NAME[key] = value` on a mutable-tracked dict (the statuses): not checked, not saved
    pub fn put_item(&self, name: &str, key: &str, value: Value) {
        let mut values = self.0.values.lock().unwrap();
        if let Some(map) = values[schema().1[name]].as_object_mut() {
            map.insert(key.into(), value);
        }
    }

    /// saveConfig: a debounced save in 2 s (pushed back by each change), or now
    pub fn request_save(&self, immediate: bool) {
        if immediate {
            *self.0.save_at.lock().unwrap() = None;
            if let Err(e) = self.save_to_file() {
                logs::error("saveConfigToFile", &e);
            }
        } else {
            *self.0.save_at.lock().unwrap() = Some(Instant::now() + DEBOUNCE);
            self.0.save_due.notify_one();
        }
    }

    /// The serialized properties, in their declared order
    pub fn serialized(&self) -> Map<String, Value> {
        let values = self.0.values.lock().unwrap();
        props().iter().zip(values.iter()).filter(|(p, _)| p.serialize && !p.readonly).map(|(p, v)| (p.name.clone(), v.clone())).collect()
    }

    pub fn path_config(&self) -> PathBuf {
        PathBuf::from(self.get_str("PATH_CONFIG"))
    }

    /// saveConfigToFile: written to config.json.tmp, synced, then renamed over config.json
    pub fn save_to_file(&self) -> std::io::Result<()> {
        let text = pyjson::dump_config(&Value::Object(self.serialized()));
        let _guard = self.0.file_lock.lock().unwrap();
        let path = self.path_config();
        let tmp = PathBuf::from(format!("{}.tmp", path.display()));
        {
            use std::io::Write;
            let mut f = std::fs::File::create(&tmp)?;
            f.write_all(text.as_bytes())?;
            f.sync_all()?;
        }
        std::fs::rename(&tmp, &path)
    }

    /// load_config(): config.json's known, saved properties through their checks (a rejected one
    /// keeps its default, logged), the release channel from the running version, the installer's
    /// UI language, then saved. A config.json that does not parse stops here, as in Python.
    pub fn load(&self) {
        let path = self.path_config();
        let text = std::fs::read_to_string(&path).unwrap_or_default();
        if !text.is_empty() {
            let data: Map<String, Value> = match serde_json::from_str(&text) {
                Ok(d) => d,
                Err(e) => {
                    logs::error("load_config", &e);
                    return;
                }
            };
            for (key, value) in data {
                let Some(&index) = schema().1.get(&key) else { continue };
                let p = &props()[index];
                if p.readonly || !p.serialize {
                    continue;
                }
                if let Err(e) = self.set(&key, value) {
                    logs::error("load_config", &e);
                }
            }
        }
        let version = self.get_str("VERSION");
        if let Err(e) = self.set("SELECTED_RELEASE_CHANNEL", json!(channel_for_version(&version))) {
            logs::error("load_config", &e);
        }
        let marker = self.0.env.path_local.join("installer_language.txt");
        if marker.is_file() {
            if let Ok(text) = std::fs::read_to_string(&marker) {
                let language = text.trim();
                if contains(&self.get("SELECTABLE_UI_LANGUAGE_LIST"), &json!(language)) {
                    let _ = self.set("UI_LANGUAGE", json!(language));
                }
            }
            if let Err(e) = std::fs::remove_file(&marker) {
                logs::error("load_config", &e);
            }
        }
        if let Err(e) = self.save_to_file() {
            logs::error("saveConfigToFile", &e);
        }
    }

    /// revalidate_selected_models: a selected model no longer in its (non-empty) list becomes the first
    pub fn revalidate_selected_models(&self) {
        for (selected, list) in [
            ("SELECTED_PLAMO_MODEL", "SELECTABLE_PLAMO_MODEL_LIST"),
            ("SELECTED_GEMINI_MODEL", "SELECTABLE_GEMINI_MODEL_LIST"),
            ("SELECTED_OPENAI_MODEL", "SELECTABLE_OPENAI_MODEL_LIST"),
            ("SELECTED_GROQ_MODEL", "SELECTABLE_GROQ_MODEL_LIST"),
            ("SELECTED_OPENROUTER_MODEL", "SELECTABLE_OPENROUTER_MODEL_LIST"),
            ("SELECTED_LMSTUDIO_MODEL", "SELECTABLE_LMSTUDIO_MODEL_LIST"),
            ("SELECTED_OPENAI_COMPATIBLE_MODEL", "SELECTABLE_OPENAI_COMPATIBLE_MODEL_LIST"),
            ("SELECTED_OLLAMA_MODEL", "SELECTABLE_OLLAMA_MODEL_LIST"),
            ("SELECTED_GROQ_WHISPER_MODEL", "SELECTABLE_GROQ_WHISPER_MODEL_LIST"),
            ("SELECTED_OPENAI_WHISPER_MODEL", "SELECTABLE_OPENAI_WHISPER_MODEL_LIST"),
            ("SELECTED_CUSTOM_WHISPER_MODEL", "SELECTABLE_CUSTOM_WHISPER_MODEL_LIST"),
            ("SELECTED_DEEPGRAM_MODEL", "SELECTABLE_DEEPGRAM_MODEL_LIST"),
        ] {
            let (current, items) = (self.get(selected), self.get(list));
            let Some(first) = items.as_array().and_then(|a| a.first()) else { continue };
            if !current.is_null() && !contains(&items, &current) {
                if let Err(e) = self.set(selected, first.clone()) {
                    logs::error("revalidate_selected_models", &e);
                }
            }
        }
    }
}

/// setupDownloadUrl's channel rule, for callers
pub fn release_channel(version: &str) -> &'static str {
    channel_for_version(version)
}

/// The folder of the running executable (PATH_LOCAL of a frozen build)
pub fn executable_dir() -> PathBuf {
    std::env::current_exe().ok().and_then(|p| p.parent().map(Path::to_path_buf)).unwrap_or_else(|| PathBuf::from("."))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn env(dir: &Path) -> Env {
        Env {
            path_local: dir.to_path_buf(),
            compute_devices: vec![json!({"device": "cpu", "device_index": 0, "device_name": "cpu", "compute_types": ["auto", "float32", "int8"]})],
            default_mic: ("Windows WASAPI".into(), "Mic A".into()),
            default_speaker: "Speaker A".into(),
            devices: Arc::new(|| DeviceLists {
                mic: vec![("Windows WASAPI".into(), vec!["Mic A".into(), "Microphone (Realtek High Definition Audio)".into()])],
                speaker: vec!["Speaker A".into()],
            }),
            transcription_lang: json!({"Japanese": {"Japan": {"Google": "ja-JP"}}, "English": {"United States": {"Google": "en-US"}}}),
            new_token: || "token".into(),
        }
    }

    #[test]
    fn gpu_mode_and_saved_selection() {
        let dir = std::env::temp_dir().join(format!("vrct-config-gpu-{}", std::process::id()));
        let old = json!({"device": "cuda", "device_index": 0, "device_name": "GPU", "compute_types": ["auto", "float32"]});
        for (vendor, mode) in [("amd", "amd"), ("nvidia", "cuda")] {
            let mut env = env(&dir);
            let mut gpu = old.clone();
            gpu["vendor"] = json!(vendor);
            env.compute_devices.push(gpu.clone());
            let config = Config::new(env);
            assert_eq!(config.get("COMPUTE_MODE"), mode);
            let key = "SELECTED_TRANSLATION_COMPUTE_DEVICE";
            assert_eq!(config.set(key, old.clone()).is_ok(), vendor == "nvidia");
            if vendor == "nvidia" {
                assert_eq!(config.get(key), gpu);
            }
        }
        let _ = std::fs::remove_dir_all(dir);
    }

    #[test]
    fn checks_like_python() {
        let dir = std::env::temp_dir().join(format!("vrct-config-test-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let c = Config::new(env(&dir));
        // isinstance(True, int)
        assert!(c.set("TRANSPARENCY", json!(true)).is_ok());
        assert!(c.set("TRANSPARENCY", json!(80.5)).is_err());
        assert!(c.set("TRANSPARENCY", Value::Null).is_ok());
        assert!(c.set("UI_LANGUAGE", json!("xx")).is_err());
        assert!(c.set("UI_LANGUAGE", json!("ja")).is_ok());
        assert!(c.set("OCR_POLL_INTERVAL_MS", json!(99)).is_err());
        assert!(c.set("OCR_POLL_INTERVAL_MS", Value::Null).is_err());
        assert!(c.set("WEBSOCKET_HOST", json!("0.0.0.0")).is_err());
        assert!(c.set("WEBSOCKET_HOST", json!("::1")).is_ok());
        // a Hub mirror: an https origin
        for ok in ["https://huggingface.co", "https://hf-mirror.com/", "https://127.0.0.1:8443"] {
            assert!(c.set("HF_ENDPOINT", json!(ok)).is_ok(), "{ok}");
        }
        for bad in [json!("http://huggingface.co"), json!("https://hf-mirror.com/x"), json!("https://a.com?b"), json!("https://a.com#b"),
                    json!("https://u:p@a.com"), json!("ftp://a.com"), json!("huggingface.co"), json!(""), json!(1), Value::Null] {
            assert!(c.set("HF_ENDPOINT", bad.clone()).is_err(), "{bad}");
        }
        assert_eq!(c.get("HF_ENDPOINT"), json!("https://127.0.0.1:8443"));
        // a bad entry keeps its old value
        c.set("MAIN_WINDOW_GEOMETRY", json!({"x_pos": 1, "y_pos": "a", "width": 2, "height": 3})).unwrap();
        assert_eq!(c.get("MAIN_WINDOW_GEOMETRY"), json!({"x_pos": 1, "y_pos": 0, "width": 2, "height": 3}));
        c.set("OVERLAY_SMALL_LOG_SETTINGS", json!({"x_pos": 1, "y_pos": 0.0, "z_pos": 0.0, "x_rotation": 0.0, "y_rotation": 0.0,
            "z_rotation": 0.0, "display_duration": 2.5, "fadeout_duration": 1, "opacity": 1, "ui_scaling": 1.0, "tracker": "Playspace"})).unwrap();
        let s = c.get("OVERLAY_SMALL_LOG_SETTINGS");
        assert_eq!((s["x_pos"].clone(), s["display_duration"].clone(), s["tracker"].clone()), (json!(1.0), json!(5), json!("HMD")));
        // a setting saved before "locked" existed keeps its position, locked off; only a bool locks
        c.set("OVERLAY_LARGE_LOG_SETTINGS", json!({"x_pos": 0.3, "y_pos": 0.0, "z_pos": 0.0, "x_rotation": 0.0, "y_rotation": 0.0,
            "z_rotation": 0.0, "display_duration": 5, "fadeout_duration": 2, "opacity": 1.0, "ui_scaling": 1.0, "tracker": "LeftHand"})).unwrap();
        let l = c.get("OVERLAY_LARGE_LOG_SETTINGS");
        assert_eq!((l["x_pos"].clone(), l["locked"].clone()), (json!(0.3), json!(false)));
        let with = |locked: Value| json!({"x_pos": 0.3, "y_pos": 0.0, "z_pos": 0.0, "x_rotation": 0.0, "y_rotation": 0.0,
            "z_rotation": 0.0, "display_duration": 5, "fadeout_duration": 2, "opacity": 1.0, "ui_scaling": 1.0, "tracker": "LeftHand", "locked": locked});
        c.set("OVERLAY_LARGE_LOG_SETTINGS", with(json!(true))).unwrap();
        assert_eq!(c.get("OVERLAY_LARGE_LOG_SETTINGS")["locked"], json!(true));
        c.set("OVERLAY_LARGE_LOG_SETTINGS", with(json!("yes"))).unwrap();
        assert_eq!(c.get("OVERLAY_LARGE_LOG_SETTINGS")["locked"], json!(true));
        assert_eq!(c.set("MIC_WORD_FILTER", json!(["a", 1, "a", "b"])), Ok(()));
        assert_eq!(c.get("MIC_WORD_FILTER"), json!(["a", "b"]));
        // the Rust backend's devices: PortAudio hosts move to WASAPI, an MME name cut at 31 characters
        c.set("SELECTED_MIC_HOST", json!("MME")).unwrap();
        assert_eq!(c.get("SELECTED_MIC_HOST"), json!("Windows WASAPI"));
        c.set("SELECTED_MIC_DEVICE", json!("Microphone (Realtek High Defini")).unwrap();
        assert_eq!(c.get("SELECTED_MIC_DEVICE"), json!("Microphone (Realtek High Definition Audio)"));
        assert!(c.set("SELECTED_SPEAKER_DEVICE", json!("nope")).is_err());
        c.set("SELECTED_YOUR_LANGUAGES", json!({"1": {"1": {"language": "English", "country": "United States", "enable": false}}})).unwrap();
        c.set("SELECTED_YOUR_LANGUAGES", json!({"1": {"1": {"language": "Klingon", "country": "x", "enable": true}}, "9": {"1": {}}})).unwrap();
        assert_eq!(c.get("SELECTED_YOUR_LANGUAGES"),
                   json!({"1": {"1": {"language": "English", "country": "United States", "enable": false}}, "9": {"1": null}}));
        c.save_to_file().unwrap();
        let saved: Value = serde_json::from_str(&std::fs::read_to_string(dir.join("config.json")).unwrap()).unwrap();
        assert_eq!(saved["UI_LANGUAGE"], json!("ja"));
        assert!(saved.get("VERSION").is_none() && saved.get("ENABLE_TRANSLATION").is_none());
        let _ = std::fs::remove_dir_all(&dir);
    }
}
