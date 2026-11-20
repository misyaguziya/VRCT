//! The web translators (Google / Bing / Papago) of `bin/translator_engines.dll`.
//!
//! The DLL is a binary of the translator engines, licensed for use in VRCT only (`LICENSE`); its
//! source is not part of this repository. The sidecar loads it from `_internal` at the first
//! translation, so a missing DLL fails that translation, not the start.
use std::ffi::{c_char, CStr, CString};
use std::sync::OnceLock;

use libloading::Library;

const DLL: &str = "translator_engines.dll";

type TranslateText = unsafe extern "C" fn(
    *const c_char,
    *const c_char,
    *const c_char,
    *const c_char,
    f64,
    *mut *mut c_char,
) -> i32;
type FreeString = unsafe extern "C" fn(*mut c_char);

struct Api {
    translate_text: TranslateText,
    free_string: FreeString,
    _lib: Library,
}

fn load(path: &str) -> Result<Api, String> {
    let fail = |e: libloading::Error| format!("{DLL}: {e}");
    // SAFETY: the DLL runs no initialization of its own, and the signatures are capi.rs's
    unsafe {
        let lib = Library::new(path).map_err(fail)?;
        let translate_text = *lib.get::<TranslateText>(b"te_translate_text\0").map_err(fail)?;
        let free_string = *lib.get::<FreeString>(b"te_free_string\0").map_err(fail)?;
        Ok(Api { translate_text, free_string, _lib: lib })
    }
}

fn api() -> Result<&'static Api, String> {
    static API: OnceLock<Result<Api, String>> = OnceLock::new();
    API.get_or_init(|| load(DLL)).as_ref().map_err(Clone::clone)
}

fn call(api: &Api, query_text: Option<&str>, translator: &str, from_language: Option<&str>,
        to_language: Option<&str>, timeout: Option<f64>) -> Result<String, String> {
    let c = |name: &str, s: Option<&str>| s.map(CString::new).transpose().map_err(|_| format!("{name} contains NUL"));
    let text = c("text", query_text)?;
    let translator = c("translator", Some(translator))?;
    let from = c("from_language", from_language)?;
    let to = c("to_language", to_language)?;
    let ptr = |s: &Option<CString>| s.as_ref().map_or(std::ptr::null(), |s| s.as_ptr());
    let mut out = std::ptr::null_mut();
    // SAFETY: the strings live until the call returns; `out` is written by it and freed by the DLL
    let code = unsafe {
        (api.translate_text)(ptr(&text), ptr(&translator), ptr(&from), ptr(&to), timeout.unwrap_or(f64::NAN), &mut out)
    };
    if out.is_null() {
        return Err(format!("{DLL}: te_translate_text returned {code} without a result"));
    }
    // SAFETY: a NUL-terminated string of the DLL, freed once right after the copy
    let s = unsafe { CStr::from_ptr(out) }.to_string_lossy().into_owned();
    unsafe { (api.free_string)(out) };
    if code == 0 { Ok(s) } else { Err(s) }
}

/// translator_engines.translate_text(query_text, translator, from_language, to_language, timeout).
/// Empty or whitespace-only text gives "" without a request. Errors are TranslationError's message
/// (or why the DLL could not be loaded).
pub fn translate_text(query_text: Option<&str>, translator: &str, from_language: Option<&str>,
                      to_language: Option<&str>, timeout: Option<f64>) -> Result<String, String> {
    call(api()?, query_text, translator, from_language, to_language, timeout)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn bundled() -> Api {
        load(concat!(env!("CARGO_MANIFEST_DIR"), "/bin/translator_engines.dll")).unwrap()
    }

    #[test]
    fn blank_text_gives_empty_without_a_request() {
        let api = bundled();
        assert_eq!(call(&api, Some(" \n"), "google", Some("ja"), Some("en"), Some(5.0)), Ok(String::new()));
        assert_eq!(call(&api, None, "bing", None, None, None), Ok(String::new()));
    }

    #[test]
    fn errors_come_back_as_messages() {
        let api = bundled();
        let err = call(&api, Some("hi"), "nope", None, None, Some(5.0)).unwrap_err();
        assert!(err.starts_with("Unknown translator"), "{err}");
        assert_eq!(call(&api, Some("a\0b"), "google", None, None, None), Err("text contains NUL".into()));
    }

    #[test]
    fn a_missing_dll_is_an_error() {
        let err = load("no_such_translator_engines.dll").err().unwrap();
        assert!(err.starts_with(DLL), "{err}");
    }
}
