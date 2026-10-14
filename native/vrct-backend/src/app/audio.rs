//! The microphone and the speaker (model.py's MicSession / SpeakerSession / AudioLifecycleWorker,
//! device_manager.py and controller.py's audio handlers): one recorder per device for the
//! transcription and the volume meter, the device lists and their changes, the automatic
//! selection, and VRChat's mute.
use super::features::whisper_weight_ok;
use super::pipeline;
use super::{current, App};
use crate::devices::{self, Snapshot, NO_DEVICE, NO_HOST};
use crate::errors;
use crate::ipc::{self, Reply};
use crate::logs;
use crate::osc::OscEvent;
use crate::pyjson::py_str;
use crate::recorder::{Failure, Recorder, Segmenting, STOP_TIMEOUT};
use crate::transcriber::{Engine, Transcriber, Transcript};
use anyhow::{anyhow, Result};
use serde_json::{json, Value};
use std::collections::{HashSet, VecDeque};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::mpsc;
use std::sync::{Arc, Condvar, Mutex, MutexGuard, Weak};
use std::time::{Duration, Instant};
use vrct_audio::endpoints::{ActiveEndpointTracker, DeviceWatcher, Flow};

type Data = Option<Value>;

const MONITOR_WAIT: Duration = Duration::from_secs(2);
/// _SHUTDOWN_LIFECYCLE_LOCK_TIMEOUT_SEC
const SHUTDOWN_WAIT: Duration = Duration::from_secs(20);

// ------------------------------------------------------------------------------------ worker

type Job = Box<dyn FnOnce() + Send>;

#[derive(Default)]
struct WorkerState {
    queue: VecDeque<(Option<&'static str>, Job)>,
    pending: HashSet<&'static str>,
    stopped: bool,
}

/// AudioLifecycleWorker: device changes run one at a time on their own thread, so the device
/// monitor never waits. A coalesce key drops a job while the same one waits to start.
pub struct Worker {
    state: Arc<(Mutex<WorkerState>, Condvar)>,
    thread: Mutex<Option<std::thread::JoinHandle<()>>>,
}

impl Worker {
    fn new(name: &str) -> Self {
        let state: Arc<(Mutex<WorkerState>, Condvar)> = Arc::default();
        let s = state.clone();
        let thread = std::thread::Builder::new().name(name.into()).spawn(move || loop {
            let job = {
                let mut st = s.0.lock().unwrap();
                loop {
                    if let Some((key, job)) = st.queue.pop_front() {
                        if let Some(key) = key {
                            st.pending.remove(key);
                        }
                        break job;
                    }
                    if st.stopped {
                        return;
                    }
                    st = s.1.wait(st).unwrap();
                }
            };
            job();
        }).ok();
        Self { state, thread: Mutex::new(thread) }
    }

    /// False when stopped or the same key is waiting
    pub fn enqueue(&self, key: Option<&'static str>, job: impl FnOnce() + Send + 'static) -> bool {
        let mut st = self.state.0.lock().unwrap();
        if st.stopped || key.is_some_and(|k| !st.pending.insert(k)) {
            return false;
        }
        st.queue.push_back((key, Box::new(job)));
        self.state.1.notify_one();
        true
    }

    /// No jobs from now on; the ones queued still run. Waits up to `timeout`.
    fn stop(&self, timeout: Duration) {
        {
            let mut st = self.state.0.lock().unwrap();
            if st.stopped {
                return;
            }
            st.stopped = true;
            self.state.1.notify_all();
        }
        if let Some(thread) = self.thread.lock().unwrap().take() {
            let (tx, rx) = mpsc::channel();
            std::thread::spawn(move || {
                let _ = thread.join();
                let _ = tx.send(());
            });
            let _ = rx.recv_timeout(timeout);
        }
    }
}

/// A job on the worker that needs the app
fn enqueue(app: &App, worker: &Worker, key: Option<&'static str>, job: fn(&App)) {
    let me = app.me();
    worker.enqueue(key, move || {
        if let Some(app) = me.upgrade() {
            job(&app);
        }
    });
}

// ----------------------------------------------------------------------------------- session

#[derive(Clone, Copy, PartialEq, Debug)]
pub enum Kind {
    Mic,
    Speaker,
}

impl Kind {
    fn label(self) -> &'static str {
        match self {
            Kind::Mic => "mic",
            Kind::Speaker => "speaker",
        }
    }

    fn x(self) -> &'static str {
        match self {
            Kind::Mic => "MIC",
            Kind::Speaker => "SPEAKER",
        }
    }

    fn session(self, app: &App) -> &Mutex<Session> {
        match self {
            Kind::Mic => &app.audio.mic,
            Kind::Speaker => &app.audio.speaker,
        }
    }
}

/// The pipeline's failure told once per start (_pipeline_error_started / _notified)
#[derive(Default)]
struct ErrorGate {
    started: AtomicBool,
    notified: AtomicBool,
}

struct Running {
    stop: Arc<AtomicBool>,
    thread: std::thread::JoinHandle<()>,
}

/// _AudioDeviceSession: the recorder of one device, for the features on (transcript, energy).
/// Its mutex is the lifecycle lock (mic_lifecycle_lock / speaker_lifecycle_lock).
pub struct Session {
    kind: Kind,
    transcript: bool,
    energy: bool,
    recorder: Option<Arc<Recorder>>,
    transcribing: Option<Running>,
    active_device: Option<String>,
    generation: u64,
    gate: Arc<ErrorGate>,
}

static GENERATIONS: AtomicU64 = AtomicU64::new(0);

/// What the session tells the controller (transcript_fnc)
enum Event {
    /// {"text": False}: no device
    NoDevice,
    Text(Transcript, bool),
    Failure(Failure),
}

impl Session {
    fn new(kind: Kind) -> Self {
        Self { kind, transcript: false, energy: false, recorder: None, transcribing: None, active_device: None, generation: 0,
               gate: Arc::default() }
    }

    fn running(&self) -> bool {
        self.recorder.is_some()
    }

    /// _resolve_device: the device to record, None when there is none
    fn resolve_device(&self, app: &App, device: Option<String>) -> Option<String> {
        if let Some(device) = device {
            return (device != NO_DEVICE).then_some(device);
        }
        let snapshot = devices::snapshot();
        let (name, listed) = match self.kind {
            Kind::Mic => {
                let host = app.config.get_str("SELECTED_MIC_HOST");
                (app.config.get_str("SELECTED_MIC_DEVICE"), snapshot.mic_devices(&host).cloned().unwrap_or_default())
            }
            Kind::Speaker => (app.config.get_str("SELECTED_SPEAKER_DEVICE"), snapshot.speaker.clone()),
        };
        (name != NO_DEVICE && listed.contains(&name)).then_some(name)
    }

