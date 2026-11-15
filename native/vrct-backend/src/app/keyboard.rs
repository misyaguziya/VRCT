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
use std::sync::{Mutex, MutexGuard, OnceLock};
use std::time::{Duration, Instant};
use vrct_ime::input::{Input, Key, Language, State};
use vrct_ime::rime::Rime;

type Data = Option<Value>;

/// The dictionaries (Japanese and Chinese; English and Korean need none)
#[derive(Clone, Copy, Debug, PartialEq)]
enum Status {
    /// not started: nothing needed the keyboard yet (shown as preparing)
    Idle,
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
    typing: Mutex<Typing>,
    /// the typing indicator is on in VRChat
    indicator: Mutex<bool>,
    /// rime.dll loaded and started (once a process: a retry only builds again)
    rime: OnceLock<&'static Rime>,
    /// the microphone types into the keyboard (its transcription runs for it, VRCT's microphone
    /// switch untouched)
    dictation: Mutex<bool>,
}

/// What is typed, and what goes with it (one lock: keys, sends and what the microphone heard
/// change it in turn)
struct Typing {
    input: Input<'static>,
    history: History,
    /// when Enter last committed a word: an Enter right after it is a double press, not a send
    committed_at: Option<Instant>,
}

impl Typing {
    /// ↑ (older) or ↓ (newer): what was sent, called back in place of what is typed
    fn recall(&mut self, older: bool) {
        let Typing { input, history, .. } = self;
        if let Some(text) = history.step(older, || input.take()) {
            input.set_text(&text);
        }
    }

    /// Everything typed gone; ↑ starts from the newest again
    fn clear(&mut self) {
        self.input.clear();
        self.history.at = None;
    }
}

/// What VRCT sent (the message box, the microphone and the keyboard: the main window's history,
/// not what was pasted), called back with ↑ ↓ as a shell does
#[derive(Default)]
struct History {
    sent: Vec<String>,
    /// the one shown (None: what is being typed)
    at: Option<usize>,
    /// what was being typed before ↑, back after the newest
    draft: String,
}

const HISTORY_KEPT: usize = 50;

impl History {
    /// A text sent: the newest (once: sent again, it moves up)
    fn add(&mut self, text: &str) {
        self.sent.retain(|sent| sent != text);
        self.sent.push(text.into());
        let excess = self.sent.len().saturating_sub(HISTORY_KEPT);
        self.sent.drain(..excess);
        self.at = None;
    }

    /// ↑ (older) or ↓ (newer): the text to show, None: nothing changes
    fn step(&mut self, older: bool, typed: impl FnOnce() -> String) -> Option<String> {
        let at = match (self.at, older) {
            (None, true) if !self.sent.is_empty() => {
                self.draft = typed();
                self.sent.len() - 1
            }
            (Some(at), true) if at > 0 => at - 1,
            (Some(at), false) if at + 1 < self.sent.len() => at + 1,
            (Some(_), false) => {
                self.at = None;
                return Some(std::mem::take(&mut self.draft));
            }
            _ => return None,
        };
        self.at = Some(at);
        Some(self.sent[at].clone())
    }
}

/// An Enter this soon after the one that committed the word does not send
const SEND_AFTER_COMMIT: Duration = Duration::from_millis(400);

impl Keyboard {
    pub fn new(config: &crate::config::Config) -> Self {
        let language = Language::from_code(&config.get_str("KEYBOARD_LANGUAGE")).unwrap_or(Language::Japanese);
        let typing = Typing { input: Input::new(language), history: History::default(), committed_at: None };
        Keyboard { status: Mutex::new(Status::Idle), typing: Mutex::new(typing), indicator: Mutex::default(), rime: OnceLock::new(),
                   dictation: Mutex::default() }
    }
}

fn keyboard(app: &App) -> &Keyboard {
    &app.model.keyboard
}

fn typing(app: &App) -> MutexGuard<'_, Typing> {
    keyboard(app).typing.lock().unwrap()
}

