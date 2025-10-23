from os import path as os_path
from datetime import datetime
from typing import Tuple, List, Optional
from PIL import Image, ImageDraw, ImageFont
try:
    from utils import errorLogging
except ImportError:
    def errorLogging():
        import traceback
        print(traceback.format_exc())

class OverlayImage:
    LANGUAGES = {
        "Default": "NotoSansJP-Regular.ttf",
        "Japanese": "NotoSansJP-Regular.ttf",
        "Korean": "NotoSansKR-Regular.ttf",
        "Chinese Simplified": "NotoSansSC-Regular.ttf",
        "Chinese Traditional": "NotoSansTC-Regular.ttf",
    }

    def __init__(self, root_path: Optional[str] = None) -> None:
        """Overlay image helper.

        Args:
            root_path: optional project root to resolve bundled fonts. If omitted,
                defaults to repository `fonts` directory.
        """
        self.message_log: List[dict] = []
        # PyInstallerでビルドされた場合のパス
        if  root_path and os_path.exists(os_path.join(root_path, "_internal", "fonts")):
            self.root_path = os_path.join(root_path, "_internal", "fonts")
        # src-pythonフォルダから直接実行している場合のパス
        elif os_path.exists(os_path.join(os_path.dirname(__file__), "models", "overlay", "fonts")):
            self.root_path = os_path.join(os_path.dirname(__file__), "models", "overlay", "fonts")
        # overlayフォルダから直接実行している場合のパス
        elif os_path.exists(os_path.join(os_path.dirname(__file__), "fonts")):
            self.root_path = os_path.join(os_path.dirname(__file__), "fonts")
        else:
            raise FileNotFoundError("Font directory not found.")
        # Simple in-memory font cache to avoid repeated truetype loading cost.
        self._font_cache = {}

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

    def _get_font(self, font_family: str, size: int) -> ImageFont.FreeTypeFont:
        font_path = os_path.join(self.root_path, font_family)
        key = (font_path, size)
        if key not in self._font_cache:
            self._font_cache[key] = ImageFont.truetype(font_path, size)
        return self._font_cache[key]

    def createTextboxSmallLog(self, text: str, language: str, text_color: Tuple[int, int, int], base_width: int, base_height: int, font_size: int) -> Image:
        if text is None:
            text = ""
        font_family = self.LANGUAGES.get(language, self.LANGUAGES["Default"])
        font = self._get_font(font_family, font_size)

        # Initial image for width measurement
        img_tmp = Image.new("RGBA", (base_width, base_height), (0, 0, 0, 0))
        draw_tmp = ImageDraw.Draw(img_tmp)
        try:
            text_width = draw_tmp.textlength(text, font) if len(text) > 0 else 1
            character_width = max(1, text_width // max(1, len(text)))
            character_line_num = int((base_width // character_width) - 12)
            if len(text) > character_line_num and character_line_num > 0:
                text = "\n".join([text[i:i + character_line_num] for i in range(0, len(text), character_line_num)])
        except Exception:
            errorLogging()
        lines = text.split("\n") if text else [""]
        text_height = font_size * (len(lines) + 1) + 20
        img = Image.new("RGBA", (base_width, text_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        text_x = base_width // 2
        text_y = text_height // 2
        draw.text((text_x, text_y), text, text_color, anchor="mm", stroke_width=0, font=font, align="center")
        return img

    def renderRubyBlock(self, transliteration: List[dict], language: str, base_width: int, base_font_size: int, ruby_font_scale: float, ruby_line_spacing: int, text_color: Tuple[int, int, int]) -> Optional[Image.Image]:
        # Build romaji and hiragana lines.
        romaji_line = " ".join([t.get("hepburn", "") for t in transliteration if t.get("hepburn")])
        hira_line = " ".join([t.get("hira", "") for t in transliteration if t.get("hira")])
        if not romaji_line and not hira_line:
            return None
        font_family = self.LANGUAGES.get(language, self.LANGUAGES["Default"])
        ruby_size = max(1, int(base_font_size * ruby_font_scale))
        font_ruby = self._get_font(font_family, ruby_size)
        # Symmetric outer padding so ruby block has breathing room top/bottom
        outer_padding = 10
        # Measure widths to center lines independently.
        img_tmp = Image.new("RGBA", (base_width, ruby_size * 2 + ruby_line_spacing + outer_padding * 2), (0, 0, 0, 0))
        draw_tmp = ImageDraw.Draw(img_tmp)
        romaji_width = draw_tmp.textlength(romaji_line, font_ruby) if romaji_line else 0
        hira_width = draw_tmp.textlength(hira_line, font_ruby) if hira_line else 0
        romaji_x = (base_width - romaji_width) // 2
        hira_x = (base_width - hira_width) // 2
        # Construct final ruby image with symmetric padding
        ruby_height = outer_padding + ruby_size * (2 if hira_line and romaji_line else 1) + (ruby_line_spacing if hira_line and romaji_line else 0) + outer_padding
        ruby_img = Image.new("RGBA", (base_width, ruby_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(ruby_img)
        current_y = outer_padding + ruby_size // 2
        if romaji_line:
            draw.text((romaji_x + romaji_width // 2, current_y), romaji_line, text_color, anchor="mm", font=font_ruby)
            current_y += ruby_size + (ruby_line_spacing if hira_line else 0)
        if hira_line:
            draw.text((hira_x + hira_width // 2, current_y), hira_line, text_color, anchor="mm", font=font_ruby)
        return ruby_img

    def createTextboxSmallLogWithRubyTokens(self, message: str, transliteration: List[dict], language: str, text_color: Tuple[int, int, int], base_width: int, font_size: int, ruby_font_scale: float, ruby_line_spacing: int, ruby_original_spacing: int) -> Image:
        """Render a single textbox (original message) with per-token centered ruby (romaji above hiragana) over each original token.

        Fallback: if wrapping would occur (message too wide) or tokens mismatch, revert to block-level ruby (renderRubyBlock + createTextboxSmallLog).
        """
        if not message or not transliteration:
            return self.createTextboxSmallLog(message, language, text_color, base_width, self.getUiSizeSmallLog()["height"], font_size)

        # Obtain font instances
        font_family = self.LANGUAGES.get(language, self.LANGUAGES["Default"])
        font_orig = self._get_font(font_family, font_size)
        ruby_size = max(1, int(font_size * ruby_font_scale))
        font_ruby = self._get_font(font_family, ruby_size)

        # Token width measurement
        draw_tmp_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        draw_tmp = ImageDraw.Draw(draw_tmp_img)
        token_infos = []
        total_width = 0
        for tok in transliteration:
            orig = tok.get("orig", "")
            if not orig:
                continue
            hira = tok.get("hira", "")
            romaji = tok.get("hepburn", "")
            orig_w = max(1, int(draw_tmp.textlength(orig, font_orig)))
            hira_w = max(0, int(draw_tmp.textlength(hira, font_ruby))) if hira else 0
            romaji_w = max(0, int(draw_tmp.textlength(romaji, font_ruby))) if romaji else 0
            layout_w = max(orig_w, hira_w, romaji_w)  # allocate width so ruby lines never overflow neighboring token
            token_infos.append((orig, hira, romaji, layout_w))
            total_width += layout_w

        if not token_infos:
            # Fallback
            ruby_block = self.renderRubyBlock(transliteration, language, base_width, font_size, ruby_font_scale, ruby_line_spacing, text_color)
            base_img = self.createTextboxSmallLog(message, language, text_color, base_width, self.getUiSizeSmallLog()["height"], font_size)
            if ruby_block:
                return self.concatenateImagesVertically(ruby_block, base_img)
            return base_img

        # Simple wrapping detection: if total width exceeds base_width * 0.9 → fallback
        if total_width > base_width * 0.9:
            ruby_block = self.renderRubyBlock(transliteration, language, base_width, font_size, ruby_font_scale, ruby_line_spacing, text_color)
            base_img = self.createTextboxSmallLog(message, language, text_color, base_width, self.getUiSizeSmallLog()["height"], font_size)
            if ruby_block:
                return self.concatenateImagesVertically(ruby_block, base_img)
            return base_img

        # Compute left start for centering complete line
        start_x = (base_width - total_width) // 2
        # Vertical positioning
        # Symmetric outer padding: make top padding equal to bottom padding (previously top was 4, bottom ~10)
        outer_padding = 10  # uniform top & bottom padding for visual balance
        ruby_lines_count = 0
        has_romaji_any = any(r for (_, _, r, _) in token_infos)
        has_hira_any = any(h for (_, h, _, _) in token_infos)
        if has_romaji_any:
            ruby_lines_count += 1
        if has_hira_any:
            ruby_lines_count += 1
        # Height calculation (replace asymmetric 4/10 with symmetric outer_padding)
        ruby_block_height = ruby_lines_count * ruby_size + (ruby_line_spacing if ruby_lines_count == 2 else 0)
        total_height = outer_padding + ruby_block_height + ruby_original_spacing + font_size + outer_padding
        img = Image.new("RGBA", (base_width, total_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Y centers
        current_y = outer_padding + ruby_size // 2
        romaji_y = current_y if has_romaji_any else None
        hira_y = None
        if has_romaji_any and has_hira_any:
            hira_y = romaji_y + ruby_size + ruby_line_spacing
        elif has_hira_any:
            hira_y = current_y

        orig_y = outer_padding + ruby_block_height + ruby_original_spacing + font_size // 2

        # Draw tokens sequentially
        cursor_x = start_x
        for orig, hira, romaji, w in token_infos:
            token_center_x = cursor_x + w // 2
            if romaji_y is not None and romaji:
                draw.text((token_center_x, romaji_y), romaji, text_color, anchor="mm", font=font_ruby)
            if hira_y is not None and hira:
                draw.text((token_center_x, hira_y), hira, text_color, anchor="mm", font=font_ruby)
            draw.text((token_center_x, orig_y), orig, text_color, anchor="mm", font=font_orig)
            cursor_x += w
        return img

    def createOverlayImageSmallLog(self, message: str, your_language: str, translation: List[str] = [], target_language: List[str] = [], transliteration_message: List[dict] = [], transliteration_translation: List[List[dict]] = [], ruby_font_scale: float = 0.5, ruby_line_spacing: int = 4) -> Image:
        # UI設定を取得
        ui_size = self.getUiSizeSmallLog()
        width, height, font_size = ui_size["width"], ui_size["height"], ui_size["font_size"]

        ui_colors = self.getUiColorSmallLog()
        text_color = ui_colors["text_color"]
        background_color = ui_colors["background_color"]
        background_outline_color = ui_colors["background_outline_color"]

        # テキストボックス画像のリストを作成
        textbox_images = []

        # 翻訳がある場合
        # Use improved per-token placement if possible; else fallback to previous block approach.
        ruby_original_spacing = 2  # Narrow vertical gap between hiragana block and original text.
        if translation and target_language:
            if message:
                base_msg_img = self.createTextboxSmallLog(message, your_language, text_color, width, height, font_size)
                textbox_images.append(base_msg_img)
            for trans, lang, translite in zip(translation, target_language, transliteration_translation):
                try:
                    trans_img = self.createTextboxSmallLogWithRubyTokens(
                        trans,
                        translite,
                        lang,
                        text_color,
                        width,
                        font_size,
                        ruby_font_scale,
                        ruby_line_spacing,
                        ruby_original_spacing,
                    )
                except Exception:
                    errorLogging()
                    trans_img = self.createTextboxSmallLog(trans, lang, text_color, width, height, font_size)
                textbox_images.append(trans_img)
        else:
            # 翻訳無しモード
            if message and transliteration_message:
                try:
                    base_msg_img = self.createTextboxSmallLogWithRubyTokens(
                        message,
                        transliteration_message,
                        your_language,
                        text_color,
                        width,
                        font_size,
                        ruby_font_scale,
                        ruby_line_spacing,
                        ruby_original_spacing,
                    )
                except Exception:
                    errorLogging()
                    base_msg_img = self.createTextboxSmallLog(message, your_language, text_color, width, height, font_size)
                    try:
                        ruby_img = self.renderRubyBlock(transliteration_message, your_language, width, font_size, ruby_font_scale, ruby_line_spacing, text_color)
                        if ruby_img is not None:
                            base_msg_img = self.concatenateImagesVertically(ruby_img, base_msg_img)
                    except Exception:
                        errorLogging()
            else:
                base_msg_img = self.createTextboxSmallLog(message, your_language, text_color, width, height, font_size)
            textbox_images.append(base_msg_img)

        # すべてのテキストボックスを縦に結合
        img = textbox_images[0]
        for textbox_img in textbox_images[1:]:
            img = self.concatenateImagesVertically(img, textbox_img)

        # 画像周囲にUIパディングを追加して、文字が端に張り付かないようにする
        ui_outer_padding = 50
        img = self.addImageMargin(img, ui_outer_padding, ui_outer_padding, ui_outer_padding, ui_outer_padding, (0, 0, 0, 0))

        # 角丸背景を作成
        background = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(background)
        draw.rounded_rectangle([(0, 0), img.size], radius=50, fill=background_color, outline=background_outline_color, width=5)

        # 背景とテキストを合成
        img = Image.alpha_composite(background, img)
        return img

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

    def createTextImageLargeLog(self, message_type: str, size: str, text: str, language: str) -> Image:
        ui_size = self.getUiSizeLargeLog()
        font_size = ui_size["font_size_large"] if size == "large" else ui_size["font_size_small"]
        text_color = self.getUiColorLargeLog()[f"text_color_{size}"]
        anchor = "lm" if message_type == "receive" else "rm"
        text_x = 0 if message_type == "receive" else ui_size["width"]
        align = "left" if message_type == "receive" else "right"
        font_family = self.LANGUAGES.get(language, self.LANGUAGES["Default"])

        img = Image.new("RGBA", (0, 0), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        font_path = os_path.join(self.root_path, font_family)
        font = ImageFont.truetype(font_path, font_size)

        # 改行を含んだtextの最大の文字数を計算する
        text_width = max(draw.textlength(line, font) for line in text.split("\n"))
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

    def createTextboxLargeLogWithRubyTokens(self, message_type: str, size: str, message: str, transliteration: List[dict], language: str, ruby_font_scale: float, ruby_line_spacing: int) -> Image:
        """Render a large-log textbox with per-token centered ruby above each original token.

        Falls back to block-level ruby if message wraps or tokens mismatch.
        """
        ui_size = self.getUiSizeLargeLog()
        font_size = ui_size["font_size_large"] if size == "large" else ui_size["font_size_small"]
        text_color = self.getUiColorLargeLog()[f"text_color_{size}"]
        font_family = self.LANGUAGES.get(language, self.LANGUAGES["Default"])
        font_orig = self._get_font(font_family, font_size)
        ruby_size = max(1, int(font_size * ruby_font_scale))
        font_ruby = self._get_font(font_family, ruby_size)

        # Simple guard
        if not message or not transliteration:
            return self.createTextImageLargeLog(message_type, size, message, language)

        # Reject multiline for per-token layout; fallback to block ruby
        if "\n" in message:
            ruby_block = self.renderRubyBlock(transliteration, language, ui_size["width"], font_size, ruby_font_scale, ruby_line_spacing, text_color)
            base_img = self.createTextImageLargeLog(message_type, size, message, language)
            if ruby_block is not None:
                return self.concatenateImagesVertically(ruby_block, base_img)
            return base_img

        # Measure token widths
        draw_tmp_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        draw_tmp = ImageDraw.Draw(draw_tmp_img)
        token_infos = []
        total_width = 0
        for tok in transliteration:
            orig = tok.get("orig", "")
            if not orig:
                continue
            hira = tok.get("hira", "")
            romaji = tok.get("hepburn", "")
            orig_w = max(1, int(draw_tmp.textlength(orig, font_orig)))
            hira_w = max(0, int(draw_tmp.textlength(hira, font_ruby))) if hira else 0
            romaji_w = max(0, int(draw_tmp.textlength(romaji, font_ruby))) if romaji else 0
            layout_w = max(orig_w, hira_w, romaji_w)
            token_infos.append((orig, hira, romaji, layout_w))
            total_width += layout_w

        # Fallback if nothing to render or would overflow
        base_width = ui_size["width"]
        if not token_infos or total_width > base_width * 0.9:
            ruby_block = self.renderRubyBlock(transliteration, language, base_width, font_size, ruby_font_scale, ruby_line_spacing, text_color)
            base_img = self.createTextImageLargeLog(message_type, size, message, language)
            if ruby_block is not None:
                return self.concatenateImagesVertically(ruby_block, base_img)
            return base_img

        # Determine start_x according to message type (left for receive, right-align for send)
        start_x = 0 if message_type == "receive" else (base_width - total_width)

        # Vertical layout
        outer_padding = 10
        has_romaji_any = any(r for (_, _, r, _) in token_infos)
        has_hira_any = any(h for (_, h, _, _) in token_infos)
        ruby_lines_count = (1 if has_romaji_any else 0) + (1 if has_hira_any else 0)
        ruby_block_height = ruby_lines_count * ruby_size + (ruby_line_spacing if ruby_lines_count == 2 else 0)
        total_height = outer_padding + ruby_block_height + font_size + outer_padding
        img = Image.new("RGBA", (base_width, total_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # y positions
        current_y = outer_padding + ruby_size // 2
        romaji_y = current_y if has_romaji_any else None
        hira_y = None
        if has_romaji_any and has_hira_any:
            hira_y = romaji_y + ruby_size + ruby_line_spacing
        elif has_hira_any:
            hira_y = current_y
        orig_y = outer_padding + ruby_block_height + font_size // 2

        # Draw tokens
        cursor_x = start_x
        for orig, hira, romaji, w in token_infos:
            token_center_x = cursor_x + w // 2
            if romaji_y is not None and romaji:
                draw.text((token_center_x, romaji_y), romaji, text_color, anchor="mm", font=font_ruby)
            if hira_y is not None and hira:
                draw.text((token_center_x, hira_y), hira, text_color, anchor="mm", font=font_ruby)
            draw.text((token_center_x, orig_y), orig, text_color, anchor="mm", font=font_orig)
            cursor_x += w
        return img

    def createTextImageMessageType(self, message_type: str, date_time: str) -> Image:
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

        font_path = os_path.join(self.root_path, self.LANGUAGES["Default"])
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

    def createTextboxLargeLog(self, message_type: str, message: Optional[str] = None, your_language: Optional[str] = None, translation: List[str] = [], target_language: List[str] = [], date_time: Optional[str] = None, transliteration_message: Optional[List[dict]] = None, transliteration_translation: Optional[List[List[dict]]] = None, ruby_font_scale: float = 0.5, ruby_line_spacing: int = 4) -> Image:
        # テキスト画像のリストを作成
        images = [self.createTextImageMessageType(message_type, date_time)]

        # 翻訳がある場合
        if translation and target_language:
            # 元のメッセージがある場合は小さいサイズで追加
            if message is not None:
                small_img = self.createTextImageLargeLog(message_type, "small", message, your_language)
                images.append(small_img)

            # 翻訳をすべて大きいサイズで追加
            for trans, lang, translite in zip(translation, target_language, transliteration_translation):
                try:
                    large_img = self.createTextboxLargeLogWithRubyTokens(message_type, "large", trans, translite, lang, ruby_font_scale, ruby_line_spacing)
                except Exception:
                    errorLogging()
                    large_img = self.createTextImageLargeLog(message_type, "large", trans, lang)
                images.append(large_img)
        else:
            # 翻訳がない場合は元のメッセージのみ
            try:
                large_img = self.createTextboxLargeLogWithRubyTokens(message_type, "large", message, transliteration_message, your_language, ruby_font_scale, ruby_line_spacing)
            except Exception:
                errorLogging()
                large_img = self.createTextImageLargeLog(message_type, "large", message, your_language)
            images.append(large_img)

        # すべてのテキスト画像を縦に結合
        combined_img = images[0]
        for img in images[1:]:
            combined_img = self.concatenateImagesVertically(combined_img, img)

        return combined_img

    def createOverlayImageLargeLog(self, message_type: str, message: Optional[str] = None, your_language: Optional[str] = None, translation: List[str] = [], target_language: List[str] = [], transliteration_message: List[dict] = [], transliteration_translation: List[List[dict]] = [], ruby_font_scale: float = 0.5, ruby_line_spacing: int = 4) -> Image:
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
            "transliteration_message": transliteration_message,
            "transliteration_translation": transliteration_translation,
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
                log["datetime"],
                transliteration_message=log.get("transliteration_message", [{}]),
                transliteration_translation=log.get("transliteration_translation", [{}]),
                ruby_font_scale=ruby_font_scale,
                ruby_line_spacing=ruby_line_spacing,
            ) for log in self.message_log
            ]

        img = imgs[0]
        for i in imgs[1:]:
            img = self.concatenateImagesVertically(img, i, ui_clause_margin)
        img = self.addImageMargin(img, ui_margin, ui_margin, ui_margin, ui_margin, (0, 0, 0, 0))

        width, height = img.size
        background = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(background)
        draw.rounded_rectangle([(0, 0), (width, height)], radius=ui_radius, fill=background_color, outline=background_outline_color, width=5)
        img = Image.alpha_composite(background, img)
        return img

if __name__ == "__main__":
    overlay = OverlayImage()
    # Basic small log test (with translation list form)
    img = overlay.createOverlayImageSmallLog("Hello, World!", "English", ["こんにちは、世界！"], ["Japanese"], [], [[]])
    img.save("overlay_small.png")

    # Ruby small log test (Japanese original with transliteration tokens)
    ruby_tokens = [
        {"orig": "慮", "hira": "おもんぱか", "hepburn": "omonpaka"},
        {"orig": "る", "hira": "る", "hepburn": "ru"},
    ]
    # Ruby on original + ruby on translation example
    translation_tokens = [
        [
            {"orig": "慮", "hira": "おもんぱか", "hepburn": "omonpaka"},
            {"orig": "る", "hira": "る", "hepburn": "ru"},
        ],
        [
            {"orig": "慮", "hira": "おもんぱか", "hepburn": "omonpaka"},
            {"orig": "る", "hira": "る", "hepburn": "ru"},
        ],
        [
            {"orig": "慮", "hira": "おもんぱか", "hepburn": "omonpaka"},
            {"orig": "る", "hira": "る", "hepburn": "ru"},
        ]
    ]
    img_ruby = overlay.createOverlayImageSmallLog(
        "慮る",
        "Japanese",
        ["慮る", "慮る", "慮る"],
        ["Japanese", "Japanese", "Japanese"],
        transliteration_message=ruby_tokens,
        transliteration_translation=translation_tokens,
        ruby_font_scale=0.5,
        ruby_line_spacing=4,
    )
    img_ruby.save("overlay_small_ruby.png")

    # Large log tests (adjusted to pass translation/target_language as lists)
    img = overlay.createOverlayImageLargeLog("send", "Hello, World!", "English", ["こんにちは、世界！"], ["Japanese"], transliteration_message=[], transliteration_translation=[])
    img = overlay.createOverlayImageLargeLog("receive", "こんにちは、世界！", "Japanese", ["Hello, World!"], ["English"], transliteration_message=[
        {"orig": "慮", "hira": "おもんぱか", "hepburn": "omonpaka"},
        {"orig": "る", "hira": "る", "hepburn": "ru"},
    ], transliteration_translation=[
        [
            {"orig": "慮", "hira": "おもんぱか", "hepburn": "omonpaka"},
            {"orig": "る", "hira": "る", "hepburn": "ru"},
        ]
    ])
    long_en = "Hello, World!"
    long_jp = "こんにちは、世界！"
    img = overlay.createOverlayImageLargeLog("send", long_en, "English", [long_jp], ["Japanese"], transliteration_message=[
            {"orig": "慮", "hira": "おもんぱか", "hepburn": "omonpaka"},
            {"orig": "る", "hira": "る", "hepburn": "ru"},
        ], transliteration_translation=[[]])
    img = overlay.createOverlayImageLargeLog("receive", long_jp, "Japanese", [long_en], ["English"], transliteration_message=[], transliteration_translation=[
        [
            {"orig": "慮", "hira": "おもんぱか", "hepburn": "omonpaka"},
            {"orig": "る", "hira": "る", "hepburn": "ru"},
        ]
    ])
    img = overlay.createOverlayImageLargeLog("send", "Hello, World!", "English", ["こんにちは、世界！"], ["Japanese"], transliteration_message=[
            {"orig": "慮", "hira": "おもんぱか", "hepburn": "omonpaka"},
            {"orig": "る", "hira": "る", "hepburn": "ru"},
    ], transliteration_translation=[[]])

    img = overlay.createOverlayImageLargeLog("receive", "こんにちは、世界！", "Japanese", ["Hello, World!"], ["English"], transliteration_message=[
            {"orig": "こんにちは", "hira": "こんにちは", "hepburn": "konnichiha"},
            {"orig": "世界", "hira": "sekai", "hepburn": "sekai"},
        ], transliteration_translation=[
        [
            {"orig": "慮", "hira": "おもんぱか", "hepburn": "omonpaka"},
            {"orig": "る", "hira": "る", "hepburn": "ru"},
        ]
    ])
    img = overlay.createOverlayImageLargeLog("send", long_en, "English", [long_jp], ["Japanese"], transliteration_message=[
        {"orig": "慮", "hira": "おもんぱか", "hepburn": "omonpaka"},
        {"orig": "る", "hira": "る", "hepburn": "ru"},
    ], transliteration_translation=[
        [
            {"orig": "慮", "hira": "おもんぱか", "hepburn": "omonpaka"},
            {"orig": "る", "hira": "る", "hepburn": "ru"},
        ]
    ])
    img = overlay.createOverlayImageLargeLog("receive", long_jp, "Japanese", [long_en, long_en, long_en], ["English", "English", "English"], transliteration_message=[
        {"orig": "慮", "hira": "おもんぱか", "hepburn": "omonpaka"},
        {"orig": "る", "hira": "る", "hepburn": "ru"},
    ], transliteration_translation=[
        [
            {"orig": "慮", "hira": "おもんぱか", "hepburn": "omonpaka"},
            {"orig": "る", "hira": "る", "hepburn": "ru"},
        ],
        [
            {"orig": "慮", "hira": "おもんぱか", "hepburn": "omonpaka"},
            {"orig": "る", "hira": "る", "hepburn": "ru"},
        ],
        [
            {"orig": "慮", "hira": "おもんぱか", "hepburn": "omonpaka"},
            {"orig": "る", "hira": "る", "hepburn": "ru"},
        ]
    ])
    img.save("overlay_large.png")