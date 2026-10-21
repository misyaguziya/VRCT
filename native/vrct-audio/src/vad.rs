//! Speech segments from VAD probabilities (audio_vad.py of the removed Python backend:
//! VadSegmenter and VadRecognizerAdapter): pre-roll, start after `min_speech_frames` positive
//! frames, end after `hangover_frames` frames below the negative threshold (the anchor, not a
//! decaying counter), and a forced split at `max_speech_frames` that keeps the VAD state.
use crate::audioop::Pcm16MonoNormalizer;
use std::collections::VecDeque;
use std::sync::atomic::{AtomicU64, Ordering};

pub const TARGET_SAMPLE_RATE: u32 = 16000;
pub const FRAME_SAMPLES: usize = 512;
const FRAME_BYTES: usize = FRAME_SAMPLES * 2;
pub const FRAME_DURATION_MS: f64 = FRAME_SAMPLES as f64 / TARGET_SAMPLE_RATE as f64 * 1000.0;

/// One counter for the process, as audio_vad's itertools.count()
static SEGMENT_IDS: AtomicU64 = AtomicU64::new(0);

fn next_segment_id() -> u64 {
    SEGMENT_IDS.fetch_add(1, Ordering::Relaxed)
}

/// The speech probability of 512-sample frames (Silero VAD)
pub trait FrameProbability {
    fn probability(&mut self, frame: &[f32]) -> Result<f32, String>;
    fn reset(&mut self);
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum EndReason {
    Silence,
    MaxDuration,
    Flush,
}

impl EndReason {
    pub fn as_str(self) -> &'static str {
        match self {
            EndReason::Silence => "silence",
            EndReason::MaxDuration => "max_duration",
            EndReason::Flush => "flush",
        }
    }
}

/// A finished segment: 16 kHz mono PCM16
#[derive(Debug)]
pub struct SpeechSegment {
    pub audio: Vec<u8>,
    pub segment_id: u64,
    pub reason: EndReason,
}

impl SpeechSegment {
    pub fn duration_ms(&self) -> f64 {
        self.audio.len() as f64 / 2.0 / TARGET_SAMPLE_RATE as f64 * 1000.0
    }
}

pub struct VadSegmenter<P: FrameProbability> {
    pub probability: P,
    speech_threshold: f64,
    negative_threshold: f64,
    hangover_frames: usize,
    max_speech_frames: Option<usize>,
    min_speech_frames: usize,
    pre_speech_pad_frames: usize,
    /// Diagnostics at speech start / end (printLog lines in Python)
    log: Option<Box<dyn FnMut(String) + Send>>,
    label: String,
    remainder: Vec<u8>,
    pre_speech_frames: VecDeque<Vec<u8>>,
    speech_frames: Vec<Vec<u8>>,
    positive_frames: usize,
    speech_frame_count: usize,
    silence_start_frame: Option<usize>,
    speaking: bool,
    segment_id: u64,
}

impl<P: FrameProbability> VadSegmenter<P> {
    /// VadSegmenter(probability, max_speech_frames=...) with the other defaults (threshold 0.25,
    /// negative 0.25 - 0.15, hangover 24, min speech 2, pre-roll 5)
    pub fn new(probability: P, max_speech_frames: Option<usize>) -> Self {
        let speech_threshold = 0.25;
        Self {
            probability,
            speech_threshold,
            negative_threshold: f64::max(0.0, speech_threshold - 0.15),
            hangover_frames: 24,
            max_speech_frames,
            min_speech_frames: 2,
            pre_speech_pad_frames: 5,
            log: None,
            label: "vad".into(),
            remainder: vec![],
            pre_speech_frames: VecDeque::new(),
            speech_frames: vec![],
            positive_frames: 0,
            speech_frame_count: 0,
            silence_start_frame: None,
            speaking: false,
            segment_id: next_segment_id(),
        }
    }

    /// diagnostic_callback / diagnostic_label
    pub fn with_log(mut self, label: &str, log: Box<dyn FnMut(String) + Send>) -> Self {
        self.label = label.into();
        self.log = Some(log);
        self
    }

    pub fn speaking(&self) -> bool {
        self.speaking
    }

    fn frame_probability(&mut self, frame: &[u8]) -> Result<f64, String> {
        let samples: Vec<f32> = frame.chunks_exact(2).map(|b| i16::from_le_bytes([b[0], b[1]]) as f32 / 32768.0).collect();
        Ok(self.probability.probability(&samples)? as f64)
    }

    /// 16 kHz mono PCM16 in, finished segments out
    pub fn process(&mut self, pcm: &[u8]) -> Result<Vec<SpeechSegment>, String> {
        self.remainder.extend_from_slice(pcm);
        let mut segments = vec![];
        while self.remainder.len() >= FRAME_BYTES {
            let frame: Vec<u8> = self.remainder.drain(..FRAME_BYTES).collect();
            let probability = self.frame_probability(&frame)?;
            if let Some(segment) = self.process_frame(frame, probability) {
                segments.push(segment);
            }
        }
        Ok(segments)
    }

