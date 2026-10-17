//! The VR keyboard (vrct-ime): its dictionaries made ready in the background (downloaded on the
//! first start, then built by RIME), what is typed, and where it goes: VRCT's chat box (translated,
//! as the message box sends) or pasted into VRChat's open text field.
use super::basic::validated;
use super::pipeline::{process, CHAT};
use super::{current, App};
use crate::ime_data;
use crate::ipc::{self, Reply};
use crate::logs;
use anyhow::{anyhow, bail, Result};
use serde_json::{json, Value};
use std::sync::Mutex;
use vrct_ime::input::{Input, Key, Language, State};
use vrct_ime::rime::Rime;

type Data = Option<Value>;

/// The dictionaries (Japanese and Chinese; English and Korean need none)
#[derive(Clone, Copy, Debug, PartialEq)]
enum Status {
    Preparing,
    /// downloading, 0..1
    Downloading(f64),
    /// RIME builds them (about 15 s the first time)
    Building,
    Ready,
    Failed,
}

pub struct Keyboard {
    status: Mutex<Status>,
    input: Mutex<Input<'static>>,
    /// the typing indicator is on in VRChat
    typing: Mutex<bool>,
}

impl Keyboard {
    pub fn new(config: &crate::config::Config) -> Self {
        let language = Language::from_code(&config.get_str("KEYBOARD_LANGUAGE")).unwrap_or(Language::Japanese);
        Keyboard { status: Mutex::new(Status::Preparing), input: Mutex::new(Input::new(language)), typing: Mutex::default() }
    }
}

fn keyboard(app: &App) -> &Keyboard {
    &app.model.keyboard
}

fn state_json(status: Status, s: &State, language: Language) -> Value {
    // progress: of the download, 0..1
    let (status, progress) = match status {
        Status::Preparing => ("preparing", 0.0),
        Status::Downloading(p) => ("downloading", p),
        Status::Building => ("building", 1.0),
        Status::Ready => ("ready", 1.0),
        Status::Failed => ("failed", 0.0),
    };
    json!({
        "status": status,
        "progress": progress,
        "language": language.code(),
        "text": s.text,
        "composition": s.composition.as_ref().map(|c| json!({"preedit": c.preedit, "selection": [c.selection.0, c.selection.1], "cursor": c.cursor})),
        "candidates": s.candidates,
        "highlighted": s.highlighted,
        "converting": s.converting,
        "page": s.page,
        "last_page": s.last_page,
        "syllable": s.syllable.as_ref().map(|(s, jamo)| json!({"text": s, "jamo": jamo.iter().map(char::to_string).collect::<Vec<_>>()})),
        "length": s.length,
    })
}

/// Everything the keyboard shows, after a change: VRChat's typing indicator follows whether
/// anything is typed
fn changed(app: &App, input: &Input) -> Result<Value> {
    let s = input.state();
    let typing = s.length > 0 && app.config.get_bool("KEYBOARD_TYPING_INDICATOR") && app.config.get_bool("SEND_MESSAGE_TO_VRC");
    let mut was = keyboard(app).typing.lock().unwrap();
    if *was != typing {
        app.model.osc.send_typing(typing)?;
        *was = typing;
    }
    Ok(state_json(*keyboard(app).status.lock().unwrap(), &s, input.language()))
}

fn set_status(app: &App, status: Status) {
    *keyboard(app).status.lock().unwrap() = status;
    let input = keyboard(app).input.lock().unwrap();
    let _ = app.run(200, "keyboard_state", state_json(status, &input.state(), input.language()));
}

// ------------------------------------------------------------------------------- the dictionaries

/// The dictionaries downloaded (the first time) and built, then Japanese and Chinese type
pub fn start(app: &App) {
    let me = app.me();
    std::thread::spawn(move || {
        let Some(app) = me.upgrade() else { return };
        if let Err(e) = prepare(&app) {
            logs::error("Keyboard dictionaries", &format!("{e:#}"));
            set_status(&app, Status::Failed);
        }
    });
}

