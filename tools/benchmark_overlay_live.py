"""Stage-0 baseline of the VR UI image path on real SteamVR (does not import VRCT).

Run in a separate process while VRCT runs with VRCT_OVERLAY_PROFILE=<jsonl>
(see models/overlay/overlay.py). Each set plays three timed scenarios that
are announced by voice (Windows SAPI) and beeps, so they can be followed
with the HMD on:

    S0  VR UI OFF (subtitles only), hands still
    S1  VR UI ON, log visible, not pointing at it
    S2  VR UI ON, laser on the log, keep scrolling

Per second it samples the VRCT backend process (CPU, threads, RSS, handles)
and the SteamVR compositor (per-frame timings, VRChat's cumulative dropped /
reprojected frames). The overlay profile JSONL adds per-frame convert / upload
/ finish / set_texture times. Nothing is captured from the screen.

    python tools/benchmark_overlay_live.py --profile-jsonl tmp/overlay_profile/vrct.jsonl
    python tools/benchmark_overlay_live.py --dry-run   # no SteamVR, short, for checking the tool
    python tools/benchmark_overlay_live.py --compare GL.json GPU.json   # stage 5: GL vs GPU

Other VRCT features (transcription, translation, OCR) may stay ON: their load
varies, so the comparison uses the CPU attributable to the VR UI image path
(overlay thread CPU, plus the windows-capture copy thread on OpenGL) rather
than whole-process CPU, which is still reported.

Decision rule fixed before measuring (2026-10-08, agreed with the user):
go to the GPU-direct Rust path when S2 adds >= 50 ms/s (5% of a core) of VRCT
CPU over S0, or worsens compositor p95 / dropped+reprojected frames beyond the
set-to-set spread; try Python copy reduction first when upload/finish/set
dominate the overlay time; otherwise stop.
"""

from __future__ import annotations

import argparse
import ctypes as ct
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = {
    "S0": "シナリオゼロ。VR UIをオフにして、手を止めてください。",
    "S1": "シナリオいち。VR UIをオンにして、ログを表示したまま、指さないでください。",
    "S2": "シナリオに。レーザーをログに当てたまま、スクロールし続けてください。",
}
TIMING_FIELDS = ("m_flTotalRenderGpuMs", "m_flCompositorRenderGpuMs", "m_flCompositorRenderCpuMs",
                 "m_flClientFrameIntervalMs")


def announce(text, beeps, enabled):
    print(text, flush=True)
    if not enabled:
        return
    import winsound
    for _ in range(beeps):
        winsound.Beep(880, 150)
        time.sleep(0.1)
    # Popen: speech must not delay the timed scenario.
    subprocess.Popen(["powershell", "-NoProfile", "-Command",
                      "Add-Type -AssemblyName System.Speech;"
                      "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;$s.Speak($env:VRCT_SAY)"],
                     env={**__import__("os").environ, "VRCT_SAY": text},
                     creationflags=subprocess.CREATE_NO_WINDOW)


def find_backend():
    """The VRCT Python backend: frozen sidecar or the dev venv's python running mainloop.py."""
    import psutil

    found = []
    for proc in psutil.process_iter(["name", "cmdline", "memory_info"]):
        cmd = " ".join(proc.info["cmdline"] or [])
        name = (proc.info["name"] or "").lower()
        if "mainloop.py" in cmd or (name.startswith("vrct-sidecar") and "python" not in name):
            found.append(proc)
    if not found:
        raise SystemExit("VRCT backend process not found; pass --pid")
    # The dev wrapper exe spawns python; the real backend is the larger one.
    return max(found, key=lambda p: p.info["memory_info"].rss).pid


class Compositor:
    def __init__(self):
        import openvr

        self.openvr = openvr
        system = openvr.init(openvr.VRApplication_Background)
        self.compositor = openvr.VRCompositor()
        self.hmd = system.getStringTrackedDeviceProperty(0, openvr.Prop_ModelNumber_String)
        self.last_frame = None
        self.buffer = (openvr.Compositor_FrameTiming * 128)()
        self.buffer[0].m_nSize = ct.sizeof(openvr.Compositor_FrameTiming)  # wrapper omits it

    def frames(self):
        count = self.compositor.function_table.getFrameTimings(ct.byref(self.buffer[0]), len(self.buffer))
        rows = []
        for timing in self.buffer[:count]:
            if self.last_frame is not None and timing.m_nFrameIndex <= self.last_frame:
                continue
            rows.append({f: round(getattr(timing, f), 3) for f in TIMING_FIELDS}
                        | {"dropped": timing.m_nNumDroppedFrames, "mispresented": timing.m_nNumMisPresented,
                           "reprojection": timing.m_nReprojectionFlags})
        if count:
            self.last_frame = max(t.m_nFrameIndex for t in self.buffer[:count])
        return rows

    def cumulative(self):
        stats = self.compositor.getCumulativeStats(ct.sizeof(self.openvr.Compositor_CumulativeStats))
        return {"pid": stats.m_nPid, "presents": stats.m_nNumFramePresents,
                "dropped": stats.m_nNumDroppedFrames, "reprojected": stats.m_nNumReprojectedFrames}

    def close(self):
        self.openvr.shutdown()


