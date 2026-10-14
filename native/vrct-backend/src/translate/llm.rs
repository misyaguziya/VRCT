//! The LLM translation engines (models/translation/translation_{openai,groq,openrouter,plamo,
//! openai_compatible,lmstudio,ollama,gemini}.py and translation_model_list.py), sending the same
//! HTTP requests as the SDKs they used: the openai SDK (model lists, with its retries), langchain's
//! ChatOpenAI (chat completions), langchain-ollama (/api/chat), google-genai (model list pages) and
//! langchain-google-genai (generateContent; gRPC in Python, the same request over REST here).
use crate::net::{Body, Http};
use crate::openai;
use crate::pyfmt;
use anyhow::{anyhow, bail, Context, Result};
use reqwest::Method;
use serde_json::{json, Value};
use std::path::Path;
use std::time::{Duration, Instant};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Engine {
    OpenAi,
    Groq,
    OpenRouter,
    Plamo,
    OpenAiCompatible,
    LmStudio,
    Ollama,
    Gemini,
}

impl Engine {
    /// The engine's key in languages.yml / config
    pub fn key(self) -> &'static str {
        match self {
            Engine::OpenAi => "OpenAI_API",
            Engine::Groq => "Groq_API",
            Engine::OpenRouter => "OpenRouter_API",
            Engine::Plamo => "Plamo_API",
            Engine::OpenAiCompatible => "OpenAI_Compatible",
            Engine::LmStudio => "LMStudio",
            Engine::Ollama => "Ollama",
            Engine::Gemini => "Gemini_API",
        }
    }

    fn prompt_file(self) -> &'static str {
        match self {
            Engine::OpenAi => "translation_openai.yml",
            Engine::Groq => "translation_groq.yml",
            Engine::OpenRouter => "translation_openrouter.yml",
            Engine::Plamo => "translation_plamo.yml",
            Engine::OpenAiCompatible => "translation_openai_compatible.yml",
            Engine::LmStudio => "translation_lmstudio.yml",
            Engine::Ollama => "translation_ollama.yml",
            Engine::Gemini => "translation_gemini.yml",
        }
    }

    fn default_base_url(self) -> Option<&'static str> {
        match self {
            Engine::Groq => Some("https://api.groq.com/openai/v1"),
            Engine::OpenRouter => Some("https://openrouter.ai/api/v1"),
            Engine::Plamo => Some("https://api.platform.preferredai.jp/v1"),
            Engine::OpenAiCompatible => Some(openai::DEFAULT_BASE_URL),
            Engine::Ollama => Some("http://localhost:11434"),
            Engine::OpenAi | Engine::LmStudio | Engine::Gemini => None,
        }
    }
}

const GEMINI_BASE_URL: &str = "https://generativelanguage.googleapis.com/v1beta";
/// translation_model_list._RECENT_SEC
const RECENT: Duration = Duration::from_secs(30);
const OPENAI_EXCLUDE: [&str; 9] = ["whisper", "embedding", "image", "tts", "audio", "search", "transcribe", "diarize", "vision"];
const COMPATIBLE_EXCLUDE: [&str; 12] = ["whisper", "embedding", "image", "tts", "audio", "search", "transcribe", "diarize",
                                        "vision", "dall-e", "moderation", "rerank"];
const GEMINI_EXCLUDE: [&str; 6] = ["audio", "image", "veo", "tts", "robotics", "computer-use"];

/// One recent message for the prompt (Translator.setContextHistory items)
#[derive(Clone, Debug, Default)]
pub struct HistoryItem {
    pub source: String,
    pub text: String,
    pub timestamp: Option<String>,
}

struct HistoryConfig {
    use_history: bool,
    sources: Vec<String>,
    max_messages: i64,
    max_chars: i64,
    header_template: String,
    item_template: String,
}

