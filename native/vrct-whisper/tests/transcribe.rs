//! transcribe against the Python backend (native/testdata/whisper/*.json, written by
//! native/reference/export_whisper.py): suppressed tokens, mel features (80 and 128 mels), language
//! detection and every segment field must be identical.
//!
//! VRCT_WEIGHTS_ROOTS: folders holding weights/whisper/<model> (';'-separated). Models not found are
//! skipped (and say so). VRCT_TEST_CUDA=1 also runs the *-cuda.json data.
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};
use vrct_whisper::mel::FeatureExtractor;
use vrct_whisper::{TranscribeOptions, WhisperModel};

fn testdata() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../testdata/whisper")
}

fn weights_dir(weight_type: &str) -> Option<PathBuf> {
    std::env::var("VRCT_WEIGHTS_ROOTS")
        .ok()?
        .split(';')
        .map(|root| Path::new(root).join("weights/whisper").join(weight_type))
        .find(|dir| dir.join("model.bin").is_file())
}

/// int16 samples / 32768 in float32, as LocalWhisperProvider converts them
fn read_wav(name: &str) -> Vec<f32> {
    let mut reader = hound::WavReader::open(testdata().join("audio").join(format!("{name}.wav"))).unwrap();
    let spec = reader.spec();
    assert_eq!((spec.sample_rate, spec.channels, spec.bits_per_sample), (16000, 1, 16));
    reader.samples::<i16>().map(|s| s.unwrap() as f32 / 32768.0).collect()
}

fn sha256(v: &[f32]) -> String {
    let bytes: Vec<u8> = v.iter().flat_map(|x| x.to_le_bytes()).collect();
    Sha256::digest(&bytes).iter().map(|b| format!("{b:02x}")).collect()
}

/// JSON equality with numbers compared as f64 (Python writes 1 for a float 1.0)
fn same(a: &Value, b: &Value) -> bool {
    match (a, b) {
        (Value::Number(x), Value::Number(y)) => x.as_f64() == y.as_f64(),
        (Value::Array(x), Value::Array(y)) => x.len() == y.len() && x.iter().zip(y).all(|(a, b)| same(a, b)),
        (Value::Object(x), Value::Object(y)) => x.len() == y.len() && x.iter().all(|(k, v)| y.get(k).is_some_and(|w| same(v, w))),
        _ => a == b,
    }
}

fn check(file: &Path) -> Vec<String> {
    let data: Value = serde_json::from_slice(&std::fs::read(file).unwrap()).unwrap();
    let weight_type = data["weight_type"].as_str().unwrap();
    let Some(dir) = weights_dir(weight_type) else {
        eprintln!("SKIPPED {}: no weights for {weight_type} in VRCT_WEIGHTS_ROOTS", file.display());
        return vec![];
    };
    let model = WhisperModel::new(&dir, data["device"].as_str().unwrap(), 0, data["compute_type"].as_str().unwrap()).unwrap();
    let mut problems = vec![];
    let expected: Vec<i32> = data["suppress_tokens"].as_array().unwrap().iter().map(|v| v.as_i64().unwrap() as i32).collect();
    if model.suppress_tokens() != expected {
        problems.push(format!("suppress_tokens {:?} != {expected:?}", model.suppress_tokens()));
    }
    // both sizes whatever the model uses (large-v3 and its turbo take 128)
    let (mel80, mel128) = (FeatureExtractor::new(80), FeatureExtractor::new(128));
    for (clip, hashes) in data["features_sha256"].as_object().unwrap() {
        let audio = read_wav(clip);
        for (n, got) in [("80", sha256(&mel80.compute(&audio).unwrap().data)), ("128", sha256(&mel128.compute(&audio).unwrap().data))] {
            if got != hashes[n].as_str().unwrap() {
                problems.push(format!("features {clip} {n} mels differ"));
            }
        }
    }
    for case in data["cases"].as_array().unwrap() {
        let files: Vec<&str> = case["files"].as_array().unwrap().iter().map(|f| f.as_str().unwrap()).collect();
        let audio: Vec<f32> = files.iter().flat_map(|f| read_wav(f)).collect();
        let language = case["language"].as_str().unwrap();
        let options = TranscribeOptions {
            language: case["force_language"].as_bool().unwrap().then(|| language.to_string()),
            log_prob_threshold: case["avg_logprob"].as_f64(),
            no_speech_threshold: case["no_speech_prob"].as_f64(),
            no_repeat_ngram_size: case["no_repeat_ngram_size"].as_u64().unwrap() as usize,
            without_timestamps: true,
            ..TranscribeOptions::default()
        };
        let name = format!("{}{} force={}", files[0], if files.len() > 1 { "+" } else { "" }, options.language.is_some());
        let (segments, info) = model.transcribe(&audio, &options).unwrap();
        let got_info = serde_json::json!({"language": info.language, "language_probability": info.language_probability as f64,
                                          "duration": info.duration});
        if !same(&got_info, &case["info"]) {
            problems.push(format!("{name}: info {got_info} != {}", case["info"]));
        }
        let got: Vec<Value> = segments
            .iter()
            .map(|s| serde_json::json!({"id": s.id, "seek": s.seek, "start": s.start, "end": s.end, "text": s.text,
                                       "tokens": s.tokens, "avg_logprob": s.avg_logprob, "no_speech_prob": s.no_speech_prob as f64}))
            .collect();
        if !same(&Value::Array(got.clone()), &case["segments"]) {
            problems.push(format!("{name}: segments {got:?} != {}", case["segments"]));
        }
    }
    eprintln!("{}: {} cases, {} clips, problems {}", file.display(), data["cases"].as_array().unwrap().len(),
              data["features_sha256"].as_object().unwrap().len(), problems.len());
    problems
}

#[test]
fn transcribe_matches_python() {
    let cuda = std::env::var("VRCT_TEST_CUDA").is_ok_and(|v| v == "1");
    let mut files: Vec<PathBuf> = std::fs::read_dir(testdata())
        .unwrap()
        .map(|e| e.unwrap().path())
        .filter(|p| p.extension().is_some_and(|e| e == "json"))
        .collect();
    files.sort();
    let mut problems = vec![];
    for file in files.iter().filter(|f| cuda || f.to_string_lossy().ends_with("-cpu.json")) {
        problems.extend(check(file));
    }
    for p in problems.iter().take(20) {
        eprintln!("{p}");
    }
    assert!(problems.is_empty(), "{} problems", problems.len());
}
