//! A check of the OCR frame source (ocr_capture::OcrCapture) with VRChat: every second, which
//! backend gave the frame (SteamVR mirror or the window), its size, whether it counted as blank and
//! how long the read took. No image is kept.
//!     cargo run -p vrct-backend --example ocr_capture_check [seconds]
use std::time::{Duration, Instant};
use vrct_backend::ocr_capture::{is_frame_blank, OcrCapture};

fn main() {
    let seconds: u64 = std::env::args().nth(1).and_then(|s| s.parse().ok()).unwrap_or(30);
    let mut capture = OcrCapture::new("VRChat");
    let started = Instant::now();
    while started.elapsed() < Duration::from_secs(seconds) {
        let t = Instant::now();
        let frame = capture.get(&|line| println!("  log: {line}"));
        let ms = t.elapsed().as_secs_f64() * 1000.0;
        match &frame {
            Some(f) => println!("[{:5.1}s] {:?} {}x{} blank={} {ms:.1} ms", started.elapsed().as_secs_f64(), capture.backend(), f.w, f.h,
                                is_frame_blank(Some(f))),
            None => println!("[{:5.1}s] {:?} no frame {ms:.1} ms", started.elapsed().as_secs_f64(), capture.backend()),
        }
        std::thread::sleep(Duration::from_secs(1));
    }
    capture.close();
}
