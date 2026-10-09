"""Stage-1 PoC probe for the VR UI image path: WGC -> Rust-owned D3D11 texture -> SteamVR.

Runs alone (not inside VRCT); needs the built vrct_graphics on PYTHONPATH.

    python tools/probe_overlay_d3d11.py headless           # no SteamVR: pixel check of the copy
    python tools/probe_overlay_d3d11.py vr --seconds 60    # SteamVR: shows overlays in front of the HMD

vr mode shows a Tk test window as `--handles` overlays (each a slice of one
texture, as VRCT does with its atlas) submitted as TextureType_DirectX /
ColorSpace_Gamma. Patterns: `flip` alternates black/white with a frame
counter every tick (tearing shows as mixed halves), `static` four colours.
`--recreate-at S` replaces the texture with a smaller one after S seconds
(checks whether SteamVR follows a new texture or keeps the first size).

Long runs: RSS / handles / threads are sampled every 10 s, and the run stops
with a `stop_reason` when SteamVR quits or is lost, or capture fails.
Writes a JSON report (timings of poll and setOverlayTexture per frame, errors).
"""

from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src-python"))
QUADRANTS = (("#ff0000", (0, 0, 255)), ("#00ff00", (0, 255, 0)), ("#0000ff", (255, 0, 0)), ("#ffffff", (255, 255, 255)))


def make_window(width, height):
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # per-monitor v2, physical px
    import tkinter

    root = tkinter.Tk()
    root.title("VRCT D3D11 overlay probe")
    root.geometry(f"{width}x{height}+40+40")
    root.resizable(False, False)
    canvas = tkinter.Canvas(root, width=width, height=height, highlightthickness=0, bg="black")
    canvas.pack()
    root.update()
    hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
    return root, canvas, hwnd


