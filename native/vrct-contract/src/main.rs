//! IPC contract tests (docs/rust_backend_design_2026-10-11.md §8).
//!
//! The backend is driven only through its stdin / stdout, the way the UI does, so the same cases
//! run against the Python backend and the Rust sidecar:
//!
//!   vrct-contract run --python <python.exe> --src <src-python> --out <report.json>
//!   vrct-contract run --exe <VRCT-sidecar.exe> --out <report.json>
//!   vrct-contract compare <a.json> <b.json>
//!
//! `run` copies the backend into a fresh folder under native/target/contract-run/ (its config.json
//! and logs are written next to it, never into the real install), cuts it off from the network
//! with a dead proxy (the "offline" start, same every time), waits for
//! /run/initialization_complete, then sends cases/*.toml in order and records every answer.
//! `compare` checks two reports case by case with each case's rule (exact / shape / status).
use anyhow::{bail, Context, Result};
use base64::Engine;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::BTreeMap;
use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::mpsc::{self, Receiver, RecvTimeoutError};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

const INIT_TIMEOUT: Duration = Duration::from_secs(300);
const CASE_TIMEOUT: Duration = Duration::from_secs(90);
const WATCHDOG_FEED: Duration = Duration::from_secs(15);

#[derive(Deserialize, Serialize, Clone, Copy, PartialEq, Debug, Default)]
#[serde(rename_all = "lowercase")]
enum Rule {
    /// status and result are equal
    #[default]
    Exact,
    /// status is equal and result has the same JSON shape (types, object keys)
    Shape,
    /// only the status is equal
    Status,
}

#[derive(Deserialize, Serialize, Clone, Debug)]
struct Case {
    name: String,
    endpoint: String,
    /// JSON value sent as base64(JSON) in "data"; absent = null
    data: Option<Value>,
    /// sent verbatim as "data" instead (to test broken payloads)
    raw_data: Option<String>,
    #[serde(default)]
    rule: Rule,
    /// the status the backend must answer, checked on every run (not only in compare)
    expect_status: Option<u16>,
}

#[derive(Deserialize)]
struct CaseFile {
    #[serde(default)]
    case: Vec<Case>,
}

#[derive(Serialize, Deserialize)]
struct Answer {
    name: String,
    endpoint: String,
    status: Option<i64>,
    result: Value,
    /// endpoints of the pushes seen while waiting for this answer, in order
    pushes: Vec<String>,
    ms: u128,
}

#[derive(Serialize, Deserialize)]
struct Report {
    backend: String,
    cases: Vec<Case>,
    init: Value,
    init_ms: u128,
    answers: Vec<Answer>,
    stderr: Vec<String>,
    problems: Vec<String>,
}

fn crate_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

fn load_cases() -> Result<Vec<Case>> {
    let mut files: Vec<PathBuf> = fs::read_dir(crate_dir().join("cases"))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().is_some_and(|e| e == "toml"))
        .collect();
    files.sort();
    let mut cases = Vec::new();
    for f in files {
        let parsed: CaseFile = toml::from_str(&fs::read_to_string(&f)?).with_context(|| f.display().to_string())?;
        cases.extend(parsed.case);
    }
    Ok(cases)
}

// ------------------------------------------------------------------------------------- run dir

fn copy_tree(src: &Path, dst: &Path, skip: &[&str]) -> Result<()> {
    fs::create_dir_all(dst)?;
    for entry in fs::read_dir(src)? {
        let entry = entry?;
        let name = entry.file_name().to_string_lossy().to_string();
        if skip.contains(&name.as_str()) || name.ends_with(".log") || name == "config.json" {
            continue;
        }
        let (from, to) = (entry.path(), dst.join(&name));
        if entry.file_type()?.is_dir() {
            copy_tree(&from, &to, skip)?;
        } else {
            fs::copy(&from, &to)?;
        }
    }
    Ok(())
}

/// A directory junction (no admin rights needed) so the copy reads the real model weights.
fn junction(link: &Path, target: &Path) -> Result<()> {
    let status = Command::new("cmd")
        .args(["/C", "mklink", "/J"])
        .arg(link)
        .arg(target)
        .stdout(Stdio::null())
        .status()?;
    if !status.success() {
        bail!("mklink /J {} failed", link.display());
    }
    Ok(())
}

