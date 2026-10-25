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
            ("bopomofo.custom.yaml", ZHUYIN_PATCH.into()), ("cangjie5.custom.yaml", CANGJIE_PATCH.into()),
            ("quick5.custom.yaml", QUICK_PATCH.into())])
}

/// jaroomaji's rules, changed:
/// - its preedit_format turns every consonant left alone into っ (for kitte's first t): the one
///   being typed at the end too ("nihong" shows にほんっ). Those rules skip the end here.
/// - ん is spelled nn and n only abbreviates it, so konnichiha reads こんいちは (nn + i) before
///   こんにちは (n + ni). n is made a full spelling of ん, and nn before a vowel shows as n + n.
fn jaroomaji_patch(shared: &Path) -> Result<String> {
    let path = shared.join("jaroomaji.schema.yaml");
    let schema: serde_yaml::Value = serde_yaml::from_str(&std::fs::read_to_string(&path).with_context(|| path.display().to_string())?)?;
    let mut out = String::from("patch:\n");
    for (key, rules, change) in [
        ("translator/preedit_format", &schema["translator"]["preedit_format"], shown as fn(&str) -> String),
        ("speller/algebra", &schema["speller"]["algebra"], n_spells_n),
    ] {
        let rules = rules.as_sequence().with_context(|| format!("jaroomaji has no {key}"))?;
        out += &format!("  {key}:\n");
        for rule in rules.iter().filter_map(|r| r.as_str()) {
            out += &format!("    - {}\n", serde_yaml::to_string(&change(rule))?.trim_end());
        }
    }
    Ok(out)
}

fn n_spells_n(rule: &str) -> String {
    if rule == "abbrev/nn/n/" { "derive/nn/n/".to_string() } else { rule.to_string() }
}

/// "xform/k/っ/" -> "xform/k(?!$)/っ/" (a consonant at the end is still being typed),
/// "xform/nn/ん/" -> "xform/nn(?![aiueo])/ん/" (konnichiha: ko n ni..., kanna: ka n na); the
/// katakana (Shift) rules alike
fn shown(rule: &str) -> String {
    let Some((from, to)) = rule.strip_prefix("xform/").and_then(|r| r.strip_suffix('/')).and_then(|r| r.split_once('/')) else {
        return rule.to_string();
    };
    match (from, to) {
        (c, "っ" | "ッ") if c.len() == 1 && c.chars().all(|c| c.is_ascii_alphabetic()) => format!("xform/{c}(?!$)/{to}/"),
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
        assert_eq!(shown("xform/k/っ/"), "xform/k(?!$)/っ/");
        assert_eq!(shown("xform/K/ッ/"), "xform/K(?!$)/ッ/");
        assert_eq!(shown("xform/xtsu/っ/"), "xform/xtsu/っ/");
        assert_eq!(shown("xform/n/ん/"), "xform/n/ん/");
        assert_eq!(shown("xform/nn/ん/"), "xform/nn(?![aiueo])/ん/");
        let dir = std::env::temp_dir().join(format!("vrct-ime-setup-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join("jaroomaji.schema.yaml"),
                       "speller:\n  algebra:\n    - \"derive/ka/ca/\"\n    - \"abbrev/nn/n/\"\ntranslator:\n  preedit_format:\n    - \"xform/ //\"\n    - \"xform/ka/か/\"\n    - \"xform/k/っ/\"\n").unwrap();
        let files = user_files(&dir).unwrap();
        let patch = &files.iter().find(|(n, _)| *n == "jaroomaji.custom.yaml").unwrap().1;
        let parsed: serde_yaml::Value = serde_yaml::from_str(patch).unwrap();
        let rules = |key: &str| -> Vec<String> { parsed["patch"][key].as_sequence().unwrap().iter().map(|r| r.as_str().unwrap().to_string()).collect() };
        assert_eq!(rules("translator/preedit_format"), ["xform/ //", "xform/ka/か/", "xform/k(?!$)/っ/"]);
        assert_eq!(rules("speller/algebra"), ["derive/ka/ca/", "derive/nn/n/"]);
        let _ = std::fs::remove_dir_all(&dir);
    }
}
