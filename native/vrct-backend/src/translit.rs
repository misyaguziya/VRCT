//! Readings of Japanese text: models/transliteration (Transliterator.analyze, the context rules and
//! katakana_to_hepburn) on sudachi.rs, which SudachiPy 0.6.10 is (full dictionary, SplitMode C).
//! Python counts and slices by code points, so the text is handled as chars.
use anyhow::{anyhow, Result};
use std::path::Path;
use std::sync::Arc;
use sudachi::analysis::stateless_tokenizer::StatelessTokenizer;
use sudachi::analysis::{Mode, Tokenize};
use sudachi::config::Config;
use sudachi::dic::dictionary::JapaneseDictionary;

/// One part of analyze()'s result.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Part {
    pub orig: String,
    pub kana: String,
    pub hira: String,
    pub hepburn: String,
}

pub struct Transliterator {
    tokenizer: StatelessTokenizer<Arc<JapaneseDictionary>>,
}

impl Transliterator {
    /// `dictionary.Dictionary(dict_type="full").create()`: SudachiPy's resources (sudachi.json,
    /// char.def, rewrite.def, unk.def; native/data/sudachi) and SudachiDict-full's system.dic.
    pub fn new(resource_dir: &Path, system_dic: &Path) -> Result<Self> {
        let config = Config::new(Some(resource_dir.join("sudachi.json")), Some(resource_dir.to_path_buf()),
                                 Some(system_dic.to_path_buf()))?;
        let dictionary = JapaneseDictionary::from_cfg(&config).map_err(|e| anyhow!("{e}"))?;
        Ok(Self { tokenizer: StatelessTokenizer::new(Arc::new(dictionary)) })
    }

    /// (surface, reading_form, part_of_speech) of each morpheme (tokenize(text, SplitMode.C))
    pub fn tokens(&self, text: &str) -> Result<Vec<(String, String, Vec<String>)>> {
        let morphemes = self.tokenizer.tokenize(text, Mode::C, false).map_err(|e| anyhow!("{e}"))?;
        Ok(morphemes
            .iter()
            .map(|m| (m.surface().to_string(), m.reading_form().to_string(), m.part_of_speech().to_vec()))
            .collect())
    }

    /// Transliterator.analyze(text, use_macron)
    pub fn analyze(&self, text: &str, use_macron: bool) -> Result<Vec<Part>> {
        let mut results = vec![];
        for (surface, reading, pos) in self.tokens(text)? {
            let reading = if pos.first().is_some_and(|p| ["記号", "補助記号", "空白"].contains(&p.as_str())) {
                surface.clone()
            } else {
                reading
            };
            if surface == reading {
                results.push(Part { orig: surface.clone(), kana: reading, hira: surface.clone(), hepburn: surface });
            } else if surface.chars().count() == 1 {
                let (hira, hepburn) = (kata_to_hira(&reading), katakana_to_hepburn(&reading, use_macron));
                results.push(Part { orig: surface, kana: reading, hira, hepburn });
            } else {
                results.extend(split_kanji_okurigana(&surface, &reading, use_macron));
            }
        }
        apply_context_rules(&mut results);
        // the rules may have rewritten kana: hira and hepburn are recomputed for every part with kana
        for part in results.iter_mut().filter(|p| !p.kana.is_empty()) {
            part.hira = kata_to_hira(&part.kana);
            part.hepburn = katakana_to_hepburn(&part.kana, use_macron);
        }
        Ok(results)
    }
}

fn is_kanji(c: char) -> bool {
    ('\u{4e00}'..='\u{9fff}').contains(&c)
}

/// Transliterator.kata_to_hira: ァ..ン shifted to the hiragana block
pub fn kata_to_hira(text: &str) -> String {
    text.chars()
        .map(|c| if ('ァ'..='ン').contains(&c) { char::from_u32(c as u32 - 0x60).unwrap() } else { c })
        .collect()
}

/// Transliterator.split_kanji_okurigana: the reading shared out over the kanji / non-kanji blocks.
fn split_kanji_okurigana(surface: &str, reading: &str, use_macron: bool) -> Vec<Part> {
    let mut blocks: Vec<(bool, String)> = vec![];
    for c in surface.chars() {
        match blocks.last_mut() {
            Some((kanji, part)) if *kanji == is_kanji(c) => part.push(c),
            _ => blocks.push((is_kanji(c), c.to_string())),
        }
    }
    let kana: Vec<char> = reading.chars().collect();
    let mut allocs: Vec<usize> = blocks.iter().map(|(_, p)| p.chars().count()).collect();
    let mut remaining = kana.len() as i64 - allocs.iter().sum::<usize>() as i64;
    if remaining > 0 {
        // one more for each kanji block, left to right, then round robin over all blocks
        for (i, (kanji, _)) in blocks.iter().enumerate() {
            if remaining <= 0 {
                break;
            }
            if *kanji {
                allocs[i] += 1;
                remaining -= 1;
            }
        }
        let mut i = 0;
        while remaining > 0 && !blocks.is_empty() {
            allocs[i] += 1;
            remaining -= 1;
            i = (i + 1) % blocks.len();
        }
    }
    if remaining < 0 {
        // shrink from the right, keeping at least one per block
        let mut need = (-remaining) as usize;
        for alloc in allocs.iter_mut().rev() {
            if need == 0 {
                break;
            }
            let take = if *alloc > 1 { (*alloc - 1).min(need) } else { 0 };
            *alloc -= take;
            need -= take;
        }
    }
    let mut pos = 0;
    blocks
        .into_iter()
        .zip(allocs)
        .map(|((_, orig), count)| {
            let part: String = kana[pos.min(kana.len())..(pos + count).min(kana.len())].iter().collect();
            pos += count;
            Part { orig, hira: kata_to_hira(&part), hepburn: katakana_to_hepburn(&part, use_macron), kana: part }
        })
        .collect()
}

