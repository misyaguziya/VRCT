"""Synthetic changed intro frames only; excludes capture, GPU upload and VR I/O."""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
import time

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src-python"))
from models.overlay.overlay import (  # noqa: E402
    DEFAULT_LAYOUT, LAUNCHER, atlasMaskArray, introKeyAlpha, regionRect,
)
from models.overlay.window_capture import bgraFromCapture  # noqa: E402


def legacy_intro(pixels, rect):
    x0, y0, x1, y1 = rect
    region = pixels[y0:y1, x0:x1]
    key = region[0, 0, :3].astype(np.int32)
    diff = np.abs(region[..., :3].astype(np.int32) - key).max(axis=2)
    keyed = np.clip((diff - 4) * 255 // 16, 0, 255).astype(np.uint8)
    region[..., 3] = np.minimum(region[..., 3], keyed)
    region[region[..., 3] == 0, :3] = 0
    return tuple(int(v) for v in key), float(np.mean(region[..., 3] == 0))


def benchmark(repeats):
    results = []
    for scale in (1, 1.25, 1.5, 2):
        width, height = (round(value * scale) for value in DEFAULT_LAYOUT["atlas"])
        rect = regionRect(LAUNCHER, (width, height), DEFAULT_LAYOUT)
        x0, y0, x1, y1 = rect
        for mode in ("background", "random"):
            raw_pixels = np.random.default_rng(720).integers(0, 256, (height + 4, width + 6, 4), dtype=np.uint8)
            pixels = raw_pixels[2:height + 2, 3:width + 3]
            if mode == "background":
                pixels[y0:y1, x0:x1] = [50, 40, 30, 255]
                pixels[y0 + 10:y1 - 10, x0 + 30:x0 + 140, :3] = 255
            capture = (raw_pixels.tobytes(), (width + 6, height + 4), (3, 2, width + 3, height + 2))
            mask = atlasMaskArray((width, height), DEFAULT_LAYOUT)
            pixels = bgraFromCapture(capture)
            pixels[..., 3] = mask
            functions = {"old": legacy_intro, "opencv": introKeyAlpha}

            def full(function):
                result = bgraFromCapture(capture)
                result[..., 3] = atlasMaskArray((width, height), DEFAULT_LAYOUT)
                key_ratio = function(result, rect)
                return result, key_ratio

            expected, reference = full(legacy_intro)
            actual, response = full(introKeyAlpha)
            assert reference == response and np.array_equal(expected, actual)
            for scope in ("intro_only", "crop_mask_intro"):
                timings = {name: [] for name in functions}
                # Warm up caches and OpenCV before any recorded trial.
                for function in functions.values():
                    full(function)
                    function(pixels.copy(), rect)
                for iteration in range(repeats):
                    order = tuple(functions) if iteration % 2 == 0 else tuple(reversed(functions))
                    for name in order:
                        if scope == "intro_only":
                            work = pixels.copy()  # Copy outside the function-only timer.
                            started = time.perf_counter_ns()
                            functions[name](work, rect)
                        else:
                            started = time.perf_counter_ns()
                            full(functions[name])
                        timings[name].append((time.perf_counter_ns() - started) / 1_000_000)
                results.append({
                    "scope": scope, "dpi_scale": scale, "mode": mode,
                    "atlas_size": [width, height], "intro_rect": rect,
                    "trials_ms": timings,
                    **{name + "_median_ms": statistics.median(values) for name, values in timings.items()},
                })
    sources = [ROOT / "src-python/models/overlay/overlay.py",
               ROOT / "src-python/models/overlay/window_capture.py", Path(__file__).resolve()]
    return {
        "python": platform.python_version(), "platform": platform.platform(),
        "processor": platform.processor(), "opencv_version": cv2.__version__,
        "opencv_threads": cv2.getNumThreads(), "numpy_version": np.__version__,
        "seed": 720, "repeats": repeats,
        "scope": "Only changed frames during launcher intro. CPU keying or crop/mask/keying; excludes capture, GPU upload, model inference and app startup.",
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
        "results": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=9)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repeats < 9:
        parser.error("--repeats must be at least 9")
    report = json.dumps(benchmark(args.repeats), indent=2)
    print(report)
    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
