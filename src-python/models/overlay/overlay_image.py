from os import path as os_path
from datetime import datetime
from typing import Tuple
from PIL import Image, ImageDraw, ImageFont
try:
    from utils import errorLogging
except ImportError:
    def errorLogging():
        import traceback
        print(traceback.format_exc())

class OverlayImage:
    LANGUAGES = {
        "Japanese": "NotoSansJP-Regular",
        "Korean": "NotoSansKR-Regular",
        "Chinese Simplified": "NotoSansSC-Regular",
        "Chinese Traditional": "NotoSansTC-Regular",
    }

    def __init__(self):
        self.message_log = []

    @staticmethod
    def concatenateImagesVertically(img1: Image, img2: Image, margin: int = 0) -> Image:
        total_height = img1.height + img2.height + margin
        dst = Image.new("RGBA", (img1.width, total_height))
        dst.paste(img1, (0, 0))
        dst.paste(img2, (0, img1.height + margin))
        return dst

    @staticmethod
    def addImageMargin(image: Image, top: int, right: int, bottom: int, left: int, color: Tuple[int, int, int, int]) -> Image:
        new_width = image.width + right + left
        new_height = image.height + top + bottom
        result = Image.new(image.mode, (new_width, new_height), color)
        result.paste(image, (left, top))
        return result

    @staticmethod
    def getUiSizeSmallLog() -> dict:
        return {
            "width": 3840,
            "height": 92,
            "font_size": 92,
        }

    @staticmethod
    def getUiColorSmallLog() -> dict:
        colors = {
            "background_color": (41, 42, 45),
            "background_outline_color": (41, 42, 45),
            "text_color": (223, 223, 223)
        }
        return colors

    def createTextboxSmallLog(self, text:str, language:str, text_color:tuple, base_width:int, base_height:int, font_size:int) -> Image:
        font_family = self.LANGUAGES.get(language, "NotoSansJP-Regular")
        img = Image.new("RGBA", (base_width, base_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        try:
            font_path = os_path.join(os_path.dirname(os_path.dirname(os_path.dirname(__file__))), "fonts", f"{font_family}.ttf")
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            errorLogging()
            font_path = os_path.join(os_path.dirname(__file__), "..", "..", "..", "fonts", f"{font_family}.ttf")
            font = ImageFont.truetype(font_path, font_size)

        text_width = draw.textlength(text, font)
        character_width = text_width // len(text)
        character_line_num = int((base_width // character_width) - 12)
        if len(text) > character_line_num:
            text = "\n".join([text[i:i + character_line_num] for i in range(0, len(text), character_line_num)])
        text_height = font_size * (len(text.split("\n")) + 1) + 20
        img = Image.new("RGBA", (base_width, text_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        text_x = base_width // 2
        text_y = text_height // 2
        draw.text((text_x, text_y), text, text_color, anchor="mm", stroke_width=0, font=font, align="center")
        return img

    def createOverlayImageSmallLog(self, message:str, your_language:str, translation:str="", target_language:str=None) -> Image:
        ui_size = self.getUiSizeSmallLog()
        width, height, font_size = ui_size["width"], ui_size["height"], ui_size["font_size"]

        ui_colors = self.getUiColorSmallLog()
        text_color = ui_colors["text_color"]
        background_color = ui_colors["background_color"]
        background_outline_color = ui_colors["background_outline_color"]

        img = self.createTextboxSmallLog(message, your_language, text_color, width, height, font_size)
        if translation and target_language:
            translation_img = self.createTextboxSmallLog(translation, target_language, text_color, width, height, font_size)
            img = self.concatenateImagesVertically(img, translation_img)

        background = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(background)
        draw.rounded_rectangle([(0, 0), img.size], radius=50, fill=background_color, outline=background_outline_color, width=5)

        return Image.alpha_composite(background, img)

    @staticmethod
    def getUiSizeLargeLog() -> dict:
        return {
            "width": 960,
            "font_size_large": 30,
            "font_size_small": 20,
            "margin": 25,
            "radius": 25,
            "padding": 10,
            "clause_margin": 20,
        }

    @staticmethod
    def getUiColorLargeLog() -> dict:
        return {
            "background_color": (41, 42, 45),
            "background_outline_color": (41, 42, 45),
            "text_color_large": (223, 223, 223),
            "text_color_small": (190, 190, 190),
            "text_color_send": (97, 151, 180),
            "text_color_receive": (168, 97, 180),
            "text_color_time": (120, 120, 120)
        }

    def createTextImageLargeLog(self, message_type:str, size:str, text:str, language:str) -> Image:
        ui_size = self.getUiSizeLargeLog()
        font_size = ui_size["font_size_large"] if size == "large" else ui_size["font_size_small"]
        text_color = self.getUiColorLargeLog()[f"text_color_{size}"]
        anchor = "lm" if message_type == "receive" else "rm"
        text_x = 0 if message_type == "receive" else ui_size["width"]
        align = "left" if message_type == "receive" else "right"
        font_family = self.LANGUAGES.get(language, "NotoSansJP-Regular")

        img = Image.new("RGBA", (0, 0), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        try:
            font_path = os_path.join(os_path.dirname(os_path.dirname(os_path.dirname(__file__))), "fonts", f"{font_family}.ttf")
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            errorLogging()
            font_path = os_path.join(os_path.dirname(__file__), "..", "..", "..", "fonts", f"{font_family}.ttf")
            font = ImageFont.truetype(font_path, font_size)

        text_width = draw.textlength(text, font)
        character_width = text_width // len(text)
        character_line_num = int((ui_size["width"] // character_width) - 1)
        if len(text) > character_line_num:
            text = "\n".join([text[i:i + character_line_num] for i in range(0, len(text), character_line_num)])
        text_height = font_size * len(text.split("\n")) + ui_size["padding"]
        img = Image.new("RGBA", (ui_size["width"], text_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        text_y = text_height // 2
        draw.multiline_text((text_x, text_y), text, text_color, anchor=anchor, stroke_width=0, font=font, align=align)
        return img

    def createTextImageMessageType(self, message_type:str, date_time:str) -> Image:
        ui_size = self.getUiSizeLargeLog()
        font_size = ui_size["font_size_small"]
        ui_padding = ui_size["padding"]

        ui_color = self.getUiColorLargeLog()
        text_color = ui_color[f"text_color_{message_type}"]
        text_color_time = ui_color["text_color_time"]

        anchor = "lm" if message_type == "receive" else "rm"
        text = "Receive" if message_type == "receive" else "Send"

        img = Image.new("RGBA", (0, 0), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        try:
            font_path = os_path.join(os_path.dirname(os_path.dirname(os_path.dirname(__file__))), "fonts", "NotoSansJP-Regular.ttf")
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            errorLogging()
            font_path = os_path.join(os_path.dirname(__file__), "..", "..", "..", "fonts", "NotoSansJP-Regular.ttf")
            font = ImageFont.truetype(font_path, font_size)

        text_height = font_size + ui_padding
        text_width = draw.textlength(date_time, font)
        character_width = text_width // len(date_time)
        img = Image.new("RGBA", (ui_size["width"], text_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        text_y = text_height // 2
        text_time_x = 0 if message_type == "receive" else ui_size["width"] - (text_width + character_width)
        text_x = (text_width + character_width) if message_type == "receive" else ui_size["width"]
        draw.text((text_time_x, text_y), date_time, text_color_time, anchor=anchor, stroke_width=0, font=font)
        draw.text((text_x, text_y), text, text_color, anchor=anchor, stroke_width=0, font=font)
        return img

    def createTextboxLargeLog(self, message_type:str, message:str, your_language:str, translation:str, target_language:str, date_time:str) -> Image:
        message_type_img = self.createTextImageMessageType(message_type, date_time)
        if translation and target_language:
            img = self.createTextImageLargeLog(message_type, "small", message, your_language)
            translation_img = self.createTextImageLargeLog(message_type, "large", translation, target_language)
            img = self.concatenateImagesVertically(img, translation_img)
        else:
            img = self.createTextImageLargeLog(message_type, "large", message, your_language)
        return self.concatenateImagesVertically(message_type_img, img)

    def createOverlayImageLargeLog(self, message_type:str, message:str, your_language:str, translation:str="", target_language:str=None) -> Image:
        ui_color = self.getUiColorLargeLog()
        background_color = ui_color["background_color"]
        background_outline_color = ui_color["background_outline_color"]

        ui_size = self.getUiSizeLargeLog()
        ui_margin = ui_size["margin"]
        ui_radius = ui_size["radius"]
        ui_clause_margin = ui_size["clause_margin"]

        self.message_log.append({
            "message_type": message_type,
            "message": message,
            "your_language": your_language,
            "translation": translation,
            "target_language": target_language,
            "datetime": datetime.now().strftime("%H:%M")
        })

        if len(self.message_log) > 5:
            self.message_log = self.message_log[-5:]

        imgs = [
            self.createTextboxLargeLog(
                log["message_type"],
                log["message"],
                log["your_language"],
                log["translation"],
                log["target_language"],
                log["datetime"]) for log in self.message_log
            ]

        img = imgs[0]
        for i in imgs[1:]:
            img = self.concatenateImagesVertically(img, i, ui_clause_margin)
        img = self.addImageMargin(img, ui_margin, ui_margin, ui_margin, ui_margin, (0, 0, 0, 0))

        width, height = img.size
        background = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(background)
        draw.rounded_rectangle([(0, 0), (width, height)], radius=ui_radius, fill=background_color, outline=background_outline_color, width=5)
        return Image.alpha_composite(background, img)

if __name__ == "__main__":
    overlay = OverlayImage()
    img = overlay.createOverlayImageSmallLog("Hello, World!", "English", "こんにちは、世界！", "Japanese")
    img.save("overlay_small.png")
    img = overlay.createOverlayImageLargeLog("send", "Hello, World!", "English", "こんにちは、世界！", "Japanese")
    img = overlay.createOverlayImageLargeLog("receive", "こんにちは、世界！", "Japanese", "Hello, World!", "English")
    img = overlay.createOverlayImageLargeLog("send", "Hello, World!aaaaaaaaaaaaaaaaaあああああああああああああああaaaaaaaaaaaaaaaaaあああああああああああああああ", "English", "aaaaaaaaaaaaaaaaaあああああああああああああああaaaaaaaaaaaaaaaaaあああああああああああああああこんにちは、世界！", "Japanese")
    img = overlay.createOverlayImageLargeLog("receive", "こんにちは、世界！aaaaaaaaaaaaaaaaaあああああああああああああああaaaaaaaaaaaaaaaaaあああああああああああああああ", "Japanese", "Hello, World!aaaaaaaaaaaaaaaaaあああああああああああああああaaaaaaaaaaaaaaaaaあああああああああああああああ", "English")
    img = overlay.createOverlayImageLargeLog("send", "Hello, World!", "English", "こんにちは、世界！", "Japanese")
    img = overlay.createOverlayImageLargeLog("receive", "こんにちは、世界！", "Japanese", "Hello, World!", "English")
    img = overlay.createOverlayImageLargeLog("send", "Hello, World!aaaaaaaaaaaaaaaaaあああああああああああああああaaaaaaaaaaaaaaaaaあああああああああああああああ", "English", "aaaaaaaaaaaaaaaaaあああああああああああああああaaaaaaaaaaaaaaaaaあああああああああああああああこんにちは、世界！", "Japanese")
    img = overlay.createOverlayImageLargeLog("receive", "こんにちは、世界！aaaaaaaaaaaaaaaaaあああああああああああああああaaaaaaaaaaaaaaaaaあああああああああああああああ", "Japanese", "Hello, World!aaaaaaaaaaaaaaaaaあああああああああああああああaaaaaaaaaaaaaaaaaあああああああああああああああ", "English")
    img = overlay.createOverlayImageLargeLog("send", "Hello, World!", "English", "こんにちは、世界！", "Japanese")
    img = overlay.createOverlayImageLargeLog("receive", "こんにちは、世界！", "Japanese", "Hello, World!", "English")
    img = overlay.createOverlayImageLargeLog("send", "Hello, World!aaaaaaaaaaaaaaaaaあああああああああああああああaaaaaaaaaaaaaaaaaあああああああああああああああ", "English", "aaaaaaaaaaaaaaaaaあああああああああああああああaaaaaaaaaaaaaaaaaあああああああああああああああこんにちは、世界！", "Japanese")
    img = overlay.createOverlayImageLargeLog("receive", "こんにちは、世界！aaaaaaaaaaaaaaaaaあああああああああああああああaaaaaaaaaaaaaaaaaあああああああああああああああ", "Japanese", "Hello, World!aaaaaaaaaaaaaaaaaあああああああああああああああaaaaaaaaaaaaaaaaaあああああああああああああああ", "English")
    img.save("overlay_large.png")