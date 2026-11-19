use crate::hip_abi::HipDevicePropR0600;
use crate::report::{Check, Status};
use anyhow::{ensure, Context, Result};
use libloading::os::windows::Library;
use serde_json::{json, Value};
use std::io::Write;
use std::os::windows::ffi::OsStrExt;
use std::path::{Path, PathBuf};
use windows_sys::Win32::System::LibraryLoader::{
    AddDllDirectory, GetModuleFileNameW, RemoveDllDirectory, SetDefaultDllDirectories,
    LOAD_LIBRARY_SEARCH_DEFAULT_DIRS, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR,
};

pub fn origin(path: &Path, base: &Path) -> &'static str {
    let p = path
        .to_string_lossy()
        .replace('/', "\\")
        .to_ascii_lowercase();
    let system32 = std::env::var("SystemRoot").ok().map(|root| {
        format!(
            "{}\\system32\\",
            root.replace('/', "\\")
                .trim_end_matches('\\')
                .to_ascii_lowercase()
        )
    });
    if system32.is_some_and(|root| p.starts_with(&root)) {
        "driver (System32/DriverStore)"
    } else if path.starts_with(base) {
        "bundled (does not prove a driver-only installation works)"
    } else if p.contains("\\amd\\rocm\\")
        || std::env::var_os("HIP_PATH").is_some_and(|root| path.starts_with(root))
    {
        "HIP SDK"
    } else {
        "other location on PATH"
    }
}

fn search_dirs(base: &Path) -> Vec<PathBuf> {
    let mut dirs = Vec::new();
    if let Some(root) = std::env::var_os("SystemRoot") {
        dirs.push(PathBuf::from(root).join("System32"));
    }
    dirs.extend([base.to_owned(), base.join("hip")]);
    if let Some(root) = std::env::var_os("HIP_PATH") {
        dirs.extend([PathBuf::from(&root).join("bin"), PathBuf::from(root)]);
    }
    if let Some(program_files) = std::env::var_os("ProgramFiles") {
        let rocm = PathBuf::from(program_files).join("AMD/ROCm");
        if crate::config::is_local_disk(&rocm) {
            if let Ok(entries) = std::fs::read_dir(rocm) {
                for entry in entries.flatten().take(32) {
                    dirs.push(entry.path().join("bin"));
                }
            }
        }
    }
    if let Some(path) = std::env::var_os("PATH") {
        dirs.extend(std::env::split_paths(&path).filter(|p| p.is_absolute()));
    }
    let mut seen = std::collections::BTreeSet::new();
    dirs.retain(|p| {
        crate::config::is_local_disk(p) && seen.insert(p.to_string_lossy().to_lowercase())
    });
    dirs
}

pub(crate) struct DllDirectories(Vec<*mut std::ffi::c_void>);
impl DllDirectories {
    pub(crate) fn new(base: &Path) -> Result<Self> {
        ensure!(
            unsafe { SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_DEFAULT_DIRS) } != 0,
            "SetDefaultDllDirectories: {}",
            std::io::Error::last_os_error()
        );
        let mut out = Self(Vec::new());
        // 作業ディレクトリの任意 DLL は探索対象にしない。
        for dir in [base.to_owned(), base.join("hip")] {
            if !dir.is_dir() {
                continue;
            }
            let wide: Vec<_> = dir.as_os_str().encode_wide().chain([0]).collect();
            let cookie = unsafe { AddDllDirectory(wide.as_ptr()) };
            ensure!(
                !cookie.is_null(),
                "AddDllDirectory: {}",
                std::io::Error::last_os_error()
            );
            out.0.push(cookie);
        }
        Ok(out)
    }
}
impl Drop for DllDirectories {
    fn drop(&mut self) {
        for cookie in &self.0 {
            unsafe {
                RemoveDllDirectory(*cookie);
            }
        }
    }
}

