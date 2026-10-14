//! faster-whisper 1.1.1's `WhisperModel(...)` and `transcribe(...)` on the path VRCT uses
//! (LocalWhisperProvider): temperature 0 only, no VAD filter, no word timestamps, no initial prompt,
//! prefix or hotwords, clip_timestamps "0". The loop, the prompts, the suppressed tokens and the
//! language detection follow transcribe.py / tokenizer.py line by line.
pub mod mel;

use anyhow::{anyhow, bail, Context, Result};
use mel::{FeatureExtractor, Features, N_FRAMES, TIME_PER_FRAME};
use std::collections::BTreeSet;
use std::path::Path;
use vrct_ct2::{ModelConfig, WhisperOptions};

/// tokenizer._LANGUAGE_CODES
pub const LANGUAGE_CODES: [&str; 100] = [
    "af", "am", "ar", "as", "az", "ba", "be", "bg", "bn", "bo", "br", "bs", "ca", "cs", "cy", "da", "de", "el", "en",
    "es", "et", "eu", "fa", "fi", "fo", "fr", "gl", "gu", "ha", "haw", "he", "hi", "hr", "ht", "hu", "hy", "id", "is",
    "it", "ja", "jw", "ka", "kk", "km", "kn", "ko", "la", "lb", "ln", "lo", "lt", "lv", "mg", "mi", "mk", "ml", "mn",
    "mr", "ms", "mt", "my", "ne", "nl", "nn", "no", "oc", "pa", "pl", "ps", "pt", "ro", "ru", "sa", "sd", "si", "sk",
    "sl", "sn", "so", "sq", "sr", "su", "sv", "sw", "ta", "te", "tg", "th", "tk", "tl", "tr", "tt", "uk", "ur", "uz",
    "vi", "yi", "yo", "zh", "yue",
];

/// WhisperModel.max_length
const MAX_LENGTH: usize = 448;
/// WhisperModel.time_precision
const TIME_PRECISION: f64 = 0.02;
/// WhisperModel.input_stride
const INPUT_STRIDE: usize = 2;

/// The transcribe() arguments VRCT can change; `Default` is faster-whisper's.
#[derive(Clone, Debug)]
pub struct TranscribeOptions {
    pub language: Option<String>,
    pub beam_size: usize,
    pub patience: f32,
    pub length_penalty: f32,
    pub repetition_penalty: f32,
    pub no_repeat_ngram_size: usize,
    pub log_prob_threshold: Option<f64>,
    pub no_speech_threshold: Option<f64>,
    pub condition_on_previous_text: bool,
    pub without_timestamps: bool,
}

