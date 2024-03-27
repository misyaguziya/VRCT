import ctypes
import time
import asyncio
import openvr
from PIL import Image, ImageDraw, ImageFont
from os import path as os_path

def create_overlay_image(message, your_language, translation=None, target_language=None):
    width, height = (1920, 46)
    background_color = (54, 63, 77)
    text_color = (223, 223, 224)
    font_size = 46
    languages = {
        "Japanese" : "NotoSansJP-Regular",
        "Korean" : "NotoSansKR-Regular",
        "Chinese Simplified" : "NotoSansSC-Regular",
        "Chinese Traditional" : "NotoSansTC-Regular",
    }

    def get_concat_v(im1, im2):
        dst = Image.new('RGBA', (im1.width, im1.height + im2.height))
        dst.paste(im1, (0, 0))
        dst.paste(im2, (0, im1.height))
        return dst

    def create_textbox(text, language):
        font_family = languages.get(language, "NotoSansJP-Regular")
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(os_path.join(os_path.dirname(__file__), "fonts", f"{font_family}.ttf"), font_size)
        text_width = draw.textlength(text, font)
        character_width = text_width // len(text)
        character_line_num = int((width - 40) // character_width)
        if len(text) > character_line_num:
            text = "\n".join([text[i:i+character_line_num] for i in range(0, len(text), character_line_num)])
        text_height = font_size * (len(text.split("\n")) + 1) + 20
        img = Image.new("RGBA", (width, text_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # draw.rounded_rectangle([(0, 0), (width, text_height)], radius=30, fill=background_color, outline=background_color, width=5)

        text_x = width // 2
        text_y = text_height // 2
        draw.text((text_x, text_y), text, text_color, anchor="mm", stroke_width=0, font=font, align="center")
        return img

    img = create_textbox(message, your_language)
    if translation is not None and target_language is not None:
        translation_img = create_textbox(translation, target_language)
        img = get_concat_v(img, translation_img)

    width, height = img.size
    background = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(background)
    draw.rounded_rectangle([(0, 0), (width, height)], radius=30, fill=background_color, outline=background_color, width=5)
    img = Image.alpha_composite(background, img)

    return img

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

def mat34Id():
    arr = openvr.HmdMatrix34_t()
    arr[0][0] = 1
    arr[1][1] = 1
    arr[2][2] = 1
    return arr

class UIElement:
    def __init__(self, overlayRoot, key, name, pos, flip = False) -> None:
        """
        pos is a 2-tuple representing (x, y) normalised position of the overlay on the screen
        """
        self.overlay = overlayRoot
        self.overlayKey = key
        self.overlayName = name
        self.flip = flip

        self.handle = self.overlay.createOverlay(self.overlayKey, self.overlayName)

        self.setImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0))) # blank image for default
        self.setColour(settings['Colour'])
        self.setTransparency(settings['Transparency'])
        self.overlay.setOverlayWidthInMeters(
            self.handle,
            settings['Normalised icon width'] * settings['Icon plane depth']
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
        self.transform[0][3] = pos[0] * settings['Icon plane depth']
        self.transform[1][3] = pos[1] * settings['Icon plane depth']
        self.transform[2][3] = -settings['Icon plane depth']

        self.overlay.setOverlayTransformTrackedDeviceRelative(
            self.handle,
            openvr.k_unTrackedDeviceIndex_Hmd,
            self.transform
        )

class UIManager:
    def __init__(self):
        self.overlay = openvr.IVROverlay()

        self.overlayUI = UIElement(
            self.overlay,
            "VRCT",
            "Receive UI Element",
            (settings['Normalised icon X position'], settings['Normalised icon Y position']),
        )
        self.lastUpdate = time.monotonic()

    def update(self):
        currTime = time.monotonic()
        if settings['Fade interval'] != 0:
            self.evaluateTransparencyFade(self.overlayUI, self.lastUpdate, currTime)

    def uiUpdate(self, img):
        self.overlayUI.setImage(img)
        self.overlayUI.setTransparency(settings['Transparency'])
        self.lastUpdate = time.monotonic()

    def evaluateTransparencyFade(self, ui, lastUpdate, currentTime):
        if (currentTime - lastUpdate) > settings['Fade time']:
            timeThroughInterval = currentTime - lastUpdate - settings['Fade time']
            fadeRatio = 1 - timeThroughInterval / settings['Fade interval']
            if fadeRatio < 0:
                fadeRatio = 0

            ui.setTransparency(fadeRatio * settings['Transparency'])

class Overlay:
    def __init__(self):
        self.initFlag = False

    def checkHMD(self):
        return openvr.isHmdPresent()

    def checkRuntime(self):
        return openvr.isRuntimeInstalled()

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
        self.uiMan = UIManager()
        await self.mainLoop()

    def startOverlay(self):
        asyncio.run(self.init_main())

if __name__ == '__main__':
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

    if overlay.initFlag is False:
        overlay.init()
    if overlay.initFlag is True:
        t = threadFnc(overlay.startOverlay)
        t.start()

    img = create_overlay_image("こんにちは、世界！さようなら", "Japanese", "Hello,World!Goodbye", "Japanese")
    if overlay.initFlag is True:
        overlay.uiMan.uiUpdate(img)
    time.sleep(10)

    img = create_overlay_image("こんにちは、世界！さようなら", "Japanese", "안녕하세요, 세계!안녕", "Korean")
    if overlay.initFlag is True:
        overlay.uiMan.uiUpdate(img)
    time.sleep(10)

    img = create_overlay_image("こんにちは、世界！さようなら", "Japanese", "你好世界！再见", "Chinese Simplified")
    if overlay.initFlag is True:
        overlay.uiMan.uiUpdate(img)
    time.sleep(10)