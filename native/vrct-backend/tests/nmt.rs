//! CTranslate2 translation against the Python backend (native/testdata/nmt/*.json, written by
//! native/reference/export_nmt.py): tokenization, the model's hypotheses and decoding must all be
//! identical.
//!
//! VRCT_WEIGHTS_ROOTS: folders holding weights/ctranslate2/<model> (';'-separated). Models not found
//! there are skipped (and say so). VRCT_TEST_CUDA=1 also runs the *-cuda.json data.
use serde_json::Value;
use std::path::{Path, PathBuf};
use vrct_backend::translate::ctranslate2::{weight, Ct2Translator};

fn testdata() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../testdata/nmt")
}

fn weights_root(directory_name: &str) -> Option<PathBuf> {
    std::env::var("VRCT_WEIGHTS_ROOTS")
        .ok()?
        .split(';')
        .map(PathBuf::from)
        .find(|root| root.join("weights/ctranslate2").join(directory_name).join("model.bin").is_file())
}

fn strings(v: &Value) -> Vec<String> {
    v.as_array().unwrap().iter().map(|s| s.as_str().unwrap().to_string()).collect()
}

fn check(file: &Path) -> Vec<String> {
    let data: Value = serde_json::from_slice(&std::fs::read(file).unwrap()).unwrap();
    let weight_type = data["weight_type"].as_str().unwrap();
    let Some(root) = weights_root(weight(weight_type).unwrap().directory_name) else {
        eprintln!("SKIPPED {}: no weights for {weight_type} in VRCT_WEIGHTS_ROOTS", file.display());
        return vec![];
    };
    let device = data["device"].as_str().unwrap();
    let t = Ct2Translator::load(&root, weight_type, device, 0, data["compute_type"].as_str().unwrap()).unwrap();
    let mut problems = vec![];
    for case in data["tokenize"].as_array().unwrap() {
        let (text, lang) = (case["text"].as_str().unwrap(), case["source_language"].as_str().unwrap());
        let got = t.source_tokens(text, lang);
        match (&got, case.get("error")) {
            (Err(_), Some(_)) => {}
            (Ok(tokens), None) if *tokens == strings(&case["tokens"]) => {}
            _ => problems.push(format!("tokenize {text:?} {lang}: {got:?} != {}", case.get("tokens").or(case.get("error")).unwrap())),
        }
    }
    for case in data["translate"].as_array().unwrap() {
        let (text, src, tgt) = (case["text"].as_str().unwrap(), case["source_language"].as_str().unwrap(),
                                case["target_language"].as_str().unwrap());
        let prefix = t.target_prefix(tgt).unwrap();
        assert_eq!(prefix, strings(&case["target_prefix"]));
        let hypothesis = t.translate_tokens(&strings(&case["source_tokens"]), &prefix).unwrap();
        if hypothesis != strings(&case["hypothesis"]) {
            problems.push(format!("hypothesis {text:?} {src}->{tgt}: {hypothesis:?} != {}", case["hypothesis"]));
        }
        let result = t.translate(text, src, tgt).unwrap();
        if result != case["result"].as_str().unwrap() {
            problems.push(format!("translate {text:?} {src}->{tgt}: {result:?} != {}", case["result"]));
        }
    }
    for case in data["decode"].as_array().unwrap() {
        let got = t.decode(&strings(&case["tokens"])).unwrap();
        if got != case["text"].as_str().unwrap() {
            problems.push(format!("decode {}: {got:?} != {}", case["tokens"], case["text"]));
        }
    }
    eprintln!("{}: tokenize {}, translate {}, decode {}, problems {}", file.display(),
              data["tokenize"].as_array().unwrap().len(), data["translate"].as_array().unwrap().len(),
              data["decode"].as_array().unwrap().len(), problems.len());
    problems
}

#[test]
fn nmt_matches_python() {
    let cuda = std::env::var("VRCT_TEST_CUDA").is_ok_and(|v| v == "1");
    let mut files: Vec<PathBuf> = std::fs::read_dir(testdata()).unwrap().map(|e| e.unwrap().path()).collect();
    files.sort();
    let mut problems = vec![];
    for file in files.iter().filter(|f| cuda || f.to_string_lossy().ends_with("-cpu.json")) {
        problems.extend(check(file));
    }
    for p in problems.iter().take(30) {
        eprintln!("{p}");
    }
    assert!(problems.is_empty(), "{} problems", problems.len());
}