fn loaded_path(lib: Library) -> Result<(Library, PathBuf)> {
    let handle = lib.into_raw();
    // 生ハンドルを確認し、直ちに所有権を戻す。
    let owned = unsafe { Library::from_raw(handle) };
    let mut buf = vec![0u16; 32768];
    let len =
        unsafe { GetModuleFileNameW(handle as _, buf.as_mut_ptr(), buf.len() as u32) } as usize;
    ensure!(
        len != 0 && len < buf.len(),
        "GetModuleFileNameW: {}",
        std::io::Error::last_os_error()
    );
    Ok((owned, PathBuf::from(String::from_utf16_lossy(&buf[..len]))))
}

fn load(path: &Path) -> Result<Library> {
    println!("Loading {}", path.display());
    let _ = std::io::stdout().flush();
    // ベンダーコードは監視された子プロセス内でのみ実行する。
    unsafe {
        Library::load_with_flags(
            path,
            LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS,
        )
    }
    .with_context(|| format!("load {}", path.display()))
}

fn candidates(base: &Path, names: &[&str], wildcard: bool) -> Vec<PathBuf> {
    let mut paths = Vec::new();
    for dir in search_dirs(base) {
        for name in names {
            paths.push(dir.join(name));
        }
        if wildcard {
            if let Ok(entries) = std::fs::read_dir(&dir) {
                let mut extra: Vec<_> = entries
                    .flatten()
                    .filter_map(|e| {
                        let n = e.file_name().to_string_lossy().to_ascii_lowercase();
                        (n.starts_with("amdhip64") && n.ends_with(".dll")).then(|| e.path())
                    })
                    .take(64)
                    .collect();
                extra.sort();
                paths.extend(extra);
            }
        }
    }
    let mut seen = std::collections::BTreeSet::new();
    paths.retain(|p| p.is_file() && seen.insert(p.to_string_lossy().to_lowercase()));
    paths
}

fn ctext(bytes: &[u8]) -> String {
    String::from_utf8_lossy(bytes.split(|&b| b == 0).next().unwrap_or_default()).into_owned()
}

fn api_ok(code: i32, call: &str) -> Result<()> {
    ensure!(code == 0, "{call} returned HIP error {code}");
    Ok(())
}