fn fresh_run_dir(name: &str) -> Result<PathBuf> {
    let dir = crate_dir().parent().unwrap().join("target").join("contract-run").join(name);
    if dir.exists() {
        // a junction inside is removed as a link (remove_dir), never followed
        for entry in fs::read_dir(&dir)? {
            let p = entry?.path();
            if fs::symlink_metadata(&p)?.file_type().is_symlink() || is_junction(&p) {
                fs::remove_dir(&p)?;
            }
        }
        fs::remove_dir_all(&dir)?;
    }
    fs::create_dir_all(&dir)?;
    Ok(dir)
}

fn is_junction(p: &Path) -> bool {
    use std::os::windows::fs::MetadataExt;
    const FILE_ATTRIBUTE_REPARSE_POINT: u32 = 0x400;
    fs::symlink_metadata(p).is_ok_and(|m| m.file_attributes() & FILE_ATTRIBUTE_REPARSE_POINT != 0)
}

// ------------------------------------------------------------------------------------- backend

struct Backend {
    child: Child,
    stdin: Arc<Mutex<ChildStdin>>,
    lines: Receiver<Value>,
    stderr: Arc<Mutex<Vec<String>>>,
}

impl Backend {
    fn spawn(mut cmd: Command) -> Result<Backend> {
        // offline, the same way on every run: a proxy nobody listens on
        for key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY"] {
            cmd.env(key, "http://127.0.0.1:9");
        }
        cmd.env("NO_PROXY", "").env("no_proxy", "").env("HF_HUB_OFFLINE", "1").env("PYTHONUNBUFFERED", "1");
        let mut child = cmd.stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped()).spawn()?;
        let stdin = Arc::new(Mutex::new(child.stdin.take().unwrap()));
        let (tx, lines) = mpsc::channel();
        let stdout = child.stdout.take().unwrap();
        std::thread::spawn(move || {
            for line in BufReader::new(stdout).lines().map_while(Result::ok) {
                if line.trim().is_empty() {
                    continue;
                }
                let value = serde_json::from_str(&line).unwrap_or_else(|_| json!({"unparsed": line}));
                if tx.send(value).is_err() {
                    break;
                }
            }
        });
        let stderr = Arc::new(Mutex::new(Vec::new()));
        let (err_pipe, sink) = (child.stderr.take().unwrap(), stderr.clone());
        std::thread::spawn(move || {
            for line in BufReader::new(err_pipe).lines().map_while(Result::ok) {
                sink.lock().unwrap().push(line);
            }
        });
        // the UI feeds the watchdog every 20 s from the start
        let feeder = stdin.clone();
        std::thread::spawn(move || loop {
            std::thread::sleep(WATCHDOG_FEED);
            if send(&feeder, "/run/feed_watchdog", None, None).is_err() {
                break;
            }
        });
        Ok(Backend { child, stdin, lines, stderr })
    }

    /// Next line that is not a log (348) or the watchdog feeder's answer.
    fn next(&self, deadline: Instant) -> Result<Option<Value>> {
        loop {
            let left = deadline.saturating_duration_since(Instant::now());
            match self.lines.recv_timeout(left) {
                Ok(v) => {
                    if v["status"] == 348 || v["endpoint"] == "/run/feed_watchdog" {
                        continue;
                    }
                    return Ok(Some(v));
                }
                Err(RecvTimeoutError::Timeout) => return Ok(None),
                Err(RecvTimeoutError::Disconnected) => bail!("backend exited"),
            }
        }
    }
}

fn send(stdin: &Mutex<ChildStdin>, endpoint: &str, data: Option<&Value>, raw: Option<&str>) -> Result<()> {
    let data = match (raw, data) {
        (Some(raw), _) => Value::String(raw.to_string()),
        (None, Some(v)) => Value::String(base64::engine::general_purpose::STANDARD.encode(serde_json::to_vec(v)?)),
        (None, None) => Value::Null,
    };
    let line = serde_json::to_string(&json!({"endpoint": endpoint, "data": data}))?;
    let mut w = stdin.lock().unwrap();
    writeln!(w, "{line}")?;
    w.flush()?;
    Ok(())
}

