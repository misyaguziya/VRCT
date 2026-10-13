//! Recording (transcription_recorder.py + audio_listener.py): one capture of a device, its phrases
//! cut by the energy threshold or by Silero VAD into a queue, and its energy for the meter.
//! Opening and closing devices is serialized (pyaudio_op_lock).
use std::collections::VecDeque;
use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use vrct_audio::devices::Capture;
use vrct_audio::vad::{FrameProbability, VadRecognizer, VadSegmenter, FRAME_DURATION_MS};
use vrct_audio::EnergyDetector;
use vrct_ocr::silero::SileroVad;

/// The frames read at a time (AudioCaptureSource's chunk_size)
const CHUNK: usize = 1024;
const OPEN_TIMEOUT: Duration = Duration::from_secs(8);
/// _AUDIO_QUEUE_MAXSIZE: phrases kept for the transcriber (the oldest goes)
const QUEUE_MAX: usize = 20;
const MAX_SPEECH_DURATION_MS: f64 = 7000.0;
pub const STOP_TIMEOUT: Duration = Duration::from_secs(15);
/// A read waits at most this long, so a mute or a stop is seen at once
const READ_POLL: Duration = Duration::from_millis(100);

/// pyaudio_op_lock: device opens and closes one at a time
static DEVICE_OPS: Mutex<()> = Mutex::new(());

/// AudioPipelineFailure (without the exception's type, which the UI never gets)
#[derive(Clone, Debug, PartialEq)]
pub struct Failure {
    pub code: &'static str,
    pub stage: &'static str,
}

/// A phrase for the transcriber; `reason` only from VAD ("silence" / "max_duration" / "flush")
pub struct Phrase {
    pub pcm: Vec<u8>,
    pub at: Instant,
    pub reason: Option<&'static str>,
}

pub enum Segmenting {
    /// listen_energy_and_audio_in_background with the Recognizer's settings
    Energy { threshold: f64, dynamic: bool },
    /// listen_with_segmenter_in_background with Silero VAD (the folder with its two models)
    Vad { silero: std::path::PathBuf },
}

struct Silero(SileroVad);

impl FrameProbability for Silero {
    fn probability(&mut self, frame: &[f32]) -> Result<f32, String> {
        self.0.probability(frame).map_err(|e| e.to_string())
    }

    fn reset(&mut self) {
        self.0.reset()
    }
}

struct Shared {
    phrases: Mutex<VecDeque<Phrase>>,
    keep_phrases: bool,
    /// VRChat's mute: the audio is still read (for the meter) but dropped
    paused: AtomicBool,
    stopped: AtomicBool,
    error: Mutex<Option<Failure>>,
}

impl Shared {
    /// boundary(): false once stopped (a mute does not wait here: the listener keeps reading)
    fn boundary(&self) -> bool {
        !self.stopped.load(Ordering::SeqCst)
    }

    fn paused(&self) -> bool {
        self.paused.load(Ordering::SeqCst)
    }

    /// putDroppingOldestOnFull
    fn deliver(&self, pcm: Vec<u8>, reason: Option<&'static str>, log: &dyn Fn(String)) {
        if !self.keep_phrases {
            return;
        }
        let mut q = self.phrases.lock().unwrap();
        if q.len() >= QUEUE_MAX {
            q.pop_front();
            log("audio_queue is full; dropped the oldest queued chunk to keep up".into());
        }
        q.push_back(Phrase { pcm, at: Instant::now(), reason });
    }

    /// _set_device_error: the first failure while not stopping
    fn fail(&self, failure: Failure, detail: &str) {
        if self.stopped.load(Ordering::SeqCst) {
            return;
        }
        let mut error = self.error.lock().unwrap();
        if error.is_none() {
            crate::logs::error(&format!("recording ({})", failure.code), &detail);
            *error = Some(failure);
        }
    }
}

pub struct Recorder {
    /// what the phrases are: the device's rate and channels (energy), 16 kHz mono (VAD)
    pub sample_rate: u32,
    pub channels: u16,
    shared: Arc<Shared>,
    /// taken when the recorder goes (closed under the device lock)
    capture: Option<Arc<Capture>>,
    thread: Mutex<Option<std::thread::JoinHandle<()>>>,
}

/// _create_microphone: the device (or, failing that, the default input), given up after 8 s
fn open_capture(name: &str, log: &dyn Fn(String)) -> Result<Capture, String> {
    let (tx, rx) = mpsc::channel();
    let device = name.to_string();
    std::thread::Builder::new().name("mic-open".into()).spawn(move || {
        let _ops = DEVICE_OPS.lock().unwrap_or_else(|e| e.into_inner());
        let opened = Capture::open(Some(&device))
            .or_else(|_| Capture::open(None))
            .map_err(|e| format!("Selected and default audio devices could not be opened: {e}"));
        // after the timeout nobody receives: the capture is dropped here, under the lock
        let _ = tx.send(opened);
    }).map_err(|e| e.to_string())?;
    match rx.recv_timeout(OPEN_TIMEOUT) {
        Ok(opened) => opened,
        Err(_) => {
            log(format!("Timed out after {}s opening audio device (device_name={name:?})", OPEN_TIMEOUT.as_secs()));
            Err("Timed out opening audio device".into())
        }
    }
}

