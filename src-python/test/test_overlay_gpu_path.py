"""The VRCT_OVERLAY_GPU path of overlay.transferCapture with a fake CaptureSession (no GPU, no SteamVR)."""

import threading
from unittest.mock import patch

import numpy as np
import pytest

from models.overlay import overlay as overlay_module
from models.overlay.overlay import LAUNCHER, PANEL, atlasMaskArray, regionRect
from models.overlay.overlay_tooltip import marker_points, tooltip_mask
from test_overlay_tooltip import overlay_fixture, payload


class FakeGpu:
    def __init__(self, size=(2128, 1136), row=None):
        self.size, self.row, self.calls, self.closed = size, row, [], False
        self.texture_ptr = 1234

    def upload(self, raw, width, height, box):
        self.calls.append(("upload", len(raw), width, height, box))
        return box[2] - box[0], box[3] - box[1]

    def read_row(self, y):
        self.calls.append(("read_row", y))
        return self.row if self.row is not None else bytes(self.size[0] * 4)

    def set_mask(self, data, width, height):
        self.calls.append(("set_mask", width, height))
        self.mask = np.frombuffer(data, np.uint8).reshape(height, width)

    def render(self, intro=0, rect=(0, 0, 0, 0)):
        self.calls.append(("render", intro, rect))

    def close(self):
        self.closed = True


def gpu_overlay(**fake):
    overlay = overlay_fixture()
    overlay.gpu = FakeGpu(**fake)
    overlay.gpu_owner = threading.get_ident()
    overlay.gpu_vr_texture = object()
    overlay.layout_rendered = overlay.layout["regions"][PANEL][2:]
    return overlay


def capture(overlay, token=("gpu", 1)):
    width, height = overlay.window_size
    return token, (width + 2, height + 32), (1, 31, width + 1, height + 31)


def names(fake):
    return [call[0] for call in fake.calls]


@pytest.fixture(autouse=True)
def no_cpu_frame_copy():
    with patch("models.overlay.overlay.window_capture.bgraFromCapture", side_effect=AssertionError("CPU copy")):
        yield


def test_render_then_submit_dx_texture_to_every_region():
    overlay = gpu_overlay()
    overlay.transferCapture(capture(overlay), 1)
    assert names(overlay.gpu) == ["set_mask", "render"]
    submitted = [call.args for call in overlay.overlay.setOverlayTexture.call_args_list]
    assert submitted and all(texture is overlay.gpu_vr_texture for _, texture in submitted)
    assert {handle for handle, _ in submitted} == set(overlay.vrRegionHandles().values())
    np.testing.assert_array_equal(overlay.gpu.mask, atlasMaskArray(overlay.window_size, overlay.layout))


def test_same_frame_is_skipped_and_mask_is_sent_once():
    overlay = gpu_overlay()
    overlay.transferCapture(capture(overlay), 1)
    overlay.transferCapture(capture(overlay), 2)  # same token: nothing to do
    overlay.transferCapture(capture(overlay, ("gpu", 2)), 3)  # new frame, same mask
    assert names(overlay.gpu) == ["set_mask", "render", "render"]


def test_printwindow_bytes_are_uploaded():
    overlay = gpu_overlay()
    token, frame, box = capture(overlay)
    raw = bytes(frame[0] * frame[1] * 4)
    overlay.transferCapture((raw, frame, box), 1)
    assert overlay.gpu.calls[0] == ("upload", len(raw), *frame, box)


def test_tooltip_marker_row_decides_mask_and_ready():
    overlay = gpu_overlay()
    state = payload()
    overlay.tooltip_state = state
    width = overlay.window_size[0]
    py, columns = marker_points(width, overlay.layout)
    row = np.zeros((overlay.gpu.size[0], 4), np.uint8)
    bits = (state["epoch"] << 32) | state["revision"]
    for index, px in enumerate(columns):
        row[px, :3] = 255 if (bits >> (79 - index)) & 1 else 0
    overlay.gpu.row = row.tobytes()
    with patch.object(overlay, "safeUpdateTooltip"):
        overlay.transferCapture(capture(overlay), 1)
    assert ("read_row", py) in overlay.gpu.calls
    assert overlay.tooltip_ready is True
    expected = tooltip_mask(overlay.window_size, overlay.layout, state, atlasMaskArray(overlay.window_size, overlay.layout))
    np.testing.assert_array_equal(overlay.gpu.mask, expected)
    overlay.tooltip_state = dict(state, revision=state["revision"] + 1)  # the marker no longer matches
    overlay.panel_last_raw = None
    with patch.object(overlay, "hideTooltipOverlay") as hide, patch.object(overlay, "safeUpdateTooltip"):
        overlay.transferCapture(capture(overlay), 2)
    hide.assert_called()
    assert overlay.tooltip_ready is False


