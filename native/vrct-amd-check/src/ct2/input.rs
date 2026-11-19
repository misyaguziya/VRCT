use super::ffi::Model;
use anyhow::{anyhow, ensure, Context, Result};
use std::path::Path;
use tokenizers::Tokenizer;

pub enum Input {
    Whisper {
        tokenizer: Tokenizer,
        features: crate::mel::PreparedMel,
        prompt: Vec<usize>,
    },
    Nllb {
        tokenizer: Tokenizer,
        source: Vec<String>,
    },
}

fn tokenizer(path: &Path) -> Result<Tokenizer> {
    Tokenizer::from_file(path)
        .map_err(|e| anyhow!("{e}"))
        .with_context(|| format!("read local tokenizer {}", path.display()))
}

fn id(tokenizer: &Tokenizer, token: &str) -> Result<u32> {
    tokenizer
        .token_to_id(token)
        .with_context(|| format!("tokenizer lacks {token}"))
}

impl Input {
    pub fn whisper(model: &Model<'_>, root: &Path, audio: &Path) -> Result<Self> {
        let (mels, multilingual) = model.whisper_info()?;
        ensure!(
            mels == crate::mel::N_MELS,
            "common-mel comparison requires a 128-mel Whisper model"
        );
        let features = crate::mel::PreparedMel::from_audio(audio)?;
        let tokenizer = tokenizer(&root.join("tokenizer.json"))?;
        let mut prompt = vec![id(&tokenizer, "<|startoftranscript|>")? as usize];
        if multilingual {
            prompt.push(id(&tokenizer, "<|en|>")? as usize);
            prompt.push(id(&tokenizer, "<|transcribe|>")? as usize);
        }
        prompt.push(id(&tokenizer, "<|notimestamps|>")? as usize);
        Ok(Self::Whisper {
            tokenizer,
            features,
            prompt,
        })
    }

    pub fn nllb(path: &Path) -> Result<Self> {
        let tokenizer = tokenizer(path)?;
        let source = nllb_source(&tokenizer, crate::config::SENTENCE)?;
        id(&tokenizer, "jpn_Jpan")?;
        Ok(Self::Nllb { tokenizer, source })
    }

    pub fn infer(&self, model: &Model<'_>) -> Result<serde_json::Value> {
        let (text, count) = match self {
            Self::Whisper {
                tokenizer,
                features,
                prompt,
            } => {
                let ids = model.transcribe(features.values(), crate::mel::N_MELS, prompt)?;
                let text = tokenizer.decode(&ids, true).map_err(|e| anyhow!("{e}"))?;
                (text.trim().to_owned(), ids.len())
            }
            Self::Nllb { tokenizer, source } => {
                let tokens = model.translate(source)?;
                ensure!(
                    tokens.first().is_some_and(|s| s == "jpn_Jpan"),
                    "NLLB hypothesis is missing the requested target prefix"
                );
                let text = nllb_decode(tokenizer, &tokens[1..])?;
                (text.trim().to_owned(), tokens.len() - 1)
            }
        };
        ensure!(
            !text.is_empty(),
            "CT2 returned an empty transcript/translation"
        );
        Ok(serde_json::json!({"text":text, "token_count":count}))
    }

    pub fn feature_metadata(&self) -> serde_json::Value {
        match self {
            Self::Whisper { features, .. } => features.metadata(),
            Self::Nllb { .. } => serde_json::Value::Null,
        }
    }
}

// Mirrors vrct-backend/src/translate/ctranslate2.rs, NllbTokenizerFast
// (legacy_behaviour=False). Only cache lookup/model management is omitted.
fn nllb_source(tokenizer: &Tokenizer, text: &str) -> Result<Vec<String>> {
    let encoding = tokenizer.encode(text, false).map_err(|e| anyhow!("{e}"))?;
    let mut ids = vec![id(tokenizer, "eng_Latn")?];
    ids.extend_from_slice(encoding.get_ids());
    ids.push(id(tokenizer, "</s>")?);
    ids.into_iter()
        .map(|id| tokenizer.id_to_token(id).context("NLLB token ID"))
        .collect()
}

fn nllb_decode(tokenizer: &Tokenizer, tokens: &[String]) -> Result<String> {
    let unk = id(tokenizer, "<unk>")?;
    let ids: Vec<_> = tokens
        .iter()
        .map(|t| tokenizer.token_to_id(t).unwrap_or(unk))
        .collect();
    let text = tokenizer.decode(&ids, false).map_err(|e| anyhow!("{e}"))?;
    Ok(text
        .replace(" .", ".")
        .replace(" ?", "?")
        .replace(" !", "!")
        .replace(" ,", ",")
        .replace(" ' ", "'")
        .replace(" n't", "n't")
        .replace(" 'm", "'m")
        .replace(" 's", "'s")
        .replace(" 've", "'ve")
        .replace(" 're", "'re"))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn nllb_uses_app_language_prefix_eos_and_cleanup() {
        let tokenizer = Tokenizer::from_bytes(br#"{
            "version":"1.0","truncation":null,"padding":null,"added_tokens":[],
            "normalizer":null,"pre_tokenizer":{"type":"Whitespace"},
            "post_processor":null,"decoder":null,
            "model":{"type":"WordLevel","vocab":{"<unk>":0,"eng_Latn":1,"</s>":2,"jpn_Jpan":3,"Hello":4,"?":5},"unk_token":"<unk>"}
        }"#).unwrap();
        assert_eq!(
            nllb_source(&tokenizer, "Hello?").unwrap(),
            ["eng_Latn", "Hello", "?", "</s>"]
        );
        assert_eq!(
            nllb_decode(&tokenizer, &["Hello".into(), "?".into()]).unwrap(),
            "Hello?"
        );
    }
}