/// transliteration_context_rules.apply_context_rules with DEFAULT_RULES (one rule): 何 reads ナン
/// before a word starting with タ..ド / ナ行, otherwise ナニ. hira / hepburn are cleared.
fn apply_context_rules(results: &mut [Part]) {
    const KANA_SET: &str = "タチツテトダヂヅデドナニヌネノ";
    for i in 0..results.len() {
        if results[i].orig != "何" {
            continue;
        }
        let condition = match results[i + 1..].iter().find(|p| !p.orig.is_empty()) {
            None => false,
            Some(next) => match next.kana.chars().next() {
                Some(first) => KANA_SET.contains(first),
                None => next.orig.chars().next().is_some_and(|c| ('ァ'..='ン').contains(&c) && KANA_SET.contains(c)),
            },
        };
        let entry = &mut results[i];
        entry.kana = if condition { "ナン" } else { "ナニ" }.to_string();
        entry.hira.clear();
        entry.hepburn.clear();
    }
}

fn base(c: char) -> Option<&'static str> {
    Some(match c {
        'ア' => "a", 'イ' => "i", 'ウ' => "u", 'エ' => "e", 'オ' => "o",
        'カ' => "ka", 'キ' => "ki", 'ク' => "ku", 'ケ' => "ke", 'コ' => "ko",
        'サ' => "sa", 'シ' => "shi", 'ス' => "su", 'セ' => "se", 'ソ' => "so",
        'タ' => "ta", 'チ' => "chi", 'ツ' => "tsu", 'テ' => "te", 'ト' => "to",
        'ナ' => "na", 'ニ' => "ni", 'ヌ' => "nu", 'ネ' => "ne", 'ノ' => "no",
        'ハ' => "ha", 'ヒ' => "hi", 'フ' => "fu", 'ヘ' => "he", 'ホ' => "ho",
        'マ' => "ma", 'ミ' => "mi", 'ム' => "mu", 'メ' => "me", 'モ' => "mo",
        'ヤ' => "ya", 'ユ' => "yu", 'ヨ' => "yo",
        'ラ' => "ra", 'リ' => "ri", 'ル' => "ru", 'レ' => "re", 'ロ' => "ro",
        'ワ' => "wa", 'ヲ' => "wo", 'ン' => "n",
        'ガ' => "ga", 'ギ' => "gi", 'グ' => "gu", 'ゲ' => "ge", 'ゴ' => "go",
        'ザ' => "za", 'ジ' => "ji", 'ズ' => "zu", 'ゼ' => "ze", 'ゾ' => "zo",
        'ダ' => "da", 'ヂ' => "ji", 'ヅ' => "zu", 'デ' => "de", 'ド' => "do",
        'バ' => "ba", 'ビ' => "bi", 'ブ' => "bu", 'ベ' => "be", 'ボ' => "bo",
        'パ' => "pa", 'ピ' => "pi", 'プ' => "pu", 'ペ' => "pe", 'ポ' => "po",
        'ァ' => "a", 'ィ' => "i", 'ゥ' => "u", 'ェ' => "e", 'ォ' => "o",
        'ャ' => "ya", 'ュ' => "yu", 'ョ' => "yo", 'ッ' => "xtsu", 'ー' => "-",
        'ヴ' => "vu",
        _ => return None,
    })
}

