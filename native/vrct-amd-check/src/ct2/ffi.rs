//! Dynamically loaded check-only C ABI. The supervisor never loads this module's DLLs.
use anyhow::{ensure, Context, Result};
use libloading::os::windows::Library;
use std::ffi::{c_char, c_void, CStr, CString};
use std::path::Path;
use std::ptr::NonNull;
use windows_sys::Win32::System::LibraryLoader::{
    LOAD_LIBRARY_SEARCH_DEFAULT_DIRS, LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR,
};

pub struct Adapter {
    // Drop adapter first, then CT2, then the search-directory cookies.
    _library: Library,
    _ct2: Library,
    _dirs: crate::hip::DllDirectories,
    error: unsafe extern "C" fn() -> *const c_char,
    gpu_count: unsafe extern "C" fn() -> i32,
    compute_types: unsafe extern "C" fn(*const c_char) -> i32,
    model_new:
        unsafe extern "C" fn(*const c_char, *const c_char, *const c_char, i32) -> *mut c_void,
    model_free: unsafe extern "C" fn(*mut c_void) -> i32,
    model_info: unsafe extern "C" fn(*mut c_void, *mut c_char, usize) -> i32,
    whisper_mels: unsafe extern "C" fn(*mut c_void) -> i32,
    whisper_multilingual: unsafe extern "C" fn(*mut c_void) -> i32,
    transcribe: unsafe extern "C" fn(
        *mut c_void,
        *mut f32,
        usize,
        usize,
        *const usize,
        usize,
        *mut usize,
        usize,
    ) -> i32,
    translate: unsafe extern "C" fn(*mut c_void, *const c_char, usize, *mut c_char, usize) -> i32,
}

impl Adapter {
    pub fn load(base: &Path) -> Result<Self> {
        ensure!(super::BUILT, "{}", super::WITHOUT_ADAPTER);
        let dirs = crate::hip::DllDirectories::new(base)?;
        let flags = LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS;
        // An absolute CT2 path is preloaded before resolving the adapter's import.
        // No fallback to the app DLL, PATH, or Python installation is permitted.
        unsafe {
            let ct2 = Library::load_with_flags(base.join("ctranslate2.dll"), flags)
                .context("load packaged CTranslate2 4.9.0 DLL and its dependencies")?;
            let library = Library::load_with_flags(base.join("vrct_ct2_49_adapter.dll"), flags)
                .context("load vrct_ct2_49_adapter.dll built for this package")?;
            let protocol = library.get::<unsafe extern "C" fn() -> i32>(b"ct2_49_protocol\0")?;
            ensure!(
                protocol() == 2,
                "unsupported check-adapter protocol; rebuild the CT2 adapter"
            );
            Ok(Self {
                error: *library.get(b"ct2_49_error\0")?,
                gpu_count: *library.get(b"ct2_49_gpu_count\0")?,
                compute_types: *library.get(b"ct2_49_compute_types\0")?,
                model_new: *library.get(b"ct2_49_model_new\0")?,
                model_free: *library.get(b"ct2_49_model_free\0")?,
                model_info: *library.get(b"ct2_49_model_info\0")?,
                whisper_mels: *library.get(b"ct2_49_whisper_mels\0")?,
                whisper_multilingual: *library.get(b"ct2_49_whisper_multilingual\0")?,
                transcribe: *library.get(b"ct2_49_transcribe\0")?,
                translate: *library.get(b"ct2_49_translate\0")?,
                _library: library,
                _ct2: ct2,
                _dirs: dirs,
            })
        }
    }

    fn last_error(&self) -> String {
        // The adapter returns a non-null thread-local string, valid until the next call.
        unsafe {
            CStr::from_ptr((self.error)())
                .to_string_lossy()
                .into_owned()
        }
    }

    fn checked(&self, n: i32) -> Result<usize> {
        ensure!(n >= 0, "CT2 4.9 adapter: {}", self.last_error());
        Ok(n as usize)
    }

    pub fn capabilities(&self, device: &str) -> Result<(usize, i32)> {
        let count = self.checked(unsafe { (self.gpu_count)() })?;
        ensure!(count > 0, "CTranslate2 found no GPU");
        let device = CString::new(device)?;
        let mask = self.checked(unsafe { (self.compute_types)(device.as_ptr()) })?;
        Ok((count, mask as i32))
    }