fn state_json(status: Status, s: &State) -> Value {
    // progress: of the download, 0..1
    let (status, progress) = match status {
        Status::Idle | Status::Preparing => ("preparing", 0.0),
        Status::Downloading(p) => ("downloading", p),
        Status::Building => ("building", 1.0),
        Status::Ready => ("ready", 1.0),
        Status::Failed => ("failed", 0.0),
    };
    json!({
        "status": status,
        "progress": progress,
        "text": s.text,
        "after": s.after,
        "composition": s.composition.as_ref().map(|c| json!({"preedit": c.preedit, "cursor": c.cursor, "selection": [c.selection.0, c.selection.1]})),
        "candidates": s.candidates,
        "highlighted": s.highlighted,
        "converting": s.converting,
        "page": s.page,
        "last_page": s.last_page,
        "syllable": s.syllable,
        "length": s.length,
        "half_width": s.half_width,
        // characters selected before / after the cursor
        "selected": [s.selected.0, s.selected.1],
    })
}

/// Everything the keyboard shows, after a change: VRChat's typing indicator follows whether
/// anything is typed for VRCT to write to the chat box (not when pasting: VRChat's own field is
/// open then), and not sent, as when OSC cannot send: logged, the typing goes on
fn changed(app: &App, input: &Input) -> Value {
    let s = input.state();
    let typing = s.length > 0 && app.config.get_bool("KEYBOARD_TYPING_INDICATOR") && app.config.get_bool("SEND_MESSAGE_TO_VRC")
        && app.config.get_str("KEYBOARD_SEND_TO") == "vrct";
    set_indicator(app, typing);
    state_json(*keyboard(app).status.lock().unwrap(), &s)
}

fn set_indicator(app: &App, on: bool) {
    let mut was = keyboard(app).indicator.lock().unwrap();
    if *was != on {
        if let Err(e) = app.model.osc.send_typing(on) {
            logs::error("keyboard typing indicator", &format!("{e:#}"));
        }
        *was = on;
    }
}

/// The keyboard closed or VRCT ends: VRChat's typing indicator off (what is typed stays)
pub fn indicator_off(app: &App) {
    set_indicator(app, false);
}

/// The keyboard closed (or the VR UI with it), with text in it: VRChat's typing indicator is not
/// left on, nor its microphone
pub fn hidden(app: &App) {
    indicator_off(app);
    stop_dictation(app, true);
}

fn push_state(app: &App, input: &Input) {
    let _ = app.run(200, "keyboard_state", changed(app, input));
}

fn set_status(app: &App, status: Status) {
    *keyboard(app).status.lock().unwrap() = status;
    let state = typing(app).input.state();
    let _ = app.run(200, "keyboard_state", state_json(status, &state));
}

// ------------------------------------------------------------------------------- the dictionaries

/// The dictionaries downloaded (the first time) and built, then Japanese and Chinese type. Not at
/// start-up: when the keyboard is first needed (the VR UI on, or the UI asking for its state), once
pub fn start(app: &App) {
    begin(app, Status::Idle);
}

/// The dictionaries made ready in the background, when they are `from` (one caller wins: the status
/// changes under its lock)
fn begin(app: &App, from: Status) {
    {
        let mut status = keyboard(app).status.lock().unwrap();
        if *status != from {
            return;
        }
        *status = Status::Preparing;
    }
    // the tests see the status change only: no download, no librime
    if cfg!(test) {
        return;
    }
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
            // the logs relative to the working directory (`local`, set in main): librime reads log_dir in
            // the ANSI code page, and a UTF-8 path with, say, テ in a Japanese user name aborts it
            rime.start(&shared, &user, std::path::Path::new("logs"))?;
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
    typing(app).input.attach(session, app.config.get_bool("KEYBOARD_CHINESE_SIMPLIFIED"));
    ipc::log(format!("Keyboard ready (librime {})", rime.version()));
    set_status(app, Status::Ready);
    Ok(())
}

// --------------------------------------------------------------------------------- handlers

/// The dictionaries once more, after they failed (a press while they are being made does nothing)
pub fn keyboard_retry(app: &App, _: Data) -> Result<Reply> {
    begin(app, Status::Failed);
    get_keyboard_state(app, None)
}

/// Asked for: the keyboard is needed, its dictionaries start if they have not
pub fn get_keyboard_state(app: &App, _: Data) -> Result<Reply> {
    start(app);
    let state = typing(app).input.state();
    Ok(Reply::ok(state_json(*keyboard(app).status.lock().unwrap(), &state)))
}

