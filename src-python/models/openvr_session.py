"""Process-wide, reference-counted OpenVR session.

openvr.shutdown() (VR_Shutdown) tears down the SteamVR client connection
for the *entire process*, not just the caller's own handles. VRCT has two
independent OpenVR users -- Clipboard (one-shot VR app-name lookup) and
Overlay (persistent 16fps overlay loop) -- that used to call
openvr.init()/openvr.shutdown() directly and independently. If Clipboard's
shutdown ran while Overlay's system/overlay handles were still in use, it
silently invalidated them even though Overlay.initialized stayed True, and
Overlay's retry path could then spin in an unbounded busy-wait
(see overlay.py: updateImage -> reStartOverlay).

Every openvr.init()/openvr.shutdown() call in the process should go
through acquire()/release() here instead of calling openvr directly, so
the real VR_Shutdown() only happens once nobody is still holding a
reference.
"""

import threading
from typing import Any, Optional

import openvr

_lock = threading.Lock()
_ref_count = 0
_system: Optional[Any] = None


def acquire(application_type: int = openvr.VRApplication_Background) -> Any:
    """Acquire a reference to the shared OpenVR session.

    Calls openvr.init() only for the first caller; later, concurrent
    callers reuse the same system handle and just bump the reference
    count. Every successful acquire() must be paired with exactly one
    release() (use try/finally at the call site).

    Raises whatever openvr.init() raises if the first acquire fails; the
    reference count is left unchanged in that case (nothing to release).
    """
    global _ref_count, _system
    with _lock:
        if _ref_count == 0:
            _system = openvr.init(application_type)
        _ref_count += 1
        return _system


def release() -> None:
    """Release a reference taken with acquire().

    Only calls openvr.shutdown() once the last outstanding reference is
    released. Calling this without a matching acquire() is a no-op
    (defensive against double-release bugs, not something to rely on).
    """
    global _ref_count, _system
    with _lock:
        if _ref_count <= 0:
            return
        _ref_count -= 1
        if _ref_count == 0:
            openvr.shutdown()
            _system = None


def is_active() -> bool:
    """True if at least one caller currently holds a reference."""
    with _lock:
        return _ref_count > 0
