//! The IPC with the UI (mainloop.py / utils.py; docs/rust_backend_design_2026-10-11.md §3).
//!
//! In: one line of stdin = {"endpoint": str, "data": base64(JSON) | null}. Out: one line of stdout =
//! {"status", "endpoint", "result"} for answers and pushes, {"status": 348, "log", "data"} for logs
//! (the UI drops them). One thread writes stdout: answers are never dropped and go first, logs wait
//! in a queue of 200 (the oldest dropped). 50 failed writes in a row: the UI is gone, the process ends.
//! Requests go to a few workers. A feature's enable / disable share one lock (one at a time; busy:
//! requeued every 50 ms, 423 after ~20 s). Endpoints not ready during initialization answer 423 after
//! being requeued every 100 ms for ~30 s.
use crate::{logs, pyjson};
use base64::Engine as _;
use serde_json::{json, Value};
use std::collections::{HashMap, VecDeque};
use std::io::{BufRead, Write};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Condvar, Mutex, OnceLock};
use std::time::Duration;

const LOG_QUEUE_MAX: usize = 200;
const MAX_CONSECUTIVE_STDOUT_FAILURES: u32 = 50;
const LOCK_BUSY_RETRY: Duration = Duration::from_millis(50);
const LOCK_BUSY_MAX_RETRIES: u32 = 400;
const ENDPOINT_LOCKED_RETRY: Duration = Duration::from_millis(100);
const ENDPOINT_LOCKED_MAX_RETRIES: u32 = 300;
/// Answers sent so often they are kept out of process.log (the VR UI's pointer)
const UNLOGGED_ENDPOINTS: [&str; 1] = ["/run/vr_panel_pointer"];
const SENSITIVE_MARKERS: [&str; 5] = ["auth_key", "api_key", "password", "token", "secret"];
const MASKED: &str = "***MASKED***";

// ------------------------------------------------------------------------------------- output

#[derive(Default)]
struct Lines {
    answers: VecDeque<String>,
    logs: VecDeque<String>,
}

struct Out {
    lines: Mutex<Lines>,
    ready: Condvar,
}

fn out() -> &'static Out {
    static OUT: OnceLock<Out> = OnceLock::new();
    OUT.get_or_init(|| {
        std::thread::Builder::new().name("stdout".into()).spawn(writer).expect("stdout writer");
        Out { lines: Mutex::new(Lines::default()), ready: Condvar::new() }
    })
}

/// The writing thread: answers first, then logs
fn writer() {
    let out = out();
    let mut failures = 0;
    loop {
        let line = {
            let mut lines = out.lines.lock().unwrap();
            loop {
                if let Some(line) = lines.answers.pop_front().or_else(|| lines.logs.pop_front()) {
                    break line;
                }
                lines = out.ready.wait(lines).unwrap();
            }
        };
        let mut stdout = std::io::stdout().lock();
        if stdout.write_all(line.as_bytes()).and_then(|()| stdout.write_all(b"\n")).and_then(|()| stdout.flush()).is_ok() {
            failures = 0;
            continue;
        }
        failures += 1;
        logs::ERROR.write("stdout: write failed");
        if failures >= MAX_CONSECUTIVE_STDOUT_FAILURES {
            // the UI is gone
            std::process::exit(1);
        }
    }
}

fn push_answer(line: String) {
    let out = out();
    out.lines.lock().unwrap().answers.push_back(line);
    out.ready.notify_one();
}

fn push_log(line: String) {
    let out = out();
    let mut lines = out.lines.lock().unwrap();
    if lines.logs.len() >= LOG_QUEUE_MAX {
        lines.logs.pop_front();
    }
    lines.logs.push_back(line);
    drop(lines);
    out.ready.notify_one();
}

/// _isSensitiveEndpoint: a name (endpoint or log label, spaces as "_") with a secret's marker
pub fn is_sensitive(name: &str) -> bool {
    let lowered = name.to_lowercase().replace(' ', "_");
    SENSITIVE_MARKERS.iter().any(|m| lowered.contains(m))
}

fn mask_value(value: &Value) -> Value {
    match value {
        Value::Null => Value::Null,
        Value::String(s) if s.is_empty() => value.clone(),
        _ => Value::String(MASKED.into()),
    }
}

/// _maskSensitiveData: values under secret-looking keys, all the way down
fn mask_data(value: &Value) -> Value {
    match value {
        Value::Object(map) => {
            Value::Object(map.iter().map(|(k, v)| (k.clone(), if is_sensitive(k) { mask_value(v) } else { mask_data(v) })).collect())
        }
        Value::Array(items) => Value::Array(items.iter().map(mask_data).collect()),
        _ => value.clone(),
    }
}