pub struct LlmClient {
    engine: Engine,
    http: Http,
    pub api_key: Option<String>,
    pub model: Option<String>,
    pub base_url: Option<String>,
    prompt_template: String,
    history_cfg: HistoryConfig,
    supported_languages: Vec<String>,
    /// the last context set; translations to several targets share the client
    history: std::sync::Mutex<Vec<HistoryItem>>,
    recent_models: Option<(Instant, Vec<String>)>,
    auth_models: Option<(Instant, Vec<String>)>,
}

fn str_field<'a>(v: &'a Value, key: &str) -> &'a str {
    v.get(key).and_then(Value::as_str).unwrap_or("")
}

/// datetime.fromisoformat(value).strftime("%H:%M"), or None where Python raises.
// ponytail: the forms datetime.isoformat() writes (date, any one-char separator, HH:MM[:SS[.f]],
// optional Z / ±HH:MM), not Python 3.11's full ISO 8601 parser; VRCT writes these timestamps itself.
fn iso_hour_minute(value: &str) -> Option<String> {
    let b = value.as_bytes();
    let digits = |s: &[u8]| !s.is_empty() && s.iter().all(u8::is_ascii_digit);
    let num = |s: &[u8]| std::str::from_utf8(s).ok()?.parse::<u32>().ok();
    if b.len() < 10 || !digits(&b[0..4]) || b[4] != b'-' || !digits(&b[5..7]) || b[7] != b'-' || !digits(&b[8..10]) {
        return None;
    }
    let (year, month, day) = (num(&b[0..4])?, num(&b[5..7])?, num(&b[8..10])?);
    let leap = year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
    let days = [31, if leap { 29 } else { 28 }, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    if year == 0 || !(1..=12).contains(&month) || day == 0 || day > days[month as usize - 1] {
        return None;
    }
    if b.len() == 10 {
        return Some("00:00".into());
    }
    let mut time = std::str::from_utf8(&b[10..]).ok()?.get(1..)?; // any one-char separator
    if let Some(i) = time.find(['+', '-']) {
        let tz = &time.as_bytes()[i + 1..];
        if !(tz.len() == 5 && digits(&tz[0..2]) && tz[2] == b':' && digits(&tz[3..5])) {
            return None;
        }
        time = &time[..i];
    } else if let Some(t) = time.strip_suffix('Z') {
        time = t;
    }
    let t = time.as_bytes();
    if t.len() < 5 || !digits(&t[0..2]) || t[2] != b':' || !digits(&t[3..5]) {
        return None;
    }
    let (hour, minute) = (num(&t[0..2])?, num(&t[3..5])?);
    if hour > 23 || minute > 59 {
        return None;
    }
    let rest = &t[5..];
    if !rest.is_empty() {
        if rest.len() < 3 || rest[0] != b':' || !digits(&rest[1..3]) || num(&rest[1..3])? > 59 {
            return None;
        }
        let frac = &rest[3..];
        if !(frac.is_empty() || frac[0] == b'.' && digits(&frac[1..])) {
            return None;
        }
    }
    Some(format!("{hour:02}:{minute:02}"))
}

/// `client.models.list().data` (openai SDK)
fn fetch_openai_models(http: &Http, base: &str, api_key: &str) -> Result<Vec<Value>> {
    Ok(openai::list_models(http, base, api_key, openai::DEFAULT_TIMEOUT)?)
}

fn sorted(mut v: Vec<String>) -> Vec<String> {
    v.sort();
    v
}

/// translation_openai._text_models: GPT models (and fine-tunes of them) without the excluded words
fn filter_openai(models: &[Value]) -> Vec<String> {
    sorted(models
        .iter()
        .filter_map(|m| {
            let (id, root) = (str_field(m, "id"), str_field(m, "root"));
            if OPENAI_EXCLUDE.iter().any(|kw| id.contains(kw)) {
                return None;
            }
            (id.starts_with("gpt-") || (id.starts_with("ft:") && root.starts_with("gpt-"))).then(|| id.to_string())
        })
        .collect())
}

/// Groq / OpenRouter / OpenAI_Compatible: everything but the excluded words (case-insensitive)
fn filter_excluding(models: &[Value], exclude: &[&str]) -> Vec<String> {
    sorted(models
        .iter()
        .map(|m| str_field(m, "id"))
        .filter(|id| !exclude.iter().any(|kw| id.to_lowercase().contains(kw)))
        .map(String::from)
        .collect())
}

fn ids(models: &[Value], key: &str) -> Vec<String> {
    sorted(models.iter().map(|m| str_field(m, key).to_string()).collect())
}

/// translation_gemini._text_models over every page
fn filter_gemini(models: &[Value]) -> Vec<String> {
    sorted(models
        .iter()
        .filter_map(|m| {
            let name = str_field(m, "name");
            let actions = m.get("supportedGenerationMethods").and_then(Value::as_array);
            let generate = actions.is_some_and(|a| a.iter().any(|v| v == "generateContent"));
            let lower = name.to_lowercase();
            ((lower.contains("gemini") || lower.contains("gemma")) && generate && !GEMINI_EXCLUDE.iter().any(|x| name.contains(x)))
                .then(|| name.replace("models/", ""))
        })
        .collect())
}

/// google-genai's models.list() pager: (first page, the rest of the pages fetched lazily)
fn gemini_page(http: &Http, api_key: &str, page_token: Option<&str>) -> Result<Value> {
    let url = match page_token {
        None => format!("{GEMINI_BASE_URL}/models"),
        Some(t) => format!("{GEMINI_BASE_URL}/models?pageToken={}", urlencoding(t)),
    };
    let headers = [("content-type", "application/json".to_string()), ("x-goog-api-key", api_key.to_string())];
    let response = http.get(&url, &headers, None)?;
    if !response.status().is_success() {
        bail!("HTTP {}: {}", response.status(), response.text().unwrap_or_default());
    }
    Ok(response.json()?)
}

fn urlencoding(s: &str) -> String {
    s.bytes()
        .map(|b| match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'.' | b'_' | b'~' => (b as char).to_string(),
            b => format!("%{b:02X}"),
        })
        .collect()
}

