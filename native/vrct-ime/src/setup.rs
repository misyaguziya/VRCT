//! RIME's user folder as the keyboard sets it: the schemas to build, and VRCT's changes to them
//! (*.custom.yaml patches, the downloaded schemas themselves are not touched).
use anyhow::{Context, Result};
use std::path::Path;

/// The candidates on a page (the keyboard's candidate row)
pub const PAGE_SIZE: usize = 8;

/// The schemas RIME builds (each language's: Language::schema)
pub const SCHEMAS: [&str; 5] = ["jaroomaji", "luna_pinyin", "bopomofo", "cangjie5", "quick5"];

/// Zhuyin, Cangjie and Quick without what needs data not downloaded (the reverse lookups by
/// strokes / pinyin and their dictionaries, the user's phrases). Cangjie shows its radicals only
/// (its own format adds the letters after a tab).
const ZHUYIN_PATCH: &str = "patch:\n  schema/dependencies: []\n  engine/translators: [punct_translator, script_translator]\n";
const CANGJIE_PATCH: &str = "patch:\n  schema/dependencies: []\n  engine/translators: [punct_translator, table_translator]\n  abc_segmentor/extra_tags: []\n  translator/preedit_format:\n    - \"xlit|abcdefghijklmnopqrstuvwxyz|日月金木水火土竹戈十大中一弓人心手口尸廿山女田難卜符|\"\n";
const QUICK_PATCH: &str = "patch:\n  schema/dependencies: []\n  engine/translators: [punct_translator, script_translator]\n  abc_segmentor/extra_tags: []\n";

/// The files to write into the user folder before RIME builds: (name, contents)
pub fn user_files(shared: &Path) -> Result<Vec<(&'static str, String)>> {
    let schemas: String = SCHEMAS.iter().map(|s| format!("    - schema: {s}\n")).collect();
    let default = format!("patch:\n  schema_list:\n{schemas}  menu/page_size: {PAGE_SIZE}\n");
    Ok(vec![("default.custom.yaml", default), ("jaroomaji.custom.yaml", jaroomaji_patch(shared)?),
            ("vrct_jaroomaji.dict.yaml", japanese_dictionary(shared)?),
            ("bopomofo.custom.yaml", ZHUYIN_PATCH.into()), ("cangjie5.custom.yaml", CANGJIE_PATCH.into()),
            ("quick5.custom.yaml", QUICK_PATCH.into())])
}

/// Keep unrecognized consonants inside the same editable RIME composition. Without literal
/// syllables, script_translator stops at e.g. `kj` and never translates the following `fi`.
fn japanese_dictionary(shared: &Path) -> Result<String> {
    let path = shared.join("jaroomaji.dict.yaml");
    let source = std::fs::read_to_string(&path).with_context(|| path.display().to_string())?;
    let header = source.lines().take_while(|line| line.trim() != "...").collect::<Vec<_>>().join("\n");
    let mut dictionary: serde_yaml::Value = serde_yaml::from_str(&header)?;
    dictionary.as_mapping().context("Japanese dictionary has no header mapping")?;
    dictionary["name"] = "vrct_jaroomaji".into();
    // Code first prevents a literal # candidate from being parsed as a comment.
    dictionary["columns"] = serde_yaml::to_value(["code", "text", "weight"])?;
    let imports = dictionary["import_tables"].as_sequence_mut().context("Japanese dictionary has no import_tables")?;
    imports.push("jaroomaji".into());
    let mut out = format!("---\n{}...\n", serde_yaml::to_string(&dictionary)?);
    // n already spells ん, l spells ー. Keep these canonical readings and give real words
    // priority over the fallback. Uppercase input is handled outside RIME by Input.
    for c in "bcdfghjkmpqrstvwxyz".chars() {
        out += &format!("{c}\t{c}\t0\n");
    }
    for (glyph, code, group) in crate::punctuation::entries() {
        out += &format!("{code}\t{glyph}\t100000\n");
        for alternative in group.chars().filter(|&c| c != glyph) {
            out += &format!("{code}\t{alternative}\t1\n");
        }
    }
    Ok(out)
}

