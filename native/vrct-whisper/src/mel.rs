//! Log-mel features as faster-whisper 1.1.1's FeatureExtractor computes them with numpy 1.26. The
//! arithmetic follows numpy step by step so the float32 results round the same way: the filter bank
//! in float64 (linspace / rfftfreq / hanning as numpy writes them), frames * window in float32, the
//! FFT in float64 (numpy < 2 promotes float32 to double) cast to complex64, |z| as numpy's SIMD loop
//! does, `filters @ power` through numpy's own OpenBLAS, then float32 from there on.
use anyhow::{anyhow, Context, Result};
use rustfft::{num_complex::Complex64, FftPlanner};
use std::path::Path;
use std::sync::OnceLock;

pub const SAMPLE_RATE: usize = 16000;
pub const N_FFT: usize = 400;
pub const HOP: usize = 160;
const N_FREQ: usize = N_FFT / 2 + 1;
/// chunk_length 30 s: nb_max_frames
pub const N_FRAMES: usize = 3000;
/// hop_length / sampling_rate
pub const TIME_PER_FRAME: f64 = HOP as f64 / SAMPLE_RATE as f64;

/// FeatureExtractor.get_mel_filters (Slaney scale, slaney norm) cast to float32, [n_mels][N_FREQ].
fn mel_filters(n_mels: usize) -> Vec<f32> {
    // np.fft.rfftfreq(n, d=1/sr): arange(n//2+1) * (1.0 / (n * d))
    let val = 1.0 / (N_FFT as f64 * (1.0 / SAMPLE_RATE as f64));
    let fftfreqs: Vec<f64> = (0..N_FREQ).map(|i| i as f64 * val).collect();
    // np.linspace(0, 45.245640471924965, n_mels + 2): arange * step + start, last = stop
    let (min_mel, max_mel) = (0.0f64, 45.245640471924965f64);
    let step = (max_mel - min_mel) / (n_mels + 1) as f64;
    let mut mels: Vec<f64> = (0..n_mels + 2).map(|i| i as f64 * step + min_mel).collect();
    mels[n_mels + 1] = max_mel;
    let f_sp = 200.0 / 3.0;
    let min_log_hz = 1000.0;
    let min_log_mel = (min_log_hz - 0.0) / f_sp;
    let logstep = (6.4f64).ln() / 27.0;
    let freqs: Vec<f64> = mels
        .iter()
        .map(|&m| if m >= min_log_mel { min_log_hz * (logstep * (m - min_log_mel)).exp() } else { 0.0 + f_sp * m })
        .collect();
    let mut filters = Vec::with_capacity(n_mels * N_FREQ);
    for m in 0..n_mels {
        let enorm = 2.0 / (freqs[m + 2] - freqs[m]);
        for &f in &fftfreqs {
            let lower = -(freqs[m] - f) / (freqs[m + 1] - freqs[m]);
            let upper = (freqs[m + 2] - f) / (freqs[m + 2] - freqs[m + 1]);
            filters.push((lower.min(upper).max(0.0) * enorm) as f32);
        }
    }
    filters
}

/// np.abs for complex64 as numpy 1.26's SIMD loop computes it (not hypotf): the larger part times
/// sqrt(fma(r, r, 1)) with r = smaller / larger.
fn cabs(re: f32, im: f32) -> f32 {
    let (a, b) = (re.abs(), im.abs());
    let (large, small) = if a >= b { (a, b) } else { (b, a) };
    if large == 0.0 {
        return 0.0;
    }
    let r = small / large;
    large * r.mul_add(r, 1.0).sqrt()
}

/// np.pad(mode="reflect") index: repeated reflection without repeating the edge.
fn reflect(i: isize, n: usize) -> usize {
    if n == 1 {
        return 0;
    }
    let period = 2 * (n as isize - 1);
    let m = i.rem_euclid(period);
    (if m < n as isize { m } else { period - m }) as usize
}

type Sgemm = unsafe extern "C" fn(i32, i32, i32, i64, i64, i64, f32, *const f32, i64, *const f32, i64, f32,
                                  *mut f32, i64);

/// cblas_sgemm64_ of numpy 1.26's bundled OpenBLAS (ILP64, symbol suffix 64_), which `@` calls.
/// Its accumulation order depends on the CPU kernel, so nothing else rounds the same way.
fn sgemm() -> Result<Sgemm> {
    static SGEMM: OnceLock<std::result::Result<Sgemm, String>> = OnceLock::new();
    SGEMM
        .get_or_init(|| {
            // the executable's folder or its `_internal` (the installed layout)
            let exe = std::env::current_exe().map_err(|e| e.to_string())?;
            let dir = exe.parent().ok_or("no exe dir")?;
            let dll = [dir.to_path_buf(), dir.join("_internal")]
                .iter()
                .filter_map(|d| std::fs::read_dir(d).ok())
                .flat_map(|entries| entries.flatten().map(|e| e.path()))
                .find(|p| p.file_name().is_some_and(|n| n.to_string_lossy().starts_with("libopenblas64_")))
                .ok_or_else(|| format!("libopenblas64_*.dll not found in {} or its _internal", dir.display()))?;
            load_sgemm(&dll).map_err(|e| format!("{}: {e}", dll.display()))
        })
        .clone()
        .map_err(|e| anyhow!(e))
}

