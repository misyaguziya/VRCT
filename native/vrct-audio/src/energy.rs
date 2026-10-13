//! Energy phrase detection, matching the pinned SpeechRecognition listener.
//! Derived behavior: see native/vrct-backend/GOOGLE_SPEECH_LICENSE.txt.
use std::collections::VecDeque;


const MAX_BUFFER_BYTES: usize = 64 * 1024 * 1024;

pub fn rms(pcm: &[u8]) -> Result<u32, &'static str> {
    if pcm.len() % 2 != 0 || pcm.len() > MAX_BUFFER_BYTES {
        return Err("expected bounded PCM16LE samples");
    }
    if pcm.is_empty() {
        return Ok(0);
    }
    // Up to 2^23 samples, the sum of PCM16 squares is <= 2^53, so every
    // addition is exactly representable in f64. An integer reduction lets LLVM
    // vectorize without changing audioop's sequential-floating-point result.
    // Retain its original summation order for larger public-API inputs.
    let sum: f64 = if pcm.len() <= 16 * 1024 * 1024 {
        pcm.chunks_exact(2)
            .map(|s| {
                let value = i64::from(i16::from_le_bytes([s[0], s[1]]));
                (value * value) as u64
            })
            .sum::<u64>() as f64
    } else {
        pcm.chunks_exact(2)
            .map(|s| f64::from(i16::from_le_bytes([s[0], s[1]])).powi(2))
            .sum()
    };
    Ok((sum / (pcm.len() / 2) as f64).sqrt() as u32)
}

pub struct EnergyDetector {
    energy_threshold: f64,
    dynamic: bool,
    damping: f64,
    ratio: f64,
    seconds: f64,
    pause_buffers: usize,
    phrase_buffers: usize,
    keep_buffers: usize,
    phrase_limit: f64,
    record_timeout: f64,
    wait_timeout: f64,
    elapsed: f64,
    started_audio: f64,
    started_wall: f64,
    recording: bool,
    pause_count: usize,
    phrase_count: usize,
    frames: VecDeque<Vec<u8>>,
    buffered_bytes: usize,
    finished: bool,
    eof: bool,
    // Quiet buffers a waiting detector may still read and count the next phrase
    // as the direct continuation of a time-limit split (0 = not a continuation).
    continuation: usize,
}

impl EnergyDetector {
    fn clear_phrase(&mut self) {
        self.frames.clear();
        self.buffered_bytes = 0;
        self.recording = false;
        self.pause_count = 0;
        self.phrase_count = 0;
        self.finished = false;
        self.eof = false;
    }

    fn finish(&mut self) -> Option<Vec<u8>> {
        // Unlike the fork, a continuation is never rejected as too short: it is
        // the tail of speech that a time limit cut, e.g. a word ending.
        let accepted = self.phrase_count.saturating_sub(self.pause_count) >= self.phrase_buffers
            || self.eof
            || self.continuation > 0;
        self.continuation = 0;
        let output = if accepted {
            for _ in 0..self.pause_count.saturating_sub(self.keep_buffers) {
                self.frames.pop_back();
            }
            let size = self.frames.iter().map(Vec::len).sum();
            let mut joined = Vec::with_capacity(size);
            for frame in &self.frames {
                joined.extend_from_slice(frame);
            }
            Some(joined)
        } else {
            None
        };
        self.clear_phrase();
        if accepted {
            self.elapsed = 0.0;
        }
        output
    }

    /// Ends a phrase still in progress at a time limit; speech may go on.
    fn split(&mut self) -> Option<Vec<u8>> {
        let output = self.finish();
        if output.is_some() {
            // Same length as the pause that ends a phrase (pause_count > pause_buffers).
            self.continuation = self.pause_buffers + 1;
        }
        output
    }

    fn step(&mut self, now: f64) -> (&'static str, Option<Vec<u8>>) {
        if self.finished {
            let eof = self.eof;
            if let Some(audio) = self.finish() {
                return (if eof { "EOF" } else { "PHRASE" }, Some(audio));
            }
        }
        if self.recording
            && self.record_timeout > 0.0
            && now - self.started_wall > self.record_timeout
        {
            // The fork dropped the phrase here; it races the audio-time phrase
            // limit when both are equal, so emit it. The listen still ends.
            let audio = self.split();
            self.elapsed = 0.0;
            return match audio {
                Some(audio) => ("PHRASE", Some(audio)),
                None => ("RETRY", None),
            };
        }
        self.elapsed += self.seconds;
        if self.recording {
            if self.phrase_limit > 0.0 && self.elapsed - self.started_audio > self.phrase_limit {
                if let Some(audio) = self.split() {
                    return ("PHRASE", Some(audio));
                }
                // A rejected short phrase immediately resumes waiting within the same listen.
                return self.step(now);
            }
        } else if self.wait_timeout > 0.0 && self.elapsed > self.wait_timeout {
            self.cancel();
            return ("RETRY", None);
        }
        ("READ", None)
    }

