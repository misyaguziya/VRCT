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
use std::sync::{Mutex, OnceLock};
use std::time::{Duration, Instant};
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
    /// when Enter last committed a word: an Enter right after it is a double press, not a send
    committed_at: Mutex<Option<Instant>>,
    /// rime.dll loaded and started (once a process: a retry only builds again)
    rime: OnceLock<&'static Rime>,
}

/// An Enter this soon after the one that committed the word does not send
const SEND_AFTER_COMMIT: Duration = Duration::from_millis(400);

impl Keyboard {
    pub fn new(config: &crate::config::Config) -> Self {
        let language = Language::from_code(&config.get_str("KEYBOARD_LANGUAGE")).unwrap_or(Language::Japanese);
        Keyboard { status: Mutex::new(Status::Preparing), input: Mutex::new(Input::new(language)), typing: Mutex::default(),
                   committed_at: Mutex::default(), rime: OnceLock::new() }
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
/// anything is typed (not sent, as when OSC cannot send: logged, the typing goes on)
fn changed(app: &App, input: &Input) -> Value {
    let s = input.state();
    let typing = s.length > 0 && app.config.get_bool("KEYBOARD_TYPING_INDICATOR") && app.config.get_bool("SEND_MESSAGE_TO_VRC");
    set_typing(app, typing);
    state_json(*keyboard(app).status.lock().unwrap(), &s, input.language())
}

fn set_typing(app: &App, typing: bool) {
    let mut was = keyboard(app).typing.lock().unwrap();
    if *was != typing {
        if let Err(e) = app.model.osc.send_typing(typing) {
            logs::error("keyboard typing indicator", &format!("{e:#}"));
        }
        *was = typing;
    }
}

/// The keyboard closed or VRCT ends: VRChat's typing indicator off (what is typed stays)
pub fn stop_typing(app: &App) {
    set_typing(app, false);
}

fn push_state(app: &App, input: &Input) {
    let _ = app.run(200, "keyboard_state", changed(app, input));
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
    let rime = match keyboard(app).rime.get() {
        Some(rime) => *rime,
        None => {
            // the sessions borrow it for as long as the app runs
            let rime: &'static Rime = Box::leak(Box::new(Rime::load(&resources.join("rime.dll"))?));
            rime.start(&shared, &user, &local.join("logs"))?;
            *keyboard(app).rime.get_or_init(|| rime)
        }
    };
    // false: nothing changed since the last build (or it did not start): the built files tell
    rime.deploy(false);
    for schema in ["jaroomaji", "luna_pinyin"] {
        let built = user.join("build").join(format!("{schema}.prism.bin"));
        if !built.is_file() {
            bail!("RIME could not build the dictionaries ({} is missing)", built.display());
        }
    }
    let session = rime.session()?;
    keyboard(app).input.lock().unwrap().attach(session, app.config.get_bool("KEYBOARD_CHINESE_SIMPLIFIED"));
    ipc::log(format!("Keyboard ready (librime {})", rime.version()));
    set_status(app, Status::Ready);
    Ok(())
}

// --------------------------------------------------------------------------------- handlers

/// The dictionaries once more, after they failed (a press while they are being made does nothing)
pub fn keyboard_retry(app: &App, _: Data) -> Result<Reply> {
    let retry = {
        let mut status = keyboard(app).status.lock().unwrap();
        let failed = *status == Status::Failed;
        if failed {
            *status = Status::Preparing;
        }
        failed
    };
    if retry {
        start(app);
    }
    get_keyboard_state(app, None)
}

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
    if key == Key::Enter {
        let mut committed_at = keyboard(app).committed_at.lock().unwrap();
        if input.composing() {
            *committed_at = Some(Instant::now());
        } else {
            // nothing being composed: Enter sends (KEYBOARD_SEND_TO), told by keyboard_sent
            let double = committed_at.take().is_some_and(|at| at.elapsed() < SEND_AFTER_COMMIT);
            drop(committed_at);
            let text = if double { String::new() } else { input.take() };
            if text.trim().is_empty() {
                input.restore(&text);
            }
            drop(input);
            if !text.trim().is_empty() {
                send(app, text, &app.config.get_str("KEYBOARD_SEND_TO"))?;
            }
            return Ok(Reply::ok(changed(app, &keyboard(app).input.lock().unwrap())));
        }
    }
    input.key(key);
    Ok(Reply::ok(changed(app, &input)))
}

/// The candidate at this index of the page shown
pub fn keyboard_select(app: &App, data: Data) -> Result<Reply> {
    let index = data.as_ref().and_then(Value::as_u64).ok_or_else(|| anyhow!("the index is not a number"))?;
    let mut input = keyboard(app).input.lock().unwrap();
    input.select(index as usize);
    Ok(Reply::ok(changed(app, &input)))
}

pub fn keyboard_clear(app: &App, _: Data) -> Result<Reply> {
    let mut input = keyboard(app).input.lock().unwrap();
    input.clear();
    Ok(Reply::ok(changed(app, &input)))
}

/// The text taken out (Korean's syllable being made included), sent: through VRCT as the message box
/// sends it ({"to": "vrct", "message": its answer}) or pasted into VRChat ({"to": "paste", "pasted"}),
/// told by keyboard_sent. On the keyboard's ordered worker, as the keys: sends go one at a time in
/// the order typed, and the keys typed meanwhile wait (never pass them). What did not go (an error;
/// only copied: no VRChat window took the focus) is put back, so nothing typed is lost.
fn send(app: &App, text: String, to: &str) -> Result<()> {
    let put_back = || {
        let mut input = keyboard(app).input.lock().unwrap();
        input.restore(&text);
        changed(app, &input)
    };
    let mut out = json!({"to": to});
    if to == "paste" {
        let window = app.model.app_name.get();
        let pasted = crate::clipboard::copy_and_paste(&text, window.as_deref(), &|line| ipc::log(line));
        out["pasted"] = json!(pasted);
        out["state"] = if pasted { changed(app, &keyboard(app).input.lock().unwrap()) } else { put_back() };
    } else {
        match process(app, &CHAT, &text, None, None, None) {
            Ok(message) => {
                out["message"] = message.unwrap_or(Value::Null);
                out["state"] = changed(app, &keyboard(app).input.lock().unwrap());
            }
            // the text back on the keyboard, the error to the UI (500, as the message box)
            Err(e) => {
                let _ = app.run(200, "keyboard_state", put_back());
                return Err(e);
            }
        }
    }
    app.run(200, "keyboard_sent", out)
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
        // what was being composed is written now: shown at once (not at the next key)
        push_state(app, &input);
    }
    Ok(reply)
}

