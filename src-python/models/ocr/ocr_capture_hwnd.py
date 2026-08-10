"""HWND-based VRChat window capture using PrintWindow.

PrintWindow renders straight from the target window's own surface, so it
captures VRChat's content even when another window (e.g. VRCT itself)
visually overlaps it on screen. A screen-region grab (e.g. via mss) would
instead capture whatever is topmost at those screen coordinates, which is
wrong whenever VRCT overlaps the VRChat window.
"""

from __future__ import annotations

import sys
from typing import Optional, Tuple

import numpy as np

try:
    from psutil import Process
except Exception:  # pragma: no cover
    Process = None  # type: ignore

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
    _gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

    _PW_RENDERFULLCONTENT = 0x00000002

    _user32.GetWindowDC.restype = wintypes.HDC
    _user32.GetWindowDC.argtypes = [wintypes.HWND]
    _user32.ReleaseDC.restype = ctypes.c_int
    _user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    _user32.PrintWindow.restype = wintypes.BOOL
    _user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
    _user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    _user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]

    _gdi32.CreateCompatibleDC.restype = wintypes.HDC
    _gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    _gdi32.CreateCompatibleBitmap.restype = ctypes.c_void_p
    _gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
    _gdi32.SelectObject.restype = ctypes.c_void_p
    _gdi32.SelectObject.argtypes = [wintypes.HDC, ctypes.c_void_p]
    _gdi32.DeleteObject.restype = wintypes.BOOL
    _gdi32.DeleteObject.argtypes = [ctypes.c_void_p]
    _gdi32.DeleteDC.restype = wintypes.BOOL
    _gdi32.DeleteDC.argtypes = [wintypes.HDC]
    _gdi32.GetDIBits.restype = ctypes.c_int
    _gdi32.GetDIBits.argtypes = [
        wintypes.HDC, ctypes.c_void_p, wintypes.UINT, wintypes.UINT,
        ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT,
    ]

    class _RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    class _BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", ctypes.c_long),
            ("biHeight", ctypes.c_long),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", ctypes.c_long),
            ("biYPelsPerMeter", ctypes.c_long),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    def _process_name(hwnd: int) -> str:
        """Return the lowercase executable name (without .exe) owning hwnd, or ""."""
        if Process is None:
            return ""
        pid = wintypes.DWORD(0)
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return ""
        try:
            name = Process(pid.value).name()
        except Exception:
            return ""
        if name.lower().endswith(".exe"):
            name = name[:-4]
        return name.lower()

    def _find_vrchat_hwnd(substring: str = _VRCHAT_WINDOW_TITLE) -> Optional[int]:
        """Return HWND of first visible window matching substring.

        Matches against the window title first (exact, then substring), and
        falls back to the owning process's executable name so values like
        "VRChat.exe" work too, not just literal window titles.
        """
        HWND = wintypes.HWND
        cb_type = ctypes.WINFUNCTYPE(wintypes.BOOL, HWND, wintypes.LPARAM)
        exact: list[int] = []
        partial: list[int] = []
        by_process: list[int] = []

        needle = substring.lower()
        needle_no_exe = needle[:-4] if needle.endswith(".exe") else needle

        def _cb(hwnd, _lp):
            if not _user32.IsWindowVisible(hwnd):
                return True
            length = _user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                _user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value or ""
                if title == substring:
                    exact.append(hwnd)
                    return True
                if needle in title.lower():
                    partial.append(hwnd)
                    return True
            if _process_name(hwnd) == needle_no_exe:
                by_process.append(hwnd)
            return True

        _user32.EnumWindows(cb_type(_cb), 0)
        if exact:
            return exact[0]
        if partial:
            return partial[0]
        if by_process:
            return by_process[0]
        return None

    def _is_iconic(hwnd: int) -> bool:
        return bool(_user32.IsIconic(hwnd))

    def _window_rect(hwnd: int) -> Optional[Tuple[int, int, int, int]]:
        """Return the window's screen-coordinate full rect (left, top, w, h)."""
        rect = _RECT()
        if not _user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return None
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w <= 0 or h <= 0:
            return None
        return int(rect.left), int(rect.top), int(w), int(h)

    def _print_window(hwnd: int, width: int, height: int) -> Optional[np.ndarray]:
        """Render hwnd's own content into an offscreen bitmap via PrintWindow.

        This is occlusion-safe: it reads directly from the window's surface
        rather than from screen pixels, so overlapping windows on top of it
        (e.g. VRCT's own window) never bleed into the capture.
        """
        hwnd_dc = _user32.GetWindowDC(hwnd)
        if not hwnd_dc:
            return None
        mem_dc = None
        bitmap = None
        old_obj = None
        try:
            mem_dc = _gdi32.CreateCompatibleDC(hwnd_dc)
            if not mem_dc:
                return None
            bitmap = _gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
            if not bitmap:
                return None
            old_obj = _gdi32.SelectObject(mem_dc, bitmap)

            ok = _user32.PrintWindow(hwnd, mem_dc, _PW_RENDERFULLCONTENT)
            if not ok:
                return None

            bmi = _BITMAPINFOHEADER()
            bmi.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
            bmi.biWidth = width
            bmi.biHeight = -height  # negative = top-down DIB
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            bmi.biCompression = 0  # BI_RGB

            buf = (ctypes.c_ubyte * (width * height * 4))()
            got = _gdi32.GetDIBits(
                mem_dc, bitmap, 0, height,
                ctypes.byref(buf), ctypes.byref(bmi), 0,  # DIB_RGB_COLORS
            )
            if got == 0:
                return None
            arr = np.frombuffer(buf, dtype=np.uint8).reshape((height, width, 4))
            return arr[:, :, :3].copy()  # BGRA -> BGR
        finally:
            if mem_dc and old_obj is not None:
                _gdi32.SelectObject(mem_dc, old_obj)
            if bitmap:
                _gdi32.DeleteObject(bitmap)
            if mem_dc:
                _gdi32.DeleteDC(mem_dc)
            _user32.ReleaseDC(hwnd, hwnd_dc)

else:  # non-Windows placeholder — HWND path is a no-op
    def _find_vrchat_hwnd(substring: str = _VRCHAT_WINDOW_TITLE) -> Optional[int]:
        return None

    def _is_iconic(hwnd: int) -> bool:
        return True

    def _window_rect(hwnd: int):
        return None

    def _print_window(hwnd: int, width: int, height: int):
        return None


class HwndCapture:
    """Captures VRChat's own window content via PrintWindow.

    Returns a BGR ndarray on success, or None if the window is missing,
    minimized, or capture failed.
    """

    def __init__(self, window_title: str = _VRCHAT_WINDOW_TITLE) -> None:
        self.window_title = window_title
        self._hwnd: Optional[int] = None

    def isAvailable(self) -> bool:
        return sys.platform == "win32"

    def _refreshHwnd(self) -> Optional[int]:
        hwnd = _find_vrchat_hwnd(self.window_title)
        self._hwnd = hwnd
        return hwnd

    def capture(self) -> Optional[np.ndarray]:
        if not self.isAvailable():
            return None
        hwnd = self._hwnd
        if hwnd is None or _window_rect(hwnd) is None:
            hwnd = self._refreshHwnd()
        if hwnd is None:
            return None
        if _is_iconic(hwnd):
            return None
        rect = _window_rect(hwnd)
        if rect is None:
            self._hwnd = None
            return None
        _left, _top, width, height = rect
        try:
            frame = _print_window(hwnd, width, height)
        except Exception:
            errorLogging()
            self._hwnd = None
            return None
        return frame

    def close(self) -> None:
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
