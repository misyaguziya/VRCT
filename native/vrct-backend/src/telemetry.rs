//! Telemetry (models/telemetry of the removed Python backend + the aptabase 0.1.0 SDK it wraps): "app_started" once a
//! day and "error" once a day per error code, deduplicated with the state file v3.6.x wrote
//! (telemetry_state.json). Events are queued and sent in batches of up to 25 every 10 s and at shutdown.
//!
//! Kept as the Python version sends it: osVersion is "10" (Python 3.11's platform.release() on
//! Windows 10 and 11). Changed from it: the event timestamp is UTC (the SDK sent local time with a
//! "Z"), and enabling telemetry while running starts sending (the SDK started only on the first init).
use crate::net::{Body, Http};
use reqwest::Method;
use serde_json::{json, Map, Value};
use std::path::{Path, PathBuf};
use std::sync::{mpsc, Arc, Condvar, Mutex, MutexGuard};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

const MAX_BATCH: usize = 25;
const FLUSH_INTERVAL: Duration = Duration::from_secs(10);
const SEND_TIMEOUT: Duration = Duration::from_secs(30);
const SESSION_TIMEOUT: Duration = Duration::from_secs(3600);
/// Python waited 5 s for the client to stop and 5 s for its loop to end
const STOP_WAIT: Duration = Duration::from_secs(10);

/// date.today().isoformat()
pub fn today() -> String {
    chrono::Local::now().format("%Y-%m-%d").to_string()
}

/// The event's time: UTC, ISO 8601 with microseconds and "Z"
fn utc_iso_now() -> String {
    chrono::Utc::now().format("%Y-%m-%dT%H:%M:%S%.6fZ").to_string()
}

/// The daily dedup state (models/telemetry/state.py)
struct State {
    path: Option<PathBuf>,
    data: Map<String, Value>,
}

impl State {
    fn load(path: Option<PathBuf>) -> Self {
        let mut data = Map::new();
        let loaded = path.as_ref().and_then(|p| std::fs::read(p).ok()).and_then(|b| serde_json::from_slice::<Value>(&b).ok());
        let loaded = loaded.as_ref().and_then(Value::as_object);
        data.insert("last_app_started_date".into(), loaded.and_then(|o| o.get("last_app_started_date")).cloned().unwrap_or(Value::Null));
        // `loaded.get("errors_sent") or {}`
        let errors = loaded.and_then(|o| o.get("errors_sent")).and_then(Value::as_object).cloned().unwrap_or_default();
        data.insert("errors_sent".into(), Value::Object(errors));
        Self { path, data }
    }

    fn save(&self) {
        let Some(path) = &self.path else { return };
        if let Some(parent) = path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        // json.dump(indent=2, ensure_ascii=False)
        let _ = std::fs::write(path, serde_json::to_string_pretty(&self.data).unwrap());
    }

    fn errors_today(&self, today: &str) -> Vec<Value> {
        self.data["errors_sent"].get(today).and_then(Value::as_array).cloned().unwrap_or_default()
    }

    fn should_send_app_started_today(&self) -> bool {
        self.data["last_app_started_date"] != today()
    }

    fn mark_app_started_sent_today(&mut self) {
        let today = today();
        let errors = self.errors_today(&today);
        let pruned = if self.data["errors_sent"].get(&today).is_some() { json!({ &today: errors }) } else { json!({}) };
        self.data.insert("last_app_started_date".into(), json!(today));
        self.data.insert("errors_sent".into(), pruned);
        self.save();
    }

    fn should_send_error_today(&self, code: &str) -> bool {
        !self.errors_today(&today()).contains(&json!(code))
    }

    fn mark_error_sent_today(&mut self, code: &str) {
        let today = today();
        let mut errors = self.errors_today(&today);
        if !errors.contains(&json!(code)) {
            errors.push(json!(code));
        }
        self.data.insert("errors_sent".into(), json!({ &today: errors }));
        self.save();
    }
}

struct Queue {
    events: Vec<Value>,
    stop: Option<bool>, // Some(flush)
}

/// The Aptabase client: a thread that sends the queue
struct Client {
    shared: Arc<(Mutex<Queue>, Condvar)>,
    done: mpsc::Receiver<()>,
    app_version: String,
    session: Option<(String, Instant)>,
}

impl Client {
    /// None when the key is missing or not an EU / US key (the SDK refused it and nothing was sent)
    fn start(http: &Http, app_key: Option<&str>, app_version: &str) -> Option<Self> {
        let key = app_key?.to_string();
        let parts: Vec<&str> = key.split('-').collect();
        let host = match (parts.len(), parts.first(), parts.get(1)) {
            (3, Some(&"A"), Some(&"EU")) => "https://eu.aptabase.com",
            (3, Some(&"A"), Some(&"US")) => "https://us.aptabase.com",
            _ => return None,
        };
        let url = format!("{host}/api/v0/events");
        let shared = Arc::new((Mutex::new(Queue { events: vec![], stop: None }), Condvar::new()));
        let (done_tx, done) = mpsc::channel();
        let (http, s) = (http.clone(), shared.clone());
        std::thread::Builder::new().name("telemetry".into()).spawn(move || {
            let (lock, wake) = &*s;
            let mut queue = lock.lock().unwrap();
            let mut next = Instant::now() + FLUSH_INTERVAL;
            loop {
                if let Some(flush) = queue.stop {
                    if flush {
                        drop(send_batch(lock, queue, &http, &url, &key));
                    }
                    break;
                }
                let now = Instant::now();
                if now >= next || queue.events.len() >= MAX_BATCH {
                    queue = send_batch(lock, queue, &http, &url, &key);
                    if now >= next {
                        next = now + FLUSH_INTERVAL;
                    }
                    continue;
                }
                queue = wake.wait_timeout(queue, next - now).unwrap().0;
            }
            let _ = done_tx.send(());
        }).ok()?;
        Some(Self { shared, done, app_version: app_version.into(), session: None })
    }

