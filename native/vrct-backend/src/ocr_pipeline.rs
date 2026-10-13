//! The chat-bubble OCR (models/ocr/ocr_pipeline.py): on its own thread, every poll interval, the
//! VRChat frame → the bubbles (YOLOX) → their text (RapidOCR) → the lines joined → a text not seen
//! lately goes to the callback. Below normal priority, so VR UI and VRChat come first.
use crate::ocr_capture::OcrCapture;
use crate::platform;
use std::collections::{HashSet, VecDeque};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Condvar, Mutex};
use std::time::{Duration, Instant};
use vrct_ocr::detector::BubbleDetector;
use vrct_ocr::engine::{reader, readtext_bgr, resolve_model_spec, Line};
use vrct_ocr::rapidocr::RapidOcr;

const MAX_CANDIDATES_PER_TICK: usize = 6;
const TICK_OCR_BUDGET_RATIO: f64 = 0.8;
const STATUS_INTERVAL: Duration = Duration::from_secs(30);
const DEDUP_RETENTION_SEC: f64 = 30.0;
const DEDUP_MAX_ITEMS: usize = 128;
const SENTENCE_END_CHARS: [char; 12] = ['。', '．', '.', '！', '!', '？', '?', '…', '」', '』', ')', '）'];

#[derive(Clone, Debug, PartialEq)]
pub struct Settings {
    pub source_language: String,
    pub window_title: String,
    pub poll_interval_ms: i64,
    pub min_confidence: f64,
    pub min_text_length: i64,
}

/// Where the models are: RapidOCR's folder and the bubble detector
#[derive(Clone)]
pub struct Models {
    pub rapidocr: PathBuf,
    pub detector: PathBuf,
}

/// _isLatin: ASCII letters, digits and quotes (a space joins lines around them)
fn is_latin(c: char) -> bool {
    c.is_ascii_alphanumeric() || c == '"' || c == '\''
}

/// _similar: an edit distance of at most `max_distance` (OCR flips a character or two between frames)
fn similar(a: &str, b: &str, max_distance: usize) -> bool {
    if a == b {
        return true;
    }
    let (a, b): (Vec<char>, Vec<char>) = (a.chars().collect(), b.chars().collect());
    if a.len().abs_diff(b.len()) > max_distance {
        return false;
    }
    let mut previous: Vec<usize> = (0..=b.len()).collect();
    for (i, ca) in a.iter().enumerate() {
        let mut current = vec![i + 1];
        for (j, cb) in b.iter().enumerate() {
            current.push((previous[j + 1] + 1).min(current[j] + 1).min(previous[j] + usize::from(ca != cb)));
        }
        if current.iter().min().copied().unwrap_or(0) > max_distance {
            return false;
        }
        previous = current;
    }
    previous[b.len()] <= max_distance
}

/// _DedupCache: a text delivered is not delivered again while it stays on screen, nor for 30 s
/// after it went (the time is "last seen"); a near text counts as the same
#[derive(Default)]
struct Dedup {
    /// (key, last seen, text), oldest first
    items: VecDeque<(String, f64, String)>,
}

impl Dedup {
    fn evict_stale(&mut self, now: f64, retention: f64) {
        self.items.retain(|(_, seen, _)| now - seen <= retention);
        while self.items.len() > DEDUP_MAX_ITEMS {
            self.items.pop_front();
        }
    }

    fn touch(&mut self, i: usize, now: f64) {
        if let Some(mut item) = self.items.remove(i) {
            item.1 = now;
            self.items.push_back(item);
        }
    }

    /// seen: known (the time is refreshed, so a text on screen is never forgotten)
    fn seen(&mut self, key: &str, text: &str, now: f64) -> bool {
        if let Some(i) = self.items.iter().position(|(k, _, _)| k == key) {
            self.touch(i, now);
            return true;
        }
        if let Some(i) = self.items.iter().position(|(_, _, t)| similar(text, t, 2)) {
            self.touch(i, now);
            return true;
        }
        false
    }

    fn record(&mut self, key: String, text: String, now: f64) {
        self.items.retain(|(k, _, _)| *k != key);
        self.items.push_back((key, now, text));
    }
}

