"""Detect candidate VRChat chat-bubble regions in a captured frame.

VRChat chat bubbles are semi-transparent rounded panels floating above
avatars. This detector uses a color/contour heuristic to enumerate
candidate ROIs before we spend cycles on OCR:

1. Convert to grayscale, blur, then threshold to isolate bright-on-dark
   text-ish areas plus the darker bubble backing plate.
2. Morphologically close text lines together so a paragraph forms one
   contiguous blob.
3. Take contour bounding rects and filter by aspect ratio, size, and
   position (exclude far edges where HUD/nameplate strips live).
4. Return a list of (bbox, crop_bgr) tuples for the OCR engine.

The thresholds are intentionally lenient — false positives are cheaper
than false negatives here because the OCR engine + min-confidence knob
filters out noise crops that contain no readable text.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore


BBox = Tuple[int, int, int, int]  # (x, y, w, h)


class BubbleDetector:
    def __init__(
        self,
        min_area_ratio: float = 0.0008,
        max_area_ratio: float = 0.20,
        min_aspect: float = 1.2,
        max_aspect: float = 20.0,
        edge_margin_ratio: float = 0.03,
        exclude_bottom_ratio: float = 0.15,
    ) -> None:
        self.min_area_ratio = min_area_ratio
        self.max_area_ratio = max_area_ratio
        self.min_aspect = min_aspect
        self.max_aspect = max_aspect
        self.edge_margin_ratio = edge_margin_ratio
        self.exclude_bottom_ratio = exclude_bottom_ratio

    def isAvailable(self) -> bool:
        return cv2 is not None

    def detect(self, frame: np.ndarray) -> List[Tuple[BBox, np.ndarray]]:
        if not self.isAvailable() or frame is None or frame.size == 0:
            return []
        h, w = frame.shape[:2]
        frame_area = float(h * w)
        if frame_area <= 0:
            return []

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (3, 3), 0)
            # Adaptive threshold catches both light-on-dark and dark-on-light
            # panel-vs-text combinations without hard-coding VRChat's palette.
            binary = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV,
                31,
                7,
            )
            # Close text into paragraph-sized blobs.
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 5))
            closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        except Exception:
            return []

        try:
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        except Exception:
            return []

        margin_x = int(w * self.edge_margin_ratio)
        margin_y = int(h * self.edge_margin_ratio)
        bottom_hud_y = int(h * (1.0 - self.exclude_bottom_ratio))

        results: List[Tuple[BBox, np.ndarray]] = []
        for cnt in contours:
            x, y, cw, ch = cv2.boundingRect(cnt)
            if cw <= 0 or ch <= 0:
                continue
            area = float(cw * ch)
            area_ratio = area / frame_area
            if area_ratio < self.min_area_ratio or area_ratio > self.max_area_ratio:
                continue
            aspect = cw / float(ch)
            if aspect < self.min_aspect or aspect > self.max_aspect:
                continue
            # Reject anything hugging the frame borders (world sign / HUD).
            if x < margin_x or y < margin_y:
                continue
            if (x + cw) > (w - margin_x):
                continue
            # Reject bottom HUD strip (nameplate, notifications, VRChat menu).
            if y > bottom_hud_y:
                continue

            # Pad the crop slightly so OCR sees full glyph boundaries.
            pad = 4
            x0 = max(0, x - pad)
            y0 = max(0, y - pad)
            x1 = min(w, x + cw + pad)
            y1 = min(h, y + ch + pad)
            crop = frame[y0:y1, x0:x1]
            if crop.size == 0:
                continue
            results.append(((x0, y0, x1 - x0, y1 - y0), crop))

        # Sort by area descending so bigger bubbles come first (they're more
        # likely the primary chat message and get OCR budget first).
        results.sort(key=lambda item: item[0][2] * item[0][3], reverse=True)
        return results