    fn push_pcm(&mut self, input: &[u8], now: f64) -> Result<u32, &'static str> {
        let energy = rms(input)?;
        if !now.is_finite() || self.finished {
            return Err("invalid detector transition");
        }
        if input.is_empty() {
            self.eof = true;
            self.finished = true;
            return Ok(energy);
        }
        if self.buffered_bytes + input.len() > MAX_BUFFER_BYTES {
            return Err("energy phrase buffer exceeds 64 MiB");
        }
        self.frames.push_back(input.to_vec());
        self.buffered_bytes += input.len();
        if self.recording {
            self.phrase_count += 1;
            self.pause_count = if f64::from(energy) > self.energy_threshold {
                0
            } else {
                self.pause_count + 1
            };
            self.finished = self.pause_count > self.pause_buffers;
        } else {
            if self.frames.len() > self.keep_buffers {
                self.buffered_bytes -= self.frames.pop_front().unwrap().len();
            }
            if f64::from(energy) > self.energy_threshold {
                self.recording = true;
                self.started_audio = self.elapsed;
                self.started_wall = now;
            } else {
                self.continuation = self.continuation.saturating_sub(1);
                if self.dynamic {
                    self.calibrate(energy);
                }
            }
        }
        Ok(energy)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn detector() -> EnergyDetector {
        EnergyDetector::new(
            16000,
            1024,
            300.0,
            false,
            0.0,
            f64::INFINITY,
            1.0,
            0.8,
            0.3,
            0.5,
            0.15,
            1.5,
        )
        .unwrap()
    }

    #[test]
    fn rms_uses_signed_samples_and_truncates() {
        assert_eq!(rms(&[]), Ok(0));
        assert_eq!(rms(&[0, 128]), Ok(32768));
        assert_eq!(rms(&[1, 0, 2, 0]), Ok(1));
        assert!(rms(&[0]).is_err());
    }

    #[test]
    fn finish_discards_short_phrase_but_eof_accepts_it() {
        let mut state = detector();
        state.frames.push_back(vec![1, 0]);
        state.phrase_count = 1;
        assert_eq!(state.finish(), None);
        state.frames.push_back(vec![2, 0]);
        state.eof = true;
        assert_eq!(state.finish(), Some(vec![2, 0]));
        assert!(!state.recording);
        assert!(state.frames.is_empty());
    }

    #[test]
    fn cancel_keeps_calibration_but_drops_phrase() {
        let mut state = detector();
        state.calibrate(100);
        let threshold = state.energy_threshold;
        state.frames.push_back(vec![1, 0]);
        state.elapsed = 10.0;
        state.recording = true;
        state.cancel();
        assert!(state.waiting());
        assert_eq!(state.elapsed, 0.0);
        assert_eq!(state.energy_threshold, threshold);
        assert!(state.frames.is_empty());
    }

    /// Non-READ actions with phrase sizes in buffers, up to the first RETRY.
    fn drive(state: &mut EnergyDetector, values: &[i16]) -> Vec<(&'static str, usize)> {
        let (mut now, mut reads, mut out) = (0.0, values.iter(), Vec::new());
        loop {
            let (action, audio) = state.step(now);
            if action != "READ" {
                out.push((action, audio.map_or(0, |a| a.len() / 2048)));
                if action == "RETRY" {
                    return out;
                }
                continue;
            }
            let value = *reads.next().expect("RETRY before input ends");
            now += state.seconds;
            state
                .push_pcm(&value.to_le_bytes().repeat(1024), now)
                .unwrap();
        }
    }

    #[test]
    fn record_timeout_emits_long_phrase_instead_of_dropping_it() {
        let mut state = detector();
        state.record_timeout = 0.5;
        // Trigger at read 1 (wall 0.064); the wall limit passes after read 9.
        let mut values = vec![2000; 9];
        values.extend([0; 40]);
        assert_eq!(drive(&mut state, &values), [("PHRASE", 9), ("RETRY", 0)]);
        let mut state = detector();
        state.record_timeout = 0.1;
        // Still too short for phrase_threshold: dropped as before.
        assert_eq!(drive(&mut state, &[2000; 40])[0], ("RETRY", 0));
    }

