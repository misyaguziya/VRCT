//! CTranslate2 through the ctranslate2.dll of the Python wheel (shim/ct2_shim.cpp), so the Rust
//! backend runs the very same binary as the Python one. Each call mirrors what the Python binding
//! (python/cpp/*.cc of CTranslate2 4.6.0) does.
//!
//! The DLL loads libiomp5md.dll and cudnn64_9.dll from its folder; for CUDA the cuBLAS / cuDNN DLLs
//! of the nvidia-*-cu12 wheels must be on PATH too.
use anyhow::{bail, Result};
use std::ffi::{c_char, c_void, CStr, CString};
use std::path::Path;
use std::ptr::NonNull;

mod ffi {
    use std::ffi::{c_char, c_void};

    #[repr(C)]
    pub struct WhisperOptions {
        pub beam_size: usize,
        pub patience: f32,
        pub length_penalty: f32,
        pub repetition_penalty: f32,
        pub no_repeat_ngram_size: usize,
        pub max_length: usize,
        pub sampling_topk: usize,
        pub sampling_temperature: f32,
        pub num_hypotheses: usize,
        pub return_scores: bool,
        pub return_no_speech_prob: bool,
        pub max_initial_timestamp_index: usize,
        pub suppress_blank: bool,
        pub suppress_tokens: *const i32,
        pub suppress_tokens_len: usize,
    }

    pub type NewFn = unsafe extern "C" fn(*const c_char, *const c_char, i32, *const c_char, usize, usize) -> *mut c_void;

    extern "C" {
        pub fn ct2_last_error() -> *const c_char;
        pub fn ct2_redirect_stderr(path: *const c_char) -> bool;
        pub fn ct2_cuda_device_count() -> i32;
        pub fn ct2_supported_compute_types(device: *const c_char, index: i32) -> i32;
        pub fn ct2_translator_new(path: *const c_char, device: *const c_char, index: i32, compute: *const c_char,
                                  inter: usize, intra: usize) -> *mut c_void;
        pub fn ct2_translator_free(t: *mut c_void);
        pub fn ct2_translate_options_default(o: *mut super::TranslateOptions);
        pub fn ct2_translate(t: *mut c_void, source: *const c_char, source_len: usize, prefix: *const c_char,
                             prefix_len: usize, o: *const super::TranslateOptions) -> *mut c_void;
        pub fn ct2_translation_num_hypotheses(r: *const c_void) -> usize;
        pub fn ct2_translation_hypothesis_len(r: *const c_void, i: usize) -> usize;
        pub fn ct2_translation_token(r: *const c_void, i: usize, j: usize) -> *const c_char;
        pub fn ct2_translation_score(r: *const c_void, i: usize) -> f32;
        pub fn ct2_translation_free(r: *mut c_void);
        pub fn ct2_whisper_new(path: *const c_char, device: *const c_char, index: i32, compute: *const c_char,
                               inter: usize, intra: usize) -> *mut c_void;
        pub fn ct2_whisper_free(w: *mut c_void);
        pub fn ct2_whisper_is_multilingual(w: *const c_void) -> bool;
        pub fn ct2_whisper_n_mels(w: *const c_void) -> usize;
        pub fn ct2_whisper_encode(w: *mut c_void, features: *mut f32, batch: usize, n_mels: usize, frames: usize,
                                  to_cpu: bool) -> *mut c_void;
        pub fn ct2_storage_free(s: *mut c_void);
        pub fn ct2_whisper_detect_language(w: *mut c_void, encoded: *const c_void) -> *mut c_void;
        pub fn ct2_languages_len(l: *const c_void) -> usize;
        pub fn ct2_languages_token(l: *const c_void, i: usize) -> *const c_char;
        pub fn ct2_languages_prob(l: *const c_void, i: usize) -> f32;
        pub fn ct2_languages_free(l: *mut c_void);
        pub fn ct2_whisper_options_default(o: *mut WhisperOptions);
        pub fn ct2_whisper_generate(w: *mut c_void, encoded: *const c_void, prompt: *const usize, prompt_len: usize,
                                    o: *const WhisperOptions) -> *mut c_void;
        pub fn ct2_generation_num_sequences(r: *const c_void) -> usize;
        pub fn ct2_generation_sequence_len(r: *const c_void, i: usize) -> usize;
        pub fn ct2_generation_sequence(r: *const c_void, i: usize) -> *const usize;
        pub fn ct2_generation_score(r: *const c_void, i: usize) -> f32;
        pub fn ct2_generation_no_speech_prob(r: *const c_void) -> f32;
        pub fn ct2_generation_free(r: *mut c_void);
    }
}

