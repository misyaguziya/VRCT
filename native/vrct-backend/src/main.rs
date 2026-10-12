//! VRCT-sidecar: the backend the UI starts (mainloop.py). Requests come on stdin, answers and
//! pushes go to stdout; nothing is written to stderr (the UI takes any line there for a fatal error).
use anyhow::Result;
use serde_json::Value;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;
use vrct_backend::app::{init, routes, App, Model};
use vrct_backend::config::{executable_dir, Config, DeviceLists, Env, RUST_HOST_NAME};
use vrct_backend::ipc::{self, Dispatcher};
use vrct_backend::{app, compute, logs, net, websocket};

const WORKERS: usize = 3;
/// After the UI stopped feeding the watchdog: the process ends this long after the shutdown began
const WATCHDOG_GRACE: Duration = Duration::from_secs(30);

/// The microphones and speakers now (device_manager.update with the Rust devices)
fn device_lists() -> DeviceLists {
    match vrct_audio::devices::list() {
        Ok(d) => DeviceLists {
            mic: if d.inputs.is_empty() { vec![] } else { vec![(config_host(), d.inputs.into_iter().map(|i| i.name).collect())] },
            speaker: d.loopbacks.into_iter().map(|i| i.name).collect(),
        },
        Err(e) => {
            logs::error("list devices", &e);
            DeviceLists::default()
        }
    }
}

fn config_host() -> String {
    RUST_HOST_NAME.to_string()
}

/// The defaults the PC gives (getDefaultMicDevice / getDefaultSpeakerDevice)
fn default_devices() -> ((String, String), String) {
    let none = || ("NoHost".to_string(), "NoDevice".to_string());
    match vrct_audio::devices::list() {
        Ok(d) => {
            let mic = d.default_input.filter(|n| d.inputs.iter().any(|i| &i.name == n)).map_or_else(none, |n| (config_host(), n));
            let speaker = d.default_loopback.filter(|n| d.loopbacks.iter().any(|i| &i.name == n)).unwrap_or_else(|| "NoDevice".into());
            (mic, speaker)
        }
        Err(_) => (none(), "NoDevice".into()),
    }
}

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
    let (default_mic, default_speaker) = default_devices();
    let config = Config::new(Env {
        path_local: local.clone(),
        compute_devices: compute::device_list(),
        default_mic,
        default_speaker,
        devices: Arc::new(device_lists),
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