    /// reconfigure: Some(true) on, Some(false) off, None as is. Nothing happens when the
    /// features and the device are the same and it runs.
    fn reconfigure(&mut self, app: &App, transcript: Option<bool>, energy: Option<bool>, device: Option<String>) -> Result<()> {
        let (t, e) = (transcript.unwrap_or(self.transcript), energy.unwrap_or(self.energy));
        let resolved = self.resolve_device(app, device);
        let unchanged = t == self.transcript && e == self.energy && resolved == self.active_device;
        if unchanged && (!(t || e) || self.running()) {
            return Ok(());
        }
        self.stop();
        self.transcript = t;
        self.energy = e;
        if t || e {
            self.start(app, resolved)?;
        }
        Ok(())
    }

    fn pause(&self) {
        if let Some(r) = &self.recorder {
            r.pause();
        }
    }

    fn resume(&self) {
        if let Some(r) = &self.recorder {
            r.resume();
        }
    }

    fn start(&mut self, app: &App, device: Option<String>) -> Result<()> {
        let kind = self.kind;
        let Some(device) = device else {
            if self.transcript {
                transcript_event(app, kind, Event::NoDevice);
            }
            if self.energy {
                energy_event(app, kind, None);
            }
            self.transcript = false;
            self.energy = false;
            self.active_device = None;
            return Ok(());
        };
        self.active_device = Some(device.clone());
        self.generation = GENERATIONS.fetch_add(1, Ordering::SeqCst) + 1;
        self.gate = Arc::default();
        let gate = self.gate.clone();
        // told through transcript_fnc, which only a transcription has
        let tell = self.transcript;
        let fail = |session: &mut Session, failure: Failure, error: anyhow::Error| -> anyhow::Error {
            logs::error(&format!("{} start ({})", kind.label(), failure.code), &format!("{error:#}"));
            let failure = if session.stop() { Failure { code: "CLEANUP_TIMEOUT", stage: "cleanup" } } else { failure };
            if tell {
                notify(app, kind, &gate, failure);
            }
            error
        };
        let opened = create_recorder(app, kind, &device, self.transcript, self.energy).or_else(|e| {
            // the selected device does not open: the default one is selected (and told) instead
            let Some(default) = default_device(kind, &device) else { return Err(e) };
            logs::error(&format!("open {} {device:?}", kind.label()), &format!("{e:#}"));
            ipc::log(format!("{} device {device:?} could not be opened; the default {:?} is selected", capitalized(kind), default.1));
            select_device(app, kind, &default)?;
            self.active_device = Some(default.1.clone());
            create_recorder(app, kind, &default.1, self.transcript, self.energy)
        });
        let recorder = match opened {
            Ok(r) => Arc::new(r),
            Err(e) => return Err(fail(self, Failure { code: "AUDIO_OPEN_ERROR", stage: "recording" }, e)),
        };
        self.recorder = Some(recorder.clone());
        if !self.transcript {
            return Ok(());
        }
        let transcriber = match create_transcriber(app, kind, &recorder) {
            Ok(t) => t,
            Err(e) => return Err(fail(self, Failure { code: "TRANSCRIBER_INIT_ERROR", stage: "asr" }, e)),
        };
        let stop = Arc::new(AtomicBool::new(false));
        let (me, generation, flag) = (app.me(), self.generation, stop.clone());
        let thread = std::thread::Builder::new().name(format!("{}-transcription", kind.label()))
            .spawn(move || send_transcripts(me, kind, generation, gate, recorder, transcriber, flag))?;
        self.transcribing = Some(Running { stop, thread });
        Ok(())
    }

    /// _stop: everything stopped and released; true when something did not stop in time
    fn stop(&mut self) -> bool {
        let mut timed_out = false;
        if let Some(Running { stop, thread }) = self.transcribing.take() {
            stop.store(true, Ordering::SeqCst);
            if thread.thread().id() != std::thread::current().id() && !join(thread, STOP_TIMEOUT) {
                timed_out = true;
                ipc::log(format!("{} transcription thread did not terminate within timeout", capitalized(self.kind)));
            }
        }
        if let Some(recorder) = self.recorder.take() {
            if !recorder.stop() {
                timed_out = true;
                ipc::log(format!("{} recorder did not stop within timeout", capitalized(self.kind)));
            }
            recorder.clear_phrases();
        }
        self.active_device = None;
        self.transcript = false;
        self.energy = false;
        timed_out
    }
}

/// The default device to move to when `device` does not open: (host, device), or None when there
/// is no other device
fn default_device(kind: Kind, device: &str) -> Option<(String, String)> {
    let s = devices::snapshot();
    let default = match kind {
        Kind::Mic => s.default_mic,
        Kind::Speaker => (String::new(), s.default_speaker),
    };
    (default.1 != NO_DEVICE && default.1 != device).then_some(default)
}

/// The selection moved to `device` and told to the UI (as when a selected device goes away)
fn select_device(app: &App, kind: Kind, (host, device): &(String, String)) -> Result<()> {
    match kind {
        Kind::Mic => update_selected_mic_device(app, host, device),
        Kind::Speaker => update_selected_speaker_device(app, device),
    }
}

fn capitalized(kind: Kind) -> &'static str {
    match kind {
        Kind::Mic => "Mic",
        Kind::Speaker => "Speaker",
    }
}

fn join(thread: std::thread::JoinHandle<()>, timeout: Duration) -> bool {
    let (tx, rx) = mpsc::channel();
    std::thread::spawn(move || {
        let _ = thread.join();
        let _ = tx.send(());
    });
    rx.recv_timeout(timeout).is_ok()
}

fn int(app: &App, name: &str) -> i64 {
    app.config.get(name).as_i64().unwrap_or_default()
}

fn float(app: &App, name: &str) -> f64 {
    app.config.get(name).as_f64().unwrap_or_default()
}

/// _create_recorder: the energy threshold, or VAD when it is on; the record timeout at most the
/// phrase timeout
fn create_recorder(app: &App, kind: Kind, device: &str, transcript: bool, energy: bool) -> Result<Recorder> {
    let x = kind.x();
    let record_timeout = float(app, &format!("{x}_RECORD_TIMEOUT")).min(float(app, &format!("{x}_PHRASE_TIMEOUT")));
    let segmenting = if app.config.get_bool(&format!("{x}_ENABLE_VAD")) {
        Segmenting::Vad { silero: crate::recorder::silero_dir(&app.model.resources.dir) }
    } else {
        Segmenting::Energy { threshold: float(app, &format!("{x}_THRESHOLD")),
                             dynamic: app.config.get_bool(&format!("{x}_AUTOMATIC_THRESHOLD")) }
    };
    let on_energy: Option<Box<dyn Fn(u32) + Send>> = energy.then(|| {
        let me = app.me();
        Box::new(move |e: u32| {
            if let Some(app) = me.upgrade() {
                energy_event(&app, kind, Some(e));
            }
        }) as Box<dyn Fn(u32) + Send>
    });
    Recorder::start(device, segmenting, record_timeout, kind.label(), transcript, on_energy, Arc::new(ipc::log))
        .map_err(|e| anyhow!(e))
}