fn gemini_rest_of_pages(http: &Http, api_key: &str, first: &Value) -> Result<Vec<Value>> {
    let mut models: Vec<Value> = first.get("models").and_then(Value::as_array).cloned().unwrap_or_default();
    let mut token = str_field(first, "nextPageToken").to_string();
    while !token.is_empty() {
        let page = gemini_page(http, api_key, Some(&token))?;
        models.extend(page.get("models").and_then(Value::as_array).cloned().unwrap_or_default());
        token = str_field(&page, "nextPageToken").to_string();
    }
    Ok(models)
}

impl LlmClient {
    /// `XClient(root_path)` / `XClient(base_url=...)`: the prompt YAML and the language names come
    /// from `settings_dir` (translation_settings: prompt/*.yml, languages/languages.yml).
    pub fn new(engine: Engine, http: Http, settings_dir: &Path, base_url: Option<&str>) -> Result<Self> {
        let prompt: serde_yaml::Value = serde_yaml::from_slice(
            &std::fs::read(settings_dir.join("prompt").join(engine.prompt_file()))
                .with_context(|| format!("prompt file {}", engine.prompt_file()))?,
        )?;
        let languages: serde_yaml::Value =
            serde_yaml::from_slice(&std::fs::read(settings_dir.join("languages").join("languages.yml"))?)?;
        let supported_languages = languages[engine.key()]["source"]
            .as_mapping()
            .with_context(|| format!("languages.yml: {}", engine.key()))?
            .keys()
            .map(|k| k.as_str().map(String::from).context("language name"))
            .collect::<Result<_>>()?;
        let h = &prompt["history"];
        let history_cfg = if h.is_mapping() {
            let s = |k: &str, d: &str| h.get(k).and_then(|v| v.as_str()).unwrap_or(d).to_string();
            HistoryConfig {
                use_history: h.get("use_history").and_then(|v| v.as_bool()).unwrap_or(false),
                sources: h.get("sources").and_then(|v| v.as_sequence())
                    .map(|v| v.iter().filter_map(|x| x.as_str().map(String::from)).collect()).unwrap_or_default(),
                max_messages: h.get("max_messages").and_then(|v| v.as_i64()).unwrap_or(0),
                max_chars: h.get("max_chars").and_then(|v| v.as_i64()).unwrap_or(0),
                header_template: s("header_template", "{history}"),
                item_template: s("item_template", "[{source}] {role}: {text}"),
            }
        } else {
            HistoryConfig { use_history: false, sources: vec![], max_messages: 0, max_chars: 0,
                            header_template: String::new(), item_template: "[{source}] {role}: {text}".into() }
        };
        let base_url = match engine {
            Engine::OpenAi | Engine::LmStudio => base_url.map(String::from),
            Engine::OpenAiCompatible => Some(base_url.filter(|u| !u.is_empty()).unwrap_or(openai::DEFAULT_BASE_URL).to_string()),
            _ => engine.default_base_url().map(String::from),
        };
        Ok(Self {
            engine,
            http,
            api_key: None,
            model: None,
            base_url,
            prompt_template: prompt["system_prompt"].as_str().context("system_prompt")?.to_string(),
            history_cfg,
            supported_languages,
            history: Default::default(),
            recent_models: None,
            auth_models: None,
        })
    }

