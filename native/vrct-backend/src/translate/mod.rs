//! Translation (models/translation/translation_translator.py's `Translator`): the engines, the
//! language codes of languages.yml, and translate()'s three outcomes.
pub mod ctranslate2;
pub mod deepl;
pub mod llm;

use crate::net::Http;
use anyhow::{Context, Result};
use llm::{Engine, HistoryItem, LlmClient};
use std::collections::HashMap;
use std::path::{Path, PathBuf};

/// translator_engines' timeout as Translator passes it (_WEB_TRANSLATOR_TIMEOUT_SECONDS)
const WEB_TRANSLATOR_TIMEOUT_SECONDS: f64 = 10.0;

/// translate()'s result: the text, None (the language pair is not in this engine's table) or
/// False (the engine failed; the reason is kept for the error log).
#[derive(Clone, Debug, PartialEq)]
pub enum Translation {
    Text(String),
    Unsupported,
    Failed(String),
}

pub struct Translator {
    http: Http,
    settings_dir: PathBuf,
    languages: serde_yaml::Value,
    deepl: Option<deepl::DeepL>,
    /// The LLM engines with a client (authenticated / connected)
    llm: HashMap<&'static str, LlmClient>,
    pub lmstudio_connected: bool,
    pub ollama_connected: bool,
    pub ctranslate2: Option<ctranslate2::Ct2Translator>,
    /// In the tests: answers every pair the engine knows (engine, target language, message)
    #[cfg(test)]
    pub fake: Option<fn(&str, &str, &str) -> Translation>,
}

impl Translator {
    /// `settings_dir`: translation_settings (prompt/*.yml, languages/languages.yml)
    pub fn new(http: Http, settings_dir: &Path) -> Result<Self> {
        let languages = serde_yaml::from_slice(&std::fs::read(settings_dir.join("languages").join("languages.yml"))?)?;
        Ok(Self {
            http,
            settings_dir: settings_dir.to_path_buf(),
            languages,
            deepl: None,
            llm: HashMap::new(),
            lmstudio_connected: false,
            ollama_connected: false,
            ctranslate2: None,
            #[cfg(test)]
            fake: None,
        })
    }

    /// authenticationDeepLAuthKey: a one-space translation to EN-US checks the key
    pub fn authenticate_deepl(&mut self, auth_key: &str) -> Result<bool, String> {
        let client = deepl::DeepL::new(self.http.clone(), auth_key);
        match client.translate(" ", None, "EN-US") {
            Ok(_) => {
                self.deepl = Some(client);
                Ok(true)
            }
            Err(e) => {
                self.deepl = None;
                Err(format!("{e:#}"))
            }
        }
    }

    /// authenticationRegistryAuthKey / authenticationOpenAICompatibleAuthKey: a new client; kept
    /// only when the key works.
    pub fn authenticate_llm(&mut self, engine: Engine, auth_key: &str, base_url: Option<&str>) -> Result<bool> {
        let mut client = LlmClient::new(engine, self.http.clone(), &self.settings_dir, base_url)?;
        let ok = client.set_auth_key(auth_key)?;
        if ok {
            self.llm.insert(engine.key(), client);
        } else {
            self.llm.remove(engine.key());
        }
        Ok(ok)
    }

    /// setLMStudioClientURL
    pub fn set_lmstudio_url(&mut self, base_url: Option<&str>) -> Result<bool> {
        let mut client = LlmClient::new(Engine::LmStudio, self.http.clone(), &self.settings_dir, base_url)?;
        self.lmstudio_connected = client.set_base_url(base_url);
        if self.lmstudio_connected {
            self.llm.insert(Engine::LmStudio.key(), client);
        } else {
            self.llm.remove(Engine::LmStudio.key());
        }
        Ok(self.lmstudio_connected)
    }

    /// checkOllamaClient
    pub fn check_ollama(&mut self) -> Result<bool> {
        let client = LlmClient::new(Engine::Ollama, self.http.clone(), &self.settings_dir, None)?;
        self.ollama_connected = client.authentication_check();
        if self.ollama_connected {
            self.llm.insert(Engine::Ollama.key(), client);
        } else {
            self.llm.remove(Engine::Ollama.key());
        }
        Ok(self.ollama_connected)
    }

