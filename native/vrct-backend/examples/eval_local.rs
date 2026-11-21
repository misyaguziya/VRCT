//! P5 の評価: 今のローカルのエンジン (CTranslate2 の Whisper と NLLB / M2M100) を VRCT と同じ呼び方で
//! 動かし、結果と時間を JSON で書く。tools/eval_engines/run_eval.py が呼ぶ。配布物には入らない。
//!
//!     cargo run --release -p vrct-backend --example eval_local -- asr <model dir> <cpu|cuda> <in.json> <out.json>
//!     cargo run --release -p vrct-backend --example eval_local -- mt <weights root> <weight type> <cpu|cuda> <in.json> <out.json>
//!
//! asr の入力: [{"id", "wav", "language"}] (wav は 16 kHz mono 16 bit、language は Whisper の言語コード)。
//! mt の入力: [{"id", "text", "source", "target"}] (NLLB / M2M100 の言語コード)。
//! 出力: {"load_ms", "items": [{"id", "text", "ms", "error"?}]}。1 件目の前に 1 回だけ空打ちで温める。
use anyhow::{bail, Context, Result};
use serde_json::{json, Value};
use std::path::Path;
use std::time::Instant;
use vrct_backend::compute::best_compute_type;
use vrct_backend::translate::ctranslate2::Ct2Translator;
use vrct_whisper::{TranscribeOptions, WhisperModel};

// the config defaults (WHISPER: avg_logprob / no_speech_prob / no_repeat_ngram_size)
const AVG_LOGPROB: f64 = -0.8;
const NO_SPEECH_PROB: f64 = 0.6;

/// The samples of a 16 kHz mono 16 bit PCM WAVE file, as LocalWhisperProvider converts them
fn read_wav(path: &str) -> Result<Vec<f32>> {
    let bytes = std::fs::read(path).with_context(|| path.to_string())?;
    if bytes.len() < 12 || &bytes[..4] != b"RIFF" || &bytes[8..12] != b"WAVE" {
        bail!("{path}: not a WAVE file");
    }
    let (mut at, mut format, mut data) = (12, None, None);
    while at + 8 <= bytes.len() {
        let size = u32::from_le_bytes(bytes[at + 4..at + 8].try_into()?) as usize;
        let body = &bytes[at + 8..(at + 8 + size).min(bytes.len())];
        match &bytes[at..at + 4] {
            b"fmt " if body.len() >= 16 => format = Some(body[..16].to_vec()),
            b"data" => data = Some(body),
            _ => {}
        }
        at += 8 + size + (size & 1);
    }
    let (format, data) = (format.context("no fmt chunk")?, data.context("no data chunk")?);
    let field = |at: usize, len: usize| format[at..at + len].iter().rev().fold(0u32, |v, b| v << 8 | u32::from(*b));
    // PCM, 1 channel, 16000 Hz, 16 bit
    if (field(0, 2), field(2, 2), field(4, 4), field(14, 2)) != (1, 1, 16000, 16) {
        bail!("{path}: not 16 kHz mono 16 bit PCM");
    }
    Ok(data.chunks_exact(2).map(|b| i16::from_le_bytes([b[0], b[1]]) as f32 / 32768.0).collect())
}

fn ms(t: Instant) -> f64 {
    t.elapsed().as_secs_f64() * 1000.0
}

/// transcriber.rs の Engine::Whisper と同じオプションと区間の除き方 (言語は指定する)
fn transcribe(model: &WhisperModel, audio: &[f32], language: &str) -> Result<String> {
    let options = TranscribeOptions {
        language: Some(language.to_string()),
        log_prob_threshold: Some(AVG_LOGPROB),
        no_speech_threshold: Some(NO_SPEECH_PROB),
        without_timestamps: true,
        ..Default::default()
    };
    let (segments, _) = model.transcribe(audio, &options)?;
    Ok(segments.iter()
        .filter(|s| !(s.avg_logprob < AVG_LOGPROB || f64::from(s.no_speech_prob) > NO_SPEECH_PROB))
        .map(|s| s.text.as_str())
        .collect())
}

fn run(items: &[Value], mut one: impl FnMut(&Value) -> Result<String>) -> Vec<Value> {
    if let Some(first) = items.first() {
        let _ = one(first);
    }
    items.iter().map(|item| {
        let t = Instant::now();
        let result = one(item);
        let elapsed = ms(t);
        match result {
            Ok(text) => json!({"id": item["id"], "text": text, "ms": elapsed}),
            Err(e) => json!({"id": item["id"], "text": "", "ms": elapsed, "error": format!("{e:#}")}),
        }
    }).collect()
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let str_of = |v: &Value, k: &str| v[k].as_str().map(String::from).with_context(|| format!("no {k}"));
    let (load_ms, items, out) = match args.iter().map(String::as_str).collect::<Vec<_>>().as_slice() {
        ["asr", dir, device, input, out] => {
            let items: Vec<Value> = serde_json::from_str(&std::fs::read_to_string(input)?)?;
            let t = Instant::now();
            let model = WhisperModel::new(Path::new(dir), device, 0, &best_compute_type(device, 0))?;
            let load_ms = ms(t);
            let results = run(&items, |item| transcribe(&model, &read_wav(&str_of(item, "wav")?)?, &str_of(item, "language")?));
            (load_ms, results, out.to_string())
        }
        ["mt", root, weight_type, device, input, out] => {
            let items: Vec<Value> = serde_json::from_str(&std::fs::read_to_string(input)?)?;
            let t = Instant::now();
            let translator = Ct2Translator::load(Path::new(root), weight_type, device, 0, &best_compute_type(device, 0))?;
            let load_ms = ms(t);
            let results = run(&items, |item| {
                translator.translate(&str_of(item, "text")?, &str_of(item, "source")?, &str_of(item, "target")?)
            });
            (load_ms, results, out.to_string())
        }
        _ => bail!("usage: eval_local asr <model dir> <device> <in> <out> | mt <weights root> <weight type> <device> <in> <out>"),
    };
    std::fs::write(&out, serde_json::to_string_pretty(&json!({"load_ms": load_ms, "items": items}))?)?;
    Ok(())
}
