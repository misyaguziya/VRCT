//! The application (controller.py / model.py): the settings, the services, the endpoints' handlers
//! and the start / shutdown sequences. Handlers take the request's data and answer
//! {"status", "result"}; pushes go out through `run` (run_mapping's names).
pub mod getters;
mod audio;
mod basic;
mod engines;
mod features;
pub mod init;
mod model;
mod ocr;
mod overlay;
mod pipeline;
mod pending;
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
use std::sync::{Arc, Mutex, Weak};

/// Every handler, by the snake_case of its Controller method's name
pub mod handlers {
    pub use super::audio::*;
    pub use super::basic::*;
    pub use super::engines::*;
    pub use super::features::*;
    pub use super::init::shutdown;
    pub use super::ocr::*;
    pub use super::pipeline::{send_message_box, set_enable_translation};
    pub use super::getters::*;
    pub use super::pending::*;
    pub use super::transcription_api::*;
    pub use super::translation_api::*;
}

pub struct App {
    pub config: Config,
    pub model: Model,
    /// The microphone's and the speaker's start / stop, one at a time (mic_lifecycle_lock)
    pub mic_lifecycle: Mutex<()>,
    pub speaker_lifecycle: Mutex<()>,
    me: Weak<App>,
}

impl App {
    pub fn new(config: Config, model: Model) -> Arc<App> {
        Arc::new_cyclic(|me| App { config, model, mic_lifecycle: Mutex::new(()), speaker_lifecycle: Mutex::new(()), me: me.clone() })
    }

    /// For the threads and callbacks that outlive a request
    pub fn me(&self) -> Weak<App> {
        self.me.clone()
    }

    /// self.run(status, self.run_mapping[name], result): a name not in run_mapping fails as the
    /// KeyError did (the handler answers 500)
    pub fn run(&self, status: i64, name: &str, result: impl Into<Value>) -> Result<()> {
        let endpoint = routes::RUN_MAPPING.iter().find(|(n, _)| *n == name).map(|(_, e)| *e)
            .ok_or_else(|| anyhow!("KeyError: {name:?} is not in run_mapping"))?;
        ipc::print_response(status, Some(endpoint), &result.into());
        Ok(())
    }

    /// self.run_mapping.get(name, default) (the device-loss pushes)
    pub fn run_or(&self, status: i64, name: &str, default: &str, result: impl Into<Value>) {
        let endpoint = routes::RUN_MAPPING.iter().find(|(n, _)| *n == name).map_or(default, |(_, e)| *e);
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

/// register_error_report_hook(model.telemetryTrackError): every error code goes to telemetry
pub fn register_error_hook(app: &std::sync::Arc<App>) {
    let me = app.me();
    errors::register_hook(move |code| {
        if let Some(app) = me.upgrade() {
            app.model.telemetry.track_error(code);
        }
    });
}
