import os
import ctypes
import time
from psutil import process_iter
from threading import Thread
from typing import Any, Dict, Optional, Sequence

import openvr
import numpy as np
from PIL import Image
try:
    from utils import errorLogging
except ImportError:
    def errorLogging():
        import traceback
        print(traceback.format_exc())

try:
    from . import overlay_utils as utils
except ImportError:
    import overlay_utils as utils

def mat34Id(array: Sequence[Sequence[float]]) -> Any:
    """Convert a 3x4 nested sequence into an openvr.HmdMatrix34_t instance.

    Args:
        array: 3x4 numeric sequence

    Returns:
        openvr HmdMatrix34_t compatible object
    """
    arr = openvr.HmdMatrix34_t()
    for i in range(3):
        for j in range(4):
            arr[i][j] = array[i][j]
    return arr

def getBaseMatrix(x_pos: float, y_pos: float, z_pos: float, x_rotation: float, y_rotation: float, z_rotation: float) -> np.ndarray:
    """Create a 3x4 base matrix for an overlay given position and Euler rotations.

    Returns a numpy array of shape (3,4).
    """
    arr = np.zeros((3, 4))
    rot = utils.euler_to_rotation_matrix((x_rotation, y_rotation, z_rotation))

    for i in range(3):
        for j in range(3):
            arr[i][j] = rot[i][j]

    arr[0][3] = x_pos * z_pos
    arr[1][3] = y_pos * z_pos
    arr[2][3] = - z_pos
    return arr

def getHMDBaseMatrix() -> np.ndarray:
    x_pos = 0.0
    y_pos = -0.4
    z_pos = 1.0
    x_rotation = 0.0
    y_rotation = 0.0
    z_rotation = 0.0
    arr = getBaseMatrix(x_pos, y_pos, z_pos, x_rotation, y_rotation, z_rotation)
    return arr

def getLeftHandBaseMatrix() -> np.ndarray:
    x_pos = 0.3
    y_pos = 0.1
    z_pos = -0.31
    x_rotation = -65.0
    y_rotation = 165.0
    z_rotation = 115.0
    arr = getBaseMatrix(x_pos, y_pos, z_pos, x_rotation, y_rotation, z_rotation)
    return arr

def getRightHandBaseMatrix() -> np.ndarray:
    x_pos = -0.3
    y_pos = 0.1
    z_pos = -0.31
    x_rotation = -65.0
    y_rotation = -165.0
    z_rotation = -115.0
    arr = getBaseMatrix(x_pos, y_pos, z_pos, x_rotation, y_rotation, z_rotation)
    return arr

