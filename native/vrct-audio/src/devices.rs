//! Recording devices on WASAPI (cpal), in place of PyAudioWPatch (device_manager.py, audio_source.py).
//!
//! Names are the Windows friendly names, which are PortAudio's "Windows WASAPI" names; a loopback
//! (what an output device plays) is listed as "<output name> [Loopback]" as PyAudioWPatch did.
//! A capture delivers PCM16 at the device's own rate: a microphone as mono (the channels
//! averaged, as PortAudio did when asked for 1 channel), a loopback with all its channels.
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use cpal::{Device, SampleFormat, StreamConfig};
use std::collections::VecDeque;
use std::sync::mpsc;
use std::sync::{Arc, Condvar, Mutex};
use std::time::{Duration, Instant};

pub const LOOPBACK_SUFFIX: &str = " [Loopback]";
/// What a capture keeps when nobody reads (older samples are dropped)
const MAX_BUFFERED_SECONDS: usize = 10;

#[derive(Clone, Debug, PartialEq)]
pub struct DeviceInfo {
    /// The friendly name ("<name> [Loopback]" for a loopback)
    pub name: String,
    pub sample_rate: u32,
    pub channels: u16,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct Devices {
    pub inputs: Vec<DeviceInfo>,
    pub loopbacks: Vec<DeviceInfo>,
    pub default_input: Option<String>,
    /// The loopback of the default output
    pub default_loopback: Option<String>,
}

fn info(device: &Device, loopback: bool) -> Option<DeviceInfo> {
    let name = device.name().ok()?;
    let config = if loopback { device.default_output_config() } else { device.default_input_config() }.ok()?;
    Some(DeviceInfo {
        name: if loopback { format!("{name}{LOOPBACK_SUFFIX}") } else { name },
        sample_rate: config.sample_rate().0,
        channels: config.channels(),
    })
}

/// The active WASAPI devices now
pub fn list() -> Result<Devices, String> {
    let host = cpal::default_host();
    let inputs = host.input_devices().map_err(|e| e.to_string())?.filter_map(|d| info(&d, false)).collect();
    let loopbacks = host.output_devices().map_err(|e| e.to_string())?.filter_map(|d| info(&d, true)).collect();
    Ok(Devices {
        inputs,
        loopbacks,
        default_input: host.default_input_device().and_then(|d| d.name().ok()),
        default_loopback: host.default_output_device().and_then(|d| d.name().ok()).map(|n| format!("{n}{LOOPBACK_SUFFIX}")),
    })
}

fn find(name: &str) -> Result<(Device, bool), String> {
    let host = cpal::default_host();
    let (wanted, loopback) = match name.strip_suffix(LOOPBACK_SUFFIX) {
        Some(output) => (output, true),
        None => (name, false),
    };
    let mut devices = if loopback { host.output_devices() } else { host.input_devices() }.map_err(|e| e.to_string())?;
    devices.find(|d| d.name().is_ok_and(|n| n == wanted)).map(|d| (d, loopback)).ok_or_else(|| format!("no device {name:?}"))
}

struct Shared {
    samples: VecDeque<i16>,
    error: Option<String>,
    stopped: bool,
}

/// An open recording. `read` blocks until enough samples came; `stop` (from any thread) ends a
/// read in progress, as PortAudio's stop_stream did.
pub struct Capture {
    pub sample_rate: u32,
    pub channels: u16,
    shared: Arc<(Mutex<Shared>, Condvar)>,
    stop: Option<mpsc::Sender<()>>,
    thread: Option<std::thread::JoinHandle<()>>,
}

/// `out` gets the frame as PCM16: averaged to one channel for a microphone. f32 is scaled by
/// 32767 and truncated, as PortAudio's Float32_To_Int16 (without its dither).
fn push_frames<T: Copy>(data: &[T], channels: usize, mono: bool, to_f32: impl Fn(T) -> f32, out: &mut VecDeque<i16>) {
    let convert = |x: f32| (x * 32767.0).clamp(-32768.0, 32767.0) as i16;
    if mono && channels > 1 {
        for frame in data.chunks_exact(channels) {
            out.push_back(convert(frame.iter().map(|&s| to_f32(s)).sum::<f32>() / channels as f32));
        }
    } else {
        out.extend(data.iter().map(|&s| convert(to_f32(s))));
    }
}

impl Capture {
    /// Opens `name` (an input, or "<output> [Loopback]"); None is the default input
    pub fn open(name: Option<&str>) -> Result<Self, String> {
        let (ready_tx, ready_rx) = mpsc::channel();
        let (stop_tx, stop_rx) = mpsc::channel::<()>();
        let shared = Arc::new((Mutex::new(Shared { samples: VecDeque::new(), error: None, stopped: false }), Condvar::new()));
        let name = name.map(String::from);
        let s = shared.clone();
        // the stream lives on its own thread (a cpal stream is not to be moved between threads)
        let thread = std::thread::Builder::new().name("audio-capture".into()).spawn(move || {
            let opened = (|| -> Result<(cpal::Stream, u32, u16), String> {
                let (device, loopback) = match &name {
                    Some(n) => find(n)?,
                    None => (cpal::default_host().default_input_device().ok_or("no default input device")?, false),
                };
                let supported = if loopback { device.default_output_config() } else { device.default_input_config() }
                    .map_err(|e| e.to_string())?;
                let config: StreamConfig = supported.config();
                let device_channels = config.channels as usize;
                let mono = !loopback;
                let channels = if mono { 1 } else { config.channels };
                let limit = MAX_BUFFERED_SECONDS * config.sample_rate.0 as usize * channels as usize;
                let (data_shared, error_shared) = (s.clone(), s.clone());
                let on_error = move |e: cpal::StreamError| {
                    let (lock, wake) = &*error_shared;
                    lock.lock().unwrap().error = Some(e.to_string());
                    wake.notify_all();
                };
                macro_rules! build {
                    ($t:ty, $f:expr) => {
                        device.build_input_stream(&config, move |data: &[$t], _: &cpal::InputCallbackInfo| {
                            let (lock, wake) = &*data_shared;
                            let mut shared = lock.lock().unwrap();
                            push_frames(data, device_channels, mono, $f, &mut shared.samples);
                            let over = shared.samples.len().saturating_sub(limit);
                            shared.samples.drain(..over);
                            wake.notify_all();
                        }, on_error, None)
                    };
                }
                let stream = match supported.sample_format() {
                    SampleFormat::F32 => build!(f32, |x: f32| x),
                    SampleFormat::I16 => build!(i16, |x: i16| x as f32 / 32768.0),
                    SampleFormat::I32 => build!(i32, |x: i32| x as f32 / 2147483648.0),
                    SampleFormat::U8 => build!(u8, |x: u8| (x as f32 - 128.0) / 128.0),
                    other => return Err(format!("unsupported sample format {other}")),
                }.map_err(|e| e.to_string())?;
                stream.play().map_err(|e| e.to_string())?;
                Ok((stream, config.sample_rate.0, channels))
            })();
            match opened {
                Ok((stream, rate, channels)) => {
                    let _ = ready_tx.send(Ok((rate, channels)));
                    let _ = stop_rx.recv();
                    drop(stream);
                }
                Err(e) => {
                    let _ = ready_tx.send(Err(e));
                }
            }
        }).map_err(|e| e.to_string())?;
        let (sample_rate, channels) = ready_rx.recv().map_err(|_| "the capture thread ended".to_string())??;
        Ok(Self { sample_rate, channels, shared, stop: Some(stop_tx), thread: Some(thread) })
    }

