"""HWND-based VRChat window capture using mss."""

from __future__ import annotations

import sys
from typing import Optional, Tuple

import numpy as np

try:
    import mss
except Exception:  # pragma: no cover - optional runtime
    mss = None  # type: ignore

try:
    from utils import errorLogging, printLog
except Exception:  # pragma: no cover
    def errorLogging():
        import traceback
        print(traceback.format_exc())

    def printLog(*args, **kwargs):
        print(*args, **kwargs)


_VRCHAT_WINDOW_TITLE = "VRChat"


if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes as wintypes

    _user32 = ctypes.WinDLL("user32", use_last_error=True)

    class _RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    def _find_vrchat_hwnd(substring: str = _VRCHAT_WINDOW_TITLE) -> Optional[int]:
        """Return HWND of first visible window whose title matches substring.

        Prefers exact-title match ("VRChat"), falls back to substring so
        window titles like "VRChat 2023" still resolve.
        """
        HWND = wintypes.HWND
        cb_type = ctypes.WINFUNCTYPE(wintypes.BOOL, HWND, wintypes.LPARAM)
        exact: list[int] = []
        partial: list[int] = []

        def _cb(hwnd, _lp):
            if not _user32.IsWindowVisible(hwnd):
                return True
            length = _user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return True
            buf = ctypes.create_unicode_buffer(length + 1)
            _user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value or ""
            if title == substring:
                exact.append(hwnd)
            elif substring.lower() in title.lower():
                partial.append(hwnd)
            return True

        _user32.EnumWindows(cb_type(_cb), 0)
        if exact:
            return exact[0]
        if partial:
            return partial[0]
        return None

    def _is_iconic(hwnd: int) -> bool:
        return bool(_user32.IsIconic(hwnd))

    def _client_rect(hwnd: int) -> Optional[Tuple[int, int, int, int]]:
        """Return the window's screen-coordinate client rect (left, top, w, h)."""
        rect = _RECT()
        if not _user32.GetClientRect(hwnd, ctypes.byref(rect)):
            return None
        pt = wintypes.POINT(0, 0)
        _user32.ClientToScreen(hwnd, ctypes.byref(pt))
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w <= 0 or h <= 0:
            return None
        return int(pt.x), int(pt.y), int(w), int(h)

else:  # non-Windows placeholder — HWND path is a no-op
    def _find_vrchat_hwnd(substring: str = _VRCHAT_WINDOW_TITLE) -> Optional[int]:
        return None

    def _is_iconic(hwnd: int) -> bool:
        return True

    def _client_rect(hwnd: int):
        return None


class HwndCapture:
    """Captures the VRChat client area via mss.

    Returns a BGR ndarray on success, or None if the window is missing,
    minimized, or capture failed.
    """

    def __init__(self, window_title: str = _VRCHAT_WINDOW_TITLE) -> None:
        self.window_title = window_title
        self._hwnd: Optional[int] = None
        self._sct = None
        if mss is not None:
            try:
                self._sct = mss.mss()
            except Exception:
                errorLogging()
                self._sct = None

    def isAvailable(self) -> bool:
        return sys.platform == "win32" and mss is not None and self._sct is not None

    def _refreshHwnd(self) -> Optional[int]:
        hwnd = _find_vrchat_hwnd(self.window_title)
        self._hwnd = hwnd
        return hwnd

    def capture(self) -> Optional[np.ndarray]:
        if not self.isAvailable():
            return None
        hwnd = self._hwnd
        if hwnd is None or not _client_rect(hwnd):
            hwnd = self._refreshHwnd()
        if hwnd is None:
            return None
        if _is_iconic(hwnd):
            return None
        rect = _client_rect(hwnd)
        if rect is None:
            self._hwnd = None
            return None
        left, top, width, height = rect
        try:
            shot = self._sct.grab({"left": left, "top": top, "width": width, "height": height})
        except Exception:
            errorLogging()
            self._hwnd = None
            return None
        # mss returns BGRA; convert to BGR (OpenCV convention)
        arr = np.array(shot, dtype=np.uint8)
        if arr.ndim == 3 and arr.shape[2] == 4:
            arr = arr[:, :, :3]
        return arr

    def close(self) -> None:
        try:
            if self._sct is not None:
                self._sct.close()
        except Exception:
            pass
        self._sct = None
        self._hwnd = None


def isFrameBlank(frame: Optional[np.ndarray], mean_threshold: float = 3.0, var_threshold: float = 20.0) -> bool:
    """Return True when frame is effectively black / no signal (VRChat minimized)."""
    if frame is None:
        return True
    try:
        mean = float(np.mean(frame))
        var = float(np.var(frame))
    except Exception:
        return True
    return mean < mean_threshold or var < var_threshold