fn prepare(app: &App) -> Result<()> {
    let local = app.config.env().path_local.clone();
    let resources = &app.model.resources.dir;
    if !ime_data::ready(&local, ime_data::SOURCES) {
        // a push for each percent
        let shown = Mutex::new(-1);
        let progress = |p: f64| {
            let percent = (p * 100.0) as i32;
            if std::mem::replace(&mut *shown.lock().unwrap(), percent) != percent {
                set_status(app, Status::Downloading(p));
            }
        };
        set_status(app, Status::Downloading(0.0));
        ime_data::prepare(&app.model.http, &local, ime_data::SOURCES, ime_data::GITHUB_ARCHIVES, &resources.join("rime").join("opencc"),
                          &progress, &|message, url| ipc::log(format!("{message}: {url}")))?;
    }
    set_status(app, Status::Building);
    let shared = ime_data::shared_dir(&local);
    let user = local.join("ime").join("user");
    std::fs::create_dir_all(&user)?;
    for (name, contents) in vrct_ime::setup::user_files(&shared)? {
        std::fs::write(user.join(name), contents)?;
    }
    // the sessions borrow it for as long as the app runs
    let rime: &'static Rime = Box::leak(Box::new(Rime::load(&resources.join("rime.dll"))?));
    rime.start(&shared, &user, &local.join("logs"))?;
    if !rime.deploy(false) {
        bail!("RIME could not build the dictionaries");
    }
    let session = rime.session()?;
    keyboard(app).input.lock().unwrap().attach(session, app.config.get_bool("KEYBOARD_CHINESE_SIMPLIFIED"));
    ipc::log(format!("Keyboard ready (librime {})", rime.version()));
    set_status(app, Status::Ready);
    Ok(())
}

// --------------------------------------------------------------------------------- handlers

pub fn get_keyboard_state(app: &App, _: Data) -> Result<Reply> {
    let input = keyboard(app).input.lock().unwrap();
    Ok(Reply::ok(state_json(*keyboard(app).status.lock().unwrap(), &input.state(), input.language())))
}

/// A key: one character ("a", "A" with Shift, "、"), or Backspace, Space, Enter, Left, Right,
/// PageUp, PageDown
pub fn keyboard_key(app: &App, data: Data) -> Result<Reply> {
    let name = data.as_ref().and_then(Value::as_str).ok_or_else(|| anyhow!("the key is not a string"))?;
    let key = match name {
        "Backspace" => Key::Backspace,
        "Space" => Key::Space,
        "Enter" => Key::Enter,
        "Left" => Key::Left,
        "Right" => Key::Right,
        "PageUp" => Key::PageUp,
        "PageDown" => Key::PageDown,
        _ => {
            let mut chars = name.chars();
            match (chars.next(), chars.next()) {
                (Some(c), None) => Key::Char(c),
                _ => bail!("no key {name:?}"),
            }
        }
    };
    let mut input = keyboard(app).input.lock().unwrap();
    input.key(key);
    Ok(Reply::ok(changed(app, &input)?))
}

/// The candidate at this index of the page shown
pub fn keyboard_select(app: &App, data: Data) -> Result<Reply> {
    let index = data.as_ref().and_then(Value::as_u64).ok_or_else(|| anyhow!("the index is not a number"))?;
    let mut input = keyboard(app).input.lock().unwrap();
    input.select(index as usize);
    Ok(Reply::ok(changed(app, &input)?))
}

pub fn keyboard_clear(app: &App, _: Data) -> Result<Reply> {
    let mut input = keyboard(app).input.lock().unwrap();
    input.clear();
    Ok(Reply::ok(changed(app, &input)?))
}

