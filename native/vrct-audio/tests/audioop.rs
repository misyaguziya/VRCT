//! PCM conversions against Python 3.11's audioop and PcmAudio / Pcm16MonoNormalizer
//! (native/testdata/audio/audioop.json, written by native/reference/export_audioop.py).
use serde_json::Value;
use vrct_audio::audioop::{self, Pcm16MonoNormalizer, RateState};

fn unbase64(s: &str) -> Vec<u8> {
    use base64::Engine;
    base64::engine::general_purpose::STANDARD.decode(s).unwrap()
}

/// Python's state: [d, [[prev, cur], ...]]
fn state(v: &Value) -> RateState {
    RateState {
        d: v[0].as_i64().unwrap() as i32,
        samples: v[1].as_array().unwrap().iter().map(|p| (p[0].as_i64().unwrap() as i32, p[1].as_i64().unwrap() as i32)).collect(),
    }
}

#[test]
fn matches_python() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../testdata/audio/audioop.json");
    let data: Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    let n = |v: &Value| v.as_u64().unwrap() as usize;
    let b = |v: &Value| unbase64(v.as_str().unwrap());
    let mut problems = vec![];
    for c in data["ratecv"].as_array().unwrap() {
        let (wa, wb) = c.get("weights").map_or((1, 0), |w| (w[0].as_u64().unwrap() as u32, w[1].as_u64().unwrap() as u32));
        let (out, st) = audioop::ratecv(&b(&c["input"]), n(&c["width"]), n(&c["channels"]), n(&c["inrate"]) as u32,
                                        n(&c["outrate"]) as u32, None, wa, wb).unwrap();
        if out != b(&c["output"]) || st != state(&c["state"]) {
            problems.push(format!("ratecv w{} c{} {}->{} weights {wa},{wb}", c["width"], c["channels"], c["inrate"], c["outrate"]));
        }
    }
    for c in data["ratecv_chunked"].as_array().unwrap() {
        let input = b(&c["input"]);
        let (mut pos, mut st) = (0, None);
        for (chunk, expected) in c["chunks"].as_array().unwrap().iter().zip(c["outputs"].as_array().unwrap()) {
            let end = (pos + n(chunk)).min(input.len());
            let (out, s) = audioop::ratecv(&input[pos..end], 2, 1, n(&c["inrate"]) as u32, 16000, st.as_ref(), 1, 0).unwrap();
            if out != b(expected) {
                problems.push(format!("ratecv chunked {} at {pos}", c["inrate"]));
                break;
            }
            st = Some(s);
            pos = end;
        }
        if st != Some(state(&c["state"])) {
            problems.push(format!("ratecv chunked {} final state", c["inrate"]));
        }
    }
    for c in data["lin2lin"].as_array().unwrap() {
        if audioop::lin2lin(&b(&c["input"]), n(&c["width"]), n(&c["newwidth"])) != b(&c["output"]) {
            problems.push(format!("lin2lin {} -> {}", c["width"], c["newwidth"]));
        }
    }
    for c in data["bias"].as_array().unwrap() {
        if audioop::bias(&b(&c["input"]), n(&c["width"]), c["bias"].as_i64().unwrap() as i32) != b(&c["output"]) {
            problems.push(format!("bias w{} {}", c["width"], c["bias"]));
        }
    }
    for c in data["tomono"].as_array().unwrap() {
        if audioop::tomono(&b(&c["input"]), n(&c["width"])) != b(&c["output"]) {
            problems.push(format!("tomono w{}", c["width"]));
        }
    }
    for c in data["pcm_audio"].as_array().unwrap() {
        let (rate, width) = (n(&c["rate"]) as u32, n(&c["width"]));
        let to_rate = c["convert_rate"].as_u64().map_or(rate, |r| r as u32);
        let to_width = c["convert_width"].as_u64().map_or(width, |w| w as usize);
        let raw = audioop::convert(&b(&c["input"]), rate, width, to_rate, to_width).unwrap();
        if raw != b(&c["raw"]) || audioop::wav(&raw, to_rate, to_width) != b(&c["wav"]) {
            problems.push(format!("pcm_audio w{width} {rate} -> {to_rate} w{to_width}"));
        }
    }
    for c in data["normalizer"].as_array().unwrap() {
        let mut normalizer = Pcm16MonoNormalizer::new(n(&c["rate"]) as u32, n(&c["width"]), n(&c["channels"]));
        let input = b(&c["input"]);
        let mut pos = 0;
        for (chunk, expected) in c["chunks"].as_array().unwrap().iter().zip(c["outputs"].as_array().unwrap()) {
            let end = (pos + n(chunk)).min(input.len());
            if normalizer.process(&input[pos..end]).unwrap() != b(expected) {
                problems.push(format!("normalizer {} w{} c{} at {pos}", c["rate"], c["width"], c["channels"]));
                break;
            }
            pos = end;
        }
    }
    for p in &problems {
        eprintln!("{p}");
    }
    assert!(problems.is_empty(), "{} problems", problems.len());
}
