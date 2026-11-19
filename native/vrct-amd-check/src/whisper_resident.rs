//! モデル・melを一度だけ準備する、whisper.cpp v1.8.4 の検証専用ワーカー。
use crate::benchmark;
use crate::config::Config;
use crate::report::{Check, Report, Status};
use anyhow::{ensure, Context, Result};
use libloading::os::windows::Library;
use serde_json::{json, Value};
use std::ffi::{c_char, c_void, CStr, CString};
use std::ptr::NonNull;
use std::time::Instant;
use windows_sys::Win32::System::LibraryLoader::{
    LOAD_LIBRARY_SEARCH_DEFAULT_DIRS, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR,
};

pub const BUILT: bool = cfg!(whisper_184_adapter);
pub const WITHOUT_ADAPTER: &str = "skipped: built without the whisper.cpp v1.8.4 resident adapter";

struct Adapter {
    _adapter: Library,
    _whisper: Library,
    _dirs: crate::hip::DllDirectories,
    new: unsafe extern "C" fn(*const c_char, i32, i32, i32, i32) -> *mut c_void,
    free: unsafe extern "C" fn(*mut c_void) -> i32,
    prepare: unsafe extern "C" fn(*mut c_void, *const f32, usize, i32, i32, i32) -> i32,
    transcribe: unsafe extern "C" fn(*mut c_void, *mut c_char, usize) -> i32,
    error: unsafe extern "C" fn() -> *const c_char,
}

impl Adapter {
    fn load(c: &Config) -> Result<Self> {
        ensure!(BUILT, "{WITHOUT_ADAPTER}");
        let base = c.base.join("whisper-vulkan");
        let dirs = crate::hip::DllDirectories::new(&base)?;
        let flags = LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS;
        unsafe {
            let whisper = Library::load_with_flags(base.join("whisper.dll"), flags)
                .context("load packaged whisper.dll v1.8.4 and its Vulkan dependencies")?;
            let adapter =
                Library::load_with_flags(base.join("vrct_whisper_184_adapter.dll"), flags)
                    .context("load check-only resident whisper adapter")?;
            let protocol =
                adapter.get::<unsafe extern "C" fn() -> i32>(b"whisper_184_protocol\0")?;
            ensure!(
                protocol() == 2,
                "incompatible whisper adapter protocol; use the common-mel adapter"
            );
            let version =
                adapter.get::<unsafe extern "C" fn() -> *const c_char>(b"whisper_184_version\0")?;
            let version = CStr::from_ptr(version()).to_str()?;
            ensure!(
                version.trim_start_matches('v') == "1.8.4",
                "expected whisper.cpp v1.8.4, got {version}"
            );
            Ok(Self {
                new: *adapter.get(b"whisper_184_model_new\0")?,
                free: *adapter.get(b"whisper_184_model_free\0")?,
                prepare: *adapter.get(b"whisper_184_prepare\0")?,
                transcribe: *adapter.get(b"whisper_184_transcribe\0")?,
                error: *adapter.get(b"whisper_184_error\0")?,
                _adapter: adapter,
                _whisper: whisper,
                _dirs: dirs,
            })
        }
    }
    fn error(&self) -> String {
        unsafe {
            CStr::from_ptr((self.error)())
                .to_string_lossy()
                .into_owned()
        }
    }
    fn checked(&self, value: i32) -> Result<usize> {
        ensure!(value >= 0, "whisper.cpp: {}", self.error());
        Ok(value as usize)
    }
    fn model(&self, c: &Config, gpu: bool) -> Result<Model<'_>> {
        let path = CString::new(
            c.whisper_model
                .to_str()
                .context("model path must be UTF-8")?,
        )?;
        let handle = unsafe {
            (self.new)(
                path.as_ptr(),
                i32::from(gpu),
                c.vulkan_device as i32,
                benchmark::THREADS as i32,
                benchmark::MAX_NEW_TOKENS as i32,
            )
        };
        let handle = NonNull::new(handle)
            .with_context(|| format!("load whisper model: {}", self.error()))?;
        Ok(Model {
            adapter: self,
            handle,
        })
    }
}

