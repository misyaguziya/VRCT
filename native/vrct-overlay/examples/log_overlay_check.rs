//! A check of the log overlays in SteamVR (the Python version's defaults): the small log in front of
//! the headset and the large log on the left hand. A message every 10 s; each stays 5 s then fades
//! out in 2 s. Halfway through, the small log moves up a little and becomes half transparent.
//!     cargo run -p vrct-overlay --example log_overlay_check [seconds]
use std::sync::Arc;
use std::time::{Duration, Instant};
use vrct_overlay::image::{OverlayImage, Token};
use vrct_overlay::overlay::{Overlay, Settings};

fn main() {
    let seconds: u64 = std::env::args().nth(1).and_then(|s| s.parse().ok()).unwrap_or(60);
    let fonts = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../src-python/models/overlay/fonts");
    let defaults = |tracker: &str, ui_scaling: f64| Settings {
        position: [0.0; 6], tracker: tracker.into(), opacity: 1.0, ui_scaling, display_duration: 5.0, fadeout_duration: 2.0,
        panel_size: None,
    };
    // model.py makes the large log a quarter of its setting
    let mut overlay = Overlay::new(vec![("small".into(), defaults("HMD", 1.0)), ("large".into(), defaults("LeftHand", 0.25))],
                                   Arc::new(|line| println!("{line}")), Arc::new(|_| {}));
    // no VR UI here
    overlay.set_vr_panel_enabled(false);
    overlay.start();
    let mut images = OverlayImage::new(&fonts);
    let ruby = vec![Token { orig: "慮".into(), hira: "おもんぱか".into(), hepburn: "omonpaka".into() },
                    Token { orig: "る".into(), hira: "る".into(), hepburn: "ru".into() }];
    let started = Instant::now();
    let mut n = 0;
    while started.elapsed() < Duration::from_secs(seconds) {
        n += 1;
        let message = format!("Rust overlay check #{n}");
        let small = images.small_log(&message, "English", &["慮る".into()], &["Japanese".into()], &[], std::slice::from_ref(&ruby)).unwrap();
        overlay.update_image("small", small);
        let kind = if n % 2 == 0 { "receive" } else { "send" };
        let large = images.large_log(kind, Some(&message), "English", &["慮る".into()], &["Japanese".into()], &[], std::slice::from_ref(&ruby)).unwrap();
        overlay.update_image("large", large);
        println!("[{:5.1}s] message #{n}", started.elapsed().as_secs_f64());
        if n == 4 {
            println!("small log: up 0.1 and opacity 0.5");
            overlay.update_position("small", [0.0, 0.1, 0.0, 0.0, 0.0, 0.0], "HMD");
            overlay.update_opacity("small", 0.5, false);
        }
        std::thread::sleep(Duration::from_secs(10));
    }
    overlay.stop();
}
