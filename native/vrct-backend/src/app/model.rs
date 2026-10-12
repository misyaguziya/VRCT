//! The services behind the handlers (model.py's Model) and the language tables' questions
//! (which engine speaks which language).
use super::services::{Osc, Servers, Watchdog};
use crate::asr::{self, Languages};
use crate::clipboard::AppName;
use crate::config::Config;
use crate::keywords::Keywords;
use crate::logs::LogFile;
use crate::net::Http;
use crate::telemetry::Telemetry;
use crate::translate::llm::HistoryItem;
use crate::translate::Translator;
use crate::translit::Transliterator;
use anyhow::Result;
use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use std::sync::atomic::AtomicBool;
use std::sync::{Arc, Mutex};

/// The files beside the executable (or the folder given)
pub struct Resources {
    pub dir: PathBuf,
}

impl Resources {
    pub fn translation_settings(&self) -> PathBuf {
        self.dir.join("translation_settings")
    }

    /// SudachiPy's resources and SudachiDict-full's system.dic
    pub fn sudachi(&self) -> PathBuf {
        self.dir.join("sudachi")
    }
}

pub struct Model {
    pub http: Http,
    pub resources: Resources,
    /// translation_lang (languages.yml): engine -> {source, target} (CTranslate2: weight type -> ...)
    pub translation_lang: Value,
    pub transcription_lang: Languages,
    pub translator: Mutex<Translator>,
    /// isChangedTranslatorParameters: the CTranslate2 model loads again on the next use
    pub translator_changed: AtomicBool,
    pub watchdog: Arc<Watchdog>,
    pub osc: Osc,
    pub servers: Servers,
    pub telemetry: Telemetry,
    /// the microphone's word filter (keyword_processor)
    pub keywords: Mutex<Keywords>,
    /// the chat log (logger), while LOGGER_FEATURE is on
    pub logger: Mutex<Option<LogFile>>,
    pub transliterator: Mutex<Option<Transliterator>>,
    /// VRChat's MuteSelf as last seen (None: not known yet)
    pub mic_mute_status: Mutex<Option<bool>>,
    /// the context of the LLM engines (the last messages)
    pub translation_history: Mutex<Vec<HistoryItem>>,
    pub previous_send_message: Mutex<String>,
    pub previous_receive_message: Mutex<String>,
    /// the window the clipboard pastes into (the Steam app SteamVR runs)
    pub app_name: AppName,
}

impl Model {
    pub fn new(http: Http, resources: Resources, transcription_lang: Value, config: &Config) -> Result<Model> {
        let settings = resources.translation_settings();
        let yaml: serde_yaml::Value = serde_yaml::from_slice(&std::fs::read(settings.join("languages").join("languages.yml"))?)?;
        let translation_lang = serde_json::to_value(yaml)?;
        let translator = Translator::new(http.clone(), &settings)?;
        Ok(Model {
            resources,
            translation_lang,
            transcription_lang: Languages::new(transcription_lang),
            translator: Mutex::new(translator),
            translator_changed: AtomicBool::new(false),
            watchdog: Arc::default(),
            osc: Osc::new(&config.get_str("OSC_IP_ADDRESS"), config.get("OSC_PORT").as_i64().unwrap_or(9000)),
            servers: Servers::default(),
            telemetry: Telemetry::new(http.clone(), option_env!("VRCT_TELEMETRY_APP_KEY").map(String::from)),
            keywords: Mutex::default(),
            logger: Mutex::new(None),
            transliterator: Mutex::new(None),
            mic_mute_status: Mutex::new(None),
            translation_history: Mutex::default(),
            previous_send_message: Mutex::default(),
            previous_receive_message: Mutex::default(),
            app_name: {
                crate::ipc::log("Clipboard initialized. Waiting for SteamVR.");
                AppName::watch(crate::ipc::log)
            },
            http,
        })
    }

    pub fn settings_dir(&self) -> &Path {
        &self.resources.dir
    }

    // ---------------------------------------------------------------- translation languages

    /// getTranslationLanguagesForEngine: the source languages (CTranslate2: of the weight type)
    pub fn translation_languages_for_engine(&self, config: &Config, engine: &str) -> Vec<String> {
        let table = &self.translation_lang[engine];
        let table = if engine == "CTranslate2" { &table[config.get_str("CTRANSLATE2_WEIGHT_TYPE")] } else { table };
        table["source"].as_object().map(|m| m.keys().cloned().collect()).unwrap_or_default()
    }

    pub fn is_language_supported_by_engine(&self, config: &Config, engine: &str, language: &str) -> bool {
        self.translation_languages_for_engine(config, engine).iter().any(|l| l == language)
    }