    /// `frames` frames (interleaved PCM16 LE). Err when the device failed or the capture was stopped;
    /// None after `timeout` without enough samples.
    pub fn read(&self, frames: usize, timeout: Option<Duration>) -> Result<Option<Vec<u8>>, String> {
        let want = frames * self.channels as usize;
        let deadline = timeout.map(|t| Instant::now() + t);
        let (lock, wake) = &*self.shared;
        let mut shared = lock.lock().unwrap();
        loop {
            if shared.stopped {
                return Err("the capture was stopped".into());
            }
            if let Some(e) = &shared.error {
                return Err(e.clone());
            }
            if shared.samples.len() >= want {
                return Ok(Some(shared.samples.drain(..want).flat_map(i16::to_le_bytes).collect()));
            }
            shared = match deadline {
                None => wake.wait(shared).unwrap(),
                Some(d) => {
                    let now = Instant::now();
                    if now >= d {
                        return Ok(None);
                    }
                    wake.wait_timeout(shared, d - now).unwrap().0
                }
            };
        }
    }

    /// Frames that can be read without waiting (get_read_available)
    pub fn available(&self) -> usize {
        self.shared.0.lock().unwrap().samples.len() / self.channels as usize
    }

    /// Ends reads in progress and later ones (stop_stream)
    pub fn stop(&self) {
        let (lock, wake) = &*self.shared;
        lock.lock().unwrap().stopped = true;
        wake.notify_all();
    }

    pub fn is_stopped(&self) -> bool {
        self.shared.0.lock().unwrap().stopped
    }
}

impl Drop for Capture {
    /// Closes the stream and waits for its thread
    fn drop(&mut self) {
        self.stop();
        drop(self.stop.take());
        if let Some(t) = self.thread.take() {
            let _ = t.join();
        }
    }
}