/// printLog: process.log and a 348 line (the data masked under a secret's label)
pub fn print_log(log: &str, data: &Value) {
    let data = if is_sensitive(log) { mask_value(data) } else { data.clone() };
    let line = json!({"status": 348, "log": log, "data": pyjson::py_str(&data)});
    logs::PROCESS.write(&pyjson::repr(&line));
    push_log(pyjson::dumps(&line, None, true));
}

/// printLog(text) with no data
pub fn log(text: impl AsRef<str>) {
    print_log(text.as_ref(), &Value::Null);
}

/// printResponse: an answer or a push (logged masked, sent as it is)
pub fn print_response(status: i64, endpoint: Option<&str>, result: &Value) {
    let endpoint_value = endpoint.map_or(Value::Null, |e| Value::String(e.into()));
    if !endpoint.is_some_and(|e| UNLOGGED_ENDPOINTS.contains(&e)) {
        let logged = if endpoint.is_some_and(is_sensitive) { mask_value(result) } else { mask_data(result) };
        logs::PROCESS.write(&pyjson::repr(&json!({"status": status, "endpoint": endpoint_value, "result": logged})));
    }
    push_answer(pyjson::dumps(&json!({"status": status, "endpoint": endpoint_value, "result": result}), None, true));
}

// ------------------------------------------------------------------------------------- requests

/// A handler's answer ({"status", "result"})
#[derive(Clone, Debug, PartialEq)]
pub struct Reply {
    pub status: i64,
    pub result: Value,
}

impl Reply {
    pub fn ok(result: impl Into<Value>) -> Reply {
        Reply { status: 200, result: result.into() }
    }
}

pub type Handler<C> = fn(&C, Option<Value>) -> anyhow::Result<Reply>;

/// An endpoint: its handler and whether it answers while the backend initializes
pub struct Route<C> {
    pub during_init: bool,
    pub handler: Handler<C>,
}

struct Request {
    endpoint: Option<String>,
    data: Option<Value>,
    attempt: u32,
}

/// The receiving thread, the workers and the locks
pub struct Dispatcher<C: Send + Sync + 'static> {
    context: Arc<C>,
    routes: HashMap<&'static str, Route<C>>,
    locks: HashMap<String, Mutex<()>>,
    queue: Mutex<VecDeque<Request>>,
    ready: Condvar,
    initialized: AtomicBool,
}

/// enable / disable of a feature share a lock
fn lock_key(endpoint: &str) -> String {
    for prefix in ["/set/enable/", "/set/disable/"] {
        if let Some(rest) = endpoint.strip_prefix(prefix) {
            return format!("/lock/set/{rest}");
        }
    }
    endpoint.to_string()
}