def sample(proc):
    times = proc.cpu_times()
    return {"t": time.monotonic(), "cpu_s": times.user + times.system, "rss": proc.memory_info().rss,
            "handles": proc.num_handles(),
            "threads": {t.id: t.user_time + t.system_time for t in proc.threads()}}


def read_profile(path, start_wall, end_wall):
    """Overlay profile rows (kind=frame / kind=window) whose wall time is in the window."""
    if path is None or not Path(path).exists():
        return [], []
    frames, windows = [], []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        wall = row.get("wall", 0)
        if row.get("kind") == "frame" and start_wall <= wall <= end_wall:
            frames.append(row)
        elif row.get("kind") == "window" and start_wall <= wall - row.get("dur_s", 0) and wall <= end_wall:
            windows.append(row)  # only windows fully inside the scenario
    return frames, windows


def pct(values, q):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    return round(values[min(len(values) - 1, int(q * len(values)))], 3)


def summarize(samples, frames_vr, cumulative, profile_frames, profile_windows):
    seconds = samples[-1]["t"] - samples[0]["t"]
    cpu_ms_per_s = (samples[-1]["cpu_s"] - samples[0]["cpu_s"]) * 1000 / seconds
    first, last = samples[0]["threads"], samples[-1]["threads"]
    busiest = sorted(((last[i] - first.get(i, 0)) * 1000 / seconds for i in last), reverse=True)[:3]
    out = {"seconds": round(seconds, 2), "cpu_ms_per_s": round(cpu_ms_per_s, 2),
           "busiest_threads_ms_per_s": [round(v, 2) for v in busiest],
           "rss_mb_max": round(max(s["rss"] for s in samples) / 2**20, 1),
           "handles_delta": samples[-1]["handles"] - samples[0]["handles"]}
    if frames_vr:
        out["compositor"] = {f: {"p50": pct([r[f] for r in frames_vr], 0.5),
                                 "p95": pct([r[f] for r in frames_vr], 0.95)} for f in TIMING_FIELDS}
        out["compositor"]["frames"] = len(frames_vr)
        out["compositor"]["reprojected_frames"] = sum(1 for r in frames_vr if r["reprojection"])
    if cumulative:
        a, b = cumulative
        out["vrchat_cumulative_delta"] = {k: b[k] - a[k] for k in ("presents", "dropped", "reprojected")}
        out["vrchat_cumulative_delta"]["same_app"] = a["pid"] == b["pid"]
    if profile_frames:
        out["overlay_frames"] = {"submitted": len(profile_frames)}
        for key in ("convert_ms", "upload_ms", "finish_ms", "set_ms", "arrive_to_submit_ms"):
            values = [f.get(key) for f in profile_frames]
            out["overlay_frames"][key] = {"p50": pct(values, 0.5), "p95": pct(values, 0.95),
                                          "ms_per_s": round(sum(v for v in values if v) / seconds, 2)}
        out["overlay_frames"]["printwindow"] = sum(1 for f in profile_frames if f.get("src") == "pw")
        out["overlay_frames"]["texture"] = profile_frames[-1].get("texture")
        out["overlay_frames"]["client"] = profile_frames[-1].get("client")
    if profile_windows:
        out["overlay_windows"] = {k: round(sum(w.get(k, 0) or 0 for w in profile_windows), 3)
                                  for k in ("frames_submitted", "frames_unchanged", "wgc_arrivals",
                                            "wgc_copy_ms", "overlay_thread_cpu_s", "dur_s")}
        out["overlay_windows"]["backends"] = sorted({w.get("backend", "gl") for w in profile_windows})
        covered = out["overlay_windows"]["dur_s"]
        # GL copies frames on the windows-capture thread (add it); GPU polls on the overlay thread (already in).
        separate_copy = sum(w.get("wgc_copy_ms", 0) for w in profile_windows if w.get("backend", "gl") == "gl")
        out["image_path_ms_per_s"] = round(
            (out["overlay_windows"]["overlay_thread_cpu_s"] * 1000 + separate_copy) / covered, 2) if covered else None
    return out


