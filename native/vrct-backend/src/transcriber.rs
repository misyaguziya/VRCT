//! The transcriber (transcription_transcriber.py + transcription_providers.py): phrases from the
//! recorder are gathered until a phrase is complete, then sent to the engine (Google, Whisper on
//! this PC, a Whisper API, Deepgram) once per candidate language, the most confident kept.
use crate::asr::{self, ApiError, Deepgram, Languages, WhisperApi};
use crate::net::Http;
use crate::recorder::{Failure, Recorder};
use std::collections::VecDeque;
use std::time::{Duration, Instant};
use vrct_audio::audioop;
use vrct_whisper::{TranscribeOptions, WhisperModel};

const MAX_PHRASE_DURATION_SECONDS: f64 = 15.0;
const VAD_PRE_PAD_MS: f64 = 300.0;
const VAD_POST_PAD_MS: f64 = 500.0;

pub enum Engine {
    Google,
    Whisper(WhisperModel),
    Api(WhisperApi),
    Deepgram(Deepgram),
}

impl Engine {
    fn name(&self) -> &str {
        match self {
            Engine::Google => "Google",
            Engine::Whisper(_) => "Whisper",
            Engine::Api(api) => &api.engine_name,
            Engine::Deepgram(_) => "Deepgram",
        }
    }
}

/// A transcript: the text, the candidate language it was heard in, how long the engine took
#[derive(Clone, Debug)]
pub struct Transcript {
    pub text: String,
    pub language: Option<String>,
    pub confidence: f64,
    pub asr_ms: u128,
}

pub struct Transcriber {
    pub label: &'static str,
    speaker: bool,
    phrase_timeout: f64,
    max_phrases: usize,
    vad: bool,
    engine: Engine,
    http: Http,
    sample_rate: u32,
    channels: u16,
    last_sample: Vec<u8>,
    last_spoken: Option<Instant>,
    phrase_started: Option<Instant>,
    transcripts: VecDeque<Transcript>,
    pub last_recognition_error: bool,
    attempts: u64,
    successes: u64,
}

/// What a candidate language gave: (text, confidence, no need to try the others)
type Heard = (String, f64, bool);

impl Transcriber {
    #[allow(clippy::too_many_arguments)]
    pub fn new(label: &'static str, speaker: bool, recorder: &Recorder, phrase_timeout: f64, max_phrases: usize, vad: bool,
               engine: Engine, http: Http) -> Self {
        Self {
            label,
            speaker,
            phrase_timeout,
            max_phrases,
            vad,
            engine,
            http,
            sample_rate: recorder.sample_rate,
            channels: recorder.channels,
            last_sample: vec![],
            last_spoken: None,
            phrase_started: None,
            transcripts: VecDeque::new(),
            last_recognition_error: false,
            attempts: 0,
            successes: 0,
        }
    }

    /// _bufferedSeconds
    fn buffered_seconds(&self) -> f64 {
        let per_second = self.sample_rate as f64 * 2.0 * self.channels as f64;
        if per_second == 0.0 { 0.0 } else { self.last_sample.len() as f64 / per_second }
    }

    /// The gathered audio as 16-bit mono at the recording's rate (processMicData / processSpeakerData)
    fn mono(&self) -> Result<Vec<u8>, String> {
        let raw = &self.last_sample;
        let channels = self.channels as usize;
        if !self.speaker || channels == 1 {
            return Ok(raw.clone());
        }
        if raw.len() % (2 * channels) != 0 {
            return Err("invalid speaker PCM frame".into());
        }
        if channels == 2 {
            Ok(audioop::tomono(raw, 2))
        } else {
            vrct_audio::speaker_downmix_pcm16(raw, channels).map_err(String::from)
        }
    }