/// The transcription engine's key, model or URL (_resolve_api_transcription_kwargs)
fn auth(app: &App, engine: &str) -> String {
    app.config.get("TRANSCRIPTION_AUTH_KEYS").get(engine).and_then(Value::as_str).unwrap_or_default().to_string()
}

/// _create_transcriber: Whisper only when its weight loads (else Google)
fn create_transcriber(app: &App, kind: Kind, recorder: &Recorder) -> Result<Transcriber> {
    let x = kind.x();
    let s = |name: &str| app.config.get(name).as_str().unwrap_or_default().to_string();
    let http = app.model.http.clone();
    let engine = match app.config.get_str("SELECTED_TRANSCRIPTION_ENGINE").as_str() {
        "Whisper" if whisper_weight_ok(app, &app.config.get_str("WHISPER_WEIGHT_TYPE")) => {
            let device = app.config.get("SELECTED_TRANSCRIPTION_COMPUTE_DEVICE");
            let (name, index) = (device["device"].as_str().unwrap_or("cpu").to_string(), device["device_index"].as_i64().unwrap_or(0));
            let mut compute_type = app.config.get_str("SELECTED_TRANSCRIPTION_COMPUTE_TYPE");
            if compute_type == "auto" {
                compute_type = crate::compute::best_compute_type(&name, index as usize);
            }
            let path = app.config.env().path_local.join("weights").join("whisper").join(app.config.get_str("WHISPER_WEIGHT_TYPE"));
            Engine::Whisper(crate::transcriber::load_whisper(&path, &name, index as i32, &compute_type)?)
        }
        engine @ ("Groq_Whisper" | "OpenAI_Whisper" | "Custom_Whisper") => {
            let (base_url, model) = match engine {
                "Groq_Whisper" => ("https://api.groq.com/openai/v1".into(), s("SELECTED_GROQ_WHISPER_MODEL")),
                "OpenAI_Whisper" => ("https://api.openai.com/v1".into(), s("SELECTED_OPENAI_WHISPER_MODEL")),
                _ => (s("TRANSCRIPTION_CUSTOM_URL"), s("SELECTED_CUSTOM_WHISPER_MODEL")),
            };
            Engine::Api(crate::asr::WhisperApi { http: http.clone(), api_key: auth(app, engine), base_url, model, engine_name: engine.into() })
        }
        "Deepgram" => {
            let model = s("SELECTED_DEEPGRAM_MODEL");
            let languages = app.config.get("DEEPGRAM_MODEL_LANGUAGES").get(&model).and_then(Value::as_array)
                .map(|l| l.iter().filter_map(|v| v.as_str().map(String::from)).collect()).unwrap_or_default();
            Engine::Deepgram(crate::asr::Deepgram { http: http.clone(), api_key: auth(app, "Deepgram"), model, model_languages: languages })
        }
        _ => Engine::Google,
    };
    Ok(Transcriber::new(kind.label(), kind == Kind::Speaker, recorder, float(app, &format!("{x}_PHRASE_TIMEOUT")),
                        int(app, &format!("{x}_MAX_PHRASES")).max(0) as usize, app.config.get_bool(&format!("{x}_ENABLE_VAD")),
                        engine, http))
}

/// The candidate languages: yours for the microphone, the targets for the speaker (enabled ones)
fn candidates(app: &App, kind: Kind) -> Vec<(String, String)> {
    let setting = if kind == Kind::Mic { "SELECTED_YOUR_LANGUAGES" } else { "SELECTED_TARGET_LANGUAGES" };
    let tab = py_str(&app.config.get("SELECTED_TAB_NO"));
    app.config.get(setting).get(&tab).and_then(Value::as_object).into_iter().flatten()
        .filter(|(_, v)| v["enable"] == json!(true))
        .map(|(_, v)| (v["language"].as_str().unwrap_or_default().into(), v["country"].as_str().unwrap_or_default().into()))
        .collect()
}

/// sendTranscript, until stopped: the recorder's failure or the engine's stops the session
fn send_transcripts(me: Weak<App>, kind: Kind, generation: u64, gate: Arc<ErrorGate>, recorder: Arc<Recorder>,
                    mut transcriber: Transcriber, stop: Arc<AtomicBool>) {
    while !stop.load(Ordering::SeqCst) {
        let Some(app) = me.upgrade() else { return };
        if let Some(failure) = recorder.take_error() {
            pipeline_error(&app, kind, generation, gate, failure);
            break;
        }
        // muted: what was gathered before goes and nothing is transcribed until resumed
        if recorder.is_paused() {
            transcriber.clear();
            recorder.clear_phrases();
            std::thread::sleep(Duration::from_millis(10));
            continue;
        }
        let x = kind.x();
        let result = transcriber.transcribe_queue(&recorder, &app.model.transcription_lang, &candidates(&app, kind),
                                                  float(&app, &format!("{x}_AVG_LOGPROB")), float(&app, &format!("{x}_NO_SPEECH_PROB")),
                                                  int(&app, &format!("{x}_NO_REPEAT_NGRAM_SIZE")).max(0) as usize,
                                                  &|l| ipc::log(l));
        if let Err(failure) = result {
            pipeline_error(&app, kind, generation, gate, failure);
            break;
        }
        // a transcription that finished after the mute is not told
        if recorder.is_paused() {
            transcriber.clear();
            continue;
        }
        while let Some(t) = transcriber.take_transcript() {
            transcript_event(&app, kind, Event::Text(t, transcriber.last_recognition_error));
        }
    }
    recorder.clear_phrases();
}

/// _handle_pipeline_error: once per start; the session is stopped on another thread, then told
fn pipeline_error(app: &App, kind: Kind, generation: u64, gate: Arc<ErrorGate>, failure: Failure) {
    if gate.started.swap(true, Ordering::SeqCst) {
        return;
    }
    let me = app.me();
    let _ = std::thread::Builder::new().name(format!("{}-transcription-error-cleanup", kind.label())).spawn(move || {
        let Some(app) = me.upgrade() else { return };
        let timed_out = {
            let mut session = kind.session(&app).lock().unwrap();
            // a session started again since is not this one
            session.generation == generation && session.stop()
        };
        let failure = if timed_out { Failure { code: "CLEANUP_TIMEOUT", stage: "cleanup" } } else { failure };
        notify(&app, kind, &gate, failure);
    });
}

fn notify(app: &App, kind: Kind, gate: &ErrorGate, failure: Failure) {
    if !gate.notified.swap(true, Ordering::SeqCst) {
        transcript_event(app, kind, Event::Failure(failure));
    }
}

// ------------------------------------------------------------------------- controller side

/// micMessage / speakerMessage
fn transcript_event(app: &App, kind: Kind, event: Event) {
    if let Err(e) = handle_transcript(app, kind, event) {
        logs::error(&format!("{} message", kind.label()), &format!("{e:#}"));
    }
}

