// Copyright (c) 2026 misyaguziya. Licensed for use in VRCT only; see LICENSE.
//! Web translators (Google / Bing / Papago), taken from translator_engines (bb8eaf1) with its
//! PyO3 entry points replaced by the plain functions below. The engines are unchanged.
use std::error::Error as _;
use std::sync::{Mutex, MutexGuard, OnceLock};
use std::time::Duration;

use obfstr::obfstr;
use reqwest::blocking::{Client, RequestBuilder};
use serde_json::Value;

mod bing;
mod google;
mod languages;
mod papago;
#[cfg(test)]
mod test_http;

pub(crate) type Res<T> = Result<T, String>;
pub(crate) type Table = &'static [(&'static str, &'static str)];

/// translator_engines.DEFAULT_TIMEOUT
pub const DEFAULT_TIMEOUT: f64 = 10.0;

fn lock<T>(m: &Mutex<T>) -> MutexGuard<'_, T> {
    m.lock().unwrap_or_else(|e| e.into_inner())
}

static CLIENT: Mutex<Option<Client>> = Mutex::new(None);

fn user_agent() -> String {
    obfstr!(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
         (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    .to_owned()
}

pub(crate) fn client() -> Res<Client> {
    let mut slot = lock(&CLIENT);
    if let Some(c) = slot.as_ref() {
        return Ok(c.clone());
    }
    let c = Client::builder().user_agent(user_agent()).build().map_err(describe)?;
    *slot = Some(c.clone());
    Ok(c)
}

/// translator_engines.close(): drop the shared HTTP client (a new one is made on the next call)
pub fn close() {
    *lock(&CLIENT) = None;
}

fn describe(e: reqwest::Error) -> String {
    let timed_out = e.is_timeout();
    let e = e.without_url();
    let mut out = e.to_string();
    let mut source = e.source();
    while let Some(s) = source {
        out.push_str(": ");
        out.push_str(&s.to_string());
        source = s.source();
    }
    if timed_out {
        out.push_str(" (timeout)");
    }
    out
}

pub(crate) struct Resp {
    pub status: u16,
    pub body: String,
}

pub(crate) fn send(_phase: &'static str, rb: RequestBuilder, timeout: Duration) -> Res<Resp> {
    let rb = rb.timeout(timeout);
    #[cfg(test)]
    if let Some(response) = test_http::send(&rb) {
        return response;
    }
    let resp = rb.send().map_err(describe)?;
    let status = resp.status().as_u16();
    let body = resp.text().map_err(describe)?;
    Ok(Resp { status, body })
}

fn head(s: &str) -> String {
    s.chars().take(200).collect()
}

pub(crate) fn json_ok(who: &str, r: &Resp) -> Res<Value> {
    if r.status != 200 {
        return Err(format!("{who}: HTTP {}: {}", r.status, head(&r.body)));
    }
    serde_json::from_str(&r.body).map_err(|_| format!("{who}: response was not JSON: {}", head(&r.body)))
}

pub(crate) trait Backend: Send + Sync {
    fn lang_map(&self) -> Table;
    fn languages(&self) -> Table;
    fn auto_code(&self) -> &'static str;
    fn translate(&self, text: &str, src: &str, tgt: &str, timeout: Duration) -> Res<String>;
}

pub(crate) fn normalize(map: Table, auto: &str, language: Option<&str>) -> String {
    match language {
        None | Some("") | Some("auto") | Some("auto-detect") => auto.to_owned(),
        Some(l) => map.iter().find(|(k, _)| *k == l).map_or(l, |(_, v)| *v).to_owned(),
    }
}

fn python_whitespace(c: char) -> bool {
    c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c)
}

fn run(b: &dyn Backend, text: Option<&str>, from: Option<&str>, to: Option<&str>, timeout: Option<f64>) -> Res<String> {
    let text = match text {
        Some(t) if !t.trim_matches(python_whitespace).is_empty() => t,
        _ => return Ok(String::new()),
    };
    let timeout = timeout.unwrap_or(DEFAULT_TIMEOUT);
    let timeout = Duration::try_from_secs_f64(timeout)
        .ok()
        .filter(|d| !d.is_zero())
        .ok_or_else(|| format!("invalid timeout: {timeout}"))?;
    let src = normalize(b.lang_map(), b.auto_code(), from);
    let tgt = normalize(b.lang_map(), b.auto_code(), to);
    b.translate(text, &src, &tgt, timeout)
}

pub(crate) use bing::BingEngine;
pub(crate) use google::GoogleEngine;
pub(crate) use papago::PapagoEngine;

/// get_engine(translator): one instance per engine for the process (Bing keeps its token).
fn engine(translator: &str) -> Res<&'static dyn Backend> {
    static GOOGLE: GoogleEngine = GoogleEngine;
    static PAPAGO: PapagoEngine = PapagoEngine;
    static BING: OnceLock<BingEngine> = OnceLock::new();
    match translator.trim_matches(python_whitespace).to_lowercase().as_str() {
        "google" => Ok(&GOOGLE),
        "bing" => Ok(BING.get_or_init(BingEngine::default)),
        "papago" => Ok(&PAPAGO),
        _ => Err(format!("Unknown translator {translator:?}; expected one of bing, google, papago")),
    }
}

/// translator_engines.translate_text(query_text, translator, from_language, to_language, timeout).
/// Empty or whitespace-only text gives "" without a request. Errors are TranslationError's message.
pub fn translate_text(query_text: Option<&str>, translator: &str, from_language: Option<&str>,
                      to_language: Option<&str>, timeout: Option<f64>) -> Result<String, String> {
    run(engine(translator)?, query_text, from_language, to_language, timeout)
}

/// translator_engines.supports_language(translator, language)
pub fn supports_language(translator: &str, language: Option<&str>) -> Result<bool, String> {
    let b = engine(translator)?;
    let code = normalize(b.lang_map(), b.auto_code(), language);
    Ok(code == b.auto_code() || b.languages().iter().any(|(k, _)| *k == code))
}

/// translator_engines.get_languages(translator): (code, name) pairs
pub fn languages(translator: &str) -> Result<&'static [(&'static str, &'static str)], String> {
    Ok(engine(translator)?.languages())
}
