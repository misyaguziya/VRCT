from os import path as os_path
# from datetime import datetime
from typing import Tuple
from PIL import Image, ImageDraw, ImageFont

class OverlayImage:
    # TEXT_COLOR_LARGE = (223, 223, 223)
    # TEXT_COLOR_SMALL = (190, 190, 190)
    # TEXT_COLOR_SEND = (70, 161, 146)
    # TEXT_COLOR_RECEIVE = (220, 20, 60)
    # TEXT_COLOR_TIME = (120, 120, 120)
    # FONT_SIZE_LARGE = HEIGHT
    # FONT_SIZE_SMALL = int(FONT_SIZE_LARGE * 2 / 3)
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

    # def create_textimage(self, message_type, size, text, language):
    #     font_size = self.FONT_SIZE_LARGE if size == "large" else self.FONT_SIZE_SMALL
    #     text_color = self.TEXT_COLOR_LARGE if size == "large" else self.TEXT_COLOR_SMALL
    #     anchor = "lm" if message_type == "receive" else "rm"
    #     text_x = 0 if message_type == "receive" else self.WIDTH
    #     align = "left" if message_type == "receive" else "right"

    #     font_family = self.LANGUAGES.get(language, "NotoSansJP-Regular")
    #     img = Image.new("RGBA", (0, 0), (0, 0, 0, 0))
    #     draw = ImageDraw.Draw(img)
    #     font = ImageFont.truetype(os_path.join(os_path.dirname(__file__), "fonts", f"{font_family}.ttf"), font_size)
    #     # font = ImageFont.truetype(os_path.join("./fonts", f"{font_family}.ttf"), font_size)
    #     text_width = draw.textlength(text, font)
    #     character_width = text_width // len(text)
    #     character_line_num = int(self.WIDTH // character_width)
    #     if len(text) > character_line_num:
    #         text = "\n".join([text[i:i+character_line_num] for i in range(0, len(text), character_line_num)])

    #     n_num = len(text.split("\n")) - 1
    #     text_height =  int(font_size*(n_num+2))

    #     img = Image.new("RGBA", (self.WIDTH, text_height), (0, 0, 0, 0))
    #     draw = ImageDraw.Draw(img)

    #     text_y = text_height // 2

    #     draw.multiline_text((text_x, text_y), text, text_color, anchor=anchor, stroke_width=0, font=font, align=align)
    #     return img

    # def create_textimage_message_type(self, message_type):
    #     anchor = "lm" if message_type == "receive" else "rm"
    #     text = "Receive" if message_type == "receive" else "Send"
    #     text_color = self.TEXT_COLOR_RECEIVE if message_type == "receive" else self.TEXT_COLOR_SEND
    #     text_color_time = self.TEXT_COLOR_TIME

    #     now = datetime.now()
    #     formatted_time = now.strftime("%H:%M")
    #     font_size = self.FONT_SIZE_SMALL
    #     img = Image.new("RGBA", (0, 0), (0, 0, 0, 0))
    #     draw = ImageDraw.Draw(img)
    #     font = ImageFont.truetype(os_path.join(os_path.dirname(__file__), "fonts", "NotoSansJP-Regular.ttf"), font_size)
    #     # font = ImageFont.truetype(os_path.join("./fonts", "NotoSansJP-Regular.ttf"), font_size)
    #     text_height = font_size*2
    #     text_width = draw.textlength(formatted_time, font)
    #     character_width = text_width // len(formatted_time)
    #     img = Image.new("RGBA", (self.WIDTH, text_height), (0, 0, 0, 0))
    #     draw = ImageDraw.Draw(img)
    #     text_y = text_height // 2
    #     text_time_x = 0 if message_type == "receive" else self.WIDTH - (text_width + character_width)
    #     text_x = (text_width + character_width) if message_type == "receive" else self.WIDTH

    #     draw.text((text_time_x, text_y), formatted_time, text_color_time, anchor=anchor, stroke_width=0, font=font)
    #     draw.text((text_x, text_y), text, text_color, anchor=anchor, stroke_width=0, font=font)
    #     return img

    # def create_textbox(self, message_type, message, your_language, translation, target_language):
    #     message_type_img = self.create_textimage_message_type(message_type)
    #     if len(translation) > 0 and target_language is not None:
    #         img = self.create_textimage(message_type, "small", message, your_language)
    #         translation_img = self.create_textimage(message_type, "large",translation, target_language)
    #         img = self.concatenateImagesVertically(img, translation_img)
    #     else:
    #         img = self.create_textimage(message_type, "large", message, your_language)
    #     return self.concatenateImagesVertically(message_type_img, img)

    # def create_overlay_image_long(self, message_type, message, your_language, translation="", target_language=None):
    #     if len(self.log_data) > 10:
    #         self.log_data.pop(0)

    #     self.log_data.append(
    #         {
    #             "message_type":message_type,
    #             "message":message,
    #             "your_language":your_language,
    #             "translation":translation,
    #             "target_language":target_language,
    #         }
    #     )

    #     imgs = []
    #     for log in self.log_data:
    #         message_type = log["message_type"]
    #         message = log["message"]
    #         your_language = log["your_language"]
    #         translation = log["translation"]
    #         target_language = log["target_language"]
    #         img = self.create_textbox(message_type, message, your_language, translation, target_language)
    #         imgs.append(img)

    #     img = imgs[0]
    #     for i in imgs[1:]:
    #         img = self.concatenateImagesVertically(img, i)
    #     img = self.addImageMargin(img, 0, 20, 0, 20, (0, 0, 0, 0))

    #     width, height = img.size
    #     background = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    #     draw = ImageDraw.Draw(background)
    #     draw.rounded_rectangle([(0, 0), (width, height)], radius=15, fill=self.BACKGROUND_COLOR, outline=self.BACKGROUND_OUTLINE_COLOR, width=5)
    #     img = Image.alpha_composite(background, img)
    #     return img

    def getUiSize(self):
        return {
            "width": int(960*4),
            "height": int(23*4),
            "font_size": int(23*4),
        }

    def getUiColors(self, ui_type):
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

    def createDecorationImage(self, ui_type, image_size):
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

    def createTextboxShort(self, text, language, text_color, base_width, base_height, font_size):
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

    def createOverlayImageShort(self, message, your_language, translation="", target_language=None, ui_type="default"):
        ui_size = self.getUiSize()
        height = ui_size["height"]
        width = ui_size["width"]
        font_size = ui_size["font_size"]

        ui_colors = self.getUiColors(ui_type)
        text_color = ui_colors["text_color"]
        background_color = ui_colors["background_color"]
        background_outline_color = ui_colors["background_outline_color"]

        img = self.createTextboxShort(message, your_language, text_color, width, height, font_size)
        if len(translation) > 0 and target_language is not None:
            translation_img = self.createTextboxShort(translation, target_language, text_color, width, height, font_size)
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

        img = self.createTextboxShort(message, your_language, text_color, width, height, font_size)

        background = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(background)
        draw.rounded_rectangle([(0, 0), img.size], radius=30, fill=background_color, outline=background_outline_color, width=5)

        decoration_image = self.createDecorationImage(ui_type, img.size)
        background = Image.alpha_composite(background, decoration_image)
        img = Image.alpha_composite(background, img)
        return img