    /// One candidate language
    #[allow(clippy::too_many_arguments)]
    fn transcribe_one(&mut self, languages: &Languages, pcm: &[u8], language: &str, country: &str, avg_logprob: f64,
                      no_speech_prob: f64, no_repeat_ngram_size: usize, force: bool) -> Result<Heard, String> {
        let at_16k = || audioop::convert(pcm, self.sample_rate, 2, 16000, 2).map_err(String::from);
        let code = |engine: &str| languages.code(language, country, engine).map(String::from)
            .ok_or_else(|| format!("KeyError: {language}/{country}/{engine}"));
        match &mut self.engine {
            Engine::Google => {
                if pcm.is_empty() {
                    return Ok((String::new(), 0.0, false));
                }
                let code = code("Google")?;
                let rate = self.sample_rate.max(8000);
                let raw = audioop::convert(pcm, self.sample_rate, 2, rate, 2).map_err(String::from)?;
                let flac = vrct_audio::encode_flac(&raw, rate).map_err(|_| "Google recognition request failed".to_string())?;
                let (text, confidence) = asr::google_recognize(&self.http, &flac, rate, &code)
                    .map_err(|_| "Google recognition request failed".to_string())?;
                Ok((text, confidence, false))
            }
            Engine::Whisper(model) => {
                let audio: Vec<f32> = at_16k()?.chunks_exact(2).map(|b| i16::from_le_bytes([b[0], b[1]]) as f32 / 32768.0).collect();
                let wanted = code("Whisper")?;
                let options = TranscribeOptions {
                    language: force.then(|| wanted.clone()),
                    log_prob_threshold: Some(avg_logprob),
                    no_speech_threshold: Some(no_speech_prob),
                    without_timestamps: true,
                    no_repeat_ngram_size,
                    ..Default::default()
                };
                let (segments, info) = model.transcribe(&audio, &options).map_err(|e| format!("{e:#}"))?;
                let text: String = segments.iter()
                    .filter(|s| !(s.avg_logprob < avg_logprob || f64::from(s.no_speech_prob) > no_speech_prob))
                    .map(|s| s.text.as_str()).collect();
                Ok((text, f64::from(info.language_probability), force || wanted == info.language))
            }
            Engine::Api(api) => {
                let wav = audioop::wav(&at_16k()?, 16000, 2);
                api.transcribe(languages, &wav, language, country, avg_logprob, no_speech_prob, force).map_err(api_error)
            }
            Engine::Deepgram(dg) => {
                let wav = audioop::wav(&at_16k()?, 16000, 2);
                dg.transcribe(languages, &wav, language, country, force).map_err(api_error)
            }
        }
    }

    /// _finalizeAndTranscribe: Err is the ASR failure that stops the session (an engine failed and
    /// nothing was heard)
    fn finalize_and_transcribe(&mut self, languages: &Languages, candidates: &[(String, String)], avg_logprob: f64,
                               no_speech_prob: f64, no_repeat_ngram_size: usize, log: &dyn Fn(String)) -> Result<bool, Failure> {
        if !matches!(self.engine, Engine::Whisper(_)) {
            self.last_recognition_error = false;
        }
        let mut best = Transcript { text: String::new(), language: None, confidence: 0.0, asr_ms: 0 };
        let mut provider_error: Option<String> = None;
        let started = Instant::now();
        let mut calls: Vec<String> = vec![];
        match self.mono() {
            Err(e) => provider_error = Some(e),
            Ok(pcm) => {
                let force = candidates.len() == 1;
                for (language, country) in candidates {
                    let t = Instant::now();
                    match self.transcribe_one(languages, &pcm, language, country, avg_logprob, no_speech_prob, no_repeat_ngram_size, force) {
                        Err(e) => {
                            self.last_recognition_error = true;
                            crate::logs::error(&format!("transcribe ({})", self.engine.name()), &e);
                            provider_error.get_or_insert(e);
                            calls.push(format!("{language}=error"));
                        }
                        Ok((text, confidence, definitive)) => {
                            let ms = t.elapsed().as_millis();
                            calls.push(if text.is_empty() { format!("{language}=nomatch({ms}ms)") } else { format!("{language}={ms}ms") });
                            if confidence > best.confidence {
                                best = Transcript { text, language: Some(language.clone()), confidence, asr_ms: 0 };
                            }
                            if definitive {
                                break;
                            }
                        }
                    }
                }
            }
        }
        let asr_ms = started.elapsed().as_millis();
        self.attempts += 1;
        let succeeded = !best.text.is_empty();
        let calls_text = format!("calls={}/{} [{}]", calls.len(), candidates.len(), calls.join(" "));
        if provider_error.is_some() && !succeeded {
            log(format!("[ASR-error][{}][{}] asr={asr_ms}ms {calls_text}", self.label, self.engine.name()));
            return Err(Failure { code: "ASR_ERROR", stage: "asr" });
        }
        if succeeded {
            self.last_recognition_error = false;
            self.successes += 1;
            best.asr_ms = asr_ms;
            // updateTranscript: the newest first, at most max_phrases + 1 kept
            if self.transcripts.len() > self.max_phrases {
                self.transcripts.pop_back();
            }
            self.transcripts.push_front(best);
        }
        log(format!("[ASR-stats][{}][{}] this_call={} attempts={} successes={} rate={:.1}% asr={asr_ms}ms {calls_text}",
                    if self.speaker { "speaker" } else { "mic" }, self.engine.name(), if succeeded { "success" } else { "failure" },
                    self.attempts, self.successes, self.successes as f64 / self.attempts as f64 * 100.0));
        Ok(true)
    }

