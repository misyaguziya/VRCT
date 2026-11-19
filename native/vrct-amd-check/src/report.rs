use regex::RegexBuilder;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::fmt::Write;

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Status {
    Ok,
    Warn,
    Fail,
    Blocked,
    Skip,
}

impl Status {
    pub fn tag(self) -> &'static str {
        match self {
            Self::Ok => "OK",
            Self::Warn => "WARN",
            Self::Fail => "FAIL",
            Self::Blocked => "BLOCKED",
            Self::Skip => "SKIP",
        }
    }
}

#[derive(Debug, Deserialize, Serialize)]
pub struct Check {
    pub name: String,
    pub status: Status,
    pub detail: String,
    pub data: Value,
}

impl Check {
    pub fn new(name: &str, status: Status, detail: impl Into<String>, data: Value) -> Self {
        Self {
            name: name.into(),
            status,
            detail: detail.into(),
            data,
        }
    }
}

#[derive(Debug, Serialize)]
pub struct Report {
    pub schema_version: u32,
    pub diagnostic_version: &'static str,
    pub started_unix_seconds: u64,
    pub checks: Vec<Check>,
    pub decision: String,
}

impl Report {
    pub fn new() -> Self {
        Self {
            schema_version: 3,
            diagnostic_version: env!("CARGO_PKG_VERSION"),
            started_unix_seconds: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs(),
            checks: Vec::new(),
            decision: String::new(),
        }
    }

    pub fn text(&self) -> String {
        let mut out = format!(
            "VRCT -- AMD GPU check (issue #88)\nDiagnostic: {} / report schema {}\nStarted (Unix seconds): {}\n\
             This program does not send anything anywhere. It only writes local files.\n\
             It does not read or change VRCT settings.\n",
            self.diagnostic_version, self.schema_version, self.started_unix_seconds
        );
        for check in &self.checks {
            writeln!(
                out,
                "\n{}\n{}\n{}",
                "=".repeat(70),
                check.name,
                "=".repeat(70)
            )
            .unwrap();
            writeln!(
                out,
                "[{:4}] {}  -- {}",
                check.status.tag(),
                check.name,
                check.detail
            )
            .unwrap();
            if !check.data.is_null() {
                writeln!(
                    out,
                    "{}",
                    serde_json::to_string_pretty(&check.data).unwrap()
                )
                .unwrap();
            }
            if matches!(check.status, Status::Fail | Status::Blocked) {
                writeln!(out, "!! STOPPING HERE (this branch only): {}", check.detail).unwrap();
            }
        }
        writeln!(out, "\n{}\nSummary\n{}", "=".repeat(70), "=".repeat(70)).unwrap();
        writeln!(out, "{}", self.decision).unwrap();
        out.push_str(
            "Partial results are still genuinely useful -- please share the report.\n\
            Please read it before sharing. Paths are redacted, but do check.\n\
            Send vrct_amd_check_report.txt and vrct_amd_check_report.json, plus your GPU model,\n\
            Adrenalin driver version, and whether the HIP SDK was installed beforehand.\n",
        );
        out
    }
}

// JSON 全体を文字列置換するとエスケープが壊れるため、全てのキーと値を処理してから直列化する。
pub fn redact_value(value: &mut Value, home: &str, user: &str) {
    match value {
        Value::String(s) => *s = redact(s, home, user),
        Value::Array(a) => a.iter_mut().for_each(|v| redact_value(v, home, user)),
        Value::Object(o) => {
            let old = std::mem::take(o);
            for (k, mut v) in old {
                redact_value(&mut v, home, user);
                o.insert(redact(&k, home, user), v);
            }
        }
        _ => {}
    }
}

pub fn redact(text: &str, home: &str, user: &str) -> String {
    let mut out = text.to_string();
    let mut patterns = Vec::new();
    if !home.is_empty() {
        let back = home.replace('/', "\\");
        patterns.extend([
            (back.replace('\\', "\\\\"), "<HOME>"),
            (back.clone(), "<HOME>"),
            (back.replace('\\', "/"), "<HOME>"),
        ]);
    }
    // 旧スパイクと同じく、短すぎるユーザー名による一般語の破壊を避ける。
    if user.chars().count() > 2 {
        patterns.push((user.to_owned(), "<USER>"));
    }
    for (pattern, replacement) in patterns {
        let re = RegexBuilder::new(&regex::escape(&pattern))
            .case_insensitive(true)
            .build()
            .unwrap();
        // 既存の伏せ字を保存し、繰り返し処理しても変わらないようにする。
        let mut replaced = String::new();
        let mut rest = out.as_str();
        while let Some(pos) = [rest.find("<HOME>"), rest.find("<USER>")]
            .into_iter()
            .flatten()
            .min()
        {
            let (prefix, suffix) = rest.split_at(pos);
            replaced.push_str(&re.replace_all(prefix, replacement));
            replaced.push_str(&suffix[..6]);
            rest = &suffix[6..];
        }
        replaced.push_str(&re.replace_all(rest, replacement));
        out = replaced;
    }
    out
}

pub fn may_run(prerequisite: Status) -> bool {
    prerequisite == Status::Ok
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn redaction_covers_paths_errors_and_json_without_corrupting_it() {
        let home = r"C:\Users\Alice";
        let text = r#"C:\Users\Alice\x c:/users/ALICE/x C:\\Users\\Alice\\x Alice"#;
        let redacted = redact(text, home, "Alice");
        assert!(!redacted.to_lowercase().contains("alice"));
        assert_eq!(redact(&redacted, home, "Alice"), redacted);
        let mut v =
            json!({ "C:\\Users\\Alice": [text, { "error": "Alice crashed" }], "seconds": 1.2 });
        redact_value(&mut v, home, "Alice");
        let encoded = serde_json::to_string(&v).unwrap();
        assert_eq!(serde_json::from_str::<Value>(&encoded).unwrap(), v);
        assert!(!encoded.to_lowercase().contains("alice"));
        assert_eq!(redact("CPU", "", "ab"), "CPU");
        assert_eq!(redact("<HOME> <USER>", home, "HOME"), "<HOME> <USER>");
    }

    #[test]
    fn stage_gating_is_fail_closed_and_each_part_is_independent() {
        for status in [Status::Fail, Status::Warn, Status::Blocked, Status::Skip] {
            assert!(!may_run(status));
        }
        assert!(may_run(Status::Ok));
        // ROCm の失敗は Vulkan の前提条件に使わない。
        let rocm = Status::Fail;
        let vulkan_binaries = Status::Ok;
        assert!(!may_run(rocm) && may_run(vulkan_binaries));
    }

    #[test]
    fn report_keeps_python_wording_and_never_claims_blocked_work_passed() {
        let mut report = Report::new();
        report.checks.push(Check::new(
            "Stage C",
            Status::Blocked,
            "ABI mismatch",
            Value::Null,
        ));
        report.decision = "Inconclusive: no AMD shipping decision is justified.".into();
        let text = report.text();
        assert!(text.contains("[BLOCKED] Stage C"));
        assert!(text.contains("!! STOPPING HERE"));
        assert!(text.contains("Partial results are still genuinely useful"));
        assert!(text.contains("Inconclusive"));
        assert!(!text.contains("Everything ran"));
    }
}
