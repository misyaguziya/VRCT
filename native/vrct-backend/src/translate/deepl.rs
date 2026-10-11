//! DeepL API as deepl-python 1.22's `DeepLClient(auth_key).translate_text(text, source_lang,
//! target_lang)` sends it: POST /v2/translate (api-free for ":fx" keys), retried on 429 / 5xx /
//! network errors up to 5 times (1 s, then x1.6 with ±23 % jitter), 10 s timeout per attempt.
use crate::net::{Body, Http};
use anyhow::{bail, Context, Result};
use reqwest::Method;
use serde_json::{json, Value};
use std::time::{Duration, Instant};

pub struct DeepL {
    http: Http,
    auth_key: String,
}

const MAX_RETRIES: u32 = 5;
const MIN_TIMEOUT: Duration = Duration::from_secs(10);

impl DeepL {
    pub fn new(http: Http, auth_key: &str) -> Self {
        Self { http, auth_key: auth_key.to_string() }
    }

    fn url(&self) -> &'static str {
        if self.auth_key.ends_with(":fx") {
            "https://api-free.deepl.com/v2/translate"
        } else {
            "https://api.deepl.com/v2/translate"
        }
    }

    /// translate_text(text, source_lang=..., target_lang=...).text
    pub fn translate(&self, text: &str, source_lang: Option<&str>, target_lang: &str) -> Result<String> {
        if text.is_empty() {
            bail!("text must not be empty");
        }
        let target = target_lang.to_uppercase();
        if target == "EN" || target == "PT" {
            bail!("target_lang={target:?} is deprecated");
        }
        let mut body = json!({"target_lang": target});
        if let Some(source) = source_lang {
            body["source_lang"] = json!(source.to_uppercase());
        }
        body["text"] = json!([text]);
        body["show_billed_characters"] = json!(true);
        let headers = [("authorization", format!("DeepL-Auth-Key {}", self.auth_key))];

        // _BackoffTimer
        let mut retries = 0;
        let mut backoff = 1.0f64;
        let mut deadline = Instant::now() + Duration::from_secs_f64(backoff);
        let response: Value = loop {
            let timeout = deadline.saturating_duration_since(Instant::now()).max(MIN_TIMEOUT);
            let result = self.http.send(Method::POST, self.url(), &headers, Some(Body::Json(body.clone())), Some(timeout));
            let retry = match &result {
                Ok(r) => r.status().as_u16() == 429 || r.status().as_u16() >= 500,
                Err(_) => true,
            };
            if !retry || retries >= MAX_RETRIES {
                let r = result?;
                let status = r.status();
                if !status.is_success() {
                    bail!("DeepL HTTP {}: {}", status.as_u16(), r.text().unwrap_or_default());
                }
                break r.json()?;
            }
            std::thread::sleep(deadline.saturating_duration_since(Instant::now()));
            backoff = (backoff * 1.6).min(120.0);
            let jitter = 1.0 + 0.23 * (2.0 * crate::rand_unit() - 1.0);
            deadline = Instant::now() + Duration::from_secs_f64(backoff * jitter);
            retries += 1;
        };
        let first = response.get("translations").and_then(Value::as_array).and_then(|t| t.first()).context("no translation")?;
        Ok(first.get("text").and_then(Value::as_str).unwrap_or("").to_string())
    }
}