impl<C: Send + Sync + 'static> Dispatcher<C> {
    pub fn new(context: Arc<C>, routes: Vec<(&'static str, Route<C>)>) -> Arc<Self> {
        let locks = routes.iter().map(|(e, _)| (lock_key(e), Mutex::new(()))).collect();
        Arc::new(Self {
            context,
            routes: routes.into_iter().collect(),
            locks,
            queue: Mutex::new(VecDeque::new()),
            ready: Condvar::new(),
            initialized: AtomicBool::new(false),
        })
    }

    pub fn routes(&self) -> impl Iterator<Item = (&&'static str, &Route<C>)> {
        self.routes.iter()
    }

    /// Every endpoint answers from now on
    pub fn set_initialized(&self) {
        self.initialized.store(true, Ordering::SeqCst);
    }

    fn enqueue(&self, request: Request) {
        self.queue.lock().unwrap().push_back(request);
        self.ready.notify_one();
    }

    /// receiver: stdin lines to the queue. At the end of input it keeps waiting (the watchdog ends
    /// the process when the UI is gone).
    pub fn start_receiver(self: &Arc<Self>) {
        let this = self.clone();
        std::thread::Builder::new().name("main_receiver".into()).spawn(move || {
            let mut stdin = std::io::stdin().lock();
            let mut line = String::new();
            loop {
                line.clear();
                match stdin.read_line(&mut line) {
                    Ok(0) | Err(_) => {
                        std::thread::sleep(Duration::from_millis(100));
                        continue;
                    }
                    Ok(_) => {}
                }
                let received: Value = match serde_json::from_str(line.trim()) {
                    Ok(v) => v,
                    Err(e) => {
                        logs::error("receiver: JSONDecodeError", &e);
                        continue;
                    }
                };
                // falsy ({} / null / ...) is dropped, as `if received_data:`
                let Some(object) = received.as_object().filter(|o| !o.is_empty()) else { continue };
                let endpoint = object.get("endpoint").and_then(Value::as_str).map(String::from);
                let data = object.get("data").filter(|d| !d.is_null()).map(decode_data);
                print_log(endpoint.as_deref().unwrap_or("None"), &json!({"receive_data": data}));
                this.enqueue(Request { endpoint, data, attempt: 0 });
            }
        }).expect("receiver thread");
    }

    pub fn start_workers(self: &Arc<Self>, count: usize) {
        for i in 0..count.max(1) {
            let this = self.clone();
            std::thread::Builder::new().name(format!("main_handler_{i}")).spawn(move || this.worker()).expect("worker thread");
        }
    }

    fn call(&self, endpoint: Option<&str>, data: Option<Value>) -> (i64, Value) {
        // the result of an unknown or locked endpoint is None ("Invalid endpoint" / "Locked endpoint"
        // were never sent)
        let Some(route) = endpoint.and_then(|e| self.routes.get(e)) else { return (404, Value::Null) };
        if !route.during_init && !self.initialized.load(Ordering::SeqCst) {
            return (423, Value::Null);
        }
        let handler = route.handler;
        let context = &self.context;
        match std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| handler(context, data))) {
            Ok(Ok(reply)) => (reply.status, reply.result),
            Ok(Err(e)) => {
                logs::error(endpoint.unwrap_or("None"), &format!("{e:#}"));
                (500, json!("Internal error"))
            }
            // the panic hook logged it
            Err(_) => (500, json!("Internal error")),
        }
    }

    fn worker(&self) {
        loop {
            let request = {
                let mut queue = self.queue.lock().unwrap();
                loop {
                    if let Some(r) = queue.pop_front() {
                        break r;
                    }
                    queue = self.ready.wait(queue).unwrap();
                }
            };
            let endpoint = request.endpoint.clone();
            let key = endpoint.as_deref().map(lock_key);
            let (status, result) = match key.as_ref().and_then(|k| self.locks.get(k)) {
                Some(lock) => {
                    let Ok(_guard) = lock.try_lock() else {
                        // the same feature is busy
                        if request.attempt >= LOCK_BUSY_MAX_RETRIES {
                            let e = endpoint.as_deref().unwrap_or("None");
                            log(format!("{e}: lock busy retry limit ({LOCK_BUSY_MAX_RETRIES}) exceeded; responding 423"));
                            print_log(e, &json!({"status": 423, "send_data": "Locked endpoint (busy)"}));
                            print_response(423, endpoint.as_deref(), &json!("Locked endpoint (busy)"));
                            continue;
                        }
                        std::thread::sleep(LOCK_BUSY_RETRY);
                        self.enqueue(Request { attempt: request.attempt + 1, ..request });
                        continue;
                    };
                    self.call(endpoint.as_deref(), request.data.clone())
                }
                None => self.call(endpoint.as_deref(), request.data.clone()),
            };
            let label = endpoint.as_deref().unwrap_or("None");
            if status == 423 && request.attempt < ENDPOINT_LOCKED_MAX_RETRIES {
                std::thread::sleep(ENDPOINT_LOCKED_RETRY);
                self.enqueue(Request { attempt: request.attempt + 1, ..request });
                continue;
            }
            if status == 423 {
                log(format!("{label}: endpoint-locked retry limit ({ENDPOINT_LOCKED_MAX_RETRIES}) exceeded; responding 423"));
            }
            print_log(label, &json!({"status": status, "send_data": result}));
            print_response(status, endpoint.as_deref(), &result);
        }
    }
}

/// encodeBase64: base64 JSON, {} when it is not
fn decode_data(data: &Value) -> Value {
    let decoded = data.as_str().ok_or_else(|| anyhow::anyhow!("data is not a string")).and_then(|s| {
        let bytes = base64::engine::general_purpose::STANDARD.decode(s)?;
        Ok(serde_json::from_slice::<Value>(&bytes)?)
    });
    decoded.unwrap_or_else(|e| {
        logs::error("encodeBase64", &e);
        json!({})
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn masks_like_python() {
        assert!(is_sensitive("/set/data/openrouter_auth_key"));
        assert!(is_sensitive("Set OpenRouter Auth Key"));
        assert!(!is_sensitive("/get/data/ui_language"));
        let v = json!({"/get/data/deepl_auth_key": "k", "/get/data/x": {"token": "", "a": [{"secret": 1}]}, "n": null});
        assert_eq!(mask_data(&v), json!({"/get/data/deepl_auth_key": MASKED, "/get/data/x": {"token": "", "a": [{"secret": MASKED}]}, "n": null}));
        assert_eq!(lock_key("/set/enable/translation"), "/lock/set/translation");
        assert_eq!(lock_key("/set/disable/translation"), "/lock/set/translation");
        assert_eq!(lock_key("/get/data/x"), "/get/data/x");
        assert_eq!(decode_data(&json!("eyJhIjogMX0=")), json!({"a": 1}));
        assert_eq!(decode_data(&json!("!!")), json!({}));
    }
}
