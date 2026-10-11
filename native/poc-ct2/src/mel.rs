//! Log-mel features as faster-whisper 1.1.1's FeatureExtractor computes them with numpy 1.26
//! (shared with poc-ct2dll). The arithmetic follows numpy step by step so the float32 results
//! round the same way: the filter bank in float64 (linspace / rfftfreq / hanning as numpy writes
//! them), frames * window in float32, the FFT in float64 (numpy < 2 promotes float32 to double)
//! cast to complex64, |z| as numpy's SIMD loop does, then float32 from there on.
use rustfft::{num_complex::Complex64, FftPlanner};

pub const SAMPLE_RATE: usize = 16000;
pub const N_FFT: usize = 400;
pub const HOP: usize = 160;
pub const N_MELS: usize = 80;
pub const N_FRAMES: usize = 3000;

/// FeatureExtractor.get_mel_filters (Slaney scale, slaney norm) cast to float32, [n_mels][n_fft/2+1].
pub fn mel_filters() -> Vec<Vec<f32>> {
    let n_freq = N_FFT / 2 + 1;
    // np.fft.rfftfreq(n, d=1/sr): arange(n//2+1) * (1.0 / (n * d))
    let val = 1.0 / (N_FFT as f64 * (1.0 / SAMPLE_RATE as f64));
    let fftfreqs: Vec<f64> = (0..n_freq).map(|i| i as f64 * val).collect();
    // np.linspace(0, 45.245640471924965, n_mels + 2): arange * step + start, last = stop
    let (min_mel, max_mel) = (0.0f64, 45.245640471924965f64);
    let step = (max_mel - min_mel) / (N_MELS + 1) as f64;
    let mut mels: Vec<f64> = (0..N_MELS + 2).map(|i| i as f64 * step + min_mel).collect();
    mels[N_MELS + 1] = max_mel;
    let f_sp = 200.0 / 3.0;
    let min_log_hz = 1000.0;
    let min_log_mel = (min_log_hz - 0.0) / f_sp;
    let logstep = (6.4f64).ln() / 27.0;
    let freqs: Vec<f64> = mels
        .iter()
        .map(|&m| if m >= min_log_mel { min_log_hz * (logstep * (m - min_log_mel)).exp() } else { 0.0 + f_sp * m })
        .collect();
    (0..N_MELS)
        .map(|m| {
            let enorm = 2.0 / (freqs[m + 2] - freqs[m]);
            fftfreqs
                .iter()
                .map(|&f| {
                    let lower = -(freqs[m] - f) / (freqs[m + 1] - freqs[m]);
                    let upper = (freqs[m + 2] - f) / (freqs[m + 2] - freqs[m + 1]);
                    (lower.min(upper).max(0.0) * enorm) as f32
                })
                .collect()
        })
        .collect()
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

/// `filters [n_mels x n_freq] @ power`, where power holds the frames' spectra one after another
/// (the F-contiguous [n_freq x frames] matrix numpy has). Returns [n_mels x frames] row-major.
pub type MatMul<'a> = &'a dyn Fn(&[f32], &[f32], usize) -> Vec<f32>;

/// Fallback for MatMul: an fma chain per cell. numpy's `@` goes through OpenBLAS sgemm, whose
/// accumulation order depends on the CPU kernel; this differs from it by 1 ulp in some cells.
pub fn matmul_fma(filters: &[f32], power: &[f32], frames: usize) -> Vec<f32> {
    let n_freq = N_FFT / 2 + 1;
    let mut out = vec![0f32; N_MELS * frames];
    for m in 0..N_MELS {
        let w = &filters[m * n_freq..(m + 1) * n_freq];
        for t in 0..frames {
            out[m * frames + t] = w.iter().zip(&power[t * n_freq..(t + 1) * n_freq]).fold(0f32, |acc, (a, b)| a.mul_add(*b, acc));
        }
    }
    out
}

/// FeatureExtractor.__call__(audio, padding=160): [n_mels * frames] row-major and frames
/// (the STFT's last frame already dropped, as `stft[..., :-1]`).
pub fn log_mel(audio: &[f32], matmul: MatMul) -> (Vec<f32>, usize) {
    let mut wave = audio.to_vec();
    wave.extend(std::iter::repeat(0.0).take(HOP)); // padding=160
    // center=True, reflect padding of n_fft/2 on both sides
    let pad = N_FFT / 2;
    let mut padded = Vec::with_capacity(wave.len() + 2 * pad);
    padded.extend((1..=pad).rev().map(|i| wave[i]));
    padded.extend_from_slice(&wave);
    padded.extend((1..=pad).map(|i| wave[wave.len() - 1 - i]));
    let n_frames = 1 + (padded.len() - N_FFT) / HOP;
    // np.hanning(n_fft + 1)[:-1]: 0.5 + 0.5 * cos(pi * n / (M - 1)), n = -400, -398, ...
    let window: Vec<f32> = (0..N_FFT)
        .map(|i| (0.5 + 0.5 * (std::f64::consts::PI * (2 * i as i64 - N_FFT as i64) as f64 / N_FFT as f64).cos()) as f32)
        .collect();
    let fft = FftPlanner::<f64>::new().plan_fft_forward(N_FFT);
    let n_freq = N_FFT / 2 + 1;
    let frames = n_frames - 1; // magnitudes = |stft[..., :-1]|^2
    let mut power = vec![0f32; n_freq * frames];
    let mut buf = vec![Complex64::new(0.0, 0.0); N_FFT];
    for t in 0..frames {
        for i in 0..N_FFT {
            buf[i] = Complex64::new((padded[t * HOP + i] * window[i]) as f64, 0.0);
        }
        fft.process(&mut buf);
        for (p, c) in power[t * n_freq..(t + 1) * n_freq].iter_mut().zip(&buf[..n_freq]) {
            let m = cabs(c.re as f32, c.im as f32);
            *p = m * m;
        }
    }
    let filters: Vec<f32> = mel_filters().concat();
    let mut mel = matmul(&filters, &power, frames);
    if let Ok(dir) = std::env::var("POC_MEL_DUMP") {
        // stage outputs for comparing with numpy: power [frames x n_freq], mel before log10, filters
        let bytes = |v: &[f32]| v.iter().flat_map(|x| x.to_le_bytes()).collect::<Vec<u8>>();
        let _ = std::fs::write(format!("{dir}/power.f32"), bytes(&power));
        let _ = std::fs::write(format!("{dir}/melspec.f32"), bytes(&mel));
        let _ = std::fs::write(format!("{dir}/filters.f32"), bytes(&filters));
    }
    for v in mel.iter_mut() {
        *v = v.max(1e-10).log10();
    }
    let max = mel.iter().cloned().fold(f32::MIN, f32::max);
    for v in mel.iter_mut() {
        *v = (v.max(max - 8.0) + 4.0) / 4.0;
    }
    (mel, frames)
}

/// pad_or_trim(mel[:, start..start + len]) to N_FRAMES, zero padded. Returns [n_mels * N_FRAMES].
pub fn window(mel: &[f32], frames: usize, start: usize, len: usize) -> Vec<f32> {
    let len = len.min(frames.saturating_sub(start)).min(N_FRAMES);
    let mut out = vec![0f32; N_MELS * N_FRAMES];
    for m in 0..N_MELS {
        out[m * N_FRAMES..m * N_FRAMES + len].copy_from_slice(&mel[m * frames + start..m * frames + start + len]);
    }
    out
}
