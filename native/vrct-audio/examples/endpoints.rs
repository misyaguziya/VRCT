//! Watches endpoint changes and the playing output for a few seconds (peak levels only).
//!     cargo run --example endpoints --features devices [seconds]
use std::time::Duration;
use vrct_audio::endpoints::{ActiveEndpointTracker, DeviceWatcher, Flow};

fn main() {
    let seconds: u64 = std::env::args().nth(1).and_then(|s| s.parse().ok()).unwrap_or(4);
    let _watcher = DeviceWatcher::start(|| println!("endpoint change")).unwrap();
    let tracker = ActiveEndpointTracker::start(Flow::Render, |name| println!("playing: {name:?}"));
    std::thread::sleep(Duration::from_secs(seconds));
    println!("last: {:?}", tracker.active_endpoint_name());
}
