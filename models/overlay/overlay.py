import ctypes
import time
import asyncio
import openvr
from PIL import Image

# This code is based on the following source:
# [GOpy](https://github.com/MeroFune/GOpy)
def mat34Id():
    arr = openvr.HmdMatrix34_t()
    arr[0][0] = 1
    arr[1][1] = 1
    arr[2][2] = 1
    return arr

class UIElement:
    def __init__(self, overlayRoot, key: str, name: str, settings: dict = None) -> None:
        """
        pos is a 2-tuple representing (x, y) normalised position of the overlay on the screen
        """
        self.overlay = overlayRoot
        self.overlayKey = key
        self.overlayName = name
        self.settings = settings
        pos = (self.settings['Normalised icon X position'], self.settings['Normalised icon Y position'])
        self.handle = self.overlay.createOverlay(self.overlayKey, self.overlayName)

        self.setImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0))) # blank image for default
        self.setColour(self.settings['Colour'])
        self.setTransparency(self.settings['Transparency'])
        self.overlay.setOverlayWidthInMeters(
            self.handle,
            self.settings['Normalised icon width'] * self.settings['Icon plane depth']
        )

        self.setPosition(pos)
        self.overlay.showOverlay(self.handle)

    def setImage(self, img):
        # configure overlay appearance
        width, height = img.size
        img = img.tobytes()
        img = (ctypes.c_char * len(img)).from_buffer_copy(img)
        self.overlay.setOverlayRaw(self.handle, img, width, height, 4)

    def setColour(self, col):
        """
        col is a 3-tuple representing (r, g, b)
        """
        self.overlay.setOverlayColor(self.handle, col[0], col[1], col[2])

    def setTransparency(self, a):
        self.overlay.setOverlayAlpha(self.handle, a)

    def setPosition(self, pos):
        """
        pos is a 2-tuple representing normalised (x, y)
        """
        self.transform = mat34Id() # no rotation required for HMD attachment

        # assign position
        self.transform[0][3] = pos[0] * self.settings['Icon plane depth']
        self.transform[1][3] = pos[1] * self.settings['Icon plane depth']
        self.transform[2][3] = - self.settings['Icon plane depth']

        self.overlay.setOverlayTransformTrackedDeviceRelative(
            self.handle,
            openvr.k_unTrackedDeviceIndex_Hmd,
            self.transform
        )

class UIManager:
    def __init__(self, settings):
        self.overlay = openvr.IVROverlay()
        self.settings = settings
        self.overlayUI = UIElement(
            self.overlay,
            "VRCT",
            "Receive UI Element",
            self.settings,
        )
        self.lastUpdate = time.monotonic()

    def update(self):
        currTime = time.monotonic()
        if self.settings['Fade interval'] != 0:
            self.evaluateTransparencyFade(self.overlayUI, self.lastUpdate, currTime)

    def uiUpdate(self, img):
        self.overlayUI.setImage(img)
        self.overlayUI.setTransparency(self.settings['Transparency'])
        self.lastUpdate = time.monotonic()

    def evaluateTransparencyFade(self, ui, lastUpdate, currentTime):
        if (currentTime - lastUpdate) > self.settings['Fade time']:
            timeThroughInterval = currentTime - lastUpdate - self.settings['Fade time']
            fadeRatio = 1 - timeThroughInterval / self.settings['Fade interval']
            if fadeRatio < 0:
                fadeRatio = 0

            ui.setTransparency(fadeRatio * self.settings['Transparency'])

    def posUpdate(self, pos):
        self.overlayUI.setPosition(pos)

class Overlay:
    def __init__(self):
        self.initFlag = False
        settings = {
            "Colour": [1, 1, 1],
            "Transparency": 1,
            "Normalised icon X position": 0.0,
            "Normalised icon Y position": -0.41,
            "Icon plane depth": 1,
            "Normalised icon width": 1,
            "Fade time": 5,
            "Fade interval": 2,
        }
        self.settings = settings

    def init(self):
        try:
            openvr.init(openvr.VRApplication_Overlay)
            self.initFlag = True
        except Exception as e:
            print("Could not initialise OpenVR")

    async def mainLoop(self):
        while True:
            startTime = time.monotonic()
            self.uiMan.update()

            sleepTime = (1 / 60) - (time.monotonic() - startTime)
            if sleepTime > 0:
                await asyncio.sleep(sleepTime)

    async def init_main(self):
        self.uiMan = UIManager(self.settings)
        await self.mainLoop()

    def startOverlay(self):
        asyncio.run(self.init_main())

if __name__ == '__main__':
    from overlay_image import OverlayImage
    from threading import Thread, Event
    class threadFnc(Thread):
        def __init__(self, fnc, end_fnc=None, daemon=True, *args, **kwargs):
            super(threadFnc, self).__init__(daemon=daemon, *args, **kwargs)
            self.fnc = fnc
            self.end_fnc = end_fnc
            self._stop = Event()
        def stop(self):
            self._stop.set()
        def stopped(self):
            return self._stop.is_set()
        def run(self):
            while True:
                if self.stopped():
                    if callable(self.end_fnc):
                        self.end_fnc()
                    return
                self.fnc(*self._args, **self._kwargs)

    overlay = Overlay()
    overlay_image = OverlayImage()

    if overlay.initFlag is False:
        overlay.init()
    if overlay.initFlag is True:
        t = threadFnc(overlay.startOverlay)
        t.start()

    time.sleep(1)
    img = overlay_image.create_overlay_image_short("こんにちは、世界！さようなら", "Japanese", "Hello,World!Goodbye", "Japanese", ui_type="sakura")
    if overlay.initFlag is True:
        overlay.uiMan.uiUpdate(img)
    time.sleep(10)

    img = overlay_image.create_overlay_image_short("こんにちは、世界！さようなら", "Japanese", "안녕하세요, 세계!안녕", "Korean")
    if overlay.initFlag is True:
        overlay.uiMan.uiUpdate(img)
    time.sleep(10)

    img = overlay_image.create_overlay_image_short("こんにちは、世界！さようなら", "Japanese", "你好世界！再见", "Chinese Simplified")
    if overlay.initFlag is True:
        overlay.uiMan.uiUpdate(img)
    time.sleep(10)