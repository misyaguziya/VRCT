//! The app name the clipboard pastes into (Clipboard.app_name), read from a running SteamVR.
//!     cargo run -p vrct-backend --example clipboard_app_name
use std::time::{Duration, Instant};

fn main() {
    let name = vrct_backend::clipboard::AppName::watch(|line| println!("{line}"));
    let started = Instant::now();
    while name.get().is_none() && started.elapsed() < Duration::from_secs(5) {
        std::thread::sleep(Duration::from_millis(100));
    }
    println!("app_name {:?}", name.get());
}