    pub fn model(
        &self,
        path: &Path,
        device: &str,
        compute: &str,
        whisper: bool,
    ) -> Result<Model<'_>> {
        let path = CString::new(path.to_str().context("CT2 model path must be UTF-8")?)?;
        let device = CString::new(device)?;
        let compute = CString::new(compute)?;
        let handle = unsafe {
            (self.model_new)(
                path.as_ptr(),
                device.as_ptr(),
                compute.as_ptr(),
                i32::from(whisper),
            )
        };
        let handle = NonNull::new(handle)
            .with_context(|| format!("load CT2 model: {}", self.last_error()))?;
        Ok(Model { api: self, handle })
    }
}

pub struct Model<'a> {
    api: &'a Adapter,
    handle: NonNull<c_void>,
}

// CTranslate2 ReplicaPool accepts simultaneous requests. Each C ABI call owns
// its input, encoder output and result. The model and DLLs outlive scoped threads;
// no create/free/unload happens while a request is in flight.
unsafe impl Send for Model<'_> {}
unsafe impl Sync for Model<'_> {}

impl Model<'_> {
    pub fn info(&self) -> Result<serde_json::Value> {
        let mut buffer = vec![0u8; 1024];
        let n = self.api.checked(unsafe {
            (self.api.model_info)(
                self.handle.as_ptr(),
                buffer.as_mut_ptr().cast(),
                buffer.len(),
            )
        })?;
        ensure!(n < buffer.len(), "invalid CT2 model info size");
        Ok(serde_json::from_slice(&buffer[..n])?)
    }
    pub fn whisper_info(&self) -> Result<(usize, bool)> {
        let mels = self
            .api
            .checked(unsafe { (self.api.whisper_mels)(self.handle.as_ptr()) })?;
        ensure!(
            matches!(mels, 80 | 128),
            "unexpected Whisper mel count {mels}"
        );
        let multilingual = self
            .api
            .checked(unsafe { (self.api.whisper_multilingual)(self.handle.as_ptr()) })?;
        Ok((mels, multilingual != 0))
    }

    pub fn transcribe(&self, features: &[f32], mels: usize, prompt: &[usize]) -> Result<Vec<u32>> {
        ensure!(
            features.len() == mels * crate::mel::N_FRAMES,
            "invalid feature shape"
        );
        // CT2 StorageView uses a mutable pointer; never share that backing buffer between calls.
        let mut features = features.to_vec();
        let mut ids = vec![0usize; 448];
        let count = self.api.checked(unsafe {
            (self.api.transcribe)(
                self.handle.as_ptr(),
                features.as_mut_ptr(),
                mels,
                crate::mel::N_FRAMES,
                prompt.as_ptr(),
                prompt.len(),
                ids.as_mut_ptr(),
                ids.len(),
            )
        })?;
        ensure!(count <= ids.len(), "invalid Whisper C ABI result length");
        ids[..count]
            .iter()
            .map(|&id| u32::try_from(id).context("Whisper token ID overflow"))
            .collect()
    }

    pub fn translate(&self, tokens: &[String]) -> Result<Vec<String>> {
        let mut packed = Vec::new();
        for token in tokens {
            packed.extend_from_slice(CString::new(token.as_str())?.as_bytes_with_nul());
        }
        let mut out = vec![0u8; 128 * 1024];
        let count = self.api.checked(unsafe {
            (self.api.translate)(
                self.handle.as_ptr(),
                packed.as_ptr().cast(),
                tokens.len(),
                out.as_mut_ptr().cast(),
                out.len(),
            )
        })?;
        ensure!(
            count <= out.len() && count > 0 && out[count - 1] == 0,
            "invalid NLLB C ABI output"
        );
        out[..count - 1]
            .split(|b| *b == 0)
            .map(|s| String::from_utf8(s.to_vec()).context("NLLB token UTF-8"))
            .collect()
    }
}

impl Drop for Model<'_> {
    fn drop(&mut self) {
        if unsafe { (self.api.model_free)(self.handle.as_ptr()) } < 0 {
            eprintln!("CT2 model destruction: {}", self.api.last_error());
        }
    }
}
