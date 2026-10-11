//! Local translation with CTranslate2 (NLLB / M2M100): `Translator.changeCTranslate2Model` and
//! `translateCTranslate2`, with the tokenizers that `transformers.AutoTokenizer` (4.40.2) loads for
//! them: NllbTokenizerFast (tokenizers 0.19.1) and M2M100Tokenizer (sentencepiece 0.2.1 +
//! vocab.json), ported call by call.
use crate::hf_cache;
use anyhow::{anyhow, bail, Context, Result};
use sentencepiece::SentencePieceProcessor;
use std::collections::{HashMap, HashSet};
use std::path::Path;
use vrct_ct2::{ModelConfig, TranslateOptions};

/// translation_utils.ctranslate2_weights
pub struct Weight {
    pub weight_type: &'static str,
    pub hf_repo: &'static str,
    pub directory_name: &'static str,
    pub tokenizer: &'static str,
}

pub const WEIGHTS: [Weight; 5] = [
    Weight { weight_type: "m2m100_418M-ct2-int8", hf_repo: "jncraton/m2m100_418M-ct2-int8",
             directory_name: "m2m100_418M-ct2-int8", tokenizer: "facebook/m2m100_418M" },
    Weight { weight_type: "m2m100_1.2B-ct2-int8", hf_repo: "jncraton/m2m100_1.2B-ct2-int8",
             directory_name: "m2m100_1.2B-ct2-int8", tokenizer: "facebook/m2m100_1.2B" },
    Weight { weight_type: "nllb-200-distilled-600M-ct2-int8", hf_repo: "JustFrederik/nllb-200-distilled-600M-ct2-int8",
             directory_name: "nllb-200-distilled-600M-ct2-int8", tokenizer: "facebook/nllb-200-distilled-600M" },
    Weight { weight_type: "nllb-200-distilled-1.3B-ct2-int8", hf_repo: "OpenNMT/nllb-200-distilled-1.3B-ct2-int8",
             directory_name: "nllb-200-distilled-1.3B-ct2-int8", tokenizer: "facebook/nllb-200-distilled-1.3B" },
    Weight { weight_type: "nllb-200-3.3B-ct2-int8", hf_repo: "OpenNMT/nllb-200-3.3B-ct2-int8",
             directory_name: "nllb-200-3.3B-ct2-int8", tokenizer: "facebook/nllb-200-3.3B" },
];

impl Weight {
    /// The files of `tokenizer` that `Ct2Translator::load` reads
    pub fn tokenizer_files(&self) -> &'static [&'static str] {
        if self.weight_type.starts_with("m2m100") { &["sentencepiece.bpe.model", "vocab.json"] } else { &["tokenizer.json"] }
    }
}

pub fn weight(weight_type: &str) -> Result<&'static Weight> {
    WEIGHTS.iter().find(|w| w.weight_type == weight_type).ok_or_else(|| anyhow!("unknown weight type {weight_type}"))
}

pub struct Ct2Translator {
    translator: vrct_ct2::Translator,
    tokenizer: Tokenizer,
}

enum Tokenizer {
    Nllb(Nllb),
    M2m100(M2m100),
}

impl Ct2Translator {
    /// changeCTranslate2Model(root, weight_type, device, device_index, compute_type) with the
    /// compute type already resolved ("auto" is getBestComputeType, `vrct_ct2::best_compute_type`).
    pub fn load(root: &Path, weight_type: &str, device: &str, device_index: i32, compute_type: &str) -> Result<Self> {
        let w = weight(weight_type)?;
        let dir = root.join("weights").join("ctranslate2").join(w.directory_name);
        let config = ModelConfig {
            device: device.into(),
            device_index,
            compute_type: compute_type.into(),
            inter_threads: 1,
            intra_threads: 4,
        };
        let translator = vrct_ct2::Translator::new(&dir, &config)?;
        let snapshot = hf_cache::snapshot_dir(&dir.join("tokenizer"), w.tokenizer)?;
        let tokenizer = if w.weight_type.starts_with("m2m100") {
            Tokenizer::M2m100(M2m100::load(&snapshot)?)
        } else {
            Tokenizer::Nllb(Nllb::load(&snapshot)?)
        };
        Ok(Self { translator, tokenizer })
    }

