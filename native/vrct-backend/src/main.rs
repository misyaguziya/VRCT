//! VRCT-sidecar: the backend the UI starts (mainloop.py). Requests come on stdin, answers and
//! pushes go to stdout; nothing is written to stderr (the UI takes any line there for a fatal error).
use anyhow::Result;
use serde_json::Value;
use std::ffi::CStr;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;
use windows_sys::Win32::System::LibraryLoader::{GetModuleHandleA, LoadLibraryExW, LOAD_LIBRARY_SEARCH_DEFAULT_DIRS, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR, LOAD_LIBRARY_SEARCH_SYSTEM32};
use vrct_backend::app::{init, routes, App, Model};
use vrct_backend::config::{executable_dir, Config, Env};
use vrct_backend::ipc::{self, Dispatcher};
use vrct_backend::{app, compute, logs, net, websocket};

const WORKERS: usize = 3;
/// After the UI stopped feeding the watchdog: the process ends this long after the shutdown began
const WATCHDOG_GRACE: Duration = Duration::from_secs(30);

/// A panic is logged (error.log, and crash_trace.log as faulthandler did), never printed to stderr
fn panic_hook() {
    std::panic::set_hook(Box::new(|info| {
        let thread = std::thread::current().name().unwrap_or("?").to_string();
        let backtrace = std::backtrace::Backtrace::force_capture();
        let message = format!("panic in thread {thread}: {info}\n{backtrace}");
        logs::error("panic", &message);
        use std::io::Write;
        if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open("crash_trace.log") {
            let _ = writeln!(f, "{message}");
        }
    }));
}

/// The DLLs are in `_internal` (the installed layout): it joins the search path of LoadLibrary and
/// of the DLLs loaded at first use (ctranslate2.dll and what it needs)
fn add_dll_directory(dir: &std::path::Path) {
    use std::os::windows::ffi::OsStrExt;
    use windows_sys::Win32::System::LibraryLoader::{AddDllDirectory, SetDefaultDllDirectories};
    let wide: Vec<u16> = dir.as_os_str().encode_wide().chain([0]).collect();
    unsafe {
        SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
        AddDllDirectory(wide.as_ptr());
    }
}

/// The native libraries read getenv(). Keep the CRT and Win32 environments in sync.
fn set_runtime_env(name: &CStr, value: &CStr) -> i32 {
    unsafe extern "C" {
        fn _putenv_s(name: *const std::ffi::c_char, value: *const std::ffi::c_char) -> i32;
    }
    std::env::set_var(name.to_str().unwrap(), value.to_str().unwrap());
    unsafe { _putenv_s(name.as_ptr(), value.as_ptr()) }
}

/// Pin the ROCm CT2 for the executable's delay import. On failure only the CPU edition's
/// _internal directory remains on the search path.
fn preload_rocm(resources: &std::path::Path) -> bool {
    use std::os::windows::ffi::OsStrExt;
    let rocm = resources.join("ct2-rocm");
    let path = rocm.join("ctranslate2.dll");
    if !path.is_file() {
        if rocm.is_dir() {
            logs::PROCESS.write(&format!("Using CPU: incomplete AMD install, missing {}", path.display()));
        }
        return false;
    }
    let hip_name: Vec<u16> = "amdhip64_7.dll".encode_utf16().chain([0]).collect();
    let hip = unsafe { LoadLibraryExW(hip_name.as_ptr(), std::ptr::null_mut(), LOAD_LIBRARY_SEARCH_SYSTEM32) };
    if hip.is_null() {
        let error = std::io::Error::last_os_error();
        logs::PROCESS.write(&format!("Using CPU: could not load amdhip64_7.dll from System32 ({error}). Update the AMD Adrenalin driver."));
        return false;
    }
    let wide: Vec<u16> = path.as_os_str().encode_wide().chain([0]).collect();
    let ct2 = unsafe { LoadLibraryExW(wide.as_ptr(), std::ptr::null_mut(), LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS) };
    if ct2.is_null() {
        let error = std::io::Error::last_os_error();
        unsafe { windows_sys::Win32::Foundation::FreeLibrary(hip) };
        logs::PROCESS.write(&format!("Using CPU: could not load {} ({error})", path.display()));
        return false;
    }
    // cwd is the exe directory. ASCII paths also work when the installation path is non-ASCII.
    for (name, value) in [
        (c"ROCBLAS_TENSILE_LIBPATH", c"_internal\\ct2-rocm\\rocblas\\library"),
        (c"HIPBLASLT_TENSILE_LIBPATH", c"_internal\\ct2-rocm\\hipblaslt\\library"),
    ] {
        let errno = set_runtime_env(name, value);
        logs::PROCESS.write(&format!("{}={} (CRT errno: {errno})", name.to_string_lossy(), value.to_string_lossy()));
        if errno != 0 {
            unsafe {
                windows_sys::Win32::Foundation::FreeLibrary(ct2);
                windows_sys::Win32::Foundation::FreeLibrary(hip);
            }
            logs::PROCESS.write("Using CPU: could not set the ROCm kernel path in the C runtime");
            return false;
        }
    }
    logs::PROCESS.write(&format!("Loaded ROCm CTranslate2 from {}", path.display()));
    true
}