impl Recorder {
    /// Opens `device` and starts listening. `on_energy`: the energy of every chunk (the meter);
    /// `keep_phrases`: phrases are queued (transcription), else dropped.
    pub fn start(device: &str, segmenting: Segmenting, record_timeout: f64, label: &str, keep_phrases: bool,
                 on_energy: Option<Box<dyn Fn(u32) + Send>>, log: Arc<dyn Fn(String) + Send + Sync>) -> Result<Recorder, String> {
        let capture = Arc::new(open_capture(device, &*log)?);
        // phrase_time_limit is the timeout as given; the listen timeout has no end at 0 or below
        let phrase_time_limit = record_timeout;
        let record_timeout = if record_timeout <= 0.0 { f64::INFINITY } else { record_timeout };
        let shared = Arc::new(Shared {
            phrases: Mutex::new(VecDeque::new()),
            keep_phrases,
            paused: AtomicBool::new(false),
            stopped: AtomicBool::new(false),
            error: Mutex::new(None),
        });
        let (rate, channels) = (capture.sample_rate, capture.channels);
        let label = label.to_string();
        let (s, c) = (shared.clone(), capture.clone());
        let (sample_rate, phrase_channels, run): (u32, u16, Box<dyn FnOnce() + Send>) = match segmenting {
            Segmenting::Energy { threshold, dynamic } => {
                let detector = EnergyDetector::new(rate, CHUNK, threshold, dynamic, phrase_time_limit, record_timeout, 1.0,
                                                   0.8, 0.3, 0.5, 0.15, 1.5).map_err(String::from)?;
                (rate, channels, Box::new(move || listen_energy(&s, &c, detector, on_energy, &*log)))
            }
            Segmenting::Vad { silero } => {
                let vad = SileroVad::new(&silero).map_err(|e| e.to_string())?;
                let max_frames = ((MAX_SPEECH_DURATION_MS / FRAME_DURATION_MS).round() as usize).max(1);
                let segment_log = log.clone();
                let segmenter = VadSegmenter::new(Silero(vad), Some(max_frames))
                    .with_log(&label, Box::new(move |line| segment_log(line)));
                let recognizer = VadRecognizer::new(rate, 2, channels as usize, segmenter);
                (16000, 1, Box::new(move || listen_vad(&s, &c, recognizer, record_timeout, on_energy, &*log)))
            }
        };
        let thread = std::thread::Builder::new().name(format!("{label}-listener")).spawn(run).map_err(|e| e.to_string())?;
        Ok(Recorder { sample_rate, channels: phrase_channels, shared, capture: Some(capture), thread: Mutex::new(Some(thread)) })
    }

    pub fn take_phrase(&self) -> Option<Phrase> {
        self.shared.phrases.lock().unwrap().pop_front()
    }

    pub fn has_phrase(&self) -> bool {
        !self.shared.phrases.lock().unwrap().is_empty()
    }

    pub fn clear_phrases(&self) {
        self.shared.phrases.lock().unwrap().clear();
    }

    /// device_error_event / device_error_info, taken once
    pub fn take_error(&self) -> Option<Failure> {
        self.shared.error.lock().unwrap().take()
    }

    /// VRChat's mute, from now: the phrase being cut and what is read go (the meter still moves)
    pub fn pause(&self) {
        self.shared.paused.store(true, Ordering::SeqCst);
        self.clear_phrases();
    }

    /// Phrases again, from now
    pub fn resume(&self) {
        self.shared.paused.store(false, Ordering::SeqCst);
        self.clear_phrases();
    }

    pub fn is_paused(&self) -> bool {
        self.shared.paused()
    }

    /// The stopper: a read in progress ends and the listener is joined (false when it did not
    /// end within STOP_TIMEOUT). The device closes when the recorder goes.
    pub fn stop(&self) -> bool {
        self.shared.stopped.store(true, Ordering::SeqCst);
        if let Some(c) = &self.capture {
            c.stop();
        }
        let Some(thread) = self.thread.lock().unwrap().take() else { return true };
        let (tx, rx) = mpsc::channel();
        std::thread::spawn(move || {
            let _ = thread.join();
            let _ = tx.send(());
        });
        rx.recv_timeout(STOP_TIMEOUT).is_ok()
    }
}

impl Drop for Recorder {
    /// The device closes under the device lock
    fn drop(&mut self) {
        self.shared.stopped.store(true, Ordering::SeqCst);
        let Some(capture) = self.capture.take() else { return };
        capture.stop();
        let _ops = DEVICE_OPS.lock().unwrap_or_else(|e| e.into_inner());
        drop(capture);
    }
}

