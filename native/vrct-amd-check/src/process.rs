use anyhow::{ensure, Context, Result};
use serde::{Deserialize, Serialize};
use std::io::{Read, Write};
use std::os::windows::{io::AsRawHandle, process::CommandExt};
use std::process::{Command, ExitStatus, Stdio};
use std::thread::{self, JoinHandle};
use std::time::{Duration, Instant};
use windows_sys::Win32::Foundation::{CloseHandle, HANDLE};
use windows_sys::Win32::System::JobObjects::{
    AssignProcessToJobObject, CreateJobObjectW, JobObjectExtendedLimitInformation,
    SetInformationJobObject, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
};
use windows_sys::Win32::System::Threading::CREATE_NO_WINDOW;

pub const RESULT_MARKER: &str = "VRCT_RESULT_JSON:";

#[derive(Clone, Copy)]
enum Tee {
    Stdout,
    Stderr,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct Captured {
    pub exit_code: Option<i32>,
    pub exit_hex: Option<String>,
    pub timed_out: bool,
    pub wall_seconds: f64,
    pub stdout: String,
    pub stderr: String,
}

impl Captured {
    pub fn success(&self) -> bool {
        !self.timed_out && self.exit_code == Some(0)
    }
}

// 先頭のデバイス情報と末尾の障害情報を残し、無制限のログで親を落とさない。
fn reader(
    mut pipe: impl Read + Send + 'static,
    limit: usize,
    tee: Option<Tee>,
) -> JoinHandle<Result<String>> {
    thread::spawn(move || {
        let mut collected = Vec::new();
        let mut chunk = [0; 8192];
        let mut truncated = false;
        loop {
            let count = pipe.read(&mut chunk)?;
            if count == 0 {
                break;
            }
            // 孫がハングして子ごと終了しても、親が直前のログを保持できるよう逐次転送する。
            if let Some(destination) = tee {
                // 読み取り境界へ文字を挟むとホーム/名前が分断され、最後の伏せ字処理が漏れる。
                match destination {
                    Tee::Stdout => {
                        let mut stream = std::io::stdout().lock();
                        let _ = stream.write_all(&chunk[..count]);
                        let _ = stream.flush();
                    }
                    Tee::Stderr => {
                        let mut stream = std::io::stderr().lock();
                        let _ = stream.write_all(&chunk[..count]);
                        let _ = stream.flush();
                    }
                }
            }
            collected.extend_from_slice(&chunk[..count]);
            if collected.len() > limit {
                let excess = collected.len() - limit;
                collected.drain(limit / 2..limit / 2 + excess);
                truncated = true;
            }
        }
        if truncated {
            collected.splice(
                limit / 2..limit / 2,
                b"\n[output truncated]\n".iter().copied(),
            );
        }
        Ok(String::from_utf8_lossy(&collected).into_owned())
    })
}

fn collect(reader: JoinHandle<Result<String>>) -> String {
    match reader.join() {
        Ok(Ok(s)) => s,
        Ok(Err(e)) => format!("[could not read child output: {e:#}]"),
        Err(_) => "[child output reader panicked]".into(),
    }
}

struct Job(HANDLE);
impl Job {
    fn new() -> Result<Self> {
        // 全ての孫プロセスも終了させる。標準入力の合図前に Job へ所属させる。
        let handle = unsafe { CreateJobObjectW(std::ptr::null(), std::ptr::null()) };
        ensure!(
            !handle.is_null(),
            "CreateJobObjectW: {}",
            std::io::Error::last_os_error()
        );
        let job = Self(handle);
        let mut limits: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = unsafe { std::mem::zeroed() };
        limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        let ok = unsafe {
            SetInformationJobObject(
                handle,
                JobObjectExtendedLimitInformation,
                (&limits as *const JOBOBJECT_EXTENDED_LIMIT_INFORMATION).cast(),
                std::mem::size_of_val(&limits) as u32,
            )
        };
        ensure!(
            ok != 0,
            "SetInformationJobObject: {}",
            std::io::Error::last_os_error()
        );
        Ok(job)
    }
}
impl Drop for Job {
    fn drop(&mut self) {
        unsafe {
            CloseHandle(self.0);
        }
    }
}

pub fn offline_command(exe: &std::path::Path, cwd: &std::path::Path) -> Command {
    let mut cmd = Command::new(exe);
    cmd.current_dir(cwd).creation_flags(CREATE_NO_WINDOW);
    // モデル取得や RPC を有効にする llama の引数環境変数を継承しない。
    for (key, _) in std::env::vars_os() {
        if key
            .to_string_lossy()
            .to_ascii_uppercase()
            .starts_with("LLAMA_ARG_")
        {
            cmd.env_remove(key);
        }
    }
    cmd.env("HF_HUB_OFFLINE", "1")
        .env("HF_DATASETS_OFFLINE", "1")
        .env("TRANSFORMERS_OFFLINE", "1")
        .env("HTTP_PROXY", "http://127.0.0.1:9")
        .env("HTTPS_PROXY", "http://127.0.0.1:9")
        .env("ALL_PROXY", "http://127.0.0.1:9")
        .env("NO_PROXY", "");
    cmd
}

fn captured(
    status: ExitStatus,
    timed_out: bool,
    start: Instant,
    out: JoinHandle<Result<String>>,
    err: JoinHandle<Result<String>>,
) -> Captured {
    let wall_seconds = start.elapsed().as_secs_f64();
    Captured {
        exit_code: status.code(),
        exit_hex: status.code().map(|c| format!("0x{:08X}", c as u32)),
        timed_out,
        wall_seconds,
        stdout: collect(out),
        stderr: collect(err),
    }
}

pub fn isolated(cmd: &mut Command, timeout: Duration) -> Result<Captured> {
    let job = Job::new()?;
    let start = Instant::now();
    let mut child = cmd
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .context("start isolated diagnostic")?;
    let ok = unsafe { AssignProcessToJobObject(job.0, child.as_raw_handle()) };
    if ok == 0 {
        let error = std::io::Error::last_os_error();
        let _ = child.kill();
        let _ = child.wait();
        anyhow::bail!("Cannot safely isolate child (AssignProcessToJobObject): {error}");
    }
    let out = reader(
        child.stdout.take().context("stdout pipe")?,
        2 * 1024 * 1024,
        None,
    );
    let err = reader(
        child.stderr.take().context("stderr pipe")?,
        256 * 1024,
        None,
    );
    // 子はこの一文字を読むまで DLL ロードも孫プロセス起動もしない。
    if let Some(mut input) = child.stdin.take() {
        let _ = input.write_all(b"G");
    }
    let (status, timed_out) = loop {
        match child.try_wait() {
            Ok(Some(status)) => break (status, false),
            Ok(None) if start.elapsed() < timeout => thread::sleep(Duration::from_millis(20)),
            Ok(None) => {
                drop(job);
                let status = child.wait()?;
                return Ok(captured(status, true, start, out, err));
            }
            Err(error) => {
                drop(job);
                let _ = child.wait();
                return Err(error.into());
            }
        }
    };
    drop(job);
    Ok(captured(status, timed_out, start, out, err))
}

// 外部 CLI は既に Job 内にいる。親がこの処理全体を監視する。
pub fn external(cmd: &mut Command) -> Result<Captured> {
    let start = Instant::now();
    let mut child = cmd
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()?;
    let out = reader(
        child.stdout.take().context("stdout pipe")?,
        64 * 1024,
        Some(Tee::Stdout),
    );
    let err = reader(
        child.stderr.take().context("stderr pipe")?,
        64 * 1024,
        Some(Tee::Stderr),
    );
    Ok(captured(child.wait()?, false, start, out, err))
}

pub fn child_handshake() -> Result<()> {
    let mut go = [0];
    std::io::stdin()
        .read_exact(&mut go)
        .context("internal worker requires supervisor")?;
    ensure!(go == *b"G", "invalid supervisor handshake");
    // WER のダイアログ待ちを避け、例外コードを親に返す。
    unsafe {
        windows_sys::Win32::System::Diagnostics::Debug::SetErrorMode(0x0001 | 0x0002 | 0x8000);
        windows_sys::Win32::System::ErrorReporting::WerSetFlags(
            windows_sys::Win32::System::ErrorReporting::WER_FAULT_REPORTING_NO_UI,
        );
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn supervised_fixture() {
        if std::env::var_os("VRCT_CHILD_FIXTURE").is_none() {
            return;
        }
        child_handshake().unwrap();
        eprintln!("fixture error text");
        if std::env::var_os("VRCT_FIXTURE_CRASH").is_some() {
            std::process::exit(0xC0000005u32 as i32);
        }
        if std::env::var_os("VRCT_FIXTURE_EXTERNAL").is_some() {
            let exe = std::env::current_exe().unwrap();
            let mut cmd = offline_command(&exe, exe.parent().unwrap());
            cmd.args([
                "--exact",
                "process::tests::hanging_engine_fixture",
                "--nocapture",
            ])
            .env("VRCT_ENGINE_FIXTURE", "1");
            external(&mut cmd).unwrap();
        }
        if std::env::var_os("VRCT_FIXTURE_HANG").is_some() {
            std::thread::sleep(Duration::from_secs(20));
        }
    }

    #[test]
    fn hanging_engine_fixture() {
        if std::env::var_os("VRCT_ENGINE_FIXTURE").is_none() {
            return;
        }
        eprintln!("Vulkan device marker immediately before hang");
        print!(r"C:\Users\Fixture");
        std::io::stdout().flush().unwrap();
        std::thread::sleep(Duration::from_millis(100));
        println!(r"User\model.bin");
        std::thread::sleep(Duration::from_secs(20));
    }

    #[test]
    fn captures_child_output_and_enforces_deadline() {
        let exe = std::env::current_exe().unwrap();
        let make = || {
            let mut cmd = offline_command(&exe, exe.parent().unwrap());
            cmd.args([
                "--exact",
                "process::tests::supervised_fixture",
                "--nocapture",
            ])
            .env("VRCT_CHILD_FIXTURE", "1");
            cmd
        };
        let ok = isolated(&mut make(), Duration::from_secs(10)).unwrap();
        assert!(ok.success(), "{ok:?}");
        assert!(ok.stderr.contains("fixture error text"));
        let mut hanging = make();
        hanging.env("VRCT_FIXTURE_HANG", "1");
        let timeout = isolated(&mut hanging, Duration::from_millis(200)).unwrap();
        assert!(timeout.timed_out);
        assert!(timeout.wall_seconds < 5.0);
        let mut crash = make();
        crash.env("VRCT_FIXTURE_CRASH", "1");
        let crashed = isolated(&mut crash, Duration::from_secs(10)).unwrap();
        assert!(!crashed.success());
        assert_eq!(crashed.exit_hex.as_deref(), Some("0xC0000005"));
        assert!(crashed.stderr.contains("fixture error text"));
        let mut external_hang = make();
        external_hang.env("VRCT_FIXTURE_EXTERNAL", "1");
        let start = Instant::now();
        let timeout = isolated(&mut external_hang, Duration::from_secs(2)).unwrap();
        assert!(timeout.timed_out);
        assert!(
            timeout
                .stderr
                .contains("Vulkan device marker immediately before hang"),
            "{timeout:?}"
        );
        assert!(timeout.stdout.contains(r"C:\Users\FixtureUser\model.bin"));
        let redacted =
            crate::report::redact(&timeout.stdout, r"C:\Users\FixtureUser", "FixtureUser");
        assert!(!redacted.contains("FixtureUser"));
        assert!(redacted.contains("<HOME>"));
        assert!(start.elapsed() < Duration::from_secs(6));
    }

    #[test]
    fn log_capture_is_bounded_and_preserves_both_ends() {
        let mut input = vec![b'x'; 100_000];
        input[..5].copy_from_slice(b"START");
        input[99_997..].copy_from_slice(b"END");
        let text = collect(reader(std::io::Cursor::new(input), 16_384, None));
        assert!(text.starts_with("START") && text.ends_with("END"));
        assert!(text.contains("[output truncated]"));
        assert!(text.len() < 16_500);
    }
}
