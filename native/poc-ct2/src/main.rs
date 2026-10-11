//! PoC 1: run Whisper and NLLB through ct2rs the way the Python backend does, and write the
//! results next to reference.py's python.json for comparison.
//!
//!     poc-ct2 <data dir> <weights dir> [cpu|cuda]
//!
//! Whisper follows faster-whisper 1.1.1 (transcribe with VRCT's options, audio under 30 s):
//! log-mel features as FeatureExtractor computes them, encode once, detect the language on the
//! encoder output, generate with the prompt [sot, lang, transcribe, notimestamps] and turn the
//! score into avg_logprob like generate_with_fallback. NLLB follows translation_translator.py.
use anyhow::{anyhow, Context, Result};
use ct2rs::sys::{
    ComputeType, Config, Device, StorageView, TranslationOptions, Translator, Whisper, WhisperOptions,
};
use rustfft::{num_complex::Complex32, FftPlanner};
use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use std::time::Instant;
use tokenizers::Tokenizer;

const SAMPLE_RATE: usize = 16000;
const N_FFT: usize = 400;
const HOP: usize = 160;
const N_MELS: usize = 80;
const N_FRAMES: usize = 3000;

/// Mel filter bank of FeatureExtractor.get_mel_filters (Slaney scale, slaney norm), [n_mels][n_fft/2+1].
fn mel_filters() -> Vec<Vec<f64>> {
    let n_freq = N_FFT / 2 + 1;
    let fftfreqs: Vec<f64> = (0..n_freq).map(|i| i as f64 * SAMPLE_RATE as f64 / N_FFT as f64).collect();
    let (min_mel, max_mel) = (0.0f64, 45.245640471924965f64);
    let mels: Vec<f64> = (0..N_MELS + 2).map(|i| min_mel + (max_mel - min_mel) * i as f64 / (N_MELS + 1) as f64).collect();
    let f_sp = 200.0 / 3.0;
    let min_log_hz = 1000.0;
    let min_log_mel = min_log_hz / f_sp;
    let logstep = (6.4f64).ln() / 27.0;
    let freqs: Vec<f64> = mels
        .iter()
        .map(|&m| if m >= min_log_mel { min_log_hz * (logstep * (m - min_log_mel)).exp() } else { f_sp * m })
        .collect();
    (0..N_MELS)
        .map(|m| {
            let enorm = 2.0 / (freqs[m + 2] - freqs[m]);
            fftfreqs
                .iter()
                .map(|&f| {
                    let lower = -(freqs[m] - f) / (freqs[m + 1] - freqs[m]);
                    let upper = (freqs[m + 2] - f) / (freqs[m + 2] - freqs[m + 1]);
                    lower.min(upper).max(0.0) * enorm
                })
                .collect()
        })
        .collect()
}

