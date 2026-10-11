//! The OBS browser source page (models/obs/obs_browser_source_server.py): a local HTTP server whose
//! page connects to the WebSocket server with its token and shows the messages. The page is
//! obs_overlay.html, taken from the Python version by native/reference/export_obs.py.
use crate::pyfmt;
use serde_json::{Map, Value};
use std::io::{Read, Write};
use std::net::{Shutdown, SocketAddr, TcpListener, TcpStream};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;

const TEMPLATE: &str = include_str!("obs_overlay.html");

/// _clamp_int(getattr(config, key, default), min, max): int() of the value, `min` when that fails
fn clamp_int(config: &Map<String, Value>, key: &str, default: i64, min: i64, max: i64) -> i64 {
    let number = match config.get(key) {
        None => Some(default),
        Some(Value::Bool(b)) => Some(*b as i64),
        Some(Value::Number(n)) => n.as_i64().or_else(|| n.as_f64().filter(|f| f.is_finite()).map(|f| f.trunc() as i64)),
        // ponytail: int(str) without underscores or non-ASCII digits
        Some(Value::String(s)) => pyfmt::strip(s).parse().ok(),
        Some(_) => None,
    };
    number.map_or(min, |n| n.clamp(min, max))
}

/// _normalize_hex_color(getattr(config, key, default), fallback)
fn hex_color(config: &Map<String, Value>, key: &str, default: &str, fallback: &str) -> String {
    let value = match config.get(key) {
        None => default,
        Some(Value::String(s)) => s,
        Some(_) => return fallback.into(),
    };
    let value = pyfmt::strip(value);
    let b = value.as_bytes();
    if b.len() == 7 && b[0] == b'#' && b[1..].iter().all(u8::is_ascii_hexdigit) { value.into() } else { fallback.into() }
}

/// _build_overlay_html(ws_token) with the config's values (keys as in config.py)
pub fn build_overlay_html(config: &Map<String, Value>, ws_token: &str) -> String {
    let values = [
        ("WEBSOCKET_PORT", clamp_int(config, "WEBSOCKET_PORT", 2231, 1, 65535).to_string()),
        ("OBS_BROWSER_SOURCE_MAX_MESSAGES", clamp_int(config, "OBS_BROWSER_SOURCE_MAX_MESSAGES", 14, 1, 50).to_string()),
        ("OBS_BROWSER_SOURCE_DISPLAY_DURATION", clamp_int(config, "OBS_BROWSER_SOURCE_DISPLAY_DURATION", 60, 1, 120).to_string()),
        ("OBS_BROWSER_SOURCE_FADEOUT_DURATION", clamp_int(config, "OBS_BROWSER_SOURCE_FADEOUT_DURATION", 12, 0, 120).to_string()),
        ("OBS_BROWSER_SOURCE_FONT_SIZE", clamp_int(config, "OBS_BROWSER_SOURCE_FONT_SIZE", 40, 10, 200).to_string()),
        ("OBS_BROWSER_SOURCE_FONT_COLOR", hex_color(config, "OBS_BROWSER_SOURCE_FONT_COLOR", "#FFFFFF", "#FFFFFF")),
        ("OBS_BROWSER_SOURCE_FONT_OUTLINE_THICKNESS",
         clamp_int(config, "OBS_BROWSER_SOURCE_FONT_OUTLINE_THICKNESS", 3, 0, 20).to_string()),
        ("OBS_BROWSER_SOURCE_FONT_OUTLINE_COLOR", hex_color(config, "OBS_BROWSER_SOURCE_FONT_OUTLINE_COLOR", "#000000", "#000000")),
        // URL-safe base64 only: nothing that breaks the JS string
        ("ws_token", ws_token.into()),
    ];
    values.iter().fold(TEMPLATE.to_string(), |page, (key, value)| page.replace(&format!("@@{key}@@"), value))
}

pub struct ObsServer {
    addr: SocketAddr,
    stop: Arc<AtomicBool>,
    thread: Option<std::thread::JoinHandle<()>>,
}

type Page = Arc<dyn Fn() -> String + Send + Sync>;

/// One request (ThreadingHTTPServer: a thread each), answered and closed as HTTP/1.0 did
fn answer(mut stream: TcpStream, page: Page) {
    let _ = stream.set_read_timeout(Some(Duration::from_secs(10)));
    let mut request = vec![];
    let mut buf = [0u8; 1024];
    while !request.windows(4).any(|w| w == b"\r\n\r\n") && request.len() < 65536 {
        match stream.read(&mut buf) {
            Ok(0) | Err(_) => return,
            Ok(n) => request.extend_from_slice(&buf[..n]),
        }
    }
    let line = String::from_utf8_lossy(&request);
    let mut words = line.lines().next().unwrap_or("").split(' ');
    let (method, target) = (words.next().unwrap_or(""), words.next().unwrap_or(""));
    let path = target.split(['?', '#']).next().unwrap_or("");
    let (status, body, kind) = match (method, path) {
        ("GET", "/" | "/obs") => ("200 OK", page(), Some("text/html; charset=utf-8")),
        ("GET", "/health") => ("200 OK", "ok".into(), Some("text/plain; charset=utf-8")),
        ("GET", _) => ("404 Not Found", String::new(), None),
        _ => ("501 Not Implemented", String::new(), None),
    };
    let mut head = format!("HTTP/1.1 {status}\r\n");
    if let Some(kind) = kind {
        head += &format!("Content-Type: {kind}\r\nCache-Control: no-store, max-age=0\r\n");
    }
    head += &format!("Content-Length: {}\r\nConnection: close\r\n\r\n", body.len());
    let _ = stream.write_all(head.as_bytes()).and_then(|()| stream.write_all(body.as_bytes()));
    let _ = stream.shutdown(Shutdown::Both);
}

impl ObsServer {
    /// Serves `/` and `/obs` (the page, made by `page` on every request so settings apply on
    /// reload) and `/health` on host:port (0: any free port)
    pub fn start(host: &str, port: u16, page: impl Fn() -> String + Send + Sync + 'static) -> anyhow::Result<Self> {
        let listener = TcpListener::bind((host, port))?;
        let addr = listener.local_addr()?;
        let stop = Arc::new(AtomicBool::new(false));
        let (page, flag): (Page, _) = (Arc::new(page), stop.clone());
        let thread = std::thread::Builder::new().name("obs_browser_source_server".into()).spawn(move || {
            for stream in listener.incoming() {
                if flag.load(Ordering::SeqCst) {
                    break;
                }
                if let Ok(stream) = stream {
                    let page = page.clone();
                    let _ = std::thread::Builder::new().name("obs_request".into()).spawn(move || answer(stream, page));
                }
            }
        })?;
        Ok(Self { addr, stop, thread: Some(thread) })
    }

    pub fn port(&self) -> u16 {
        self.addr.port()
    }
}

impl Drop for ObsServer {
    /// Stops listening before it returns (the port can be used again at once)
    fn drop(&mut self) {
        self.stop.store(true, Ordering::SeqCst);
        // wake the accept with a connection of our own
        let mut wake = self.addr;
        if wake.ip().is_unspecified() {
            wake.set_ip(std::net::Ipv4Addr::LOCALHOST.into());
        }
        let _ = TcpStream::connect_timeout(&wake, Duration::from_secs(1));
        if let Some(t) = self.thread.take() {
            let _ = t.join();
        }
    }
}