/// The C++ exception's message (kept per thread by the shim) as an error.
fn check(ptr: *mut c_void) -> Result<NonNull<c_void>> {
    match NonNull::new(ptr) {
        Some(p) => Ok(p),
        None => bail!("{}", unsafe { CStr::from_ptr(ffi::ct2_last_error()) }.to_string_lossy()),
    }
}

fn cstring(s: &str) -> Result<CString> {
    Ok(CString::new(s)?)
}

fn string_at(p: *const c_char) -> String {
    unsafe { CStr::from_ptr(p) }.to_string_lossy().into_owned()
}

/// Tokens as one '\0'-separated buffer, the shim's input format.
fn joined(tokens: &[String]) -> Result<Vec<u8>> {
    if tokens.iter().any(|t| t.contains('\0')) {
        bail!("token contains NUL");
    }
    Ok(tokens.iter().flat_map(|t| t.bytes().chain([0])).collect())
}

/// Points the C runtime's stderr (shared by ctranslate2.dll) at a file, so nothing reaches the UI's
/// stderr pipe. Returns false on failure.
pub fn redirect_stderr(path: &Path) -> bool {
    match path.to_str().map(CString::new) {
        Some(Ok(p)) => unsafe { ffi::ct2_redirect_stderr(p.as_ptr()) },
        _ => false,
    }
}

/// ctranslate2.get_cuda_device_count()
pub fn cuda_device_count() -> usize {
    unsafe { ffi::ct2_cuda_device_count() }.max(0) as usize
}

/// ctranslate2.get_supported_compute_types(device, device_index), as python/cpp/module.cc builds it.
pub fn supported_compute_types(device: &str, device_index: i32) -> Result<Vec<&'static str>> {
    let bits = unsafe { ffi::ct2_supported_compute_types(cstring(device)?.as_ptr(), device_index) };
    if bits < 0 {
        bail!("{}", string_at(unsafe { ffi::ct2_last_error() }));
    }
    let (bf16, fp16, int16, int8) = (bits & 1 != 0, bits & 2 != 0, bits & 4 != 0, bits & 8 != 0);
    let mut types = vec!["float32"];
    let mut add = |on: bool, name| if on { types.push(name) };
    add(fp16, "float16");
    add(bf16, "bfloat16");
    add(int16, "int16");
    add(int8, "int8");
    add(int8, "int8_float32");
    add(int8 && fp16, "int8_float16");
    add(int8 && bf16, "int8_bfloat16");
    Ok(types)
}

/// utils.getBestComputeType: the first preferred type the device supports. `device_name` is the
/// CUDA device name ("cpu" for the CPU); GTX cards get float32.
pub fn best_compute_type(device: &str, device_index: i32, device_name: &str) -> &'static str {
    const PREFERRED: [&str; 7] = ["int8_bfloat16", "int8_float16", "int8", "bfloat16", "float16", "int8_float32", "float32"];
    let supported = supported_compute_types(device, device_index).unwrap_or_default();
    // Python checks the keys in order default, GTX, RTX, Tesla, A100, Quadro; only GTX differs
    let preferred: &[&'static str] = if device_name.contains("GTX") { &["float32"] } else { &PREFERRED };
    preferred.iter().copied().find(|t| supported.contains(t)).unwrap_or("float32")
}

/// Where and how a model runs (ctranslate2.Translator / models.Whisper constructor arguments).
#[derive(Clone, Debug)]
pub struct ModelConfig {
    pub device: String,
    pub device_index: i32,
    pub compute_type: String,
    pub inter_threads: usize,
    pub intra_threads: usize,
}

fn new_pool(f: ffi::NewFn, path: &Path, c: &ModelConfig) -> Result<NonNull<c_void>> {
    let Some(path) = path.to_str() else { bail!("model path is not UTF-8: {}", path.display()) };
    let (path, device, compute) = (cstring(path)?, cstring(&c.device)?, cstring(&c.compute_type)?);
    check(unsafe { f(path.as_ptr(), device.as_ptr(), c.device_index, compute.as_ptr(), c.inter_threads, c.intra_threads) })
}