struct Model<'a> {
    adapter: &'a Adapter,
    handle: NonNull<c_void>,
}
impl Model<'_> {
    fn prepare(&mut self, mel: &crate::mel::PreparedMel) -> Result<()> {
        self.adapter.checked(unsafe {
            (self.adapter.prepare)(
                self.handle.as_ptr(),
                mel.values().as_ptr(),
                mel.values().len(),
                crate::mel::N_MELS as i32,
                crate::mel::N_FRAMES as i32,
                i32::try_from(mel.original_samples())?,
            )
        })?;
        Ok(())
    }
    fn transcribe(&mut self) -> Result<Value> {
        let mut text = vec![0u8; 128 * 1024];
        let n = self.adapter.checked(unsafe {
            (self.adapter.transcribe)(self.handle.as_ptr(), text.as_mut_ptr().cast(), text.len())
        })?;
        ensure!(
            n < text.len() && text[n] == 0,
            "invalid whisper transcript buffer"
        );
        let text = std::str::from_utf8(&text[..n])?.trim().to_owned();
        ensure!(!text.is_empty(), "empty whisper transcript");
        Ok(json!({"text":text}))
    }
}
impl Drop for Model<'_> {
    fn drop(&mut self) {
        if unsafe { (self.adapter.free)(self.handle.as_ptr()) } < 0 {
            eprintln!("whisper model destruction: {}", self.adapter.error());
        }
    }
}

pub fn worker(c: &Config, gpu: bool) -> Result<Check> {
    let adapter = Adapter::load(c)?;
    let start = Instant::now();
    let mut model = adapter.model(c, gpu)?;
    let load_seconds = start.elapsed().as_secs_f64();
    let start = Instant::now();
    let mel = crate::mel::PreparedMel::from_audio(&c.audio)?;
    model.prepare(&mel)?;
    let preprocess_seconds = start.elapsed().as_secs_f64();
    let input_features = mel.metadata();
    let mut infer = || -> Result<Value> {
        let start = Instant::now();
        let mut value = model.transcribe()?;
        value["seconds"] = json!(start.elapsed().as_secs_f64());
        Ok(value)
    };
    let warmup = infer()?;
    let samples = (0..c.runs).map(|_| infer()).collect::<Result<Vec<_>>>()?;
    let stats = benchmark::statistics(&samples)?;
    let mode = if gpu { "gpu" } else { "cpu" };
    Ok(Check::new(&format!("Part 2: whisper.cpp {mode} resident"), Status::Ok,
        "Resident model, precomputed mel, one warmup; timed inference ends after UTF-8 transcript retrieval.",
        json!({"executed":true,"device":if gpu {"vulkan"} else {"cpu"},
            "device_index":if gpu {c.vulkan_device} else {0},"backend_verified":true,
            "model":c.whisper_model,"engine_version":"1.8.4","load_seconds":load_seconds,
            "preprocess_seconds":preprocess_seconds,"warmup":warmup,"samples":samples,
            "input_features":input_features,
            "best_seconds":stats["best_seconds"],"median_seconds":stats["median_seconds"],
            "concurrent":false,"model_instances":1,"cpu_threads":benchmark::THREADS,
            "benchmark_contract":benchmark::contract(&benchmark::sha256(&c.audio)?),
            "timing":benchmark::SCOPE,
            "quality":"nonempty output only; semantic correctness requires manual review"})))
}

pub fn stages(c: &Config, r: &mut Report, mut supervise: impl FnMut(&Config, &str) -> Check) {
    let mut values = Vec::new();
    for mode in ["gpu", "cpu"] {
        let reason = if !BUILT {
            Some(WITHOUT_ADAPTER)
        } else if !c.base.join("whisper-vulkan/whisper.dll").is_file() {
            Some("packaged whisper.dll is missing")
        } else if !c.whisper_model.is_file() {
            Some("local whisper.cpp model is missing")
        } else {
            None
        };
        let check = match reason {
            Some(reason) => Check::new(
                &format!("Part 2: whisper.cpp {mode} resident"),
                Status::Skip,
                reason,
                json!({"executed":false}),
            ),
            None => supervise(c, &format!("whisper-resident-{mode}")),
        };
        values.push(if check.status == Status::Ok {
            check
                .data
                .pointer("/result/median_seconds")
                .and_then(Value::as_f64)
        } else {
            None
        });
        r.checks.push(check);
    }
    let ratio = values[0]
        .zip(values[1])
        .filter(|(g, c)| g.is_finite() && c.is_finite() && *g > 0.0 && *c > 0.0)
        .map(|(g, c)| c / g);
    r.checks.push(Check::new("Part 2: whisper.cpp resident CPU/GPU comparison",
        if ratio.is_some() {Status::Ok} else {Status::Blocked},
        "Same whisper.cpp model, resident timing and median latency. This is not a CT2 comparison or a process startup measurement.",
        json!({"gpu_median_seconds":values[0],"cpu_median_seconds":values[1],"cpu_over_gpu":ratio,"timing":benchmark::SCOPE})));
}
