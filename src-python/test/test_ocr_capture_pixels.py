import builtins
import ctypes as ct
import importlib.util
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from models.ocr import ocr_capture_d3d11 as pixels


@pytest.mark.parametrize("shape", [(1, 1), (1, 7), (7, 1), (3, 5)])
@pytest.mark.parametrize("fmt", [28, 29, 87, 91])
@pytest.mark.parametrize("order", ["RGB", "BGR"])
@pytest.mark.parametrize("fallback", [False, True])
def test_pixels_match_expected_and_own_writable_storage(shape, fmt, order, fallback):
    height, width = shape
    pitch = width * 4 + 7
    rgba = np.random.default_rng(38).integers(0, 256, (height, width, 4), dtype=np.uint8)
    rows = np.full((height, pitch), 255, dtype=np.uint8)
    rows[:, :width * 4] = rgba.reshape(height, width * 4)
    raw = rows.tobytes()
    expected = rgba[:, :, :3].copy()
    if (fmt in (87, 91)) != (order == "BGR"):
        expected = expected[:, :, ::-1]
    real_import = builtins.__import__

    def import_module(name, *args, **kwargs):
        if fallback and name == "cv2":
            raise ModuleNotFoundError("not installed", name="cv2")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=import_module):
        actual = pixels._pixels_from_bytes(raw, width, height, pitch, fmt, order)
    assert np.array_equal(actual, expected)
    assert actual.dtype == np.uint8 and actual.shape == (height, width, 3)
    assert actual.flags.c_contiguous and actual.flags.owndata and actual.flags.writeable
    actual[0, 0] = 0
    assert raw == rows.tobytes()


@pytest.mark.parametrize("args", [(0, 1, 4, 28, "RGB"), (1, -1, 4, 28, "RGB"),
    (2, 1, 4, 28, "RGB"), (1, 1, 4, 27, "RGB"), (1, 1, 4, 28, "XYZ")])
def test_invalid_layout(args):
    with pytest.raises(ValueError):
        pixels._pixels_from_bytes(b"\0" * 16, *args)


def test_short_raw_and_nonowned_input():
    with pytest.raises(ValueError, match="shorter"):
        pixels._pixels_from_bytes(b"\0" * 3, 1, 1, 4, 28)
    with pytest.raises(TypeError):
        pixels._pixels_from_bytes(bytearray(4), 1, 1, 4, 28)


def test_broken_opencv_import_and_conversion_are_not_hidden():
    real_import = builtins.__import__

    def broken(name, *args, **kwargs):
        if name == "cv2":
            raise ModuleNotFoundError("broken dependency", name="cv2_dependency")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=broken), pytest.raises(ModuleNotFoundError):
        pixels._pixels_from_bytes(bytes(4), 1, 1, 4, 28)
    with patch("cv2.cvtColor", side_effect=RuntimeError("conversion")), pytest.raises(RuntimeError):
        pixels._pixels_from_bytes(bytes(4), 1, 1, 4, 28)


@pytest.mark.parametrize("failure", [None, "map", "pointer", "pitch", "width", "height", "conversion"])
def test_map_cleanup_and_validation_before_pointer_copy(failure):
    mirror = pixels.D3D11Mirror.__new__(pixels.D3D11Mirror)
    mirror.context = mirror.staging = mirror.texture = ct.c_void_p(1)
    mirror.desc = pixels.TextureDesc()
    mirror.desc.Width = 0 if failure == "width" else 2
    mirror.desc.Height = 0 if failure == "height" else 1
    mirror.view_format = 87
    backing = ct.create_string_buffer(bytes([1, 2, 3, 4, 5, 6, 7, 8]))
    calls = []

    def com_call(obj, slot, result, types, *args):
        calls.append(slot)
        if slot == 14:
            mapped = ct.cast(args[-1], ct.POINTER(pixels.MappedResource)).contents
            mapped.pData = None if failure == "pointer" else ct.addressof(backing)
            mapped.RowPitch = 1 if failure == "pitch" else 8
            return -1 if failure == "map" else 0

    with patch.object(pixels, "com_call", side_effect=com_call), \
         patch.object(pixels.ct, "string_at", wraps=ct.string_at) as copy:
        if failure == "conversion":
            with patch.object(pixels, "_pixels_from_bytes", side_effect=RuntimeError("conversion")), pytest.raises(RuntimeError):
                mirror.read()
        elif failure is not None:
            with pytest.raises((ValueError, RuntimeError)):
                mirror.read()
            copy.assert_not_called()
        else:
            actual = mirror.read()
            assert actual.tolist() == [[[3, 2, 1], [7, 6, 5]]]
            copy.assert_called_once()
    assert calls.count(15) == (0 if failure == "map" else 1)


def test_bad_color_is_rejected_before_com_access():
    mirror = pixels.D3D11Mirror.__new__(pixels.D3D11Mirror)
    with patch.object(pixels, "com_call") as call, pytest.raises(ValueError):
        mirror.read(color_order="XYZ")
    call.assert_not_called()


def test_standalone_path_import_keeps_default_rgb():
    path = Path(__file__).resolve().parents[2] / "tools" / "openvr_d3d11.py"
    spec = importlib.util.spec_from_file_location("_pixel_test_standalone", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module._reader._pixels_from_bytes(bytes([1, 2, 3, 255]), 1, 1, 4, 28)
    assert result.tolist() == [[[1, 2, 3]]]