/// FeatureExtractor.__call__(audio, padding=160, chunk_length=30), then the first window padded
/// to 3000 frames (pad_or_trim). Returns [n_mels * 3000] row-major.
fn log_mel(audio: &[f32]) -> Vec<f32> {
    let mut wave = audio.to_vec();
    wave.extend(std::iter::repeat(0.0).take(HOP)); // padding=160
    // center=True, reflect padding of n_fft/2 on both sides
    let pad = N_FFT / 2;
    let mut padded = Vec::with_capacity(wave.len() + 2 * pad);
    padded.extend((1..=pad).rev().map(|i| wave[i]));
    padded.extend_from_slice(&wave);
    padded.extend((1..=pad).map(|i| wave[wave.len() - 1 - i]));
    let n_frames = 1 + (padded.len() - N_FFT) / HOP;
    // np.hanning(n_fft + 1)[:-1]
    let window: Vec<f32> = (0..N_FFT)
        .map(|i| (0.5 - 0.5 * (2.0 * std::f64::consts::PI * i as f64 / N_FFT as f64).cos()) as f32)
        .collect();
    let fft = FftPlanner::<f32>::new().plan_fft_forward(N_FFT);
    let filters = mel_filters();
    let n_freq = N_FFT / 2 + 1;
    let frames = n_frames - 1; // magnitudes = |stft[..., :-1]|^2
    let mut mel = vec![0f32; N_MELS * frames];
    let mut buf = vec![Complex32::new(0.0, 0.0); N_FFT];
    for t in 0..frames {
        for i in 0..N_FFT {
            buf[i] = Complex32::new(padded[t * HOP + i] * window[i], 0.0);
        }
        fft.process(&mut buf);
        let power: Vec<f32> = buf[..n_freq].iter().map(|c| c.norm_sqr()).collect();
        for m in 0..N_MELS {
            let s: f32 = filters[m].iter().zip(&power).map(|(w, p)| *w as f32 * p).sum();
            mel[m * frames + t] = s.max(1e-10).log10();
        }
    }
    let max = mel.iter().cloned().fold(f32::MIN, f32::max);
    for v in mel.iter_mut() {
        *v = (v.max(max - 8.0) + 4.0) / 4.0;
    }
    // content_frames = features.shape[-1] - 1, first window, zero-padded to 3000
    let content = frames - 1;
    let mut out = vec![0f32; N_MELS * N_FRAMES];
    for m in 0..N_MELS {
        for t in 0..content.min(N_FRAMES) {
            out[m * N_FRAMES + t] = mel[m * frames + t];
        }
    }
    out
}

fn read_wav(path: &Path) -> Result<Vec<f32>> {
    let mut reader = hound::WavReader::open(path)?;
    let spec = reader.spec();
    if spec.sample_rate != 16000 || spec.channels != 1 || spec.bits_per_sample != 16 {
        return Err(anyhow!("{} is not 16 kHz mono 16-bit", path.display()));
    }
    Ok(reader.samples::<i16>().map(|s| s.map(|v| v as f32 / 32768.0)).collect::<Result<_, _>>()?)
}

fn config(device: Device) -> Config {
    Config {
        device,
        compute_type: ComputeType::INT8,
        num_threads_per_replica: 4,
        ..Default::default()
    }
}

fn whisper(data: &Path, weights: &Path, device: Device) -> Result<Value> {
    let model_dir = weights.join("whisper").join("base");
    let started = Instant::now();
    let model = Whisper::new(&model_dir, config(device))?;
    let load_ms = started.elapsed().as_millis();
    let tokenizer = Tokenizer::from_file(model_dir.join("tokenizer.json")).map_err(|e| anyhow!("{e}"))?;
    let suppress: Vec<i32> = serde_json::from_str(&std::fs::read_to_string(data.join("suppress_tokens.json"))?)?;
    let eot = tokenizer.token_to_id("<|endoftext|>").context("eot")? as usize;
    let mut results = serde_json::Map::new();
    let mut wavs: Vec<PathBuf> = std::fs::read_dir(data)?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().is_some_and(|e| e == "wav"))
        .collect();
    wavs.sort();
    for wav in wavs {
        let name = wav.file_stem().unwrap().to_string_lossy().to_string();
        let started = Instant::now();
        let mut mel = log_mel(&read_wav(&wav)?);
        // compare with the features faster-whisper computed
        let reference: Option<Vec<f32>> = std::fs::read(data.join(format!("{name}.mel.f32")))
            .ok()
            .map(|b| b.chunks_exact(4).map(|c| f32::from_le_bytes([c[0], c[1], c[2], c[3]])).collect());
        let mel_max_abs_diff = reference
            .map(|r| r.iter().zip(&mel).map(|(a, b)| (a - b).abs()).fold(0f32, f32::max));
        let features = StorageView::new(&[1, N_MELS, N_FRAMES], &mut mel, Device::CPU)?;
        let encoded = model.encode(&features, false)?;
        let detected = model.detect_language(&encoded)?;
        let best = detected[0].first().context("no language")?;
        let lang_token = best.language.clone();
        let prompt = vec![vec![
            "<|startoftranscript|>".to_string(),
            lang_token.clone(),
            "<|transcribe|>".to_string(),
            "<|notimestamps|>".to_string(),
        ]];
        let options = WhisperOptions {
            beam_size: 5,
            return_scores: true,
            return_no_speech_prob: true,
            suppress_tokens: suppress.clone(),
            ..Default::default()
        };
        let result = model.generate(&encoded, &prompt, &options)?.remove(0);
        let ids = result.sequences_ids[0].clone();
        let seq_len = ids.len() as f32;
        let avg_logprob = result.scores[0] * seq_len / (seq_len + 1.0); // length_penalty = 1
        let text_ids: Vec<u32> = ids.iter().filter(|&&t| t < eot).map(|&t| t as u32).collect();
        let text = tokenizer.decode(&text_ids, false).map_err(|e| anyhow!("{e}"))?;
        let kept = !(avg_logprob < -0.8 || result.no_speech_prob > 0.6);
        results.insert(name, json!({
            "language": lang_token.trim_start_matches("<|").trim_end_matches("|>"),
            "language_probability": best.probability,
            "segments": [{"text": text, "tokens": ids, "avg_logprob": avg_logprob, "no_speech_prob": result.no_speech_prob}],
            "text": if kept { text.clone() } else { String::new() },
            "mel_max_abs_diff": mel_max_abs_diff,
            "ms": started.elapsed().as_millis(),
        }));
    }
    Ok(json!({"load_ms": load_ms, "results": results}))
}