/// jaroomaji's rules, changed:
/// - its preedit_format turns every remaining consonant into っ. Recognize doubled consonants
///   and t + ch before syllables become kana, leaving unrelated consonants intact.
/// - single consonants must not spell xtu in the dictionary; Input expands valid gemination.
/// - ん is spelled nn and n only abbreviates it, so konnichiha reads こんいちは (nn + i) before
///   こんにちは (n + ni). n is made a full spelling of ん, and nn before a vowel shows as n + n.
fn jaroomaji_patch(shared: &Path) -> Result<String> {
    let path = shared.join("jaroomaji.schema.yaml");
    let schema: serde_yaml::Value = serde_yaml::from_str(&std::fs::read_to_string(&path).with_context(|| path.display().to_string())?)?;
    let mut out = String::from("patch:\n  translator/dictionary: vrct_jaroomaji\n  translator/prism: jaroomaji\n  translator/user_dict: jaroomaji\n");
    // Reserved dictionary spellings bypass punctuator auto-commit and support Unicode marks
    // (punct_segmentor only recognizes single-byte keys). Digits are inserted only by Input.
    out += "  speller/alphabet: abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-0123456789\n";
    for (key, rules, change) in [
        ("translator/preedit_format", &schema["translator"]["preedit_format"], shown as fn(&str) -> String),
        ("speller/algebra", &schema["speller"]["algebra"], n_spells_n),
    ] {
        let rules = rules.as_sequence().with_context(|| format!("jaroomaji has no {key}"))?;
        out += &format!("  {key}:\n");
        if key == "translator/preedit_format" {
            // RIME separates syllables with spaces. Join them before recognizing doubled
            // consonants, while kitte still contains tt (before te becomes て).
            out += "    - \"xform/ //\"\n";
            for rule in rules.iter().filter_map(|r| r.as_str()).filter_map(gemination) {
                out += &format!("    - {}\n", serde_yaml::to_string(&rule)?.trim_end());
            }
        }
        for rule in rules.iter().filter_map(|r| r.as_str()) {
            if key == "speller/algebra" && standalone_gemination(rule) {
                continue;
            }
            if key == "translator/preedit_format" && (rule == "xform/ //" || gemination(rule).is_some()) {
                continue;
            }
            out += &format!("    - {}\n", serde_yaml::to_string(&change(rule))?.trim_end());
        }
        if key == "translator/preedit_format" {
            // Expand literal symbols last: '-' must not be changed by the kana long-vowel rule.
            // Different token delimiters prevent adjacent tokens from looking like gemination.
            for (glyph, code, _) in crate::punctuation::entries() {
                let replacement = match glyph { '/' | '\\' | '$' => format!("\\{glyph}"), _ => glyph.to_string() };
                let rule = format!("xform/{code}/{replacement}/");
                out += &format!("    - {}\n", serde_yaml::to_string(&rule)?.trim_end());
            }
        }
    }
    Ok(out)
}

fn n_spells_n(rule: &str) -> String {
    if rule == "abbrev/nn/n/" { "derive/nn/n/".to_string() } else { rule.to_string() }
}

fn standalone_gemination(rule: &str) -> bool {
    let Some((from, to)) = rule.strip_prefix("derive/").and_then(|r| r.strip_suffix('/')).and_then(|r| r.split_once('/')) else {
        return false;
    };
    matches!(from, "xtu" | "XTU") && to.len() == 1 && to.chars().all(|c| c.is_ascii_alphabetic())
}

/// Doubled consonants and t + ch become small tsu before kana conversion.
fn gemination(rule: &str) -> Option<String> {
    let (from, to) = rule.strip_prefix("xform/")?.strip_suffix('/')?.split_once('/')?;
    let next = match from {
        "t" => "t|ch", // matcha: t + cha is another spelling of っちゃ
        "T" => "T|CH",
        _ => from,
    };
    (from.len() == 1 && from.chars().all(|c| c.is_ascii_alphabetic()) && matches!(to, "っ" | "ッ"))
        .then(|| format!("xform/{from}(?={next})/{to}/"))
}