fn digraph(a: char, b: char) -> Option<&'static str> {
    Some(match (a, b) {
        ('キ', 'ャ') => "kya", ('キ', 'ュ') => "kyu", ('キ', 'ョ') => "kyo",
        ('ギ', 'ャ') => "gya", ('ギ', 'ュ') => "gyu", ('ギ', 'ョ') => "gyo",
        ('シ', 'ャ') => "sha", ('シ', 'ュ') => "shu", ('シ', 'ョ') => "sho",
        ('ジ', 'ャ') => "ja", ('ジ', 'ュ') => "ju", ('ジ', 'ョ') => "jo",
        ('チ', 'ャ') => "cha", ('チ', 'ュ') => "chu", ('チ', 'ョ') => "cho",
        ('ニ', 'ャ') => "nya", ('ニ', 'ュ') => "nyu", ('ニ', 'ョ') => "nyo",
        ('ヒ', 'ャ') => "hya", ('ヒ', 'ュ') => "hyu", ('ヒ', 'ョ') => "hyo",
        ('ビ', 'ャ') => "bya", ('ビ', 'ュ') => "byu", ('ビ', 'ョ') => "byo",
        ('ピ', 'ャ') => "pya", ('ピ', 'ュ') => "pyu", ('ピ', 'ョ') => "pyo",
        ('ミ', 'ャ') => "mya", ('ミ', 'ュ') => "myu", ('ミ', 'ョ') => "myo",
        ('リ', 'ャ') => "rya", ('リ', 'ュ') => "ryu", ('リ', 'ョ') => "ryo",
        ('フ', 'ャ') => "fya", ('フ', 'ュ') => "fyu", ('フ', 'ョ') => "fyo",
        ('ト', 'ゥ') => "tu", ('ド', 'ゥ') => "du",
        ('フ', 'ァ') => "fa", ('フ', 'ィ') => "fi", ('フ', 'ェ') => "fe", ('フ', 'ォ') => "fo",
        ('シ', 'ェ') => "she", ('チ', 'ェ') => "che",
        ('テ', 'ィ') => "ti",
        ('ウ', 'ァ') => "wa", ('ウ', 'ィ') => "wi", ('ウ', 'ェ') => "we", ('ウ', 'ォ') => "wo",
        ('ス', 'ィ') => "si", ('ズ', 'ィ') => "zi", ('ツ', 'ァ') => "tsa", ('ツ', 'ィ') => "tsi", ('ツ', 'ェ') => "tse",
        ('ツ', 'ォ') => "tso",
        ('キ', 'ェ') => "kye", ('ギ', 'ェ') => "gye",
        ('ヴ', 'ァ') => "va", ('ヴ', 'ィ') => "vi", ('ヴ', 'ェ') => "ve", ('ヴ', 'ォ') => "vo", ('ヴ', 'ュ') => "vyu",
        _ => return None,
    })
}

/// Python's str.isspace() for one character: Rust's White_Space plus U+001C..U+001F.
fn py_isspace(c: char) -> bool {
    c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c)
}

/// katakana_to_hepburn(kata, use_macron)
pub fn katakana_to_hepburn(kata: &str, use_macron: bool) -> String {
    const SMALL: &str = "ャュョァィゥェォヮヵヶッ";
    let k: Vec<char> = kata.trim_matches(py_isspace).chars().collect();
    let mut res = String::new();
    let mut i = 0;
    while i < k.len() {
        let c = k[i];
        if c == 'ッ' {
            // sokuon: the first letter of the next sound's consonant
            if i + 1 < k.len() {
                let next = if i + 2 < k.len() && digraph(k[i + 1], k[i + 2]).is_some() {
                    digraph(k[i + 1], k[i + 2])
                } else {
                    base(k[i + 1])
                };
                if let Some(next) = next {
                    let consonant = next.find(|ch| "aeiou".contains(ch)).map_or(next, |p| &next[..p]);
                    if let Some(first) = consonant.chars().next() {
                        res.push(first);
                    }
                }
            }
            i += 1;
        } else if c == 'ー' {
            res.push('-');
            i += 1;
        } else if let Some(d) = (i + 1 < k.len()).then(|| digraph(c, k[i + 1])).flatten() {
            res.push_str(d);
            i += 2;
        } else if SMALL.contains(c) {
            res.push_str(base(c).unwrap_or(""));
            i += 1;
        } else {
            match base(c) {
                Some(b) => res.push_str(b),
                None => res.push(c),
            }
            i += 1;
        }
    }
    // re.sub(r'n(?=[bmp])', 'm', raw)
    let chars: Vec<char> = res.chars().collect();
    let raw: Vec<char> = chars
        .iter()
        .enumerate()
        .map(|(i, &c)| if c == 'n' && chars.get(i + 1).is_some_and(|n| "bmp".contains(*n)) { 'm' } else { c })
        .collect();
    // '-' lengthens the vowel before it, and is dropped elsewhere
    let mut out: Vec<char> = Vec::with_capacity(raw.len());
    for c in raw {
        if c != '-' {
            out.push(c);
        } else if let Some(&prev) = out.last() {
            if "aiueo".contains(prev) {
                out.push(prev);
            }
        }
    }
    let mut raw: String = out.into_iter().collect();
    if use_macron {
        for (pair, macron) in [("aa", "ā"), ("ii", "ī"), ("uu", "ū"), ("ee", "ē"), ("oo", "ō"), ("ou", "ō")] {
            raw = raw.replace(pair, macron);
        }
    }
    raw.to_lowercase()
}

/// model.convertMessageToTransliteration: orig plus hira and / or hepburn of each part.
pub fn convert_message(t: &Transliterator, message: &str, hiragana: bool, romaji: bool) -> Result<Vec<serde_json::Value>> {
    if !hiragana && !romaji {
        return Ok(vec![]);
    }
    Ok(t.analyze(message, false)?
        .into_iter()
        .map(|p| {
            let mut item = serde_json::Map::new();
            item.insert("orig".into(), p.orig.into());
            if hiragana {
                item.insert("hira".into(), p.hira.into());
            }
            if romaji {
                item.insert("hepburn".into(), p.hepburn.into());
            }
            item.into()
        })
        .collect())
}
