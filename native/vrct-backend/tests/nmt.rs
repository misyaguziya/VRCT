//! Tokenization, target prefixes and decoding are checked against the Python data in testdata/nmt/.
//! Hypotheses and translations are checked against tests/nmt-ct2-<ver>/. Review the output diffs
//! first, then rerun with VRCT_TEST_ACCEPT=1 to save the baselines for the available models.
//!
//! VRCT_WEIGHTS_ROOTS: folders holding weights/ctranslate2/<model> (';'-separated). Models not found
//! there are skipped (and say so). VRCT_TEST_CUDA=1 also runs the *-cuda.json data.
use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use vrct_backend::translate::ctranslate2::Ct2Translator;

// Must match third_party.toml. Re-accept the model outputs after a CT2 upgrade.
const CT2: &str = "ct2-4.9.0";

fn testdata() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../testdata/nmt")
}

fn weights_root(weight_type: &str) -> Option<PathBuf> {
    std::env::var("VRCT_WEIGHTS_ROOTS")
        .ok()?
        .split(';')
        .map(PathBuf::from)
        .find(|root| root.join("weights/ctranslate2").join(weight_type).join("model.bin").is_file())
}

fn strings(v: &Value) -> Vec<String> {
    v.as_array().unwrap().iter().map(|s| s.as_str().unwrap().to_string()).collect()
}

fn check_translations(file: &Path, translate: Vec<Value>, problems: &mut Vec<String>) {
    let dir = Path::new(env!("CARGO_MANIFEST_DIR")).join(format!("tests/nmt-{CT2}"));
    let path = dir.join(file.file_name().unwrap());
    // accepting always fails the run (never a silent pass) and writes nothing over other problems
    if std::env::var("VRCT_TEST_ACCEPT").is_ok_and(|v| v == "1") {
        if problems.is_empty() {
            std::fs::create_dir_all(dir).unwrap();
            let baseline = serde_json::to_string_pretty(&json!({ "translate": translate })).unwrap();
            std::fs::write(&path, format!("{baseline}\n")).unwrap();
            problems.push(format!("accepted {}; run again without VRCT_TEST_ACCEPT", path.display()));
        } else {
            problems.push(format!("not accepted {}: fix the problems above first", path.display()));
        }
        return;
    }
    if !path.try_exists().unwrap() {
        problems.push(format!("no {CT2} baseline for {}; run with VRCT_TEST_ACCEPT=1 after checking the outputs", file.display()));
        return;
    }
    let baseline: Value = serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap();
    let expected = baseline["translate"].as_array().unwrap();
    if translate.len() != expected.len() {
        problems.push(format!("{}: translate case count {} != {}", file.display(), translate.len(), expected.len()));
    }
    for (i, (got, want)) in translate.iter().zip(expected).enumerate() {
        if ["text", "source_language", "target_language"].iter().any(|&key| got[key] != want[key]) {
            problems.push(format!("{}: translate case {i} text or languages differ from the {CT2} baseline", file.display()));
            continue;
        }
        let (text, src, tgt) = (&got["text"], got["source_language"].as_str().unwrap(), got["target_language"].as_str().unwrap());
        if got["hypothesis"] != want["hypothesis"] {
            problems.push(format!("hypothesis {text} {src}->{tgt}: {} != {}", got["hypothesis"], want["hypothesis"]));
        }
        if got["result"] != want["result"] {
            problems.push(format!("translate {text} {src}->{tgt}: {} != {}", got["result"], want["result"]));
        }
    }
}

fn check(file: &Path) -> Vec<String> {
    let data: Value = serde_json::from_slice(&std::fs::read(file).unwrap()).unwrap();
    let weight_type = data["weight_type"].as_str().unwrap();
    let Some(root) = weights_root(weight_type) else {
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
    let mut translate = Vec::new();
    for case in data["translate"].as_array().unwrap() {
        let (text, src, tgt) = (case["text"].as_str().unwrap(), case["source_language"].as_str().unwrap(),
                                case["target_language"].as_str().unwrap());
        let prefix = t.target_prefix(tgt).unwrap();
        if prefix != strings(&case["target_prefix"]) {
            problems.push(format!("target_prefix {tgt}: {prefix:?} != {}", case["target_prefix"]));
        }
        let hypothesis = t.translate_tokens(&strings(&case["source_tokens"]), &prefix).unwrap();
        let result = t.translate(text, src, tgt).unwrap();
        translate.push(json!({ "text": text, "source_language": src, "target_language": tgt,
                               "hypothesis": hypothesis, "result": result }));
    }
    for case in data["decode"].as_array().unwrap() {
        let got = t.decode(&strings(&case["tokens"])).unwrap();
        if got != case["text"].as_str().unwrap() {
            problems.push(format!("decode {}: {got:?} != {}", case["tokens"], case["text"]));
        }
    }
    check_translations(file, translate, &mut problems);
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
