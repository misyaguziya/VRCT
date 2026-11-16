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
            // response.json() in two steps: a body cut off while it is read is the connection's
            // failure (retried as the SDK does), a body that is not JSON is not
            Ok(response) if response.status().is_success() => match response.bytes() {
                Ok(body) => return serde_json::from_slice(&body).map_err(|e| Error::Other(e.to_string())),
                Err(e) if retries >= 2 => {
                    return Err(if e.is_timeout() { Error::Timeout } else { Error::Connection(format!("{e:#}")) });
                }
                Err(_) => None,
            },
            Ok(response) => {
                let status = response.status().as_u16();
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
                    // a request that could not be made (a bad URL or header) is not a connection failure
                    return Err(if timed_out {
                        Error::Timeout
                    } else if crate::asr::transient_send(&e) {
                        Error::Connection(format!("{e:#}"))
                    } else {
                        Error::Other(format!("{e:#}"))
                    });
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

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::{Read, Write};
    use std::sync::atomic::{AtomicU32, Ordering};
    use std::sync::Arc;

    /// A server answering 200 with each of `bodies` in turn: (what Content-Length says, what is sent)
    fn server(bodies: &'static [(usize, &'static str)]) -> (String, Arc<AtomicU32>) {
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let base = format!("http://{}", listener.local_addr().unwrap());
        let count = Arc::new(AtomicU32::new(0));
        let seen = count.clone();
        std::thread::spawn(move || {
            for (stream, (length, body)) in listener.incoming().zip(bodies.iter().cycle()) {
                let mut stream = stream.unwrap();
                seen.fetch_add(1, Ordering::SeqCst);
                let _ = stream.read(&mut [0u8; 4096]);
                let _ = write!(stream, "HTTP/1.1 200 OK\r\ncontent-type: application/json\r\ncontent-length: {length}\r\nconnection: close\r\n\r\n{body}");
                // dropped here: a shorter body than promised is cut off
            }
        });
        (base, count)
    }

    #[test]
    fn a_body_cut_off_is_a_connection_failure_and_retried() {
        let (base, count) = server(&[(100, "{\"data\":")]);
        let e = list_models(&Http::new().unwrap(), &base, "k", Duration::from_secs(5)).unwrap_err();
        assert!(matches!(e, Error::Connection(_)), "{e:?}");
        assert_eq!(count.load(Ordering::SeqCst), 3);
    }

    #[test]
    fn a_body_cut_off_once_is_read_again() {
        let (base, _) = server(&[(100, "{\"data\":"), (11, "{\"data\":[]}")]);
        assert_eq!(list_models(&Http::new().unwrap(), &base, "k", Duration::from_secs(5)).unwrap(), Vec::<Value>::new());
    }

    #[test]
    fn a_whole_body_that_is_not_json_is_not_retried() {
        let (base, count) = server(&[(8, "not json")]);
        let e = list_models(&Http::new().unwrap(), &base, "k", Duration::from_secs(5)).unwrap_err();
        assert!(matches!(e, Error::Other(_)), "{e:?}");
        assert_eq!(count.load(Ordering::SeqCst), 1);
    }
}
