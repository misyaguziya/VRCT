//! A check with VRChat of the OSC receiving side (osc::OscReceiver), the way VRCT uses it:
//! advertises "VRCT:<time>" by mDNS, prints MuteSelf and avatar changes as VRChat sends them, and
//! every 5 s asks VRChat's OSCQuery for MuteSelf. Nothing is sent to the chatbox.
//!     cargo run -p vrct-backend --example osc_check [seconds]
//! Check both orders: VRChat first then this, and this first then VRChat.
use std::time::{Duration, Instant};
use vrct_backend::osc::OscReceiver;

fn main() -> anyhow::Result<()> {
    let seconds: u64 = std::env::args().nth(1).and_then(|s| s.parse().ok()).unwrap_or(120);
    let started = Instant::now();
    let receiver = OscReceiver::start("127.0.0.1", move |event| {
        println!("[{:6.1}s] received {event:?}", started.elapsed().as_secs_f64())
    })?.expect("OSCQuery is enabled for 127.0.0.1");
    println!("advertising VRCT; running {seconds} s");
    while started.elapsed() < Duration::from_secs(seconds) {
        std::thread::sleep(Duration::from_secs(5));
        println!("[{:6.1}s] MuteSelf query: {:?}", started.elapsed().as_secs_f64(), receiver.mute_self());
    }
    receiver.stop();
    println!("stopped");
    Ok(())
}
