"""Image sources for the standalone collector; no VRCT backend initialization."""

from __future__ import annotations

import ctypes as ct
from dataclasses import dataclass
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
import time

import numpy as np
import psutil

if __package__:
    from .openvr_d3d11 import D3D11Mirror, vrchat_windows
else:
    from openvr_d3d11 import D3D11Mirror, vrchat_windows


class CaptureUnavailable(RuntimeError):
    """A transient failure: skip this sample, never reuse a previous image."""


@dataclass
class Frame:
    rgb: np.ndarray
    captured_monotonic: float
    metadata: dict


def process_name(pid: int) -> str:
    try:
        return psutil.Process(pid).name().lower() if pid else ""
    except psutil.Error:
        return ""


class CaptureSource:
    """One owner thread must call capture and close, in a standalone process."""

    def __init__(self, backend: str = "auto", eye: str = "left") -> None:
        self.backend = backend
        self.eye = eye
        self._vr = None
        self._system = None
        self._compositor = None
        self._mirror = None
        self._last_frame = None
        self._vrchat_scene_pid = None
        self._hwnd_module = None

    def _connect_vr(self) -> None:
        import openvr

        self._system = openvr.init(openvr.VRApplication_Background)
        self._vr = openvr
        self._compositor = openvr.VRCompositor()

    def capture(self) -> Frame:
        try:
            if self.backend != "hwnd":
                if self._vrchat_scene_pid and process_name(self._vrchat_scene_pid) != "vrchat.exe":
                    self._vrchat_scene_pid = None
                if self._compositor is None:
                    running = any(p.info["name"] == "vrcompositor.exe"
                                  for p in psutil.process_iter(["name"]))
                    if running or self.backend == "openvr":
                        self._connect_vr()
                if self._compositor is not None:
                    focus = self._compositor.getCurrentSceneFocusProcess()
                    if process_name(focus) == "vrchat.exe":
                        self._vrchat_scene_pid = focus
                if self.backend == "openvr" or self._vrchat_scene_pid:
                    if self._compositor is None:
                        raise CaptureUnavailable("SteamVR is unavailable; waiting to reconnect")
                    return self._capture_vr()
            return self._capture_hwnd()
        except CaptureUnavailable:
            raise
        except Exception as exc:
            self.close()
            raise CaptureUnavailable(f"Capture failed: {type(exc).__name__}: {exc}") from exc

    def _vr_state(self) -> tuple[int, int]:
        renderer = self._compositor.getLastFrameRenderer()
        focus = self._compositor.getCurrentSceneFocusProcess()
        if process_name(renderer) != "vrchat.exe" or focus != renderer:
            raise CaptureUnavailable("VRChat is not the active SteamVR scene")
        timing = self._vr.Compositor_FrameTiming()
        timing.m_nSize = ct.sizeof(timing)
        if not self._compositor.function_table.getFrameTiming(ct.byref(timing), 0):
            raise CaptureUnavailable("SteamVR frame timing is unavailable")
        return renderer, timing.m_nFrameIndex

    def _capture_vr(self) -> Frame:
        renderer, frame_index = self._vr_state()
        if (renderer, frame_index) == self._last_frame:
            raise CaptureUnavailable("SteamVR has not produced a new frame")
        if self._mirror is None:
            eye = self._vr.Eye_Left if self.eye == "left" else self._vr.Eye_Right
            self._mirror = D3D11Mirror(self._system, self._compositor, eye)
        captured = time.monotonic()
        utc = datetime.now(timezone.utc).isoformat()
        rgb = self._mirror.read()
        after_renderer, after_index = self._vr_state()
        if renderer != after_renderer:
            raise CaptureUnavailable("SteamVR scene changed during capture")
        self._last_frame = (renderer, frame_index)
        return Frame(rgb, captured, {
            "captured_at": utc, "backend": "openvr_d3d11", "eye": self.eye,
            "renderer_pid": renderer, "compositor_frame_before": frame_index,
            "compositor_frame_after": after_index, "windows": vrchat_windows(),
        })

    def _capture_hwnd(self) -> Frame:
        # Load only the existing PrintWindow implementation, not OCR/models.
        if self._hwnd_module is None:
            if getattr(sys, "frozen", False):
                path = Path(__file__).resolve().parent / "capture/ocr_capture_hwnd.py"
            else:
                path = Path(__file__).resolve().parents[1] / "src-python/models/ocr/ocr_capture_hwnd.py"
            spec = importlib.util.spec_from_file_location("_collector_hwnd", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._hwnd_module = module
        candidates = [w for w in vrchat_windows() if w["visible"]]
        if len(candidates) != 1:
            raise CaptureUnavailable("Expected one VRChat window; launch VRChat or select --backend openvr")
        window = candidates[0]
        if window["minimized"]:
            raise CaptureUnavailable("Desktop VRChat window is minimized")
        module = self._hwnd_module
        hwnd = window["hwnd"]
        rect = module._window_rect(hwnd)
        if rect is None:
            raise CaptureUnavailable("VRChat window has no drawable surface")
        captured = time.monotonic()
        utc = datetime.now(timezone.utc).isoformat()
        # Use this process-verified HWND, never the title-substring finder.
        bgr = module._print_window(hwnd, rect[2], rect[3])
        after = [w for w in vrchat_windows() if w == window]
        if not after or module.isFrameBlank(bgr):
            raise CaptureUnavailable("VRChat window changed or returned an empty image")
        return Frame(np.ascontiguousarray(bgr[:, :, ::-1]), captured, {
            "captured_at": utc, "backend": "hwnd", "eye": None,
            "renderer_pid": window["pid"], "windows": [window],
        })

    def close(self) -> None:
        try:
            if self._mirror is not None:
                self._mirror.close()
        finally:
            self._mirror = None
            self._last_frame = None
            try:
                if self._vr is not None:
                    self._vr.shutdown()
            finally:
                self._vr = self._system = self._compositor = None