    /// pickDefaultLanguageForEngine: Japanese then English, else the engine's first language that
    /// transcription knows; never one in `avoid`
    pub fn pick_default_language_for_engine(&self, config: &Config, engine: &str, avoid: &[String]) -> Option<Value> {
        let avoided = |l: &str| avoid.iter().any(|a| a == l);
        for (language, country) in [("Japanese", "Japan"), ("English", "United States")] {
            if !avoided(language) && self.is_language_supported_by_engine(config, engine, language) {
                return Some(json!({"language": language, "country": country}));
            }
        }
        let table = self.transcription_lang.table();
        self.translation_languages_for_engine(config, engine).into_iter().find(|l| !avoided(l) && table.get(l).is_some()).map(|l| {
            let country = table[&l].as_object().and_then(|m| m.keys().next().cloned()).unwrap_or_default();
            json!({"language": l, "country": country})
        })
    }

    /// findTranslationEngines: the available engines (in languages.yml's order) speaking every
    /// enabled language
    pub fn find_translation_engines(&self, config: &Config, source: &Value, target: &Value, status: &Value) -> Vec<String> {
        let enabled = |slots: &Value| -> Vec<String> {
            slots.as_object().map(|m| m.values().filter(|e| e["enable"] == json!(true)).filter_map(|e| e["language"].as_str().map(String::from)).collect())
                .unwrap_or_default()
        };
        let (sources, targets) = (enabled(source), enabled(target));
        let engines: Vec<String> = self.translation_lang.as_object().map(|m| m.keys().cloned().collect()).unwrap_or_default();
        engines.into_iter().filter(|engine| {
            let languages = self.translation_languages_for_engine(config, engine);
            sources.iter().chain(&targets).all(|l| languages.contains(l)) && status.get(engine) == Some(&json!(true))
        }).collect()
    }

    // ---------------------------------------------------------------- transcription languages

    /// isLanguageSupportedByTranscriptionEngine: every entry for all but Deepgram, which checks the
    /// selected model's languages
    pub fn is_language_supported_by_transcription_engine(&self, config: &Config, engine: &str, language: &str, country: &str) -> bool {
        if self.transcription_lang.table().get(language).and_then(|c| c.get(country)).is_none() {
            return false;
        }
        if engine != "Deepgram" {
            return true;
        }
        let selected = config.get_str("SELECTED_DEEPGRAM_MODEL");
        let model_languages: Vec<String> = config.get("DEEPGRAM_MODEL_LANGUAGES").get(&selected).and_then(Value::as_array)
            .map(|a| a.iter().filter_map(|v| v.as_str().map(String::from)).collect()).unwrap_or_default();
        // "multi": any language
        if model_languages.iter().any(|c| c.to_lowercase() == "multi") {
            return true;
        }
        asr::resolve_deepgram_language(&self.transcription_lang, language, country, &model_languages).is_some()
    }

    /// getTranscriptionLanguagesForEngine
    pub fn transcription_languages_for_engine(&self, config: &Config, engine: &str) -> Vec<(String, String)> {
        let mut out = vec![];
        for (language, countries) in self.transcription_lang.table().as_object().into_iter().flatten() {
            for country in countries.as_object().into_iter().flat_map(|c| c.keys()) {
                if self.is_language_supported_by_transcription_engine(config, engine, language, country) {
                    out.push((language.clone(), country.clone()));
                }
            }
        }
        out
    }

    /// pickDefaultLanguageAndCountryForTranscriptionEngine
    pub fn pick_default_language_for_transcription_engine(&self, config: &Config, engine: &str, avoid: &[String]) -> Option<Value> {
        let avoided = |l: &str| avoid.iter().any(|a| a == l);
        for (language, country) in [("Japanese", "Japan"), ("English", "United States")] {
            if !avoided(language) && self.is_language_supported_by_transcription_engine(config, engine, language, country) {
                return Some(json!({"language": language, "country": country}));
            }
        }
        self.transcription_languages_for_engine(config, engine).into_iter().find(|(l, _)| !avoided(l))
            .map(|(language, country)| json!({"language": language, "country": country}))
    }

    /// getListLanguageAndCountry: every language some translation engine and transcription know,
    /// filtered by the transcription engine, sorted by language
    pub fn list_language_and_country(&self, config: &Config) -> Value {
        let engine = config.get_str("SELECTED_TRANSCRIPTION_ENGINE");
        let table = self.transcription_lang.table();
        let mut languages: Vec<String> = vec![];
        for engine in self.translation_lang.as_object().into_iter().flat_map(|m| m.keys()) {
            for language in self.translation_languages_for_engine(config, engine) {
                if table.get(&language).is_some() && !languages.contains(&language) {
                    languages.push(language);
                }
            }
        }
        languages.sort();
        let mut out = vec![];
        for language in languages {
            for country in table[&language].as_object().into_iter().flat_map(|c| c.keys()) {
                if self.is_language_supported_by_transcription_engine(config, &engine, &language, country) {
                    out.push(json!({"language": language, "country": country}));
                }
            }
        }
        json!(out)
    }
}
