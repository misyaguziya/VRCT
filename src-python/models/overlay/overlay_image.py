from os import path as os_path
# from datetime import datetime
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
        pass

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
    def getUiSize():
        return {
            "width": int(960*4),
            "height": int(23*4),
            "font_size": int(23*4),
        }

    @staticmethod
    def getUiColors(ui_type):
        match ui_type:
            case "default":
                background_color = (41, 42, 45)
                background_outline_color = (41, 42, 45)
                text_color = (223, 223, 223)
            case "sakura":
                background_color = (225, 40, 30)
                background_outline_color = (255, 255, 255)
                text_color = (223, 223, 223)
        return {
            "background_color": background_color,
            "background_outline_color": background_outline_color,
            "text_color": text_color
        }

    @staticmethod
    def createDecorationImage(ui_type, image_size):
        decoration_image = Image.new("RGBA", image_size, (0, 0, 0, 0))
        match ui_type:
            case "default":
                pass
            case "sakura":
                margin = 7
                alpha_ratio = 0.4
                overlay_tl = Image.open(os_path.join(os_path.dirname(os_path.dirname(os_path.dirname(__file__))), "img", "overlay_tl_sakura.png"))
                overlay_br = Image.open(os_path.join(os_path.dirname(os_path.dirname(os_path.dirname(__file__))), "img", "overlay_br_sakura.png"))
                if overlay_tl.size[1] > image_size[1]:
                    overlay_tl = overlay_tl.resize((image_size[1]-margin, image_size[1]-margin))
                if overlay_br.size[1] > image_size[1]:
                    overlay_br = overlay_br.resize((image_size[1]-margin, image_size[1]-margin))

                alpha = overlay_tl.getchannel("A")
                alpha = alpha.point(lambda x: x * alpha_ratio)
                overlay_tl.putalpha(alpha)
                alpha = overlay_br.getchannel("A")
                alpha = alpha.point(lambda x: x * alpha_ratio)
                overlay_br.putalpha(alpha)
                decoration_image.paste(overlay_tl, (margin, margin))
                decoration_image.paste(overlay_br, (image_size[0]-overlay_br.size[0]-margin, image_size[1]-overlay_br.size[1]-margin))
        return decoration_image

    def createTextboxSmall(self, text, language, text_color, base_width, base_height, font_size):
        font_family = self.LANGUAGES.get(language, "NotoSansJP-Regular")
        img = Image.new("RGBA", (base_width, base_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(os_path.join(os_path.dirname(os_path.dirname(os_path.dirname(__file__))), "fonts", f"{font_family}.ttf"), font_size)
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
        ui_size = self.getUiSize()
        height = ui_size["height"]
        width = ui_size["width"]
        font_size = ui_size["font_size"]

        ui_colors = self.getUiColors(ui_type)
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

        decoration_image = self.createDecorationImage(ui_type, img.size)
        background = Image.alpha_composite(background, decoration_image)
        img = Image.alpha_composite(background, img)
        return img

    def createOverlayImage(self, message, your_language, ui_type="default"):
        ui_size = self.getUiSize()
        height = ui_size["height"]
        width = ui_size["width"]
        font_size = ui_size["font_size"]

        ui_colors = self.getUiColors(ui_type)
        text_color = ui_colors["text_color"]
        background_color = ui_colors["background_color"]
        background_outline_color = ui_colors["background_outline_color"]

        img = self.createTextboxSmall(message, your_language, text_color, width, height, font_size)

        background = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(background)
        draw.rounded_rectangle([(0, 0), img.size], radius=30, fill=background_color, outline=background_outline_color, width=5)

        decoration_image = self.createDecorationImage(ui_type, img.size)
        background = Image.alpha_composite(background, decoration_image)
        img = Image.alpha_composite(background, img)
        return img