/// A key: one character ("a", "A" with Shift, "、", "\n"), or Backspace, Space, Enter, Left, Right,
/// PageUp, PageDown, HalfWidth (半角/全角), Tab (the candidate highlighted), Up and Down (what was sent, called back); ◀ ▶ with
/// modifiers (Shift+Left, Ctrl+Right, Ctrl+Shift+Left…), SelectAll, Undo, Redo, and Copy, Cut,
/// Paste through the clipboard (Cut deletes only what went onto it)
pub fn keyboard_key(app: &App, data: Data) -> Result<Reply> {
    let name = data.as_ref().and_then(Value::as_str).ok_or_else(|| anyhow!("the key is not a string"))?;
    let mut t = typing(app);
    match name {
        "Up" | "Down" => t.recall(name == "Up"),
        "Copy" => {
            if let Some(text) = t.input.selected_text() {
                crate::clipboard::copy(&text);
            }
        }
        "Cut" => {
            if t.input.selected_text().is_some_and(|text| crate::clipboard::copy(&text)) {
                t.input.cut();
            }
        }
        "Paste" => {
            if let Some(text) = crate::clipboard::text() {
                t.input.paste(&text);
            }
        }
        "Enter" if !t.input.composing() => return enter(app, t),
        _ => {
            let key = key_of(name)?;
            // Enter commits the word being composed (and one right after it is not a send)
            if key == Key::Enter {
                t.committed_at = Some(Instant::now());
            }
            t.input.key(key);
        }
    }
    Ok(Reply::ok(changed(app, &t.input)))
}

fn key_of(name: &str) -> Result<Key> {
    Ok(match name {
        "Backspace" => Key::Backspace,
        "Space" => Key::Space,
        "Enter" => Key::Enter,
        "Left" => Key::Left,
        "Right" => Key::Right,
        "PageUp" => Key::PageUp,
        "PageDown" => Key::PageDown,
        "HalfWidth" => Key::HalfWidth,
        "Tab" => Key::Tab,
        "SelectAll" => Key::SelectAll,
        "Undo" => Key::Undo,
        "Redo" => Key::Redo,
        _ if name.ends_with("+Left") || name.ends_with("+Right") => {
            let (modifiers, arrow) = name.rsplit_once('+').unwrap_or_default();
            let (word, select) = match modifiers {
                "Shift" => (false, true),
                "Ctrl" => (true, false),
                "Ctrl+Shift" => (true, true),
                _ => bail!("no key {name:?}"),
            };
            Key::Move { left: arrow == "Left", word, select }
        }
        _ => {
            let mut chars = name.chars();
            match (chars.next(), chars.next()) {
                (Some(c), None) => Key::Char(c),
                _ => bail!("no key {name:?}"),
            }
        }
    })
}

/// Enter with nothing being composed: what is typed is sent (KEYBOARD_SEND_TO), told by
/// keyboard_sent. Not right after Enter committed a word (its double press), nor blank text
fn enter<'a>(app: &'a App, mut t: MutexGuard<'a, Typing>) -> Result<Reply> {
    let double = t.committed_at.take().is_some_and(|at| at.elapsed() < SEND_AFTER_COMMIT);
    if !double {
        let text = t.input.take();
        if text.trim().is_empty() {
            t.input.restore(&text);
        } else {
            // (the send takes the lock again when it is done)
            drop(t);
            send(app, text, &app.config.get_str("KEYBOARD_SEND_TO"))?;
            t = typing(app);
        }
    }
    Ok(Reply::ok(changed(app, &t.input)))
}

/// The candidate at this index of the page shown
pub fn keyboard_select(app: &App, data: Data) -> Result<Reply> {
    let index = data.as_ref().and_then(Value::as_u64).ok_or_else(|| anyhow!("the index is not a number"))?;
    let mut t = typing(app);
    t.input.select(index as usize);
    Ok(Reply::ok(changed(app, &t.input)))
}

/// The cursor to this character of the text (the input box pressed there)
pub fn keyboard_cursor(app: &App, data: Data) -> Result<Reply> {
    let index = data.as_ref().and_then(Value::as_u64).ok_or_else(|| anyhow!("the index is not a number"))?;
    let mut t = typing(app);
    t.input.set_cursor(index as usize);
    Ok(Reply::ok(changed(app, &t.input)))
}