    fn openai_base(&self) -> &str {
        self.base_url.as_deref().unwrap_or(openai::DEFAULT_BASE_URL)
    }

    // ---- RecentModelList --------------------------------------------------------------------

    fn remember(&mut self, models: Vec<String>) -> Vec<String> {
        if !models.is_empty() {
            self.recent_models = Some((Instant::now(), models.clone()));
        }
        models
    }

    fn recent(&self) -> Option<Vec<String>> {
        self.recent_models.as_ref().filter(|(t, _)| t.elapsed() <= RECENT).map(|(_, m)| m.clone())
    }

    fn remember_from_auth(&mut self, models: Result<Vec<String>>) {
        if let Ok(models) = models {
            if !models.is_empty() {
                self.auth_models = Some((Instant::now(), models));
            }
        }
    }

    fn take_auth_models(&mut self) -> Option<Vec<String>> {
        self.auth_models.take().filter(|(t, _)| t.elapsed() <= RECENT).map(|(_, m)| m).filter(|m| !m.is_empty())
    }

    /// setModel: checked against the recent list, or a fresh one
    pub fn set_model(&mut self, model: &str) -> Result<bool> {
        let models = match self.recent() {
            Some(m) => m,
            None => self.get_model_list()?,
        };
        if models.iter().any(|m| m == model) {
            self.model = Some(model.to_string());
            return Ok(true);
        }
        Ok(false)
    }

    // ---- engine-specific ----------------------------------------------------------------------

    fn filter(&self, models: &[Value]) -> Vec<String> {
        match self.engine {
            Engine::OpenAi => filter_openai(models),
            Engine::Groq | Engine::OpenRouter => filter_excluding(models, &OPENAI_EXCLUDE),
            Engine::OpenAiCompatible => filter_excluding(models, &COMPATIBLE_EXCLUDE),
            Engine::Plamo => ids(models, "id"),
            Engine::LmStudio | Engine::Ollama | Engine::Gemini => unreachable!(),
        }
    }

