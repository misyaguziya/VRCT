"""D3D11 mirror primitives for the standalone capture tools.

The reader itself lives in src-python/models/ocr/ocr_capture_d3d11.py so the
tools and VRCT's OCR share one implementation. It is loaded by path (like
ocr_capture_hwnd.py in ocr_capture_source.py) so the tools never import VRCT.
"""

from __future__ import annotations

import ctypes as ct
from ctypes import wintypes as wt
import importlib.util
from pathlib import Path
import sys


def _load_reader():
    if getattr(sys, "frozen", False):
        path = Path(__file__).resolve().parent / "capture/ocr_capture_d3d11.py"
    else:
        path = Path(__file__).resolve().parents[1] / "src-python/models/ocr/ocr_capture_d3d11.py"
    spec = importlib.util.spec_from_file_location("_tools_ocr_capture_d3d11", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_reader = _load_reader()
TextureDesc = _reader.TextureDesc
D3D11Mirror = _reader.D3D11Mirror


def vrchat_windows():
    """Read window state only; do not focus, restore or minimize anything."""
    import psutil

    pids = {p.info["pid"] for p in psutil.process_iter(["pid", "name"])
            if (p.info["name"] or "").lower() == "vrchat.exe"}
    user32 = ct.WinDLL("user32", use_last_error=True)
    callback_type = ct.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    user32.EnumWindows.argtypes = [callback_type, wt.LPARAM]
    user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ct.POINTER(wt.DWORD)]
    user32.IsIconic.argtypes = [wt.HWND]
    user32.IsWindowVisible.argtypes = [wt.HWND]
    user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ct.c_int]
    windows = []

    @callback_type
    def visit(hwnd, _):
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ct.byref(pid))
        if pid.value in pids:
            title = ct.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, title, 256)
            if title.value == "VRChat":
                windows.append({"pid": pid.value, "hwnd": int(hwnd),
                                "minimized": bool(user32.IsIconic(hwnd)),
                                "visible": bool(user32.IsWindowVisible(hwnd))})
        return True

    user32.EnumWindows(visit, 0)
    return windows
