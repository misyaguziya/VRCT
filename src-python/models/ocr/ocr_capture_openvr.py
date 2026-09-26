"""OpenVR compositor mirror-texture capture.

Grabs the HMD left-eye submitted image so OCR still works when the
VRChat desktop mirror window is minimized (a common VR-mode setup).

Uses IVRCompositor::GetMirrorTextureGL + PyOpenGL to read pixels back
into a numpy array. Requires an active OpenGL context, which we create
via GLFW (hidden window) on first use.

Three lifecycle rules matter here:

1. OpenVR is initialized **per process** and shared with Overlay and
   Clipboard, so the session goes through models/openvr_session.py
   (acquire()/release()), never openvr.init()/shutdown() directly.
2. The mirror texture must be acquired once (not per frame) and then
   locked/unlocked around every read, per the OpenVR contract.
3. Only VRChat's frames are read: while another scene app (SteamVR Home
   etc.) is presenting, capture() returns None so the facade can fall back
   to the desktop window.
"""

from __future__ import annotations

from typing import Optional, Tuple

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

try:
    from OpenGL import GL
except Exception:  # pragma: no cover
    GL = None  # type: ignore

try:
    import glfw
except Exception:  # pragma: no cover
    glfw = None  # type: ignore

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

    Lazily initializes a hidden GLFW window (for the GL context), joins the
    process-wide OpenVR session, and acquires the compositor mirror texture.
    capture() never raises: on any failure it tears down just enough state to
    retry cleanly on the next tick and returns None.
    """

    def __init__(self, eye: str = "left") -> None:
        self._eye_name = eye
        self._compositor = None
        self._gl_window = None
        self._texture_id: Optional[int] = None
        self._shared_handle = None
        self._session_held = False
        self._initialized = False

    def isAvailable(self) -> bool:
        return openvr is not None and GL is not None and glfw is not None

    @property
    def _eye(self):
        if openvr is None:
            return 0
        return openvr.Eye_Right if self._eye_name == "right" else openvr.Eye_Left

    def _initGlContext(self) -> bool:
        if self._gl_window is not None:
            return True
        if not glfw.init():
            printLog("OCR: glfw.init() failed")
            return False
        glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
        self._gl_window = glfw.create_window(64, 64, "vrct-ocr-gl", None, None)
        if self._gl_window is None:
            glfw.terminate()
            printLog("OCR: failed to create hidden GLFW window")
            return False
        glfw.make_context_current(self._gl_window)
        return True

    def _init(self) -> bool:
        if self._initialized:
            return True
        if not self.isAvailable():
            return False
        try:
            if not self._initGlContext():
                return False

            # Join (or create) the process-wide OpenVR session. Background
            # mode so we never steal focus from the running scene app.
            openvr_session.acquire(openvr.VRApplication_Background)
            self._session_held = True
            self._compositor = openvr.IVRCompositor()

            # Acquire the mirror texture exactly once.
            tex = self._compositor.getMirrorTextureGL(self._eye)
            if not isinstance(tex, (tuple, list)) or len(tex) < 2:
                printLog("OCR: unexpected getMirrorTextureGL return shape")
                self._resetVrState()
                return False
            self._texture_id = int(tex[0])
            self._shared_handle = tex[1]
            if not self._texture_id:
                printLog("OCR: compositor returned an empty mirror texture")
                self._texture_id = None
                self._resetVrState()
                return False

            self._initialized = True
            return True
        except Exception:
            errorLogging()
            self._resetVrState()
            return False

    def _resetVrState(self) -> None:
        """Release the mirror texture and our session reference, but keep
        the GL context so a retry is cheap. Releasing (rather than holding
        a possibly dead session) lets the next _init() reconnect, the same
        release-then-acquire order Overlay.reStartOverlay() uses."""
        try:
            if (
                self._compositor is not None
                and self._texture_id is not None
                and hasattr(self._compositor, "releaseSharedGLTexture")
            ):
                self._compositor.releaseSharedGLTexture(self._texture_id, self._shared_handle)
        except Exception:
            pass
        self._texture_id = None
        self._shared_handle = None
        self._compositor = None
        self._initialized = False
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

    def _lock(self) -> None:
        if self._shared_handle is None:
            return
        if hasattr(self._compositor, "lockGLSharedTextureForAccess"):
            self._compositor.lockGLSharedTextureForAccess(self._shared_handle)

    def _unlock(self) -> None:
        if self._shared_handle is None:
            return
        if hasattr(self._compositor, "unlockGLSharedTextureForAccess"):
            self._compositor.unlockGLSharedTextureForAccess(self._shared_handle)

    def capture(self) -> Optional[np.ndarray]:
        if not self._init():
            return None

        try:
            if not self._isVrchatScene():
                return None
        except Exception:
            errorLogging()
            self._resetVrState()
            return None

        locked = False
        try:
            glfw.make_context_current(self._gl_window)
            self._lock()
            locked = True

            GL.glBindTexture(GL.GL_TEXTURE_2D, self._texture_id)
            width = GL.glGetTexLevelParameteriv(GL.GL_TEXTURE_2D, 0, GL.GL_TEXTURE_WIDTH)
            height = GL.glGetTexLevelParameteriv(GL.GL_TEXTURE_2D, 0, GL.GL_TEXTURE_HEIGHT)
            if not width or not height:
                GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
                return None

            buf = (GL.GLubyte * (int(width) * int(height) * 4))()
            GL.glGetTexImage(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, buf)
            GL.glBindTexture(GL.GL_TEXTURE_2D, 0)

            arr = np.frombuffer(buf, dtype=np.uint8).reshape((int(height), int(width), 4))
            # OpenGL textures are bottom-up; flip so top-of-image is row 0.
            # Convert RGBA -> BGR to match the HWND path (OpenCV convention).
            arr = np.flipud(arr)[:, :, [2, 1, 0]]
            return np.ascontiguousarray(arr)
        except Exception:
            errorLogging()
            # The compositor session may have been torn down (SteamVR restart,
            # overlay shutdown). Drop the texture so the next tick re-acquires.
            if locked:
                try:
                    self._unlock()
                except Exception:
                    pass
                locked = False
            self._resetVrState()
            return None
        finally:
            if locked:
                try:
                    self._unlock()
                except Exception:
                    pass

    def close(self) -> None:
        """Release OCR-owned resources and our shared-session reference.

        The real openvr.shutdown() only runs once Overlay/Clipboard have
        released theirs too (models/openvr_session.py).
        """
        self._resetVrState()
        if self._gl_window is not None and glfw is not None:
            try:
                glfw.destroy_window(self._gl_window)
                glfw.terminate()
            except Exception:
                pass
            self._gl_window = None
