"""Collector regressions. No SteamVR, windows, models, or external services."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
from PIL import Image
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import ocr_capture_source as sources  # noqa: E402
from tools import ocr_dataset_collector as collector  # noqa: E402


def frame(age=0):
    return sources.Frame(np.array([[[255, 0, 7], [0, 5, 255]]], dtype=np.uint8),
                         time.monotonic() - age,
                         {"captured_at": datetime.now(timezone.utc).isoformat(),
                          "backend": "fake", "eye": "left"})


def test_save_is_lossless_and_records_capture_metadata(tmp_path):
    store = collector.ImageStore(tmp_path, "test")
    sample = frame()
    png = store.save(sample, "unlabeled", 2)
    with Image.open(png) as image:
        np.testing.assert_array_equal(np.asarray(image), sample.rgb)
    record = json.loads(png.with_suffix(".json").read_text(encoding="utf-8"))
    assert record["captured_at"] == sample.metadata["captured_at"]
    assert record["width"] == 2 and record["height"] == 1
    assert record["label"] == "unlabeled" and record["run_id"] == store.run_id
    assert record["png_compress_level"] == 1 and store.count == 1


@pytest.mark.parametrize("failure", ["png", "json", "rename"])
def test_failed_save_leaves_no_pair_and_does_not_count(tmp_path, monkeypatch, failure):
    store = collector.ImageStore(tmp_path, "test")
    if failure == "png":
        monkeypatch.setattr(Image.Image, "save", Mock(side_effect=OSError("disk full")))
    elif failure == "json":
        monkeypatch.setattr(collector.json, "dump", Mock(side_effect=OSError("metadata write failed")))
    else:
        original = Path.rename

        def fail_png(path, target):
            if path.name.endswith(".png.part"):
                raise OSError("publish failed")
            return original(path, target)
        monkeypatch.setattr(Path, "rename", fail_png)
    with pytest.raises(OSError):
        store.save(frame(), "unlabeled", 2)
    assert store.count == 0
    assert not list(store.directory.rglob("*.*"))


def test_stale_frame_rejected_and_repeat_session_does_not_overwrite(tmp_path):
    first = collector.ImageStore(tmp_path, "test")
    with pytest.raises(sources.CaptureUnavailable):
        first.save(frame(age=10), "unlabeled", 2)
    assert first.count == 0
    a = first.save(frame(), "unlabeled", 2)
    second = collector.ImageStore(tmp_path, "test")
    b = second.save(frame(), "unlabeled", 2)
    assert a != b and a.exists() and b.exists()


def test_capture_failure_never_reuses_last_success(tmp_path):
    source = Mock()
    source.capture.side_effect = [frame()] + [sources.CaptureUnavailable("lost") for _ in range(30)]
    store = collector.ImageStore(tmp_path, "test")
    worker = collector.Collector(lambda: source, store, interval=0.02, duration=0.15, emit=Mock())
    worker.start()
    assert worker.done.wait(2)
    worker.stop()
    assert source.capture.call_count > 1
    assert store.count == 1 and worker.error is None
    source.close.assert_called_once()


def test_capture_and_close_share_owner_and_stop_waits_for_read(tmp_path):
    entered, finish_read = threading.Event(), threading.Event()
    calls = []

    class SlowSource:
        def __init__(self):
            calls.append(("init", threading.get_ident()))

        def capture(self):
            calls.append(("read", threading.get_ident()))
            entered.set()
            assert finish_read.wait(3)
            calls.append(("read_done", threading.get_ident()))
            return frame()

        def close(self):
            calls.append(("close", threading.get_ident()))

    store = collector.ImageStore(tmp_path, "test")
    worker = collector.Collector(SlowSource, store, emit=Mock())
    worker.start()
    assert entered.wait(2)
    stopper = threading.Thread(target=worker.stop)
    stopper.start()
    try:
        assert not worker.done.wait(0.1)
        assert stopper.is_alive() and all(name != "close" for name, _ in calls)
    finally:
        finish_read.set()
        stopper.join(3)
    assert worker.done.is_set() and not stopper.is_alive()
    assert [name for name, _ in calls] == ["init", "read", "read_done", "close"]
    assert len({owner for _, owner in calls}) == 1
    assert calls[0][1] != threading.get_ident() and store.count == 0


def test_pause_resume_and_frame_limit(tmp_path):
    paused = threading.Event()
    source = Mock()
    source.capture.side_effect = lambda: frame()
    store = collector.ImageStore(tmp_path, "test")
    worker = collector.Collector(lambda: source, store, interval=0.04, duration=2,
                                 max_frames=2,
                                 emit=lambda message: paused.set() if message.startswith("[paused]") else None)
    worker.command("pause")
    worker.start()
    try:
        assert paused.wait(1)
        assert not worker.done.wait(0.1)
        source.capture.assert_not_called()
        worker.command("pause")
        assert worker.done.wait(2)
    finally:
        worker.stop()
    assert store.count == 2 and source.capture.call_count == 2


def test_manual_ignores_unknown_command_and_takes_fresh_requests(tmp_path):
    source = Mock()
    source.capture.side_effect = lambda: frame()
    store = collector.ImageStore(tmp_path, "test")
    worker = collector.Collector(lambda: source, store, manual=True, duration=1,
                                 max_frames=2, emit=Mock())
    for name in ("typo", "positive", "negative"):
        worker.command(name)
    worker.start()
    assert worker.done.wait(2)
    worker.stop()
    assert source.capture.call_count == 2
    assert len(list(store.directory.glob("positive/*.png"))) == 1
    assert len(list(store.directory.glob("negative/*.png"))) == 1


def test_save_error_stops_worker_and_reports_failure(tmp_path):
    source = Mock()
    source.capture.side_effect = lambda: frame()
    store = collector.ImageStore(tmp_path, "test")
    store.save = Mock(side_effect=OSError("disk full"))
    messages = []
    worker = collector.Collector(lambda: source, store, emit=messages.append)
    worker.start()
    assert worker.done.wait(2)
    worker.stop()
    assert "disk full" in worker.error and store.count == 0
    assert not any(m.startswith("[saved") for m in messages)
    source.close.assert_called_once()


def test_duration_expires_even_when_paused_or_manual(tmp_path):
    source = Mock()
    worker = collector.Collector(lambda: source, collector.ImageStore(tmp_path, "test"),
                                 manual=True, duration=0.05, emit=Mock())
    worker.command("pause")
    worker.start()
    assert worker.done.wait(1)
    worker.stop()
    source.capture.assert_not_called()


def test_schedule_skips_missed_slots():
    assert collector.next_deadline(10, 10.6, 2) == 12
    assert collector.next_deadline(10, 15.7, 2) == 16


@pytest.mark.parametrize("args", [["../bad"], ["CON"], ["trailing."],
                                 ["--interval", "nan"], ["--duration", "inf"],
                                 ["--max-frames", "-1"], ["--max-age", "0"]])
def test_reject_bad_arguments(args):
    with pytest.raises(SystemExit):
        collector.parse_args(args)


def test_valid_unicode_session():
    assert collector.session_name("日本語のワールド") == "日本語のワールド"
    with pytest.raises(argparse.ArgumentTypeError):
        collector.session_name("a/b")


def test_frozen_output_is_beside_exe_and_can_be_overridden(tmp_path, monkeypatch):
    executable = tmp_path / "日本語 配布" / "Collector.exe"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))
    assert collector.parse_args([]).out == executable.parent / "dataset_collected"
    assert collector.parse_args(["--out", str(tmp_path)]).out == tmp_path
    monkeypatch.setattr(sys, "frozen", False)
    monkeypatch.chdir(tmp_path)
    assert collector.parse_args([]).out == tmp_path / "dataset_collected"


@pytest.mark.parametrize("arguments,interactive,should_wait", [([], True, True),
                         (["--manual"], True, False), ([], False, False)])
def test_exe_exit_wait_only_for_interactive_default_launch(monkeypatch, arguments, interactive, should_wait):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "argv", ["Collector.exe", *arguments])
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(isatty=lambda: interactive))
    monkeypatch.setattr(collector, "main", Mock(return_value=0))
    wait = Mock()
    monkeypatch.setattr("builtins.input", wait)
    assert collector.entrypoint() == 0
    assert wait.called == should_wait


def test_frozen_hwnd_loads_bundled_resource_without_source_tree(tmp_path, monkeypatch):
    bundle = tmp_path / "_MEI123"
    resource = bundle / "capture/ocr_capture_hwnd.py"
    resource.parent.mkdir(parents=True)
    resource.write_text("BUNDLED = True\n", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sources, "__file__", str(bundle / "ocr_capture_source.py"))
    monkeypatch.setattr(sources, "vrchat_windows", lambda: [])
    source = sources.CaptureSource("hwnd")
    with pytest.raises(sources.CaptureUnavailable, match="Expected one VRChat"):
        source.capture()
    assert source._hwnd_module.BUNDLED


def test_hwnd_validated_handle_and_rgb_conversion(monkeypatch):
    source = sources.CaptureSource("hwnd")
    window = {"pid": 12, "hwnd": 34, "visible": True, "minimized": False}
    bgr = np.array([[[1, 2, 255]]], dtype=np.uint8)
    native = SimpleNamespace(_window_rect=Mock(return_value=(0, 0, 1, 1)),
                             _print_window=Mock(return_value=bgr), isFrameBlank=Mock(return_value=False))
    source._hwnd_module = native
    monkeypatch.setattr(sources, "vrchat_windows", lambda: [window])
    result = source.capture()
    native._print_window.assert_called_once_with(34, 1, 1)
    assert result.rgb.tolist() == [[[255, 2, 1]]]
    assert result.metadata["backend"] == "hwnd"


def test_hwnd_refuses_minimized_and_changed_source(monkeypatch):
    source = sources.CaptureSource("hwnd")
    window = {"pid": 12, "hwnd": 34, "visible": True, "minimized": True}
    native = Mock()
    source._hwnd_module = native
    monkeypatch.setattr(sources, "vrchat_windows", lambda: [window])
    with pytest.raises(sources.CaptureUnavailable, match="minimized"):
        source.capture()
    native._print_window.assert_not_called()
    window["minimized"] = False
    native._window_rect.return_value = (0, 0, 2, 1)
    monkeypatch.setattr(sources, "vrchat_windows", Mock(side_effect=[[window], []]))
    with pytest.raises(sources.CaptureUnavailable, match="changed"):
        source.capture()


def test_vr_refuses_stale_or_changed_renderer_without_fallback():
    source = sources.CaptureSource("openvr")
    source._mirror = Mock()
    source._mirror.read.return_value = frame().rgb
    source._vr_state = Mock(side_effect=[(12, 100), (12, 101)])
    # Read before metadata collection; a changed renderer must be rejected.
    source._vr_state.side_effect = [(12, 100), (99, 101)]
    with pytest.raises(sources.CaptureUnavailable, match="changed"):
        source._capture_vr()
    source._last_frame = (12, 100)
    source._vr_state.side_effect = [(12, 100)]
    source._mirror.read.reset_mock()
    with pytest.raises(sources.CaptureUnavailable, match="new frame"):
        source._capture_vr()
    source._mirror.read.assert_not_called()