pub fn keyboard_clear(app: &App, _: Data) -> Result<Reply> {
    let mut t = typing(app);
    t.clear();
    Ok(Reply::ok(changed(app, &t.input)))
}

/// VRCT sent this (the message box, the microphone or the keyboard): ↑ calls it back
pub fn sent(app: &App, text: &str) {
    if !text.trim().is_empty() {
        typing(app).history.add(text);
    }
}

// --------------------------------------------------------------------------------- dictation

/// The microphone types into the keyboard: what it hears goes after the text (to be corrected
/// and sent with ↵) instead of being sent. Its transcription runs for it without turning VRCT's
/// microphone on (ENABLE_TRANSCRIPTION_SEND and its switch stay as they are)
pub fn keyboard_dictating(app: &App) -> bool {
    *keyboard(app).dictation.lock().unwrap()
}

/// What the microphone heard, while dictating
pub fn dictated(app: &App, text: &str) {
    let mut t = typing(app);
    t.input.append(text);
    push_state(app, &t.input);
}

fn dictation_reply(app: &App) -> Result<Reply> {
    Ok(Reply::ok(json!(keyboard_dictating(app))))
}

pub fn get_keyboard_dictation(app: &App, _: Data) -> Result<Reply> {
    dictation_reply(app)
}

/// On the keyboard's ordered worker (as its switching off): one at a time
pub fn set_enable_keyboard_dictation(app: &App, _: Data) -> Result<Reply> {
    if !keyboard_dictating(app) {
        // (marked first: the microphone's session then knows it runs for the keyboard)
        *keyboard(app).dictation.lock().unwrap() = true;
        // the session started for it (already running when VRCT's microphone is on); it may not
        // start (no device…). VRChat's mute does not hold it while it types here
        if !super::audio::start_mic_for_keyboard(app) {
            *keyboard(app).dictation.lock().unwrap() = false;
        }
    }
    dictation_reply(app)
}

pub fn set_disable_keyboard_dictation(app: &App, _: Data) -> Result<Reply> {
    stop_dictation(app, false);
    dictation_reply(app)
}

/// Dictation off (the keyboard closed, or turned off): the microphone's session stops unless VRCT's
/// microphone is on (then VRChat's mute holds it again). `told`: the UI is told (when it did not ask)
fn stop_dictation(app: &App, told: bool) {
    if !std::mem::take(&mut *keyboard(app).dictation.lock().unwrap()) {
        return;
    }
    if let Err(e) = super::audio::release_mic_for_keyboard(app) {
        logs::error("keyboard dictation", &format!("{e:#}"));
    }
    if told {
        ipc::print_response(200, Some("/set/disable/keyboard_dictation"), &json!(false));
    }
}

/// The microphone's transcription stopped by itself (an error, its device lost): dictation ends with it
pub fn transcription_stopped(app: &App) {
    if std::mem::take(&mut *keyboard(app).dictation.lock().unwrap()) {
        ipc::print_response(200, Some("/set/disable/keyboard_dictation"), &json!(false));
    }
}

/// The text taken out (Korean's syllable being made included), sent: through VRCT as the message box
/// sends it ({"to": "vrct", "message": its answer}) or pasted into VRChat ({"to": "paste", "pasted"}),
/// told by keyboard_sent. On the keyboard's ordered worker, as the keys: sends go one at a time in
/// the order typed, and the keys typed meanwhile wait (never pass them). What did not go (an error;
/// only copied: no VRChat window took the focus) is put back, so nothing typed is lost.
fn send(app: &App, text: String, to: &str) -> Result<()> {
    let mut out = json!({"to": to});
    // Ok(false): only copied
    let sent = if to == "paste" {
        let window = app.model.app_name.get();
        let pasted = crate::clipboard::copy_and_paste(&text, window.as_deref(), &|line| ipc::log(line));
        out["pasted"] = json!(pasted);
        Ok(pasted)
    } else {
        process(app, &CHAT, &text, None, None, None).map(|message| {
            out["message"] = message.unwrap_or(Value::Null);
            true
        })
    };
    let state = {
        let mut t = typing(app);
        if matches!(sent, Ok(true)) {
            // (what went through VRCT is in the history already: sent())
            t.history.at = None;
        } else {
            t.input.restore(&text);
        }
        changed(app, &t.input)
    };
    match sent {
        Ok(_) => {
            out["state"] = state;
            app.run(200, "keyboard_sent", out)
        }
        // the text back on the keyboard, the error to the UI (500, as the message box)
        Err(e) => {
            let _ = app.run(200, "keyboard_state", state);
            Err(e)
        }
    }
}