/// _mergeWords: the lines top to bottom; a line ending a sentence is a line break, otherwise a
/// wrap (a space around Latin letters, nothing between Japanese / Chinese)
pub fn merge_lines(lines: &[Line]) -> String {
    let mut lines: Vec<&Line> = lines.iter().filter(|l| !l.text.trim().is_empty()).collect();
    if lines.is_empty() {
        return String::new();
    }
    lines.sort_by(|a, b| a.top.partial_cmp(&b.top).unwrap_or(std::cmp::Ordering::Equal));
    let mut merged = lines[0].text.trim().to_string();
    for pair in lines.windows(2) {
        let (previous, text) = (pair[0].text.trim(), pair[1].text.trim());
        if previous.ends_with(SENTENCE_END_CHARS) {
            merged.push('\n');
        } else if previous.chars().last().is_some_and(is_latin) || text.chars().next().is_some_and(is_latin) {
            merged.push(' ');
        }
        merged.push_str(text);
    }
    merged.trim().to_string()
}

/// OcrStartError's codes
pub type StartError = &'static str;

struct Control {
    stopped: bool,
    pending: Option<Settings>,
}

pub struct OcrPipeline {
    control: Arc<(Mutex<Control>, Condvar)>,
    thread: Option<std::thread::JoinHandle<()>>,
}

type OnText = Box<dyn Fn(String, Option<String>) + Send>;
type Log = Arc<dyn Fn(String) + Send + Sync>;

/// BackgroundThreads: the native threads made since `before` (onnxruntime's) below normal priority
fn lower_new_threads(before: &HashSet<u32>, done: &mut HashSet<u32>) {
    for id in platform::thread_ids() {
        if !before.contains(&id) && done.insert(id) {
            platform::lower_thread(id);
        }
    }
}

fn load_reader(models: &Models, language: &str, log: &Log) -> Option<RapidOcr> {
    let spec = resolve_model_spec(language)?;
    match reader(&models.rapidocr, spec) {
        Ok(r) => Some(r),
        Err(e) => {
            log(format!("OCR pipeline: OCR engine init failed for {}/{}/{}: {e}", spec.ocr_version, spec.model_type,
                        spec.lang_rec.unwrap_or("default")));
            None
        }
    }
}

impl OcrPipeline {
    /// start: the models load here (both), then the worker starts. `on_text(text, language)`:
    /// language None for "auto".
    pub fn start(models: Models, settings: Settings, on_text: OnText, log: Log) -> Result<Self, StartError> {
        if !models.detector.is_file() || !models.rapidocr.is_dir() {
            log("OCR pipeline: engine or opencv unavailable, refusing to start".into());
            return Err("OCR_DISABLED_ENGINE_UNAVAILABLE");
        }
        if resolve_model_spec(&settings.source_language).is_none() {
            log(format!("OCR pipeline: language {:?} is not supported by the OCR engine", settings.source_language));
            return Err("OCR_DISABLED_UNSUPPORTED_LANGUAGE");
        }
        let before = platform::thread_ids();
        let reader = load_reader(&models, &settings.source_language, &log).ok_or("OCR_DISABLED_MODEL_LOAD_FAILED")?;
        let detector = BubbleDetector::new(&models.detector).map_err(|e| {
            log(format!("OCR pipeline: bubble detector model load failed: {e}"));
            "OCR_DISABLED_MODEL_LOAD_FAILED"
        })?;
        let mut lowered = HashSet::new();
        lower_new_threads(&before, &mut lowered);
        let control = Arc::new((Mutex::new(Control { stopped: false, pending: None }), Condvar::new()));
        let c = control.clone();
        let thread = std::thread::Builder::new().name("ocr_pipeline".into()).spawn(move || {
            platform::lower_current_thread();
            let mut worker = Worker { models, settings, reader, detector, on_text, log, dedup: Dedup::default(),
                                      counts: [0; 6], counts_since: None, last_tick: None, capture: None,
                                      started: Instant::now() };
            worker.run(&c, &before, &mut lowered);
        }).map_err(|_| "OCR_DISABLED_UNKNOWN")?;
        Ok(Self { control, thread: Some(thread) })
    }

