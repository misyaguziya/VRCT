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
use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use std::time::Instant;
use tokenizers::Tokenizer;

mod mel;
use mel::{log_mel, matmul_fma, window, N_FRAMES, N_MELS};

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
        // POC_COMPUTE=f32 isolates the int8 GEMM from the rest of the computation
        compute_type: if std::env::var("POC_COMPUTE").is_ok_and(|v| v == "f32") { ComputeType::FLOAT32 } else { ComputeType::INT8 },
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
        let (full, frames) = log_mel(&read_wav(&wav)?, &matmul_fma);
        let mut mel = window(&full, frames, 0, frames - 1);
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
        let debug = std::env::var("POC_ONLY").is_ok();
        let options = if debug {
            TranslationOptions { num_hypotheses: 2, return_scores: true, ..Default::default() }
        } else {
            TranslationOptions::default()
        };
        let result = translator.translate_batch_with_target_prefix(
            &[source.clone()], &[vec![tgt.to_string()]], &options, None)?;
        if debug {
            for (h, s) in result[0].hypotheses.iter().zip(&result[0].scores) {
                println!("  {s:.5} {}", h[1..h.len().min(4)].join(" "));
            }
        }
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
    // POC_ONLY=nllb skips Whisper (to check that running it first does not change NLLB)
    let only_nllb = std::env::var("POC_ONLY").is_ok_and(|v| v == "nllb");
    let whisper = if only_nllb { Value::Null } else { whisper(&data, &weights, device)? };
    let report = json!({"device": format!("{device:?}"), "whisper": whisper, "nllb": nllb(&data, &weights, device)?});
    let name = if device == Device::CUDA { "rust-cuda.json" } else { "rust.json" };
    std::fs::write(data.join(name), serde_json::to_string_pretty(&report)?)?;
    println!("wrote {}", data.join(name).display());
    Ok(())
}
