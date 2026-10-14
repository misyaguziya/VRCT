//! Speech recognition over the network (models/transcription): the legacy Google web recognizer
//! (google_speech.py), OpenAI-compatible transcription APIs (Groq / OpenAI / custom) and Deepgram
//! (transcription_providers.py, transcription_openai_compatible.py, transcription_deepgram.py).
//! They take the audio already encoded (FLAC / 16 kHz WAV, made by vrct-audio as PcmAudio does).
use crate::net::{Body, Http};
use crate::openai;
use anyhow::{bail, Context, Result};
use reqwest::blocking::multipart::{Form, Part};
use reqwest::Method;
use serde_json::{json, Value};
use std::path::Path;
use std::time::Duration;

/// transcription_lang (native/data/transcription_languages.json): language -> country -> engine -> code
pub struct Languages(Value);

impl Languages {
    pub fn load(path: &Path) -> Result<Self> {
        Ok(Self(serde_json::from_slice(&std::fs::read(path)?)?))
    }

    pub fn new(table: Value) -> Self {
        Self(table)
    }

    /// The whole table (language -> country -> engine -> code), in its order
    pub fn table(&self) -> &Value {
        &self.0
    }

    pub fn code(&self, language: &str, country: &str, engine: &str) -> Option<&str> {
        self.0.get(language)?.get(country)?.get(engine)?.as_str()
    }

    fn entry(&self, language: &str, country: &str) -> Option<&Value> {
        self.0.get(language)?.get(country)
    }
}

/// A failed API transcription with the ErrorCode the Python provider raises
#[derive(Debug, PartialEq, Eq)]
pub struct ApiError(pub &'static str);

impl std::fmt::Display for ApiError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.0)
    }
}

impl std::error::Error for ApiError {}

pub const AUTH_FAILED: ApiError = ApiError("TRANSCRIPTION_API_AUTH_FAILED");
pub const RATE_LIMITED: ApiError = ApiError("TRANSCRIPTION_API_RATE_LIMITED");
pub const TIMEOUT: ApiError = ApiError("TRANSCRIPTION_API_TIMEOUT");
pub const SERVER_ERROR: ApiError = ApiError("TRANSCRIPTION_API_SERVER_ERROR");

/// transcription_providers._HTTP_TIMEOUT (connect 10 s, read 60 s)
const HTTP_TIMEOUT: Duration = Duration::from_secs(60);

// ---- Google (legacy web recognizer) ----------------------------------------------------------

/// The key every SpeechRecognition-derived client uses
const GOOGLE_LEGACY_KEY: &str = "AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw";

/// GoogleSpeechClient.recognize after the FLAC encoding: (joined transcripts, mean confidence).
/// Any transport, HTTP or format failure is an error (GoogleRequestError).
pub fn google_recognize(http: &Http, flac: &[u8], rate: u32, language: &str) -> Result<(String, f64)> {
    let query = form_urlencode(&[("client", "chromium"), ("lang", language), ("key", GOOGLE_LEGACY_KEY), ("pFilter", "0")]);
    let url = format!("http://www.google.com/speech-api/v2/recognize?{query}");
    let headers = [("content-type", format!("audio/x-flac; rate={rate}"))];
    let response = http
        .send(Method::POST, &url, &headers, Some(Body::Bytes(flac.to_vec())), Some(Duration::from_secs(10)))
        .context("Google recognition request failed")?;
    if !response.status().is_success() {
        bail!("Google recognition request failed: HTTP {}", response.status());
    }
    parse_google_response(&response.text()?)
}

/// urllib.parse.urlencode (quote_plus)
fn form_urlencode(pairs: &[(&str, &str)]) -> String {
    let enc = |s: &str| -> String {
        s.bytes()
            .map(|b| match b {
                b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'_' | b'.' | b'-' | b'~' => (b as char).to_string(),
                b' ' => "+".to_string(),
                b => format!("%{b:02X}"),
            })
            .collect()
    };
    pairs.iter().map(|(k, v)| format!("{}={}", enc(k), enc(v))).collect::<Vec<_>>().join("&")
}

