// Copyright (c) 2026 misyaguziya. Licensed for use in VRCT only; see LICENSE.
use std::time::Duration;

use obfstr::obfstr;
use serde_json::Value;

use crate::{client, json_ok, languages, send, Backend, Res, Table};

#[derive(Default)]
pub struct GoogleEngine;

const LANG_MAP: Table = &[
    ("fil", "tl"),
    ("he", "iw"),
    ("jv", "jw"),
    ("zh", "zh-CN"),
    ("zh-Hans", "zh-CN"),
    ("zh-Hant", "zh-TW"),
];

const RETRYABLE: [u16; 5] = [429, 500, 502, 503, 504];

impl Backend for GoogleEngine {
    fn lang_map(&self) -> Table {
        LANG_MAP
    }
    fn languages(&self) -> Table {
        languages::GOOGLE
    }
    fn auto_code(&self) -> &'static str {
        "auto"
    }

    fn translate(&self, text: &str, src: &str, tgt: &str, timeout: Duration) -> Res<String> {
        let rb = client()?
            .post(obfstr!(
                "https://translate.googleapis.com/translate_a/single"
            ))
            .query(&[
                (obfstr!("client"), obfstr!("gtx")),
                (obfstr!("sl"), src),
                (obfstr!("tl"), tgt),
                (obfstr!("dt"), "t"),
                (obfstr!("dj"), "1"),
            ])
            .form(&[("q", text)]);
        let r = send("google.primary", rb, timeout)?;
        if RETRYABLE.contains(&r.status) {
            return fallback(text, src, tgt, timeout, r.status);
        }
        parse_primary(&json_ok("Google", &r)?)
    }
}

fn fallback(text: &str, src: &str, tgt: &str, timeout: Duration, primary: u16) -> Res<String> {
    let rb = client()?
        .post(obfstr!("https://clients5.google.com/translate_a/t"))
        .query(&[
            (obfstr!("client"), obfstr!("dict-chrome-ex")),
            (obfstr!("sl"), src),
            (obfstr!("tl"), tgt),
        ])
        .form(&[("q", text)]);
    let r = send("google.fallback", rb, timeout)?;
    if r.status != 200 {
        return Err(format!(
            "Google: HTTP {primary} from the primary endpoint and HTTP {} from the fallback endpoint",
            r.status
        ));
    }
    parse_fallback(&json_ok("Google", &r)?)
}

fn parse_primary(data: &Value) -> Res<String> {
    match data.get("sentences").and_then(Value::as_array) {
        Some(s) if !s.is_empty() => Ok(s
            .iter()
            .map(|p| p.get("trans").and_then(Value::as_str).unwrap_or(""))
            .collect()),
        _ => Err(format!(
            "Google: unexpected response: {}",
            crate::head(&data.to_string())
        )),
    }
}

/// `["text"]` with an explicit source, `[["text", "<detected>"]]` for auto.
fn parse_fallback(data: &Value) -> Res<String> {
    let first = data.as_array().and_then(|a| a.first());
    let text = match first {
        Some(Value::String(s)) => Some(s.as_str()),
        Some(Value::Array(a)) => a.first().and_then(Value::as_str),
        _ => None,
    };
    text.map(str::to_owned).ok_or_else(|| {
        format!(
            "Google: unexpected fallback response: {}",
            crate::head(&data.to_string())
        )
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_http::{form, response, scripted};
    use serde_json::json;

    #[test]
    fn joins_every_sentence() {
        let d = json!({"sentences": [{"trans": "こんにちは。"}, {"trans": "元気ですか？"}], "src": "en"});
        assert_eq!(parse_primary(&d).unwrap(), "こんにちは。元気ですか？");
    }

    #[test]
    fn rejects_empty_or_missing_sentences() {
        assert!(parse_primary(&json!({"sentences": []})).is_err());
        assert!(parse_primary(&json!({})).is_err());
        assert!(parse_primary(&json!([])).is_err());
    }

    #[test]
    fn fallback_accepts_both_shapes() {
        assert_eq!(
            parse_fallback(&json!(["こんにちは"])).unwrap(),
            "こんにちは"
        );
        assert_eq!(
            parse_fallback(&json!([["こんにちは", "en"]])).unwrap(),
            "こんにちは"
        );
        assert!(parse_fallback(&json!([])).is_err());
        assert!(parse_fallback(&json!({"a": 1})).is_err());
    }

    #[test]
    fn request_keeps_text_in_form_and_applies_default_timeout() {
        let (result, requests) = scripted(
            vec![response(200, r#"{"sentences":[{"trans":"hi"}]}"#)],
            || {
                crate::run(
                    &GoogleEngine,
                    Some("hello & こんにちは"),
                    Some("he"),
                    Some("zh"),
                    None,
                )
            },
        );
        assert_eq!(result.unwrap(), "hi");
        let r = &requests[0];
        assert_eq!(r.method(), "POST");
        assert_eq!(r.url().host_str(), Some("translate.googleapis.com"));
        assert_eq!(r.url().path(), "/translate_a/single");
        assert_eq!(r.timeout(), Some(&Duration::from_secs(10)));
        let query: std::collections::HashMap<_, _> = r.url().query_pairs().into_owned().collect();
        assert_eq!(query["sl"], "iw");
        assert_eq!(query["tl"], "zh-CN");
        assert_eq!(query["dj"], "1");
        assert_eq!(query["client"], "gtx");
        assert!(!query.contains_key("q"));
        assert_eq!(form(r)["q"], "hello & こんにちは");
    }

    #[test]
    fn falls_back_once_only_for_retryable_statuses() {
        for status in RETRYABLE {
            let (result, requests) = scripted(
                vec![response(status, "busy"), response(200, r#"[["hi","en"]]"#)],
                || Backend::translate(&GoogleEngine, "hello", "auto", "en", Duration::from_secs(2)),
            );
            assert_eq!(result.unwrap(), "hi");
            assert_eq!(requests.len(), 2);
            assert_eq!(requests[1].url().host_str(), Some("clients5.google.com"));
            assert_eq!(requests[1].url().path(), "/translate_a/t");
            assert_eq!(form(&requests[1])["q"], "hello");
            assert_eq!(requests[1].timeout(), Some(&Duration::from_secs(2)));
        }
        for status in [400, 403, 405, 501] {
            let (result, requests) = scripted(vec![response(status, "bad")], || {
                Backend::translate(&GoogleEngine, "hello", "en", "ja", Duration::from_secs(2))
            });
            assert!(result.unwrap_err().contains(&status.to_string()));
            assert_eq!(requests.len(), 1);
        }
        let (result, _) = scripted(vec![response(429, "busy"), response(503, "busy")], || {
            Backend::translate(&GoogleEngine, "hello", "en", "ja", Duration::from_secs(2))
        });
        let error = result.unwrap_err();
        assert!(error.contains("429") && error.contains("503"));
        assert!(!error.contains("https://"));
    }
}
