"""Exact tensor compatibility against the previous independent preprocessing."""

import cv2
import numpy as np
import pytest

from models.ocr.ocr_bubble_detector import BubbleDetector


def legacy_letterbox(frame, image_size):
    height, width = frame.shape[:2]
    scale = min(image_size / width, image_size / height)
    nw, nh = max(1, int(width * scale)), max(1, int(height * scale))
    resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((-(-nh // 32) * 32, -(-nw // 32) * 32, 3), 114, dtype=np.uint8)
    canvas[:nh, :nw] = resized
    return np.ascontiguousarray(canvas.transpose(2, 0, 1)[None], dtype=np.float32), scale


@pytest.mark.parametrize("shape", [(1, 1), (1, 37), (37, 1), (31, 53), (32, 32), (65, 47)])
@pytest.mark.parametrize("image_size", [32, 33, 1279, 1280])
def test_exact_tensor_padding_and_owned_output(shape, image_size):
    frame = np.random.default_rng(8).integers(0, 256, (*shape, 3), dtype=np.uint8)
    unchanged = frame.copy()
    detector = BubbleDetector(image_size=image_size)
    expected, expected_scale = legacy_letterbox(frame, image_size)
    actual, scale = detector._letterbox(frame)
    assert scale == expected_scale
    np.testing.assert_array_equal(actual, expected)
    assert actual.dtype == np.float32 and actual.flags.c_contiguous
    assert actual.flags.owndata and actual.flags.writeable
    actual.fill(42)
    np.testing.assert_array_equal(frame, unchanged)
    second, _ = detector._letterbox(frame)
    np.testing.assert_array_equal(second, expected)
    assert not np.shares_memory(actual, second)


def test_all_values_and_bgr_primary_colors_without_resize():
    frame = np.tile(np.arange(256, dtype=np.uint8), 3).reshape(16, 16, 3)
    frame[0, :3] = [[255, 0, 0], [0, 255, 0], [0, 0, 255]]
    np.testing.assert_array_equal(np.unique(frame), np.arange(256))
    actual, scale = BubbleDetector(image_size=16)._letterbox(frame)
    assert scale == 1
    np.testing.assert_array_equal(actual[0, :, :16, :16], frame.transpose(2, 0, 1))
    assert np.all(actual[0, :, 16:, :] == 114)
    assert np.all(actual[0, :, :16, 16:] == 114)


@pytest.mark.parametrize("view", ["negative", "columns", "transpose", "readonly"])
def test_strided_and_readonly_inputs(view):
    frame = np.random.default_rng(80).integers(0, 256, (17, 29, 3), dtype=np.uint8)
    if view == "negative":
        frame = frame[::-1, ::-1]
    elif view == "columns":
        frame = frame[:, ::2]
    elif view == "transpose":
        frame = frame.transpose(1, 0, 2)
    else:
        frame.flags.writeable = False
    expected, scale = legacy_letterbox(frame, 33)
    actual, actual_scale = BubbleDetector(image_size=33)._letterbox(frame)
    assert scale == actual_scale
    np.testing.assert_array_equal(actual, expected)


@pytest.mark.parametrize("dtype", [np.uint16, np.float32])
def test_other_dtypes_preserve_uint8_canvas_conversion(dtype):
    frame = np.random.default_rng(3).integers(0, 1200, (11, 19, 3)).astype(dtype)
    if dtype == np.float32:
        frame -= 300.25
    expected, scale = legacy_letterbox(frame, 33)
    actual, actual_scale = BubbleDetector(image_size=33)._letterbox(frame)
    assert scale == actual_scale
    np.testing.assert_array_equal(actual, expected)


@pytest.mark.parametrize("channels", [1, 2, 4, 5])
def test_other_channel_counts_preserve_legacy_outcome(channels):
    frame = np.zeros((7, 11, channels), dtype=np.uint8)
    try:
        expected, scale = legacy_letterbox(frame, 33)
    except (ValueError, cv2.error) as error:
        with pytest.raises(type(error)):
            BubbleDetector(image_size=33)._letterbox(frame)
    else:
        actual, actual_scale = BubbleDetector(image_size=33)._letterbox(frame)
        assert scale == actual_scale
        np.testing.assert_array_equal(actual, expected)
