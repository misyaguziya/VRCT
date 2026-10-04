"""Tooltip protocol and capture helpers, independent of OpenVR."""
import math

import numpy as np
from PIL import Image, ImageDraw


def _finite_number(value: object) -> bool:
    return type(value) in (int, float) and -1e6 <= value <= 1e6 and math.isfinite(value)


def validate_tooltip(data: object) -> dict:
    """Return a detached payload; reject malformed or out-of-range values."""
    if not isinstance(data, dict):
        raise ValueError("tooltip must be an object")  # noqa: TRY004 - endpoint validation uses ValueError for every malformed payload.
    for key, limit in (("epoch", (1 << 48) - 1), ("revision", (1 << 32) - 1)):
        value = data.get(key)
        if type(value) is not int or not 1 <= value <= limit:
            raise ValueError(key)
    if type(data.get("visible")) is not bool:
        raise ValueError("visible")
    result = {key: data[key] for key in ("epoch", "revision", "visible")}
    if not result["visible"]:
        if set(data) != set(result):
            raise ValueError("hidden payload")
        return result
    if set(data) - {"epoch", "revision", "visible", "region", "button", "size", "arrow_x", "mode"}:
        raise ValueError("unknown field")
    region = data.get("region")
    if region not in ("launcher", "toolbar") or data.get("mode", "hover") not in ("hover", "focus"):
        raise ValueError("region or mode")
    result.update(region=region, mode=data.get("mode", "hover"))
    for key, length in (("button", 4), ("size", 2)):
        values = data.get(key)
        if not isinstance(values, list) or len(values) != length or any(not _finite_number(v) for v in values):
            raise ValueError(key)
        result[key] = list(values)
    x, y, w, h = result["button"]
    parent_w, parent_h = (880, 128) if region == "launcher" else (720, 96)
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > parent_w or y + h > parent_h:
        raise ValueError("button bounds")
    if result["size"][0] != 360 or not 1 <= result["size"][1] <= 104:
        raise ValueError("size bounds")
    arrow = data.get("arrow_x")
    if not _finite_number(arrow) or not 12 <= arrow <= 348:
        raise ValueError("arrow_x")
    result["arrow_x"] = arrow
    return result


def marker_matches(pixels: np.ndarray, layout: dict, state: dict) -> bool:
    """Read 80 big-endian bits from 4x8 logical-pixel black/white cells."""
    scale = pixels.shape[1] / layout["atlas"][0]
    x, y, _, _ = layout["regions"]["tooltip"]
    bits = (state["epoch"] << 32) | state["revision"]
    for index in range(80):
        px, py = round((x + index * 4 + 2) * scale), round((y + 4) * scale)
        if not (0 <= py < pixels.shape[0] and 0 <= px < pixels.shape[1]):
            return False
        color = pixels[py, px, :3]
        expected = (bits >> (79 - index)) & 1
        if not (np.all(color >= 224) if expected else np.all(color <= 31)):
            return False
    return True


def tooltip_mask(image_size: tuple, layout: dict, state: dict, static_mask: np.ndarray) -> np.ndarray:
    """Add only the body and arrow; the generation marker stays transparent."""
    mask = Image.fromarray(static_mask.copy())
    draw = ImageDraw.Draw(mask)
    scale = image_size[0] / layout["atlas"][0]
    x, y, _, _ = layout["regions"]["tooltip"]
    y += 8
    w, h = state["size"]
    draw.rounded_rectangle((round(x * scale), round(y * scale), round((x + w) * scale) - 1, round((y + h) * scale) - 1), radius=round(12 * scale), fill=255)
    arrow = state["arrow_x"]
    draw.polygon([(round((x + arrow - 6) * scale), round((y + h - 1) * scale)), (round((x + arrow + 6) * scale), round((y + h - 1) * scale)), (round((x + arrow) * scale), round((y + h + 6) * scale) - 1)], fill=255)
    return np.asarray(mask)