fn handle_transcript(app: &App, kind: Kind, event: Event) -> Result<()> {
    let recognition_error = match &event {
        Event::Failure(_) => true,
        Event::Text(_, error) => *error,
        Event::NoDevice => false,
    };
    // muted in VRChat: what the microphone heard is dropped
    if kind == Kind::Mic && !recognition_error && app.config.get_bool("VRC_MIC_MUTE_SYNC")
        && *app.model.mic_mute_status.lock().unwrap() == Some(true) {
        return Ok(());
    }
    if recognition_error {
        let payload = match &event {
            Event::Failure(f) => {
                disable_after_pipeline_error(app, kind)?;
                json!({"error_code": f.code, "stage": f.stage, "source": kind.label(),
                       "message": errors::message(f.code), "recoverable": false})
            }
            _ => json!({"message": format!("{} speech recognition request failed. Check your network connection.", capitalized(kind)),
                        "data": null}),
        };
        return app.run(200, "transcription_recognition_error", payload);
    }
    match event {
        Event::NoDevice => {
            let message = if kind == Kind::Mic { "No mic device detected" } else { "No speaker device detected" };
            app.run(400, "error_device", json!({"message": message, "data": null}))
        }
        Event::Text(t, _) if !t.text.is_empty() => {
            let spec = if kind == Kind::Mic { &pipeline::MIC } else { &pipeline::SPEAKER };
            pipeline::process(app, spec, &t.text, t.language.as_deref(), None, Some(t.asr_ms as i64)).map(|_| ())
        }
        _ => Ok(()),
    }
}

/// _disableTranscriptionAfterPipelineError: the stopped transcription is off in the settings and the UI
fn disable_after_pipeline_error(app: &App, kind: Kind) -> Result<()> {
    let (name, endpoint, default) = match kind {
        Kind::Mic => ("ENABLE_TRANSCRIPTION_SEND", "disable_transcription_send", "/set/disable/transcription_send"),
        Kind::Speaker => ("ENABLE_TRANSCRIPTION_RECEIVE", "disable_transcription_receive", "/set/disable/transcription_receive"),
    };
    app.config.set(name, json!(false))?;
    app.run_or(200, endpoint, default, json!(false));
    Ok(())
}

/// progressBarMicEnergy / progressBarSpeakerEnergy (None: no device)
fn energy_event(app: &App, kind: Kind, energy: Option<u32>) {
    let result = match (energy, kind) {
        (None, Kind::Mic) => app.run_error("error_device", "DEVICE_NO_MIC", Value::Null),
        (None, Kind::Speaker) => app.run_error("error_device", "DEVICE_NO_SPEAKER", Value::Null),
        (Some(e), Kind::Mic) => app.run(200, "check_mic_volume", json!(e)),
        (Some(e), Kind::Speaker) => app.run(200, "check_speaker_volume", json!(e)),
    };
    if let Err(e) = result {
        logs::error("energy", &format!("{e:#}"));
    }
}

/// A CUDA allocation that failed (detectVRAMError)
fn vram_error(error: &anyhow::Error) -> Option<String> {
    let text = format!("{error:#}");
    (text.contains("CUDA out of memory") || text.contains("CUBLAS_STATUS_ALLOC_FAILED")).then_some(text)
}

/// startTranscriptionSendMessage / ReceiveMessage: whether it started
fn start_transcription(app: &App, kind: Kind) -> Result<bool> {
    let (name, vram_code, vram_endpoint, endpoint, default) = match kind {
        Kind::Mic => ("ENABLE_TRANSCRIPTION_SEND", "TRANSCRIPTION_VRAM_MIC", "error_transcription_mic_vram_overflow",
                      "disable_transcription_send", "/set/disable/transcription_send"),
        Kind::Speaker => ("ENABLE_TRANSCRIPTION_RECEIVE", "TRANSCRIPTION_VRAM_SPEAKER", "error_transcription_speaker_vram_overflow",
                          "disable_transcription_receive", "/set/disable/transcription_receive"),
    };
    let mut session = kind.session(app).lock().unwrap();
    let started = session.reconfigure(app, Some(true), None, None).map(|()| {
        let on = session.transcript;
        if on && kind == Kind::Mic {
            apply_mute(app, &session);
        }
        on
    });
    match started {
        Ok(true) => Ok(true),
        Ok(false) => {
            app.config.set(name, json!(false))?;
            Ok(false)
        }
        Err(e) => {
            match vram_error(&e) {
                Some(message) => {
                    app.run_error(vram_endpoint, vram_code, json!(message))?;
                    let _ = session.reconfigure(app, Some(false), None, None);
                    if app.config.get_bool(name) {
                        app.run_or(200, endpoint, default, json!(false));
                    }
                }
                None => logs::error(&format!("start {} transcription", kind.label()), &format!("{e:#}")),
            }
            app.config.set(name, json!(false))?;
            Ok(false)
        }
    }
}

fn stop_transcription(app: &App, kind: Kind) -> Result<()> {
    kind.session(app).lock().unwrap().reconfigure(app, Some(false), None, None)
}

fn set_energy(app: &App, kind: Kind, on: bool) -> Result<()> {
    kind.session(app).lock().unwrap().reconfigure(app, None, Some(on), None)
}

/// reconfigureMicDevice / reconfigureSpeakerDevice: the session moves to the selected device
/// (the speaker's endpoint tracker waits meanwhile)
fn reopen(app: &App, kind: Kind) -> Result<()> {
    let tracker = (kind == Kind::Speaker).then(|| app.audio.monitor.tracker.lock().unwrap());
    if let Some(Some(t)) = tracker.as_deref() {
        t.pause();
    }
    let result = kind.session(app).lock().unwrap().reconfigure(app, None, None, None);
    if let Some(Some(t)) = tracker.as_deref() {
        t.resume();
    }
    result
}

/// changeMicTranscriptStatus: paused while VRChat mutes (with mute sync on); the caller holds the lock
fn apply_mute(app: &App, session: &Session) {
    if app.config.get_bool("VRC_MIC_MUTE_SYNC") && *app.model.mic_mute_status.lock().unwrap() == Some(true) {
        session.pause();
    } else {
        session.resume();
    }
}

pub fn change_mic_transcript_status(app: &App) -> Result<()> {
    apply_mute(app, &app.audio.mic.lock().unwrap());
    Ok(())
}

/// setMuteSelfStatus: VRChat's MuteSelf now
pub fn read_mute_self(app: &App) {
    *app.model.mic_mute_status.lock().unwrap() = app.model.osc.mute_self();
}

