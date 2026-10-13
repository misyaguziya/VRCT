// Dev-time sidecar wrapper.
//
// Tauri's externalBin requires a real executable at
// src-tauri/bin/VRCT-sidecar-<triple>.exe. In release builds that slot is
// filled by the Rust backend with its _internal (bat/build.bat). During
// development this wrapper is dropped into that slot instead and launches the
// backend staged by `cargo xtask stage-sidecar --out target\sidecar-stage`
// under native/, so rebuilding and restaging the backend needs no Tauri
// rebuild. Its config.json and logs stay in that folder.
//
// stdin/stdout/stderr are inherited so the Tauri <-> sidecar JSON protocol
// works unchanged.
//
// On Windows the wrapper also puts itself into a Job Object with
// KILL_ON_JOB_CLOSE. When Tauri terminates the sidecar process, the Job
// closes and the backend is killed with it, preventing orphaned backends
// after a dev restart.

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
    // Walk upward until we find the project root (contains native/Cargo.toml).
    let root = match find_project_root(&self_exe) {
        Some(p) => p,
        None => {
            eprintln!(
                "dev-sidecar: could not locate project root above {}. Expected a parent dir containing native/Cargo.toml.",
                self_exe.display()
            );
            std::process::exit(127);
        }
    };

    let exe = root.join("native").join("target").join("sidecar-stage").join("VRCT-sidecar.exe");
    if !exe.exists() {
        eprintln!(
            "dev-sidecar: the backend is not staged at {}. Run cargo xtask stage-sidecar --out target/sidecar-stage in native/ first.",
            exe.display()
        );
        std::process::exit(127);
    }
    let status = Command::new(&exe)
        .args(env::args().skip(1))
        .current_dir(exe.parent().unwrap())
        .stdin(Stdio::inherit())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .status();
    match status {
        Ok(s) => std::process::exit(s.code().unwrap_or(1)),
        Err(e) => {
            eprintln!("dev-sidecar: failed to launch {}: {}", exe.display(), e);
            std::process::exit(127);
        }
    }
}

fn find_project_root(start: &Path) -> Option<PathBuf> {
    let mut cursor = start.parent();
    while let Some(dir) = cursor {
        if dir.join("native").join("Cargo.toml").is_file() {
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
    use windows_sys::Win32::Foundation::{CloseHandle, GetLastError};
    use windows_sys::Win32::System::JobObjects::{
        AssignProcessToJobObject, CreateJobObjectW, JobObjectExtendedLimitInformation,
        SetInformationJobObject, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    };
    use windows_sys::Win32::System::Threading::GetCurrentProcess;

    let job = CreateJobObjectW(null(), null());
    if job.is_null() {
        eprintln!(
            "dev-sidecar: CreateJobObjectW failed (error {})",
            GetLastError()
        );
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
        eprintln!(
            "dev-sidecar: SetInformationJobObject failed (error {})",
            GetLastError()
        );
        CloseHandle(job);
        return;
    }

    if AssignProcessToJobObject(job, GetCurrentProcess()) == 0 {
        eprintln!(
            "dev-sidecar: AssignProcessToJobObject failed (error {})",
            GetLastError()
        );
        CloseHandle(job);
        return;
    }
    // Intentionally leak the job handle: the OS closes it on process exit,
    // which is exactly when we want the KILL_ON_JOB_CLOSE to fire.
}