fn run(backend_name: &str, cmd: Command, out: &Path) -> Result<()> {
    let cases = load_cases()?;
    let mut problems = Vec::new();
    let backend = Backend::spawn(cmd)?;
    let started = Instant::now();
    let deadline = started + INIT_TIMEOUT;
    let init = loop {
        match backend.next(deadline)? {
            Some(v) if v["endpoint"] == "/run/initialization_complete" => break v["result"].clone(),
            Some(_) => continue,
            None => bail!("no /run/initialization_complete within {INIT_TIMEOUT:?}"),
        }
    };
    let init_ms = started.elapsed().as_millis();
    eprintln!("{backend_name}: initialized in {init_ms} ms, {} cases", cases.len());
    let mut answers = Vec::new();
    for case in &cases {
        let t = Instant::now();
        send(&backend.stdin, &case.endpoint, case.data.as_ref(), case.raw_data.as_deref())?;
        let mut pushes = Vec::new();
        let answer = loop {
            match backend.next(t + CASE_TIMEOUT)? {
                Some(v) if v["endpoint"] == case.endpoint.as_str() => break Some(v),
                Some(v) => pushes.push(v["endpoint"].as_str().unwrap_or("?").to_string()),
                None => break None,
            }
        };
        let (status, result) = match &answer {
            Some(v) => (v["status"].as_i64(), v["result"].clone()),
            None => {
                problems.push(format!("{}: no answer within {CASE_TIMEOUT:?}", case.name));
                (None, Value::Null)
            }
        };
        if let (Some(want), Some(got)) = (case.expect_status, status) {
            if want as i64 != got {
                problems.push(format!("{}: status {got}, expected {want}", case.name));
            }
        }
        if status == Some(500) {
            problems.push(format!("{}: 500 {result}", case.name));
        }
        answers.push(Answer { name: case.name.clone(), endpoint: case.endpoint.clone(), status, result, pushes,
                              ms: t.elapsed().as_millis() });
    }
    send(&backend.stdin, "/run/shutdown", None, None)?;
    let mut child = backend.child;
    let end = Instant::now() + Duration::from_secs(30);
    while child.try_wait()?.is_none() && Instant::now() < end {
        std::thread::sleep(Duration::from_millis(200));
    }
    if child.try_wait()?.is_none() {
        child.kill().ok(); // the UI closes the sidecar 2 s after /run/shutdown anyway
    }
    let stderr = backend.stderr.lock().unwrap().clone();
    let report = Report { backend: backend_name.to_string(), cases, init, init_ms, answers, stderr, problems };
    fs::write(out, serde_json::to_string_pretty(&report)?)?;
    println!("{backend_name}: {} answers, {} problems, {} stderr lines -> {}",
             report.answers.len(), report.problems.len(), report.stderr.len(), out.display());
    for p in &report.problems {
        println!("  problem: {p}");
    }
    for l in report.stderr.iter().take(20) {
        println!("  stderr: {l}");
    }
    Ok(())
}

// ------------------------------------------------------------------------------------- compare

fn shape(v: &Value) -> Value {
    match v {
        Value::Object(m) => Value::Object(m.iter().map(|(k, v)| (k.clone(), shape(v))).collect()),
        Value::Array(a) => json!(["array", a.first().map(shape)]),
        Value::String(_) => json!("string"),
        Value::Number(_) => json!("number"),
        Value::Bool(_) => json!("bool"),
        Value::Null => json!("null"),
    }
}

fn same(rule: Rule, a: (Option<i64>, &Value), b: (Option<i64>, &Value)) -> bool {
    a.0 == b.0
        && match rule {
            Rule::Exact => a.1 == b.1,
            Rule::Shape => shape(a.1) == shape(b.1),
            Rule::Status => true,
        }
}