fn main() -> Result<()> {
    let crt_errno = set_runtime_env(c"AMD_COMGR_CACHE", c"0");
    // GetModuleHandle only observes the module table and never loads a DLL.
    let before_load = unsafe {
        GetModuleHandleA(c"amdhip64_7.dll".as_ptr().cast()).is_null()
            && GetModuleHandleA(c"ctranslate2.dll".as_ptr().cast()).is_null()
    };
    // Physical px in every window API (vrct-overlay's window.rs: the VR panel's size, capture and
    // input). DPI-unaware, Windows would scale them to 96 DPI at any display scale but 100%.
    // A failure is logged once the working directory (where error.log is) is set
    let dpi_error = unsafe {
        use windows_sys::Win32::UI::HiDpi::{SetProcessDpiAwarenessContext, DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2};
        (SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2) == 0).then(std::io::Error::last_os_error)
    };
    let local = executable_dir();
    let resources = local.join("_internal");
    add_dll_directory(&resources);
    // config.json, the logs and the weights are beside the executable, as the frozen Python build
    std::env::set_current_dir(&local)?;
    logs::PROCESS.clear();
    logs::PROCESS.write(&format!("AMD_COMGR_CACHE={} (set before HIP/CT2 load: {before_load}, CRT errno: {crt_errno})", std::env::var("AMD_COMGR_CACHE")?));
    panic_hook();
    if let Some(e) = dpi_error {
        logs::error("SetProcessDpiAwarenessContext", &e);
    }
    let rocm = if crt_errno == 0 {
        preload_rocm(&resources)
    } else {
        logs::PROCESS.write("Skipping ROCm: could not disable the COMGR cache in the C runtime");
        false
    };
    // what the native libraries print (CTranslate2's logs, drivers) goes to error.log
    vrct_ct2::redirect_stderr(&PathBuf::from("error.log"));

    let transcription_lang: Value = serde_json::from_str(include_str!("../../data/transcription_languages.json"))?;
    let devices = vrct_backend::devices::snapshot();
    let config = Config::new(Env {
        path_local: local.clone(),
        compute_devices: compute::device_list(rocm, &resources),
        default_mic: devices.default_mic,
        default_speaker: devices.default_speaker,
        devices: Arc::new(|| vrct_backend::devices::snapshot().lists()),
        transcription_lang: transcription_lang.clone(),
        new_token: websocket::new_auth_token,
    });
    config.load();

    let http = net::Http::new()?;
    let model = Model::new(http, app::Resources { dir: resources }, transcription_lang, &config)?;
    let app = App::new(config, model);
    app::register_error_hook(&app);

    let dispatcher = Dispatcher::new(app.clone(), routes::routes());
    dispatcher.start_receiver();
    dispatcher.start_workers(WORKERS);

    // escalateShutdown: once; the process ends after the shutdown, or WATCHDOG_GRACE at the latest
    let escalated = Arc::new(AtomicBool::new(false));
    let me = app.me();
    let escalate = move || {
        if escalated.swap(true, Ordering::SeqCst) {
            return;
        }
        std::thread::spawn(|| {
            std::thread::sleep(WATCHDOG_GRACE);
            std::process::exit(1);
        });
        let me = me.clone();
        std::thread::spawn(move || {
            if let Some(app) = me.upgrade() {
                let _ = init::shutdown(&app, None);
            }
            std::process::exit(0);
        });
    };
    // an exception out of Controller.init ended the Python process (the UI shows it closed)
    if let Err(e) = init::init(&app, escalate) {
        logs::error("init", &format!("{e:#}"));
        ipc::log(format!("Initialization failed: {e:#}"));
        std::process::exit(1);
    }
    dispatcher.set_initialized();
    loop {
        std::thread::sleep(Duration::from_secs(1));
    }
}
