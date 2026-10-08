"""Synthetic mapped-pixel copies only: no screen capture, GPU calls or OCR models."""

import argparse
import ctypes as ct
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import statistics
import time

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
READER = ROOT / "src-python/models/ocr/ocr_capture_d3d11.py"
spec = importlib.util.spec_from_file_location("_benchmark_ocr_pixels", READER)
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


def benchmark(repeats):
    results = []
    for width, height, pitch in [(1920, 1080, 7680), (2575, 1455, 10496), (3840, 2160, 15360)]:
        for fmt in (28, 87):
            rows = np.random.default_rng(730).integers(0, 256, (height, pitch), dtype=np.uint8)
            backing = ct.create_string_buffer(rows.tobytes())
            address, size = ct.addressof(backing), height * pitch

            def old():
                raw = ct.string_at(address, size)
                rgba = np.frombuffer(raw, np.uint8).reshape(height, pitch)[:, :width * 4].reshape(height, width, 4)
                rgb = rgba[:, :, [2, 1, 0]] if fmt == 87 else rgba[:, :, :3]
                rgb = np.ascontiguousarray(rgb)
                return np.ascontiguousarray(rgb[:, :, ::-1])

            def new():
                return reader._pixels_from_bytes(ct.string_at(address, size), width, height, pitch, fmt, "BGR")

            def numpy_only():
                raw = ct.string_at(address, size)
                rgba = np.frombuffer(raw, np.uint8).reshape(height, pitch)[:, :width * 4].reshape(height, width, 4)
                bgr = rgba[:, :, :3] if fmt == 87 else rgba[:, :, 2::-1]
                return np.array(bgr, dtype=np.uint8, copy=True, order="C")

            expected = old()
            assert np.array_equal(new(), expected)
            assert np.array_equal(numpy_only(), expected)
            functions = {"old": old, "opencv": new, "numpy": numpy_only}
            timings = {name: [] for name in functions}
            for iteration in range(repeats):
                order = tuple(functions) if iteration % 2 == 0 else tuple(reversed(functions))
                for name in order:
                    started = time.perf_counter_ns()
                    functions[name]()
                    timings[name].append((time.perf_counter_ns() - started) / 1_000_000)
            results.append({
                "width": width, "height": height, "row_pitch": pitch, "dxgi_format": fmt,
                "input_bytes": size, "output_color": "BGR", "trials_ms": timings,
                **{name + "_median_ms": statistics.median(values) for name, values in timings.items()},
            })
    return {
        "python": platform.python_version(), "platform": platform.platform(),
        "opencv_version": cv2.__version__, "opencv_threads": cv2.getNumThreads(),
        "numpy_version": np.__version__, "seed": 730, "repeats": repeats,
        "scope": "ct.string_at owned copy and CPU pixel conversion through OCR BGR output; excludes GPU Map/Unmap, capture and inference",
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in (READER, ROOT / "src-python/models/ocr/ocr_capture_openvr.py", Path(__file__).resolve())},
        "results": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=9)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repeats < 3:
        parser.error("--repeats must be at least 3")
    report = json.dumps(benchmark(args.repeats), indent=2)
    print(report)
    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
