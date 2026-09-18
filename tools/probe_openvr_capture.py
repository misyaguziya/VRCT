"""Standalone Windows/OpenVR D3D11 capture probe; does not import VRCT.

Run in a separate process, never in the VRCT backend (owns VR_Init/Shutdown).
Requires the existing openvr, numpy, Pillow and psutil packages. Saves local
diagnostics under ignored tmp/ by default; does not label or upload images.
"""

from __future__ import annotations

import argparse
import ctypes as ct
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import time


if __package__:
    from .openvr_d3d11 import D3D11Mirror, TextureDesc, vrchat_windows
else:
    from openvr_d3d11 import D3D11Mirror, TextureDesc, vrchat_windows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=int, default=5)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--eye", choices=["left", "right"], default="left")
    parser.add_argument("--out", type=Path, default=Path("tmp/openvr_probe"))
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("This probe requires Windows")
    if not 1 <= args.frames <= 120 or not 0.1 <= args.interval <= 10:
        parser.error("Use 1..120 frames and an interval of 0.1..10 seconds")
    import numpy as np
    import openvr
    from PIL import Image
    import psutil

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    output = args.out.resolve() / stamp
    output.mkdir(parents=True, exist_ok=False)
    report = {"utc_start": stamp, "eye": args.eye, "status": "ERROR",
              "packages": {p: importlib.metadata.version(p)
                           for p in ("openvr", "numpy", "Pillow", "psutil")},
              "frames": []}
    mirror, initialized = None, False
    try:
        system = openvr.init(openvr.VRApplication_Background)
        initialized = True
        compositor = openvr.VRCompositor()
        report["hmd"] = system.getStringTrackedDeviceProperty(
            0, openvr.Prop_ModelNumber_String)
        report["recommended_size"] = system.getRecommendedRenderTargetSize()
        mirror = D3D11Mirror(system, compositor,
                             openvr.Eye_Left if args.eye == "left" else openvr.Eye_Right)
        report["adapter_index"] = mirror.adapter_index
        report["view_format"] = mirror.view_format
        report["texture"] = {k: getattr(mirror.desc, k) for k, _ in TextureDesc._fields_}
        previous = None
        for index in range(args.frames):
            if index:
                time.sleep(args.interval)
            start = time.perf_counter()
            frame = mirror.read()
            capture_ms = (time.perf_counter() - start) * 1000
            focus_pid = compositor.getCurrentSceneFocusProcess()
            renderer_pid = compositor.getLastFrameRenderer()
            try:
                renderer_name = psutil.Process(renderer_pid).name() if renderer_pid else None
            except psutil.Error:
                renderer_name = None
            # The 1.26.701 wrapper also omits the required m_nSize field.
            timing = openvr.Compositor_FrameTiming()
            timing.m_nSize = ct.sizeof(timing)
            ok = compositor.function_table.getFrameTiming(ct.byref(timing), 0)
            record = {"index": index, "utc": datetime.now(timezone.utc).isoformat(),
                      "capture_ms": round(capture_ms, 3), "focus_pid": focus_pid,
                      "renderer_pid": renderer_pid, "renderer_name": renderer_name,
                      "compositor_frame_index": timing.m_nFrameIndex if ok else None,
                      "vrchat_windows": vrchat_windows(),
                      "sha256": hashlib.sha256(frame.tobytes()).hexdigest(),
                      "mean": float(frame.mean()), "std": float(frame.std()),
                      "changed_pixel_fraction": None if previous is None else
                      float(np.any(frame != previous, axis=2).mean()),
                      "file": f"{args.eye}_{index:03d}.png"}
            Image.fromarray(frame).save(output / record["file"], compress_level=1)
            report["frames"].append(record)
            previous = frame
            print(json.dumps(record, ensure_ascii=False), flush=True)
        report["row_pitch"] = mirror.row_pitch
        report["status"] = "CAPTURED"  # Never equates this with VRChat validation.
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        print(report["error"], file=sys.stderr, flush=True)
    finally:
        if mirror is not None:
            mirror.close()
        if initialized:
            openvr.shutdown()
        (output / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Report: {output / 'report.json'}", flush=True)
    return 0 if report["status"] == "CAPTURED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
