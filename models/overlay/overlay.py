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
}

def mat34Id():
    arr = openvr.HmdMatrix34_t()
    arr[0][0] = 1
    arr[1][1] = 1
    arr[2][2] = 1
    return arr

class UIElement:
    def __init__(self, overlayRoot, key, name, pos, img, flip = False) -> None:
        """
        pos is a 2-tuple representing (x, y) normalised position of the overlay on the screen
        """
        self.overlay = overlayRoot
        self.overlayKey = key
        self.overlayName = name
        self.flip = flip

        self.handle = self.overlay.createOverlay(self.overlayKey, self.overlayName)

        # configure overlay appearance
        width, height = img.size
        img = img.tobytes()
        img = (ctypes.c_char * len(img)).from_buffer_copy(img)

        self.setImage(img, width, height) # blank image for default
        self.setColour(settings['Colour'])
        self.setTransparency(settings['Transparency'])
        self.overlay.setOverlayWidthInMeters(
            self.handle,
            settings['Normalised icon width'] * settings['Icon plane depth']
        )

        self.setPosition(pos)

        self.overlay.showOverlay(self.handle)

    def setImage(self, img, width, height):
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
    def __init__(self, img) -> None:
        self.overlay = openvr.IVROverlay()

        self.UI = UIElement(
            self.overlay,
            "VRCT",
            "Receive UI Element",
            (settings['Normalised icon X position'], settings['Normalised icon Y position']),
            img,
        )

async def mainLoop(uiMan):
    time.sleep(10)

async def init_main(img):
    uiMan = UIManager(img)
    await mainLoop(uiMan)

class Overlay:
    def __init__(self):
        openvr.init(openvr.VRApplication_Overlay)

    def plot_overlay(message, your_language="Japanese", translation=None, target_language=None):
        img = create_overlay_image(message, your_language, translation, target_language)
        UIManager(img)

if __name__ == '__main__':
    message = "Hello,World!Goodbye こんにちは、世界！さようなら안녕하세요, 세계!안녕 你好世界！再见 你好世界！再見 Hello,World!Goodbye こんにちは、世界！さようなら안녕하세요, 세계!안녕 你好世界！再见 你好世界！再見 Hello,World!Goodbye こんにちは、世界！さようなら안녕하세요, 세계!안녕 你好世界！再见 你好世界！再見"
    translation = "Hello,World!Goodbye こんにちは、世界！さようなら안녕하세요, 세계!안녕 你好世界！再见 你好世界！再見 Hello,World!Goodbye こんにちは、世界！さようなら안녕하세요, 세계!안녕 你好世界！再见 你好世界！再見 Hello,World!Goodbye こんにちは、世界！さようなら안녕하세요, 세계!안녕 你好世界！再见 你好世界！再見"
    your_language = "Japanese"
    target_language = "Chinese Simplified"
    # font_family = "NotoSansJP-Regular"
    # img = create_text_image(message, font_family)

    # openvr.init(openvr.VRApplication_Overlay)
    # asyncio.run(init_main(img))
    o = Overlay()
    o.plot_overlay(message, your_language, translation, target_language)