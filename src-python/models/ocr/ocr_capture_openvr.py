"""OpenVR compositor mirror-texture capture.

Grabs the HMD left-eye submitted image so OCR still works when the
VRChat desktop mirror window is minimized (a common VR-mode setup).

Uses IVRCompositor::GetMirrorTextureGL + PyOpenGL to read pixels back
into a numpy array. Requires an active OpenGL context, which we create
via GLFW (offscreen) on first use.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

try:
    import openvr
except Exception:  # pragma: no cover
    openvr = None  # type: ignore

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

    The class lazily initializes OpenVR + a hidden GLFW window (for the
    GL context) on first capture. All resources are released in close().
    A capture() failure never raises: it just returns None.
    """

    def __init__(self, eye: str = "left") -> None:
        self._eye = openvr.Eye_Left if (openvr is not None and eye == "left") else (
            openvr.Eye_Right if openvr is not None else 0
        )
        self._compositor = None
        self._system = None
        self._gl_window = None
        self._gl_texture_id: Optional[int] = None
        self._gl_texture_size = (0, 0)
        self._initialized = False

    def isAvailable(self) -> bool:
        return openvr is not None and GL is not None and glfw is not None

    def _init(self) -> bool:
        if self._initialized:
            return True
        if not self.isAvailable():
            return False
        try:
            # Small hidden GLFW window provides the required GL context.
            if not glfw.init():
                return False
            glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
            self._gl_window = glfw.create_window(64, 64, "vrct-ocr-gl", None, None)
            if self._gl_window is None:
                glfw.terminate()
                return False
            glfw.make_context_current(self._gl_window)

            # Prefer VRApplication_Background so we do not disturb the
            # currently running scene application.
            self._system = openvr.init(openvr.VRApplication_Background)
            self._compositor = openvr.IVRCompositor()
            self._initialized = True
            return True
        except Exception:
            errorLogging()
            self.close()
            return False

    def _fetchTexture(self) -> Optional[int]:
        """Return the OpenGL texture ID of the compositor mirror."""
        try:
            # Newer openvr Python bindings expose getMirrorTextureGL
            # returning (glTextureId, glSharedTextureHandle).
            tex_id, _shared = self._compositor.getMirrorTextureGL(self._eye)
            return int(tex_id)
        except Exception:
            errorLogging()
            return None

    def capture(self) -> Optional[np.ndarray]:
        if not self._init():
            return None
        try:
            glfw.make_context_current(self._gl_window)
            tex_id = self._fetchTexture()
            if tex_id is None or tex_id == 0:
                return None

            GL.glBindTexture(GL.GL_TEXTURE_2D, tex_id)
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
            arr = np.flipud(arr)
            # Convert RGBA -> BGR to match the HWND path (OpenCV convention).
            arr = arr[:, :, [2, 1, 0]]
            return np.ascontiguousarray(arr)
        except Exception:
            errorLogging()
            return None

    def close(self) -> None:
        try:
            if self._compositor is not None:
                try:
                    self._compositor.releaseSharedGLTexture(self._eye) if hasattr(
                        self._compositor, "releaseSharedGLTexture"
                    ) else None
                except Exception:
                    pass
                try:
                    self._compositor.releaseMirrorTextureGL(self._eye) if hasattr(
                        self._compositor, "releaseMirrorTextureGL"
                    ) else None
                except Exception:
                    pass
                self._compositor = None
            if self._system is not None:
                try:
                    openvr.shutdown()
                except Exception:
                    pass
                self._system = None
            if self._gl_window is not None and glfw is not None:
                try:
                    glfw.destroy_window(self._gl_window)
                    glfw.terminate()
                except Exception:
                    pass
                self._gl_window = None
        finally:
            self._initialized = False
