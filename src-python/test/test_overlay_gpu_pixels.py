"""The GPU compose pass (native/vrct-graphics) equals the CPU path bit for bit.

Uses the real extension and a D3D11 device; skipped where either is missing.
CPU reference = overlay.transferCapture: pixels[..., 3] = mask, then the launcher
intro (pending: launcher cleared; playing: introKeyAlpha).
"""

import numpy as np
import pytest

from models.overlay.overlay import (
    DEFAULT_LAYOUT, LAUNCHER, MAX_LAYOUT, atlasMaskArray, computeVrLayout, introKeyAlpha, regionRect,
)
from models.overlay.overlay_tooltip import marker_matches, marker_points, marker_row_matches, tooltip_mask

vrct_graphics = pytest.importorskip("vrct_graphics")

LAYOUTS = {"min": computeVrLayout(600, 400), "default": DEFAULT_LAYOUT, "max": MAX_LAYOUT}
SCALES = (1.0, 1.25, 1.5, 2.0)
TEXTURE = (MAX_LAYOUT["atlas"][0] * 2, MAX_LAYOUT["atlas"][1] * 2)  # the largest image at DPI 2
STATE = {"epoch": 0x123456789A, "revision": 0x0BADF00D, "visible": True, "region": "launcher", "mode": "hover",
         "button": [10, 10, 40, 40], "size": [360, 60], "arrow_x": 100}


@pytest.fixture(scope="module")
def session():
    try:
        gpu = vrct_graphics.CaptureSession(0, *TEXTURE)
    except RuntimeError as error:
        pytest.skip(f"no D3D11 device: {error}")
    yield gpu
    gpu.close()


def frame(size, launcher, seed):
    """Random BGRA (alpha too: WGC/PrintWindow alpha is undefined) with a keyed launcher."""
    width, height = size
    pixels = np.random.default_rng(seed).integers(0, 256, (height, width, 4), dtype=np.uint8)
    x0, y0, x1, y1 = launcher
    key = np.array([40, 30, 20], dtype=np.uint8)
    region = pixels[y0:y1, x0:x1]
    region[..., :3] = key
    # Colour distances 0..40 around the LUT edges (4 and 20), mixed per channel.
    ramp = np.arange(region.shape[1]) % 41
    region[: region.shape[0] // 2, :, 0] = (key[0] + ramp).astype(np.uint8)
    region[region.shape[0] // 2 :, :, 2] = np.clip(key[2] - ramp, 0, 255).astype(np.uint8)
    region[::7, ::5, :3] = 255
    return pixels


def gpu_compose(session, pixels, mask, intro=0, launcher=(0, 0, 0, 0)):
    height, width = mask.shape
    assert session.upload(pixels.tobytes(), width, height, (0, 0, width, height)) == (width, height)
    session.set_mask(np.ascontiguousarray(mask).tobytes(), width, height)
    session.render(intro, launcher)
    tw, th = session.size
    return np.frombuffer(session.read_back(), np.uint8).reshape(th, tw, 4)[:height, :width]


def cpu_compose(pixels, mask, intro=0, launcher=(0, 0, 0, 0)):
    expected = pixels.copy()
    expected[..., 3] = mask
    x0, y0, x1, y1 = launcher
    if intro == 1:
        expected[y0:y1, x0:x1] = 0
    elif intro == 2:
        introKeyAlpha(expected, launcher)
    return expected


@pytest.mark.parametrize("scale", SCALES)
@pytest.mark.parametrize("name", LAYOUTS)
def test_mask_and_intro_match_cpu(session, name, scale):
    layout = LAYOUTS[name]
    size = (round(layout["atlas"][0] * scale), round(layout["atlas"][1] * scale))
    launcher = regionRect(LAUNCHER, size, layout)
    pixels = frame(size, launcher, seed=int(scale * 100) + len(name))
    mask = atlasMaskArray(size, layout)
    for intro in (0, 1, 2):
        np.testing.assert_array_equal(gpu_compose(session, pixels, mask, intro, launcher),
                                      cpu_compose(pixels, mask, intro, launcher), err_msg=f"intro={intro}")


def test_tooltip_mask_and_marker_row_match_cpu(session):
    layout = DEFAULT_LAYOUT
    size = (round(layout["atlas"][0] * 1.5), round(layout["atlas"][1] * 1.5))
    pixels = frame(size, regionRect(LAUNCHER, size, layout), seed=7)
    py, columns = marker_points(size[0], layout)
    bits = (STATE["epoch"] << 32) | STATE["revision"]
    for index, px in enumerate(columns):
        pixels[py, px, :3] = 255 if (bits >> (79 - index)) & 1 else 0
    mask = tooltip_mask(size, layout, STATE, atlasMaskArray(size, layout))
    np.testing.assert_array_equal(gpu_compose(session, pixels, mask), cpu_compose(pixels, mask))
    row = np.frombuffer(session.read_row(py), np.uint8).reshape(-1, 4)
    assert marker_row_matches(row, columns, STATE) is marker_matches(pixels, layout, STATE) is True
    other = dict(STATE, revision=STATE["revision"] + 1)
    assert marker_row_matches(row, columns, other) is marker_matches(pixels, layout, other) is False


def test_upload_copies_only_the_client_box(session):
    frame_size, box = (40, 30), (3, 5, 23, 25)
    raw = np.random.default_rng(3).integers(0, 256, (frame_size[1], frame_size[0], 4), dtype=np.uint8)
    assert session.upload(raw.tobytes(), *frame_size, box) == (20, 20)
    mask = np.full((20, 20), 255, np.uint8)
    session.set_mask(mask.tobytes(), 20, 20)
    session.render()
    tw, th = session.size
    out = np.frombuffer(session.read_back(), np.uint8).reshape(th, tw, 4)
    np.testing.assert_array_equal(out[:20, :20, :3], raw[5:25, 3:23, :3])


def test_invalid_inputs_raise(session):
    with pytest.raises(ValueError):
        session.upload(b"\0" * 10, 4, 4, (0, 0, 4, 4))
    with pytest.raises(ValueError):
        session.upload(b"\0" * 64, 4, 4, (8, 8, 9, 9))
    with pytest.raises(ValueError):
        session.set_mask(b"\0" * 3, 2, 2)
    with pytest.raises(ValueError):
        session.set_mask(b"\0" * 4, TEXTURE[0] + 1, 1)
    with pytest.raises(ValueError):
        session.read_row(TEXTURE[1])
    with pytest.raises(ValueError):
        session.render(3)
    with pytest.raises(RuntimeError):
        session.start(0)  # not a window
    assert not session.capturing


def test_render_requires_a_mask_and_close_is_idempotent():
    try:
        gpu = vrct_graphics.CaptureSession(0, 16, 16)
    except RuntimeError as error:
        pytest.skip(f"no D3D11 device: {error}")
    with pytest.raises(ValueError):
        gpu.render()
    gpu.close()
    gpu.close()
    assert gpu.closed
    with pytest.raises(RuntimeError):
        gpu.texture_ptr