/// google_speech.parse_google_response
pub fn parse_google_response(text: &str) -> Result<(String, f64)> {
    let malformed = || anyhow::anyhow!("Malformed Google recognition response");
    let (mut transcripts, mut confidences) = (vec![], vec![]);
    for line in text.lines().filter(|l| !crate::pyfmt::strip(l).is_empty()) {
        let v: Value = serde_json::from_str(line).map_err(|_| malformed())?;
        let results = v.get("result").ok_or_else(malformed)?.as_array().ok_or_else(malformed)?;
        let Some(candidate) = results.first() else { continue };
        let candidate = candidate.as_object().ok_or_else(malformed)?;
        let alternatives = match candidate.get("alternative") {
            None => continue,
            Some(a) => a.as_array().ok_or_else(malformed)?,
        };
        let Some(best) = alternatives.first() else { continue };
        let best = best.as_object().ok_or_else(malformed)?;
        let Some(transcript) = best.get("transcript") else { continue };
        let transcript = transcript.as_str().ok_or_else(malformed)?;
        // type(confidence) in (int, float): JSON booleans are not numbers here
        let confidence = match best.get("confidence") {
            None => 0.5,
            Some(c) => c.as_f64().filter(|_| c.is_number()).ok_or_else(malformed)?,
        };
        if !confidence.is_finite() || !(0.0..=1.0).contains(&confidence) {
            return Err(malformed());
        }
        transcripts.push(transcript.to_string());
        confidences.push(confidence);
    }
    if transcripts.is_empty() {
        return Ok((String::new(), 0.0));
    }
    let sum: f64 = confidences.iter().sum();
    Ok((transcripts.join(" "), sum / confidences.len() as f64))
}

// ---- OpenAI-compatible transcription (Groq / OpenAI / custom) ------------------------------

fn map_openai(e: openai::Error) -> ApiError {
    match e {
        openai::Error::Status(401, _) => AUTH_FAILED,
        openai::Error::Status(429, _) => RATE_LIMITED,
        openai::Error::Timeout => TIMEOUT,
        _ => SERVER_ERROR,
    }
}

/// OpenAICompatibleTranscriptionProvider
pub struct WhisperApi {
    pub http: Http,
    pub api_key: String,
    pub base_url: String,
    pub model: String,
    /// "Groq_Whisper" / "OpenAI_Whisper" / "Custom_Whisper": the column of transcription_lang
    pub engine_name: String,
}

impl WhisperApi {
    /// transcribe(audio, language, country, avg_logprob, no_speech_prob, force_language):
    /// (text, confidence, is_definitive). `wav` is the 16 kHz / 16 bit WAV.
    // the parameters of the Python method
    #[allow(clippy::too_many_arguments)]
    pub fn transcribe(&self, languages: &Languages, wav: &[u8], language: &str, country: &str, avg_logprob: f64,
                      no_speech_prob: f64, force_language: bool) -> Result<(String, f64, bool), ApiError> {
        // ponytail: Python raises KeyError here (outside its try) for a language missing from the
        // table; VRCT only offers languages that are in it
        let source_language = if force_language {
            Some(languages.code(language, country, &self.engine_name).ok_or(SERVER_ERROR)?.to_string())
        } else {
            None
        };
        let base = if self.base_url.is_empty() { openai::DEFAULT_BASE_URL } else { &self.base_url };
        let headers = [("accept", "application/json".to_string()), ("authorization", format!("Bearer {}", self.api_key))];
        let form = || {
            let mut form = Form::new().text("model", self.model.clone());
            if let Some(l) = &source_language {
                form = form.text("language", l.clone());
            }
            let file = Part::bytes(wav.to_vec()).file_name("audio.wav").mime_str("audio/wav").unwrap();
            Some(Body::Multipart(form.text("response_format", "verbose_json").text("temperature", "0.0").part("file", file)))
        };
        let response = openai::send(&self.http, Method::POST, &openai::url(base, "audio/transcriptions"), &headers, &form,
                                    HTTP_TIMEOUT)
            .map_err(map_openai)?;
        let segments = response.get("segments").and_then(Value::as_array).cloned().unwrap_or_default();
        let mut accepted: Vec<f64> = vec![];
        let mut text = String::new();
        if !segments.is_empty() {
            for s in &segments {
                let avg = s.get("avg_logprob").and_then(Value::as_f64).unwrap_or(0.0);
                let nsp = s.get("no_speech_prob").and_then(Value::as_f64).unwrap_or(0.0);
                if avg < avg_logprob || nsp > no_speech_prob {
                    continue;
                }
                text += s.get("text").and_then(Value::as_str).unwrap_or("");
                accepted.push(avg);
            }
        } else {
            text = response.get("text").and_then(Value::as_str).unwrap_or("").to_string();
        }
        if text.is_empty() {
            return Ok((String::new(), 0.0, false));
        }
        let confidence = if accepted.is_empty() {
            0.5
        } else {
            (accepted.iter().sum::<f64>() / accepted.len() as f64).exp()
        };
        let detected = response.get("language").and_then(Value::as_str);
        let is_definitive = force_language
            || detected.is_some_and(|d| languages.code(language, country, &self.engine_name) == Some(d));
        Ok((text, confidence, is_definitive))
    }
}