def decide(all_sets):
    """Apply the pre-agreed stage-0 rule to per-set summaries.

    A set whose S0 still submitted overlay frames was not switched off in time
    (VR UI still ON), so it is excluded instead of skewing min/spread.
    """
    excluded = [i for i, s in enumerate(all_sets) if s["S0"].get("overlay_frames", {}).get("submitted")]
    sets = [s for i, s in enumerate(all_sets) if i not in excluded]
    if not sets:
        return {"verdict": "INVALID_no_clean_S0", "excluded_sets": excluded}

    def values(name, getter):
        return [v for v in (getter(s[name]) for s in sets) if v is not None]

    def comp_p95(r):
        return r.get("compositor", {}).get("m_flCompositorRenderGpuMs", {}).get("p95")

    cpu_delta = [s["S2"]["cpu_ms_per_s"] - s["S0"]["cpu_ms_per_s"] for s in sets]
    image_path = [s["S2"].get("image_path_ms_per_s") for s in sets]
    s0_cpu = values("S0", lambda r: r["cpu_ms_per_s"])
    spread = (max(s0_cpu) - min(s0_cpu)) if len(s0_cpu) > 1 else 0.0
    p95_s0, p95_s2 = values("S0", comp_p95), values("S2", comp_p95)
    p95_spread = (max(p95_s0) - min(p95_s0)) if len(p95_s0) > 1 else 0.0
    compositor_worse = bool(p95_s0 and p95_s2 and min(p95_s2) - max(p95_s0) > p95_spread)
    cpu_go = min(cpu_delta) >= 50 and min(cpu_delta) > spread
    parts = {}
    for key in ("convert_ms", "upload_ms", "finish_ms", "set_ms"):
        parts[key] = statistics.mean(
            [s["S2"].get("overlay_frames", {}).get(key, {}).get("ms_per_s", 0) or 0 for s in sets])
    transfer = parts["upload_ms"] + parts["finish_ms"] + parts["set_ms"]
    verdict = ("A_gpu_direct" if cpu_go or compositor_worse
               else "B_python_copy_reduction" if transfer > parts["convert_ms"] and transfer >= 25
               else "C_stop")
    return {"verdict": verdict, "excluded_sets": excluded, "s2_minus_s0_cpu_ms_per_s": [round(v, 2) for v in cpu_delta],
            "s0_cpu_spread_ms_per_s": round(spread, 2), "compositor_gpu_p95_worse": compositor_worse,
            "s2_image_path_ms_per_s": image_path,
            "s2_overlay_ms_per_s_mean": {k: round(v, 2) for k, v in parts.items()}}