fn read_error(shared: &Shared, e: &str) {
    shared.fail(Failure { code: "AUDIO_READ_ERROR", stage: "recording" }, e);
}

/// While muted: a chunk read only for its energy, then dropped. False when the device failed.
fn read_for_meter(shared: &Shared, capture: &Capture, on_energy: &Option<Box<dyn Fn(u32) + Send>>) -> bool {
    match capture.read(CHUNK, Some(READ_POLL)) {
        Ok(Some(raw)) => {
            if let Some(f) = on_energy {
                f(vrct_audio::rms(&raw).unwrap_or(0));
            }
            true
        }
        Ok(None) => true,
        Err(e) => {
            read_error(shared, &e);
            false
        }
    }
}

fn listen_energy(shared: &Shared, capture: &Capture, mut detector: EnergyDetector, on_energy: Option<Box<dyn Fn(u32) + Send>>,
                 log: &dyn Fn(String)) {
    let started = Instant::now();
    let now = || started.elapsed().as_secs_f64();
    while !shared.stopped.load(Ordering::SeqCst) {
        if shared.paused() {
            // muted: the phrase being cut goes; what is read only moves the meter
            detector.cancel();
            if !read_for_meter(shared, capture, &on_energy) {
                break;
            }
            continue;
        }
        let (action, audio) = match detector.before_read(now()) {
            Ok(step) => step,
            Err(e) => {
                read_error(shared, e);
                break;
            }
        };
        if action != "READ" {
            if let Some(audio) = audio.filter(|_| !shared.stopped.load(Ordering::SeqCst)) {
                shared.deliver(audio, None, log);
            }
            if action == "EOF" || !shared.boundary() {
                break;
            }
            continue;
        }
        // nothing to read (a silent loopback): wait here, not in a read that would not return
        if detector.waiting() && capture.available() == 0 {
            detector.cancel();
            std::thread::sleep(Duration::from_millis(10));
            if shared.stopped.load(Ordering::SeqCst) || !shared.boundary() {
                break;
            }
            continue;
        }
        let raw = match capture.read(CHUNK, Some(READ_POLL)) {
            Ok(Some(raw)) => raw,
            Ok(None) => continue,
            Err(e) => {
                read_error(shared, &e);
                break;
            }
        };
        if shared.stopped.load(Ordering::SeqCst) {
            break;
        }
        if shared.paused() {
            continue;
        }
        match detector.push(&raw, now()) {
            Ok(energy) => {
                if let Some(f) = &on_energy {
                    f(energy);
                }
            }
            Err(e) => {
                read_error(shared, e);
                break;
            }
        }
    }
    // an unfinished phrase is not sent when stopping
    detector.cancel();
}

fn listen_vad(shared: &Shared, capture: &Capture, mut vad: VadRecognizer<Silero>, record_timeout: f64,
              on_energy: Option<Box<dyn Fn(u32) + Send>>, log: &dyn Fn(String)) {
    let vad_error = |e: &str| shared.fail(Failure { code: "VAD_INFERENCE_ERROR", stage: "vad" }, e);
    let mut started = Instant::now();
    while !shared.stopped.load(Ordering::SeqCst) {
        if shared.paused() {
            // muted: the speech being cut goes; what is read only moves the meter
            vad.reset();
            if !read_for_meter(shared, capture, &on_energy) {
                break;
            }
            started = Instant::now();
            continue;
        }
        if started.elapsed().as_secs_f64() > record_timeout {
            if !shared.boundary() {
                break;
            }
            started = Instant::now();
        }
        let raw = match capture.read(CHUNK, Some(READ_POLL)) {
            Ok(Some(raw)) => raw,
            Ok(None) => continue,
            Err(e) => {
                read_error(shared, &e);
                break;
            }
        };
        if shared.stopped.load(Ordering::SeqCst) {
            break;
        }
        if shared.paused() {
            continue;
        }
        if let Some(f) = &on_energy {
            f(vrct_audio::rms(&raw).unwrap_or(0));
        }
        if raw.is_empty() {
            break;
        }
        let segments = match vad.process(&raw) {
            Ok(s) => s,
            Err(e) => {
                vad_error(&e);
                break;
            }
        };
        let any = !segments.is_empty();
        for segment in segments {
            shared.deliver(segment.audio, Some(segment.reason.as_str()), log);
        }
        if any {
            if !shared.boundary() {
                break;
            }
            started = Instant::now();
        }
    }
    if shared.paused() {
        return;
    }
    match vad.flush() {
        Ok(Some(segment)) => shared.deliver(segment.audio, Some(segment.reason.as_str()), log),
        Ok(None) => {}
        Err(e) => vad_error(&e),
    }
}

/// The Silero models beside the executable
pub fn silero_dir(resources: &Path) -> std::path::PathBuf {
    resources.join("silero")
}