    /// applyConfig: taken by the worker at its next tick (no OFF → ON)
    pub fn apply(&self, settings: Settings) {
        self.control.0.lock().unwrap().pending = Some(settings);
    }

    /// The worker ends (waited up to 5 s)
    pub fn stop(mut self) {
        self.control.0.lock().unwrap().stopped = true;
        self.control.1.notify_all();
        if let Some(thread) = self.thread.take() {
            let deadline = Instant::now() + Duration::from_secs(5);
            while !thread.is_finished() && Instant::now() < deadline {
                std::thread::sleep(Duration::from_millis(20));
            }
            if thread.is_finished() {
                let _ = thread.join();
            }
        }
    }
}

impl Drop for OcrPipeline {
    fn drop(&mut self) {
        self.control.0.lock().unwrap().stopped = true;
        self.control.1.notify_all();
    }
}

struct Worker {
    models: Models,
    settings: Settings,
    reader: RapidOcr,
    detector: BubbleDetector,
    on_text: OnText,
    log: Log,
    dedup: Dedup,
    /// tick, frame, candidate, ocr, text, emit
    counts: [u64; 6],
    counts_since: Option<Instant>,
    last_tick: Option<Instant>,
    capture: Option<OcrCapture>,
    /// the dedup cache's clock starts here
    started: Instant,
}

impl Worker {
    fn poll_interval(&self) -> Duration {
        Duration::from_secs_f64((self.settings.poll_interval_ms as f64 / 1000.0).max(0.1))
    }

    fn run(&mut self, control: &(Mutex<Control>, Condvar), before: &HashSet<u32>, lowered: &mut HashSet<u32>) {
        self.capture = Some(OcrCapture::new(&self.settings.window_title));
        let mut ticks = 0;
        loop {
            let started = Instant::now();
            let pending = {
                let mut c = control.0.lock().unwrap();
                if c.stopped {
                    break;
                }
                c.pending.take()
            };
            if let Some(settings) = pending {
                self.apply(settings);
            }
            self.tick(control);
            ticks += 1;
            // the threads onnxruntime starts on the first runs
            if ticks <= 2 {
                lower_new_threads(before, lowered);
            }
            let wait = self.poll_interval().saturating_sub(started.elapsed());
            let c = control.0.lock().unwrap();
            let (c, _) = control.1.wait_timeout_while(c, wait, |c| !c.stopped).unwrap();
            if c.stopped {
                break;
            }
        }
        if let Some(mut capture) = self.capture.take() {
            capture.close();
        }
    }

    /// _applyPending: the reader (when the language changes) and the capture (the window) change here
    fn apply(&mut self, settings: Settings) {
        if settings.source_language != self.settings.source_language {
            match resolve_model_spec(&settings.source_language) {
                None => (self.log)(format!("OCR pipeline: language {:?} is not supported, keeping {:?}",
                                            settings.source_language, self.settings.source_language)),
                Some(_) => match load_reader(&self.models, &settings.source_language, &self.log) {
                    None => (self.log)(format!("OCR pipeline: could not load the reader, keeping {:?}", self.settings.source_language)),
                    Some(reader) => {
                        self.reader = reader;
                        self.settings.source_language = settings.source_language.clone();
                        self.dedup = Dedup::default();
                    }
                },
            }
        }
        if !settings.window_title.is_empty() && settings.window_title != self.settings.window_title {
            self.settings.window_title = settings.window_title.clone();
            if let Some(mut capture) = self.capture.take() {
                capture.close();
            }
            self.capture = Some(OcrCapture::new(&self.settings.window_title));
        }
        self.settings.poll_interval_ms = settings.poll_interval_ms;
        self.settings.min_confidence = settings.min_confidence;
        self.settings.min_text_length = settings.min_text_length;
    }