    /// setAuthKey (OpenAI / Groq / Plamo / OpenAI_Compatible / OpenRouter / Gemini)
    pub fn set_auth_key(&mut self, api_key: &str) -> Result<bool> {
        match self.engine {
            Engine::OpenRouter => {
                let headers = [("authorization", format!("Bearer {api_key}"))];
                let response = self.http.get("https://openrouter.ai/api/v1/auth/key", &headers, Some(Duration::from_secs(10)))?;
                let ok = response.status().as_u16() == 200;
                if ok {
                    self.api_key = Some(api_key.to_string());
                }
                Ok(ok)
            }
            Engine::Gemini => {
                let Ok(first) = gemini_page(&self.http, api_key, None) else { return Ok(false) };
                self.api_key = Some(api_key.to_string());
                let models = gemini_rest_of_pages(&self.http, api_key, &first).map(|m| filter_gemini(&m));
                self.remember_from_auth(models);
                Ok(true)
            }
            Engine::LmStudio | Engine::Ollama => bail!("{} has no auth key", self.engine.key()),
            _ => {
                let Ok(models) = fetch_openai_models(&self.http, self.openai_base(), api_key) else { return Ok(false) };
                self.api_key = Some(api_key.to_string());
                let filtered = self.filter(&models);
                self.remember_from_auth(Ok(filtered));
                Ok(true)
            }
        }
    }

    /// getModelList
    pub fn get_model_list(&mut self) -> Result<Vec<String>> {
        match self.engine {
            Engine::OpenAi | Engine::Groq | Engine::Plamo => {
                let Some(key) = self.api_key.clone() else { return Ok(vec![]) };
                let models = match self.take_auth_models() {
                    Some(m) => m,
                    None => self.filter(&fetch_openai_models(&self.http, self.openai_base(), &key)?),
                };
                Ok(self.remember(models))
            }
            Engine::OpenRouter => {
                let Some(key) = self.api_key.clone() else { return Ok(vec![]) };
                let models = self.filter(&fetch_openai_models(&self.http, self.openai_base(), &key)?);
                Ok(self.remember(models))
            }
            Engine::OpenAiCompatible => {
                let (Some(key), Some(_)) = (self.api_key.clone(), self.base_url.as_ref().filter(|u| !u.is_empty())) else {
                    return Ok(vec![]);
                };
                let models = match self.take_auth_models() {
                    Some(m) => Ok(m),
                    None => fetch_openai_models(&self.http, self.openai_base(), &key).map(|m| self.filter(&m)),
                };
                Ok(models.map(|m| self.remember(m)).unwrap_or_default())
            }
            Engine::LmStudio => {
                let Some(base) = self.base_url.clone() else { return Ok(vec![]) };
                let models = self
                    .http
                    .get(&format!("{base}/models"), &[], Some(Duration::from_millis(200)))
                    .and_then(|r| Ok(r.json::<Value>()?))
                    .ok()
                    .and_then(|v| v.get("data").and_then(Value::as_array).cloned())
                    .unwrap_or_default();
                let models = ids(&models, "id");
                Ok(self.remember(models))
            }
            Engine::Ollama => {
                if !self.authentication_check() {
                    return Ok(vec![]);
                }
                let base = self.base_url.clone().unwrap_or_default();
                let models = self
                    .http
                    .get(&format!("{base}/api/tags"), &[], None)
                    .and_then(|r| Ok(r.json::<Value>()?))
                    .ok()
                    .and_then(|v| v.get("models").and_then(Value::as_array).cloned())
                    .unwrap_or_default();
                let models = ids(&models, "name");
                Ok(self.remember(models))
            }
            Engine::Gemini => {
                let models = match self.take_auth_models() {
                    Some(m) => m,
                    None => {
                        let key = self.api_key.clone().context("Gemini: no API key")?;
                        let first = gemini_page(&self.http, &key, None)?;
                        filter_gemini(&gemini_rest_of_pages(&self.http, &key, &first)?)
                    }
                };
                Ok(self.remember(models))
            }
        }
    }

    /// LMStudio.setBaseURL: kept only when `{url}/models` answers 200 within 0.2 s.
    /// OpenAI_Compatible.setBaseURL: always kept (empty = the official endpoint).
    pub fn set_base_url(&mut self, url: Option<&str>) -> bool {
        match self.engine {
            Engine::OpenAiCompatible => {
                self.base_url = Some(url.filter(|u| !u.is_empty()).unwrap_or(openai::DEFAULT_BASE_URL).to_string());
                true
            }
            _ => {
                let target = format!("{}/models", url.unwrap_or("None"));
                let ok = self.http.get(&target, &[], Some(Duration::from_millis(200)))
                    .is_ok_and(|r| r.status().as_u16() == 200);
                if ok {
                    self.base_url = url.map(String::from);
                }
                ok
            }
        }
    }

