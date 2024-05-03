import ctypes
import psutil
# from os import path as os_path
import ctypes
import time
import openvr
from PIL import Image
# from queue import Queue
from threading import Thread

def checkSteamvrRunning() -> bool:
    for proc in psutil.process_iter():
        if "vrserver.exe" == proc.name().lower():
            return True
    return False

def mat34Id():
    arr = openvr.HmdMatrix34_t()
    arr[0][0] = 1
    arr[1][1] = 1
    arr[2][2] = 1
    return arr

class Overlay:
    def __init__(self, x, y , depth, fade_time, fade_interval, transparency, ui_scaling):
        self.initialized = False
        settings = {
            "Color": [1, 1, 1],
            "Transparency": transparency,
            "Normalized_icon_X_position": x,
            "Normalized_icon_Y_position": y,
            "Icon_plane_depth": depth,
            "Fade_time": fade_time,
            "Fade_interval": fade_interval,
            "Ui_scaling": ui_scaling,
        }
        self.settings = settings
        self.system = None
        self.overlay = None
        self.handle = None
        # self.image_queue = Queue()
        self.lastUpdate = time.monotonic()
        self.thread_overlay = None

    def init(self):
        try:
            if checkSteamvrRunning() is True:
                self.system = openvr.init(openvr.VRApplication_Background)
                self.overlay = openvr.IVROverlay()
                self.handle = self.overlay.createOverlay("Overlay_Speaker2log", "SOverlay_Speaker2log_UI")

                self.updateImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))
                self.setColor(self.settings['Color'])
                self.updateColor()
                self.setTransparency(self.settings['Transparency'])
                self.updateTransparency()
                self.setUiScaling(self.settings['Ui_scaling'])
                self.updateUiScaling()
                self.setPosition((self.settings["Normalized_icon_X_position"], self.settings["Normalized_icon_Y_position"]))
                self.updatePosition()
                self.overlay.showOverlay(self.handle)
                self.initialized = True
        except Exception as e:
            print("Could not initialise OpenVR", e)

    # def setImage(self, img):
    #     self.image_queue.put(img)

    def updateImage(self, img):
        # _ = self.image_queue.get()
        # img = Image.open(os_path.join(os_path.dirname(os_path.dirname(os_path.dirname(__file__))), "img", "test_chatbox.png"))
        width, height = img.size
        img = img.tobytes()
        img = (ctypes.c_char * len(img)).from_buffer_copy(img)
        self.overlay.setOverlayRaw(self.handle, img, width, height, 4)
        self.updateTransparency()
        self.lastUpdate = time.monotonic()

    def clearImage(self):
        # while self.image_queue.empty() is False:
        #     self.image_queue.get()
        self.updateImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))

    def setColor(self, col):
        """
        col is a 3-tuple representing (r, g, b)
        """
        self.settings["Color"] = col

    def updateColor(self):
        r, g, b = self.settings["Color"]
        self.overlay.setOverlayColor(self.handle, r, g, b)

    def setTransparency(self, transparency):
        self.settings['Transparency'] = transparency

    def updateTransparency(self):
        self.overlay.setOverlayAlpha(self.handle, self.settings['Transparency'])

    def setUiScaling(self, ui_scaling):
        self.settings['Ui_scaling'] = ui_scaling

    def updateUiScaling(self):
        self.overlay.setOverlayWidthInMeters(self.handle, self.settings['Ui_scaling'])

    def setPosition(self, pos):
        """
        pos is a 2-tuple representing normalized (x, y)
        """
        self.settings["Normalized_icon_X_position"] = pos[0]
        self.settings["Normalized_icon_Y_position"] = pos[1]

    def setDepth(self, depth):
        self.settings["Icon_plane_depth"] = depth

    def updatePosition(self):
        self.transform = mat34Id() # no rotation required for HMD attachment

        # assign position
        self.transform[0][3] = self.settings["Normalized_icon_X_position"] * self.settings['Icon_plane_depth']
        self.transform[1][3] = self.settings["Normalized_icon_Y_position"] * self.settings['Icon_plane_depth']
        self.transform[2][3] = - self.settings['Icon_plane_depth']

        self.overlay.setOverlayTransformTrackedDeviceRelative(
            self.handle,
            openvr.k_unTrackedDeviceIndex_Hmd,
            self.transform
        )

    def setFadeTime(self, fade_time):
        self.settings['Fade_time'] = fade_time

    def setFadeInterval(self, fade_interval):
        self.settings['Fade_interval'] = fade_interval

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

    def evaluateTransparencyFade(self, lastUpdate, currentTime):
        if (currentTime - lastUpdate) > self.settings['Fade_time']:
            timeThroughInterval = currentTime - lastUpdate - self.settings['Fade_time']
            self.fadeRatio = 1 - timeThroughInterval / self.settings['Fade_interval']
            if self.fadeRatio < 0:
                self.fadeRatio = 0
            self.overlay.setOverlayAlpha(self.handle, self.fadeRatio * self.settings['Transparency'])

    def update(self):
        # self.updateUiScaling()
        # self.updatePosition()

        currTime = time.monotonic()
        if self.settings['Fade_interval'] != 0:
            self.evaluateTransparencyFade(self.lastUpdate, currTime)
        else:
            self.updateTransparency()

    def mainloop(self):
        while self.checkActive() is True:
            startTime = time.monotonic()
            self.update()
            sleepTime = (1 / 16) - (time.monotonic() - startTime)
            if sleepTime > 0:
                time.sleep(sleepTime)
        self.shutdown()

    def main(self):
        self.init()
        if self.initialized is True:
            self.mainloop()

    def startOverlay(self):
        self.thread_overlay = Thread(target=self.main)
        self.thread_overlay.daemon = True
        self.thread_overlay.start()

    def shutdown(self):
        if self.thread_overlay is not None:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(self.thread_overlay.ident), ctypes.py_object(SystemExit))
            self.thread_overlay = None
        if self.overlay is not None:
            self.overlay.destroyOverlay(self.handle)
            self.overlay = None
        if self.system is not None:
            openvr.shutdown()
            self.system = None
        self.initialized = False

if __name__ == '__main__':
    from overlay_image import OverlayImage
    overlay_image = OverlayImage()

    for i in range(100):
        print(i)
        overlay = Overlay(0, 0, 1, 1, 1, 1, 1)
        overlay.startOverlay()
        # time.sleep(0.1)

        # Example usage
        img = overlay_image.createOverlayImageShort("こんにちは、世界！さようなら", "Japanese", "Hello,World!Goodbye", "Japanese", ui_type="sakura")
        overlay.updateImage(img)
        time.sleep(0.5)

        img = overlay_image.createOverlayImageShort("こんにちは、世界！さようなら", "Japanese", "Hello,World!Goodbye", "Japanese")
        overlay.updateImage(img)
        time.sleep(0.5)

        overlay.shutdown()
