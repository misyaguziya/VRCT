import os
import ctypes
import time
from psutil import process_iter
from threading import Thread
import openvr
import numpy as np
from PIL import Image
try:
    from . import overlay_utils as utils
except ImportError:
    import overlay_utils as utils

def mat34Id(array):
    arr = openvr.HmdMatrix34_t()
    for i in range(3):
        for j in range(4):
            arr[i][j] = array[i][j]
    return arr

def getBaseMatrix(x_pos, y_pos, z_pos, x_rotation, y_rotation, z_rotation):
    arr = np.zeros((3, 4))
    rot = utils.euler_to_rotation_matrix((x_rotation, y_rotation, z_rotation))

    for i in range(3):
        for j in range(3):
            arr[i][j] = rot[i][j]

    arr[0][3] = x_pos * z_pos
    arr[1][3] = y_pos * z_pos
    arr[2][3] = - z_pos
    return arr

def getHMDBaseMatrix():
    x_pos = 0.0
    y_pos = -0.4
    z_pos = 1.0
    x_rotation = 0.0
    y_rotation = 0.0
    z_rotation = 0.0
    arr = getBaseMatrix(x_pos, y_pos, z_pos, x_rotation, y_rotation, z_rotation)
    return arr

def getLeftHandBaseMatrix():
    x_pos = 0.0
    y_pos = -0.06
    z_pos = -0.14
    x_rotation = -62.0
    y_rotation = 154.0
    z_rotation = 71.0
    arr = getBaseMatrix(x_pos, y_pos, z_pos, x_rotation, y_rotation, z_rotation)
    return arr

def getRightHandBaseMatrix():
    x_pos = 0.0
    y_pos = -0.06
    z_pos = -0.14
    x_rotation = -62.0
    y_rotation = -154.0
    z_rotation = -71.0
    arr = getBaseMatrix(x_pos, y_pos, z_pos, x_rotation, y_rotation, z_rotation)
    return arr