    /// translateCTranslate2(message, source_language, target_language). Python returns False where
    /// this returns an error.
    pub fn translate(&self, message: &str, source_language: &str, target_language: &str) -> Result<String> {
        let source = self.source_tokens(message, source_language)?;
        let prefix = self.target_prefix(target_language)?;
        let hypothesis = self.translate_tokens(&source, &prefix)?;
        self.decode(&hypothesis[1..])
    }

    /// `tokenizer.src_lang = source_language; convert_ids_to_tokens(encode(message))`
    pub fn source_tokens(&self, text: &str, source_language: &str) -> Result<Vec<String>> {
        match &self.tokenizer {
            Tokenizer::Nllb(t) => t.source_tokens(text, source_language),
            Tokenizer::M2m100(t) => t.source_tokens(text, source_language),
        }
    }

    /// M2M100: `[lang_code_to_token[target]]`, NLLB: `[target]`
    pub fn target_prefix(&self, target_language: &str) -> Result<Vec<String>> {
        match &self.tokenizer {
            Tokenizer::Nllb(_) => Ok(vec![target_language.to_string()]),
            Tokenizer::M2m100(_) => Ok(vec![M2m100::lang_token(target_language)?]),
        }
    }

    /// `translate_batch([source], target_prefix=[prefix])[0].hypotheses[0]`
    pub fn translate_tokens(&self, source: &[String], prefix: &[String]) -> Result<Vec<String>> {
        let mut hypotheses = self.translator.translate(source, prefix, &TranslateOptions::default())?;
        if hypotheses.is_empty() {
            bail!("no hypothesis");
        }
        Ok(hypotheses.swap_remove(0).tokens)
    }

    /// `decode(convert_tokens_to_ids(tokens))`
    pub fn decode(&self, tokens: &[String]) -> Result<String> {
        match &self.tokenizer {
            Tokenizer::Nllb(t) => t.decode(tokens),
            Tokenizer::M2m100(t) => t.decode(tokens),
        }
    }
}

/// PreTrainedTokenizerBase.clean_up_tokenization (clean_up_tokenization_spaces defaults to True)
fn clean_up_tokenization(s: &str) -> String {
    s.replace(" .", ".")
        .replace(" ?", "?")
        .replace(" !", "!")
        .replace(" ,", ",")
        .replace(" ' ", "'")
        .replace(" n't", "n't")
        .replace(" 'm", "'m")
        .replace(" 's", "'s")
        .replace(" 've", "'ve")
        .replace(" 're", "'re")
}

/// Python's str.isspace() for one character: Rust's White_Space plus U+001C..U+001F.
fn py_isspace(c: char) -> bool {
    c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c)
}

// ---- NLLB (NllbTokenizerFast, legacy_behaviour=False) ----------------------------------------

struct Nllb {
    tokenizer: tokenizers::Tokenizer,
    unk_id: u32,
}

impl Nllb {
    fn load(snapshot: &Path) -> Result<Self> {
        let tokenizer = tokenizers::Tokenizer::from_file(snapshot.join("tokenizer.json")).map_err(|e| anyhow!("{e}"))?;
        let unk_id = tokenizer.token_to_id("<unk>").context("<unk>")?;
        Ok(Self { tokenizer, unk_id })
    }

    /// convert_tokens_to_ids: unknown tokens are unk_token_id
    fn id(&self, token: &str) -> u32 {
        self.tokenizer.token_to_id(token).unwrap_or(self.unk_id)
    }

    fn token(&self, id: u32) -> Result<String> {
        self.tokenizer.id_to_token(id).with_context(|| format!("token id {id}"))
    }