class Overlay:
    """Manage OpenVR overlays for multiple sizes (e.g. 'small'/'large')."""
    def __init__(self, settings_dict: Dict[str, Dict[str, Any]]) -> None:
        self.system: Optional[Any] = None
        self.overlay: Optional[Any] = None
        self.handle: Dict[str, Any] = {}
        self.init_process: bool = False
        self.initialized: bool = False
        self.loop: bool = False
        self.thread_overlay: Optional[Thread] = None

        self.settings: Dict[str, Dict[str, Any]] = {}
        self.lastUpdate: Dict[str, float] = {}
        self.fadeRatio: Dict[str, float] = {}
        for key, value in settings_dict.items():
            self.settings[key] = value
            self.lastUpdate[key] = time.monotonic()
            self.fadeRatio[key] = 1.0

    def init(self) -> None:
        try:
            self.system = openvr.init(openvr.VRApplication_Background)
            self.overlay = openvr.IVROverlay()
            self.overlay_system = openvr.IVRSystem()
            self.handle = {}
            for i, size in enumerate(self.settings.keys()):
                self.handle[size] = self.overlay.createOverlay(f"VRCT{i}", f"VRCT{i}")
                self.overlay.showOverlay(self.handle[size])
            self.initialized = True

            for size in self.settings.keys():
                self.updateImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0)), size)
                self.updateColor([1, 1, 1], size)
                self.updateOpacity(self.settings[size]["opacity"], size)
                self.updateUiScaling(self.settings[size]["ui_scaling"], size)
                self.updatePosition(
                    self.settings[size]["x_pos"],
                    self.settings[size]["y_pos"],
                    self.settings[size]["z_pos"],
                    self.settings[size]["x_rotation"],
                    self.settings[size]["y_rotation"],
                    self.settings[size]["z_rotation"],
                    self.settings[size]["tracker"],
                    size
                )
                self.updateDisplayDuration(self.settings[size]["display_duration"], size)
                self.updateFadeoutDuration(self.settings[size]["fadeout_duration"], size)
            self.init_process = False

        except Exception:
            errorLogging()

    def updateImage(self, img: Image.Image, size: str) -> None:
        if self.initialized is True:
            width, height = img.size
            img = img.tobytes()
            img = (ctypes.c_char * len(img)).from_buffer_copy(img)

            try:
                self.overlay.setOverlayRaw(self.handle[size], img, width, height, 4)
            except Exception:
                self.reStartOverlay()
                while self.initialized is False:
                    time.sleep(0.1)
                try:
                    self.overlay.setOverlayRaw(self.handle[size], img, width, height, 4)
                except Exception:
                    errorLogging()

            self.updateOpacity(self.settings[size]["opacity"], size)
            self.lastUpdate[size] = time.monotonic()

    def clearImage(self, size: str) -> None:
        if self.initialized is True:
            self.updateImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0)), size)

    def updateColor(self, col, size):
        """
        col is a 3-tuple representing (r, g, b)
        """
        if self.initialized is True:
            r, g, b = col
            self.overlay.setOverlayColor(self.handle[size], r, g, b)

    def updateOpacity(self, opacity: float, size: str, with_fade: bool = False) -> None:
        self.settings[size]["opacity"] = opacity

        if self.initialized is True:
            if with_fade is True:
                if self.fadeRatio[size] > 0:
                    self.overlay.setOverlayAlpha(self.handle[size], self.fadeRatio[size] * self.settings[size]["opacity"])
            else:
                self.overlay.setOverlayAlpha(self.handle[size], self.settings[size]["opacity"])

    def updateUiScaling(self, ui_scaling: float, size: str) -> None:
        self.settings[size]["ui_scaling"] = ui_scaling
        if self.initialized is True:
            self.overlay.setOverlayWidthInMeters(self.handle[size], self.settings[size]["ui_scaling"])

    def updatePosition(self, x_pos: float, y_pos: float, z_pos: float, x_rotation: float, y_rotation: float, z_rotation: float, tracker: str, size: str) -> None:
        """
        x_pos, y_pos, z_pos are floats representing the position of overlay
        x_rotation, y_rotation, z_rotation are floats representing the rotation of overlay
        tracker is a string representing the tracker to use ("HMD", "LeftHand", "RightHand")
        """

        self.settings[size]["x_pos"] = x_pos
        self.settings[size]["y_pos"] = y_pos
        self.settings[size]["z_pos"] = z_pos
        self.settings[size]["x_rotation"] = x_rotation
        self.settings[size]["y_rotation"] = y_rotation
        self.settings[size]["z_rotation"] = z_rotation
        self.settings[size]["tracker"] = tracker

        if self.initialized is True:
            match tracker:
                case "HMD":
                    base_matrix = getHMDBaseMatrix()
                    trackerIndex = openvr.k_unTrackedDeviceIndex_Hmd
                case "LeftHand":
                    base_matrix = getLeftHandBaseMatrix()
                    trackerIndex = self.overlay_system.getTrackedDeviceIndexForControllerRole(openvr.TrackedControllerRole_LeftHand)
                case "RightHand":
                    base_matrix = getRightHandBaseMatrix()
                    trackerIndex = self.overlay_system.getTrackedDeviceIndexForControllerRole(openvr.TrackedControllerRole_RightHand)
                case _:
                    base_matrix = getHMDBaseMatrix()
                    trackerIndex = openvr.k_unTrackedDeviceIndex_Hmd

            translation = (self.settings[size]["x_pos"], self.settings[size]["y_pos"], - self.settings[size]["z_pos"])
            rotation = (self.settings[size]["x_rotation"], self.settings[size]["y_rotation"], self.settings[size]["z_rotation"])
            transform = utils.transform_matrix(base_matrix, translation, rotation)
            transform = mat34Id(transform)

            if bool(self.overlay_system.isTrackedDeviceConnected(trackerIndex)) is True:
                self.overlay.setOverlayTransformTrackedDeviceRelative(
                    self.handle[size],
                    trackerIndex,
                    transform
                )

    def updateDisplayDuration(self, display_duration: float, size: str) -> None:
        self.settings[size]["display_duration"] = display_duration

    def updateFadeoutDuration(self, fadeout_duration: float, size: str) -> None:
        self.settings[size]["fadeout_duration"] = fadeout_duration

    def checkActive(self) -> bool:
        try:
            if self.system is not None and self.initialized is True:
                new_event = openvr.VREvent_t()
                while self.system.pollNextEvent(new_event):
                    if new_event.eventType == openvr.VREvent_Quit:
                        return False
            return True
        except Exception:
            errorLogging()
            return False

    def evaluateOpacityFade(self, size: str) -> None:
        currentTime = time.monotonic()
        if (currentTime - self.lastUpdate[size]) > self.settings[size]["display_duration"]:
            timeThroughInterval = currentTime - self.lastUpdate[size] - self.settings[size]["display_duration"]
            self.fadeRatio[size] = 1 - timeThroughInterval / self.settings[size]["fadeout_duration"]
            if self.fadeRatio[size] < 0:
                self.fadeRatio[size] = 0
            self.overlay.setOverlayAlpha(self.handle[size], self.fadeRatio[size] * self.settings[size]["opacity"])

    def update(self, size: str) -> None:
        if self.settings[size]["fadeout_duration"] != 0:
            self.evaluateOpacityFade(size)
        else:
            self.updateOpacity(self.settings[size]["opacity"], size)

    def mainloop(self) -> None:
        self.loop = True
        while self.checkActive() is True and self.loop is True:
            startTime = time.monotonic()
            for size in self.settings.keys():
                self.update(size)
            sleepTime = (1 / 16) - (time.monotonic() - startTime)
            if sleepTime > 0:
                time.sleep(sleepTime)

    def main(self) -> None:
        while self.checkSteamvrRunning() is False:
            time.sleep(10)
        self.init()
        if self.initialized is True:
            self.mainloop()

    def startOverlay(self) -> None:
        if self.initialized is False and self.init_process is False:
            self.init_process = True
            self.thread_overlay = Thread(target=self.main)
            self.thread_overlay.daemon = True
            self.thread_overlay.start()

    def shutdownOverlay(self) -> None:
        if self.initialized is True and self.init_process is False:
            if isinstance(self.thread_overlay, Thread):
                self.loop = False
                self.thread_overlay.join()
                self.thread_overlay = None
            if isinstance(self.overlay, openvr.IVROverlay):
                for size in self.settings.keys():
                    if isinstance(self.handle[size], int):
                        self.overlay.destroyOverlay(self.handle[size])
                self.overlay = None
            if isinstance(self.system, openvr.IVRSystem):
                openvr.shutdown()
                self.system = None
            self.initialized = False

    def reStartOverlay(self) -> None:
        self.shutdownOverlay()
        self.startOverlay()

    @staticmethod
    def checkSteamvrRunning() -> bool:
        _proc_name = "vrmonitor.exe" if os.name == "nt" else "vrmonitor"
        return _proc_name in (p.name() for p in process_iter())