/// checkTranscriptionApiKey: the model list can be fetched
pub fn check_whisper_api_key(http: &Http, api_key: &str, base_url: &str) -> bool {
    let base = if base_url.is_empty() { openai::DEFAULT_BASE_URL } else { base_url };
    openai::list_models(http, base, api_key, openai::DEFAULT_TIMEOUT).is_ok()
}

/// getAvailableTranscriptionModels(api_key, base_url, keyword_filter)
pub fn whisper_api_models(http: &Http, api_key: &str, base_url: &str, keywords: Option<&[&str]>) -> Result<Vec<String>> {
    let base = if base_url.is_empty() { openai::DEFAULT_BASE_URL } else { base_url };
    let models = openai::list_models(http, base, api_key, openai::DEFAULT_TIMEOUT)?;
    let mut ids: Vec<String> = models.iter().map(|m| m.get("id").and_then(Value::as_str).unwrap_or("").to_string()).collect();
    if let Some(keywords) = keywords.filter(|k| !k.is_empty()) {
        ids.retain(|m| keywords.iter().any(|kw| m.to_lowercase().contains(kw)));
    }
    ids.sort();
    Ok(ids)
}

/// transcription_openai_compatible.TRANSCRIPTION_MODEL_KEYWORDS
pub const TRANSCRIPTION_MODEL_KEYWORDS: [&str; 2] = ["whisper", "transcribe"];

// ---- Deepgram -----------------------------------------------------------------------------

const DEEPGRAM_BASE_URL: &str = "https://api.deepgram.com/v1";

/// DeepgramProvider
pub struct Deepgram {
    pub http: Http,
    pub api_key: String,
    pub model: String,
    pub model_languages: Vec<String>,
}

