//! A local HTTP server for the external-API tests: it answers with a responder, records every
//! request in the shape native/reference/http_capture.py records the Python ones, and compares
//! the two.
#![allow(dead_code)]
use serde_json::{json, Value};
use std::sync::{Arc, Mutex};
use vrct_backend::net::ORIGINAL_ORIGIN_HEADER;

pub type Responder = dyn Fn(&Value) -> (u16, Vec<(&'static str, String)>, Vec<u8>) + Send + Sync;

pub struct Mock {
    server: Arc<tiny_http::Server>,
    pub root: String,
    records: Arc<Mutex<Vec<Value>>>,
    thread: Option<std::thread::JoinHandle<()>>,
}

/// The body as http_capture._body does: {"json"}, {"text"} or {"base64"}, null when empty
pub fn body_value(raw: &[u8]) -> Value {
    if raw.is_empty() {
        return Value::Null;
    }
    match std::str::from_utf8(raw) {
        Err(_) => json!({"base64": base64(raw)}),
        Ok(text) => match serde_json::from_str::<Value>(text) {
            Ok(v) => json!({"json": v}),
            Err(_) => json!({"text": text}),
        },
    }
}

fn base64(data: &[u8]) -> String {
    use base64::Engine;
    base64::engine::general_purpose::STANDARD.encode(data)
}

/// multipart/form-data as http_capture._multipart records it
fn multipart(raw: &[u8], boundary: &str) -> Value {
    let delimiter = format!("--{boundary}").into_bytes();
    let mut parts = vec![];
    let mut positions = vec![];
    let mut i = 0;
    while i + delimiter.len() <= raw.len() {
        if raw[i..].starts_with(&delimiter) {
            positions.push(i);
            i += delimiter.len();
        } else {
            i += 1;
        }
    }
    for w in positions.windows(2) {
        let part = &raw[w[0] + delimiter.len()..w[1]];
        let part = part.strip_prefix(b"\r\n").unwrap_or(part);
        let part = part.strip_suffix(b"\r\n").unwrap_or(part);
        let split = part.windows(4).position(|x| x == b"\r\n\r\n").unwrap();
        let head = std::str::from_utf8(&part[..split]).unwrap();
        let data = &part[split + 4..];
        let param = |line: &str, key: &str| {
            line.split(';').map(str::trim).find_map(|p| p.strip_prefix(&format!("{key}=\"")).map(|v| v.trim_end_matches('"').to_string()))
        };
        let (mut name, mut filename, mut content_type) = (None, None, None);
        for line in head.split("\r\n") {
            let lower = line.to_ascii_lowercase();
            if lower.starts_with("content-disposition:") {
                name = param(line, "name");
                filename = param(line, "filename");
            } else if lower.starts_with("content-type:") {
                content_type = Some(line[13..].trim().to_string());
            }
        }
        let mut entry = json!({"name": name, "filename": filename, "content_type": content_type});
        match std::str::from_utf8(data) {
            Ok(t) => entry["text"] = json!(t),
            Err(_) => entry["base64"] = json!(base64(data)),
        }
        parts.push(entry);
    }
    json!({"multipart": parts})
}

impl Mock {
    pub fn start(responder: Box<Responder>) -> Mock {
        let server = Arc::new(tiny_http::Server::http("127.0.0.1:0").unwrap());
        let root = format!("http://{}", server.server_addr().to_ip().unwrap());
        let records = Arc::new(Mutex::new(vec![]));
        let (s, r) = (server.clone(), records.clone());
        let thread = std::thread::spawn(move || {
            for mut request in s.incoming_requests() {
                let mut raw = vec![];
                request.as_reader().read_to_end(&mut raw).unwrap();
                let mut origin = String::new();
                let mut headers = serde_json::Map::new();
                for h in request.headers() {
                    let name = h.field.as_str().as_str().to_ascii_lowercase();
                    if name == ORIGINAL_ORIGIN_HEADER {
                        origin = h.value.as_str().to_string();
                    } else {
                        headers.insert(name, h.value.as_str().into());
                    }
                }
                let content_type = headers.get("content-type").and_then(Value::as_str).unwrap_or("").to_string();
                let body = match content_type.strip_prefix("multipart/form-data; boundary=") {
                    Some(boundary) => {
                        headers.insert("content-type".into(), "multipart/form-data".into());
                        multipart(&raw, boundary)
                    }
                    None => body_value(&raw),
                };
                let entry = json!({"method": request.method().as_str(), "url": format!("{origin}{}", request.url()),
                                   "headers": headers, "body": body});
                let (status, extra, body) = responder(&entry);
                r.lock().unwrap().push(entry);
                let mut response = tiny_http::Response::from_data(body).with_status_code(status);
                let mut has_type = false;
                for (k, v) in extra {
                    has_type |= k.eq_ignore_ascii_case("content-type");
                    response.add_header(tiny_http::Header::from_bytes(k.as_bytes(), v.as_bytes()).unwrap());
                }
                if !has_type {
                    response.add_header(tiny_http::Header::from_bytes(&b"content-type"[..], &b"application/json"[..]).unwrap());
                }
                let _ = request.respond(response);
            }
        });
        Mock { server, root, records, thread: Some(thread) }
    }

    /// The requests recorded since the last call
    pub fn take(&self) -> Vec<Value> {
        std::mem::take(&mut *self.records.lock().unwrap())
    }
}

impl Drop for Mock {
    fn drop(&mut self) {
        self.server.unblock();
        let _ = self.thread.take().unwrap().join();
    }
}

/// Headers that differ by client library, not by what VRCT sends
fn ignored_header(name: &str) -> bool {
    matches!(name, "host" | "accept-encoding" | "connection" | "user-agent" | "content-length" | "x-goog-api-client")
        || name.starts_with("x-stainless-")
}

/// Differences between the Python requests and the Rust ones (method, URL, headers, body)
pub fn compare_requests(label: &str, python: &[Value], rust: &[Value]) -> Vec<String> {
    let mut problems = vec![];
    if python.len() != rust.len() {
        problems.push(format!("{label}: {} requests (Python {})", rust.len(), python.len()));
        return problems;
    }
    for (i, (p, r)) in python.iter().zip(rust).enumerate() {
        for key in ["method", "url", "body"] {
            if p[key] != r[key] {
                problems.push(format!("{label} #{i} {key}: {}", first_difference(&r[key], &p[key], key)));
            }
        }
        let (ph, rh) = (p["headers"].as_object().unwrap(), r["headers"].as_object().unwrap());
        for (name, value) in ph.iter().filter(|(n, _)| !ignored_header(n)) {
            if rh.get(name) != Some(value) {
                problems.push(format!("{label} #{i} header {name}: {:?} != {value}", rh.get(name)));
            }
        }
        // "accept: */*" means the same as no Accept header (reqwest always sends it)
        let any_accept = |name: &str, h: &serde_json::Map<String, Value>| name == "accept" && h[name] == "*/*";
        for name in rh.keys().filter(|n| !ignored_header(n) && !ph.contains_key(*n) && !any_accept(n, rh)) {
            problems.push(format!("{label} #{i} extra header {name}: {}", rh[name]));
        }
    }
    problems
}

/// Where two JSON values first differ: the path and the two values (strings around the first
/// differing character)
pub fn first_difference(rust: &Value, python: &Value, path: &str) -> String {
    match (rust, python) {
        (Value::Object(a), Value::Object(b)) => {
            for k in a.keys().chain(b.keys()) {
                if a.get(k) != b.get(k) {
                    return first_difference(a.get(k).unwrap_or(&Value::Null), b.get(k).unwrap_or(&Value::Null), &format!("{path}.{k}"));
                }
            }
        }
        (Value::Array(a), Value::Array(b)) if a.len() == b.len() => {
            for (i, (x, y)) in a.iter().zip(b).enumerate() {
                if x != y {
                    return first_difference(x, y, &format!("{path}[{i}]"));
                }
            }
        }
        (Value::String(a), Value::String(b)) => {
            let at = a.chars().zip(b.chars()).take_while(|(x, y)| x == y).count();
            let around = |s: &str| s.chars().skip(at.saturating_sub(30)).take(80).collect::<String>();
            return format!("{path} at char {at}: rust {:?} / python {:?}", around(a), around(b));
        }
        _ => {}
    }
    format!("{path}: rust {rust} / python {python}")
}
