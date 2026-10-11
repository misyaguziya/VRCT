//! Transliteration against the Python backend (native/testdata/translit/translit.json, written by
//! native/reference/export_translit.py): Sudachi's morphemes, analyze() with and without macrons,
//! and katakana_to_hepburn must all be identical.
//!
//! VRCT_SUDACHI_DICT: SudachiDict-full's system.dic (the venv's sudachidict_full/resources/system.dic).
//! The Sudachi part is skipped (and says so) without it.
use serde_json::Value;
use std::path::{Path, PathBuf};
use vrct_backend::translit::{katakana_to_hepburn, Part, Transliterator};

fn native() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("..")
}

fn parts(v: &Value) -> Vec<Part> {
    v.as_array()
        .unwrap()
        .iter()
        .map(|p| Part {
            orig: p["orig"].as_str().unwrap().into(),
            kana: p["kana"].as_str().unwrap().into(),
            hira: p["hira"].as_str().unwrap().into(),
            hepburn: p["hepburn"].as_str().unwrap().into(),
        })
        .collect()
}

#[test]
fn translit_matches_python() {
    let data: Value =
        serde_json::from_slice(&std::fs::read(native().join("testdata/translit/translit.json")).unwrap()).unwrap();
    let mut problems = vec![];
    for case in data["hepburn"].as_array().unwrap() {
        let kata = case["kata"].as_str().unwrap();
        for (macron, key) in [(false, "plain"), (true, "macron")] {
            let got = katakana_to_hepburn(kata, macron);
            if got != case[key].as_str().unwrap() {
                problems.push(format!("hepburn {kata:?} macron={macron}: {got:?} != {}", case[key]));
            }
        }
    }
    match std::env::var_os("VRCT_SUDACHI_DICT") {
        None => eprintln!("SKIPPED the Sudachi part: VRCT_SUDACHI_DICT is not set"),
        Some(dict) => {
            let t = Transliterator::new(&native().join("data/sudachi"), Path::new(&dict)).unwrap();
            for case in data["cases"].as_array().unwrap() {
                let text = case["text"].as_str().unwrap();
                let tokens: Vec<Value> =
                    t.tokens(text).unwrap().into_iter().map(|(s, r, p)| serde_json::json!([s, r, p])).collect();
                if tokens != case["tokens"].as_array().unwrap().as_slice() {
                    problems.push(format!("tokens {text:?}: {tokens:?} != {}", case["tokens"]));
                    continue;
                }
                for (macron, key) in [(false, "analyze"), (true, "analyze_macron")] {
                    let got = t.analyze(text, macron).unwrap();
                    if got != parts(&case[key]) {
                        problems.push(format!("analyze {text:?} macron={macron}: {got:?} != {}", case[key]));
                    }
                }
            }
        }
    }
    eprintln!("{} texts, {} katakana strings, problems {}", data["cases"].as_array().unwrap().len(),
              data["hepburn"].as_array().unwrap().len(), problems.len());
    for p in problems.iter().take(20) {
        eprintln!("{p}");
    }
    assert!(problems.is_empty(), "{} problems", problems.len());
}
