//! Short-clip audio processing. No recording devices, networking or model loading.
//! The `python` feature builds the extension module the Python backend imports (`vrct_audio`).
use flacenc::{bitsink::ByteSink, component::BitRepr, error::Verify};
pub mod audioop;
#[cfg(feature = "devices")]
pub mod devices;
mod energy;
#[cfg(feature = "devices")]
pub mod endpoints;
mod normalize;
pub mod vad;
#[cfg(feature = "python")]
mod python;

pub use energy::{rms, EnergyDetector};
pub use normalize::normalize_pcm16;

// This limits the input, not the total memory used by the encoder.
const MAX_PCM_BYTES: usize = 64 * 1024 * 1024;
const MAX_CHANNELS: usize = 256;

fn validate_pcm(len: usize, channels: usize) -> Result<(), &'static str> {
    if channels == 0 || channels > MAX_CHANNELS {
        return Err("channels must be between 1 and 256");
    }
    if len > MAX_PCM_BYTES {
        return Err("PCM input exceeds 64 MiB");
    }
    if len % (2 * channels) != 0 {
        return Err("expected complete PCM16LE frames");
    }
    Ok(())
}

fn validate_flac(len: usize, sample_rate: u32) -> Result<(), &'static str> {
    validate_pcm(len, 1)?;
    if len == 0 {
        return Err("FLAC input must not be empty");
    }
    if !(8_000..=96_000).contains(&sample_rate) {
        return Err("FLAC sample rate must be between 8000 and 96000 Hz");
    }
    Ok(())
}

fn mix_frames(pcm: &[u8], channels: usize) -> Vec<u8> {
    if channels == 1 {
        return pcm.to_vec();
    }
    let mut out = Vec::with_capacity(pcm.len() / channels);
    for frame in pcm.chunks_exact(channels * 2) {
        let sum: i64 = frame
            .chunks_exact(2)
            .map(|s| i64::from(i16::from_le_bytes([s[0], s[1]])))
            .sum();
        // Integer PCM sums up to 256 channels are exactly representable in f64.
        // Match np.rint(mean(...)): half-way values round to the even integer.
        let sample = (sum as f64 / channels as f64).round_ties_even() as i16;
        out.extend_from_slice(&sample.to_le_bytes());
    }
    out
}

// Match pydub 0.25.1 set_channels(1): floor each channel separately and
// check the signed-16 accumulator after every addition. See its MIT notice.
fn mix_speaker_frames(pcm: &[u8], channels: usize) -> Result<Vec<u8>, &'static str> {
    let mut out = Vec::with_capacity(pcm.len() / channels);
    for frame in pcm.chunks_exact(channels * 2) {
        let mut sum = 0i32;
        for sample in frame.chunks_exact(2) {
            sum +=
                i32::from(i16::from_le_bytes([sample[0], sample[1]])).div_euclid(channels as i32);
            if sum < i32::from(i16::MIN) || sum > i32::from(i16::MAX) {
                return Err("speaker downmix sample exceeds PCM16 range");
            }
        }
        out.extend_from_slice(&(sum as i16).to_le_bytes());
    }
    Ok(out)
}

/// The speaker transcription downmix (3 to 256 channels), as pydub's set_channels(1)
pub fn speaker_downmix_pcm16(pcm: &[u8], channels: usize) -> Result<Vec<u8>, &'static str> {
    validate_pcm(pcm.len(), channels)?;
    if channels < 3 {
        return Err("speaker downmix requires 3 to 256 channels");
    }
    mix_speaker_frames(pcm, channels)
}

