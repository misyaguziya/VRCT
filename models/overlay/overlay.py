import os
import ctypes
from psutil import process_iter
# from os import path as os_path
import ctypes
import time
import openvr
from PIL import Image
# from queue import Queue
from threading import Thread

def mat34Id():
    arr = openvr.HmdMatrix34_t()
    arr[0][0] = 1
    arr[1][1] = 1
    arr[2][2] = 1
    return arr

class Overlay:
    def __init__(self, x, y , depth, display_duration, fadeout_duration, opacity, ui_scaling):
        self.initialized = False
        settings = {
            "color": [1, 1, 1],
            "opacity": opacity,
            "x_pos": x,
            "y_pos": y,
            "depth": depth,
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
            self.handle = self.overlay.createOverlay("Overlay_Speaker2log", "SOverlay_Speaker2log_UI")

            self.updateImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))
            self.updateColor(self.settings["color"])
            self.updateOpacity(self.settings["opacity"])
            self.updateUiScaling(self.settings["ui_scaling"])
            self.updatePosition(
                (self.settings["x_pos"], self.settings["y_pos"]),
                self.settings["depth"]
            )
            self.overlay.showOverlay(self.handle)
            self.initialized = True
        except Exception as e:
            print("Could not initialise OpenVR", e)

    def updateImage(self, img):
        width, height = img.size
        img = img.tobytes()
        img = (ctypes.c_char * len(img)).from_buffer_copy(img)
        self.overlay.setOverlayRaw(self.handle, img, width, height, 4)
        self.updateOpacity(self.settings["opacity"])
        self.lastUpdate = time.monotonic()

    def clearImage(self):
        self.updateImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))

    def updateColor(self, col):
        """
        col is a 3-tuple representing (r, g, b)
        """
        self.settings["color"] = col
        r, g, b = self.settings["color"]
        self.overlay.setOverlayColor(self.handle, r, g, b)

    def updateOpacity(self, opacity, with_fade=False):
        self.settings["opacity"] = opacity

        if with_fade is True:
            if self.fadeRatio > 0:
                self.overlay.setOverlayAlpha(self.handle, self.fadeRatio * self.settings["opacity"])
        else:
            self.overlay.setOverlayAlpha(self.handle, self.settings["opacity"])

    def updateUiScaling(self, ui_scaling):
        self.settings['ui_scaling'] = ui_scaling
        self.overlay.setOverlayWidthInMeters(self.handle, self.settings['ui_scaling'])

    def updatePosition(self, pos, depth):
        """
        pos is a 2-tuple representing normalized (x, y)
        depth is a float representing the depth of the icon plane
        """
        self.settings["x_pos"] = pos[0]
        self.settings["y_pos"] = pos[1]
        self.settings["depth"] = depth

        self.transform = mat34Id() # no rotation required for HMD attachment

        # assign position
        self.transform[0][3] = self.settings["x_pos"] * self.settings['depth']
        self.transform[1][3] = self.settings["y_pos"] * self.settings['depth']
        self.transform[2][3] = - self.settings['depth']

        self.overlay.setOverlayTransformTrackedDeviceRelative(
            self.handle,
            openvr.k_unTrackedDeviceIndex_Hmd,
            self.transform
        )

    def updateDisplayDuration(self, display_duration):
        self.settings['display_duration'] = display_duration

    def updateFadeoutDuration(self, fadeout_duration):
        self.settings['fadeout_duration'] = fadeout_duration

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
        if (currentTime - lastUpdate) > self.settings['display_duration']:
            timeThroughInterval = currentTime - lastUpdate - self.settings['display_duration']
            self.fadeRatio = 1 - timeThroughInterval / self.settings['fadeout_duration']
            if self.fadeRatio < 0:
                self.fadeRatio = 0
            self.overlay.setOverlayAlpha(self.handle, self.fadeRatio * self.settings['opacity'])

    def update(self):
        currTime = time.monotonic()
        if self.settings['fadeout_duration'] != 0:
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
        self.shutdownOverlay()

    def main(self):
        self.init()
        if self.initialized is True:
            self.mainloop()

    def startOverlay(self):
        self.thread_overlay = Thread(target=self.main)
        self.thread_overlay.daemon = True
        self.thread_overlay.start()

    def setStopOverlay(self):
        self.loop = False

    def shutdownOverlay(self):
        if self.thread_overlay is not None:
            self.thread_overlay.join()
            self.thread_overlay = None
        if self.overlay is not None:
            self.overlay.destroyOverlay(self.handle)
            self.overlay = None
        if self.system is not None:
            openvr.shutdown()
            self.system = None
        self.initialized = False

    @staticmethod
    def checkSteamvrRunning() -> bool:
        _proc_name = "vrmonitor.exe" if os.name == 'nt' else "vrmonitor"
        return _proc_name in (p.name() for p in process_iter())

if __name__ == '__main__':
    from overlay_image import OverlayImage
    overlay_image = OverlayImage()

    for i in range(100):
        print(i)
        overlay = Overlay(0, 0, 1, 1, 1, 1, 1)
        overlay.startOverlay()
        time.sleep(1)

        # Example usage
        img = overlay_image.createOverlayImageShort("こんにちは、世界！さようなら", "Japanese", "Hello,World!Goodbye", "Japanese", ui_type="sakura")
        overlay.updateImage(img)
        time.sleep(0.5)

        img = overlay_image.createOverlayImageShort("こんにちは、世界！さようなら", "Japanese", "Hello,World!Goodbye", "Japanese")
        overlay.updateImage(img)
        time.sleep(0.5)

        overlay.setStopOverlay()