    fn source_tokens(&self, text: &str, source_language: &str) -> Result<Vec<String>> {
        // set_src_lang_special_tokens: the post-processor becomes [src_lang_code] $A [</s>]
        let encoding = self.tokenizer.encode(text, false).map_err(|e| anyhow!("{e}"))?;
        let mut ids = vec![self.id(source_language)];
        ids.extend_from_slice(encoding.get_ids());
        ids.push(self.id("</s>"));
        ids.into_iter().map(|id| self.token(id)).collect()
    }

    fn decode(&self, tokens: &[String]) -> Result<String> {
        let ids: Vec<u32> = tokens.iter().map(|t| self.id(t)).collect();
        let text = self.tokenizer.decode(&ids, false).map_err(|e| anyhow!("{e}"))?;
        Ok(clean_up_tokenization(&text))
    }
}

// ---- M2M100 (M2M100Tokenizer, a slow tokenizer) ---------------------------------------------

/// FAIRSEQ_LANGUAGE_CODES["m2m100"]; the token of code i has the id len(vocab.json) + i.
const M2M100_LANGUAGES: [&str; 100] = [
    "af", "am", "ar", "ast", "az", "ba", "be", "bg", "bn", "br", "bs", "ca", "ceb", "cs", "cy", "da", "de", "el",
    "en", "es", "et", "fa", "ff", "fi", "fr", "fy", "ga", "gd", "gl", "gu", "ha", "he", "hi", "hr", "ht", "hu", "hy",
    "id", "ig", "ilo", "is", "it", "ja", "jv", "ka", "kk", "km", "kn", "ko", "lb", "lg", "ln", "lo", "lt", "lv", "mg",
    "mk", "ml", "mn", "mr", "ms", "my", "ne", "nl", "no", "ns", "oc", "or", "pa", "pl", "ps", "pt", "ro", "ru", "sd",
    "si", "sk", "sl", "so", "sq", "sr", "ss", "su", "sv", "sw", "ta", "th", "tl", "tn", "tr", "uk", "ur", "uz", "vi",
    "wo", "xh", "yi", "yo", "zh", "zu",
];

/// bos, pad, eos (= sep), unk
const M2M100_SPECIAL: [&str; 4] = ["<s>", "<pad>", "</s>", "<unk>"];

struct M2m100 {
    sp: SentencePieceProcessor,
    encoder: HashMap<String, u32>,
    decoder: HashMap<u32, String>,
    /// The added tokens (special tokens and language tokens) and their ids
    added: HashMap<String, u32>,
    added_by_id: HashMap<u32, String>,
    lang_tokens: HashSet<String>,
    unk_id: u32,
}

impl M2m100 {
    fn load(snapshot: &Path) -> Result<Self> {
        let sp = SentencePieceProcessor::open(snapshot.join("sentencepiece.bpe.model"))?;
        let vocab: serde_json::Map<String, serde_json::Value> =
            serde_json::from_slice(&std::fs::read(snapshot.join("vocab.json"))?)?;
        let mut encoder = HashMap::new();
        let mut decoder = HashMap::new();
        for (token, id) in vocab {
            let id = id.as_u64().context("vocab.json: id")? as u32;
            decoder.insert(id, token.clone()); // {v: k for k, v in encoder.items()}: the last one wins
            encoder.insert(token, id);
        }
        let mut added = HashMap::new();
        for token in M2M100_SPECIAL {
            added.insert(token.to_string(), *encoder.get(token).with_context(|| format!("vocab.json: {token}"))?);
        }
        let mut lang_tokens = HashSet::new();
        for (i, code) in M2M100_LANGUAGES.iter().enumerate() {
            let token = format!("__{code}__");
            added.insert(token.clone(), (encoder.len() + i) as u32);
            lang_tokens.insert(token);
        }
        let added_by_id = added.iter().map(|(t, &id)| (id, t.clone())).collect();
        let unk_id = added["<unk>"];
        Ok(Self { sp, encoder, decoder, added, added_by_id, lang_tokens, unk_id })
    }