def draw(canvas, pattern, tick, width, height):
    canvas.delete("all")
    if pattern == "flip":
        color = "white" if tick % 2 else "black"
        canvas.create_rectangle(0, 0, width, height, fill=color, outline=color)
        canvas.create_text(width // 2, height // 2, text=str(tick), font=("Consolas", height // 4),
                           fill="black" if tick % 2 else "white")
        return
    for index, (name, _) in enumerate(QUADRANTS):
        x, y = (index % 2) * width // 2, (index // 2) * height // 2
        canvas.create_rectangle(x, y, x + width // 2, y + height // 2, fill=name, outline=name)


def client_box(hwnd):
    from models.overlay.window_capture import _frameClientBox

    found = _frameClientBox(hwnd)
    if found is None:
        raise SystemExit("could not read the window frame bounds")
    return found[1]


def pct(values, q):
    values = sorted(values)
    return round(values[min(len(values) - 1, int(q * len(values)))], 3) if values else None


def open_session(vrct_graphics, hwnd, adapter, texture, box):
    """Texture + WGC on the window, composed with an all-opaque mask of the client size."""
    session = vrct_graphics.CaptureSession(adapter, *texture)
    session.start(hwnd)
    width, height = min(box[2] - box[0], texture[0]), min(box[3] - box[1], texture[1])
    session.set_mask(bytes([255]) * (width * height), width, height)
    return session


def wait_frame(session, box, root, timeout=3.0):
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        root.update()
        polled = session.poll(box)
        if polled is not None:
            session.render()
            return polled
        time.sleep(0.01)
    return None


def headless(args):
    import vrct_graphics

    width, height = args.size
    root, canvas, hwnd = make_window(width, height)
    draw(canvas, "static", 0, width, height)
    root.update()
    box = client_box(hwnd)
    session = open_session(vrct_graphics, hwnd, args.adapter, args.texture, box)
    report = {"mode": "headless", "client_box": box, "texture": session.size, "status": "FAIL"}
    try:
        polled = wait_frame(session, box, root)
        report["polled"] = polled
        assert polled is not None, "no WGC frame arrived"
        pixels = session.read_back()
        tw = session.size[0]
        cw, ch = box[2] - box[0], box[3] - box[1]
        checks = {}
        for index, (name, bgr) in enumerate(QUADRANTS):
            x = (index % 2) * cw // 2 + cw // 4
            y = (index // 2) * ch // 2 + ch // 4
            offset = (y * tw + x) * 4
            checks[name] = {"at": [x, y], "bgra": list(pixels[offset:offset + 4]), "expected": [*bgr, 255]}
        if cw < tw and ch < session.size[1]:  # the texture area never copied into stays transparent
            outside = (min(cw + 4, tw - 1), min(ch + 4, session.size[1] - 1))
            offset = (outside[1] * tw + outside[0]) * 4
            checks["outside_copy"] = {"at": list(outside), "bgra": list(pixels[offset:offset + 4]),
                                      "expected": [0, 0, 0, 0]}
        report["checks"] = checks
        report["copied_matches_client"] = list(polled["copied"]) == [cw, ch]
        ok = report["copied_matches_client"] and all(c["bgra"] == c["expected"] for c in checks.values())
        report["status"] = "PASS" if ok else "FAIL"
    finally:
        session.close()
        root.destroy()
    return report


def vr(args):
    import openvr
    import vrct_graphics

    width, height = args.size
    root, canvas, hwnd = make_window(width, height)
    draw(canvas, args.pattern, 0, width, height)
    root.update()
    box = client_box(hwnd)
    system = openvr.init(openvr.VRApplication_Overlay)
    overlay = openvr.IVROverlay()
    adapter = system.getDXGIOutputInfo()
    report = {"mode": "vr", "pattern": args.pattern, "adapter_index": adapter, "client_box": box,
              "handles": args.handles, "hmd": system.getStringTrackedDeviceProperty(0, openvr.Prop_ModelNumber_String),
              "errors": [], "status": "FAIL"}
    handles, session = [], None

    def texture_for(session):
        texture = openvr.Texture_t()
        texture.handle = session.texture_ptr
        texture.eType = openvr.TextureType_DirectX
        texture.eColorSpace = openvr.ColorSpace_Gamma
        return texture

    def set_bounds(session):
        tw, th = session.size
        cw, ch = box[2] - box[0], box[3] - box[1]
        for index, handle in enumerate(handles):
            bounds = openvr.VRTextureBounds_t()
            bounds.uMin, bounds.uMax = cw * index / len(handles) / tw, cw * (index + 1) / len(handles) / tw
            bounds.vMin, bounds.vMax = 0.0, ch / th  # D3D: top-left origin, no GL flip
            overlay.setOverlayTextureBounds(handle, bounds)

    try:
        session = open_session(vrct_graphics, hwnd, adapter, args.texture, box)
        span = 1.2
        for index in range(args.handles):
            handle = overlay.createOverlay(f"vrct.d3d11.poc.{index}", f"VRCT D3D11 PoC {index}")
            overlay.setOverlayWidthInMeters(handle, span / args.handles)
            matrix = openvr.HmdMatrix34_t()
            x = -span / 2 + span * (index + 0.5) / args.handles
            for r, row in enumerate(((1, 0, 0, x), (0, 1, 0, 0.0), (0, 0, 1, -1.2))):
                for c, value in enumerate(row):
                    matrix.m[r][c] = value
            overlay.setOverlayTransformTrackedDeviceRelative(handle, openvr.k_unTrackedDeviceIndex_Hmd, matrix)
            overlay.showOverlay(handle)
            handles.append(handle)
        set_bounds(session)
        texture = texture_for(session)
        poll_ms, set_ms, cpu_ms, frames = [], [], [], 0
        import psutil

        me, resources, last_sample, failing = psutil.Process(), [], 0.0, 0
        event = openvr.VREvent_t()
        started = time.perf_counter()
        recreated = False
        tick = 0
        report["stop_reason"] = "duration"
        while time.perf_counter() - started < args.seconds:
            tick_start = time.perf_counter()
            tick += 1
            if tick_start - last_sample >= 10:  # resource leaks show up over a long run
                resources.append({"t_s": round(tick_start - started, 1), "rss_mb": round(me.memory_info().rss / 2**20, 1),
                                  "handles": me.num_handles(), "threads": me.num_threads(), "frames": frames})
                last_sample = tick_start
            quit_requested = False
            while system.pollNextEvent(event):
                quit_requested |= event.eventType == openvr.VREvent_Quit
            if quit_requested:
                system.acknowledgeQuit_Exiting()
                report["stop_reason"] = "steamvr_quit"
                break
            if args.pattern == "flip":
                draw(canvas, "flip", tick, width, height)
            root.update()
            if args.recreate_at and not recreated and tick_start - started >= args.recreate_at:
                # A new, smaller texture: does SteamVR follow it or keep the first size?
                for handle in handles:
                    overlay.clearOverlayTexture(handle)
                session.close()
                session = open_session(vrct_graphics, hwnd, adapter, (args.texture[0] * 3 // 4, args.texture[1] * 3 // 4), box)
                set_bounds(session)
                texture = texture_for(session)
                recreated = True
                report["recreated_at_frame"] = frames
            cpu0, t0 = time.thread_time(), time.perf_counter()
            try:
                polled = session.poll(box)
            except RuntimeError as error:  # e.g. device removed or the window closed
                report["errors"].append(f"poll: {error}")
                report["stop_reason"] = "capture_failed"
                break
            if polled is not None:
                session.render()
            t1 = time.perf_counter()
            if polled is not None:
                failed = False
                for handle in handles:
                    try:
                        overlay.setOverlayTexture(handle, texture)
                    except openvr.OpenVRError as error:
                        failed = True
                        if len(report["errors"]) < 20:
                            report["errors"].append(f"frame {frames}: {error}")
                failing = failing + 1 if failed else 0
                if failing >= 20:  # SteamVR went away without a quit event
                    report["stop_reason"] = "steamvr_lost"
                    break
                t2 = time.perf_counter()
                frames += 1
                poll_ms.append((t1 - t0) * 1000)
                set_ms.append((t2 - t1) * 1000)
                cpu_ms.append((time.thread_time() - cpu0) * 1000)
            time.sleep(max(0.0, 1 / args.hz - (time.perf_counter() - tick_start)))
        elapsed = time.perf_counter() - started
        report.update(frames=frames, ticks=tick, seconds=round(elapsed, 2),
                      poll_ms={"p50": pct(poll_ms, 0.5), "p95": pct(poll_ms, 0.95), "max": pct(poll_ms, 1.0)},
                      set_ms={"p50": pct(set_ms, 0.5), "p95": pct(set_ms, 0.95), "max": pct(set_ms, 1.0)},
                      thread_cpu_ms_per_frame={"p50": pct(cpu_ms, 0.5), "p95": pct(cpu_ms, 0.95),
                                               "mean": round(statistics.mean(cpu_ms), 3) if cpu_ms else None},
                      thread_cpu_ms_per_s=round(sum(cpu_ms) / elapsed, 2), resources=resources)
        report["status"] = "RAN" if frames and not report["errors"] else "FAIL"  # visual checks are the user's
    finally:
        for handle in handles:
            try:
                overlay.clearOverlayTexture(handle)
            except Exception as error:  # keep tearing down
                report["errors"].append(f"clear: {error}")
        if session is not None:
            session.close()
        for handle in handles:
            try:
                overlay.destroyOverlay(handle)
            except Exception as error:
                report["errors"].append(f"destroy: {error}")
        openvr.shutdown()
        root.destroy()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=("headless", "vr"))
    parser.add_argument("--size", type=int, nargs=2, default=(1690, 880), help="client size of the test window")
    parser.add_argument("--texture", type=int, nargs=2, default=(2128, 1136))
    parser.add_argument("--adapter", type=int, default=0, help="headless only; vr uses SteamVR's adapter")
    parser.add_argument("--handles", type=int, default=5)
    parser.add_argument("--pattern", choices=("flip", "static"), default="flip")
    parser.add_argument("--seconds", type=float, default=60)
    parser.add_argument("--hz", type=float, default=20)
    parser.add_argument("--recreate-at", type=float, default=0)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = (headless if args.mode == "headless" else vr)(args)
    report["utc"] = datetime.now(timezone.utc).isoformat()
    out = args.out or ROOT / "tmp" / "overlay_poc" / f"{args.mode}-{datetime.now():%Y%m%d-%H%M%S}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "checks"}, ensure_ascii=False))
    print(f"Report: {out}")
    return 0 if report["status"] in ("PASS", "RAN") else 1


if __name__ == "__main__":
    sys.exit(main())