/// "xform/nn/ん/" -> "xform/nn(?![aiueo])/ん/" (konnichiha: ko n ni..., kanna: ka n na); the
/// katakana (Shift) rules alike
fn shown(rule: &str) -> String {
    let Some((from, to)) = rule.strip_prefix("xform/").and_then(|r| r.strip_suffix('/')).and_then(|r| r.split_once('/')) else {
        return rule.to_string();
    };
    match (from, to) {
        ("nn", "ん") => "xform/nn(?![aiueo])/ん/".to_string(),
        ("NN", "ン") => "xform/NN(?![AIUEO])/ン/".to_string(),
        _ => rule.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_patch_changes_only_those_rules() {
        assert!(standalone_gemination("derive/xtu/k/"));
        assert!(standalone_gemination("derive/XTU/K/"));
        assert!(!standalone_gemination("derive/xtu/xtsu/"));
        assert_eq!(gemination("xform/k/っ/"), Some("xform/k(?=k)/っ/".into()));
        assert_eq!(gemination("xform/K/ッ/"), Some("xform/K(?=K)/ッ/".into()));
        assert_eq!(gemination("xform/t/っ/"), Some("xform/t(?=t|ch)/っ/".into()));
        assert_eq!(gemination("xform/xtsu/っ/"), None);
        assert_eq!(shown("xform/xtsu/っ/"), "xform/xtsu/っ/");
        assert_eq!(shown("xform/n/ん/"), "xform/n/ん/");
        assert_eq!(shown("xform/nn/ん/"), "xform/nn(?![aiueo])/ん/");
        let dir = std::env::temp_dir().join(format!("vrct-ime-setup-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join("jaroomaji.schema.yaml"),
                       "speller:\n  algebra:\n    - \"derive/ka/ca/\"\n    - \"abbrev/nn/n/\"\n    - \"derive/xtu/k/\"\n    - \"derive/XTU/K/\"\n    - \"derive/xtu/xtsu/\"\ntranslator:\n  preedit_format:\n    - \"xform/ //\"\n    - \"xform/ka/か/\"\n    - \"xform/k/っ/\"\n").unwrap();
        std::fs::write(dir.join("jaroomaji.dict.yaml"), "---\nname: jaroomaji\nimport_tables: [jaroomaji.kana_kigou]\n...\n").unwrap();
        let files = user_files(&dir).unwrap();
        let patch = &files.iter().find(|(n, _)| *n == "jaroomaji.custom.yaml").unwrap().1;
        let parsed: serde_yaml::Value = serde_yaml::from_str(patch).unwrap();
        assert_eq!(parsed["patch"]["translator/dictionary"].as_str(), Some("vrct_jaroomaji"));
        assert_eq!(parsed["patch"]["translator/prism"].as_str(), Some("jaroomaji"));
        assert_eq!(parsed["patch"]["translator/user_dict"].as_str(), Some("jaroomaji"));
        let rules = |key: &str| -> Vec<String> { parsed["patch"][key].as_sequence().unwrap().iter().map(|r| r.as_str().unwrap().to_string()).collect() };
        let preedit = rules("translator/preedit_format");
        assert_eq!(preedit.first().unwrap(), "xform/ //");
        assert_eq!(&preedit[1..3], ["xform/k(?=k)/っ/", "xform/ka/か/"]);
        assert!(entries_for_punctuation_are_present(&files));
        assert_eq!(rules("speller/algebra"), ["derive/ka/ca/", "derive/nn/n/", "derive/xtu/xtsu/"]);
        let dictionary = &files.iter().find(|(n, _)| *n == "vrct_jaroomaji.dict.yaml").unwrap().1;
        let (header, entries) = dictionary.split_once("...\n").unwrap();
        let header: serde_yaml::Value = serde_yaml::from_str(header).unwrap();
        assert_eq!(header["name"].as_str(), Some("vrct_jaroomaji"));
        assert_eq!(header["import_tables"].as_sequence().unwrap(), &vec![
            serde_yaml::Value::from("jaroomaji.kana_kigou"), serde_yaml::Value::from("jaroomaji")]);
        assert!(entries.contains("k\tk\t0\n") && entries.contains("f\tf\t0\n"));
        for c in "aiueonl".chars() {
            assert!(!entries.contains(&format!("{c}\t{c}\t")), "canonical reading {c}");
        }
        let _ = std::fs::remove_dir_all(&dir);
    }

    fn entries_for_punctuation_are_present(files: &[(&str, String)]) -> bool {
        let dictionary = &files.iter().find(|(name, _)| *name == "vrct_jaroomaji.dict.yaml").unwrap().1;
        crate::punctuation::entries().all(|(glyph, code, _)| dictionary.contains(&format!("{code}\t{glyph}\t100000\n")))
    }
}