def compare(gl_path, gpu_path):
    """Stage-5 adoption check from two reports taken under the same conditions."""
    runs = {name: json.loads(Path(path).read_text(encoding="utf-8")) for name, path in (("gl", gl_path), ("gpu", gpu_path))}

    def values(name, scenario, getter):
        return [v for v in (getter(s[scenario]) for s in runs[name]["sets"] if scenario in s) if v is not None]

    def mean(vals):
        return round(statistics.mean(vals), 2) if vals else None

    def p95(r):
        return r.get("compositor", {}).get("m_flTotalRenderGpuMs", {}).get("p95")

    out = {"inputs": {"gl": str(gl_path), "gpu": str(gpu_path)}}
    for name in runs:
        out[name] = {
            "sets": len(runs[name]["sets"]),
            "s2_image_path_ms_per_s": values(name, "S2", lambda r: r.get("image_path_ms_per_s")),
            "s1_image_path_ms_per_s": values(name, "S1", lambda r: r.get("image_path_ms_per_s")),
            "s2_frames_submitted": values(name, "S2", lambda r: r.get("overlay_windows", {}).get("frames_submitted")),
            "backends": sorted({b for sc in ("S1", "S2") for bs in values(
                name, sc, lambda r: r.get("overlay_windows", {}).get("backends")) for b in bs}),
            "printwindow_frames": sum(sum(values(name, sc, lambda r: r.get("overlay_frames", {}).get("printwindow")))
                                      for sc in ("S1", "S2")),
            "process_cpu_ms_per_s": {sc: mean(values(name, sc, lambda r: r["cpu_ms_per_s"])) for sc in ("S0", "S1", "S2")},
            "total_render_gpu_p95_ms": {sc: mean(values(name, sc, p95)) for sc in ("S0", "S2")},
            "vrchat_dropped": sum(sum(values(name, sc, lambda r: r.get("vrchat_cumulative_delta", {}).get("dropped")))
                                  for sc in ("S0", "S1", "S2")),
        }
    gl, gpu = out["gl"], out["gpu"]
    gl_s2, gpu_s2 = mean(gl["s2_image_path_ms_per_s"]), mean(gpu["s2_image_path_ms_per_s"])
    work = mean(gpu["s2_frames_submitted"]) and mean(gl["s2_frames_submitted"]) and \
        mean(gpu["s2_frames_submitted"]) / mean(gl["s2_frames_submitted"])
    checks = {
        "gpu_image_path_le_25pct_of_gl": bool(gl_s2 and gpu_s2 is not None and gpu_s2 <= 0.25 * gl_s2),
        "no_printwindow_on_gpu": gpu["printwindow_frames"] == 0,
        "no_dropped_frames_added": gpu["vrchat_dropped"] <= gl["vrchat_dropped"],
        "reports_are_gl_then_gpu": gl["backends"] == ["gl"] and gpu["backends"] == ["gpu"],
        "workload_similar_frames_ratio": round(work, 2) if work else None,
    }
    out["ratio_s2_image_path_gpu_over_gl"] = round(gpu_s2 / gl_s2, 3) if gl_s2 and gpu_s2 is not None else None
    out["checks"] = checks
    out["adopt"] = all(v for k, v in checks.items() if k != "workload_similar_frames_ratio") and bool(
        work and 0.8 <= work <= 1.25)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--profile-jsonl", type=Path, default=ROOT / "tmp" / "overlay_profile" / "vrct.jsonl")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--sets", type=int, default=3)
    parser.add_argument("--prepare", type=float, default=10, help="seconds to switch scenario")
    parser.add_argument("--warmup", type=float, default=5)
    parser.add_argument("--duration", type=float, default=30)
    parser.add_argument("--compare", nargs=2, metavar=("GL_JSON", "GPU_JSON"), type=Path,
                        help="compare two finished reports (stage 5) instead of measuring")
    parser.add_argument("--dpi-note", default="", help="Windows display scale you are using, e.g. 150%%")
    parser.add_argument("--dry-run", action="store_true", help="no SteamVR/speech; 1 set of 3 s scenarios")
    args = parser.parse_args()
    if args.compare:
        result = compare(*args.compare)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.out:
            args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if result["adopt"] else 1
    import psutil

    if args.dry_run:
        args.sets, args.prepare, args.warmup, args.duration = 1, 0, 0, 3
    proc = psutil.Process(args.pid or (find_backend() if not args.dry_run else __import__("os").getpid()))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_dir = ROOT / "tmp" / "overlay_profile" / stamp
    raw_dir.mkdir(parents=True, exist_ok=True)
    out = args.out or (ROOT / "docs" / "benchmarks" / f"overlay_live_baseline_{stamp[:8]}.json"
                       if not args.dry_run else raw_dir / "summary.json")
    compositor = None if args.dry_run else Compositor()
    report = {"utc_start": stamp, "pid": proc.pid, "process": proc.name(), "dpi_note": args.dpi_note,
              "hmd": compositor.hmd if compositor else None, "settings": vars(args) | {
                  "profile_jsonl": str(args.profile_jsonl), "out": str(out), "pid": proc.pid},
              "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in (
                  "tools/benchmark_overlay_live.py", "src-python/models/overlay/overlay.py",
                  "src-python/models/overlay/window_capture.py")},
              "sets": [], "status": "INCOMPLETE"}
    raw = (raw_dir / "samples.jsonl").open("w", encoding="utf-8")
    try:
        announce("計測を始めます。", 1, not args.dry_run)
        for set_index in range(args.sets):
            results = {}
            for beeps, (name, text) in enumerate(SCENARIOS.items(), start=1):
                announce(f"セット{set_index + 1}。{text}", beeps, not args.dry_run)
                time.sleep(args.prepare + args.warmup)
                if compositor:
                    compositor.frames()  # drop frames from the switch
                    cumulative = [compositor.cumulative()]
                start_wall, samples, frames_vr = time.time(), [sample(proc)], []
                while samples[-1]["t"] - samples[0]["t"] < args.duration:
                    time.sleep(1)
                    samples.append(sample(proc))
                    if compositor:
                        frames_vr += compositor.frames()
                    raw.write(json.dumps({"set": set_index, "scenario": name} | {
                        k: v for k, v in samples[-1].items() if k != "threads"}) + "\n")
                if compositor:
                    cumulative.append(compositor.cumulative())
                pf, pw = read_profile(args.profile_jsonl, start_wall, time.time())
                results[name] = summarize(samples, frames_vr, cumulative if compositor else None, pf, pw)
                print(name, json.dumps(results[name], ensure_ascii=False), flush=True)
            report["sets"].append(results)
        report["decision"] = decide(report["sets"])
        report["status"] = "COMPLETE"
        announce("計測が終わりました。", 2, not args.dry_run)
    finally:
        raw.close()
        if compositor:
            compositor.close()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Report: {out}", flush=True)
    return 0 if report["status"] == "COMPLETE" else 1


if __name__ == "__main__":
    sys.exit(main())