/// changeHandlerMute / changeHandlerAvatar (on the OSC receive thread: nothing waits here)
pub fn on_osc_event(app: &App, event: OscEvent) {
    if !app.config.get_bool("VRC_MIC_MUTE_SYNC") {
        return;
    }
    match event {
        OscEvent::MuteSelf(muted) => {
            let mut status = app.model.mic_mute_status.lock().unwrap();
            if *status == Some(!muted) {
                *status = Some(muted);
                enqueue(app, &app.audio.mic_worker, None, |a| {
                    let _ = change_mic_transcript_status(a);
                });
            }
        }
        // the avatar loaded: MuteSelf can be read now (on its own thread: an HTTP wait)
        OscEvent::AvatarChange => enqueue(app, &app.audio.avatar_worker, None, |a| {
            let mute = a.model.osc.mute_self();
            ipc::print_log("OSC: MuteSelf read on avatar change", &json!({"mute": mute}));
            let Some(mute) = mute else { return };
            let mut status = a.model.mic_mute_status.lock().unwrap();
            if *status == Some(mute) {
                return;
            }
            *status = Some(mute);
            drop(status);
            enqueue(a, &a.audio.mic_worker, None, |a| {
                let _ = change_mic_transcript_status(a);
            });
        }),
    }
}

/// _initVrcMicMuteSync: MuteSelf when VRChat is already up (else on its avatar change)
pub fn init_vrc_mic_mute_sync(app: &App) -> Result<()> {
    read_mute_self(app);
    if app.model.mic_mute_status.lock().unwrap().is_some() {
        change_mic_transcript_status(app)?;
    }
    Ok(())
}

// --------------------------------------------------------------------------- device monitor

#[derive(Default)]
struct Flags {
    list: bool,
    mic_auto: bool,
    speaker_auto: bool,
}

/// DeviceManager's monitoring and the speaker's endpoint tracker
pub struct Monitor {
    flags: Mutex<Flags>,
    /// prev_*: the lists last told to the UI (empty at first, as in Python)
    prev: Mutex<Snapshot>,
    running: Mutex<Option<Running>>,
    notified: Arc<(Mutex<bool>, Condvar)>,
    tracker: Mutex<Option<ActiveEndpointTracker>>,
}

impl Default for Monitor {
    fn default() -> Self {
        Self {
            flags: Mutex::default(),
            prev: Mutex::new(Snapshot {
                mic: vec![(NO_HOST.into(), vec![NO_DEVICE.into()])],
                default_mic: (NO_HOST.into(), NO_DEVICE.into()),
                speaker: vec![NO_DEVICE.into()],
                default_speaker: NO_DEVICE.into(),
            }),
            running: Mutex::new(None),
            notified: Arc::default(),
            tracker: Mutex::new(None),
        }
    }
}

fn notify_monitor(notified: &(Mutex<bool>, Condvar)) {
    *notified.0.lock().unwrap() = true;
    notified.1.notify_all();
}

/// _syncMonitoringLifecycleLocked: the monitor runs while any of the flags is on
fn sync_monitoring(app: &App, flags: &MutexGuard<Flags>) {
    let mut running = app.audio.monitor.running.lock().unwrap();
    if flags.list || flags.mic_auto || flags.speaker_auto {
        if running.as_ref().is_some_and(|r| !r.thread.is_finished()) {
            return;
        }
        let stop = Arc::new(AtomicBool::new(false));
        let (me, flag) = (app.me(), stop.clone());
        if let Ok(thread) = std::thread::Builder::new().name("device_monitoring".into()).spawn(move || monitoring(me, flag)) {
            *running = Some(Running { stop, thread });
        }
    } else if let Some(r) = running.take() {
        r.stop.store(true, Ordering::SeqCst);
        notify_monitor(&app.audio.monitor.notified);
        let _ = join(r.thread, Duration::from_millis(500));
    }
}

fn set_flag(app: &App, set: impl FnOnce(&mut Flags)) {
    let mut flags = app.audio.monitor.flags.lock().unwrap();
    set(&mut flags);
    sync_monitoring(app, &flags);
}

/// monitoring: a device change (or every 2 s without the change notifications) reads the devices again
fn monitoring(me: Weak<App>, stop: Arc<AtomicBool>) {
    let notified = match me.upgrade() {
        Some(app) => app.audio.monitor.notified.clone(),
        None => return,
    };
    let n = notified.clone();
    let watcher = DeviceWatcher::start(move || notify_monitor(&n))
        .map_err(|e| logs::error("device watcher", &e)).ok();
    while !stop.load(Ordering::SeqCst) {
        let was_notified = {
            let mut flag = notified.0.lock().unwrap();
            *flag = false;
            let (mut flag, _) = notified.1.wait_timeout_while(flag, MONITOR_WAIT, |f| !*f).unwrap();
            std::mem::take(&mut *flag)
        };
        if stop.load(Ordering::SeqCst) {
            break;
        }
        if !was_notified && watcher.is_some() {
            continue;
        }
        let Some(app) = me.upgrade() else { break };
        let (mic_auto, speaker_auto) = {
            let f = app.audio.monitor.flags.lock().unwrap();
            (f.mic_auto, f.speaker_auto)
        };
        if mic_auto {
            enqueue(&app, &app.audio.mic_worker, None, stop_access_mic);
        }
        if speaker_auto {
            enqueue(&app, &app.audio.speaker_worker, None, stop_access_speaker);
        }
        let now = devices::update();
        notice_changes(&app, &now, mic_auto, speaker_auto);
        if mic_auto {
            enqueue(&app, &app.audio.mic_worker, None, restart_access_mic);
        }
        if speaker_auto {
            enqueue(&app, &app.audio.speaker_worker, None, restart_access_speaker);
        }
    }
    drop(watcher);
}

/// _applyDeviceDiffs + noticeUpdateDevices
fn notice_changes(app: &App, now: &Snapshot, mic_auto: bool, speaker_auto: bool) {
    let mut prev = app.audio.monitor.prev.lock().unwrap();
    let default_mic = prev.default_mic.1 != now.default_mic.1;
    let default_speaker = prev.default_speaker != now.default_speaker;
    let hosts = |s: &Snapshot| s.mic.iter().map(|(h, _)| h.clone()).collect::<Vec<_>>();
    let host_list = hosts(&prev) != hosts(now);
    let mic_list = prev.mic != now.mic;
    let speaker_list = prev.speaker != now.speaker;
    *prev = now.clone();
    drop(prev);
    let log = |r: Result<()>| {
        if let Err(e) = r {
            logs::error("device change", &format!("{e:#}"));
        }
    };
    if default_mic && mic_auto {
        log(update_selected_mic_device(app, &now.default_mic.0, &now.default_mic.1));
    }
    if default_speaker && speaker_auto {
        log(update_selected_speaker_device(app, &now.default_speaker));
    }
    if host_list {
        log(push_mic_host_list(app));
    }
    if mic_list {
        log(update_mic_device_list(app));
    }
    if speaker_list {
        log(update_speaker_device_list(app));
    }
}

fn stop_access_mic(app: &App) {
    if app.config.get_bool("ENABLE_TRANSCRIPTION_SEND") {
        let _ = stop_transcription(app, Kind::Mic);
    }
    if app.config.get_bool("ENABLE_CHECK_ENERGY_SEND") {
        let _ = set_energy(app, Kind::Mic, false);
    }
}