fn compare(a: &Path, b: &Path) -> Result<bool> {
    let a: Report = serde_json::from_str(&fs::read_to_string(a)?)?;
    let b: Report = serde_json::from_str(&fs::read_to_string(b)?)?;
    let rules: BTreeMap<&str, Rule> = a.cases.iter().map(|c| (c.endpoint.as_str(), c.rule)).collect();
    let mut diffs = Vec::new();
    // the start-up bundle: every /get/data/* value, with the rule of that endpoint's case
    let (ia, ib) = (a.init.as_object(), b.init.as_object());
    if let (Some(ia), Some(ib)) = (ia, ib) {
        for key in ia.keys().chain(ib.keys().filter(|k| !ia.contains_key(*k))) {
            let rule = rules.get(key.as_str()).copied().unwrap_or_default();
            let (va, vb) = (ia.get(key).unwrap_or(&Value::Null), ib.get(key).unwrap_or(&Value::Null));
            if !ia.contains_key(key) || !ib.contains_key(key) || !same(rule, (Some(200), va), (Some(200), vb)) {
                diffs.push(format!("init {key}:\n    {}: {va}\n    {}: {vb}", a.backend, b.backend));
            }
        }
    }
    for (x, y) in a.answers.iter().zip(&b.answers) {
        let rule = a.cases.iter().find(|c| c.name == x.name).map(|c| c.rule).unwrap_or_default();
        if x.name != y.name {
            bail!("the reports ran different cases ({} / {})", x.name, y.name);
        }
        if !same(rule, (x.status, &x.result), (y.status, &y.result)) {
            diffs.push(format!("{} [{rule:?}]:\n    {}: {:?} {}\n    {}: {:?} {}", x.name, a.backend, x.status, x.result,
                               b.backend, y.status, y.result));
        }
    }
    if a.answers.len() != b.answers.len() {
        diffs.push(format!("answer count {} / {}", a.answers.len(), b.answers.len()));
    }
    for d in &diffs {
        println!("DIFF {d}");
    }
    println!("{} differences ({} cases, {} start-up values)", diffs.len(), a.answers.len(),
             a.init.as_object().map_or(0, |m| m.len()));
    Ok(diffs.is_empty())
}

// ------------------------------------------------------------------------------------- main

fn arg(args: &[String], flag: &str) -> Option<String> {
    args.iter().position(|a| a == flag).and_then(|i| args.get(i + 1)).cloned()
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match args.first().map(String::as_str) {
        Some("run") => {
            let out = PathBuf::from(arg(&args, "--out").context("--out")?);
            let name = arg(&args, "--name").unwrap_or_else(|| "backend".into());
            let dir = fresh_run_dir(&name)?;
            let cmd = if let Some(python) = arg(&args, "--python") {
                let src = PathBuf::from(arg(&args, "--src").context("--src")?);
                copy_tree(&src, &dir, &["weights", "__pycache__", ".venv", "test", "logs", ".pytest_cache"])?;
                if src.join("weights").exists() {
                    junction(&dir.join("weights"), &fs::canonicalize(src.join("weights"))?)?;
                }
                let mut cmd = Command::new(python);
                cmd.arg(dir.join("mainloop.py")).current_dir(&dir);
                // the branch's own builds of vrct_audio / vrct_graphics (tmp/native-site, tmp/graphics-site)
                if let Some(pythonpath) = arg(&args, "--pythonpath") {
                    cmd.env("PYTHONPATH", pythonpath);
                }
                cmd
            } else if let Some(exe) = arg(&args, "--exe") {
                let exe = PathBuf::from(exe);
                copy_tree(exe.parent().unwrap(), &dir, &["weights", "logs"])?;
                if let Some(weights) = arg(&args, "--weights") {
                    junction(&dir.join("weights"), Path::new(&weights))?;
                }
                let mut cmd = Command::new(dir.join(exe.file_name().unwrap()));
                cmd.current_dir(&dir);
                cmd
            } else {
                bail!("run needs --python <python.exe> --src <src-python>, or --exe <sidecar.exe>");
            };
            run(&name, cmd, &out)
        }
        Some("compare") => {
            let (a, b) = (args.get(1).context("a.json")?, args.get(2).context("b.json")?);
            if !compare(Path::new(a), Path::new(b))? {
                std::process::exit(1);
            }
            Ok(())
        }
        _ => bail!("usage: vrct-contract run (--python <py> --src <dir> [--pythonpath <p>] | --exe <exe> [--weights <dir>]) --name <n> --out <json>\n       vrct-contract compare <a.json> <b.json>"),
    }
}