    /// Ends the stream (pause / stop): a segment still open is finished with reason "flush"
    pub fn flush(&mut self) -> Result<Option<SpeechSegment>, String> {
        if !self.remainder.is_empty() {
            let mut padded = std::mem::take(&mut self.remainder);
            padded.resize(FRAME_BYTES, 0);
            let probability = self.frame_probability(&padded)?;
            if let Some(segment) = self.process_frame(padded, probability) {
                return Ok(Some(segment));
            }
        }
        if !self.speaking {
            return Ok(None);
        }
        Ok(self.finish_segment(EndReason::Flush))
    }

    /// Back to the initial state (mute, device change)
    pub fn reset(&mut self) {
        self.remainder.clear();
        self.speech_frames.clear();
        self.positive_frames = 0;
        self.speech_frame_count = 0;
        self.silence_start_frame = None;
        self.speaking = false;
        self.pre_speech_frames.clear();
        self.probability.reset();
    }

    fn process_frame(&mut self, frame: Vec<u8>, probability: f64) -> Option<SpeechSegment> {
        if !self.speaking {
            if self.pre_speech_frames.len() == self.pre_speech_pad_frames {
                self.pre_speech_frames.pop_front();
            }
            if self.pre_speech_pad_frames > 0 {
                self.pre_speech_frames.push_back(frame);
            }
            if probability >= self.speech_threshold {
                self.positive_frames += 1;
            } else {
                self.positive_frames = 0;
            }
            if self.positive_frames >= self.min_speech_frames {
                self.speaking = true;
                self.speech_frames = self.pre_speech_frames.drain(..).collect();
                self.speech_frame_count = self.positive_frames;
                self.silence_start_frame = None;
                let message = format!(
                    "speech_start segment_id={} prob={probability:.3} threshold={} pre_roll_frames={}",
                    self.segment_id, self.speech_threshold, self.speech_frames.len());
                self.log(message);
                if self.max_speech_reached() {
                    return self.finish_segment(EndReason::MaxDuration);
                }
            }
            return None;
        }
        self.speech_frames.push(frame);
        self.speech_frame_count += 1;
        if probability >= self.speech_threshold {
            self.silence_start_frame = None;
        } else if probability < self.negative_threshold {
            let start = *self.silence_start_frame.get_or_insert(self.speech_frame_count);
            if self.speech_frame_count - start >= self.hangover_frames {
                return self.finish_segment(EndReason::Silence);
            }
        }
        if self.max_speech_reached() {
            return self.finish_segment(EndReason::MaxDuration);
        }
        None
    }

    fn max_speech_reached(&self) -> bool {
        self.max_speech_frames.is_some_and(|max| self.speech_frame_count >= max)
    }

    fn finish_segment(&mut self, reason: EndReason) -> Option<SpeechSegment> {
        let frame_count = self.speech_frame_count;
        let result = (self.speaking && frame_count >= self.min_speech_frames)
            .then(|| SpeechSegment { audio: self.speech_frames.concat(), segment_id: self.segment_id, reason });
        if self.speaking || self.positive_frames > 0 {
            self.segment_id = next_segment_id();
        }
        self.speech_frames.clear();
        self.positive_frames = 0;
        self.speech_frame_count = 0;
        self.silence_start_frame = None;
        self.speaking = false;
        self.pre_speech_frames.clear();
        if let Some(r) = &result {
            let message = format!("speech_end segment_id={} reason={} duration_ms={:.1} frames={frame_count}",
                                  r.segment_id, reason.as_str(), r.duration_ms());
            self.log(message);
        }
        // a forced split keeps the VAD state: speech goes on
        if reason != EndReason::MaxDuration {
            self.probability.reset();
        }
        result
    }

    fn log(&mut self, message: String) {
        let label = &self.label;
        if let Some(log) = &mut self.log {
            log(format!("[VAD][{label}] {message}"));
        }
    }
}

/// VadRecognizerAdapter: the device's PCM (any rate, width, channels) through the normalizer
/// into the segmenter
pub struct VadRecognizer<P: FrameProbability> {
    normalizer: Pcm16MonoNormalizer,
    pub segmenter: VadSegmenter<P>,
}

impl<P: FrameProbability> VadRecognizer<P> {
    pub fn new(sample_rate: u32, sample_width: usize, channels: usize, segmenter: VadSegmenter<P>) -> Self {
        Self { normalizer: Pcm16MonoNormalizer::new(sample_rate, sample_width, channels), segmenter }
    }

    pub fn process(&mut self, pcm: &[u8]) -> Result<Vec<SpeechSegment>, String> {
        let normalized = self.normalizer.process(pcm)?;
        if normalized.is_empty() {
            return Ok(vec![]);
        }
        self.segmenter.process(&normalized)
    }

    pub fn flush(&mut self) -> Result<Option<SpeechSegment>, String> {
        let result = self.segmenter.flush();
        self.normalizer.reset();
        result
    }

    pub fn reset(&mut self) {
        self.normalizer.reset();
        self.segmenter.reset();
    }
}