if __name__ == "__main__":
    from overlay_image import OverlayImage
    import logging

    logging.basicConfig(level=logging.DEBUG)

    small_settings = {
        "x_pos": 0.0,
        "y_pos": 0.0,
        "z_pos": 0.0,
        "x_rotation": 0.0,
        "y_rotation": 0.0,
        "z_rotation": 0.0,
        "display_duration": 5,
        "fadeout_duration": 2,
        "opacity": 1.0,
        "ui_scaling": 1.0,
        "tracker": "HMD",
    }

    large_settings = {
        "x_pos": 0.0,
        "y_pos": 0.0,
        "z_pos": 0.0,
        "x_rotation": 0.0,
        "y_rotation": 0.0,
        "z_rotation": 0.0,
        "display_duration": 5,
        "fadeout_duration": 2,
        "opacity": 1.0,
        "ui_scaling": 0.25,
        "tracker": "LeftHand",
    }

    settings_dict = {
        "small": small_settings,
        "large": large_settings
    }

    # オーバーレイの初期化設定を確認
    logging.debug(f"Settings Dict: {settings_dict}")

    overlay_image = OverlayImage()
    overlay = Overlay(settings_dict)
    overlay.startOverlay()

    while overlay.initialized is False:
        time.sleep(1)

    # Example usage
    for i in range(1000):
        try:
            print(i)
            img = overlay_image.createOverlayImageLargeLog("send", f"こんにちは、世界！さようなら {i}", "Japanese", "Hello,World!Goodbye", "Japanese")
            logging.debug(f"Generated Image: {img}")
            overlay.updateImage(img, "large")
            img = overlay_image.createOverlayImageSmallLog(f"こんにちは、世界！さようなら_{i}", "Japanese", "Hello,World!Goodbye", "Japanese")
            overlay.updateImage(img, "small")
            time.sleep(1)
        except openvr.error_code.OverlayError_InvalidParameter as e:
            errorLogging()
            logging.error(f"OverlayError_InvalidParameter: {e}")
            break
        except Exception as e:
            errorLogging()
            logging.error(f"Unexpected error: {e}")
            break

    # for i in range(100):
    #     print(i)
    #     # Example usage
    #     img = overlay_image.createOverlayImageSmallLog(f"こんにちは、世界！さようなら_{i}", "Japanese", "Hello,World!Goodbye", "Japanese")
    #     overlay.updateImage(img, "small")
    #     time.sleep(5)

    #     if i%2 == 0:
    #         overlay.updatePosition(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "HMD", "small")
    #     else:
    #         overlay.updatePosition(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "RightHand", "small")

    overlay.shutdownOverlay()