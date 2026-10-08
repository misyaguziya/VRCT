"""Offline per-clip provider preparation benchmark; no inference or network.

Each trial creates fresh PcmAudio and then prepares 1/3/5 language candidates.
The previous classes preserve the pre-cache raw/WAV and Whisper preparation.
Conversion ordering attribution: src-python/models/transcription/google_speech_LICENSE.txt.
"""

import argparse
import audioop
from dataclasses import dataclass
import hashlib
from io import BytesIO
import json
from pathlib import Path
import platform
import statistics
import sys
import time
from types import SimpleNamespace
import wave

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src-python"))
from models.transcription.pcm_audio import PcmAudio  # noqa: E402
from models.transcription.transcription_providers import LocalWhisperProvider, transcription_lang  # noqa: E402


@dataclass(frozen=True)
class PreviousPcmAudio:
    frame_data: bytes
    sample_rate: int
    sample_width: int
    channels: int = 1

    __post_init__ = PcmAudio.__post_init__  # The constructor validation is unchanged.

    def get_raw_data(self, convert_rate=None, convert_width=None):
        rate = self.sample_rate if convert_rate is None else convert_rate
        width = self.sample_width if convert_width is None else convert_width
        if type(rate) is not int or rate <= 0:
            raise ValueError("conversion rate must be a positive integer")
        if type(width) is not int or not 1 <= width <= 4:
            raise ValueError("conversion width must be between 1 and 4")
        raw = self.frame_data
        if self.sample_width == 1:
            raw = audioop.bias(raw, 1, -128)
        if rate != self.sample_rate:
            raw, _ = audioop.ratecv(raw, self.sample_width, 1, self.sample_rate, rate, None)
        if width != self.sample_width:
            raw = audioop.lin2lin(raw, self.sample_width, width)
        if width == 1:
            raw = audioop.bias(raw, 1, 128)
        return raw

    def get_wav_data(self, convert_rate=None, convert_width=None):
        raw = self.get_raw_data(convert_rate, convert_width)
        with BytesIO() as output:
            with wave.open(output, "wb") as writer:
                writer.setnchannels(1)
                writer.setsampwidth(self.sample_width if convert_width is None else convert_width)
                writer.setframerate(self.sample_rate if convert_rate is None else convert_rate)
                writer.writeframes(raw)
            return output.getvalue()


class PreviousWhisperProvider(LocalWhisperProvider):
    def transcribe(self, audio_data, language, country, *, avg_logprob, no_speech_prob,
                   no_repeat_ngram_size, force_language):
        raw = np.frombuffer(
            audio_data.get_raw_data(convert_rate=16000, convert_width=2), np.int16
        ).flatten().astype(np.float32) / 32768.0
        source_language = transcription_lang[language][country]["Whisper"] if force_language else None
        segments, info = self._whisper_model.transcribe(
            raw, beam_size=5, temperature=0.0, log_prob_threshold=avg_logprob,
            no_speech_threshold=no_speech_prob, language=source_language,
            word_timestamps=False, without_timestamps=True, task="transcribe",
            no_repeat_ngram_size=no_repeat_ngram_size,
        )
        text = ""
        for segment in segments:
            if segment.avg_logprob < avg_logprob or segment.no_speech_prob > no_speech_prob:
                continue
            text += segment.text
        is_definitive = force_language or transcription_lang[language][country]["Whisper"] == info.language
        return text, info.language_probability, is_definitive


class InputSink:
    def transcribe(self, samples, **kwargs):
        self.samples = samples
        return (), SimpleNamespace(language="en", language_probability=0.5)


def runner(kind, previous, pcm, rate, candidates):
    audio_type = PreviousPcmAudio if previous else PcmAudio
    sink = InputSink()
    provider = (PreviousWhisperProvider if previous else LocalWhisperProvider)(sink)

    def run():
        audio = audio_type(pcm, rate, 2)  # A new utterance for every timed invocation.
        for _ in range(candidates):
            if kind == "raw":
                output = audio.get_raw_data(16000, 2)
            elif kind == "wav":
                output = audio.get_wav_data(16000, 2)
            else:
                provider.transcribe(
                    audio, "English", "United States", avg_logprob=-0.8,
                    no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=False,
                )
                output = sink.samples
        return output
    return run


def compare(kind, rate, seconds, candidates, repeats):
    pcm = np.random.default_rng(615).integers(-32768, 32768, rate * seconds, dtype="<i2").tobytes()
    methods = {"previous": runner(kind, True, pcm, rate, candidates),
               "current": runner(kind, False, pcm, rate, candidates)}
    previous, current = methods["previous"](), methods["current"]()
    if kind == "whisper":
        np.testing.assert_array_equal(previous, current)
    else:
        assert previous == current
    # Batch only the tiny no-resampling cases; every iteration still gets fresh audio.
    batch = 100 if rate == 16000 else 1
    trials = {"previous": [], "current": []}
    for iteration in range(repeats):
        order = ("previous", "current") if iteration % 2 == 0 else ("current", "previous")
        for name in order:
            started = time.perf_counter_ns()
            for _ in range(batch):
                methods[name]()
            trials[name].append((time.perf_counter_ns() - started) / batch / 1_000_000)
    return {
        "operation": kind, "rate": rate, "seconds": seconds, "candidates": candidates,
        "batch": batch, "input_equal": True,
        **{name + "_median_ms": statistics.median(values) for name, values in trials.items()},
        "trials_ms": trials,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=9)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    root = Path(__file__).resolve().parents[1]
    paths = ["src-python/models/transcription/pcm_audio.py",
             "src-python/models/transcription/transcription_providers.py",
             "tools/benchmark_audio_preparation.py"]
    report = {
        "python": sys.version, "platform": platform.platform(), "numpy": np.__version__,
        "repeats": args.repeats, "fresh_clip_each_trial": True,
        "baseline_pcm_sha256": "501cd5adbf4952cfd39e29da8b59bb708616df84e628358b7a7fbeba09874a57",
        "baseline_provider_sha256": "9e873e4e2eaa89052021038878d07e85d883cf9b62bbcc71ff90c5c8ebd41061",
        "source_sha256": {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in paths},
        "results": [compare(kind, rate, seconds, candidates, args.repeats)
                    for kind in ("raw", "wav", "whisper") for rate in (16000, 44100, 48000)
                    for seconds in (3, 15) for candidates in (1, 3, 5)],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {len(report['results'])} cases, equivalent inputs; report: {args.output}")


if __name__ == "__main__":
    main()
