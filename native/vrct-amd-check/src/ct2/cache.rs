//! COMGR's Windows cache-pruning workaround, scoped to supervised CT2 workers.
use crate::report::{Check, Status};
use anyhow::{ensure, Result};
use serde_json::json;
use std::io::Write;
use std::process::Command;

pub const VARIABLE: &str = "AMD_COMGR_CACHE";
const MARKER: &str = "VRCT_CT2_COMGR_CACHE:";

pub fn configure(command: &mut Command, operation: &str) {
    if operation.starts_with("ct2-") {
        command.env(VARIABLE, "0");
    }
}

/// Called after the Job Object handshake, before dispatch can load vendor DLLs.
pub fn verify_before_load(operation: &str) -> Result<()> {
    if operation.starts_with("ct2-") {
        let disabled = std::env::var_os(VARIABLE).is_some_and(|v| v == "0");
        eprintln!(
            "{MARKER}{}",
            if disabled { "disabled" } else { "not_disabled" }
        );
        std::io::stderr().flush()?;
        ensure!(
            disabled,
            "CT2 worker requires AMD_COMGR_CACHE=0 before DLL load"
        );
    }
    Ok(())
}

/// Keep requested and observed state distinct, including crashes/spawn failures.
pub fn record(check: &mut Check, operation: &str) {
    if !operation.starts_with("ct2-") {
        return;
    }
    let stderr = check.data["isolation"]["stderr"].as_str().unwrap_or("");
    let observations: Vec<_> = stderr
        .lines()
        .filter_map(|line| line.strip_prefix(MARKER))
        .collect();
    let observed = match observations.as_slice() {
        ["disabled"] => Some(true),
        ["not_disabled"] => Some(false),
        _ => None,
    };
    let verified = observed == Some(true);
    if check.data.is_null() {
        check.data = json!({});
    }
    check.data["ct2_comgr_cache"] = json!({
        "environment_variable":VARIABLE,"configured_value":"0",
        "observed_disabled":observed,"verified_before_vendor_load":verified,
        "scope":"CT2 child process only",
        "reason":"Avoid ROCm LLVM cache-pruning failure on non-ASCII Windows paths"
    });
    if check.status == Status::Ok && !verified {
        check.status = Status::Fail;
        check.detail = "CT2 cache workaround was not verified before vendor DLL load".into();
    }
}

pub fn verified(check: &Check) -> bool {
    let value = &check.data["ct2_comgr_cache"];
    value["environment_variable"] == VARIABLE
        && value["configured_value"] == "0"
        && value["observed_disabled"] == true
        && value["verified_before_vendor_load"] == true
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    #[test]
    fn child_fixture() {
        if std::env::var_os("VRCT_COMGR_FIXTURE").is_none() {
            return;
        }
        crate::process::child_handshake().unwrap();
        verify_before_load("ct2-compute").unwrap();
        if std::env::var_os("VRCT_COMGR_CRASH").is_some() {
            std::process::exit(0xC0000409u32 as i32);
        }
    }

    #[test]
    fn overrides_conflicting_child_environment_and_preserves_crash_evidence() {
        let exe = std::env::current_exe().unwrap();
        for crash in [false, true] {
            let mut command = crate::process::offline_command(&exe, exe.parent().unwrap());
            command
                .args(["--exact", "ct2::cache::tests::child_fixture", "--nocapture"])
                .env("VRCT_COMGR_FIXTURE", "1")
                .env(VARIABLE, "1");
            if crash {
                command.env("VRCT_COMGR_CRASH", "1");
            }
            configure(&mut command, "ct2-whisper-float16");
            let capture = crate::process::isolated(&mut command, Duration::from_secs(10)).unwrap();
            assert_eq!(capture.success(), !crash);
            if crash {
                assert_eq!(capture.exit_hex.as_deref(), Some("0xC0000409"));
            }
            let status = if crash { Status::Fail } else { Status::Ok };
            let mut check = Check::new("fixture", status, "", json!({"isolation":capture}));
            record(&mut check, "ct2-whisper-float16");
            assert!(verified(&check));
            assert_eq!(check.status, status);
            let mut report = crate::report::Report::new();
            report.checks.push(check);
            assert!(report.text().contains("verified_before_vendor_load"));
            assert_eq!(
                serde_json::to_value(&report).unwrap()["checks"][0]["data"]["ct2_comgr_cache"]
                    ["observed_disabled"],
                true
            );
        }
    }

    #[test]
    fn only_ct2_children_are_configured_and_unobserved_state_is_not_success() {
        for operation in [
            "ct2-compute",
            "ct2-imports",
            "ct2-whisper-cpu-float32",
            "ct2-nllb-float16-concurrent",
            "hip",
            "environment",
            "whisper-resident-gpu",
            "llama-help",
        ] {
            let mut command = Command::new("fixture.exe");
            configure(&mut command, operation);
            assert_eq!(
                command
                    .get_envs()
                    .any(|(k, v)| k == VARIABLE && v == Some(std::ffi::OsStr::new("0"))),
                operation.starts_with("ct2-")
            );
            let mut check = Check::new(
                "fixture",
                Status::Fail,
                "spawn failed",
                serde_json::Value::Null,
            );
            record(&mut check, operation);
            assert_eq!(
                check.data.get("ct2_comgr_cache").is_some(),
                operation.starts_with("ct2-")
            );
            assert!(!verified(&check));
            if operation.starts_with("ct2-") {
                assert!(check.data["ct2_comgr_cache"]["observed_disabled"].is_null());
            }
        }
        for marker in [
            "",
            "VRCT_CT2_COMGR_CACHE:not_disabled\n",
            "VRCT_CT2_COMGR_CACHE:invalid\n",
            "VRCT_CT2_COMGR_CACHE:disabled\nVRCT_CT2_COMGR_CACHE:disabled\n",
        ] {
            let mut check = Check::new(
                "fixture",
                Status::Ok,
                "",
                json!({"isolation":{"stderr":marker}}),
            );
            record(&mut check, "ct2-compute");
            assert_eq!(check.status, Status::Fail);
            assert!(!verified(&check));
        }
    }
}