impl Default for TranscribeOptions {
    fn default() -> Self {
        Self {
            language: None,
            beam_size: 5,
            patience: 1.0,
            length_penalty: 1.0,
            repetition_penalty: 1.0,
            no_repeat_ngram_size: 0,
            log_prob_threshold: Some(-1.0),
            no_speech_threshold: Some(0.6),
            condition_on_previous_text: true,
            without_timestamps: false,
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct Segment {
    pub id: usize,
    pub seek: usize,
    pub start: f64,
    pub end: f64,
    pub text: String,
    pub tokens: Vec<usize>,
    pub avg_logprob: f64,
    pub no_speech_prob: f32,
}

#[derive(Clone, Debug, PartialEq)]
pub struct TranscriptionInfo {
    pub language: String,
    pub language_probability: f32,
    pub duration: f64,
}

/// Token ids of the special tokens (Tokenizer's cached properties)
struct Special {
    sot: usize,
    sot_prev: usize,
    sot_lm: usize,
    eot: usize,
    no_timestamps: usize,
    transcribe: usize,
    translate: usize,
}

pub struct WhisperModel {
    model: vrct_ct2::Whisper,
    tokenizer: tokenizers::Tokenizer,
    features: FeatureExtractor,
    special: Special,
    /// get_suppressed_tokens(tokenizer, [-1]); the same for every language
    suppress_tokens: Vec<i32>,
}

impl WhisperModel {
    /// WhisperModel(path, device, device_index, compute_type, cpu_threads=4, num_workers=1,
    /// local_files_only=True), as getWhisperModel calls it.
    pub fn new(path: &Path, device: &str, device_index: i32, compute_type: &str) -> Result<Self> {
        let config = ModelConfig {
            device: device.into(),
            device_index,
            compute_type: compute_type.into(),
            inter_threads: 1,
            intra_threads: 4,
        };
        let model = vrct_ct2::Whisper::new(path, &config)?;
        let tokenizer = tokenizers::Tokenizer::from_file(path.join("tokenizer.json")).map_err(|e| anyhow!("{e}"))?;
        let features = FeatureExtractor::new(feature_size(path)?);
        let id = |t: &str| tokenizer.token_to_id(t).map(|v| v as usize).with_context(|| format!("no token {t}"));
        let special = Special {
            sot: id("<|startoftranscript|>")?,
            sot_prev: id("<|startofprev|>")?,
            sot_lm: id("<|startoflm|>")?,
            eot: id("<|endoftext|>")?,
            no_timestamps: id("<|notimestamps|>")?,
            transcribe: id("<|transcribe|>")?,
            translate: id("<|translate|>")?,
        };
        let mut this = Self { model, tokenizer, features, special, suppress_tokens: vec![] };
        this.suppress_tokens = this.suppressed_tokens()?;
        Ok(this)
    }

    fn encode_text(&self, text: &str) -> Result<Vec<usize>> {
        let encoding = self.tokenizer.encode(text, false).map_err(|e| anyhow!("{e}"))?;
        Ok(encoding.get_ids().iter().map(|&i| i as usize).collect())
    }

    /// Tokenizer.decode: text tokens only, special tokens skipped (tokenizers' default)
    fn decode(&self, tokens: &[usize]) -> Result<String> {
        let ids: Vec<u32> = tokens.iter().filter(|&&t| t < self.special.eot).map(|&t| t as u32).collect();
        self.tokenizer.decode(&ids, true).map_err(|e| anyhow!("{e}"))
    }

    /// Tokenizer.non_speech_tokens + get_suppressed_tokens(tokenizer, [-1])
    fn suppressed_tokens(&self) -> Result<Vec<i32>> {
        let mut symbols: Vec<String> = "\"#()*+/:;<=>@[\\]^_`{|}~「」『』".chars().map(String::from).collect();
        symbols.extend("<< >> <<< >>> -- --- -( -[ (' (\" (( )) ((( ))) [[ ]] {{ }} ♪♪ ♪♪♪".split(' ').map(String::from));
        let miscellaneous: Vec<String> = "♩♪♫♬♭♮♯".chars().map(String::from).collect();
        let first = |text: &str| -> Result<usize> { self.encode_text(text)?.first().copied().context("empty encoding") };
        let mut result = BTreeSet::from([first(" -")?, first(" '")?]);
        for symbol in symbols.iter().chain(&miscellaneous) {
            let is_misc = miscellaneous.contains(symbol);
            for tokens in [self.encode_text(symbol)?, self.encode_text(&format!(" {symbol}"))?] {
                if tokens.len() == 1 || is_misc {
                    result.insert(tokens[0]);
                }
            }
        }
        let s = &self.special;
        result.extend([s.transcribe, s.translate, s.sot, s.sot_prev, s.sot_lm]);
        Ok(result.into_iter().map(|t| t as i32).collect())
    }

    pub fn suppress_tokens(&self) -> &[i32] {
        &self.suppress_tokens
    }

    /// FeatureExtractor.__call__(audio)
    pub fn features(&self, audio: &[f32]) -> Result<Features> {
        self.features.compute(audio)
    }

    /// detect_language(features=features[..., 0:]) with language_detection_segments=1: the first 30 s
    /// (the last frame included) are encoded on their own; the most probable language wins.
    fn detect_language(&self, features: &Features) -> Result<(String, f32)> {
        let window = features.window(0, N_FRAMES);
        let encoded = self.model.encode(&window, features.n_mels, N_FRAMES)?;
        let probs = self.model.detect_language(&encoded)?;
        let (token, prob) = probs.first().context("no language")?;
        Ok((token[2..token.len() - 2].to_string(), *prob))
    }

    /// transcribe(audio, ..., temperature=0.0, task="transcribe"); the segments a caller iterating
    /// the generator gets.
    pub fn transcribe(&self, audio: &[f32], o: &TranscribeOptions) -> Result<(Vec<Segment>, TranscriptionInfo)> {
        let duration = audio.len() as f64 / mel::SAMPLE_RATE as f64;
        let features = self.features(audio)?;
        let multilingual = self.model.is_multilingual();
        let (language, language_probability) = match &o.language {
            None if multilingual => self.detect_language(&features)?,
            None => ("en".to_string(), 1.0),
            Some(l) if !multilingual && l != "en" => ("en".to_string(), 1.0),
            Some(l) => (l.clone(), 1.0),
        };
        // Tokenizer(hf_tokenizer, multilingual, task="transcribe", language)
        let sot_sequence = if multilingual {
            if !LANGUAGE_CODES.contains(&language.as_str()) {
                bail!("'{language}' is not a valid language code");
            }
            let lang = self.tokenizer.token_to_id(&format!("<|{language}|>")).context("language token")? as usize;
            vec![self.special.sot, lang, self.special.transcribe]
        } else {
            vec![self.special.sot]
        };
        let segments = self.generate_segments(&features, &sot_sequence, o)?;
        Ok((segments, TranscriptionInfo { language, language_probability, duration }))
    }

    fn generate_segments(&self, features: &Features, sot_sequence: &[usize], o: &TranscribeOptions) -> Result<Vec<Segment>> {
        let content_frames = features.frames - 1;
        let mut segments = vec![];
        let mut seek = 0;
        let mut all_tokens: Vec<usize> = vec![];
        let mut prompt_reset_since = 0;
        // clip_timestamps "0": one clip, [0, content_frames)
        while seek < content_frames {
            let time_offset = seek as f64 * TIME_PER_FRAME;
            let segment_size = N_FRAMES.min(content_frames - seek);
            let segment_duration = segment_size as f64 * TIME_PER_FRAME;
            let encoded = self.model.encode(&features.window(seek, segment_size), features.n_mels, N_FRAMES)?;
            let prompt = self.prompt(&all_tokens[prompt_reset_since..], sot_sequence, o.without_timestamps);
            let (result, avg_logprob) = self.generate(&encoded, &prompt, o)?;

            if let Some(no_speech_threshold) = o.no_speech_threshold {
                let mut should_skip = result.no_speech_prob as f64 > no_speech_threshold;
                if o.log_prob_threshold.is_some_and(|t| avg_logprob > t) {
                    should_skip = false; // the logprob is high enough, despite the no_speech_prob
                }
                if should_skip {
                    seek += segment_size;
                    continue;
                }
            }

            let tokens = result.sequences.into_iter().next().context("no sequence")?;
            let previous_seek = seek;
            let (current, next_seek) = self.split_by_timestamps(tokens, time_offset, segment_size, segment_duration, seek);
            seek = next_seek;
            for (start, end, tokens) in current {
                let text = self.decode(&tokens)?;
                if start == end || text.trim_matches(py_isspace).is_empty() {
                    continue;
                }
                all_tokens.extend(&tokens);
                segments.push(Segment {
                    id: segments.len() + 1,
                    seek: previous_seek,
                    start,
                    end,
                    text,
                    tokens,
                    avg_logprob,
                    no_speech_prob: result.no_speech_prob,
                });
            }
            // temperature 0 never exceeds prompt_reset_on_temperature (0.5)
            if !o.condition_on_previous_text {
                prompt_reset_since = all_tokens.len();
            }
        }
        Ok(segments)
    }

    /// get_prompt(tokenizer, previous_tokens, without_timestamps, prefix=None, hotwords=None)
    fn prompt(&self, previous: &[usize], sot_sequence: &[usize], without_timestamps: bool) -> Vec<usize> {
        let mut prompt = vec![];
        if !previous.is_empty() {
            prompt.push(self.special.sot_prev);
            prompt.extend(&previous[previous.len().saturating_sub(MAX_LENGTH / 2 - 1)..]);
        }
        prompt.extend(sot_sequence);
        if without_timestamps {
            prompt.push(self.special.no_timestamps);
        }
        prompt
    }

    /// generate_with_fallback with temperatures [0.0]. With one temperature the fallback only picks
    /// among that one result, so the compression ratio is not needed.
    fn generate(&self, encoded: &vrct_ct2::Encoded, prompt: &[usize], o: &TranscribeOptions) -> Result<(vrct_ct2::Generation, f64)> {
        let options = WhisperOptions {
            beam_size: o.beam_size,
            patience: o.patience,
            length_penalty: o.length_penalty,
            repetition_penalty: o.repetition_penalty,
            no_repeat_ngram_size: o.no_repeat_ngram_size,
            max_length: MAX_LENGTH,
            return_scores: true,
            return_no_speech_prob: true,
            suppress_blank: true,
            suppress_tokens: self.suppress_tokens.clone(),
            // int(round(max_initial_timestamp 1.0 / time_precision))
            max_initial_timestamp_index: 50,
            ..WhisperOptions::default()
        };
        let result = self.model.generate(encoded, prompt, &options)?;
        let seq_len = result.sequences.first().context("no sequence")?.len() as f64;
        // the average log prob recovered from the score, in Python floats
        let cum_logprob = *result.scores.first().context("no score")? as f64 * seq_len.powf(o.length_penalty as f64);
        Ok((result, cum_logprob / (seq_len + 1.0)))
    }

    /// _split_segments_by_timestamps: (start, end, tokens) per segment and the next seek.
    fn split_by_timestamps(&self, tokens: Vec<usize>, time_offset: f64, segment_size: usize, segment_duration: f64,
                           mut seek: usize) -> (Vec<(f64, f64, Vec<usize>)>, usize) {
        let begin = self.special.no_timestamps + 1; // timestamp_begin
        let position = |t: usize| t as i64 - begin as i64;
        let n = tokens.len();
        let single_timestamp_ending = n >= 2 && tokens[n - 2] < begin && begin <= tokens[n - 1];
        let consecutive: Vec<usize> = (1..n).filter(|&i| tokens[i] >= begin && tokens[i - 1] >= begin).collect();
        let mut out = vec![];
        if !consecutive.is_empty() {
            let mut slices = consecutive;
            if single_timestamp_ending {
                slices.push(n);
            }
            let mut last_slice = 0;
            for current in slices {
                let sliced = &tokens[last_slice..current];
                let start = time_offset + position(sliced[0]) as f64 * TIME_PRECISION;
                let end = time_offset + position(sliced[sliced.len() - 1]) as f64 * TIME_PRECISION;
                out.push((start, end, sliced.to_vec()));
                last_slice = current;
            }
            if single_timestamp_ending {
                seek += segment_size; // no speech after the last timestamp
            } else {
                // ignore the unfinished segment and seek to the last timestamp
                seek = (seek as i64 + position(tokens[last_slice - 1]) * INPUT_STRIDE as i64) as usize;
            }
        } else {
            let mut duration = segment_duration;
            if let Some(&last) = tokens.iter().filter(|&&t| t >= begin).next_back() {
                if last != begin {
                    duration = position(last) as f64 * TIME_PRECISION;
                }
            }
            out.push((time_offset, time_offset + duration, tokens));
            seek += segment_size;
        }
        (out, seek)
    }
}

/// preprocessor_config.json's feature_size (80 without the file). VRCT's models keep the other
/// FeatureExtractor arguments at their defaults; anything else is refused rather than half-handled.
fn feature_size(model_dir: &Path) -> Result<usize> {
    let path = model_dir.join("preprocessor_config.json");
    if !path.is_file() {
        return Ok(80);
    }
    let config: serde_json::Value = serde_json::from_slice(&std::fs::read(&path)?)?;
    for (key, default) in [("sampling_rate", 16000), ("hop_length", 160), ("chunk_length", 30), ("n_fft", 400)] {
        if config.get(key).is_some_and(|v| v.as_u64() != Some(default)) {
            bail!("{}: {key} {} is not supported", path.display(), config[key]);
        }
    }
    Ok(config.get("feature_size").and_then(|v| v.as_u64()).unwrap_or(80) as usize)
}

/// Python's str.isspace() for one character: Rust's White_Space plus U+001C..U+001F.
fn py_isspace(c: char) -> bool {
    c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c)
}