    /// Ollama.authenticationCheck: the server answers 200 within 0.2 s
    pub fn authentication_check(&self) -> bool {
        let base = self.base_url.clone().unwrap_or_default();
        self.http.get(&base, &[], Some(Duration::from_millis(200))).is_ok_and(|r| r.status().as_u16() == 200)
    }

    pub fn set_context_history(&self, items: Vec<HistoryItem>) {
        *self.history.lock().unwrap() = items;
    }

    /// The system prompt translate() builds (the template, then the recent history if enabled).
    pub fn system_prompt(&self, input_lang: &str, output_lang: &str) -> Result<String> {
        let languages = pyfmt::repr_list(&self.supported_languages);
        let mut prompt = pyfmt::format(&self.prompt_template,
            &[("supported_languages", &languages), ("input_lang", input_lang), ("output_lang", output_lang)])?;
        let cfg = &self.history_cfg;
        if cfg.use_history {
            let history = self.history.lock().unwrap();
            let filtered: Vec<&HistoryItem> = history.iter().filter(|h| cfg.sources.contains(&h.source)).collect();
            let recent = if cfg.max_messages > 0 {
                &filtered[filtered.len().saturating_sub(cfg.max_messages as usize)..]
            } else {
                &filtered[..]
            };
            let items = recent
                .iter()
                .map(|h| {
                    let timestamp = h.timestamp.as_deref().and_then(iso_hour_minute).unwrap_or_default();
                    pyfmt::format(&cfg.item_template, &[("timestamp", &timestamp), ("source", &h.source), ("text", &h.text)])
                })
                .collect::<Result<Vec<_>>>()?;
            let joined = items.join("\n");
            let mut blob = pyfmt::strip(&joined).to_string();
            let count = blob.chars().count() as i64;
            if cfg.max_chars != 0 && count > cfg.max_chars {
                blob = blob.chars().skip((count - cfg.max_chars) as usize).collect();
            }
            let header = pyfmt::format(&cfg.header_template,
                &[("max_messages", &cfg.max_messages.to_string()), ("history", &blob)])?;
            if !header.is_empty() {
                prompt = format!("{prompt}\n\n{header}");
            }
        }
        Ok(prompt)
    }

    /// translate(text, input_lang, output_lang): the reply, stripped.
    pub fn translate(&self, text: &str, input_lang: &str, output_lang: &str) -> Result<String> {
        let system = self.system_prompt(input_lang, output_lang)?;
        let model = self.model.clone().ok_or_else(|| anyhow!("{}: no model", self.engine.key()))?;
        let content = match self.engine {
            Engine::Ollama => self.ollama_chat(&model, &system, text)?,
            Engine::Gemini => self.gemini_generate(&model, &system, text)?,
            _ => {
                let key = match self.engine {
                    Engine::LmStudio => "lmstudio".to_string(),
                    _ => self.api_key.clone().context("no API key")?,
                };
                let headers = [("accept", "application/json".to_string()), ("authorization", format!("Bearer {key}"))];
                // langchain-openai sends the system message as "developer" to o-series models (^o\d)
                let o_series = model.len() >= 2 && model.starts_with('o') && model.as_bytes()[1].is_ascii_digit();
                let role = if o_series { "developer" } else { "system" };
                let mut body = json!({
                    "messages": [{"content": system, "role": role}, {"content": text, "role": "user"}],
                    "model": model,
                    "stream": false,
                });
                // ChatOpenAI.validate_temperature: o1 models get temperature=1 (a float field)
                if model.starts_with("o1") {
                    body["temperature"] = json!(1.0);
                }
                let url = openai::url(self.openai_base(), "chat/completions");
                let response = openai::send(&self.http, Method::POST, &url, &headers, &|| Some(Body::Json(body.clone())),
                                            openai::DEFAULT_TIMEOUT)?;
                response["choices"][0]["message"]["content"].as_str().unwrap_or("").to_string()
            }
        };
        Ok(pyfmt::strip(&content).to_string())
    }

