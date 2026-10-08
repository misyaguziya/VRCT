"""Compare two native audio binaries on identical synthetic immutable inputs.

Both binaries are loaded in one process under distinct package names. Timings
include the Python API and returned bytes, alternating order to limit drift.
No device, recognition model, or network is used.
"""

import argparse
import hashlib
from importlib.util import module_from_spec, spec_from_file_location
from io import BytesIO
import json
from pathlib import Path
import platform
import statistics
import sys
import time

import av
import numpy as np


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_native(path, label):
    # The final component must match the DLL's PyInit_vrct_audio symbol.
    spec = spec_from_file_location(f"{label}.vrct_audio", path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    assert Path(module.__file__).resolve() == path.resolve()
    return module


def cases():
    for frames, batch in ((1024, 1000), (48000 * 15, 1)):
        for channels in (1, 2, 6):
            yield "downmix_pcm16", (channels,), 2, channels, frames, batch
        for channels in (3, 6, 8):
            yield "speaker_downmix_pcm16", (channels,), 2, channels, frames, batch
        for width in (1, 2, 3, 4):
            for channels in (1, 2, 6):
                if (width, channels) != (2, 1):  # Existing identity path is unchanged.
                    yield "normalize_pcm16", (width, channels), width, channels, frames, batch
    for rate in (16000, 48000):
        for seconds in (3, 15):
            yield "encode_flac", (rate,), 2, 1, rate * seconds, 1


def compare(modules, case, repeats):
    name, args, width, channels, frames, batch = case
    rng = np.random.default_rng(9341)
    if name == "encode_flac":
        position = np.arange(frames) / args[0]
        pcm = (np.sin(2 * np.pi * 220 * position) * 8000 + rng.normal(0, 900, frames)).astype("<i2").tobytes()
    else:
        pcm = rng.bytes(frames * width * channels)
    functions = {label: getattr(module, name) for label, module in modules.items()}
    expected = functions["baseline"](pcm, *args)
    assert functions["candidate"](pcm, *args) == expected
    if name == "encode_flac":
        with av.open(BytesIO(expected)) as container:
            assert container.streams.audio[0].sample_rate == args[0]
            decoded = []
            for frame in container.decode(audio=0):
                assert frame.format.name == "s16" and len(frame.layout.channels) == 1
                decoded.append(frame.to_ndarray().astype("<i2").tobytes())
            assert b"".join(decoded) == pcm
    trials = {label: [] for label in functions}
    for iteration in range(repeats):
        order = ("baseline", "candidate") if iteration % 2 == 0 else ("candidate", "baseline")
        for label in order:
            function = functions[label]
            started = time.perf_counter_ns()
            for _ in range(batch):
                output = function(pcm, *args)
            trials[label].append((time.perf_counter_ns() - started) / batch / 1_000_000)
            assert output == expected
    return {
        "operation": name, "args": args, "width": width, "channels": channels,
        "frames": frames, "batch": batch, "input_bytes": len(pcm),
        "input_sha256": hashlib.sha256(pcm).hexdigest(),
        "output_sha256": hashlib.sha256(expected).hexdigest(),
        "identical_output": True,
        "trials_ms": trials,
        **{label + "_median_ms": statistics.median(values) for label, values in trials.items()},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-pyd", type=Path, required=True)
    parser.add_argument("--candidate-pyd", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=9)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    paths = {"baseline": args.baseline_pyd.resolve(), "candidate": args.candidate_pyd.resolve()}
    if paths["baseline"] == paths["candidate"]:
        parser.error("baseline and candidate must be distinct binaries")
    modules = {label: load_native(path, label) for label, path in paths.items()}
    report = {
        "python": sys.version, "platform": platform.platform(),
        "numpy": np.__version__, "av": av.__version__, "repeats": args.repeats,
        "benchmark_source_sha256": digest(Path(__file__)),
        "binaries": {label: {"path": str(path), "sha256": digest(path)} for label, path in paths.items()},
        "measurement": "Python API including returned bytes; alternating order; synthetic PCM; no ASR or I/O",
        "results": [compare(modules, case, args.repeats) for case in cases()],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    improved = sum(case["candidate_median_ms"] < case["baseline_median_ms"] for case in report["results"])
    print(f"PASS: {len(report['results'])} identical outputs; {improved} lower candidate medians; {args.output}")


if __name__ == "__main__":
    main()
