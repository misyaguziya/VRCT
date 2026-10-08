"""Synthetic resize/letterbox benchmark; no model execution or screen capture."""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src-python"))
from models.ocr.ocr_bubble_detector import BubbleDetector, findModelPath  # noqa: E402


def legacy_letterbox(frame, image_size):
    height, width = frame.shape[:2]
    scale = min(image_size / width, image_size / height)
    nw, nh = max(1, int(width * scale)), max(1, int(height * scale))
    resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((-(-nh // 32) * 32, -(-nw // 32) * 32, 3), 114, dtype=np.uint8)
    canvas[:nh, :nw] = resized
    return np.ascontiguousarray(canvas.transpose(2, 0, 1)[None], dtype=np.float32), scale


def benchmark(repeats, image_size):
    detector = BubbleDetector(image_size=image_size)
    results = []
    for width, height in [(2575, 1455), (1920, 1080), (1000, 1400), (1024, 1024),
                          (2984, 3256), (17, 11), (1, 37), (37, 1)]:
        frame = np.random.default_rng(83).integers(0, 256, (height, width, 3), dtype=np.uint8)
        expected, scale = legacy_letterbox(frame, image_size)
        actual, actual_scale = detector._letterbox(frame)
        assert actual_scale == scale and np.array_equal(actual, expected)
        functions = {"old": lambda: legacy_letterbox(frame, image_size),
                     "direct": lambda: detector._letterbox(frame)}
        timings = {name: [] for name in functions}
        for function in functions.values():
            for _ in range(3):
                function()
        for iteration in range(repeats):
            order = tuple(functions) if iteration % 2 == 0 else tuple(reversed(functions))
            for name in order:
                start = time.perf_counter_ns()
                functions[name]()
                timings[name].append((time.perf_counter_ns() - start) / 1_000_000)
        nw, nh = max(1, int(width * scale)), max(1, int(height * scale))
        results.append({
            "input_shape": list(frame.shape), "input_dtype": str(frame.dtype),
            "tensor_shape": list(actual.shape), "tensor_dtype": str(actual.dtype),
            "scale": scale, "input_bytes": frame.nbytes, "resized_bytes": nh * nw * 3,
            "removed_canvas_bytes": actual.shape[2] * actual.shape[3] * 3,
            "output_bytes": actual.nbytes, "trials_ms": timings,
            **{name + "_median_ms": statistics.median(values) for name, values in timings.items()},
        })
    model = findModelPath()
    sources = [ROOT / "src-python/models/ocr/ocr_bubble_detector.py", Path(__file__).resolve()]
    return {
        "python": platform.python_version(), "platform": platform.platform(),
        "processor": platform.processor(), "opencv_version": cv2.__version__,
        "opencv_threads": cv2.getNumThreads(), "numpy_version": np.__version__,
        "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "model_sha256": hashlib.sha256(Path(model).read_bytes()).hexdigest() if model else None,
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
        "image_size": image_size, "seed": 83, "repeats": repeats,
        "scope": "Synthetic BGR resize and letterbox through contiguous float32 NCHW output. Excludes imports, model load/inference, capture and full app latency. Memory values are array byte sizes, not process peak memory.",
        "results": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=19)
    parser.add_argument("--image-size", type=int, default=1280)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repeats < 19 or args.image_size < 1:
        parser.error("at least 19 repeats and a positive image-size are required")
    report = json.dumps(benchmark(args.repeats, args.image_size), indent=2)
    print(report)
    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
