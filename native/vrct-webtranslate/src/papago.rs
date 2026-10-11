// Copyright (c) 2026 misyaguziya. Licensed for use in VRCT only; see LICENSE.
use std::time::Duration;

use obfstr::obfstr;
use serde_json::Value;

use crate::{client, json_ok, languages, send, Backend, Res, Table};

#[derive(Default)]
pub struct PapagoEngine;

const LANG_MAP: Table = &[("zh", "zh-CN"), ("zh-Hans", "zh-CN"), ("zh-Hant", "zh-TW")];

impl Backend for PapagoEngine {
    fn lang_map(&self) -> Table {
        LANG_MAP
    }
    fn languages(&self) -> Table {
        languages::PAPAGO
    }
    fn auto_code(&self) -> &'static str {
        "auto"
    }

    fn translate(&self, text: &str, src: &str, tgt: &str, timeout: Duration) -> Res<String> {
        let rb = client()?
            .post(obfstr!("https://papago.naver.com/api/text/translation"))
            .form(&[("source", src), ("target", tgt), ("text", text)])
            .header("Referer", obfstr!("https://papago.naver.com/"));
        let r = send("papago.translate", rb, timeout)?;
        if r.status != 200 {
            if let Some(msg) = api_error(&r.body) {
                return Err(msg);
            }
        }
        parse(&json_ok("Papago", &r)?)
    }
}

/// Papago answers bad language pairs with a JSON error body.
fn api_error(body: &str) -> Option<String> {
    let v: Value = serde_json::from_str(body).ok()?;
    let msg = v.get("errorMessage")?.as_str().filter(|m| !m.is_empty())?;
    let code = v.get("errorCode").map_or("None".to_owned(), |c| match c {
        Value::String(s) => s.clone(),
        other => other.to_string(),
    });
    Some(format!("Papago: {msg} (errorCode={code})"))
}

fn parse(data: &Value) -> Res<String> {
    data.get("translatedText")
        .and_then(Value::as_str)
        .map(str::to_owned)
        .ok_or_else(|| {
            format!(
                "Papago: unexpected response: {}",
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
    fn parses_translated_text() {
        assert_eq!(
            parse(&json!({"translatedText": "こんにちは", "srcLangType": "en"})).unwrap(),
            "こんにちは"
        );
        assert!(parse(&json!({"translatedText": null})).is_err());
        assert!(parse(&json!([])).is_err());
    }

    #[test]
    fn surfaces_the_api_error_message() {
        let body = r#"{"errorCode": "TR04", "errorMessage": "Unsupported target language"}"#;
        let e = api_error(body).unwrap();
        assert!(e.contains("Unsupported target language") && e.contains("TR04"));
        assert!(api_error("<html>").is_none());
        assert!(api_error(r#"{"errorMessage": ""}"#).is_none());
    }

    #[test]
    fn posts_form_and_surfaces_http_failures() {
        let (result, requests) = scripted(
            vec![response(200, r#"{"translatedText":"こんにちは"}"#)],
            || {
                Backend::translate(
                    &PapagoEngine,
                    "Hello & goodbye",
                    "en",
                    "ja",
                    Duration::from_secs(3),
                )
            },
        );
        assert_eq!(result.unwrap(), "こんにちは");
        let r = &requests[0];
        assert_eq!(r.method(), "POST");
        assert_eq!(
            r.url().as_str(),
            "https://papago.naver.com/api/text/translation"
        );
        assert_eq!(r.headers()["Referer"], "https://papago.naver.com/");
        assert_eq!(r.timeout(), Some(&Duration::from_secs(3)));
        let fields = form(r);
        assert_eq!(fields.len(), 3);
        assert_eq!(fields["source"], "en");
        assert_eq!(fields["target"], "ja");
        assert_eq!(fields["text"], "Hello & goodbye");
        for (body, expected) in [
            (
                r#"{"errorCode":"TR04","errorMessage":"Unsupported target language"}"#,
                "TR04",
            ),
            ("bad gateway", "HTTP 400"),
        ] {
            let (result, _) = scripted(vec![response(400, body)], || {
                Backend::translate(&PapagoEngine, "Hello", "en", "xx", Duration::from_secs(3))
            });
            assert!(result.unwrap_err().contains(expected));
        }
    }
}