def test_no_marker_read_without_tooltip():
    overlay = gpu_overlay()
    overlay.transferCapture(capture(overlay), 1)
    assert "read_row" not in names(overlay.gpu)


@pytest.mark.parametrize("state,mode", [("pending", 1), ("playing", 2)])
def test_launcher_intro_is_rendered_on_gpu(state, mode):
    overlay = gpu_overlay()
    overlay.launcher_intro_state = state
    overlay.transferCapture(capture(overlay), 1)
    rect = regionRect(LAUNCHER, overlay.window_size, overlay.layout)
    assert ("render", mode, rect) in overlay.gpu.calls


def test_dx_bounds_are_not_flipped():
    overlay = gpu_overlay()
    overlay.panel_image_size = overlay.window_size
    overlay.applyLayout()
    bounds = {call.args[0]: call.args[1] for call in overlay.overlay.setOverlayTextureBounds.call_args_list}
    panel = bounds[overlay.handle[PANEL]]
    _, _, _, panel_h = overlay.layout["regions"][PANEL]
    assert panel.vMin == pytest.approx(0.0)
    assert panel.vMax == pytest.approx(panel_h / overlay.gpu.size[1])


@pytest.mark.parametrize("failure", ["too_small", "render_error"])
def test_falls_back_to_gl(failure):
    overlay = gpu_overlay(size=(10, 10)) if failure == "too_small" else gpu_overlay()
    fake = overlay.gpu
    if failure == "render_error":
        fake.render = lambda *a: (_ for _ in ()).throw(RuntimeError("device removed"))
    with patch.object(overlay_module, "errorLogging"):
        overlay.transferCapture(capture(overlay), 1)
    assert overlay.gpu is None and overlay.gpu_failed is True
    assert fake in overlay.gpu_retired and not fake.closed  # SteamVR may still read it: closed in teardown
    cleared = {call.args[0] for call in overlay.overlay.clearOverlayTexture.call_args_list}
    assert cleared == set(overlay.vrRegionHandles().values())
    assert overlay.panel_last_raw is None and overlay.layout_applied is None
    overlay.closeGpu()
    assert fake.closed and overlay.gpu_retired == []


def test_close_only_on_the_owner_thread():
    overlay = gpu_overlay()
    fake = overlay.gpu
    overlay.gpu_owner = threading.get_ident() + 1
    overlay.closeGpu()
    assert not fake.closed and overlay.gpu is None


def test_gpu_is_off_by_default():
    overlay = overlay_fixture()
    with patch.object(overlay_module, "_GPU_ENABLED", False), \
         patch.dict("sys.modules", {"vrct_graphics": None}):
        overlay.ensureGpu()
    assert overlay.gpu is None and overlay.gpu_failed is False


def test_creation_failure_keeps_gl():
    overlay = overlay_fixture()
    overlay.system = None  # getDXGIOutputInfo fails
    with patch.object(overlay_module, "_GPU_ENABLED", True), patch.object(overlay_module, "errorLogging"):
        overlay.ensureGpu()
    assert overlay.gpu is None and overlay.gpu_failed is True


class FakeCaptureSession:
    def __init__(self, polls):
        self.polls, self.closed, self.capturing, self.boxes = list(polls), False, False, []

    def start(self, hwnd):
        self.capturing = True

    def stop(self):
        self.capturing = False

    def poll(self, box):
        self.boxes.append(box)
        return self.polls.pop(0) if self.polls else None


def poll(frame_id, frame, copied=(1690, 880)):
    return {"frame_id": frame_id, "frame": frame, "copied": copied}


FRAME, BOX = (1692, 912), (1, 31, 1691, 911)


def gpu_stream(polls):
    from models.overlay import window_capture

    session = FakeCaptureSession(polls)
    return window_capture, session


def test_gpu_stream_returns_frame_tokens_and_keeps_stale_until_a_good_frame():
    window_capture, session = gpu_stream([poll(1, FRAME), None, poll(2, (800, 600)), None, poll(3, FRAME)])
    with patch.object(window_capture, "_frameClientBox", return_value=(FRAME, BOX)):
        stream = window_capture.GpuStream(session, 42)
        assert not stream.closed
        assert stream.take() == (("gpu", 1), FRAME, BOX)
        assert stream.take() == (("gpu", 1), FRAME, BOX)  # nothing new: same frame again
        assert stream.take() is None and stream.stale  # old-size frame: its copy is unusable
        assert stream.take() is None and stream.stale  # keep PrintWindow going, never reuse token 2
        assert stream.take() == (("gpu", 3), FRAME, BOX)
    assert session.boxes == [BOX] * 5
    stream.close()
    assert stream.closed


