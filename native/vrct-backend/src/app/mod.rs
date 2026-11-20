//! The application (controller.py / model.py): the settings, the services, the endpoints' handlers
//! and the start / shutdown sequences. Handlers take the request's data and answer
//! {"status", "result"}; pushes go out through `run` (run_mapping's names).
pub mod getters;
mod audio;
mod basic;
mod engines;
mod features;
pub mod init;
mod keyboard;
mod model;
mod ocr;
pub mod overlay;
mod pipeline;
mod services;
mod transcription_api;
mod translation_api;
pub mod routes;

pub use model::{Model, Resources};

use crate::config::Config;
use crate::errors;
use crate::ipc::{self, Reply};
use anyhow::{anyhow, Result};
use serde_json::Value;
use std::sync::{Arc, Weak};

/// Every handler, by the snake_case of its Controller method's name
pub mod handlers {
    pub use super::audio::*;
    pub use super::basic::*;
    pub use super::engines::*;
    pub use super::features::*;
    pub use super::init::shutdown;
    pub use super::keyboard::*;
    pub use super::ocr::*;
    pub use super::overlay::*;
    pub use super::pipeline::{send_message_box, set_enable_translation};
    pub use super::getters::*;
    pub use super::transcription_api::*;
    pub use super::translation_api::*;
}

pub struct App {
    pub config: Config,
    pub model: Model,
    /// The microphone and the speaker (their sessions are the lifecycle locks)
    pub audio: audio::Audio,
    me: Weak<App>,
}

impl App {
    pub fn new(config: Config, model: Model) -> Arc<App> {
        Arc::new_cyclic(|me| {
            let _ = model.overlay_app.set(me.clone());
            App { config, model, audio: audio::Audio::default(), me: me.clone() }
        })
    }

    /// For the threads and callbacks that outlive a request
    pub fn me(&self) -> Weak<App> {
        self.me.clone()
    }

    /// self.run(status, self.run_mapping[name], result): a name not in run_mapping fails as the
    /// KeyError did (the handler answers 500)
    pub fn run(&self, status: i64, name: &str, result: impl Into<Value>) -> Result<()> {
        let endpoint = routes::run_endpoint(name)
            .ok_or_else(|| anyhow!("KeyError: {name:?} is not in run_mapping"))?;
        ipc::print_response(status, Some(endpoint), &result.into());
        Ok(())
    }

    /// self.run_mapping.get(name, default) (the device-loss pushes)
    pub fn run_or(&self, status: i64, name: &str, default: &str, result: impl Into<Value>) {
        let endpoint = routes::run_endpoint(name).unwrap_or(default);
        ipc::print_response(status, Some(endpoint), &result.into());
    }

    /// An error response pushed to `name` (VRCTError.create_error_response then self.run)
    pub fn run_error(&self, name: &str, code: &str, data: Value) -> Result<()> {
        let reply = errors::error(code, data);
        self.run(reply.status, name, reply.result)
    }
}

/// {"status": 200, "result": config.NAME}
pub fn current(app: &App, name: &str) -> Result<Reply> {
    Ok(Reply::ok(app.config.get(name)))
}

/// The tests' App: as main.rs makes it, with config.json in a fresh folder, the data from
/// native/data, OSC to a port on this PC (a socket the test reads) and no devices
#[cfg(test)]
pub(crate) fn test_app(osc_port: u16) -> Arc<App> {
    test_app_with(osc_port, crate::net::Http::new().unwrap())
}

/// `test_app` with its HTTP (e.g. `Http::redirected` to `test_server`)
#[cfg(test)]
pub(crate) fn test_app_with(osc_port: u16, http: crate::net::Http) -> Arc<App> {
    use crate::config::{DeviceLists, Env};
    use serde_json::json;
    static RUN: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
    let n = RUN.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
    let dir = std::env::temp_dir().join(format!("vrct-app-test-{}-{n}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let data = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../data");
    let transcription_lang: Value = serde_json::from_slice(&std::fs::read(data.join("transcription_languages.json")).unwrap()).unwrap();
    let config = Config::new(Env {
        path_local: dir,
        compute_devices: vec![json!({"device": "cpu", "device_index": 0, "device_name": "cpu", "compute_types": ["auto", "int8"]})],
        default_mic: ("NoHost".into(), "NoDevice".into()),
        default_speaker: "NoDevice".into(),
        devices: Arc::new(DeviceLists::default),
        transcription_lang: transcription_lang.clone(),
        new_token: || "token".into(),
    });
    config.set("OSC_PORT", json!(osc_port)).unwrap();
    let model = Model::new(http, Resources { dir: data }, transcription_lang, &config).unwrap();
    App::new(config, model)
}

/// A local HTTP server for the tests, answering each request's path with `respond`; its root
/// (for `Http::redirected`). ponytail: it runs until the test process ends.
#[cfg(test)]
pub(crate) fn test_server(respond: impl Fn(&str) -> (u16, Vec<u8>) + Send + 'static) -> String {
    let server = tiny_http::Server::http("127.0.0.1:0").unwrap();
    let root = format!("http://{}", server.server_addr().to_ip().unwrap());
    std::thread::spawn(move || {
        for request in server.incoming_requests() {
            let (status, body) = respond(request.url());
            let _ = request.respond(tiny_http::Response::from_data(body).with_status_code(status));
        }
    });
    root
}

/// register_error_report_hook(model.telemetryTrackError): every error code goes to telemetry
pub fn register_error_hook(app: &std::sync::Arc<App>) {
    let me = app.me();
    errors::register_hook(move |code| {
        if let Some(app) = me.upgrade() {
            app.model.telemetry.track_error(code);
        }
    });
}