fn set_simplified(app: &App, on: bool) -> Result<Reply> {
    app.config.set("KEYBOARD_CHINESE_SIMPLIFIED", json!(on))?;
    let input = keyboard(app).input.lock().unwrap();
    input.set_simplified(on);
    // the candidates shown change script
    push_state(app, &input);
    drop(input);
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

pub fn get_keyboard_send_to(app: &App, _: Data) -> Result<Reply> {
    current(app, "KEYBOARD_SEND_TO")
}

/// Where Enter sends: "vrct" (translated, to the chat box) or "paste" (into VRChat's text field)
pub fn set_keyboard_send_to(app: &App, data: Data) -> Result<Reply> {
    validated(app, "KEYBOARD_SEND_TO", data.unwrap_or(Value::Null))
}

pub fn get_keyboard_typing_indicator(app: &App, _: Data) -> Result<Reply> {
    current(app, "KEYBOARD_TYPING_INDICATOR")
}

fn set_typing_indicator(app: &App, on: bool) -> Result<Reply> {
    app.config.set("KEYBOARD_TYPING_INDICATOR", json!(on))?;
    changed(app, &keyboard(app).input.lock().unwrap());
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

        // Enter with nothing being composed sends (KEYBOARD_SEND_TO: vrct by default)
        ipc::take_printed();
        assert_eq!(keys(&app, &["Enter"])["text"], json!(""));
        let sent: Vec<Value> = ipc::take_printed().into_iter().filter(|v| v["endpoint"] == "/run/keyboard_sent").map(|v| v["result"].clone()).collect();
        assert_eq!(sent.len(), 1, "{sent:?}");
        assert_eq!((sent[0]["to"].clone(), sent[0]["message"]["original"]["message"].clone()), (json!("vrct"), json!("Hi ")));
        let got = osc_got(&osc);
        assert!(got.contains(&("/chatbox/typing".into(), "false".into())) && got.contains(&("/chatbox/input".into(), "Hi ".into())), "{got:?}");
        // nothing typed: nothing sent
        keys(&app, &["Enter"]);
        assert_eq!(osc_got(&osc), []);
        assert!(!ipc::take_printed().iter().any(|v| v["endpoint"] == "/run/keyboard_sent"));
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
        ipc::take_printed();
        set_keyboard_language(&app, Some(json!("en"))).unwrap();
        // shown at once (not at the next key)
        let pushed: Vec<Value> = ipc::take_printed().into_iter().filter(|v| v["endpoint"] == "/run/keyboard_state").collect();
        assert_eq!(pushed.last().map(|v| v["result"]["text"].clone()), Some(json!("한")));
        assert_eq!(get_keyboard_state(&app, None).unwrap().result["text"], json!("한"));
        assert!(keyboard_key(&app, Some(json!("ab"))).is_err());
        assert_eq!(set_keyboard_send_to(&app, Some(json!("elsewhere"))).unwrap().status, 400);
        assert_eq!(set_keyboard_send_to(&app, Some(json!("paste"))).unwrap().result, json!("paste"));
        keyboard_clear(&app, None).unwrap();
        assert_eq!(get_keyboard_state(&app, None).unwrap().result["length"], json!(0));
        // the typing indicator is off
        assert_eq!(osc_got(&osc), []);
    }

    #[test]
    fn retry_starts_again_only_after_a_failure() {
        let (app, _osc) = rig();
        // not failed (being prepared): nothing starts, nothing changes
        assert_eq!(keyboard_retry(&app, None).unwrap().result["status"], json!("preparing"));
        assert_eq!(*keyboard(&app).status.lock().unwrap(), Status::Preparing);
    }

    #[test]
    fn a_send_that_fails_puts_the_text_back_and_answers_the_error() {
        let (app, _osc) = rig();
        app.config.set("SEND_MESSAGE_TO_VRC", json!(true)).unwrap();
        // OSC cannot send: the chat box fails, the typing indicator too
        app.model.osc.clear_sender();
        set_keyboard_language(&app, Some(json!("en"))).unwrap();
        // typing goes on though the typing indicator is not sent
        assert_eq!(keys(&app, &["h", "i"])["text"], json!("hi"));
        ipc::take_printed();
        assert!(keyboard_key(&app, Some(json!("Enter"))).is_err());
        // nothing typed is lost: back in the keyboard, shown at once
        assert_eq!(get_keyboard_state(&app, None).unwrap().result["text"], json!("hi"));
        let printed = ipc::take_printed();
        let pushed: Vec<&Value> = printed.iter().filter(|v| v["endpoint"] == "/run/keyboard_state").collect();
        assert_eq!(pushed.last().map(|v| v["result"]["text"].clone()), Some(json!("hi")));
        assert!(!printed.iter().any(|v| v["endpoint"] == "/run/keyboard_sent"));
    }

    #[test]
    fn closing_the_keyboard_turns_the_typing_indicator_off_and_keeps_the_text() {
        let (app, osc) = rig();
        app.config.set("SEND_MESSAGE_TO_VRC", json!(true)).unwrap();
        set_keyboard_language(&app, Some(json!("en"))).unwrap();
        keys(&app, &["h", "i"]);
        assert_eq!(osc_got(&osc), [("/chatbox/typing".to_string(), "true".to_string())]);
        super::super::overlay::set_vr_panel_windows(&app, Some(json!({"log": false, "popup": false, "keyboard": false}))).unwrap();
        assert_eq!(osc_got(&osc), [("/chatbox/typing".to_string(), "false".to_string())]);
        assert_eq!(get_keyboard_state(&app, None).unwrap().result["text"], json!("hi"));
        // typing again: on again
        keys(&app, &["!"]);
        assert_eq!(osc_got(&osc), [("/chatbox/typing".to_string(), "true".to_string())]);
    }

    #[test]
    fn sends_go_one_at_a_time_in_the_order_typed() {
        let (app, osc) = rig();
        app.config.set("SEND_MESSAGE_TO_VRC", json!(true)).unwrap();
        set_keyboard_language(&app, Some(json!("en"))).unwrap();
        keys(&app, &["o", "n", "e", "Enter", "t", "w", "o", "Enter"]);
        let sent: Vec<String> = osc_got(&osc).into_iter().filter(|(addr, _)| addr == "/chatbox/input").map(|(_, text)| text).collect();
        assert_eq!(sent, ["one", "two"]);
    }

    #[test]
    fn enter_sends_the_korean_syllable_being_made_too() {
        let (app, osc) = rig();
        app.config.set("SEND_MESSAGE_TO_VRC", json!(true)).unwrap();
        set_keyboard_language(&app, Some(json!("ko"))).unwrap();
        keys(&app, &["g", "k", "s", "r", "m", "f", "Enter"]);
        assert!(osc_got(&osc).contains(&("/chatbox/input".into(), "한글".into())));
    }
}