    fn track(&mut self, name: &str, props: Value) {
        let now = Instant::now();
        let session = match self.session.take() {
            Some((id, last)) if now - last <= SESSION_TIMEOUT => id,
            _ => {
                let t = SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default();
                (t.as_secs() * 100_000_000 + (t.subsec_nanos() % 100_000_000) as u64).to_string()
            }
        };
        self.session = Some((session.clone(), now));
        let event = json!({
            "timestamp": utc_iso_now(),
            "sessionId": session,
            "eventName": name,
            "systemProps": {"locale": "en-US", "osName": "Windows", "osVersion": "10", "deviceModel": "AMD64",
                            "isDebug": false, "appVersion": self.app_version, "sdkVersion": "aptabase-python@0.1.0"},
            "props": props,
        });
        let (lock, wake) = &*self.shared;
        lock.lock().unwrap().events.push(event);
        wake.notify_one();
    }

    /// Stops the thread, sending one more batch first when `flush`
    fn stop(self, flush: bool) {
        let (lock, wake) = &*self.shared;
        lock.lock().unwrap().stop = Some(flush);
        wake.notify_one();
        let _ = self.done.recv_timeout(STOP_WAIT);
    }
}

/// Sends up to 25 queued events without holding the lock; on failure they go back to the front
fn send_batch<'a>(lock: &'a Mutex<Queue>, mut queue: MutexGuard<'a, Queue>, http: &Http, url: &str, key: &str)
                  -> MutexGuard<'a, Queue> {
    let n = queue.events.len().min(MAX_BATCH);
    let batch: Vec<Value> = queue.events.drain(..n).collect();
    if batch.is_empty() {
        return queue;
    }
    drop(queue);
    let ok = http.send(Method::POST, url, &[("App-Key", key.to_string())], Some(Body::Json(json!(batch))), Some(SEND_TIMEOUT))
        .is_ok_and(|r| r.status().is_success());
    let mut queue = lock.lock().unwrap();
    if !ok {
        queue.events.splice(0..0, batch);
    }
    queue
}

struct Inner {
    enabled: bool,
    state: State,
    client: Option<Client>,
}

/// models/telemetry.Telemetry
pub struct Telemetry {
    http: Http,
    app_key: Option<String>,
    inner: Mutex<Inner>,
}

impl Telemetry {
    /// `app_key`: the build's Aptabase key (none in forks and local builds: nothing is sent)
    pub fn new(http: Http, app_key: Option<String>) -> Self {
        let inner = Inner { enabled: true, state: State::load(None), client: None };
        Self { http, app_key, inner: Mutex::new(inner) }
    }

    /// Starts sending when enabled (if not sending yet), with "app_started" unless it was sent
    /// today; when disabled, stops sending and drops what is queued.
    pub fn init(&self, enabled: bool, app_version: &str, storage_path: Option<&Path>) {
        let stopped = {
            let mut i = self.inner.lock().unwrap();
            if let Some(path) = storage_path {
                i.state = State::load(Some(path.to_path_buf()));
            }
            i.enabled = enabled;
            if !enabled {
                i.client.take()
            } else {
                if i.client.is_none() {
                    i.client = Client::start(&self.http, self.app_key.as_deref(), app_version);
                    if i.state.should_send_app_started_today() {
                        if let Some(c) = &mut i.client {
                            c.track("app_started", json!({}));
                        }
                        i.state.mark_app_started_sent_today();
                    }
                }
                None
            }
        };
        // outside the lock: the thread may be in the middle of a send
        if let Some(c) = stopped {
            c.stop(false);
        }
    }

    /// Sends what is queued (when enabled) and stops
    pub fn shutdown(&self) {
        let (client, enabled) = {
            let mut i = self.inner.lock().unwrap();
            (i.client.take(), i.enabled)
        };
        if let Some(c) = client {
            c.stop(enabled);
        }
    }

    /// "error" with `error_code`, once a day per code (marked before it is sent, also when nothing sends)
    pub fn track_error(&self, error_code: &str) {
        let mut i = self.inner.lock().unwrap();
        if !i.enabled || error_code.is_empty() || !i.state.should_send_error_today(error_code) {
            return;
        }
        i.state.mark_error_sent_today(error_code);
        if let Some(c) = &mut i.client {
            c.track("error", json!({"error_code": error_code}));
        }
    }

    pub fn is_enabled(&self) -> bool {
        self.inner.lock().unwrap().enabled
    }
}
