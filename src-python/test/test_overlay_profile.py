"""Stage-0 overlay profile (VRCT_OVERLAY_PROFILE) is inert by default and writes frame/window rows when set."""

import json
from unittest.mock import patch

import numpy as np

from models.overlay import overlay as overlay_module
from test_overlay_tooltip import overlay_fixture


def transfer_twice(overlay):
    width, height = overlay.window_size
    pixels = np.zeros((height, width, 4), dtype=np.uint8)
    capture = (b"frame", None, (0, 0, width, height))
    with patch.object(overlay, "prepareGl", return_value=overlay.gl["GL"]), \
         patch("models.overlay.overlay.window_capture.bgraFromCapture", return_value=pixels):
        overlay.transferCapture(capture, 1)
        overlay.transferCapture(capture, 2)  # same bytes: skipped as unchanged


def test_profile_is_off_by_default(tmp_path):
    overlay = overlay_fixture()
    with patch.object(overlay_module, "_PROFILE_PATH", None), \
         patch.object(overlay, "writeProfile") as write:
        transfer_twice(overlay)
        overlay.step_reported_at -= 60
        overlay.profile_window_at -= 60
        overlay.reportSlowSteps()
    write.assert_not_called()


def test_profile_writes_frame_and_window_rows(tmp_path):
    path = tmp_path / "overlay.jsonl"
    overlay = overlay_fixture()
    with patch.object(overlay_module, "_PROFILE_PATH", str(path)):
        transfer_twice(overlay)
        overlay.step_reported_at -= 60
        overlay.profile_window_at -= 60
        overlay.reportSlowSteps()
        overlay.profile_file.close()
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    frame, window = rows
    assert frame["kind"] == "frame" and frame["client"] == list(overlay.window_size)
    for key in ("convert_ms", "prepare_ms", "upload_ms", "finish_ms", "set_ms"):
        assert frame[key] >= 0
    assert frame["handles"] >= 1
    assert window["kind"] == "window" and window["backend"] == "gl"
    assert (window["frames_submitted"], window["frames_unchanged"]) == (1, 1)
    assert overlay.profile_submitted == overlay.profile_unchanged == 0