pub fn runtime(base: &Path) -> Result<Check> {
    let _dirs = DllDirectories::new(base)?;
    let names = ["amdhip64_7.dll", "amdhip64_6.dll", "amdhip64.dll"];
    let paths = candidates(base, &names, true);
    let mut attempts = Vec::new();
    let mut selected = None;
    for path in paths {
        match load(&path) {
            Ok(lib) => {
                selected = Some(lib);
                break;
            }
            Err(e) => attempts.push(json!({"path":path, "error":format!("{e:#}")})),
        }
    }
    let Some(lib) = selected else {
        return Ok(Check::new("Stage A: HIP runtime", Status::Fail,
            "No HIP runtime found. Please make sure your AMD driver (Adrenalin) is up to date, then run this again.",
            json!({"attempted_names":names, "load_errors":attempts, "hip_device_count":0})));
    };
    let (lib, path) = loaded_path(lib)?;
    let from = origin(&path, base);
    println!("HIP runtime: {} / {from}", path.display());
    let _ = std::io::stdout().flush();
    // 全てのシンボルは公式の C ABI。R0600 以外の構造体 API は使わない。
    let result = unsafe {
        let init = lib.get::<unsafe extern "C" fn(u32) -> i32>(b"hipInit\0")?;
        let count_fn = lib.get::<unsafe extern "C" fn(*mut i32) -> i32>(b"hipGetDeviceCount\0")?;
        let device = lib.get::<unsafe extern "C" fn(*mut i32, i32) -> i32>(b"hipDeviceGet\0")?;
        let name =
            lib.get::<unsafe extern "C" fn(*mut u8, i32, i32) -> i32>(b"hipDeviceGetName\0")?;
        let capability = lib.get::<unsafe extern "C" fn(*mut i32, *mut i32, i32) -> i32>(
            b"hipDeviceComputeCapability\0",
        )?;
        let properties = lib.get::<unsafe extern "C" fn(*mut HipDevicePropR0600, i32) -> i32>(
            b"hipGetDevicePropertiesR0600\0",
        );
        let version = lib.get::<unsafe extern "C" fn(*mut i32) -> i32>(b"hipRuntimeGetVersion\0");
        let mut runtime_version = 0;
        if let Ok(f) = version {
            let _ = f(&mut runtime_version);
        }
        api_ok(init(0), "hipInit(0)")?;
        let mut count = 0;
        api_ok(count_fn(&mut count), "hipGetDeviceCount")?;
        ensure!(
            (0..=64).contains(&count),
            "invalid HIP device count {count}"
        );
        let mut devices = Vec::new();
        let mut complete = true;
        for i in 0..count {
            let mut dev = 0;
            api_ok(device(&mut dev, i), "hipDeviceGet")?;
            let mut buf = [0u8; 256];
            api_ok(name(buf.as_mut_ptr(), 256, dev), "hipDeviceGetName")?;
            let (mut major, mut minor) = (0, 0);
            api_ok(
                capability(&mut major, &mut minor, dev),
                "hipDeviceComputeCapability",
            )?;
            let (arch, arch_error) = match &properties {
                Ok(f) => {
                    let mut p: HipDevicePropR0600 = std::mem::zeroed();
                    match api_ok(f(&mut p, i), "hipGetDevicePropertiesR0600") {
                        Ok(()) => (Some(ctext(&p.gcn_arch_name)), None),
                        Err(e) => {
                            complete = false;
                            (None, Some(format!("{e:#}")))
                        }
                    }
                }
                Err(e) => {
                    complete = false;
                    (
                        None,
                        Some(format!("R0600 unavailable; no ABI guessing: {e}")),
                    )
                }
            };
            let name = ctext(&buf);
            println!(
                "Device {i}: {name}, compute capability {major}.{minor}, gcnArchName={arch:?}"
            );
            let _ = std::io::stdout().flush();
            devices.push(json!({"index":i, "name":name, "major":major, "minor":minor,
                "gcnArchName":arch, "gcnArchName_error":arch_error, "planned_rdna3_rdna4_gate":matches!(major, 11 | 12)}));
        }
        let status = if count == 0 {
            Status::Fail
        } else if complete {
            Status::Ok
        } else {
            Status::Warn
        };
        Check::new(
            "Stage A: HIP runtime",
            status,
            if count == 0 {
                "HIP runtime loaded, but no HIP GPU was found."
            } else {
                "HIP device enumeration completed; see the architecture and origin below."
            },
            json!({"hip_runtime_path":path, "origin":from, "runtime_version":runtime_version,
                "hip_device_count":count, "devices":devices, "load_errors":attempts}),
        )
    };
    Ok(result)
}

pub fn blas(base: &Path, name: &str) -> Result<Check> {
    let _dirs = DllDirectories::new(base)?;
    let mut found = Vec::new();
    let mut errors = Vec::new();
    for path in candidates(base, &[name], false) {
        match load(&path) {
            Ok(lib) => {
                let (_lib, actual) = loaded_path(lib)?;
                found.push(json!({"path":actual, "origin":origin(&actual, base)}));
            }
            Err(e) => errors.push(json!({"path":path,"error":format!("{e:#}")})),
        }
    }
    Ok(Check::new(
        &format!("Stage A: {name} (CT2 issue #2016)"),
        if found.is_empty() {
            Status::Warn
        } else {
            Status::Ok
        },
        if found.is_empty() {
            "Not loadable under this name; do not rename DLLs to hide the mismatch."
        } else {
            "DLL present and loadable."
        },
        json!({"loaded":found,"errors":errors}),
    ))
}

pub fn environment(base: &Path) -> Value {
    let sdk_dirs: Vec<_> = search_dirs(base)
        .into_iter()
        .filter(|p| {
            p.to_string_lossy()
                .to_ascii_lowercase()
                .contains("amd\\rocm")
                && p.is_dir()
        })
        .collect();
    json!({"os":"Windows", "architecture":std::env::consts::ARCH,
        "hip_path":std::env::var("HIP_PATH").ok(), "sdk_directories":sdk_dirs,
        "note":"HIP SDK is not required. Its absence is useful to know."})
}
