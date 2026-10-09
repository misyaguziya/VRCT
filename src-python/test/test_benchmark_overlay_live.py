"""tools/benchmark_overlay_live.py: windows inside a scenario, image-path CPU, and the stage-5 comparison."""

import importlib.util
import json
from pathlib import Path

_PATH = Path(__file__).resolve().parents[2] / "tools" / "benchmark_overlay_live.py"
_SPEC = importlib.util.spec_from_file_location("benchmark_overlay_live", _PATH)
bench = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(bench)


def samples(cpu_ms_per_s, seconds=30):
    return [{"t": 0.0, "cpu_s": 0.0, "rss": 1, "handles": 1, "threads": {1: 0.0}},
            {"t": seconds, "cpu_s": cpu_ms_per_s * seconds / 1000, "rss": 1, "handles": 1, "threads": {1: 0.0}}]


def window(backend, thread_cpu_s, copy_ms, frames=10):
    return {"kind": "window", "dur_s": 2.0, "backend": backend, "frames_submitted": frames, "frames_unchanged": 0,
            "wgc_arrivals": frames, "wgc_copy_ms": copy_ms, "overlay_thread_cpu_s": thread_cpu_s}


def test_only_windows_fully_inside_the_scenario_are_read(tmp_path):
    path = tmp_path / "p.jsonl"
    rows = [dict(window("gl", 1, 1), wall=101.0),  # started at 99: overlaps the switch
            dict(window("gl", 1, 1), wall=104.0), {"kind": "frame", "wall": 103.0, "src": "pw"}]
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    frames, windows = bench.read_profile(path, 100.0, 130.0)
    assert [w["wall"] for w in windows] == [104.0] and len(frames) == 1


def test_image_path_adds_the_capture_thread_copy_only_on_gl():
    gl = bench.summarize(samples(500), [], None, [], [window("gl", 0.1, 50.0)] * 5)
    gpu = bench.summarize(samples(500), [], None, [], [window("gpu", 0.1, 50.0)] * 5)
    assert gl["image_path_ms_per_s"] == 75.0  # (100 ms thread + 50 ms copy) / 2 s
    assert gpu["image_path_ms_per_s"] == 50.0  # the poll time is already in the overlay thread
    assert gl["overlay_windows"]["backends"] == ["gl"] and gpu["overlay_windows"]["backends"] == ["gpu"]


def report(tmp_path, name, image_path, frames, pw=0, dropped=0, backend=None):
    backend = backend or ("gl" if name.startswith("gl") else "gpu")
    scenario = {"cpu_ms_per_s": 900.0, "image_path_ms_per_s": image_path,
                "overlay_windows": {"frames_submitted": frames, "backends": [backend]},
                "overlay_frames": {"printwindow": pw}, "vrchat_cumulative_delta": {"dropped": dropped},
                "compositor": {"m_flTotalRenderGpuMs": {"p95": 20.0}}}
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps({"sets": [{"S0": scenario, "S1": scenario, "S2": scenario}] * 3}), encoding="utf-8")
    return path


def test_compare_adopts_only_with_large_reduction_same_work_and_no_printwindow(tmp_path):
    gl = report(tmp_path, "gl", 200.0, 300)
    assert bench.compare(gl, report(tmp_path, "gpu", 40.0, 310))["adopt"] is True
    assert bench.compare(gl, report(tmp_path, "gpu2", 80.0, 310))["adopt"] is False  # only 60% less
    assert bench.compare(gl, report(tmp_path, "gpu3", 40.0, 120))["adopt"] is False  # far less work
    assert bench.compare(gl, report(tmp_path, "gpu4", 40.0, 310, pw=5))["adopt"] is False
    assert bench.compare(gl, report(tmp_path, "gpu5", 40.0, 310, backend="gl"))["adopt"] is False  # GPU was not on


def test_compare_does_not_adopt_reports_without_the_image_path(tmp_path):
    old = report(tmp_path, "gpu-old", None, 310)  # taken before image_path_ms_per_s existed
    result = bench.compare(report(tmp_path, "gl", 200.0, 300), old)
    assert result["adopt"] is False and result["ratio_s2_image_path_gpu_over_gl"] is None
