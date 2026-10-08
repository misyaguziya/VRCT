"""Offline audio benchmark. Synthetic PCM only; no recording or network requests.

Run with the VRCT venv after installing native/vrct-audio. Reports conversion
latency including Python/Rust copies, not speech recognition or UI latency.
"""

import argparse
from collections import deque
import hashlib
from importlib import import_module
from importlib.metadata import version
from io import BytesIO
import json
from pathlib import Path
import platform
import statistics
import struct
import sys
import time
from types import SimpleNamespace

import av
import numpy as np
from pydub import AudioSegment

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src-python"))
from models.transcription.audio_vad import Pcm16MonoNormalizer  # noqa: E402
from models.transcription.google_speech import encode_flac  # noqa: E402
from models.transcription.native_audio import get_native_audio  # noqa: E402
from models.transcription.transcription_transcriber import AudioTranscriber  # noqa: E402


def measure_pair(old, new, repeats, batch=1):
    times = {"old": [], "native": []}
    funcs = {"old": old, "native": new}
    old()
    new()
    for iteration in range(repeats):
        order = ("old", "native") if iteration % 2 == 0 else ("native", "old")
        for name in order:
            started = time.perf_counter_ns()
            for _ in range(batch):
                funcs[name]()
            times[name].append((time.perf_counter_ns() - started) / batch / 1_000_000)
    return {name + "_median_ms": statistics.median(values) for name, values in times.items()}



def measure_single(function, repeats, batch=1):
    function()
    trials = []
    for _ in range(repeats):
        started = time.perf_counter_ns()
        for _ in range(batch):
            function()
        trials.append((time.perf_counter_ns() - started) / batch / 1_000_000)
    return {"native_median_ms": statistics.median(trials), "native_trials_ms": trials}


def decode(encoded, rate):
    with av.open(BytesIO(encoded)) as container:
        assert container.streams.audio[0].sample_rate == rate
        frames = list(container.decode(audio=0))
        assert all(f.format.name == "s16" and len(f.layout.channels) == 1 for f in frames)
        return b"".join(f.to_ndarray().astype("<i2").tobytes() for f in frames)


def benchmark_conversion(native, repeats):
    results = []
    for rate, seconds in [(16000, 3), (16000, 15), (48000, 3), (48000, 15)]:
        t = np.arange(rate * seconds) / rate
        rng = np.random.default_rng(123)
        pcm = (np.sin(2 * np.pi * 220 * t) * 8000 + rng.normal(0, 900, len(t))).astype("<i2").tobytes()
        def run():
            return encode_flac(pcm, rate)
        encoded = run()
        assert decode(encoded, rate) == pcm
        results.append({
            "operation": "flac", "rate": rate, "seconds": seconds,
            "native_bytes": len(encoded), **measure_single(run, repeats),
        })
    for rate, channels in [(16000, 2), (48000, 2), (48000, 6)]:
        count = int(rate * 0.032) * channels
        pcm = np.random.default_rng(123).integers(-32768, 32768, count, dtype=np.int16).astype("<i2").tobytes()
        old = Pcm16MonoNormalizer(rate, 2, channels)
        old._native_audio = None  # benchmark the unchanged fallback on identical data
        new = Pcm16MonoNormalizer(rate, 2, channels)
        assert new._native_audio is native
        for _ in range(10):
            assert old.process(pcm) == new.process(pcm)
        results.append({
            "operation": "normalizer_32ms", "rate": rate, "channels": channels,
            **measure_pair(lambda: old.process(pcm), lambda: new.process(pcm), repeats, batch=1000),
        })
    return results


class SyntheticSource:
    """Already available PCM; no device, sleeps, thread, or real-time pacing."""

    SAMPLE_WIDTH = 2
    CHUNK = 1024

    def __init__(self, chunks, rate):
        self.SAMPLE_RATE = rate
        self.chunks = deque(chunks)
        self.stream = self
        self.pyaudio_stream = self
        self.read_count = 0

    def read(self, count):
        assert count == self.CHUNK
        self.read_count += 1
        return self.chunks.popleft() if self.chunks else b""

    def get_read_available(self):
        return self.CHUNK


def benchmark_energy(native, repeats):
    results = []

    def on_energy(_energy):
        pass

    for rate, channels in [(16000, 1), (48000, 1), (48000, 2)]:
        chunks = [struct.pack("<h", value) * (1024 * channels)
                  for value in [0] * 4 + [2000] * 200 + [0] * 50]

        def new():
            source = SyntheticSource(chunks, rate)
            detector = native.EnergyDetector(rate, 1024, 300, False, 3, float("inf"), 1)
            for _ in range(len(chunks) + 1):
                action, audio = detector.before_read(time.monotonic())
                if action != "READ":
                    assert action == "PHRASE"
                    return audio, source.read_count
                assert not detector.waiting or source.get_read_available() != 0
                raw = source.read(source.CHUNK)
                on_energy(detector.push(raw, time.monotonic()))
            raise AssertionError("detector did not finish")

        expected = new()
        assert new() == expected  # Deterministic native output and read boundary.
        results.append({
            "operation": "energy_phrase", "rate": rate, "channels": channels,
            "phrase_limit_seconds": 3, "read_chunks": expected[1],
            "output_bytes": len(expected[0]), "batch": 300,
            **measure_single(new, repeats, batch=300),
        })
    return results