    fn log_status(&mut self) {
        let Some(since) = self.counts_since else {
            self.counts_since = Some(Instant::now());
            return;
        };
        if since.elapsed() < STATUS_INTERVAL {
            return;
        }
        let c = self.counts;
        (self.log)(format!("OCR status ({:.0}s): tick={} frame={} candidate={} ocr={} text={} emit={} lang={:?}",
                           since.elapsed().as_secs_f64(), c[0], c[1], c[2], c[3], c[4], c[5], self.settings.source_language));
        self.counts = [0; 6];
        self.counts_since = Some(Instant::now());
    }

    fn tick(&mut self, control: &(Mutex<Control>, Condvar)) {
        self.counts[0] += 1;
        self.log_status();
        let log = self.log.clone();
        let Some(frame) = self.capture.as_mut().and_then(|c| c.get(&|l| log(l))) else { return };
        self.counts[1] += 1;
        let mut candidates = match self.detector.detect(&frame) {
            Ok(c) => c,
            Err(e) => {
                crate::logs::error("OCR detect", &e);
                return;
            }
        };
        if candidates.is_empty() {
            return;
        }
        self.counts[2] += candidates.len() as u64;
        candidates.truncate(MAX_CANDIDATES_PER_TICK);
        let now = Instant::now();
        let interval = self.last_tick.map_or(0.0, |t| now.duration_since(t).as_secs_f64());
        self.last_tick = Some(now);
        let clock = now.duration_since(self.started).as_secs_f64();
        self.dedup.evict_stale(clock, DEDUP_RETENTION_SEC.max(interval * 2.0));
        let deadline = now + self.poll_interval().mul_f64(TICK_OCR_BUDGET_RATIO);
        for (_, crop) in candidates {
            if control.0.lock().unwrap().stopped || Instant::now() > deadline {
                return;
            }
            self.counts[3] += 1;
            let lines = match readtext_bgr(&mut self.reader, &crop, self.settings.min_confidence) {
                Ok(l) => l,
                Err(e) => {
                    crate::logs::error("OCR read", &e);
                    continue;
                }
            };
            if lines.is_empty() {
                continue;
            }
            self.counts[4] += 1;
            let merged = merge_lines(&lines);
            if (merged.chars().count() as i64) < self.settings.min_text_length.max(1) {
                continue;
            }
            let key = merged.to_lowercase();
            if self.dedup.seen(&key, &merged, clock) {
                continue;
            }
            self.dedup.record(key, merged.clone(), clock);
            self.counts[5] += 1;
            let language = (self.settings.source_language != "auto").then(|| self.settings.source_language.clone());
            (self.on_text)(merged, language);
        }
    }
}

/// The models beside the executable (ocr/rapidocr, ocr/chatbox_yolox_tiny.onnx)
pub fn models(resources: &Path) -> Models {
    Models { rapidocr: resources.join("ocr").join("rapidocr"), detector: resources.join("ocr").join("chatbox_yolox_tiny.onnx") }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn line(text: &str, top: f64) -> Line {
        Line { text: text.into(), confidence: 1.0, left: 0.0, right: 0.0, top }
    }

    #[test]
    fn lines_join_as_python() {
        assert_eq!(merge_lines(&[line("こんにちは。", 0.0), line("元気？", 10.0)]), "こんにちは。\n元気？");
        assert_eq!(merge_lines(&[line("少", 0.0), line("しずつ", 10.0)]), "少しずつ");
        assert_eq!(merge_lines(&[line("hello", 0.0), line("world", 10.0)]), "hello world");
        assert_eq!(merge_lines(&[line("world", 10.0), line("hello", 0.0)]), "hello world");
        assert_eq!(merge_lines(&[line("  ", 0.0)]), "");
    }

    #[test]
    fn near_texts_are_the_same() {
        assert!(similar("こんにちは", "こんにちわ", 2));
        assert!(similar("abc", "abcde", 2));
        assert!(!similar("abc", "abcdef", 2));
        assert!(!similar("hello world", "goodbye all", 2));
        let mut d = Dedup::default();
        d.record("hello".into(), "hello".into(), 0.0);
        assert!(d.seen("helo", "helo", 10.0));
        d.evict_stale(45.0, 30.0);
        assert!(!d.seen("hello", "hello", 45.0));
    }
}