    /// transcribeAudioQueue: the queued phrases gathered; sent when the phrase is complete (a
    /// pause of phrase_timeout, 15 s of speech, VAD's natural end), Google also while it grows.
    /// True when something was sent.
    // `unsent` is read in the energy path only (the macros set it in both)
    #[allow(unused_assignments)]
    pub fn transcribe_queue(&mut self, recorder: &Recorder, languages: &Languages, candidates: &[(String, String)],
                            avg_logprob: f64, no_speech_prob: f64, no_repeat_ngram_size: usize,
                            log: &dyn Fn(String)) -> Result<bool, Failure> {
        let is_google = matches!(self.engine, Engine::Google);
        let mut transcribed = false;
        let mut unsent = false;
        let kind = if self.speaker { "speaker" } else { "mic" };
        macro_rules! send_current {
            () => {{
                if self.last_sample.is_empty() {
                    false
                } else {
                    let original = self.last_sample.clone();
                    if self.vad {
                        let per_ms = self.sample_rate as f64 * 2.0 / 1000.0;
                        let mut padded = vec![0u8; (per_ms * VAD_PRE_PAD_MS) as usize];
                        padded.extend_from_slice(&original);
                        padded.extend(std::iter::repeat_n(0u8, (per_ms * VAD_POST_PAD_MS) as usize));
                        self.last_sample = padded;
                    }
                    let result = self.finalize_and_transcribe(languages, candidates, avg_logprob, no_speech_prob, no_repeat_ngram_size, log);
                    self.last_sample = original;
                    result?
                }
            }};
        }
        macro_rules! finalize {
            () => {{
                if send_current!() {
                    transcribed = true;
                }
                self.last_sample.clear();
                self.phrase_started = None;
                unsent = false;
            }};
        }
        if self.vad {
            while let Some(phrase) = recorder.take_phrase() {
                self.phrase_started.get_or_insert(phrase.at);
                self.last_sample.extend_from_slice(&phrase.pcm);
                self.last_spoken = Some(phrase.at);
                let seconds = self.buffered_seconds();
                let reason = phrase.reason.unwrap_or("None");
                let bytes = self.last_sample.len();
                if reason != "max_duration" {
                    log(format!("[VAD-merge][{kind}] finalize reason={reason:?} accumulated={seconds:.2}s bytes={bytes}"));
                    finalize!();
                } else if seconds >= MAX_PHRASE_DURATION_SECONDS {
                    log(format!("[VAD-merge][{kind}] safety-net finalize reason={reason:?} accumulated={seconds:.2}s bytes={bytes}"));
                    finalize!();
                } else if is_google && !recorder.has_phrase() {
                    log(format!("[VAD-merge][{kind}] interim-send (Google) reason={reason:?} accumulated={seconds:.2}s bytes={bytes}"));
                    if send_current!() {
                        transcribed = true;
                    }
                } else {
                    log(format!("[VAD-merge][{kind}] accumulate reason={reason:?} accumulated={seconds:.2}s bytes={bytes}"));
                }
                if transcribed {
                    return Ok(true);
                }
            }
            std::thread::sleep(Duration::from_millis(10));
            return Ok(false);
        }
        let timeout = Duration::from_secs_f64(self.phrase_timeout.max(0.0));
        while let Some(phrase) = recorder.take_phrase() {
            if self.last_spoken.is_some_and(|last| phrase.at.saturating_duration_since(last) > timeout) {
                if is_google && !unsent {
                    self.last_sample.clear();
                    self.phrase_started = None;
                } else {
                    finalize!();
                }
            }
            self.phrase_started.get_or_insert(phrase.at);
            self.last_sample.extend_from_slice(&phrase.pcm);
            self.last_spoken = Some(phrase.at);
            unsent = true;
            if self.buffered_seconds() >= MAX_PHRASE_DURATION_SECONDS {
                finalize!();
            } else if is_google && !recorder.has_phrase() {
                if send_current!() {
                    transcribed = true;
                }
                unsent = false;
            }
            if transcribed {
                return Ok(true);
            }
        }
        if !self.last_sample.is_empty() && self.last_spoken.is_some_and(|last| last.elapsed() > timeout) {
            if is_google && !unsent {
                self.last_sample.clear();
                self.phrase_started = None;
            } else {
                finalize!();
            }
        }
        if !transcribed {
            std::thread::sleep(Duration::from_millis(10));
        }
        Ok(transcribed)
    }

    /// clearTranscriptData: the gathered audio and the waiting transcripts go
    pub fn clear(&mut self) {
        self.transcripts.clear();
        self.last_sample.clear();
        self.last_spoken = None;
        self.phrase_started = None;
    }

    /// getTranscript: the oldest waiting
    pub fn take_transcript(&mut self) -> Option<Transcript> {
        self.transcripts.pop_back()
    }
}

fn api_error(e: ApiError) -> String {
    e.0.to_string()
}

/// getWhisperModel: a CUDA allocation failure is told apart (VRAM_OUT_OF_MEMORY)
pub fn load_whisper(path: &std::path::Path, device: &str, index: i32, compute_type: &str) -> anyhow::Result<WhisperModel> {
    WhisperModel::new(path, device, index, compute_type)
}
