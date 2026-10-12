"""VRCT_RUST_OVERLAY=1: the Rust overlay (native/vrct-overlay) in place of overlay.Overlay, to check it in VR.

Model と Controller が使う Overlay の呼び方 (メソッド・属性・コールバック) をそのまま受け、Rust の vrct_overlay.Overlay へ渡す。
SteamVR との接続は Rust が pyopenvr と同じ DLL で持つ (openvr_session もそれを通す)。
"""

import os
from functools import lru_cache
from importlib import import_module
from pathlib import Path

try:
    from utils import printLog
except ImportError:
    def printLog(log, data=None):
        print(log, data)


@lru_cache(maxsize=1)
def native_overlay():
    """vrct_overlay when VRCT_RUST_OVERLAY=1 (pyopenvr's DLL set before any use), else None."""
    if os.environ.get("VRCT_RUST_OVERLAY") != "1":
        return None
    import openvr

    native = import_module("vrct_overlay")
    native.use_openvr_dll(str(Path(openvr.__file__).with_name("libopenvr_api_64.dll")))
    return native


class _SizeSettings(dict):
    """settings[size]: a copy of what the overlay published; the opacity written goes to the overlay."""

    def __init__(self, owner, size, values):
        super().__init__(values)
        self._owner, self._size = owner, size

    def __setitem__(self, key, value):
        if key != "opacity":
            raise KeyError(f"RustOverlay: settings[{self._size!r}][{key!r}] は書き換えられません")
        super().__setitem__(key, value)
        self._owner.updateOpacity(value, self._size)


class RustOverlay:
    """overlay.Overlay と同じ呼び方の、Rust のオーバーレイ。"""

    _CALLBACKS = {"layout_callback": "layout", "pointer_callback": "pointer", "position_changed_callback": "position",
                  "panel_out_of_view_callback": "out_of_view", "launcher_intro_callback": "intro"}

    def __init__(self, settings_dict):
        self._native = native_overlay().Overlay(settings_dict, lambda line: printLog(line))

    def __setattr__(self, name, value):
        if name in self._CALLBACKS:
            self._native.set_callback(self._CALLBACKS[name], value)
        elif name == "launcher_defaults":
            self._native.set_launcher_defaults(value)
        elif name == "panel_locked":
            self._native.set_panel_locked(bool(value))
        elif name == "launcher_auto_hide":
            self._native.set_launcher_auto_hide(bool(value))
        else:
            super().__setattr__(name, value)

    @property
    def initialized(self) -> bool:
        return self._native.initialized

    @property
    def launcher_intro_state(self) -> str:
        return self._native.launcher_intro_state

    @property
    def settings(self) -> dict:
        return {size: _SizeSettings(self, size, values) for size, values in self._native.settings().items()}

    def getVrLayout(self) -> dict:
        return self._native.vr_layout()

    def updateImage(self, img, size: str) -> None:
        img = img.convert("RGBA")
        self._native.update_image(size, img.size[0], img.size[1], img.tobytes())

    def clearImage(self, size: str) -> None:
        self._native.clear_image(size)

    def updateOpacity(self, opacity: float, size: str, with_fade: bool = False) -> None:
        self._native.update_opacity(size, float(opacity), bool(with_fade))

    def updateUiScaling(self, ui_scaling: float, size: str) -> None:
        self._native.update_ui_scaling(size, float(ui_scaling))

    def updatePosition(self, x_pos, y_pos, z_pos, x_rotation, y_rotation, z_rotation, tracker: str, size: str) -> None:
        position = [float(v) for v in (x_pos, y_pos, z_pos, x_rotation, y_rotation, z_rotation)]
        self._native.update_position(size, position, tracker)

    def updateDisplayDuration(self, display_duration: float, size: str) -> None:
        self._native.update_display_duration(size, float(display_duration))

    def updateFadeoutDuration(self, fadeout_duration: float, size: str) -> None:
        self._native.update_fadeout_duration(size, float(fadeout_duration))

    def setVrWindows(self, log: bool, popup: bool) -> None:
        self._native.set_vr_windows(bool(log), bool(popup))

    def setVrPanelEnabled(self, enabled: bool) -> None:
        self._native.set_vr_panel_enabled(bool(enabled))

    def requestLauncherReset(self, keep_hand: bool = False) -> None:
        self._native.reset_launcher(bool(keep_hand))

    def requestAnchor(self, anchor: str) -> None:
        self._native.request_anchor(anchor)

    def requestRecallPanel(self) -> None:
        self._native.recall_panel()

    def setTooltip(self, data: dict) -> None:
        self._native.set_tooltip(data)

    def setLayoutRendered(self, panel_size) -> None:
        self._native.set_layout_rendered(tuple(panel_size))

    def startOverlay(self) -> None:
        self._native.start()

    def shutdownOverlay(self) -> None:
        self._native.stop()

    def reStartOverlay(self) -> None:
        self.shutdownOverlay()
        self.startOverlay()
