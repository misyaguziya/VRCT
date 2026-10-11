//! Integer width conversion and VAD downmix; resampling stays in audioop.ratecv.
use dasp_sample::{Sample, I24};

use crate::{MAX_CHANNELS, MAX_PCM_BYTES};

pub(crate) fn validate(len: usize, width: usize, channels: usize) -> Result<(), &'static str> {
    if !(1..=4).contains(&width) {
        return Err("sample width must be between 1 and 4 bytes");
    }
    if channels == 0 || channels > MAX_CHANNELS {
        return Err("channels must be between 1 and 256");
    }
    if len > MAX_PCM_BYTES {
        return Err("PCM input exceeds 64 MiB");
    }
    if len % width != 0 {
        return Err("expected complete signed little-endian PCM samples");
    }
    if len / width / channels * 2 > MAX_PCM_BYTES {
        return Err("PCM output exceeds 64 MiB");
    }
    Ok(())
}

fn sample16<const WIDTH: usize>(sample: &[u8]) -> i16 {
    match WIDTH {
        1 => i16::from_sample(sample[0] as i8),
        2 => i16::from_le_bytes([sample[0], sample[1]]),
        3 => {
            let signed = i32::from_le_bytes([0, sample[0], sample[1], sample[2]]) >> 8;
            i16::from_sample(I24::new(signed).expect("sign-extended 24-bit sample"))
        }
        4 => i16::from_sample(i32::from_le_bytes([
            sample[0], sample[1], sample[2], sample[3],
        ])),
        _ => unreachable!("validated sample width"),
    }
}

fn normalize<const WIDTH: usize>(pcm: &[u8], channels: usize) -> Vec<u8> {
    let mut output = Vec::with_capacity(pcm.len() / WIDTH / channels * 2);
    if channels == 1 {
        for sample in pcm.chunks_exact(WIDTH) {
            output.extend_from_slice(&sample16::<WIDTH>(sample).to_le_bytes());
        }
        return output;
    }
    for frame in pcm.chunks_exact(WIDTH * channels) {
        // Convert each integer sample before taking the mean, as audioop.lin2lin
        // followed by the VAD normalizer does. Sum fits exactly in f64.
        let sum: i64 = frame
            .chunks_exact(WIDTH)
            .map(|sample| i64::from(sample16::<WIDTH>(sample)))
            .sum();
        let sample = (sum as f64 / channels as f64).round_ties_even() as i16;
        output.extend_from_slice(&sample.to_le_bytes());
    }
    output
}

/// Convert signed PCM8/16/24/32LE to mono PCM16LE. Drop incomplete channel frames.
pub fn normalize_pcm16(pcm: &[u8], sample_width: usize, channels: usize) -> Result<Vec<u8>, &'static str> {
    validate(pcm.len(), sample_width, channels)?;
    Ok(match sample_width {
        1 => normalize::<1>(pcm, channels),
        2 if channels == 1 => pcm.to_vec(),
        2 => normalize::<2>(pcm, channels),
        3 => normalize::<3>(pcm, channels),
        4 => normalize::<4>(pcm, channels),
        _ => unreachable!("validated sample width"),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn width_conversion_matches_signed_shifts() {
        for value in i8::MIN..=i8::MAX {
            assert_eq!(sample16::<1>(&value.to_le_bytes()), i16::from(value) << 8);
        }
        for value in i16::MIN..=i16::MAX {
            assert_eq!(sample16::<2>(&value.to_le_bytes()), value);
        }
        for value in [
            -8_388_608i32,
            -257,
            -256,
            -255,
            -1,
            0,
            1,
            255,
            256,
            8_388_607,
        ] {
            assert_eq!(
                sample16::<3>(&value.to_le_bytes()[..3]),
                (value >> 8) as i16
            );
        }
        for value in [
            i32::MIN,
            -65_537,
            -65_536,
            -1,
            0,
            1,
            65_535,
            65_536,
            i32::MAX,
        ] {
            assert_eq!(sample16::<4>(&value.to_le_bytes()), (value >> 16) as i16);
        }
    }

    #[test]
    fn rounds_after_width_conversion_and_discards_tail() {
        let samples = [0i32, 511, 256, 767, 0, -1, -256, -257, 123];
        let pcm: Vec<_> = samples
            .iter()
            .flat_map(|s| s.to_le_bytes()[..3].to_vec())
            .collect();
        let expected: Vec<_> = [0i16, 2, 0, -2]
            .iter()
            .flat_map(|s| s.to_le_bytes())
            .collect();
        assert_eq!(normalize::<3>(&pcm, 2), expected);
        assert!(normalize::<4>(&[0; 4], 256).is_empty());
    }

    #[test]
    fn validates_before_allocation_including_expanded_output() {
        for (len, width, channels) in [
            (0, 0, 1),
            (0, 5, 1),
            (0, 2, 0),
            (0, 2, 257),
            (1, 2, 1),
            (4, 3, 1),
            (MAX_PCM_BYTES + 1, 1, 2),
            (MAX_PCM_BYTES / 2 + 1, 1, 1),
        ] {
            assert!(validate(len, width, channels).is_err());
        }
        assert!(validate(MAX_PCM_BYTES / 2, 1, 1).is_ok());
        assert!(validate(MAX_PCM_BYTES, 1, 2).is_ok());
        assert!(validate(MAX_PCM_BYTES, 2, 1).is_ok());
        assert!(validate(3, 1, 2).is_ok());
        assert!(validate(0, 4, 256).is_ok());
    }
}
