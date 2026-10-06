"""OpenVR compositor mirror-texture capture.

Grabs the HMD left-eye image so OCR still works when the VRChat desktop
mirror window is minimized (a common VR-mode setup).

Reads IVRCompositor::GetMirrorTextureD3D11 through ocr_capture_d3d11.py.
The OpenGL variant (GetMirrorTextureGL) is not an option: SteamVR fails to
import its own D3D11 texture into GL ("Invalid format") and always returns
CompositorError_InvalidTexture (ValveSoftware/openvr#178, #1410; reproduced
on hardware 2026-09-27).

Three lifecycle rules matter here:

1. OpenVR is initialized **per process** and shared with Overlay and
   Clipboard, so the session goes through models/openvr_session.py
   (acquire()/release()), never openvr.init()/shutdown() directly.
2. The mirror texture is acquired once and reused every frame; the D3D11
   objects are created, read and released on the OCR worker thread.
3. Only VRChat's frames are read: while another scene app (SteamVR Home
   etc.) is presenting, capture() returns None so the facade can fall back
   to the desktop window.
"""

from __future__ import annotations

import sys
from typing import Optional

import numpy as np

try:
    import openvr
    try:
        from models import openvr_session
    except ImportError:
        import openvr_session
except Exception:  # pragma: no cover
    openvr = None  # type: ignore
    openvr_session = None  # type: ignore

try:
    from psutil import Process
except Exception:  # pragma: no cover
    Process = None  # type: ignore

from .ocr_capture_d3d11 import D3D11Mirror

try:
    from utils import errorLogging, printLog
except Exception:  # pragma: no cover
    def errorLogging():
        import traceback
        print(traceback.format_exc())

    def printLog(*args, **kwargs):
        print(*args, **kwargs)


class OpenVRMirrorCapture:
    """Read the HMD left-eye mirror texture from the OpenVR compositor.

    Lazily joins the process-wide OpenVR session and acquires the compositor
    mirror texture. capture() never raises: on any failure it releases what it
    holds so the next tick can reconnect, and returns None.
    """

    def __init__(self, eye: str = "left") -> None:
        self._eye_name = eye
        self._compositor = None
        self._mirror: Optional[D3D11Mirror] = None
        self._session_held = False
        # 失敗が続く間 (SteamVR再起動中など) は5秒ごとに再試行するので、
        # トレースバックは最初の1回だけ残す。成功したら次の失敗をまた残す。
        self._failure_logged = False

    def isAvailable(self) -> bool:
        return openvr is not None and sys.platform == "win32"

    @property
    def _eye(self):
        if openvr is None:
            return 0
        return openvr.Eye_Right if self._eye_name == "right" else openvr.Eye_Left

    def _logFailure(self, message: str) -> None:
        if self._failure_logged:
            return
        self._failure_logged = True
        errorLogging()
        printLog(f"OCR: {message} (further failures are not logged until a frame is read)")

    def _init(self) -> bool:
        if self._mirror is not None:
            return True
        if not self.isAvailable():
            return False
        try:
            # Join (or create) the process-wide OpenVR session. Background
            # mode so we never steal focus from the running scene app.
            system = openvr_session.acquire(openvr.VRApplication_Background)
            self._session_held = True
            self._compositor = openvr.IVRCompositor()
            self._mirror = D3D11Mirror(system, self._compositor, self._eye)
            return True
        except Exception:
            self._logFailure("could not open the OpenVR mirror texture")
            self._resetVrState()
            return False

    def _resetVrState(self) -> None:
        """Release the mirror texture, then our session reference.

        The mirror is released through the compositor, so it goes first.
        Releasing the session (rather than holding a possibly dead one) lets
        the next _init() reconnect, the same release-then-acquire order
        Overlay.reStartOverlay() uses.
        """
        if self._mirror is not None:
            try:
                self._mirror.close()
            except Exception:
                errorLogging()
            self._mirror = None
        self._compositor = None
        if self._session_held:
            self._session_held = False
            try:
                openvr_session.release()
            except Exception:
                errorLogging()

    def _isVrchatScene(self) -> bool:
        """VRChat is the app SteamVR is currently presenting.

        Same check as tools/ocr_capture_source.py, verified on hardware: the
        last frame renderer is the scene focus process and it is VRChat.
        """
        if Process is None:
            return False
        renderer = self._compositor.getLastFrameRenderer()
        if not renderer or renderer != self._compositor.getCurrentSceneFocusProcess():
            return False
        try:
            return Process(renderer).name().lower() == "vrchat.exe"
        except Exception:
            return False

    def capture(self) -> Optional[np.ndarray]:
        if not self._init():
            return None
        try:
            if not self._isVrchatScene():
                return None
            rgb = self._mirror.read()
        except Exception:
            # The compositor session may have been torn down (SteamVR restart).
            # Drop everything so the next tick re-acquires.
            self._logFailure("reading the OpenVR mirror texture failed")
            self._resetVrState()
            return None
        self._failure_logged = False
        # D3D11Mirror returns RGB (for the tools); OCR uses BGR like the HWND path.
        return np.ascontiguousarray(rgb[:, :, ::-1])

    def close(self) -> None:
        """Release OCR-owned resources and our shared-session reference.

        The real openvr.shutdown() only runs once Overlay/Clipboard have
        released theirs too (models/openvr_session.py).
        """
        self._resetVrState()
