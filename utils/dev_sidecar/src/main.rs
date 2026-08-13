// Dev-time sidecar wrapper.
//
// Tauri's externalBin requires a real executable at
// src-tauri/bin/VRCT-sidecar-<triple>.exe. In release builds that slot is
// filled by the PyInstaller-frozen backend. During development, packaging
// the Python backend every iteration costs minutes; instead this wrapper
// is dropped into that slot and launches the venv Python interpreter
// against src-python/mainloop.py directly, so a Python edit only costs a
// process restart.
//
// Behaviour parity with the frozen backend:
//   - stdin/stdout/stderr are inherited so the Tauri <-> sidecar JSON
//     protocol works unchanged.
//   - Python is invoked with `-u` for unbuffered IO (matching the
//     PyInstaller runtime's flush behaviour).
//   - The working directory is set to src-python/ so the existing
//     `_internal/...` -> source-tree path fallbacks resolve to the dev
//     tree.
//
// On Windows the wrapper also puts itself into a Job Object with
// KILL_ON_JOB_CLOSE. When Tauri terminates the sidecar process, the Job
// closes and the child Python process is killed with it, preventing
// orphaned interpreters after a dev restart.

use std::env;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

fn main() {
    #[cfg(windows)]
    unsafe {
        install_kill_on_close_job();
    }

    let self_exe = match env::current_exe() {
        Ok(p) => p,
        Err(e) => {
            eprintln!("dev-sidecar: failed to resolve current_exe: {e}");
            std::process::exit(127);
        }
    };

    // The exe may be executed from any of:
    //   <root>/src-tauri/bin/VRCT-sidecar-<triple>.exe   (npm run sidecar-dev drop-in)
    //   <root>/src-tauri/target/debug/VRCT-sidecar-<triple>.exe   (tauri dev copies it)
    //   <root>/src-tauri/target/release/VRCT-sidecar-<triple>.exe
    // Walk upward until we find a directory that looks like the project root
    // (contains both .venv and src-python/mainloop.py).
    let root = match find_project_root(&self_exe) {
        Some(p) => p,
        None => {
            eprintln!(
                "dev-sidecar: could not locate project root above {}. Expected a parent dir containing .venv/ and src-python/mainloop.py.",
                self_exe.display()
            );
            std::process::exit(127);
        }
    };

    let python = root.join(".venv").join("Scripts").join("python.exe");
    let cwd: PathBuf = root.join("src-python");
    let script = cwd.join("mainloop.py");

    if !python.exists() {
        eprintln!(
            "dev-sidecar: venv Python not found at {}. Run `npm run setup-python` first.",
            python.display()
        );
        std::process::exit(127);
    }
    if !script.exists() {
        eprintln!("dev-sidecar: mainloop.py not found at {}", script.display());
        std::process::exit(127);
    }

    let forwarded_args: Vec<String> = env::args().skip(1).collect();

    let mut cmd = Command::new(&python);
    cmd.arg("-u")
        .arg(&script)
        .args(&forwarded_args)
        .current_dir(&cwd)
        .env("PYTHONUNBUFFERED", "1")
        .stdin(Stdio::inherit())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit());

    let status = match cmd.status() {
        Ok(s) => s,
        Err(e) => {
            eprintln!(
                "dev-sidecar: failed to launch {} {}: {}",
                python.display(),
                script.display(),
                e
            );
            std::process::exit(127);
        }
    };

    std::process::exit(status.code().unwrap_or(1));
}

fn find_project_root(start: &Path) -> Option<PathBuf> {
    let mut cursor = start.parent();
    for _ in 0..10 {
        let dir = cursor?;
        if dir.join(".venv").join("Scripts").join("python.exe").exists()
            && dir.join("src-python").join("mainloop.py").exists()
        {
            return Some(dir.to_path_buf());
        }
        cursor = dir.parent();
    }
    None
}

#[cfg(windows)]
unsafe fn install_kill_on_close_job() {
    use std::mem::{size_of, zeroed};
    use std::ptr::null;
    use windows_sys::Win32::System::JobObjects::{
        AssignProcessToJobObject, CreateJobObjectW, JobObjectExtendedLimitInformation,
        SetInformationJobObject, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    };
    use windows_sys::Win32::System::Threading::GetCurrentProcess;

    let job = CreateJobObjectW(null(), null());
    if job.is_null() {
        return;
    }

    let mut info: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = zeroed();
    info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;

    let ok = SetInformationJobObject(
        job,
        JobObjectExtendedLimitInformation,
        &info as *const _ as *const _,
        size_of::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
    );
    if ok == 0 {
        return;
    }

    AssignProcessToJobObject(job, GetCurrentProcess());
    // Intentionally leak the job handle: the OS closes it on process exit,
    // which is exactly when we want the KILL_ON_JOB_CLOSE to fire.
}
