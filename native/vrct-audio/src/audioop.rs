//! The parts of CPython 3.11's audioop that VRCT uses (ratecv, lin2lin, bias, tomono), integer for
//! integer, and PcmAudio's conversions (pcm_audio.py of the removed Python backend) with the WAV
//! file the `wave` module writes.

/// Sample `i` of `width` bytes, signed, scaled to 32 bits (GETSAMPLE32)
fn get32(data: &[u8], width: usize, i: usize) -> i32 {
    let b = &data[i * width..];
    match width {
        1 => (b[0] as i8 as i32) << 24,
        2 => (i16::from_le_bytes([b[0], b[1]]) as i32) << 16,
        3 => i32::from_le_bytes([0, b[0], b[1], b[2]]),
        _ => i32::from_le_bytes([b[0], b[1], b[2], b[3]]),
    }
}

/// SETSAMPLE32: the top `width` bytes of a 32-bit sample
fn put32(out: &mut Vec<u8>, width: usize, value: i32) {
    out.extend_from_slice(&value.to_le_bytes()[4 - width..]);
}

/// The raw signed sample (GETRAWSAMPLE)
fn get_raw(data: &[u8], width: usize, i: usize) -> i64 {
    (get32(data, width, i) >> (32 - 8 * width)) as i64
}

fn put_raw(out: &mut Vec<u8>, width: usize, value: i64) {
    out.extend_from_slice(&(value as i32).to_le_bytes()[..width]);
}

fn gcd(mut a: i64, mut b: i64) -> i64 {
    while b > 0 {
        (a, b) = (b, a % b);
    }
    a
}

/// ratecv's state: the position and the previous / current sample of each channel
#[derive(Clone, Debug, PartialEq)]
pub struct RateState {
    pub d: i32,
    pub samples: Vec<(i32, i32)>,
}

/// audioop.ratecv(fragment, width, nchannels, inrate, outrate, state, weightA, weightB)
#[allow(clippy::too_many_arguments)] // audioop.ratecv's arguments
pub fn ratecv(fragment: &[u8], width: usize, channels: usize, inrate: u32, outrate: u32, state: Option<&RateState>,
              weight_a: u32, weight_b: u32) -> Result<(Vec<u8>, RateState), &'static str> {
    if !(1..=4).contains(&width) || channels == 0 || fragment.len() % (width * channels) != 0 {
        return Err("not a whole number of frames");
    }
    if inrate == 0 || outrate == 0 || weight_a < 1 {
        return Err("bad rate or weights");
    }
    let g = gcd(inrate as i64, outrate as i64);
    let (inrate, outrate) = (inrate as i64 / g, outrate as i64 / g);
    let g = gcd(weight_a as i64, weight_b as i64);
    let (wa, wb) = ((weight_a as i64 / g) as f64, (weight_b as i64 / g) as f64);
    let (mut d, mut prev, mut cur): (i64, Vec<i32>, Vec<i32>) = match state {
        None => (-outrate, vec![0; channels], vec![0; channels]),
        Some(s) if s.samples.len() == channels => {
            (s.d as i64, s.samples.iter().map(|p| p.0).collect(), s.samples.iter().map(|p| p.1).collect())
        }
        Some(_) => return Err("illegal state argument"),
    };
    let mut frames = fragment.len() / (width * channels);
    let mut out = vec![];
    let mut pos = 0;
    loop {
        while d < 0 {
            if frames == 0 {
                let samples = prev.iter().zip(&cur).map(|(&p, &c)| (p, c)).collect();
                return Ok((out, RateState { d: d as i32, samples }));
            }
            for chan in 0..channels {
                prev[chan] = cur[chan];
                let sample = get32(fragment, width, pos);
                pos += 1;
                // a simple digital filter
                cur[chan] = ((wa * sample as f64 + wb * prev[chan] as f64) / (wa + wb)) as i32;
            }
            frames -= 1;
            d += outrate;
        }
        while d >= 0 {
            for chan in 0..channels {
                let value = (prev[chan] as f64 * d as f64 + cur[chan] as f64 * (outrate - d) as f64) / outrate as f64;
                put32(&mut out, width, value as i32);
            }
            d -= inrate;
        }
    }
}

/// audioop.lin2lin(fragment, width, newwidth)
pub fn lin2lin(fragment: &[u8], width: usize, newwidth: usize) -> Vec<u8> {
    let mut out = Vec::with_capacity(fragment.len() / width * newwidth);
    for i in 0..fragment.len() / width {
        put32(&mut out, newwidth, get32(fragment, width, i));
    }
    out
}