    /// ChatOllama (streaming=False still streams /api/chat; the chunks are joined)
    fn ollama_chat(&self, model: &str, system: &str, text: &str) -> Result<String> {
        let body = json!({
            "model": model,
            "stream": true,
            "options": {},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": text}],
            "tools": [],
        });
        let url = format!("{}/api/chat", self.base_url.as_deref().unwrap_or_default());
        let response = self.http.send(Method::POST, &url, &[("accept", "application/json".into())], Some(Body::Json(body)), None)?;
        if !response.status().is_success() {
            bail!("HTTP {}: {}", response.status(), response.text().unwrap_or_default());
        }
        let mut content = String::new();
        for line in response.text()?.lines().filter(|l| !l.trim().is_empty()) {
            let chunk: Value = serde_json::from_str(line)?;
            if let Some(error) = chunk.get("error") {
                bail!("ollama: {error}");
            }
            content += chunk["message"]["content"].as_str().unwrap_or("");
        }
        Ok(content)
    }

    /// ChatGoogleGenerativeAI(model, api_key).invoke: generateContent with the system message as
    /// system_instruction, candidate_count 1, temperature 0.7. langchain retries up to 6 attempts
    /// (waits of 2, 4, 8, 16, 32 s) on any API error except an invalid argument (400).
    fn gemini_generate(&self, model: &str, system: &str, text: &str) -> Result<String> {
        let key = self.api_key.clone().context("Gemini: no API key")?;
        let body = json!({
            "contents": [{"parts": [{"text": text}], "role": "user"}],
            "systemInstruction": {"parts": [{"text": system}]},
            "generationConfig": {"candidateCount": 1, "temperature": 0.7},
        });
        let url = format!("{GEMINI_BASE_URL}/models/{model}:generateContent");
        let headers = [("x-goog-api-key", key)];
        let mut attempt = 1;
        let response: Value = loop {
            let result = self.http.send(Method::POST, &url, &headers, Some(Body::Json(body.clone())), None);
            let error = match result {
                Ok(r) if r.status().is_success() => break r.json()?,
                Ok(r) if r.status().as_u16() == 400 => bail!("Invalid argument provided to Gemini: {}", r.text().unwrap_or_default()),
                Ok(r) => anyhow!("HTTP {}: {}", r.status(), r.text().unwrap_or_default()),
                Err(e) => e,
            };
            if attempt >= 6 {
                return Err(error);
            }
            std::thread::sleep(Duration::from_secs(2u64 << (attempt - 1)).min(Duration::from_secs(60)));
            attempt += 1;
        };
        let parts = response["candidates"][0]["content"]["parts"].as_array().cloned().unwrap_or_default();
        Ok(parts
            .iter()
            .filter(|p| !p.get("thought").and_then(Value::as_bool).unwrap_or(false))
            .filter_map(|p| p.get("text").and_then(Value::as_str))
            .collect())
    }
}

#[cfg(test)]
mod tests {
    use super::iso_hour_minute;

    #[test]
    fn isoformat_like_python() {
        for (input, expected) in [
            ("2026-10-11T09:05:00", Some("09:05")),
            ("2026-10-11T21:30:15.123456", Some("21:30")),
            ("2026-10-11T23:59:59+09:00", Some("23:59")),
            ("2026-10-11 07:08", Some("07:08")),
            ("2026-10-11", Some("00:00")),
            ("2026-02-30T00:00:00", None),
            ("not a time", None),
            ("", None),
        ] {
            assert_eq!(iso_hour_minute(input).as_deref(), expected, "{input}");
        }
    }
}