// ---- Translator ------------------------------------------------------------------------------

/// translate_batch options (TranslationOptions). `Default` is CTranslate2's.
#[repr(C)]
#[derive(Clone, Copy, Debug)]
pub struct TranslateOptions {
    pub beam_size: usize,
    pub num_hypotheses: usize,
    pub length_penalty: f32,
    pub repetition_penalty: f32,
    pub no_repeat_ngram_size: usize,
    pub max_input_length: usize,
    pub max_decoding_length: usize,
    pub return_scores: bool,
}

impl Default for TranslateOptions {
    fn default() -> Self {
        let mut o = std::mem::MaybeUninit::uninit();
        unsafe {
            ffi::ct2_translate_options_default(o.as_mut_ptr());
            o.assume_init()
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct Hypothesis {
    pub tokens: Vec<String>,
    /// 0 unless `return_scores`
    pub score: f32,
}

/// ctranslate2.Translator (a pool of replicas; safe to call from several threads).
pub struct Translator(NonNull<c_void>);

unsafe impl Send for Translator {}
unsafe impl Sync for Translator {}

impl Translator {
    pub fn new(path: &Path, config: &ModelConfig) -> Result<Self> {
        Ok(Self(new_pool(ffi::ct2_translator_new, path, config)?))
    }

    /// translate_batch([source], target_prefix=[target_prefix]) for one sentence.
    pub fn translate(&self, source: &[String], target_prefix: &[String], options: &TranslateOptions) -> Result<Vec<Hypothesis>> {
        let (src, prefix) = (joined(source)?, joined(target_prefix)?);
        let r = check(unsafe {
            ffi::ct2_translate(self.0.as_ptr(), src.as_ptr().cast(), source.len(), prefix.as_ptr().cast(),
                               target_prefix.len(), options)
        })?
        .as_ptr();
        let hypotheses = unsafe {
            (0..ffi::ct2_translation_num_hypotheses(r))
                .map(|i| Hypothesis {
                    tokens: (0..ffi::ct2_translation_hypothesis_len(r, i))
                        .map(|j| string_at(ffi::ct2_translation_token(r, i, j)))
                        .collect(),
                    score: ffi::ct2_translation_score(r, i),
                })
                .collect()
        };
        unsafe { ffi::ct2_translation_free(r) };
        Ok(hypotheses)
    }
}

impl Drop for Translator {
    fn drop(&mut self) {
        unsafe { ffi::ct2_translator_free(self.0.as_ptr()) }
    }
}

// ---- Whisper ---------------------------------------------------------------------------------

/// generate options (WhisperOptions). `Default` is CTranslate2's (suppress_tokens = [-1]).
#[derive(Clone, Debug)]
pub struct WhisperOptions {
    pub beam_size: usize,
    pub patience: f32,
    pub length_penalty: f32,
    pub repetition_penalty: f32,
    pub no_repeat_ngram_size: usize,
    pub max_length: usize,
    pub sampling_topk: usize,
    pub sampling_temperature: f32,
    pub num_hypotheses: usize,
    pub return_scores: bool,
    pub return_no_speech_prob: bool,
    pub max_initial_timestamp_index: usize,
    pub suppress_blank: bool,
    pub suppress_tokens: Vec<i32>,
}

impl Default for WhisperOptions {
    fn default() -> Self {
        let mut o = std::mem::MaybeUninit::<ffi::WhisperOptions>::uninit();
        let o = unsafe {
            ffi::ct2_whisper_options_default(o.as_mut_ptr());
            o.assume_init()
        };
        Self {
            beam_size: o.beam_size,
            patience: o.patience,
            length_penalty: o.length_penalty,
            repetition_penalty: o.repetition_penalty,
            no_repeat_ngram_size: o.no_repeat_ngram_size,
            max_length: o.max_length,
            sampling_topk: o.sampling_topk,
            sampling_temperature: o.sampling_temperature,
            num_hypotheses: o.num_hypotheses,
            return_scores: o.return_scores,
            return_no_speech_prob: o.return_no_speech_prob,
            max_initial_timestamp_index: o.max_initial_timestamp_index,
            suppress_blank: o.suppress_blank,
            suppress_tokens: vec![-1],
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct Generation {
    pub sequences: Vec<Vec<usize>>,
    /// empty unless `return_scores`
    pub scores: Vec<f32>,
    pub no_speech_prob: f32,
}

/// Encoder output (a StorageView on the model's device).
pub struct Encoded(NonNull<c_void>);

unsafe impl Send for Encoded {}

impl Drop for Encoded {
    fn drop(&mut self) {
        unsafe { ffi::ct2_storage_free(self.0.as_ptr()) }
    }
}

/// ctranslate2.models.Whisper (a pool of replicas; safe to call from several threads).
pub struct Whisper(NonNull<c_void>);

unsafe impl Send for Whisper {}
unsafe impl Sync for Whisper {}

impl Whisper {
    pub fn new(path: &Path, config: &ModelConfig) -> Result<Self> {
        Ok(Self(new_pool(ffi::ct2_whisper_new, path, config)?))
    }

    pub fn is_multilingual(&self) -> bool {
        unsafe { ffi::ct2_whisper_is_multilingual(self.0.as_ptr()) }
    }

    pub fn n_mels(&self) -> usize {
        unsafe { ffi::ct2_whisper_n_mels(self.0.as_ptr()) }
    }

    /// encode(features [1, n_mels, frames], to_cpu=False)
    pub fn encode(&self, features: &[f32], n_mels: usize, frames: usize) -> Result<Encoded> {
        if features.len() != n_mels * frames {
            bail!("features: {} values for {n_mels} x {frames}", features.len());
        }
        // The StorageView only wraps the buffer, and encode reads it.
        let p = features.as_ptr().cast_mut();
        Ok(Encoded(check(unsafe { ffi::ct2_whisper_encode(self.0.as_ptr(), p, 1, n_mels, frames, false) })?))
    }

    /// detect_language(encoder_output)[0]: (token, probability), most probable first.
    pub fn detect_language(&self, encoded: &Encoded) -> Result<Vec<(String, f32)>> {
        let l = check(unsafe { ffi::ct2_whisper_detect_language(self.0.as_ptr(), encoded.0.as_ptr()) })?.as_ptr();
        let langs = unsafe {
            (0..ffi::ct2_languages_len(l))
                .map(|i| (string_at(ffi::ct2_languages_token(l, i)), ffi::ct2_languages_prob(l, i)))
                .collect()
        };
        unsafe { ffi::ct2_languages_free(l) };
        Ok(langs)
    }

    /// generate(encoder_output, [prompt], ...)[0]
    pub fn generate(&self, encoded: &Encoded, prompt: &[usize], o: &WhisperOptions) -> Result<Generation> {
        let options = ffi::WhisperOptions {
            beam_size: o.beam_size,
            patience: o.patience,
            length_penalty: o.length_penalty,
            repetition_penalty: o.repetition_penalty,
            no_repeat_ngram_size: o.no_repeat_ngram_size,
            max_length: o.max_length,
            sampling_topk: o.sampling_topk,
            sampling_temperature: o.sampling_temperature,
            num_hypotheses: o.num_hypotheses,
            return_scores: o.return_scores,
            return_no_speech_prob: o.return_no_speech_prob,
            max_initial_timestamp_index: o.max_initial_timestamp_index,
            suppress_blank: o.suppress_blank,
            suppress_tokens: o.suppress_tokens.as_ptr(),
            suppress_tokens_len: o.suppress_tokens.len(),
        };
        let r = check(unsafe {
            ffi::ct2_whisper_generate(self.0.as_ptr(), encoded.0.as_ptr(), prompt.as_ptr(), prompt.len(), &options)
        })?
        .as_ptr();
        let generation = unsafe {
            let n = ffi::ct2_generation_num_sequences(r);
            Generation {
                sequences: (0..n)
                    .map(|i| std::slice::from_raw_parts(ffi::ct2_generation_sequence(r, i), ffi::ct2_generation_sequence_len(r, i)).to_vec())
                    .collect(),
                scores: if o.return_scores { (0..n).map(|i| ffi::ct2_generation_score(r, i)).collect() } else { vec![] },
                no_speech_prob: ffi::ct2_generation_no_speech_prob(r),
            }
        };
        unsafe { ffi::ct2_generation_free(r) };
        Ok(generation)
    }
}

impl Drop for Whisper {
    fn drop(&mut self) {
        unsafe { ffi::ct2_whisper_free(self.0.as_ptr()) }
    }
}