    fn split_then(quiet: usize) -> Vec<(&'static str, usize)> {
        let mut state = detector();
        state.phrase_limit = 0.7; // Splits after 11 buffers.
        let mut values = vec![2000; 11];
        values.extend(std::iter::repeat_n(0, quiet));
        values.extend([2000; 3]);
        values.extend([0; 40]);
        drive(&mut state, &values)
    }

    #[test]
    fn continuation_of_split_is_not_rejected_as_short() {
        // 3 loud + 14 pause buffers, trimmed to keep_buffers: 11 buffers.
        assert_eq!(
            split_then(0),
            [("PHRASE", 11), ("PHRASE", 11), ("RETRY", 0)]
        );
        // Within the pause threshold it is still a continuation (+7 pre-roll buffers).
        assert_eq!(
            split_then(13),
            [("PHRASE", 11), ("PHRASE", 18), ("RETRY", 0)]
        );
        // After a real pause, the short blip is rejected as in the fork.
        assert_eq!(split_then(14), [("PHRASE", 11), ("RETRY", 0)]);
    }

    #[test]
    fn quiet_after_split_emits_nothing() {
        let mut state = detector();
        state.phrase_limit = 0.7;
        let mut values = vec![2000; 11];
        values.extend([0; 40]);
        assert_eq!(drive(&mut state, &values), [("PHRASE", 11), ("RETRY", 0)]);
    }
}

impl EnergyDetector {
    // These parameters mirror existing Recognizer settings; no new app settings.
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        sample_rate: u32,
        chunk: usize,
        energy_threshold: f64,
        dynamic: bool,
        phrase_time_limit: f64,
        record_timeout: f64,
        wait_timeout: f64,
        pause_threshold: f64,
        phrase_threshold: f64,
        non_speaking_duration: f64,
        damping: f64,
        ratio: f64,
    ) -> Result<Self, &'static str> {
        if sample_rate == 0
            || chunk == 0
            || chunk > MAX_BUFFER_BYTES / 2
            || !energy_threshold.is_finite()
            || energy_threshold < 0.0
            || !pause_threshold.is_finite()
            || !phrase_threshold.is_finite()
            || !non_speaking_duration.is_finite()
            || phrase_threshold < 0.0
            || non_speaking_duration < 0.0
            || pause_threshold < non_speaking_duration
            || !damping.is_finite()
            || !(0.0..=1.0).contains(&damping)
            || !ratio.is_finite()
            || ratio < 0.0
            || phrase_time_limit.is_nan()
            || record_timeout.is_nan()
            || wait_timeout.is_nan()
        {
            return Err("invalid energy detector settings");
        }
        let seconds = chunk as f64 / f64::from(sample_rate);
        Ok(Self {
            energy_threshold,
            dynamic,
            damping: damping.powf(seconds),
            ratio,
            seconds,
            pause_buffers: (pause_threshold / seconds).ceil() as usize,
            phrase_buffers: (phrase_threshold / seconds).ceil() as usize,
            keep_buffers: (non_speaking_duration / seconds).ceil() as usize,
            phrase_limit: phrase_time_limit,
            record_timeout,
            wait_timeout,
            elapsed: 0.0,
            started_audio: 0.0,
            started_wall: 0.0,
            recording: false,
            pause_count: 0,
            phrase_count: 0,
            frames: VecDeque::new(),
            buffered_bytes: 0,
            finished: false,
            eof: false,
            continuation: 0,
        })
    }

    /// Called once before each read. RETRY is a listen boundary for pause handling.
    pub fn before_read(&mut self, now: f64) -> Result<(&'static str, Option<Vec<u8>>), &'static str> {
        if !now.is_finite() {
            return Err("invalid monotonic time");
        }
        Ok(self.step(now))
    }

    /// PCM is interleaved for speakers, matching audioop.rms on the legacy input.
    pub fn push(&mut self, pcm: &[u8], now: f64) -> Result<u32, &'static str> {
        self.push_pcm(pcm, now)
    }

    pub fn calibrate(&mut self, energy: u32) {
        self.energy_threshold = self.energy_threshold * self.damping
            + f64::from(energy) * self.ratio * (1.0 - self.damping);
    }

    pub fn waiting(&self) -> bool {
        !self.recording
    }

    pub fn cancel(&mut self) {
        self.clear_phrase();
        self.elapsed = 0.0;
    }

    pub fn energy_threshold(&self) -> f64 {
        self.energy_threshold
    }
}