class Overlay:
    def __init__(self, x_pos, y_pos, z_pos, x_rotation, y_rotation, z_rotation, display_duration, fadeout_duration, opacity, ui_scaling):
        self.initialized = False
        settings = {
            "color": [1, 1, 1],
            "opacity": opacity,
            "x_pos": x_pos,
            "y_pos": y_pos,
            "z_pos": z_pos,
            "x_rotation": x_rotation,
            "y_rotation": y_rotation,
            "z_rotation": z_rotation,
            "display_duration": display_duration,
            "fadeout_duration": fadeout_duration,
            "ui_scaling": ui_scaling,
        }
        self.settings = settings
        self.system = None
        self.overlay = None
        self.handle = None
        self.lastUpdate = time.monotonic()
        self.thread_overlay = None
        self.fadeRatio = 1
        self.loop = True

    def init(self):
        try:
            self.system = openvr.init(openvr.VRApplication_Background)
            self.overlay = openvr.IVROverlay()
            self.overlay_system = openvr.IVRSystem()
            self.handle = self.overlay.createOverlay("Overlay_Speaker2log", "SOverlay_Speaker2log_UI")
            self.overlay.showOverlay(self.handle)
            self.initialized = True

            self.updateImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))
            self.updateColor(self.settings["color"])
            self.updateOpacity(self.settings["opacity"])
            self.updateUiScaling(self.settings["ui_scaling"])
            self.updatePosition(
                self.settings["x_pos"],
                self.settings["y_pos"],
                self.settings["z_pos"],
                self.settings["x_rotation"],
                self.settings["y_rotation"],
                self.settings["z_rotation"],
            )

        except Exception as e:
            print("Could not initialise OpenVR", e)

    def updateImage(self, img):
        if self.initialized is True:
            width, height = img.size
            img = img.tobytes()
            img = (ctypes.c_char * len(img)).from_buffer_copy(img)
            self.overlay.setOverlayRaw(self.handle, img, width, height, 4)
            self.updateOpacity(self.settings["opacity"])
            self.lastUpdate = time.monotonic()

    def clearImage(self):
        if self.initialized is True:
            self.updateImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))

    def updateColor(self, col):
        """
        col is a 3-tuple representing (r, g, b)
        """
        self.settings["color"] = col
        if self.initialized is True:
            r, g, b = self.settings["color"]
            self.overlay.setOverlayColor(self.handle, r, g, b)

    def updateOpacity(self, opacity, with_fade=False):
        self.settings["opacity"] = opacity

        if self.initialized is True:
            if with_fade is True:
                if self.fadeRatio > 0:
                    self.overlay.setOverlayAlpha(self.handle, self.fadeRatio * self.settings["opacity"])
            else:
                self.overlay.setOverlayAlpha(self.handle, self.settings["opacity"])

    def updateUiScaling(self, ui_scaling):
        self.settings["ui_scaling"] = ui_scaling
        if self.initialized is True:
            self.overlay.setOverlayWidthInMeters(self.handle, self.settings["ui_scaling"])

    def updatePosition(self, x_pos, y_pos, z_pos, x_rotation, y_rotation, z_rotation, tracker="HMD"):
        """
        x_pos, y_pos, z_pos are floats representing the position of overlay
        x_rotation, y_rotation, z_rotation are floats representing the rotation of overlay
        tracker is a string representing the tracker to use ("HMD", "LeftHand", "RightHand")
        """

        self.settings["x_pos"] = x_pos
        self.settings["y_pos"] = y_pos
        self.settings["z_pos"] = z_pos
        self.settings["x_rotation"] = x_rotation
        self.settings["y_rotation"] = y_rotation
        self.settings["z_rotation"] = z_rotation

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

        translation = (self.settings["x_pos"], self.settings["y_pos"], - self.settings["z_pos"])
        rotation = (self.settings["x_rotation"], self.settings["y_rotation"], self.settings["z_rotation"])
        transform = utils.transform_matrix(base_matrix, translation, rotation)
        self.transform = mat34Id(transform)

        if self.initialized is True:
            self.overlay.setOverlayTransformTrackedDeviceRelative(
                self.handle,
                trackerIndex,
                self.transform
            )

    def updateDisplayDuration(self, display_duration):
        self.settings["display_duration"] = display_duration

    def updateFadeoutDuration(self, fadeout_duration):
        self.settings["fadeout_duration"] = fadeout_duration

    def checkActive(self):
        try:
            if self.system is not None and self.initialized is True:
                new_event = openvr.VREvent_t()
                while self.system.pollNextEvent(new_event):
                    if new_event.eventType == openvr.VREvent_Quit:
                        return False
            return True
        except Exception as e:
            print("Could not check SteamVR running")
            print(e)
            return False

    def evaluateOpacityFade(self, lastUpdate, currentTime):
        if (currentTime - lastUpdate) > self.settings["display_duration"]:
            timeThroughInterval = currentTime - lastUpdate - self.settings["display_duration"]
            self.fadeRatio = 1 - timeThroughInterval / self.settings["fadeout_duration"]
            if self.fadeRatio < 0:
                self.fadeRatio = 0
            self.overlay.setOverlayAlpha(self.handle, self.fadeRatio * self.settings["opacity"])

    def update(self):
        currTime = time.monotonic()
        if self.settings["fadeout_duration"] != 0:
            self.evaluateOpacityFade(self.lastUpdate, currTime)
        else:
            self.updateOpacity(self.settings["opacity"])

    def mainloop(self):
        self.loop = True
        while self.checkActive() is True and self.loop is True:
            startTime = time.monotonic()
            self.update()
            sleepTime = (1 / 16) - (time.monotonic() - startTime)
            if sleepTime > 0:
                time.sleep(sleepTime)

    def main(self):
        self.init()
        if self.initialized is True:
            self.mainloop()

    def startOverlay(self):
        self.thread_overlay = Thread(target=self.main)
        self.thread_overlay.daemon = True
        self.thread_overlay.start()

    def shutdownOverlay(self):
        if isinstance(self.thread_overlay, Thread):
            self.loop = False
            self.thread_overlay.join()
            self.thread_overlay = None
        if isinstance(self.overlay, openvr.IVROverlay) and isinstance(self.handle, int):
            self.overlay.destroyOverlay(self.handle)
            self.overlay = None
        if isinstance(self.system, openvr.IVRSystem):
            openvr.shutdown()
            self.system = None
        self.initialized = False

    @staticmethod
    def checkSteamvrRunning() -> bool:
        _proc_name = "vrmonitor.exe" if os.name == "nt" else "vrmonitor"
        return _proc_name in (p.name() for p in process_iter())

if __name__ == "__main__":
    # from overlay_image import OverlayImage
    # overlay_image = OverlayImage()

    # overlay = Overlay(0, 0, 1, 1, 0, 1, 1)
    # overlay.startOverlay()
    # time.sleep(1)

    # # Example usage
    # img = overlay_image.createOverlayImageShort("こんにちは、世界！さようなら", "Japanese", "Hello,World!Goodbye", "Japanese")
    # overlay.updateImage(img)
    # time.sleep(100000)
    
    # for i in range(100):
    #     print(i)
    #     overlay = Overlay(0, 0, 1, 1, 1, 1, 1)
    #     overlay.startOverlay()
    #     time.sleep(1)

    #     # Example usage
    #     img = overlay_image.createOverlayImageShort("こんにちは、世界！さようなら", "Japanese", "Hello,World!Goodbye", "Japanese", ui_type="sakura")
    #     overlay.updateImage(img)
    #     time.sleep(0.5)

    #     img = overlay_image.createOverlayImageShort("こんにちは、世界！さようなら", "Japanese", "Hello,World!Goodbye", "Japanese")
    #    overlay.updateImage(img)
    #    time.sleep(0.5)

    #    overlay.shutdownOverlay()

    x_pos = 0
    y_pos = 0
    z_pos = 0
    x_rotation = 0
    y_rotation = 0
    z_rotation = 0

    base_matrix = getLeftHandBaseMatrix()
    translation = (x_pos * z_pos, y_pos * z_pos, z_pos)
    rotation = (x_rotation, y_rotation, z_rotation)
    transform = utils.transform_matrix(base_matrix, translation, rotation)
    transform = mat34Id(transform)
    print(transform)