fn stop_access_speaker(app: &App) {
    if app.config.get_bool("ENABLE_TRANSCRIPTION_RECEIVE") {
        let _ = stop_transcription(app, Kind::Speaker);
    }
    if app.config.get_bool("ENABLE_CHECK_ENERGY_RECEIVE") {
        let _ = set_energy(app, Kind::Speaker, false);
    }
}

fn restart_access_mic(app: &App) {
    if app.config.get_bool("ENABLE_TRANSCRIPTION_SEND") {
        let _ = start_transcription(app, Kind::Mic);
    }
    if app.config.get_bool("ENABLE_CHECK_ENERGY_SEND") {
        let _ = set_energy(app, Kind::Mic, true);
    }
}

fn restart_access_speaker(app: &App) {
    if app.config.get_bool("ENABLE_TRANSCRIPTION_RECEIVE") {
        let _ = start_transcription(app, Kind::Speaker);
    }
    if app.config.get_bool("ENABLE_CHECK_ENERGY_RECEIVE") {
        let _ = set_energy(app, Kind::Speaker, true);
    }
}

/// updateSelectedMicDevice
fn update_selected_mic_device(app: &App, host: &str, device: &str) -> Result<()> {
    app.config.set("SELECTED_MIC_HOST", json!(host))?;
    app.config.set("SELECTED_MIC_DEVICE", json!(device))?;
    app.run(200, "selected_mic_host", app.config.get("SELECTED_MIC_HOST"))?;
    app.run(200, "selected_mic_device", app.config.get("SELECTED_MIC_DEVICE"))
}

fn update_selected_speaker_device(app: &App, device: &str) -> Result<()> {
    app.config.set("SELECTED_SPEAKER_DEVICE", json!(device))?;
    app.run(200, "selected_speaker_device", json!(device))
}

fn mic_hosts() -> Vec<String> {
    devices::snapshot().mic.into_iter().map(|(h, _)| h).collect()
}

/// getListMicDevice: the selected host's microphones
fn mic_device_list(app: &App) -> Vec<String> {
    devices::snapshot().mic_devices(&app.config.get_str("SELECTED_MIC_HOST")).cloned().unwrap_or_else(|| vec![NO_DEVICE.into()])
}

fn push_mic_host_list(app: &App) -> Result<()> {
    app.run(200, "selectable_mic_host_list", json!(mic_hosts()))
}

/// updateMicDeviceList: a selection that went is moved (or the transcription stops), then the list
fn update_mic_device_list(app: &App) -> Result<()> {
    sync_mic_selection(app)?;
    app.run(200, "selectable_mic_device_list", json!(mic_device_list(app)))
}

fn update_speaker_device_list(app: &App) -> Result<()> {
    sync_speaker_selection(app)?;
    app.run(200, "selectable_speaker_device_list", json!(devices::snapshot().speaker))
}

/// _getAvailableDefaultMicSelection: the default microphone, else the first one
fn fallback_mic(s: &Snapshot) -> Option<(String, String)> {
    let listed = |host: &str, device: &str| host != NO_HOST && device != NO_DEVICE && s.mic_devices(host).is_some_and(|d| d.iter().any(|n| n == device));
    if listed(&s.default_mic.0, &s.default_mic.1) {
        return Some(s.default_mic.clone());
    }
    s.mic.iter().filter(|(h, _)| h != NO_HOST)
        .find_map(|(h, d)| d.iter().find(|n| *n != NO_DEVICE).map(|n| (h.clone(), n.clone())))
}

fn fallback_speaker(s: &Snapshot) -> Option<String> {
    if s.default_speaker != NO_DEVICE && s.speaker.contains(&s.default_speaker) {
        return Some(s.default_speaker.clone());
    }
    s.speaker.iter().find(|n| *n != NO_DEVICE).cloned()
}

/// _synchronizeMicSelectionAfterDeviceUpdate
fn sync_mic_selection(app: &App) -> Result<()> {
    let s = devices::snapshot();
    let (host, device) = (app.config.get_str("SELECTED_MIC_HOST"), app.config.get_str("SELECTED_MIC_DEVICE"));
    if host != NO_HOST && device != NO_DEVICE && s.mic_devices(&host).is_some_and(|d| d.contains(&device)) {
        return Ok(());
    }
    if let Some((h, d)) = fallback_mic(&s) {
        update_selected_mic_device(app, &h, &d)?;
        if !app.config.get_bool("AUTO_MIC_SELECT") && (app.config.get_bool("ENABLE_TRANSCRIPTION_SEND") || app.config.get_bool("ENABLE_CHECK_ENERGY_SEND")) {
            enqueue(app, &app.audio.mic_worker, Some("mic_device_fallback"), |a| {
                if let Err(e) = reopen(a, Kind::Mic) {
                    logs::error("mic device fallback", &format!("{e:#}"));
                }
            });
        }
        return Ok(());
    }
    if host != NO_HOST || device != NO_DEVICE {
        app.config.set("SELECTED_MIC_HOST", json!(NO_HOST))?;
        app.config.set("SELECTED_MIC_DEVICE", json!(NO_DEVICE))?;
        app.run(200, "selected_mic_host", json!(NO_HOST))?;
        app.run(200, "selected_mic_device", json!(NO_DEVICE))?;
    }
    disable_after_device_loss(app, Kind::Mic)
}

fn sync_speaker_selection(app: &App) -> Result<()> {
    let s = devices::snapshot();
    let device = app.config.get_str("SELECTED_SPEAKER_DEVICE");
    if device != NO_DEVICE && s.speaker.contains(&device) {
        return Ok(());
    }
    if let Some(d) = fallback_speaker(&s) {
        update_selected_speaker_device(app, &d)?;
        if !app.config.get_bool("AUTO_SPEAKER_SELECT")
            && (app.config.get_bool("ENABLE_TRANSCRIPTION_RECEIVE") || app.config.get_bool("ENABLE_CHECK_ENERGY_RECEIVE")) {
            enqueue(app, &app.audio.speaker_worker, Some("speaker_device_fallback"), |a| {
                if let Err(e) = reopen(a, Kind::Speaker) {
                    logs::error("speaker device fallback", &format!("{e:#}"));
                }
            });
        }
        return Ok(());
    }
    if device != NO_DEVICE {
        app.config.set("SELECTED_SPEAKER_DEVICE", json!(NO_DEVICE))?;
        app.run(200, "selected_speaker_device", json!(NO_DEVICE))?;
    }
    disable_after_device_loss(app, Kind::Speaker)
}