fn nllb(data: &Path, weights: &Path, device: Device) -> Result<Value> {
    let model_dir = weights.join("ctranslate2").join("nllb-200-distilled-600M-ct2-int8");
    let translator = Translator::new(&model_dir, &config(device))?;
    let tokenizer = Tokenizer::from_file(model_dir.join("tokenizer.json")).map_err(|e| anyhow!("{e}"))?;
    let reference: Value = serde_json::from_str(&std::fs::read_to_string(data.join("python.json"))?)?;
    let mut out = vec![];
    for case in reference["nllb"].as_array().context("nllb")? {
        let (src, tgt, text) = (case["source_language"].as_str().unwrap(), case["target_language"].as_str().unwrap(),
                                case["text"].as_str().unwrap());
        // NllbTokenizerFast (non-legacy): [src_lang] + tokens + [</s>]
        let enc = tokenizer.encode(text, false).map_err(|e| anyhow!("{e}"))?;
        let mut source = vec![src.to_string()];
        source.extend(enc.get_tokens().iter().cloned());
        source.push("</s>".to_string());
        let started = Instant::now();
        let result = translator.translate_batch_with_target_prefix(
            &[source.clone()], &[vec![tgt.to_string()]], &TranslationOptions::default(), None)?;
        let hypothesis = result[0].hypotheses[0].clone();
        let ids: Vec<u32> = hypothesis[1..].iter().filter_map(|t| tokenizer.token_to_id(t)).collect();
        let translation = tokenizer.decode(&ids, false).map_err(|e| anyhow!("{e}"))?;
        out.push(json!({"source_tokens": source, "target_tokens": hypothesis, "translation": translation,
                        "ms": started.elapsed().as_millis()}));
    }
    Ok(Value::Array(out))
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().collect();
    let data = PathBuf::from(args.get(1).context("data dir")?);
    let weights = PathBuf::from(args.get(2).context("weights dir")?);
    let device = match args.get(3).map(String::as_str) {
        Some("cuda") => Device::CUDA,
        _ => Device::CPU,
    };
    let report = json!({"device": format!("{device:?}"), "whisper": whisper(&data, &weights, device)?,
                        "nllb": nllb(&data, &weights, device)?});
    let name = if device == Device::CUDA { "rust-cuda.json" } else { "rust.json" };
    std::fs::write(data.join(name), serde_json::to_string_pretty(&report)?)?;
    println!("wrote {}", data.join(name).display());
    Ok(())
}
