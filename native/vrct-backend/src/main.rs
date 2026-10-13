//! VRCT-sidecar: the backend the UI starts (mainloop.py). Requests come on stdin, answers and
//! pushes go to stdout; nothing is written to stderr (the UI takes any line there for a fatal error).
use anyhow::Result;
use serde_json::Value;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;
use vrct_backend::app::{init, routes, App, Model};
use vrct_backend::config::{executable_dir, Config, Env};
use vrct_backend::ipc::{self, Dispatcher};
use vrct_backend::{app, compute, logs, net, websocket};

const WORKERS: usize = 3;
/// After the UI stopped feeding the watchdog: the process ends this long after the shutdown began
const WATCHDOG_GRACE: Duration = Duration::from_secs(30);

/// A panic is logged (error.log, and crash_trace.log as faulthandler did), never printed to stderr
fn panic_hook() {
    std::panic::set_hook(Box::new(|info| {
        let thread = std::thread::current().name().unwrap_or("?").to_string();
        let backtrace = std::backtrace::Backtrace::force_capture();
        let message = format!("panic in thread {thread}: {info}\n{backtrace}");
        logs::error("panic", &message);
        use std::io::Write;
        if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open("crash_trace.log") {
            let _ = writeln!(f, "{message}");
        }
    }));
}

fn main() -> Result<()> {
    let local = executable_dir();
    // config.json, the logs and the weights are beside the executable, as the frozen Python build
    std::env::set_current_dir(&local)?;
    panic_hook();
    // what the native libraries print (CTranslate2's logs, drivers) goes to error.log
    vrct_ct2::redirect_stderr(&PathBuf::from("error.log"));

    let transcription_lang: Value = serde_json::from_str(include_str!("../../data/transcription_languages.json"))?;
    let devices = vrct_backend::devices::snapshot();
    let config = Config::new(Env {
        path_local: local.clone(),
        compute_devices: compute::device_list(),
        default_mic: devices.default_mic,
        default_speaker: devices.default_speaker,
        devices: Arc::new(|| vrct_backend::devices::snapshot().lists()),
        transcription_lang: transcription_lang.clone(),
        new_token: websocket::new_auth_token,
    });
    config.load();

    let http = net::Http::new()?;
    let model = Model::new(http, app::Resources { dir: local }, transcription_lang, &config)?;
    let app = App::new(config, model);
    app::register_error_hook(&app);

    let dispatcher = Dispatcher::new(app.clone(), routes::routes());
    dispatcher.start_receiver();
    dispatcher.start_workers(WORKERS);

    // escalateShutdown: once; the process ends after the shutdown, or WATCHDOG_GRACE at the latest
    let escalated = Arc::new(AtomicBool::new(false));
    let me = app.me();
    let escalate = move || {
        if escalated.swap(true, Ordering::SeqCst) {
            return;
        }
        std::thread::spawn(|| {
            std::thread::sleep(WATCHDOG_GRACE);
            std::process::exit(1);
        });
        let me = me.clone();
        std::thread::spawn(move || {
            if let Some(app) = me.upgrade() {
                let _ = init::shutdown(&app, None);
            }
            std::process::exit(0);
        });
    };
    // an exception out of Controller.init ended the Python process (the UI shows it closed)
    if let Err(e) = init::init(&app, escalate) {
        logs::error("init", &format!("{e:#}"));
        ipc::log(format!("Initialization failed: {e:#}"));
        std::process::exit(1);
    }
    dispatcher.set_initialized();
    loop {
        std::thread::sleep(Duration::from_secs(1));
    }
}