/// _disableAudioAfterDeviceLoss: the transcription and the meter go off (the session stops on the worker)
fn disable_after_device_loss(app: &App, kind: Kind) -> Result<()> {
    let (t_name, e_name, t_endpoint, t_default, e_endpoint, e_default) = match kind {
        Kind::Mic => ("ENABLE_TRANSCRIPTION_SEND", "ENABLE_CHECK_ENERGY_SEND", "disable_transcription_send",
                      "/set/disable/transcription_send", "disable_check_mic_threshold", "/set/disable/check_mic_threshold"),
        Kind::Speaker => ("ENABLE_TRANSCRIPTION_RECEIVE", "ENABLE_CHECK_ENERGY_RECEIVE", "disable_transcription_receive",
                          "/set/disable/transcription_receive", "disable_check_speaker_threshold", "/set/disable/check_speaker_threshold"),
    };
    let (transcription, energy) = (app.config.get_bool(t_name), app.config.get_bool(e_name));
    if !(transcription || energy) {
        return Ok(());
    }
    app.config.set(t_name, json!(false))?;
    app.config.set(e_name, json!(false))?;
    if transcription {
        app.run_or(200, t_endpoint, t_default, json!(false));
    }
    if energy {
        app.run_or(200, e_endpoint, e_default, json!(false));
    }
    let (worker, key): (&Worker, &'static str) = match kind {
        Kind::Mic => (&app.audio.mic_worker, "mic_device_loss_stop"),
        Kind::Speaker => (&app.audio.speaker_worker, "speaker_device_loss_stop"),
    };
    let me = app.me();
    worker.enqueue(Some(key), move || {
        if let Some(app) = me.upgrade() {
            let mut session = kind.session(&app).lock().unwrap();
            let _ = session.reconfigure(&app, Some(false), Some(false), None);
        }
    });
    Ok(())
}

/// The speaker that plays now (Auto Speaker Select): its loopback selected and recorded
fn on_active_speaker(app: &App, endpoint: Option<String>) {
    let Some(endpoint) = endpoint else { return };
    let s = devices::snapshot();
    let target = endpoint.trim();
    let loopback = format!("{target}{}", vrct_audio::devices::LOOPBACK_SUFFIX);
    let found = s.speaker.iter().find(|n| n.trim() == loopback)
        .or_else(|| s.speaker.iter().find(|n| !n.trim().is_empty() && n.trim().starts_with(target)));
    let Some(device) = found.cloned() else { return };
    if let Err(e) = update_selected_speaker_device(app, &device) {
        logs::error("active speaker", &format!("{e:#}"));
    }
    enqueue(app, &app.audio.speaker_worker, Some("speaker_reconfigure"), |a| {
        if let Err(e) = reopen(a, Kind::Speaker) {
            logs::error("speaker reconfigure", &format!("{e:#}"));
        }
    });
}

/// applyAutoMicSelect: the lists and the default told now, then followed
fn apply_auto_mic_select(app: &App) -> Result<()> {
    let s = devices::update();
    push_mic_host_list(app)?;
    update_mic_device_list(app)?;
    update_selected_mic_device(app, &s.default_mic.0, &s.default_mic.1)?;
    set_flag(app, |f| f.mic_auto = true);
    Ok(())
}

fn apply_auto_speaker_select(app: &App) -> Result<()> {
    let s = devices::update();
    update_speaker_device_list(app)?;
    update_selected_speaker_device(app, &s.default_speaker)?;
    {
        let mut tracker = app.audio.monitor.tracker.lock().unwrap();
        if tracker.is_none() {
            let me = app.me();
            *tracker = Some(ActiveEndpointTracker::start(Flow::Render, move |name| {
                if let Some(app) = me.upgrade() {
                    on_active_speaker(&app, name);
                }
            }));
        }
    }
    set_flag(app, |f| f.speaker_auto = true);
    Ok(())
}

// ------------------------------------------------------------------------------------- state

/// The audio state of the app
pub struct Audio {
    pub mic: Mutex<Session>,
    pub speaker: Mutex<Session>,
    pub mic_worker: Worker,
    pub speaker_worker: Worker,
    /// the MuteSelf queries after an avatar change, one at a time
    pub avatar_worker: Worker,
    pub monitor: Monitor,
}

impl Default for Audio {
    fn default() -> Self {
        Self {
            mic: Mutex::new(Session::new(Kind::Mic)),
            speaker: Mutex::new(Session::new(Kind::Speaker)),
            mic_worker: Worker::new("mic_lifecycle_worker"),
            speaker_worker: Worker::new("speaker_lifecycle_worker"),
            avatar_worker: Worker::new("osc_avatar_query"),
            monitor: Monitor::default(),
        }
    }
}

/// init: the device lists followed, the automatic selections on
pub fn init_devices(app: &App) -> Result<()> {
    set_flag(app, |f| f.list = true);
    ipc::log("Init Auto Device Selection");
    if app.config.get_bool("AUTO_MIC_SELECT") {
        apply_auto_mic_select(app)?;
    }
    if app.config.get_bool("AUTO_SPEAKER_SELECT") {
        apply_auto_speaker_select(app)?;
    }
    Ok(())
}

/// lock.acquire(timeout=...): None when it did not come in time
fn lock_for<'a, T>(mutex: &'a Mutex<T>, timeout: Duration) -> Option<MutexGuard<'a, T>> {
    let deadline = Instant::now() + timeout;
    loop {
        if let Ok(guard) = mutex.try_lock() {
            return Some(guard);
        }
        if Instant::now() >= deadline {
            return None;
        }
        std::thread::sleep(Duration::from_millis(20));
    }
}

/// Controller.shutdown's audio part
pub fn shutdown(app: &App) {
    set_flag(app, |f| *f = Flags::default());
    app.audio.monitor.tracker.lock().unwrap().take();
    std::thread::scope(|s| {
        s.spawn(|| app.audio.mic_worker.stop(SHUTDOWN_WAIT));
        s.spawn(|| app.audio.speaker_worker.stop(SHUTDOWN_WAIT));
    });
    app.audio.avatar_worker.stop(Duration::from_secs(1));
    for kind in [Kind::Mic, Kind::Speaker] {
        match lock_for(kind.session(app), SHUTDOWN_WAIT) {
            Some(mut session) => {
                session.stop();
            }
            None => ipc::log(format!("shutdown: {} のロック取得が {}s でタイムアウトしたため、この停止処理をスキップします",
                                     kind.label(), SHUTDOWN_WAIT.as_secs())),
        }
    }
}

// ----------------------------------------------------------------------------------- handlers

pub fn get_mic_host_list(_: &App, _: Data) -> Result<Reply> {
    Ok(Reply::ok(json!(mic_hosts())))
}

pub fn get_mic_device_list(app: &App, _: Data) -> Result<Reply> {
    Ok(Reply::ok(json!(mic_device_list(app))))
}

pub fn get_speaker_device_list(_: &App, _: Data) -> Result<Reply> {
    Ok(Reply::ok(json!(devices::snapshot().speaker)))
}

