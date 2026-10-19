"""Capture backend facade for OCR: picks HWND vs OpenVR by SteamVR status.

Contract: get() returns a BGR ndarray or None. It never raises. The
facade rechecks SteamVR periodically so the backend follows the user
launching/closing SteamVR while VRCT is running. When the VR read gives
nothing (VRChat is not the SteamVR scene, or the read failed) it falls back
to the desktop window until the next recheck.
"""

from __future__ import annotations

import os
import time
from typing import Optional

import numpy as np

from ..process_check import isProcessRunning

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
    return isProcessRunning("vrmonitor.exe" if os.name == "nt" else "vrmonitor")


class OcrCapture:
    """Facade that returns the current VRChat frame using the best backend."""

    BACKEND_HWND = "hwnd"
    BACKEND_OPENVR = "openvr_mirror"
    BACKEND_NONE = "none"

    def __init__(self, window_title: str = "VRChat") -> None:
        self._hwnd = HwndCapture(window_title=window_title)
        self._openvr: Optional[OpenVRMirrorCapture] = None
        self._backend = self.BACKEND_NONE
        # 実際にフレームが取れた経路。VRとデスクトップを5秒ごとに試し直すので、
        # 試した経路ではなく取れた経路が変わったときだけログに出す。
        self._source = self.BACKEND_NONE
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
                self._backend = self.BACKEND_OPENVR
                return self._backend
        # Fall back to HWND
        if self._openvr is not None:
            try:
                self._openvr.close()
            except Exception:
                pass
            self._openvr = None
        self._backend = self.BACKEND_HWND if self._hwnd.isAvailable() else self.BACKEND_NONE
        return self._backend

    def _noteSource(self, backend: str) -> None:
        if self._source != backend:
            printLog(f"OCR capture backend -> {backend}")
            self._source = backend

    @property
    def backend(self) -> str:
        return self._backend

    def get(self) -> Optional[np.ndarray]:
        backend = self._selectBackend()
        try:
            if backend == self.BACKEND_OPENVR and self._openvr is not None:
                frame = self._openvr.capture()
                if frame is not None:
                    # The compositor only hands back a texture when it is actually
                    # presenting, so an all-black frame here is a legitimately dark
                    # scene (night world, loading screen) rather than a dead
                    # surface. Only reject a truly uniform frame.
                    # Exact and cheap (12 ms at 2575x1455; np.var on the whole frame took 170 ms).
                    if frame.min() == frame.max():
                        return None
                    self._noteSource(self.BACKEND_OPENVR)
                    return frame
                # VRChat is not the SteamVR scene (desktop mode, SteamVR Home)
                # or the VR read failed: use the desktop window until the
                # next recheck instead of reading nothing.
                self._backend = self.BACKEND_HWND if self._hwnd.isAvailable() else self.BACKEND_NONE
                backend = self._backend
            if backend == self.BACKEND_HWND:
                frame = self._hwnd.capture()
                # A minimized or occluded window keeps returning a stale black
                # buffer, so the stricter thresholds earn their keep here.
                if isFrameBlank(frame):
                    return None
                self._noteSource(self.BACKEND_HWND)
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
        self._source = self.BACKEND_NONE
