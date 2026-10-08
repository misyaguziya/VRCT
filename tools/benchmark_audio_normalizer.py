"""Compare the pre-fusion normalizer to the current dispatch on synthetic PCM.

The baseline below preserves cycle 6's audioop/NumPy/native-downmix pipeline.
It uses the same unchanged downmix API, so no old package is required.
"""

import argparse
import audioop
import hashlib
import inspect
import json
from pathlib import Path
import platform
import statistics
import sys
import time

import numpy as np
import vrct_audio

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src-python"))
from models.transcription.audio_vad import Pcm16MonoNormalizer  # noqa: E402


BASELINE_SOURCE_SHA256 = "3dcea90f2ad92a490cb2784a89ac5a36749c1e57df1f1d445cc9a42aecbc5892"


class PreviousNormalizer(Pcm16MonoNormalizer):
    """Cycle 6 process(), including native downmix and ratecv state."""

    def process(self, data):
        if not data:
            return b""
        if self.sample_width != 2:
            data = audioop.lin2lin(data, self.sample_width, 2)
        samples = np.frombuffer(data, dtype=np.int16)
        complete_samples = samples.size - samples.size % self.channels
        samples = samples[:complete_samples]
        if self.channels > 1 and samples.size:
            if self._native_audio is not None and self.channels <= 256:
                data = self._native_audio.downmix_pcm16(samples.tobytes(), self.channels)
                samples = np.frombuffer(data, dtype=np.int16)
            else:
                frames = samples.reshape(-1, self.channels).astype(np.int32)
                samples = np.rint(frames.mean(axis=1)).clip(-32768, 32767).astype(np.int16)
        data = samples.astype("<i2", copy=False).tobytes()
        if self.sample_rate != 16000:
            data, self._rate_state = audioop.ratecv(data, 2, 1, self.sample_rate, 16000, self._rate_state)
        return data


def compare(rate, width, channels, frames, repeats, batch):
    rng = np.random.default_rng(794)
    old = PreviousNormalizer(rate, width, channels)
    new = Pcm16MonoNormalizer(rate, width, channels)
    # Include non-frame-aligned chunk boundaries and reset semantics before timing.
    for count in (1, 1024, 3, 17, 512):
        pcm = rng.bytes((count * channels + channels - 1) * width)
        assert old.process(pcm) == new.process(pcm)
        assert old._rate_state == new._rate_state
    old.reset()
    new.reset()
    pcm = rng.bytes(frames * channels * width)
    assert old.process(pcm) == new.process(pcm)
    trials = {"previous": [], "fused": []}
    methods = {"previous": old.process, "fused": new.process}
    for iteration in range(repeats):
        order = ("previous", "fused") if iteration % 2 == 0 else ("fused", "previous")
        outputs = {}
        for name in order:
            started = time.perf_counter_ns()
            for _ in range(batch):
                output = methods[name](pcm)
            trials[name].append((time.perf_counter_ns() - started) / batch / 1_000_000)
            outputs[name] = output
        assert outputs["previous"] == outputs["fused"]
        assert old._rate_state == new._rate_state
    return {
        "rate": rate, "width": width, "channels": channels, "frames": frames,
        "batch": batch, "pcm_and_state_equal": True,
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
    native_path = Path(vrct_audio.vrct_audio.__file__)
    current_source = Path(inspect.getsourcefile(Pcm16MonoNormalizer))
    cases = [(rate, 2, channels, 1024, 1000) for rate in (16000, 44100, 48000) for channels in (1, 2, 6)]
    cases += [(48000, width, channels, 1024, 1000) for width in (1, 3, 4) for channels in (1, 2, 6)]
    cases += [(48000, 2, 6, 48000 * 15, 1), (48000, 3, 6, 48000 * 15, 1)]
    report = {
        "python": sys.version, "platform": platform.platform(), "numpy": np.__version__,
        "repeats": args.repeats,
        "baseline_source_sha256": BASELINE_SOURCE_SHA256,
        "baseline": "cycle 6 process() with unchanged native downmix; no external package",
        "native_sha256": hashlib.sha256(native_path.read_bytes()).hexdigest(),
        "normalizer_source_sha256": hashlib.sha256(current_source.read_bytes()).hexdigest(),
        "benchmark_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "results": [compare(rate, width, channels, frames, args.repeats, batch)
                    for rate, width, channels, frames, batch in cases],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {len(cases)} cases, PCM and resampler state equal; report: {args.output}")


if __name__ == "__main__":
    main()