fn encode_samples(pcm: &[u8], sample_rate: u32) -> Result<Vec<u8>, String> {
    let samples: Vec<i32> = pcm
        .chunks_exact(2)
        .map(|s| i32::from(i16::from_le_bytes([s[0], s[1]])))
        .collect();
    // Keep LPC compression while limiting prediction order for short speech clips.
    let mut config = flacenc::config::Encoder::default();
    config.subframe_coding.qlpc.lpc_order = 4;
    let config = config
        .into_verified()
        .map_err(|e| format!("invalid FLAC configuration: {e:?}"))?;
    let source = flacenc::source::MemSource::from_samples(&samples, 1, 16, sample_rate as usize);
    let stream = flacenc::encode_with_fixed_block_size(&config, source, config.block_size)
        .map_err(|e| format!("FLAC encoding failed: {e:?}"))?;
    let mut sink = ByteSink::new();
    stream
        .write(&mut sink)
        .map_err(|e| format!("FLAC serialization failed: {e:?}"))?;
    Ok(sink.as_slice().to_vec())
}

/// Encode mono PCM16LE to a complete FLAC stream without an external process.
pub fn encode_flac(pcm: &[u8], sample_rate: u32) -> Result<Vec<u8>, String> {
    validate_flac(pcm.len(), sample_rate)?;
    encode_samples(pcm, sample_rate)
}

/// VAD downmix, deliberately different from the legacy speaker sum-and-clip.
pub fn downmix_pcm16(pcm: &[u8], channels: usize) -> Result<Vec<u8>, &'static str> {
    validate_pcm(pcm.len(), channels)?;
    Ok(mix_frames(pcm, channels))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn bytes(samples: &[i16]) -> Vec<u8> {
        samples.iter().flat_map(|v| v.to_le_bytes()).collect()
    }

    #[test]
    fn speaker_floors_each_channel_and_preserves_overflow() {
        assert_eq!(
            mix_speaker_frames(&bytes(&[-1, -1, 2]), 3),
            Ok(bytes(&[-2]))
        );
        assert!(mix_speaker_frames(&bytes(&[-32768; 3]), 3).is_err());
        let mut samples = vec![-32768; 253];
        samples.push(32767);
        assert!(mix_speaker_frames(&bytes(&samples), 254).is_err());
        assert_eq!(mix_speaker_frames(&[], 3), Ok(vec![]));
    }

    #[test]
    fn rounds_ties_to_even_in_both_directions() {
        let input = bytes(&[0, 1, 1, 2, 0, -1, -1, -2, 2, 3, -2, -3]);
        assert_eq!(mix_frames(&input, 2), bytes(&[0, 2, 0, -2, 2, -2]));
    }

    #[test]
    fn supports_extremes_and_many_channels() {
        assert_eq!(mix_frames(&bytes(&[32767; 256]), 256), bytes(&[32767]));
        assert_eq!(mix_frames(&bytes(&[-32768; 256]), 256), bytes(&[-32768]));
        assert_eq!(mix_frames(&bytes(&[32767, -32768]), 2), bytes(&[0]));
    }

    #[test]
    fn mono_and_empty_are_unchanged() {
        let input = bytes(&[0, -32768, 32767]);
        assert_eq!(mix_frames(&input, 1), input);
        assert!(mix_frames(&[], 2).is_empty());
    }

    #[test]
    fn rejects_invalid_frames_and_sizes_before_allocation() {
        for (len, channels) in [(1, 1), (2, 2), (0, 0), (0, 257), (MAX_PCM_BYTES + 2, 1)] {
            assert!(validate_pcm(len, channels).is_err());
        }
        assert!(validate_pcm(0, 2).is_ok());
    }

    #[test]
    fn flac_requires_nonempty_supported_rate() {
        assert!(validate_flac(0, 16000).is_err());
        for rate in [0, 7999, 96001, u32::MAX] {
            assert!(validate_flac(2, rate).is_err());
        }
        for rate in [8000, 16000, 44100, 48000, 96000] {
            assert!(validate_flac(2, rate).is_ok());
        }
    }

    #[test]
    fn serializes_short_and_partial_blocks() {
        for len in [1, 4095, 4096, 4097] {
            let flac = encode_samples(&bytes(&vec![123; len]), 16000).unwrap();
            assert!(flac.starts_with(b"fLaC"));
        }
    }
}