/// audioop.bias(fragment, width, bias): added to the unsigned sample, wrapping
pub fn bias(fragment: &[u8], width: usize, bias: i32) -> Vec<u8> {
    let mask: u64 = (1u64 << (8 * width)) - 1;
    let mut out = Vec::with_capacity(fragment.len());
    for i in 0..fragment.len() / width {
        let unsigned = get_raw(fragment, width, i) as u64 & mask;
        put_raw(&mut out, width, (unsigned.wrapping_add(bias as i64 as u64) & mask) as i64);
    }
    out
}

/// audioop.tomono(fragment, width, 1, 1): the two channels summed and clipped
pub fn tomono(fragment: &[u8], width: usize) -> Vec<u8> {
    let (min, max) = (-(1i64 << (8 * width - 1)), (1i64 << (8 * width - 1)) - 1);
    let mut out = Vec::with_capacity(fragment.len() / 2);
    for i in 0..fragment.len() / width / 2 {
        let sum = get_raw(fragment, width, 2 * i) + get_raw(fragment, width, 2 * i + 1);
        put_raw(&mut out, width, sum.clamp(min, max));
    }
    out
}

/// PcmAudio.get_raw_data(convert_rate, convert_width): mono PCM (8-bit unsigned, otherwise signed)
/// at another rate and width
pub fn convert(frame_data: &[u8], sample_rate: u32, sample_width: usize, rate: u32, width: usize) -> Result<Vec<u8>, &'static str> {
    if !(1..=4).contains(&sample_width) || !(1..=4).contains(&width) || sample_rate == 0 || rate == 0 {
        return Err("bad sample rate or width");
    }
    if frame_data.len() % sample_width != 0 {
        return Err("incomplete PCM sample");
    }
    let mut raw = frame_data.to_vec();
    if sample_width == 1 {
        raw = bias(&raw, 1, -128);
    }
    if rate != sample_rate {
        raw = ratecv(&raw, sample_width, 1, sample_rate, rate, None, 1, 0)?.0;
    }
    if width != sample_width {
        raw = lin2lin(&raw, sample_width, width);
    }
    if width == 1 {
        raw = bias(&raw, 1, 128);
    }
    Ok(raw)
}

/// A mono WAV file as Python 3.11's `wave` writes it (no pad byte after odd-sized data)
pub fn wav(raw: &[u8], rate: u32, width: usize) -> Vec<u8> {
    let mut out = Vec::with_capacity(44 + raw.len());
    out.extend_from_slice(b"RIFF");
    out.extend_from_slice(&(36 + raw.len() as u32).to_le_bytes());
    out.extend_from_slice(b"WAVEfmt ");
    out.extend_from_slice(&16u32.to_le_bytes());
    out.extend_from_slice(&1u16.to_le_bytes()); // PCM
    out.extend_from_slice(&1u16.to_le_bytes()); // mono
    out.extend_from_slice(&rate.to_le_bytes());
    out.extend_from_slice(&(rate * width as u32).to_le_bytes());
    out.extend_from_slice(&(width as u16).to_le_bytes());
    out.extend_from_slice(&(width as u16 * 8).to_le_bytes());
    out.extend_from_slice(b"data");
    out.extend_from_slice(&(raw.len() as u32).to_le_bytes());
    out.extend_from_slice(raw);
    out
}

/// Pcm16MonoNormalizer (audio_vad.py): any PCM to 16 kHz mono PCM16, chunk by chunk
pub struct Pcm16MonoNormalizer {
    sample_rate: u32,
    sample_width: usize,
    channels: usize,
    rate_state: Option<RateState>,
}

impl Pcm16MonoNormalizer {
    pub fn new(sample_rate: u32, sample_width: usize, channels: usize) -> Self {
        Self { sample_rate, sample_width, channels: channels.max(1), rate_state: None }
    }

    pub fn reset(&mut self) {
        self.rate_state = None;
    }

    pub fn process(&mut self, data: &[u8]) -> Result<Vec<u8>, &'static str> {
        if data.is_empty() {
            return Ok(vec![]);
        }
        let data = crate::normalize_pcm16(data, self.sample_width, self.channels)?;
        if self.sample_rate == 16000 {
            return Ok(data);
        }
        let (out, state) = ratecv(&data, 2, 1, self.sample_rate, 16000, self.rate_state.as_ref(), 1, 0)?;
        self.rate_state = Some(state);
        Ok(out)
    }
}