impl Deepgram {
    /// transcribe(...): (text, confidence, True); the language is given when it resolves for the
    /// model (force_language), otherwise detected.
    pub fn transcribe(&self, languages: &Languages, wav: &[u8], language: &str, country: &str,
                      force_language: bool) -> Result<(String, f64, bool), ApiError> {
        let resolved = if force_language { resolve_deepgram_language(languages, language, country, &self.model_languages) } else { None };
        let mut params = vec![("model", self.model.as_str())];
        match &resolved {
            Some(code) => params.push(("language", code)),
            None => params.push(("detect_language", "true")),
        }
        let url = format!("{DEEPGRAM_BASE_URL}/listen?{}", form_urlencode(&params));
        let headers = [("authorization", format!("Token {}", self.api_key)), ("content-type", "audio/wav".to_string())];
        let response = match self.http.send(Method::POST, &url, &headers, Some(Body::Bytes(wav.to_vec())), Some(HTTP_TIMEOUT)) {
            Ok(r) => r,
            Err(e) if e.downcast_ref::<reqwest::Error>().is_some_and(|e| e.is_timeout()) => return Err(TIMEOUT),
            Err(_) => return Err(SERVER_ERROR),
        };
        match response.status().as_u16() {
            200 => {}
            401 | 403 => return Err(AUTH_FAILED),
            429 => return Err(RATE_LIMITED),
            _ => return Err(SERVER_ERROR),
        }
        let payload: Value = response.json().map_err(|_| SERVER_ERROR)?;
        let Some(alternative) = payload.pointer("/results/channels/0/alternatives/0") else {
            return Ok((String::new(), 0.0, false));
        };
        let text = alternative.get("transcript").and_then(Value::as_str).unwrap_or("").to_string();
        if text.is_empty() {
            return Ok((String::new(), 0.0, false));
        }
        let confidence = alternative.get("confidence").and_then(Value::as_f64).unwrap_or(0.0);
        Ok((text, confidence, true))
    }
}

/// checkDeepgramApiKey
pub fn check_deepgram_key(http: &Http, api_key: &str) -> bool {
    let headers = [("authorization", format!("Token {api_key}"))];
    http.get(&format!("{DEEPGRAM_BASE_URL}/models"), &headers, Some(HTTP_TIMEOUT)).is_ok_and(|r| r.status().as_u16() == 200)
}

/// getAvailableDeepgramModelsDetailed: the batch-capable STT models (name, languages), by name
pub fn deepgram_models(http: &Http, api_key: &str) -> Vec<(String, Vec<String>)> {
    let headers = [("authorization", format!("Token {api_key}"))];
    let Ok(response) = http.get(&format!("{DEEPGRAM_BASE_URL}/models"), &headers, Some(HTTP_TIMEOUT)) else { return vec![] };
    if !response.status().is_success() {
        return vec![];
    }
    let Ok(body) = response.json::<Value>() else { return vec![] };
    let mut seen = std::collections::HashSet::new();
    let mut result = vec![];
    for m in body.get("stt").and_then(Value::as_array).into_iter().flatten() {
        let name = m.get("name").and_then(Value::as_str).unwrap_or("");
        if name.is_empty() || m.get("batch") != Some(&json!(true)) || !seen.insert(name.to_string()) {
            continue;
        }
        let langs = m.get("languages").and_then(Value::as_array).map(|l| {
            l.iter().map(|x| x.as_str().unwrap_or("").to_string()).collect()
        }).unwrap_or_default();
        result.push((name.to_string(), langs));
    }
    result.sort_by(|a, b| a.0.cmp(&b.0));
    result
}

/// resolveDeepgramLanguageCode: the model's own code for the language (Google's regional code
/// exactly, else Whisper's base code), None when nothing matches or the model is "multi".
pub fn resolve_deepgram_language(languages: &Languages, language: &str, country: &str, model_languages: &[String]) -> Option<String> {
    let entry = languages.entry(language, country)?;
    // {lowercase: first original}, in order
    let mut normalized: Vec<(String, String)> = vec![];
    for code in model_languages.iter().filter(|c| !c.is_empty()) {
        if !normalized.iter().any(|(n, _)| *n == code.to_lowercase()) {
            normalized.push((code.to_lowercase(), code.clone()));
        }
    }
    if normalized.is_empty() || normalized.iter().any(|(n, _)| n == "multi") {
        return None;
    }
    if let Some(google) = entry.get("Google").and_then(Value::as_str).filter(|g| !g.is_empty()) {
        if let Some((_, original)) = normalized.iter().find(|(n, _)| *n == google.to_lowercase()) {
            return Some(original.clone());
        }
    }
    let whisper = entry.get("Whisper").and_then(Value::as_str).filter(|w| !w.is_empty())?;
    let base = |c: &str| c.split('-').next().unwrap_or("").to_lowercase();
    let wanted = base(whisper);
    normalized.iter().find(|(n, _)| base(n) == wanted).map(|(_, original)| original.clone())
}
