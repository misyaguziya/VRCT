//! Silero VAD and the speech segments against the Python backend (native/testdata/audio/vad.json,
//! written by native/reference/export_vad.py): every frame's probability and every segment.
//! The model is faster-whisper's: VRCT_SILERO_ASSETS, or the repository's .venv.
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use vrct_audio::audioop;
use vrct_audio::vad::{FrameProbability, VadRecognizer, VadSegmenter};
use vrct_ocr::silero::SileroVad;

fn native() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("..")
}

/// The samples of a PCM16 WAV file (the "data" chunk)
fn wav_data(path: &Path) -> Vec<u8> {
    let bytes = std::fs::read(path).unwrap();
    let mut pos = 12;
    while pos + 8 <= bytes.len() {
        let size = u32::from_le_bytes(bytes[pos + 4..pos + 8].try_into().unwrap()) as usize;
        if &bytes[pos..pos + 4] == b"data" {
            return bytes[pos + 8..pos + 8 + size].to_vec();
        }
        pos += 8 + size + size % 2;
    }
    panic!("no data chunk in {}", path.display());
}

struct Recording {
    vad: SileroVad,
    probs: Arc<Mutex<Vec<f32>>>,
}

impl FrameProbability for Recording {
    fn probability(&mut self, frame: &[f32]) -> Result<f32, String> {
        let p = self.vad.probability(frame).map_err(|e| e.to_string())?;
        self.probs.lock().unwrap().push(p);
        Ok(p)
    }

    fn reset(&mut self) {
        self.vad.reset()
    }
}

#[test]
fn vad_matches_python() {
    let assets = std::env::var_os("VRCT_SILERO_ASSETS").map(PathBuf::from)
        .unwrap_or_else(|| native().join("../.venv/Lib/site-packages/faster_whisper/assets"));
    if !assets.join("silero_encoder_v5.onnx").exists() {
        eprintln!("SKIPPED: no Silero model in {}", assets.display());
        return;
    }
    let data: Value = serde_json::from_slice(&std::fs::read(native().join("testdata/audio/vad.json")).unwrap()).unwrap();
    let step = data["chunk_frames"].as_u64().unwrap() as usize * 4;
    let mut problems = vec![];
    for run in data["runs"].as_array().unwrap() {
        let label = format!("{} max {}", run["stream"], run["max_speech_frames"]);
        let mono: Vec<u8> = run["clips"].as_array().unwrap().iter()
            .flat_map(|c| wav_data(&native().join(format!("testdata/whisper/audio/{}.wav", c.as_str().unwrap()))))
            .collect();
        let up = audioop::ratecv(&mono, 2, 1, 16000, 48000, None, 1, 0).unwrap().0;
        let stereo: Vec<u8> = up.chunks_exact(2).flat_map(|s| [s[0], s[1], s[0], s[1]]).collect();
        let probs = Arc::new(Mutex::new(vec![]));
        let silero = Recording { vad: SileroVad::new(&assets).unwrap(), probs: probs.clone() };
        let max = run["max_speech_frames"].as_u64().map(|m| m as usize);
        let mut vad = VadRecognizer::new(48000, 2, 2, VadSegmenter::new(silero, max));
        let mut segments = vec![];
        let mut record = |segment: vrct_audio::vad::SpeechSegment, chunk: i64| {
            segments.push(json!({"chunk": chunk, "bytes": segment.audio.len(), "reason": segment.reason.as_str(),
                "id": segment.segment_id,
                "sha256": Sha256::digest(&segment.audio).iter().map(|b| format!("{b:02x}")).collect::<String>()}));
        };
        for (i, chunk) in stereo.chunks(step).enumerate() {
            for segment in vad.process(chunk).unwrap() {
                record(segment, i as i64);
            }
        }
        if let Some(segment) = vad.flush().unwrap() {
            record(segment, -1);
        }
        let got: Vec<f64> = probs.lock().unwrap().iter().map(|&p| p as f64).collect();
        let expected: Vec<f64> = run["probs"].as_array().unwrap().iter().map(|p| p.as_f64().unwrap()).collect();
        if got != expected {
            let at = got.iter().zip(&expected).position(|(a, b)| a != b);
            problems.push(format!("{label}: probabilities differ ({} vs {} frames, first at {at:?})", got.len(), expected.len()));
        }
        // segment ids relative to the segmenter's first one (the counter is per process)
        let base = segments.first().map_or(0, |s| s["id"].as_u64().unwrap()) as i64
            - run["segments"].get(0).map_or(0, |s| s["id"].as_i64().unwrap());
        for s in &mut segments {
            s["id"] = json!(s["id"].as_i64().unwrap() - base);
        }
        if json!(segments) != run["segments"] {
            problems.push(format!("{label}: segments {} != {}", json!(segments), run["segments"]));
        }
    }
    for p in &problems {
        eprintln!("{}", p.chars().take(600).collect::<String>());
    }
    assert!(problems.is_empty(), "{} problems", problems.len());
}
