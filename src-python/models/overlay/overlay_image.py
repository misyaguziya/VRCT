from os import path as os_path
from datetime import datetime
from typing import Tuple
from PIL import Image, ImageDraw, ImageFont

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
    def concatenateImagesVertically(img1: Image, img2: Image) -> Image:
        dst = Image.new("RGBA", (img1.width, img1.height + img2.height))
        dst.paste(img1, (0, 0))
        dst.paste(img2, (0, img1.height))
        return dst

    @staticmethod
    def addImageMargin(image: Image, top: int, right: int, bottom: int, left: int, color: Tuple[int, int, int, int]) -> Image:
        width, height = image.size
        new_width = width + right + left
        new_height = height + top + bottom
        result = Image.new(image.mode, (new_width, new_height), color)
        result.paste(image, (left, top))
        return result

    @staticmethod
    def getUiSizeSmall():
        return {
            "width": int(960*4),
            "height": int(23*4),
            "font_size": int(23*4),
        }

    @staticmethod
    def getUiColorSmall(ui_type):
        background_color = (41, 42, 45)
        background_outline_color = (41, 42, 45)
        text_color = (223, 223, 223)
        match ui_type:
            case "default":
                pass
            case _:
                pass
        return {
            "background_color": background_color,
            "background_outline_color": background_outline_color,
            "text_color": text_color
        }

    def createTextboxSmall(self, text, language, text_color, base_width, base_height, font_size):
        font_family = self.LANGUAGES.get(language, "NotoSansJP-Regular")
        img = Image.new("RGBA", (base_width, base_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype(os_path.join(os_path.dirname(os_path.dirname(os_path.dirname(__file__))), "fonts", f"{font_family}.ttf"), font_size)
        except Exception:
            font = ImageFont.truetype(os_path.join(os_path.dirname(__file__), "..",  "..",  "..", "fonts", f"{font_family}.ttf"), font_size)

        text_width = draw.textlength(text, font)
        character_width = text_width // len(text)
        character_line_num = int((base_width) // character_width) - 12
        if len(text) > character_line_num:
            text = "\n".join([text[i:i+character_line_num] for i in range(0, len(text), character_line_num)])
        text_height = font_size * (len(text.split("\n")) + 1) + 20
        img = Image.new("RGBA", (base_width, text_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        text_x = base_width // 2
        text_y = text_height // 2
        draw.text((text_x, text_y), text, text_color, anchor="mm", stroke_width=0, font=font, align="center")
        return img

    def createOverlayImageSmall(self, message, your_language, translation="", target_language=None, ui_type="default"):
        ui_size = self.getUiSizeSmall()
        height = ui_size["height"]
        width = ui_size["width"]
        font_size = ui_size["font_size"]

        ui_colors = self.getUiColorSmall(ui_type)
        text_color = ui_colors["text_color"]
        background_color = ui_colors["background_color"]
        background_outline_color = ui_colors["background_outline_color"]

        img = self.createTextboxSmall(message, your_language, text_color, width, height, font_size)
        if len(translation) > 0 and target_language is not None:
            translation_img = self.createTextboxSmall(translation, target_language, text_color, width, height, font_size)
            img = self.concatenateImagesVertically(img, translation_img)

        background = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(background)
        draw.rounded_rectangle([(0, 0), img.size], radius=30, fill=background_color, outline=background_outline_color, width=5)

        img = Image.alpha_composite(background, img)
        return img

    @staticmethod
    def getUiSizeLarge():
        return {
            "width": int(960*2),
            "font_size_large": int(23*4),
            "font_size_small": int(23*4*2/3),
        }

    @staticmethod
    def getUiColorLarge():
        background_color = (41, 42, 45)
        background_outline_color = (41, 42, 45)
        text_color_large = (223, 223, 223)
        text_color_small = (190, 190, 190)
        text_color_send = (70, 161, 146)
        text_color_receive = (220, 20, 60)
        text_color_time = (120, 120, 120)
        return {
            "background_color": background_color,
            "background_outline_color": background_outline_color,
            "text_color_large": text_color_large,
            "text_color_small": text_color_small,
            "text_color_send": text_color_send,
            "text_color_receive": text_color_receive,
            "text_color_time": text_color_time
        }

    def createTextImageLarge(self, message_type, size, text, language):
        ui_size = self.getUiSizeLarge()
        font_size_large = ui_size["font_size_large"]
        font_size_small = ui_size["font_size_small"]
        width = ui_size["width"]

        ui_color = self.getUiColorLarge()
        text_color_large = ui_color["text_color_large"]
        text_color_small = ui_color["text_color_small"]

        font_size = font_size_large if size == "large" else font_size_small
        text_color = text_color_large if size == "large" else text_color_small
        anchor = "lm" if message_type == "receive" else "rm"
        text_x = 0 if message_type == "receive" else width
        align = "left" if message_type == "receive" else "right"
        font_family = self.LANGUAGES.get(language, "NotoSansJP-Regular")

        img = Image.new("RGBA", (0, 0), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype(os_path.join(os_path.dirname(os_path.dirname(os_path.dirname(__file__))), "fonts", f"{font_family}.ttf"), font_size)
        except Exception:
            font = ImageFont.truetype(os_path.join(os_path.dirname(__file__), "..",  "..",  "..", "fonts", f"{font_family}.ttf"), font_size)
        text_width = draw.textlength(text, font)
        character_width = text_width // len(text)
        character_line_num = int(width // character_width)
        if len(text) > character_line_num:
            text = "\n".join([text[i:i+character_line_num] for i in range(0, len(text), character_line_num)])
        n_num = len(text.split("\n")) - 1
        text_height =  int(font_size*(n_num+2))
        img = Image.new("RGBA", (width, text_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        text_y = text_height // 2
        draw.multiline_text((text_x, text_y), text, text_color, anchor=anchor, stroke_width=0, font=font, align=align)
        return img

    def createTextImageMessageType(self, message_type, date_time):
        ui_size = self.getUiSizeLarge()
        width = ui_size["width"]
        font_size = ui_size["font_size_small"]

        ui_color = self.getUiColorLarge()
        text_color_send = ui_color["text_color_send"]
        text_color_receive = ui_color["text_color_receive"]
        text_color_time = ui_color["text_color_time"]

        anchor = "lm" if message_type == "receive" else "rm"
        text = "Receive" if message_type == "receive" else "Send"
        text_color = text_color_receive if message_type == "receive" else text_color_send

        img = Image.new("RGBA", (0, 0), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype(os_path.join(os_path.dirname(os_path.dirname(os_path.dirname(__file__))), "fonts", "NotoSansJP-Regular.ttf"), font_size)
        except Exception:
            font = ImageFont.truetype(os_path.join(os_path.dirname(__file__), "..",  "..",  "..", "fonts", "NotoSansJP-Regular.ttf"), font_size)
        text_height = font_size*2
        text_width = draw.textlength(date_time, font)
        character_width = text_width // len(date_time)
        img = Image.new("RGBA", (width, text_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        text_y = text_height // 2
        text_time_x = 0 if message_type == "receive" else width - (text_width + character_width)
        text_x = (text_width + character_width) if message_type == "receive" else width
        draw.text((text_time_x, text_y), date_time, text_color_time, anchor=anchor, stroke_width=0, font=font)
        draw.text((text_x, text_y), text, text_color, anchor=anchor, stroke_width=0, font=font)
        return img

    def createTextboxLarge(self, message_type, message, your_language, translation, target_language, date_time):
        message_type_img = self.createTextImageMessageType(message_type, date_time)
        if len(translation) > 0 and target_language is not None:
            img = self.createTextImageLarge(message_type, "small", message, your_language)
            translation_img = self.createTextImageLarge(message_type, "large",translation, target_language)
            img = self.concatenateImagesVertically(img, translation_img)
        else:
            img = self.createTextImageLarge(message_type, "large", message, your_language)
        return self.concatenateImagesVertically(message_type_img, img)

    def createOverlayImageLarge(self, message_type, message, your_language, translation="", target_language=None):
        ui_color = self.getUiColorLarge()
        background_color = ui_color["background_color"]
        background_outline_color = ui_color["background_outline_color"]

        self.message_log.append(
            {
                "message_type":message_type,
                "message":message,
                "your_language":your_language,
                "translation":translation,
                "target_language":target_language,
                "datetime":datetime.now().strftime("%H:%M")
            }
        )

        if len(self.message_log) > 10:
            self.message_log = self.message_log[-10:]

        imgs = []
        for log in self.message_log:
            message_type = log["message_type"]
            message = log["message"]
            your_language = log["your_language"]
            translation = log["translation"]
            target_language = log["target_language"]
            date_time = log["datetime"]
            img = self.createTextboxLarge(message_type, message, your_language, translation, target_language, date_time)
            imgs.append(img)

        img = imgs[0]
        for i in imgs[1:]:
            img = self.concatenateImagesVertically(img, i)
        img = self.addImageMargin(img, 0, 20, 0, 20, (0, 0, 0, 0))

        width, height = img.size
        background = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(background)
        draw.rounded_rectangle([(0, 0), (width, height)], radius=15, fill=background_color, outline=background_outline_color, width=5)
        img = Image.alpha_composite(background, img)
        return img

if __name__ == "__main__":
    overlay = OverlayImage()
    img = overlay.createOverlayImageSmall("Hello, World!", "English", "こんにちは、世界！", "Japanese")
    img.save("overlay_small.png")
    img = overlay.createOverlayImageLarge("send", "Hello, World!", "English", "こんにちは、世界！", "Japanese")
    img.save("overlay_large0.png")
    img = overlay.createOverlayImageLarge("receive", "こんにちは、世界！", "Japanese", "Hello, World!", "English")
    img.save("overlay_large1.png")