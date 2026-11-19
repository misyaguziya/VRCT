//! Adapted from vrct-whisper/src/mel.rs; same Slaney filters, FFT and normalization.
//! Only the matrix multiplication differs: scalar Rust instead of numpy OpenBLAS.
use anyhow::{ensure, Result};
use rustfft::{num_complex::Complex64, FftPlanner};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::path::Path;

pub const SAMPLE_RATE: usize = 16000;
pub const N_FFT: usize = 400;
pub const HOP: usize = 160;
const N_FREQ: usize = N_FFT / 2 + 1;
/// chunk_length 30 s: nb_max_frames
pub const N_FRAMES: usize = 3000;
pub const N_MELS: usize = 128;
pub const FRONTEND_ID: &str = "vrct_shared_slaney_f32_zero_pad_v1";

/// 両adapterに渡す最終バッファ。作成後の正規化や並び替えを防ぐため不変のsliceだけ公開する。
pub struct PreparedMel {
    data: Vec<f32>,
    original_samples: usize,
}

impl PreparedMel {
    pub fn from_audio(path: &Path) -> Result<Self> {
        Self::from_samples(&crate::benchmark::audio(path)?)
    }

    pub fn from_samples(samples: &[f32]) -> Result<Self> {
        crate::benchmark::validate_sample_count(samples.len())?;
        ensure!(
            samples.iter().all(|v| v.is_finite()),
            "non-finite PCM input"
        );
        let mel = FeatureExtractor::new(N_MELS).compute(samples);
        let data = mel.window(0, mel.frames);
        ensure!(
            data.len() == N_MELS * N_FRAMES && data.iter().all(|v| v.is_finite()),
            "common mel must be finite 128x3000 row-major float32"
        );
        Ok(Self {
            data,
            original_samples: samples.len(),
        })
    }

    pub fn values(&self) -> &[f32] {
        &self.data
    }
    pub fn original_samples(&self) -> usize {
        self.original_samples
    }

    pub fn metadata(&self) -> Value {
        let mut hash = Sha256::new();
        for value in &self.data {
            hash.update(value.to_le_bytes());
        }
        json!({"frontend":FRONTEND_ID,"shape":[N_MELS,N_FRAMES],"layout":"mel_major",
            "dtype":"float32_le","sha256":format!("{:x}",hash.finalize()),
            "original_samples":self.original_samples,
            "duration_ms":self.original_samples/16,
            "valid_mel_frames":(self.original_samples/HOP+1).min(N_FRAMES)})
    }
}

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
        .map(|&m| {
            if m >= min_log_mel {
                min_log_hz * (logstep * (m - min_log_mel)).exp()
            } else {
                0.0 + f_sp * m
            }
        })
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
        Self {
            n_mels,
            filters: mel_filters(n_mels),
        }
    }

    /// FeatureExtractor.__call__(audio, padding=160); the STFT's last frame is dropped as
    /// `stft[..., :-1]`.
    pub fn compute(&self, audio: &[f32]) -> Features {
        let mut wave = audio.to_vec();
        wave.extend(std::iter::repeat_n(0.0, HOP)); // padding=160
                                                    // center=True: reflect padding of n_fft/2 on both sides
        let pad = (N_FFT / 2) as isize;
        let n = wave.len();
        let padded: Vec<f32> = (-pad..n as isize + pad)
            .map(|i| wave[reflect(i, n)])
            .collect();
        let n_frames = 1 + (padded.len() - N_FFT) / HOP;
        // np.hanning(n_fft + 1)[:-1]: 0.5 + 0.5 * cos(pi * n / (M - 1)), n = -400, -398, ...
        let window: Vec<f32> = (0..N_FFT)
            .map(|i| {
                (0.5 + 0.5
                    * (std::f64::consts::PI * (2 * i as i64 - N_FFT as i64) as f64 / N_FFT as f64)
                        .cos()) as f32
            })
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
            for (p, c) in power[t * N_FREQ..(t + 1) * N_FREQ]
                .iter_mut()
                .zip(&buf[..N_FREQ])
            {
                let m = cabs(c.re as f32, c.im as f32);
                *p = m * m;
            }
        }
        // Same filters/power as vrct-whisper, with scalar accumulation to avoid
        // requiring numpy's OpenBLAS DLL. Rounding is not bit-identical to numpy.
        let mut mel = vec![0f32; self.n_mels * frames];
        for (m, filter) in self.filters.chunks_exact(N_FREQ).enumerate() {
            for (t, spectrum) in power.chunks_exact(N_FREQ).enumerate() {
                mel[m * frames + t] = filter.iter().zip(spectrum).map(|(a, b)| a * b).sum();
            }
        }
        for v in mel.iter_mut() {
            *v = v.max(1e-10).log10();
        }
        let max = mel.iter().cloned().fold(f32::MIN, f32::max);
        for v in mel.iter_mut() {
            *v = (v.max(max - 8.0) + 4.0) / 4.0;
        }
        Features {
            data: mel,
            n_mels: self.n_mels,
            frames,
        }
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

    #[test]
    fn common_mel_keeps_original_length_and_hashes_every_padded_value() {
        let mut mel = super::PreparedMel::from_samples(&vec![0.1; 3201]).unwrap();
        let info = mel.metadata();
        assert_eq!(info["shape"], serde_json::json!([128, 3000]));
        assert_eq!(info["original_samples"], 3201);
        assert_eq!(info["duration_ms"], 200);
        assert_eq!(info["valid_mel_frames"], 21);
        assert_eq!(mel.values().len(), 128 * 3000);
        assert_eq!(info["sha256"].as_str().unwrap().len(), 64);
        assert!(mel.values().iter().all(|v| v.is_finite()));
        // 最後のpadding値もdigestに含め、作成後の変更が見逃されないことを確認。
        *mel.data.last_mut().unwrap() = 0.125;
        assert_ne!(mel.metadata()["sha256"], info["sha256"]);
        assert!(super::PreparedMel::from_samples(&vec![0.0; 3199]).is_err());
        assert!(super::PreparedMel::from_samples(&vec![0.0; 480001]).is_err());
        let mut bad = vec![0.0; 3200];
        bad[0] = f32::NAN;
        assert!(super::PreparedMel::from_samples(&bad).is_err());
    }

    #[test]
    fn common_mel_accepts_both_exact_duration_limits_without_changing_shape() {
        for count in [3200, 480000] {
            let mel = super::PreparedMel::from_samples(&vec![0.0; count]).unwrap();
            assert_eq!(mel.original_samples(), count);
            assert_eq!(mel.values().len(), 128 * 3000);
            assert_eq!(mel.metadata()["duration_ms"], count / 16);
        }
    }

    #[test]
    fn bundled_speech_has_finite_80_and_128_mel_windows() {
        let wav = std::io::Cursor::new(crate::UTTERANCE);
        let mut reader = hound::WavReader::new(wav).unwrap();
        let samples: Vec<_> = reader
            .samples::<i16>()
            .map(|s| f32::from(s.unwrap()) / 32768.0)
            .collect();
        for mels in [80, 128] {
            let features = super::FeatureExtractor::new(mels).compute(&samples);
            assert_eq!(features.frames, samples.len() / super::HOP + 1);
            assert_eq!(features.data.len(), mels * features.frames);
            assert!(features.data.iter().all(|x| x.is_finite()));
            let window = features.window(0, features.frames);
            assert_eq!(window.len(), mels * super::N_FRAMES);
            assert!(window[features.frames..super::N_FRAMES]
                .iter()
                .all(|x| *x == 0.0));
        }
    }
}
