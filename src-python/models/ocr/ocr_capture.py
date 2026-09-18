"""Capture backend facade for OCR: picks HWND vs OpenVR by SteamVR status.

Contract: get() returns a BGR ndarray or None. It never raises. The
facade rechecks SteamVR periodically so the backend follows the user
launching/closing SteamVR while VRCT is running.
"""

from __future__ import annotations

import os
import time
from typing import Optional

import numpy as np

try:
    from psutil import process_iter
except Exception:  # pragma: no cover
    process_iter = None  # type: ignore

from .ocr_capture_hwnd import HwndCapture, isFrameBlank
from .ocr_capture_openvr import OpenVRMirrorCapture

try:
    from utils import errorLogging, printLog
except Exception:  # pragma: no cover
    def errorLogging():
        import traceback
        print(traceback.format_exc())

    def printLog(*args, **kwargs):
        print(*args, **kwargs)


_STEAMVR_RECHECK_INTERVAL_SEC = 5.0


def _isSteamvrRunning() -> bool:
    if process_iter is None:
        return False
    proc_name = "vrmonitor.exe" if os.name == "nt" else "vrmonitor"
    try:
        return proc_name in (p.name() for p in process_iter())
    except Exception:
        return False


class OcrCapture:
    """Facade that returns the current VRChat frame using the best backend."""

    BACKEND_HWND = "hwnd"
    BACKEND_OPENVR = "openvr_mirror"
    BACKEND_NONE = "none"

    def __init__(self, window_title: str = "VRChat") -> None:
        self._hwnd = HwndCapture(window_title=window_title)
        self._openvr: Optional[OpenVRMirrorCapture] = None
        self._backend = self.BACKEND_NONE
        self._last_check = 0.0

    def _selectBackend(self, force: bool = False) -> str:
        now = time.monotonic()
        if not force and (now - self._last_check) < _STEAMVR_RECHECK_INTERVAL_SEC:
            return self._backend
        self._last_check = now

        want_openvr = _isSteamvrRunning()
        if want_openvr:
            if self._openvr is None:
                candidate = OpenVRMirrorCapture()
                if candidate.isAvailable():
                    self._openvr = candidate
            if self._openvr is not None and self._openvr.isAvailable():
                if self._backend != self.BACKEND_OPENVR:
                    printLog(f"OCR capture backend -> {self.BACKEND_OPENVR}")
                self._backend = self.BACKEND_OPENVR
                return self._backend
        # Fall back to HWND
        if self._openvr is not None:
            try:
                self._openvr.close()
            except Exception:
                pass
            self._openvr = None
        if self._hwnd.isAvailable():
            if self._backend != self.BACKEND_HWND:
                printLog(f"OCR capture backend -> {self.BACKEND_HWND}")
            self._backend = self.BACKEND_HWND
        else:
            self._backend = self.BACKEND_NONE
        return self._backend

    @property
    def backend(self) -> str:
        return self._backend

    def get(self) -> Optional[np.ndarray]:
        backend = self._selectBackend()
        try:
            if backend == self.BACKEND_OPENVR and self._openvr is not None:
                frame = self._openvr.capture()
                # The compositor only hands back a texture when it is actually
                # presenting, so an all-black frame here is a legitimately dark
                # scene (night world, loading screen) rather than a dead
                # surface. Only reject a truly uniform frame.
                if isFrameBlank(frame, mean_threshold=0.0, var_threshold=1e-6):
                    return None
                return frame
            if backend == self.BACKEND_HWND:
                frame = self._hwnd.capture()
                # A minimized or occluded window keeps returning a stale black
                # buffer, so the stricter thresholds earn their keep here.
                if isFrameBlank(frame):
                    return None
                return frame
        except Exception:
            errorLogging()
        return None

    def close(self) -> None:
        try:
            self._hwnd.close()
        except Exception:
            pass
        if self._openvr is not None:
            try:
                self._openvr.close()
            except Exception:
                pass
            self._openvr = None
        self._backend = self.BACKEND_NONE
