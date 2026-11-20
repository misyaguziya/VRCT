//! Suppressed tokens and mel feature hashes (80 and 128 mels) are checked against the Python data in
//! testdata/whisper/. Transcription info and segments are checked against tests/transcribe-ct2-<ver>/.
//! Review the output diffs first, then rerun with VRCT_TEST_ACCEPT=1 to save the available models' baselines.
//!
//! VRCT_WEIGHTS_ROOTS: folders holding weights/whisper/<model> (';'-separated). Models not found are
//! skipped (and say so). VRCT_TEST_CUDA=1 also runs the *-cuda.json data.
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};
use vrct_whisper::mel::FeatureExtractor;
use vrct_whisper::{TranscribeOptions, WhisperModel};

// Must match third_party.toml. Re-accept the model outputs after a CT2 upgrade.
const CT2: &str = "ct2-4.9.0";

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

/// JSON equality with numbers compared as f64 (1 and 1.0 compare equal).
fn same(a: &Value, b: &Value) -> bool {
    match (a, b) {
        (Value::Number(x), Value::Number(y)) => x.as_f64() == y.as_f64(),
        (Value::Array(x), Value::Array(y)) => x.len() == y.len() && x.iter().zip(y).all(|(a, b)| same(a, b)),
        (Value::Object(x), Value::Object(y)) => x.len() == y.len() && x.iter().all(|(k, v)| y.get(k).is_some_and(|w| same(v, w))),
        _ => a == b,
    }
}

fn check_transcriptions(file: &Path, cases: Vec<Value>, problems: &mut Vec<String>) {
    let dir = Path::new(env!("CARGO_MANIFEST_DIR")).join(format!("tests/transcribe-{CT2}"));
    let path = dir.join(file.file_name().unwrap());
    // accepting always fails the run (never a silent pass) and writes nothing over other problems
    if std::env::var("VRCT_TEST_ACCEPT").is_ok_and(|v| v == "1") {
        if problems.is_empty() {
            std::fs::create_dir_all(dir).unwrap();
            let baseline = serde_json::to_string_pretty(&json!({ "cases": cases })).unwrap();
            std::fs::write(&path, format!("{baseline}\n")).unwrap();
            problems.push(format!("accepted {}; run again without VRCT_TEST_ACCEPT", path.display()));
        } else {
            problems.push(format!("not accepted {}: fix the problems above first", path.display()));
        }
        return;
    }
    if !path.try_exists().unwrap() {
        problems.push(format!("no {CT2} baseline for {}; run with VRCT_TEST_ACCEPT=1 after checking the outputs", file.display()));
        return;
    }
    let baseline: Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    let expected = baseline["cases"].as_array().unwrap();
    if cases.len() != expected.len() {
        problems.push(format!("{}: case count {} != {}", file.display(), cases.len(), expected.len()));
    }
    for (i, (got, want)) in cases.iter().zip(expected).enumerate() {
        if got["files"] != want["files"] || got["force_language"] != want["force_language"] {
            problems.push(format!("{}: case {i} files or force_language differ from the {CT2} baseline", file.display()));
            continue;
        }
        let name = format!("{} force={}", got["files"], got["force_language"]);
        for field in ["info", "segments"] {
            if !same(&got[field], &want[field]) {
                problems.push(format!("{name}: {field} {} != {}", got[field], want[field]));
            }
        }
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
    let mut cases = Vec::new();
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
        let (segments, info) = model.transcribe(&audio, &options).unwrap();
        let got_info = json!({"language": info.language, "language_probability": info.language_probability as f64,
                              "duration": info.duration});
        // VRCT's own values stay checked against Python: the duration, and the info of a forced language
        let python_info = if options.language.is_some() { got_info.clone() } else { json!({"duration": info.duration}) };
        if python_info.as_object().unwrap().iter().any(|(k, v)| !same(v, &case["info"][k])) {
            problems.push(format!("{files:?}: info {got_info} != {} (Python)", case["info"]));
        }
        let got: Vec<Value> = segments
            .iter()
            .map(|s| json!({"id": s.id, "seek": s.seek, "start": s.start, "end": s.end, "text": s.text,
                            "tokens": s.tokens, "avg_logprob": s.avg_logprob, "no_speech_prob": s.no_speech_prob as f64}))
            .collect();
        cases.push(json!({ "files": files, "force_language": case["force_language"], "info": got_info, "segments": got }));
    }
    check_transcriptions(file, cases, &mut problems);
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