def test_gpu_stream_drops_frames_not_fully_copied_and_after_printwindow_upload():
    window_capture, session = gpu_stream([poll(1, FRAME, copied=(0, 0)), poll(2, FRAME), None])
    with patch.object(window_capture, "_frameClientBox", return_value=(FRAME, BOX)):
        stream = window_capture.GpuStream(session, 42)
        assert stream.take() is None and stream.stale
        assert stream.take() == (("gpu", 2), FRAME, BOX)
        stream.invalidate()  # PrintWindow overwrote the texture
        assert stream.take() is None and stream.stale


def test_gpu_stream_closes_without_first_frame_or_after_poll_error():
    window_capture, session = gpu_stream([])
    with patch.object(window_capture, "_frameClientBox", return_value=(FRAME, BOX)):
        stream = window_capture.GpuStream(session, 42)
        assert stream.take() is None and not stream.stale and not stream.closed
        stream.started -= window_capture._GPU_FIRST_FRAME_TIMEOUT_SEC + 1
        assert stream.closed  # WGC never delivered: let the overlay switch to PrintWindow
        failing = window_capture.GpuStream(FakeCaptureSession([]), 42)
        failing.session.poll = lambda box: (_ for _ in ()).throw(RuntimeError("device removed"))
        with pytest.raises(RuntimeError):
            failing.take()
        assert failing.closed and failing.take() is None


def test_set_texture_error_falls_back_and_drops_pending_job():
    import openvr

    overlay = gpu_overlay()
    overlay.capture_job = object()
    overlay.overlay.setOverlayTexture.side_effect = openvr.error_code.OpenVRError("InvalidTexture")
    with patch.object(overlay_module, "errorLogging"):
        overlay.transferCapture(capture(overlay), 1)
    assert overlay.gpu is None and overlay.gpu_failed and overlay.capture_job is None


def test_printwindow_size_race_skips_the_frame_only():
    overlay = gpu_overlay()
    fake = overlay.gpu
    fake.upload = lambda *a: (_ for _ in ()).throw(ValueError("client box is outside the frame"))
    token, frame, box = capture(overlay)
    with patch.object(overlay_module, "errorLogging"):
        overlay.transferCapture((bytes(frame[0] * frame[1] * 4), frame, box), 1)
    assert overlay.gpu is fake and not overlay.gpu_failed
    assert "render" not in names(fake)


def test_printwindow_upload_invalidates_the_gpu_stream():
    from models.overlay import window_capture

    overlay = gpu_overlay()
    stream = window_capture.GpuStream.__new__(window_capture.GpuStream)
    stream.latest = (("gpu", 1), (1, 1))
    overlay.panel_stream = stream
    token, frame, box = capture(overlay)
    overlay.transferCapture((bytes(frame[0] * frame[1] * 4), frame, box), 1)
    assert stream.latest is None


def test_ensure_gpu_creates_dx_texture_and_switches_the_stream():
    import types

    import openvr

    overlay = overlay_fixture()
    overlay.system = types.SimpleNamespace(getDXGIOutputInfo=lambda: 0)
    created = []
    fake_module = types.SimpleNamespace(CaptureSession=lambda adapter, w, h: created.append((adapter, w, h)) or FakeGpu((w, h)))
    with patch.object(overlay_module, "_GPU_ENABLED", True), patch.dict("sys.modules", {"vrct_graphics": fake_module}),          patch.object(overlay, "closePanelStream") as close_stream:
        overlay.ensureGpu()
    assert created and created[0][1] >= overlay.window_size[0]
    assert overlay.gpu_owner == threading.get_ident()
    assert overlay.gpu_vr_texture.handle == 1234
    assert overlay.gpu_vr_texture.eType == openvr.TextureType_DirectX
    assert overlay.gpu_vr_texture.eColorSpace == openvr.ColorSpace_Gamma
    close_stream.assert_called_once()


def test_ensure_gpu_drops_a_session_owned_by_another_thread():
    overlay = gpu_overlay()
    stale = overlay.gpu
    overlay.gpu_owner = threading.get_ident() + 1
    with patch.object(overlay_module, "_GPU_ENABLED", False):
        overlay.ensureGpu()
    assert overlay.gpu is None and not stale.closed


def test_teardown_leaves_no_reference_to_the_session(tmp_path):
    """A reference kept after closeGpu lets the unsendable session be collected on the next overlay thread."""
    import gc
    import weakref

    from models.overlay import window_capture

    overlay = gpu_overlay()
    session = FakeCaptureSession([poll(1, FRAME)])
    overlay.gpu = session
    alive = weakref.ref(session)
    with patch.object(window_capture, "_frameClientBox", return_value=(FRAME, BOX)):
        overlay.panel_stream = window_capture.GpuStream(session, 42)
        overlay.panel_stream.take()
    with patch.object(overlay_module, "_PROFILE_PATH", str(tmp_path / "p.jsonl")):
        overlay.writeProfileWindow(10.0)
        overlay.profile_file.close()
    overlay.closePanelStream()
    overlay.closeGpu()
    del session
    gc.collect()
    assert alive() is None