    /// getXModelList: [] without a client
    pub fn get_model_list(&mut self, engine: Engine) -> Result<Vec<String>> {
        match self.llm.get_mut(engine.key()) {
            None => Ok(vec![]),
            Some(c) => c.get_model_list(),
        }
    }

    /// setXModel: False without a client
    pub fn set_model(&mut self, engine: Engine, model: &str) -> Result<bool> {
        match self.llm.get_mut(engine.key()) {
            None => Ok(false),
            Some(c) => c.set_model(model),
        }
    }

    /// A client prepared without the translator's lock (the start-up checks run side by side):
    /// kept when Some, as authenticate_llm / set_lmstudio_url / check_ollama would keep it
    pub fn put_client(&mut self, engine: Engine, client: Option<LlmClient>) {
        match engine {
            Engine::LmStudio => self.lmstudio_connected = client.is_some(),
            Engine::Ollama => self.ollama_connected = client.is_some(),
            _ => {}
        }
        match client {
            Some(c) => self.llm.insert(engine.key(), c),
            None => self.llm.remove(engine.key()),
        };
    }

    pub fn settings_dir(&self) -> &Path {
        &self.settings_dir
    }

    pub fn llm_client(&self, engine: Engine) -> Option<&LlmClient> {
        self.llm.get(engine.key())
    }

    /// getLanguageCode: (source code, target code), None when a name is not in the table
    pub fn language_code(&self, translator: &str, weight_type: &str, target_country: &str, source_language: &str,
                         target_language: &str) -> Option<(String, String)> {
        let mut target = target_language;
        let table = match translator {
            "DeepL_API" => {
                target = match target_language {
                    "English" if ["United States", "Canada", "Philippines"].contains(&target_country) => "English American",
                    "English" => "English British",
                    "Portuguese" if target_country == "Portugal" => "Portuguese European",
                    "Portuguese" => "Portuguese Brazilian",
                    other => other,
                };
                &self.languages[translator]
            }
            "CTranslate2" => &self.languages[translator][weight_type],
            _ => &self.languages[translator],
        };
        let code = |side: &str, name: &str| table[side][name].as_str().map(String::from);
        Some((code("source", source_language)?, code("target", target)?))
    }

    /// translate(translator_name, weight_type, source, target, target_country, message,
    /// context_history)
    #[allow(clippy::too_many_arguments)]
    pub fn translate(&self, translator: &str, weight_type: &str, source_language: &str, target_language: &str,
                     target_country: &str, message: &str, context_history: &[HistoryItem]) -> Translation {
        if source_language == target_language {
            return Translation::Text(message.to_string());
        }
        let Some((source, target)) = self.language_code(translator, weight_type, target_country, source_language, target_language) else {
            return Translation::Unsupported;
        };
        #[cfg(test)]
        if let Some(fake) = self.fake {
            return fake(translator, target_language, message);
        }
        let result: Result<String> = match translator {
            "DeepL_API" => match &self.deepl {
                None => return Translation::Failed("DeepL is not authenticated".into()),
                Some(d) => d.translate(message, Some(&source), &target),
            },
            "Google" | "Bing" | "Papago" => vrct_webtranslate::translate_text(Some(message), &translator.to_lowercase(),
                Some(&source), Some(&target), Some(WEB_TRANSLATOR_TIMEOUT_SECONDS)).map_err(anyhow::Error::msg),
            "CTranslate2" => match &self.ctranslate2 {
                None => return Translation::Failed("no CTranslate2 model".into()),
                Some(t) => t.translate(message, &source, &target),
            },
            name => match self.llm.get(name) {
                None => return Translation::Failed(format!("{name} has no client")),
                Some(client) => {
                    if !context_history.is_empty() {
                        client.set_context_history(context_history.to_vec());
                    }
                    client.translate(message, &source, &target)
                }
            },
        };
        match result.context(translator.to_string()) {
            Ok(text) => Translation::Text(text),
            Err(e) => Translation::Failed(format!("{e:#}")),
        }
    }
}
