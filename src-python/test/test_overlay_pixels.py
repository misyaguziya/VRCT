"""Intro keying contracts on synthetic pixels only, without GL/VR devices."""

import builtins
from unittest.mock import patch

import numpy as np
import pytest

from models.overlay.overlay import (
    LAUNCHER, _INTRO_ALPHA_LUT, atlasMaskArray, introKeyAlpha, regionRect,
)


def legacy_intro(pixels, rect):
    x0, y0, x1, y1 = rect
    region = pixels[y0:y1, x0:x1]
    key = region[0, 0, :3].astype(np.int32)
    diff = np.abs(region[..., :3].astype(np.int32) - key).max(axis=2)
    keyed = np.clip((diff - 4) * 255 // 16, 0, 255).astype(np.uint8)
    region[..., 3] = np.minimum(region[..., 3], keyed)
    region[region[..., 3] == 0, :3] = 0
    return tuple(int(v) for v in key), float(np.mean(region[..., 3] == 0))


def assert_matches(pixels, rect):
    expected = pixels.copy()
    result = legacy_intro(expected, rect)
    assert introKeyAlpha(pixels, rect) == result
    np.testing.assert_array_equal(pixels, expected)


@pytest.mark.parametrize("channel", [0, 1, 2])
@pytest.mark.parametrize("alpha", [0, 1, 127, 255])
@pytest.mark.parametrize("white_key", [False, True])
def test_all_color_differences_and_alpha_values(channel, alpha, white_key):
    pixels = np.full((1, 256, 4), 255 if white_key else 0, dtype=np.uint8)
    pixels[..., 3] = alpha
    pixels[0, :, channel] = np.arange(255, -1, -1) if white_key else np.arange(256)
    assert_matches(pixels, (0, 0, 256, 1))


@pytest.mark.parametrize("view", ["plain", "negative", "columns", "transpose", "row", "column", "singleton"])
def test_views_and_roi_outside_unchanged(view):
    pixels = np.random.default_rng(73).integers(0, 256, (13, 17, 4), dtype=np.uint8)
    if view == "negative":
        pixels = pixels[::-1, ::-1]
    elif view == "columns":
        pixels = pixels[:, ::2]
    elif view == "transpose":
        pixels = pixels.transpose(1, 0, 2)
    elif view == "row":
        pixels = pixels[:1]
    elif view == "column":
        pixels = pixels[:, :1]
    elif view == "singleton":
        pixels = pixels[:1, :1]
    height, width = pixels.shape[:2]
    rect = (1, 2, width - 1, height - 2) if min(height, width) > 4 else (0, 0, width, height)
    assert_matches(pixels, rect)


@pytest.mark.parametrize("dtype,channels", [(np.uint16, 4), (np.float32, 4), (np.uint8, 5)])
def test_nonstandard_arrays_keep_legacy(dtype, channels):
    pixels = np.random.default_rng(42).integers(0, 256, (5, 7, channels)).astype(dtype)
    with patch("cv2.absdiff", side_effect=AssertionError("native must not run")):
        assert_matches(pixels, (1, 1, 6, 4))


def test_only_missing_cv2_falls_back():
    real_import = builtins.__import__

    def missing(name, *args, **kwargs):
        if name == "cv2":
            raise ModuleNotFoundError("missing", name="cv2")
        return real_import(name, *args, **kwargs)

    pixels = np.random.default_rng(43).integers(0, 256, (9, 11, 4), dtype=np.uint8)
    with patch("builtins.__import__", side_effect=missing):
        assert_matches(pixels, (1, 1, 10, 8))


@pytest.mark.parametrize("error", [ModuleNotFoundError("broken", name="cv2_internal"), ImportError("broken")])
def test_broken_import_propagates_without_mutation(error):
    real_import = builtins.__import__

    def broken(name, *args, **kwargs):
        if name == "cv2":
            raise error
        return real_import(name, *args, **kwargs)

    pixels = np.ones((3, 3, 4), dtype=np.uint8)
    expected = pixels.copy()
    with patch("builtins.__import__", side_effect=broken), pytest.raises(type(error)):
        introKeyAlpha(pixels, (0, 0, 3, 3))
    np.testing.assert_array_equal(pixels, expected)


@pytest.mark.parametrize("operation", ["absdiff", "split", "max", "LUT", "min", "copyTo", "countNonZero"])
def test_opencv_failure_does_not_partially_key_input(operation):
    pixels = np.random.default_rng(82).integers(0, 256, (5, 7, 4), dtype=np.uint8)
    expected = pixels.copy()
    with patch("cv2." + operation, side_effect=RuntimeError("failed")), pytest.raises(RuntimeError):
        introKeyAlpha(pixels, (1, 1, 6, 4))
    np.testing.assert_array_equal(pixels, expected)


def test_lut_is_readonly_and_uses_int32_threshold_arithmetic():
    assert not _INTRO_ALPHA_LUT.flags.writeable
    assert _INTRO_ALPHA_LUT.dtype == np.uint8
    np.testing.assert_array_equal(_INTRO_ALPHA_LUT, np.clip((np.arange(256, dtype=np.int32) - 4) * 255 // 16, 0, 255))


def test_mock_gl_receives_same_intro_pixels():
    from test_overlay_tooltip import overlay_fixture

    overlay = overlay_fixture()
    overlay.launcher_intro_state = "playing"
    width, height = overlay.window_size
    pixels = np.random.default_rng(9).integers(0, 256, (height, width, 4), dtype=np.uint8)
    expected = pixels.copy()
    expected[..., 3] = atlasMaskArray((width, height), overlay.layout)
    legacy_intro(expected, regionRect(LAUNCHER, (width, height), overlay.layout))
    gl = overlay.gl["GL"]
    capture = (b"synthetic frame", None, (0, 0, width, height))
    with patch.object(overlay, "prepareGl", return_value=gl), \
         patch("models.overlay.overlay.window_capture.bgraFromCapture", return_value=pixels):
        overlay.transferCapture(capture, 1)
    gl.glTexSubImage2D.assert_called_once()
    np.testing.assert_array_equal(gl.glTexSubImage2D.call_args.args[-1], expected)
