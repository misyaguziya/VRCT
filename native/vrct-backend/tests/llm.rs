//! The LLM translation engines against the Python backend (native/testdata/llm/llm.json, written
//! by native/reference/export_llm.py): every step's result and the HTTP requests it sends must be
//! the same. Gemini's translation is gRPC in Python; its request object is compared with the REST
//! body, defaults removed on both sides (proto3 does not send them).
mod support;

use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use support::{compare_requests, Mock};
use vrct_backend::net::Http;
use vrct_backend::translate::llm::{Engine, HistoryItem, LlmClient};

fn native() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("..")
}

fn data() -> Value {
    serde_json::from_slice(&std::fs::read(native().join("testdata/llm/llm.json")).unwrap()).unwrap()
}

/// export_llm.responder
fn responder(data: Value) -> Box<support::Responder> {
    Box::new(move |entry: &Value| {
        let (url, method) = (entry["url"].as_str().unwrap(), entry["method"].as_str().unwrap());
        let auth = format!("{}{}", entry["headers"]["authorization"].as_str().unwrap_or(""),
                           entry["headers"]["x-goog-api-key"].as_str().unwrap_or(""));
        if auth.contains("invalid") {
            return (401, vec![], br#"{"error": {"message": "Incorrect API key provided", "code": 401}}"#.to_vec());
        }
        let j = |v: Value| (200, vec![], serde_json::to_vec(&v).unwrap());
        if url.contains(":generateContent") {
            return j(json!({"candidates": [{"content": {"role": "model", "parts": [{"text": data["reply"]}]},
                                            "finishReason": "STOP"}]}));
        }
        if url.contains("generativelanguage.googleapis.com") && url.contains("/models") {
            return j(data["gemini_pages"][if url.contains("pageToken=page2") { 1 } else { 0 }].clone());
        }
        if url.ends_with("/auth/key") {
            return j(json!({"data": {"label": "test"}}));
        }
        if url.ends_with("/chat/completions") {
            let model = entry["body"]["json"]["model"].clone();
            return j(json!({"id": "chatcmpl-1", "object": "chat.completion", "created": 0, "model": model,
                            "choices": [{"index": 0, "message": {"role": "assistant", "content": data["reply"]},
                                         "finish_reason": "stop"}],
                            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}));
        }
        if url.ends_with("/models") && method == "GET" {
            let models: Vec<Value> = data["openai_models"].as_array().unwrap().iter().map(|m| {
                let mut o = json!({"object": "model", "created": 0, "owned_by": "x"});
                o.as_object_mut().unwrap().extend(m.as_object().unwrap().clone());
                o
            }).collect();
            return j(json!({"object": "list", "data": models}));
        }
        if url.ends_with("/api/tags") {
            return j(json!({"models": data["ollama_models"]}));
        }
        if url.ends_with("/api/chat") {
            return j(json!({"model": entry["body"]["json"]["model"], "created_at": "2026-10-11T00:00:00Z",
                            "message": {"role": "assistant", "content": data["reply"]}, "done": true, "done_reason": "stop"}));
        }
        if url.trim_end_matches('/').ends_with(":11434") {
            return (200, vec![("content-type", "text/plain".into())], b"Ollama is running".to_vec());
        }
        (404, vec![], br#"{"error": "not found"}"#.to_vec())
    })
}

fn history(data: &Value) -> Vec<HistoryItem> {
    data["history"].as_array().unwrap().iter().map(|h| HistoryItem {
        source: h["source"].as_str().unwrap().into(),
        text: h["text"].as_str().unwrap().into(),
        timestamp: h.get("timestamp").and_then(Value::as_str).map(String::from),
    }).collect()
}

fn engine(name: &str) -> Engine {
    [Engine::OpenAi, Engine::Groq, Engine::OpenRouter, Engine::Plamo, Engine::OpenAiCompatible, Engine::LmStudio,
     Engine::Ollama, Engine::Gemini].into_iter().find(|e| e.key() == name).unwrap()
}

/// proto3 JSON without its default values (false, "", 0, [], {}) and without "model" (in the URL
/// for REST), so the gRPC request object and the REST body can be compared.
fn without_defaults(v: &Value) -> Option<Value> {
    match v {
        Value::Bool(false) | Value::Null => None,
        Value::String(s) if s.is_empty() => None,
        Value::Number(n) if n.as_f64() == Some(0.0) => None,
        Value::Array(a) => {
            let a: Vec<Value> = a.iter().filter_map(without_defaults).collect();
            (!a.is_empty()).then_some(Value::Array(a))
        }
        Value::Object(o) => {
            let o: serde_json::Map<_, _> = o.iter().filter(|(k, _)| *k != "model")
                .filter_map(|(k, v)| without_defaults(v).map(|v| (k.clone(), v))).collect();
            (!o.is_empty()).then_some(Value::Object(o))
        }
        v => Some(v.clone()),
    }
}

#[test]
fn llm_engines_match_python() {
    let data = data();
    let mock = Mock::start(responder(data.clone()));
    let settings = native().join("data/translation_settings");
    let text = "こんにちは、はじめまして";
    let mut problems = vec![];
    for e in data["engines"].as_array().unwrap() {
        let name = e["engine"].as_str().unwrap();
        let base = (name == "OpenAI_Compatible").then_some("http://127.0.0.1:8000/v1/");
        let mut c = LlmClient::new(engine(name), Http::redirected(&mock.root).unwrap(), &settings, base).unwrap();
        for step in e["steps"].as_array().unwrap() {
            let label = format!("{name} {}", step["step"].as_str().unwrap());
            let result: Value = match step["step"].as_str().unwrap() {
                "setAuthKey" => {
                    let key = match name {
                        "OpenAI_API" => format!("sk-{}", "a".repeat(161)),
                        "Groq_API" => format!("gsk_{}", "b".repeat(40)),
                        "OpenRouter_API" => format!("sk-or-{}", "c".repeat(20)),
                        "Plamo_API" => "d".repeat(72),
                        "OpenAI_Compatible" => "e".repeat(10),
                        _ => "f".repeat(39),
                    };
                    json!(c.set_auth_key(&key).unwrap())
                }
                "setAuthKey_invalid" => json!(c.set_auth_key("invalid-key").unwrap()),
                "getModelList" | "getModelList_again" | "getModelList_no_key" => json!(c.get_model_list().unwrap()),
                "setModel" => json!(c.set_model(step_model(name)).unwrap()),
                "updateClient" => Value::Null,
                "setBaseURL" => json!(c.set_base_url(Some("http://127.0.0.1:1234/v1"))),
                "authenticationCheck" => json!(c.authentication_check()),
                s @ ("translate_history" | "translate_no_history") => {
                    c.set_context_history(if s == "translate_history" { history(&data) } else { vec![] });
                    let input = if matches!(name, "LMStudio" | "Ollama") { "こんにちは" } else { text };
                    json!(c.translate(input, "Japanese", "English").unwrap())
                }
                other => panic!("unknown step {other}"),
            };
            if result != step["result"] {
                problems.push(format!("{label}: result {result} != {}", step["result"]));
            }
            let rust = mock.take();
            match step.get("grpc") {
                None => problems.extend(compare_requests(&label, step["requests"].as_array().unwrap(), &rust)),
                Some(grpc) => {
                    let request = &grpc[0]["request"];
                    let model = request["model"].as_str().unwrap();
                    let url = format!("https://generativelanguage.googleapis.com/v1beta/{model}:generateContent");
                    if rust.len() != 1 || rust[0]["url"] != url.as_str() {
                        problems.push(format!("{label}: {:?} != one request to {url}", rust.iter().map(|r| &r["url"]).collect::<Vec<_>>()));
                    } else if without_defaults(&rust[0]["body"]["json"]) != without_defaults(request) {
                        problems.push(format!("{label}: body {} != {}", rust[0]["body"]["json"], request));
                    }
                }
            }
        }
    }
    for p in problems.iter().take(30) {
        eprintln!("{p}");
    }
    assert!(problems.is_empty(), "{} problems", problems.len());
}

/// export_llm.py's setModel argument per engine
fn step_model(name: &str) -> &'static str {
    match name {
        "OpenAI_API" => "gpt-4o-mini",
        "Groq_API" => "Llama-3.3-70B-Versatile",
        "OpenRouter_API" | "LMStudio" => "gpt-4o",
        "Plamo_API" | "OpenAI_Compatible" => "o1-mini",
        "Ollama" => "gemma3:4b",
        _ => "gemini-2.5-flash",
    }
}