fn load_sgemm(dll: &Path) -> Result<Sgemm> {
    let lib = unsafe { libloading::Library::new(dll)? };
    let f: Sgemm = *unsafe { lib.get::<Sgemm>(b"cblas_sgemm64_")? };
    std::mem::forget(lib); // kept loaded for the process
    Ok(f)
}

/// Log-mel spectrogram, [n_mels][frames] row-major.
pub struct Features {
    pub data: Vec<f32>,
    pub n_mels: usize,
    pub frames: usize,
}

impl Features {
    /// pad_or_trim(features[:, start..start + len]) to N_FRAMES, zero padded: [n_mels][N_FRAMES].
    pub fn window(&self, start: usize, len: usize) -> Vec<f32> {
        let len = len.min(self.frames.saturating_sub(start)).min(N_FRAMES);
        let mut out = vec![0f32; self.n_mels * N_FRAMES];
        for m in 0..self.n_mels {
            let row = m * self.frames + start;
            out[m * N_FRAMES..m * N_FRAMES + len].copy_from_slice(&self.data[row..row + len]);
        }
        out
    }
}

/// FeatureExtractor(feature_size=n_mels)
pub struct FeatureExtractor {
    n_mels: usize,
    filters: Vec<f32>,
}

impl FeatureExtractor {
    pub fn new(n_mels: usize) -> Self {
        Self { n_mels, filters: mel_filters(n_mels) }
    }

    /// FeatureExtractor.__call__(audio, padding=160); the STFT's last frame is dropped as
    /// `stft[..., :-1]`.
    pub fn compute(&self, audio: &[f32]) -> Result<Features> {
        let mut wave = audio.to_vec();
        wave.extend(std::iter::repeat_n(0.0, HOP)); // padding=160
        // center=True: reflect padding of n_fft/2 on both sides
        let pad = (N_FFT / 2) as isize;
        let n = wave.len();
        let padded: Vec<f32> = (-pad..n as isize + pad).map(|i| wave[reflect(i, n)]).collect();
        let n_frames = 1 + (padded.len() - N_FFT) / HOP;
        // np.hanning(n_fft + 1)[:-1]: 0.5 + 0.5 * cos(pi * n / (M - 1)), n = -400, -398, ...
        let window: Vec<f32> = (0..N_FFT)
            .map(|i| (0.5 + 0.5 * (std::f64::consts::PI * (2 * i as i64 - N_FFT as i64) as f64 / N_FFT as f64).cos()) as f32)
            .collect();
        let fft = FftPlanner::<f64>::new().plan_fft_forward(N_FFT);
        let frames = n_frames - 1; // magnitudes = |stft[..., :-1]|^2
        let mut power = vec![0f32; N_FREQ * frames];
        let mut buf = vec![Complex64::new(0.0, 0.0); N_FFT];
        for t in 0..frames {
            for i in 0..N_FFT {
                buf[i] = Complex64::new((padded[t * HOP + i] * window[i]) as f64, 0.0);
            }
            fft.process(&mut buf);
            for (p, c) in power[t * N_FREQ..(t + 1) * N_FREQ].iter_mut().zip(&buf[..N_FREQ]) {
                let m = cabs(c.re as f32, c.im as f32);
                *p = m * m;
            }
        }
        // mel_filters @ magnitudes: row-major filters [n_mels x N_FREQ] times the F-contiguous
        // [N_FREQ x frames] magnitudes (passed transposed), as numpy hands them to sgemm
        let sgemm = sgemm().context("OpenBLAS (numpy 1.26) for the mel features")?;
        let mut mel = vec![0f32; self.n_mels * frames];
        let (m, k) = (self.n_mels as i64, N_FREQ as i64);
        unsafe {
            sgemm(101, 111, 112, m, frames as i64, k, 1.0, self.filters.as_ptr(), k, power.as_ptr(), k, 0.0,
                  mel.as_mut_ptr(), frames as i64)
        };
        for v in mel.iter_mut() {
            *v = v.max(1e-10).log10();
        }
        let max = mel.iter().cloned().fold(f32::MIN, f32::max);
        for v in mel.iter_mut() {
            *v = (v.max(max - 8.0) + 4.0) / 4.0;
        }
        Ok(Features { data: mel, n_mels: self.n_mels, frames })
    }
}

#[cfg(test)]
mod tests {
    use super::reflect;

    #[test]
    fn reflect_matches_numpy() {
        // np.pad(np.arange(3), 5, mode="reflect") == [1 0 1 2 1 | 0 1 2 | 1 0 1 2 1]
        let got: Vec<usize> = (-5..8).map(|i| reflect(i, 3)).collect();
        assert_eq!(got, [1, 0, 1, 2, 1, 0, 1, 2, 1, 0, 1, 2, 1]);
        assert_eq!(reflect(-3, 1), 0);
    }
}