/// {"to": "vrct" | "paste", "id"}: the text (what is being composed included) through VRCT, as the
/// message box sends it ("message": its answer), or pasted into VRChat ("pasted": false when it
/// was only copied: no VRChat window took the focus). Nothing typed: nothing is sent.
pub fn keyboard_send(app: &App, data: Data) -> Result<Reply> {
    let data = data.unwrap_or(Value::Null);
    let to = data.get("to").and_then(Value::as_str).unwrap_or_default();
    if !["vrct", "paste"].contains(&to) {
        bail!("no destination {to:?}");
    }
    let mut input = keyboard(app).input.lock().unwrap();
    let text = input.take();
    let state = changed(app, &input)?;
    drop(input);
    let mut out = json!({"to": to, "state": state});
    if text.trim().is_empty() {
        return Ok(Reply::ok(out));
    }
    if to == "vrct" {
        out["message"] = process(app, &CHAT, &text, None, Some(data.get("id").cloned().unwrap_or(Value::Null)), None)?.unwrap_or(Value::Null);
    } else {
        let window = app.model.app_name.get();
        out["pasted"] = json!(crate::clipboard::copy_and_paste(&text, window.as_deref(), &|line| ipc::log(line)));
    }
    Ok(Reply::ok(out))
}

// --------------------------------------------------------------------------------- settings

pub fn get_keyboard_language(app: &App, _: Data) -> Result<Reply> {
    current(app, "KEYBOARD_LANGUAGE")
}

/// "ja", "en", "ko" or "zh"; what was being composed is written first
pub fn set_keyboard_language(app: &App, data: Data) -> Result<Reply> {
    let reply = validated(app, "KEYBOARD_LANGUAGE", data.unwrap_or(Value::Null))?;
    if let Some(language) = Language::from_code(&app.config.get_str("KEYBOARD_LANGUAGE")) {
        let mut input = keyboard(app).input.lock().unwrap();
        input.set_language(language);
        changed(app, &input)?;
    }
    Ok(reply)
}

fn set_simplified(app: &App, on: bool) -> Result<Reply> {
    app.config.set("KEYBOARD_CHINESE_SIMPLIFIED", json!(on))?;
    keyboard(app).input.lock().unwrap().set_simplified(on);
    current(app, "KEYBOARD_CHINESE_SIMPLIFIED")
}

pub fn get_keyboard_chinese_simplified(app: &App, _: Data) -> Result<Reply> {
    current(app, "KEYBOARD_CHINESE_SIMPLIFIED")
}

pub fn set_enable_keyboard_chinese_simplified(app: &App, _: Data) -> Result<Reply> {
    set_simplified(app, true)
}

pub fn set_disable_keyboard_chinese_simplified(app: &App, _: Data) -> Result<Reply> {
    set_simplified(app, false)
}

pub fn get_keyboard_key_sound(app: &App, _: Data) -> Result<Reply> {
    current(app, "KEYBOARD_KEY_SOUND")
}

pub fn set_enable_keyboard_key_sound(app: &App, _: Data) -> Result<Reply> {
    app.config.set("KEYBOARD_KEY_SOUND", json!(true))?;
    current(app, "KEYBOARD_KEY_SOUND")
}

pub fn set_disable_keyboard_key_sound(app: &App, _: Data) -> Result<Reply> {
    app.config.set("KEYBOARD_KEY_SOUND", json!(false))?;
    current(app, "KEYBOARD_KEY_SOUND")
}

pub fn get_keyboard_typing_indicator(app: &App, _: Data) -> Result<Reply> {
    current(app, "KEYBOARD_TYPING_INDICATOR")
}

fn set_typing_indicator(app: &App, on: bool) -> Result<Reply> {
    app.config.set("KEYBOARD_TYPING_INDICATOR", json!(on))?;
    changed(app, &keyboard(app).input.lock().unwrap())?;
    current(app, "KEYBOARD_TYPING_INDICATOR")
}

pub fn set_enable_keyboard_typing_indicator(app: &App, _: Data) -> Result<Reply> {
    set_typing_indicator(app, true)
}