    /// get_lang_token (KeyError for codes M2M100 does not have, e.g. "as" of the VRCT table)
    fn lang_token(code: &str) -> Result<String> {
        if M2M100_LANGUAGES.contains(&code) {
            Ok(format!("__{code}__"))
        } else {
            bail!("M2M100 has no language {code:?}")
        }
    }

    /// _convert_token_to_id_with_added_voc
    fn id(&self, token: &str) -> u32 {
        self.added.get(token).or_else(|| self.encoder.get(token)).copied().unwrap_or(self.unk_id)
    }

    /// convert_ids_to_tokens for one id
    fn token(&self, id: u32) -> &str {
        self.added_by_id.get(&id).or_else(|| self.decoder.get(&id)).map(String::as_str).unwrap_or("<unk>")
    }

    /// PreTrainedTokenizer.tokenize: split out the added tokens (tokens_trie.split, longest match
    /// first; none of them strips its neighbours), then sp_model.encode(chunk, out_type=str).
    fn tokenize(&self, text: &str) -> Result<Vec<String>> {
        let mut tokens = vec![];
        let mut chunk_start = 0;
        let mut i = 0;
        while i < text.len() {
            let found = self
                .added
                .keys()
                .filter(|t| text[i..].starts_with(t.as_str()))
                .max_by_key(|t| t.len());
            match found {
                Some(token) => {
                    self.encode_chunk(&text[chunk_start..i], &mut tokens)?;
                    tokens.push(token.clone());
                    i += token.len();
                    chunk_start = i;
                }
                None => i += text[i..].chars().next().unwrap().len_utf8(),
            }
        }
        self.encode_chunk(&text[chunk_start..], &mut tokens)?;
        Ok(tokens)
    }

    fn encode_chunk(&self, chunk: &str, tokens: &mut Vec<String>) -> Result<()> {
        if !chunk.is_empty() {
            tokens.extend(self.sp.encode(chunk)?.into_iter().map(|p| p.piece));
        }
        Ok(())
    }

    fn source_tokens(&self, text: &str, source_language: &str) -> Result<Vec<String>> {
        // set_src_lang_special_tokens: prefix [lang id], suffix [eos]; then ids back to tokens
        let mut ids = vec![self.id(&Self::lang_token(source_language)?)];
        ids.extend(self.tokenize(text)?.iter().map(|t| self.id(t)));
        ids.push(self.id("</s>"));
        Ok(ids.into_iter().map(|id| self.token(id).to_string()).collect())
    }

    /// PreTrainedTokenizer._decode(ids, skip_special_tokens=False, spaces_between_special_tokens=True)
    fn decode(&self, tokens: &[String]) -> Result<String> {
        // The language tokens have ids >= vocab_size, so they are "legacy added tokens": joined
        // with spaces instead of going through convert_tokens_to_string.
        let mut sub_texts: Vec<String> = vec![];
        let mut current: Vec<&str> = vec![];
        for token in tokens.iter().map(|t| self.token(self.id(t))) {
            if self.lang_tokens.contains(token) {
                if !current.is_empty() {
                    let s = self.tokens_to_string(&current)?;
                    if !s.is_empty() {
                        sub_texts.push(s);
                    }
                    current.clear();
                }
                sub_texts.push(token.to_string());
            } else {
                current.push(token);
            }
        }
        if !current.is_empty() {
            sub_texts.push(self.tokens_to_string(&current)?);
        }
        Ok(clean_up_tokenization(&sub_texts.join(" ")))
    }

    /// M2M100Tokenizer.convert_tokens_to_string
    fn tokens_to_string(&self, tokens: &[&str]) -> Result<String> {
        let mut out = String::new();
        let mut sub: Vec<&str> = vec![];
        for &token in tokens {
            if self.added.contains_key(token) {
                // all_special_tokens: the special and the language tokens
                out += &self.sp.decode_pieces(&sub)?;
                out += token;
                sub.clear();
            } else {
                sub.push(token);
            }
        }
        out += &self.sp.decode_pieces(&sub)?;
        Ok(out.trim_matches(py_isspace).to_string())
    }
}
