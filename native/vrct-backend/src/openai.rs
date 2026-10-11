//! Requests as the openai Python SDK (1.109) sends them: the base URL joining, and its retry loop
//! (max_retries 2) with the error kinds its exceptions map to.
use crate::net::{Body, Http};
use reqwest::Method;
use serde_json::Value;
use std::time::Duration;

/// The SDK's base URL when none is given
pub const DEFAULT_BASE_URL: &str = "https://api.openai.com/v1";
/// The SDK's default timeout (600 s)
pub const DEFAULT_TIMEOUT: Duration = Duration::from_secs(600);

/// `{base}/{path}` as the SDK joins them (a trailing slash is added to the base first)
pub fn url(base: &str, path: &str) -> String {
    if base.ends_with('/') { format!("{base}{path}") } else { format!("{base}/{path}") }
}

/// What the SDK raises: APIStatusError subclasses (by status), APITimeoutError, APIConnectionError
#[derive(Debug)]
pub enum Error {
    Status(u16, String),
    Timeout,
    Connection(String),
    Other(String),
}

impl std::fmt::Display for Error {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Error::Status(s, body) => write!(f, "HTTP {s}: {body}"),
            Error::Timeout => write!(f, "request timed out"),
            Error::Connection(e) => write!(f, "connection error: {e}"),
            Error::Other(e) => write!(f, "{e}"),
        }
    }
}

impl std::error::Error for Error {}

/// retry-after-ms / retry-after (seconds) when it is between 0 and 60 s
fn retry_after(headers: &reqwest::header::HeaderMap) -> Option<Duration> {
    let get = |name| headers.get(name).and_then(|v| v.to_str().ok()).and_then(|v| v.parse::<f64>().ok());
    let seconds = get("retry-after-ms").map(|ms| ms / 1000.0).or_else(|| get("retry-after"))?;
    (0.0 < seconds && seconds <= 60.0).then(|| Duration::from_secs_f64(seconds))
}

/// One request with the SDK's retries: connection errors, timeouts, 408 / 409 / 429 and 5xx are
/// retried twice after min(0.5 * 2^n, 8) s with up to 25 % jitter, or the server's retry-after.
/// `body` is rebuilt for each attempt (a multipart form can be sent once only).
pub fn send(http: &Http, method: Method, url: &str, headers: &[(&str, String)], body: &dyn Fn() -> Option<Body>,
            timeout: Duration) -> Result<Value, Error> {
    let mut retries = 0u32;
    loop {
        let wait = match http.send(method.clone(), url, headers, body(), Some(timeout)) {
            Ok(response) => {
                let status = response.status().as_u16();
                if response.status().is_success() {
                    return response.json().map_err(|e| Error::Other(e.to_string()));
                }
                let should_retry = match response.headers().get("x-should-retry").and_then(|v| v.to_str().ok()) {
                    Some("true") => true,
                    Some("false") => false,
                    _ => matches!(status, 408 | 409 | 429) || status >= 500,
                };
                let wait = retry_after(response.headers());
                if !should_retry || retries >= 2 {
                    return Err(Error::Status(status, response.text().unwrap_or_default()));
                }
                wait
            }
            Err(e) => {
                let timed_out = e.downcast_ref::<reqwest::Error>().is_some_and(|e| e.is_timeout());
                if retries >= 2 {
                    return Err(if timed_out { Error::Timeout } else { Error::Connection(format!("{e:#}")) });
                }
                None
            }
        };
        let backoff = (0.5 * 2f64.powi(retries as i32)).min(8.0) * (1.0 - 0.25 * crate::rand_unit());
        std::thread::sleep(wait.unwrap_or(Duration::from_secs_f64(backoff)));
        retries += 1;
    }
}

/// `client.models.list().data`
pub fn list_models(http: &Http, base: &str, api_key: &str, timeout: Duration) -> Result<Vec<Value>, Error> {
    let headers = [("accept", "application/json".to_string()), ("authorization", format!("Bearer {api_key}"))];
    let response = send(http, Method::GET, &url(base, "models"), &headers, &|| None, timeout)?;
    Ok(response.get("data").and_then(Value::as_array).cloned().unwrap_or_default())
}