/// setSelectedMicHost: the device kept when the host has it, else the host's first
pub fn set_selected_mic_host(app: &App, data: Data) -> Result<Reply> {
    let previous = app.config.get("SELECTED_MIC_DEVICE");
    app.config.set("SELECTED_MIC_HOST", data.unwrap_or(Value::Null))?;
    let list = mic_device_list(app);
    if list.iter().any(|d| json!(d) == previous) {
        app.config.set("SELECTED_MIC_DEVICE", previous)?;
    } else {
        app.config.set("SELECTED_MIC_DEVICE", json!(list.first().cloned().unwrap_or_else(|| NO_DEVICE.into())))?;
    }
    reopen(app, Kind::Mic)?;
    app.run(200, "selectable_mic_device_list", json!(mic_device_list(app)))?;
    app.run(200, "selected_mic_device", app.config.get("SELECTED_MIC_DEVICE"))?;
    current(app, "SELECTED_MIC_HOST")
}

pub fn set_selected_mic_device(app: &App, data: Data) -> Result<Reply> {
    app.config.set("SELECTED_MIC_DEVICE", data.unwrap_or(Value::Null))?;
    reopen(app, Kind::Mic)?;
    current(app, "SELECTED_MIC_DEVICE")
}

pub fn set_selected_speaker_device(app: &App, data: Data) -> Result<Reply> {
    app.config.set("SELECTED_SPEAKER_DEVICE", data.unwrap_or(Value::Null))?;
    reopen(app, Kind::Speaker)?;
    current(app, "SELECTED_SPEAKER_DEVICE")
}

pub fn set_enable_auto_mic_select(app: &App, _: Data) -> Result<Reply> {
    if app.config.get("AUTO_MIC_SELECT") == json!(false) {
        apply_auto_mic_select(app)?;
        app.config.set("AUTO_MIC_SELECT", json!(true))?;
    }
    current(app, "AUTO_MIC_SELECT")
}

pub fn set_disable_auto_mic_select(app: &App, _: Data) -> Result<Reply> {
    if app.config.get_bool("AUTO_MIC_SELECT") {
        set_flag(app, |f| f.mic_auto = false);
        app.config.set("AUTO_MIC_SELECT", json!(false))?;
    }
    current(app, "AUTO_MIC_SELECT")
}

pub fn set_enable_auto_speaker_select(app: &App, _: Data) -> Result<Reply> {
    if app.config.get("AUTO_SPEAKER_SELECT") == json!(false) {
        apply_auto_speaker_select(app)?;
        app.config.set("AUTO_SPEAKER_SELECT", json!(true))?;
    }
    current(app, "AUTO_SPEAKER_SELECT")
}

pub fn set_disable_auto_speaker_select(app: &App, _: Data) -> Result<Reply> {
    if app.config.get_bool("AUTO_SPEAKER_SELECT") {
        app.audio.monitor.tracker.lock().unwrap().take();
        set_flag(app, |f| f.speaker_auto = false);
        app.config.set("AUTO_SPEAKER_SELECT", json!(false))?;
    }
    current(app, "AUTO_SPEAKER_SELECT")
}

fn energy_switch(app: &App, kind: Kind, name: &str, on: bool) -> Result<Reply> {
    if app.config.get(name) == json!(!on) {
        set_energy(app, kind, on)?;
        app.config.set(name, json!(on))?;
    }
    current(app, name)
}

pub fn set_enable_check_mic_threshold(app: &App, _: Data) -> Result<Reply> {
    energy_switch(app, Kind::Mic, "ENABLE_CHECK_ENERGY_SEND", true)
}

pub fn set_disable_check_mic_threshold(app: &App, _: Data) -> Result<Reply> {
    energy_switch(app, Kind::Mic, "ENABLE_CHECK_ENERGY_SEND", false)
}

pub fn set_enable_check_speaker_threshold(app: &App, _: Data) -> Result<Reply> {
    energy_switch(app, Kind::Speaker, "ENABLE_CHECK_ENERGY_RECEIVE", true)
}

pub fn set_disable_check_speaker_threshold(app: &App, _: Data) -> Result<Reply> {
    energy_switch(app, Kind::Speaker, "ENABLE_CHECK_ENERGY_RECEIVE", false)
}

fn transcription_switch(app: &App, kind: Kind, name: &str, on: bool) -> Result<Reply> {
    if on && app.config.get(name) == json!(false) {
        let started = start_transcription(app, kind)?;
        app.config.set(name, json!(started))?;
    } else if !on && app.config.get_bool(name) {
        stop_transcription(app, kind)?;
        app.config.set(name, json!(false))?;
    }
    current(app, name)
}

pub fn set_enable_transcription_send(app: &App, _: Data) -> Result<Reply> {
    transcription_switch(app, Kind::Mic, "ENABLE_TRANSCRIPTION_SEND", true)
}

pub fn set_disable_transcription_send(app: &App, _: Data) -> Result<Reply> {
    transcription_switch(app, Kind::Mic, "ENABLE_TRANSCRIPTION_SEND", false)
}

pub fn set_enable_transcription_receive(app: &App, _: Data) -> Result<Reply> {
    transcription_switch(app, Kind::Speaker, "ENABLE_TRANSCRIPTION_RECEIVE", true)
}

pub fn set_disable_transcription_receive(app: &App, _: Data) -> Result<Reply> {
    transcription_switch(app, Kind::Speaker, "ENABLE_TRANSCRIPTION_RECEIVE", false)
}

pub fn set_enable_vrc_mic_mute_sync(app: &App, _: Data) -> Result<Reply> {
    if app.config.get("VRC_MIC_MUTE_SYNC") == json!(false) {
        if !app.model.osc.is_osc_query_enabled() {
            return Ok(errors::error("VRC_MIC_MUTE_SYNC_OSC_DISABLED", app.config.get("VRC_MIC_MUTE_SYNC")));
        }
        app.config.set("VRC_MIC_MUTE_SYNC", json!(true))?;
        read_mute_self(app);
        change_mic_transcript_status(app)?;
    }
    current(app, "VRC_MIC_MUTE_SYNC")
}

pub fn set_disable_vrc_mic_mute_sync(app: &App, _: Data) -> Result<Reply> {
    if app.config.get_bool("VRC_MIC_MUTE_SYNC") {
        app.config.set("VRC_MIC_MUTE_SYNC", json!(false))?;
        change_mic_transcript_status(app)?;
    }
    current(app, "VRC_MIC_MUTE_SYNC")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn worker_runs_in_order_and_coalesces_waiting_jobs() {
        let worker = Worker::new("test");
        let log = Arc::new(Mutex::new(vec![]));
        let (gate_tx, gate_rx) = mpsc::channel::<()>();
        let l = log.clone();
        // the first job holds the worker so the next ones wait
        worker.enqueue(None, move || {
            let _ = gate_rx.recv();
            l.lock().unwrap().push("first");
        });
        for name in ["a", "b"] {
            let l = log.clone();
            worker.enqueue(Some("key"), move || l.lock().unwrap().push(name));
        }
        let l = log.clone();
        worker.enqueue(None, move || l.lock().unwrap().push("last"));
        gate_tx.send(()).unwrap();
        worker.stop(Duration::from_secs(5));
        assert_eq!(*log.lock().unwrap(), ["first", "a", "last"]);
        assert!(!worker.enqueue(None, || {}));
    }
}
