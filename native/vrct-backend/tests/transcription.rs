//! Speech recognition APIs against the Python backend (native/testdata/transcription, written by
//! native/reference/export_transcription.py): results, error codes and requests. The audio bodies
//! (FLAC / WAV) are taken from the Python requests (their encoding is compared in P3).
mod support;

use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use support::{compare_requests, Mock};

fn unbase64(s: &str) -> Vec<u8> {
    use base64::Engine;
    base64::engine::general_purpose::STANDARD.decode(s).unwrap()
}
use vrct_backend::asr::{self, Deepgram, Languages, WhisperApi};
use vrct_backend::net::Http;

fn native() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("..")
}

/// export_transcription.responder
fn responder() -> Box<support::Responder> {
    let google_reply = "{\"result\":[]}\n{\"result\":[{\"alternative\":[{\"transcript\":\"こんにちは\",\"confidence\":0.75},{\"transcript\":\"今日は\"}],\"final\":true}],\"result_index\":0}\n{\"result\":[{\"alternative\":[{\"transcript\":\"いい天気\"}],\"final\":true}]}\n";
    let whisper_reply = json!({"task": "transcribe", "language": "ja", "duration": 2.5, "text": " こんにちは。いい天気",
        "segments": [
            {"id": 0, "start": 0.0, "end": 1.0, "text": " こんにちは。", "avg_logprob": -0.25, "no_speech_prob": 0.01},
            {"id": 1, "start": 1.0, "end": 2.0, "text": " ノイズ", "avg_logprob": -1.5, "no_speech_prob": 0.1},
            {"id": 2, "start": 2.0, "end": 2.5, "text": "いい天気", "avg_logprob": -0.5, "no_speech_prob": 0.2}]});
    let models = ["whisper-large-v3", "Whisper-Large-V3-Turbo", "gpt-4o-transcribe", "gpt-4o", "distil-whisper-large-v3-en", "llama-3.3-70b"];
    let deepgram_models = json!({"stt": [
        {"name": "nova-3", "batch": true, "streaming": true, "languages": ["en", "en-US", "ja", "multi"]},
        {"name": "nova-2", "batch": true, "languages": ["en", "en-AU", "en-GB", "ja", "zh-CN"]},
        {"name": "nova-3", "batch": true, "languages": ["dup"]},
        {"name": "live-only", "batch": false, "languages": ["en"]},
        {"name": "", "batch": true}, {"batch": true}, {"name": "base", "batch": true}], "tts": [{"name": "aura"}]});
    Box::new(move |entry: &Value| {
        let url = entry["url"].as_str().unwrap();
        let auth = entry["headers"]["authorization"].as_str().unwrap_or("");
        let j = |status, v: &Value| (status, vec![], serde_json::to_vec(v).unwrap());
        let text = |status, t: &str| (status, vec![("content-type", "text/plain".to_string())], t.as_bytes().to_vec());
        if auth.contains("invalid") {
            return j(401, &json!({"error": {"message": "invalid key"}}));
        }
        if auth.contains("limited") {
            return (429, vec![("retry-after", "0.01".into())], br#"{"error": {"message": "rate limited"}}"#.to_vec());
        }
        if auth.contains("broken") {
            return j(500, &json!({"error": "server"}));
        }
        if url.contains("speech-api/v2/recognize") {
            if url.contains("lang=xx-XX") {
                return j(500, &json!("error"));
            }
            if url.contains("lang=zz-ZZ") {
                return text(200, r#"{"result":[{"alternative":[{"transcript":1}]}]}"#);
            }
            return text(200, google_reply);
        }
        if url.ends_with("/audio/transcriptions") {
            if auth.contains("no-segments") {
                return j(200, &json!({"text": " セグメントなし", "language": "japanese"}));
            }
            return j(200, &whisper_reply);
        }
        if url.ends_with("/models") && url.contains("deepgram") {
            return j(200, &deepgram_models);
        }
        if url.ends_with("/models") {
            let data: Vec<Value> = models.iter().map(|m| json!({"object": "model", "created": 0, "owned_by": "x", "id": m})).collect();
            return j(200, &json!({"object": "list", "data": data}));
        }
        if url.contains("api.deepgram.com/v1/listen") {
            if auth.contains("empty") {
                return j(200, &json!({"results": {"channels": [{"alternatives": [{"transcript": ""}]}]}}));
            }
            return j(200, &json!({"metadata": {}, "results": {"channels": [{"alternatives": [
                {"transcript": "こんにちは", "confidence": 0.91, "words": []}]}]}}));
        }
        j(404, &json!({"error": "not found"}))
    })
}

fn triple(r: Result<(String, f64, bool), asr::ApiError>) -> Value {
    match r {
        Ok((t, c, d)) => json!([t, c, d]),
        Err(e) => json!({"error": e.0}),
    }
}

#[test]
fn transcription_apis_match_python() {
    let data: Value =
        serde_json::from_slice(&std::fs::read(native().join("testdata/transcription/transcription.json")).unwrap()).unwrap();
    let languages = Languages::load(&native().join("data/transcription_languages.json")).unwrap();
    let mock = Mock::start(responder());
    let http = Http::redirected(&mock.root).unwrap();
    let mut problems = vec![];
    for step in data["steps"].as_array().unwrap() {
        let (kind, args) = (step["kind"].as_str().unwrap(), &step["args"]);
        let label = format!("{kind} {}", step["label"].as_str().unwrap());
        let python = step["requests"].as_array().unwrap();
        let s = |k: &str| args[k].as_str().unwrap_or("").to_string();
        let audio = || -> Vec<u8> {
            let body = &python[0]["body"];
            match body.get("multipart") {
                Some(parts) => unbase64(parts.as_array().unwrap().iter().find(|p| p["name"] == "file").unwrap()["base64"].as_str().unwrap()),
                None => unbase64(body["base64"].as_str().unwrap()),
            }
        };
        let result = match kind {
            "google" => {
                let rate: u32 = python[0]["headers"]["content-type"].as_str().unwrap().rsplit('=').next().unwrap().parse().unwrap();
                match asr::google_recognize(&http, &audio(), rate, &s("language")) {
                    Ok((t, c)) => json!([t, c]),
                    Err(_) => json!({"error": "GoogleRequestError"}),
                }
            }
            "whisper_api" => {
                let api = WhisperApi { http: http.clone(), api_key: s("key"), base_url: s("base_url"), model: s("model"), engine_name: s("engine") };
                triple(api.transcribe(&languages, &audio(), "Japanese", "Japan", -0.8, 0.6, args["force_language"].as_bool().unwrap()))
            }
            "whisper_api_check" => json!(asr::check_whisper_api_key(&http, &s("key"), &s("base_url"))),
            "whisper_api_models" => {
                let keywords = args["keywords"].as_array().map(|k| k.iter().map(|x| x.as_str().unwrap()).collect::<Vec<_>>());
                json!(asr::whisper_api_models(&http, &s("key"), &s("base_url"), keywords.as_deref()).unwrap())
            }
            "deepgram" => {
                let langs = args["languages"].as_array().unwrap().iter().map(|x| x.as_str().unwrap().to_string()).collect();
                let d = Deepgram { http: http.clone(), api_key: s("key"), model: s("model"), model_languages: langs };
                triple(d.transcribe(&languages, &audio(), &s("language"), &s("country"), args["force_language"].as_bool().unwrap()))
            }
            "deepgram_check" => json!(asr::check_deepgram_key(&http, &s("key"))),
            "deepgram_models" => json!(asr::deepgram_models(&http, &s("key")).into_iter()
                .map(|(name, langs)| json!({"name": name, "languages": langs})).collect::<Vec<_>>()),
            other => panic!("unknown kind {other}"),
        };
        if result != step["result"] {
            problems.push(format!("{label}: result {result} != {}", step["result"]));
        }
        problems.extend(compare_requests(&label, python, &mock.take()));
    }
    for case in data["resolve_deepgram"].as_array().unwrap() {
        let langs: Vec<String> = case["model_languages"].as_array().unwrap().iter().map(|x| x.as_str().unwrap().to_string()).collect();
        let got = asr::resolve_deepgram_language(&languages, case["language"].as_str().unwrap(), case["country"].as_str().unwrap(), &langs);
        if json!(got) != case["result"] {
            problems.push(format!("resolve {case}: {got:?}"));
        }
    }
    eprintln!("{} steps, {} resolve cases, problems {}", data["steps"].as_array().unwrap().len(),
              data["resolve_deepgram"].as_array().unwrap().len(), problems.len());
    for p in problems.iter().take(30) {
        eprintln!("{p}");
    }
    assert!(problems.is_empty(), "{} problems", problems.len());
}
