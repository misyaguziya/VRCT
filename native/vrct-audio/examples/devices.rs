//! Lists the recording devices and records 1 s from the default input and the default loopback,
//! printing only how much came and its level (nothing is kept).
//!     cargo run --example devices --features devices
use std::time::Duration;
use vrct_audio::devices::{self, Capture};

fn main() {
    let d = devices::list().unwrap();
    for i in &d.inputs {
        println!("input    {:?} {} Hz {} ch", i.name, i.sample_rate, i.channels);
    }
    for l in &d.loopbacks {
        println!("loopback {:?} {} Hz {} ch", l.name, l.sample_rate, l.channels);
    }
    println!("default input {:?}, default loopback {:?}", d.default_input, d.default_loopback);
    for name in [d.default_input.clone(), d.default_loopback.clone()].into_iter().flatten() {
        let capture = Capture::open(Some(&name)).unwrap();
        let frames = capture.sample_rate as usize / 10;
        let mut got = 0;
        let mut peak = 0i32;
        for _ in 0..10 {
            if let Some(pcm) = capture.read(frames, Some(Duration::from_millis(500))).unwrap() {
                got += pcm.len() / 2 / capture.channels as usize;
                peak = pcm.chunks_exact(2).map(|b| (i16::from_le_bytes([b[0], b[1]]) as i32).abs()).fold(peak, i32::max);
            }
        }
        println!("{name:?}: {} Hz {} ch, {got} frames in ~1 s, peak {peak}", capture.sample_rate, capture.channels);
    }
}