def benchmark_speaker(repeats):
    results = []
    for seconds in (3, 15):
        for channels in (3, 6, 8):
            rate = 48000
            pcm = np.random.default_rng(932).integers(
                -24000, 24000, (rate * seconds, channels), dtype=np.int16,
            ).astype("<i2").tobytes()
            source = SimpleNamespace(SAMPLE_RATE=rate, SAMPLE_WIDTH=2, channels=channels)
            transcriber = AudioTranscriber(True, source, 3, 10, "Google")
            transcriber.audio_sources["last_sample"] = pcm

            def old():
                return AudioSegment(data=pcm, sample_width=2, frame_rate=rate,
                                    channels=channels).set_channels(1).raw_data

            def new():
                return transcriber.processSpeakerData().frame_data

            def numpy_mix():
                # Preserve every intermediate array('h') assignment, not just
                # the final sum. More channels can overflow and later recover.
                values = np.frombuffer(pcm, dtype="<i2").reshape(-1, channels).astype(np.int32)
                partials = np.cumsum(values // channels, axis=1, dtype=np.int64)
                if np.any(partials < -32768) or np.any(partials > 32767):
                    raise OverflowError("speaker downmix sample exceeds PCM16 range")
                return partials[:, -1].astype("<i2").tobytes()

            expected = old()
            assert new() == numpy_mix() == expected
            functions = {"old": old, "numpy": numpy_mix, "native": new}
            timings = {key: [] for key in functions}
            for iteration in range(repeats):
                order = tuple(functions) if iteration % 2 == 0 else tuple(reversed(functions))
                for name in order:
                    start = time.perf_counter_ns()
                    functions[name]()
                    timings[name].append((time.perf_counter_ns() - start) / 1_000_000)
            results.append({
                "operation": "speaker_downmix", "rate": rate, "seconds": seconds,
                "channels": channels, "input_bytes": len(pcm), "output_bytes": len(expected),
                "trials_ms": timings,
                **{key + "_median_ms": statistics.median(values) for key, values in timings.items()},
            })
    return results


def benchmark(repeats, suite="all"):
    native = get_native_audio()
    if native is None:
        raise RuntimeError("Install the release wheel from native/vrct-audio first")
    results = []
    if suite in ("all", "conversion"):
        results.extend(benchmark_conversion(native, repeats))
    if suite in ("all", "energy"):
        results.extend(benchmark_energy(native, repeats))
    if suite == "speaker":
        results.extend(benchmark_speaker(repeats))
    root = Path(__file__).resolve().parents[1]
    sources = ["native/vrct-audio/src/lib.rs", "native/vrct-audio/src/energy.rs",
               "native/vrct-audio/Cargo.lock", "tools/benchmark_audio_native.py",
               "src-python/models/transcription/google_speech.py",
               "src-python/models/transcription/native_audio.py",
               "src-python/models/transcription/audio_vad.py"]
    if suite == "speaker":
        sources.extend(["src-python/models/transcription/transcription_transcriber.py",
                        "src-python/models/transcription/native_audio.py"])
    binary = Path(import_module("vrct_audio.vrct_audio").__file__).resolve()
    return {
        "python": platform.python_version(), "platform": platform.platform(),
        "av": av.__version__, "numpy": np.__version__,
        "input": "synthetic PCM; no devices or network", "repeats": repeats,
        "scope": "Process-local conversion and synchronous energy detection/buffering. "
                 "Energy includes Python read/before_read/push and no-op energy callbacks. "
                 "Excludes device waiting, background thread scheduling, ASR and UI latency.",
        "source_sha256": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                          for name in sources},
        "native_binary": {
            "path": str(binary.relative_to(root)) if binary.is_relative_to(root) else str(binary),
            "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        },
        "comparison": "FLAC and energy are native-only measurements. Historical SpeechRecognition comparisons remain archived in docs/benchmarks; normalizer and speaker still compare current alternatives.",
        "pydub": {"version": version("pydub"), "audio_segment_sha256": hashlib.sha256(
            Path(import_module("pydub.audio_segment").__file__).read_bytes()).hexdigest()},
        "results": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=9)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--suite", choices=("all", "conversion", "energy", "speaker"), default="all")
    args = parser.parse_args()
    if args.repeats < 3:
        parser.error("--repeats must be at least 3")
    report = json.dumps(benchmark(args.repeats, args.suite), indent=2)
    print(report)
    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