pub fn set_disable_keyboard_typing_indicator(app: &App, _: Data) -> Result<Reply> {
    set_typing_indicator(app, false)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::net::UdpSocket;
    use std::time::Duration;
    use vrchat_osc::rosc::{self, OscPacket, OscType};

    fn rig() -> (std::sync::Arc<App>, UdpSocket) {
        let osc = UdpSocket::bind("127.0.0.1:0").unwrap();
        osc.set_read_timeout(Some(Duration::from_millis(100))).unwrap();
        let app = super::super::test_app(osc.local_addr().unwrap().port());
        ipc::take_printed();
        (app, osc)
    }

    /// What VRChat got: (address, first argument)
    fn osc_got(osc: &UdpSocket) -> Vec<(String, String)> {
        let mut buf = [0u8; 4096];
        let mut got = vec![];
        while let Ok(n) = osc.recv(&mut buf) {
            if let Ok((_, OscPacket::Message(m))) = rosc::decoder::decode_udp(&buf[..n]) {
                let arg = match m.args.first() {
                    Some(OscType::String(s)) => s.clone(),
                    Some(OscType::Bool(b)) => b.to_string(),
                    other => format!("{other:?}"),
                };
                got.push((m.addr, arg));
            }
        }
        got
    }

    fn keys(app: &App, keys: &[&str]) -> Value {
        keys.iter().map(|k| keyboard_key(app, Some(json!(k))).unwrap().result).last().unwrap()
    }

    #[test]
    fn typed_text_goes_through_vrct_with_the_typing_indicator() {
        let (app, osc) = rig();
        assert_eq!(set_keyboard_language(&app, Some(json!("en"))).unwrap().result, json!("en"));
        let state = keys(&app, &["H", "i", "Space", "!", "Backspace"]);
        assert_eq!((state["text"].clone(), state["length"].clone(), state["status"].clone()), (json!("Hi "), json!(3), json!("preparing")));
        assert_eq!(osc_got(&osc), [("/chatbox/typing".to_string(), "true".to_string())]);

        let sent = keyboard_send(&app, Some(json!({"to": "vrct", "id": "k1"}))).unwrap().result;
        assert_eq!(sent["message"]["id"], json!("k1"));
        assert_eq!(sent["message"]["original"]["message"], json!("Hi "));
        assert_eq!(sent["state"]["text"], json!(""));
        let got = osc_got(&osc);
        assert!(got.contains(&("/chatbox/typing".into(), "false".into())) && got.contains(&("/chatbox/input".into(), "Hi ".into())), "{got:?}");
        // nothing typed: nothing sent
        keyboard_send(&app, Some(json!({"to": "vrct"}))).unwrap();
        assert_eq!(osc_got(&osc), []);
    }

    #[test]
    fn korean_composes_and_the_settings_check_their_values() {
        let (app, osc) = rig();
        app.config.set("KEYBOARD_TYPING_INDICATOR", json!(false)).unwrap();
        set_keyboard_language(&app, Some(json!("ko"))).unwrap();
        let state = keys(&app, &["g", "k", "s"]);
        assert_eq!(state["syllable"], json!({"text": "한", "jamo": ["ㅎ", "ㅏ", "ㄴ"]}));
        assert_eq!(set_keyboard_language(&app, Some(json!("xx"))).unwrap().status, 400);
        assert_eq!(app.config.get_str("KEYBOARD_LANGUAGE"), "ko");
        // switching writes the syllable being made
        set_keyboard_language(&app, Some(json!("en"))).unwrap();
        assert_eq!(get_keyboard_state(&app, None).unwrap().result["text"], json!("한"));
        assert!(keyboard_key(&app, Some(json!("ab"))).is_err());
        assert!(keyboard_send(&app, Some(json!({"to": "elsewhere"}))).is_err());
        keyboard_clear(&app, None).unwrap();
        assert_eq!(get_keyboard_state(&app, None).unwrap().result["length"], json!(0));
        // the typing indicator is off
        assert_eq!(osc_got(&osc), []);
    }
}