// --------------------------------------------------------------------------------- settings

pub fn get_keyboard_language(app: &App, _: Data) -> Result<Reply> {
    current(app, "KEYBOARD_LANGUAGE")
}

/// "ja", "en", "ko", "zh", "zhuyin", "cangjie" or "quick"; what was being composed is written first
pub fn set_keyboard_language(app: &App, data: Data) -> Result<Reply> {
    let reply = validated(app, "KEYBOARD_LANGUAGE", data.unwrap_or(Value::Null))?;
    if let Some(language) = Language::from_code(&app.config.get_str("KEYBOARD_LANGUAGE")) {
        let mut t = typing(app);
        t.input.set_language(language);
        // what was being composed is written now: shown at once (not at the next key)
        push_state(app, &t.input);
    }
    Ok(reply)
}

fn set_simplified(app: &App, on: bool) -> Result<Reply> {
    app.config.set("KEYBOARD_CHINESE_SIMPLIFIED", json!(on))?;
    let t = typing(app);
    t.input.set_simplified(on);
    // the candidates shown change script
    push_state(app, &t.input);
    drop(t);
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

pub fn get_keyboard_key_sound_volume(app: &App, _: Data) -> Result<Reply> {
    current(app, "KEYBOARD_KEY_SOUND_VOLUME")
}

/// The keys' sound, 0–100 % (whole percents)
pub fn set_keyboard_key_sound_volume(app: &App, data: Data) -> Result<Reply> {
    let rounded = data.as_ref().and_then(crate::pyjson::py_float).map_or(Value::Null, |v| json!(v.round() as i64));
    validated(app, "KEYBOARD_KEY_SOUND_VOLUME", rounded)
}

pub fn get_keyboard_send_to(app: &App, _: Data) -> Result<Reply> {
    current(app, "KEYBOARD_SEND_TO")
}

/// Where Enter sends: "vrct" (translated, to the chat box) or "paste" (into VRChat's text field)
pub fn set_keyboard_send_to(app: &App, data: Data) -> Result<Reply> {
    let reply = validated(app, "KEYBOARD_SEND_TO", data.unwrap_or(Value::Null))?;
    // the typing indicator follows at once
    changed(app, &typing(app).input);
    Ok(reply)
}

pub fn get_keyboard_typing_indicator(app: &App, _: Data) -> Result<Reply> {
    current(app, "KEYBOARD_TYPING_INDICATOR")
}

fn set_typing_indicator(app: &App, on: bool) -> Result<Reply> {
    app.config.set("KEYBOARD_TYPING_INDICATOR", json!(on))?;
    changed(app, &typing(app).input);
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
    fn modified_arrows_select_all_undo_redo_and_half_width_by_name() {
        let (app, _osc) = rig();
        set_keyboard_language(&app, Some(json!("en"))).unwrap();
        keys(&app, &["a", "b", "Space", "c", "d", "Ctrl+Left"]);
        assert_eq!(keys(&app, &["Ctrl+Shift+Right"])["selected"], json!([2, 0]));
        assert_eq!(keys(&app, &["SelectAll", "Backspace"])["text"], json!(""));
        assert_eq!(keys(&app, &["Undo"])["text"], json!("ab cd"));
        assert_eq!(keys(&app, &["Redo"])["text"], json!(""));
        assert!(keyboard_key(&app, Some(json!("Alt+Left"))).is_err());
        set_keyboard_language(&app, Some(json!("ja"))).unwrap();
        assert_eq!(keys(&app, &["HalfWidth"])["half_width"], json!(true));
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
    fn up_and_down_call_back_what_was_sent_and_a_line_break_goes_with_it() {
        let (app, osc) = rig();
        set_keyboard_language(&app, Some(json!("en"))).unwrap();
        // nothing sent yet: nothing to call back
        assert_eq!(keys(&app, &["x", "Up"])["text"], json!("x"));
        keys(&app, &["\n", "o", "k", "Enter"]);
        assert!(osc_got(&osc).contains(&("/chatbox/input".into(), "x\nok".into())));
        keys(&app, &["t", "w", "o", "Enter", "d", "r", "a", "f", "t"]);
        let text = |key| keys(&app, &[key])["text"].clone();
        assert_eq!([text("Up"), text("Up"), text("Up"), text("Down"), text("Down"), text("Down")],
                   [json!("two"), json!("x\nok"), json!("x\nok"), json!("two"), json!("draft"), json!("draft")]);
        // one called back and sent again is the newest, once
        keys(&app, &["Up", "Up", "Enter"]);
        assert_eq!([text("Up"), text("Up"), text("Up")], [json!("x\nok"), json!("two"), json!("two")]);
        // cleared: ↑ starts from the newest again
        keyboard_clear(&app, None).unwrap();
        assert_eq!(text("Up"), json!("x\nok"));
        // the opacity: 0.2–1.0
        assert!(app.config.set("KEYBOARD_OPACITY", json!(0.1)).is_err());
        assert!(app.config.set("KEYBOARD_OPACITY", json!(0.6)).is_ok());
    }

    #[test]
    fn the_typing_indicator_is_only_for_the_chat_box_and_up_calls_back_the_message_box_too() {
        let (app, osc) = rig();
        app.config.set("SEND_MESSAGE_TO_VRC", json!(true)).unwrap();
        set_keyboard_language(&app, Some(json!("en"))).unwrap();
        keys(&app, &["h", "i"]);
        assert_eq!(osc_got(&osc), [("/chatbox/typing".to_string(), "true".to_string())]);
        // pasting: VRChat's own field is open, the indicator goes off at once
        set_keyboard_send_to(&app, Some(json!("paste"))).unwrap();
        assert_eq!(osc_got(&osc), [("/chatbox/typing".to_string(), "false".to_string())]);
        keys(&app, &["!"]);
        assert_eq!(osc_got(&osc), []);
        set_keyboard_send_to(&app, Some(json!("vrct"))).unwrap();
        assert_eq!(osc_got(&osc), [("/chatbox/typing".to_string(), "true".to_string())]);
        // what the main window's message box sent is called back by ↑
        keyboard_clear(&app, None).unwrap();
        super::super::pipeline::send_message_box(&app, Some(json!({"id": "1", "message": "from the box"}))).unwrap();
        assert_eq!(keys(&app, &["Up"])["text"], json!("from the box"));
    }

    #[test]
    fn korean_composes_and_the_settings_check_their_values() {
        let (app, osc) = rig();
        app.config.set("KEYBOARD_TYPING_INDICATOR", json!(false)).unwrap();
        set_keyboard_language(&app, Some(json!("ko"))).unwrap();
        let state = keys(&app, &["g", "k", "s"]);
        assert_eq!(state["syllable"], json!("한"));
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
    fn the_dictionaries_start_once_when_first_needed_and_again_only_after_a_failure() {
        let (app, _osc) = rig();
        let status = || *keyboard(&app).status.lock().unwrap();
        // started up: not yet
        assert_eq!(status(), Status::Idle);
        // the UI asks for the state: they start, shown as preparing all along
        assert_eq!(get_keyboard_state(&app, None).unwrap().result["status"], json!("preparing"));
        assert_eq!(status(), Status::Preparing);
        // being made: asked again, the VR UI on (start) or a retry start nothing again
        *keyboard(&app).status.lock().unwrap() = Status::Building;
        assert_eq!(get_keyboard_state(&app, None).unwrap().result["status"], json!("building"));
        start(&app);
        assert_eq!(keyboard_retry(&app, None).unwrap().result["status"], json!("building"));
        assert_eq!(status(), Status::Building);
        // failed: a retry starts them again
        *keyboard(&app).status.lock().unwrap() = Status::Failed;
        assert_eq!(keyboard_retry(&app, None).unwrap().result["status"], json!("preparing"));
        assert_eq!(status(), Status::Preparing);
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
