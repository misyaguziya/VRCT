"""Generates PIL Image objects for VR overlays, including text rendering for different languages and log styles."""
from datetime import datetime
from os import path as os_path
from typing import Any, Dict, List, Optional, Tuple # Added Any, Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont

try:
    from utils import errorLogging
except ImportError:
    import traceback
    def errorLogging() -> None: # Added type hint for consistency
        """Basic error logging if the main utils.errorLogging is not available."""
        print(traceback.format_exc())

class OverlayImage:
    """
    Handles the creation of images for VR overlays, managing text,
    styles, and message history for logs.
    """
    # Font mapping for different languages. Assumes Noto Sans family.
    LANGUAGES: Dict[str, str] = {
        "Japanese": "NotoSansJP-Regular",
        "Korean": "NotoSansKR-Regular",
        "Chinese Simplified": "NotoSansSC-Regular",
        "Chinese Traditional": "NotoSansTC-Regular",
        "English": "NotoSans-Regular", # Added for completeness, adjust if a different default is used
        # Add other languages and their corresponding Noto Sans font names here
    }
    DEFAULT_FONT = "NotoSans-Regular" # Default font if a specific language font is not found

    def __init__(self) -> None:
        """
        Initializes the OverlayImage creator.
        `message_log` stores history for the large log display.
        Structure of each log entry:
            "message_type": str (e.g., "send", "receive")
            "message": str (original message)
            "your_language": str (language of the original message)
            "translation": Optional[str] (translated message)
            "target_language": Optional[str] (language of the translation)
            "datetime": str (formatted time of the message)
        """
        self.message_log: List[Dict[str, Any]] = []

    @staticmethod
    def concatenateImagesVertically(img1: Image.Image, img2: Image.Image, margin: int = 0) -> Image.Image:
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
    def getUiSizeSmallLog() -> Dict[str, int]:
        """Returns UI size parameters for the small log overlay."""
        return {
            "width": 3840,  # Base width for text rendering calculations
            "height": 92,   # Target height for a single line of text, influences font size
            "font_size": 92, # Default font size
        }

    @staticmethod
    def getUiColorSmallLog() -> Dict[str, Tuple[int, int, int]]:
        colors = {
            "background_color": (41, 42, 45),
            "background_outline_color": (41, 42, 45),
            "text_color": (223, 223, 223)
        }
        return colors

    def createTextboxSmallLog(self, text:str, language:str, text_color:Tuple[int, int, int], base_width:int, base_height:int, font_size:int) -> Image.Image:
        """
        Creates a textbox image for the small log with given text and language.
        Dynamically adjusts height based on text content.

        Args:
            text: The message text.
            language: The language of the text, used for font selection.
            text_color: RGB tuple for text color.
            base_width: The target width of the textbox.
            base_height: Initial height, will be adjusted. (Note: base_height seems unused for final image height)
            font_size: The font size.

        Returns:
            A PIL Image.Image object for the textbox.
        """
        font_family = self.LANGUAGES.get(language, self.DEFAULT_FONT)
        # Initial image for text size calculation, transparent
        img_calc = Image.new("RGBA", (base_width, font_size * 2), (0, 0, 0, 0)) # Temp height
        draw_calc = ImageDraw.Draw(img_calc)

        font: ImageFont.FreeTypeFont
        try:
            # Path relative to this file's location, then up to project root, then to fonts
            font_dir = os_path.join(os_path.dirname(__file__), "..", "..", "..", "fonts")
            font_path = os_path.join(font_dir, f"{font_family}.ttf")
            font = ImageFont.truetype(font_path, font_size)
        except IOError: # More specific exception for file issues
            errorLogging(f"Failed to load font: {font_family} from {font_path}. Falling back to default.")
            default_font_path = os_path.join(font_dir, f"{self.DEFAULT_FONT}.ttf")
            try:
                font = ImageFont.truetype(default_font_path, font_size)
            except IOError:
                errorLogging(f"Failed to load default font: {self.DEFAULT_FONT}. Using PIL default.")
                font = ImageFont.load_default() # PIL's built-in fallback
        except Exception as e: # Catch other font loading errors
            errorLogging(f"An unexpected error occurred while loading font {font_family}: {e}")
            font = ImageFont.load_default()


        # Calculate required lines and height
        final_text = text
        if text: # Avoid division by zero if text is empty
            # Heuristic for character width; TrueType font metrics are complex.
            # Using textbbox for more accurate width estimation if available and reliable.
            # text_bbox = draw_calc.textbbox((0,0), text, font=font)
            # text_width_calc = text_bbox[2] - text_bbox[0]
            text_width_calc = draw_calc.textlength(text, font=font)

            avg_char_width = text_width_calc / len(text) if len(text) > 0 else font_size
            if avg_char_width == 0: avg_char_width = font_size # Avoid division by zero for very thin chars

            # character_line_num: how many characters fit in one line approximately
            # Subtracting a few characters for padding/margin.
            character_line_num = max(1, int((base_width / avg_char_width) - 2)) 

            if len(text) > character_line_num:
                wrapped_lines = [text[i:i + character_line_num] for i in range(0, len(text), character_line_num)]
                final_text = "\n".join(wrapped_lines)
            else:
                wrapped_lines = [text]

            num_lines = len(wrapped_lines)
            # Estimate height: num_lines * (font_size * line_spacing_factor) + vertical_padding
            # Using font.getsize_multiline or textbbox for height is more accurate
            # For simplicity, using font_size * num_lines + padding
            text_height = font_size * num_lines + 20 # 20 for padding
        else: # Empty text
            text_height = font_size + 20 


        img = Image.new("RGBA", (base_width, text_height), (0, 0, 0, 0)) # Final image with calculated height
        draw = ImageDraw.Draw(img)

        text_x = base_width // 2
        text_y = text_height // 2
        draw.text((text_x, text_y), final_text, fill=text_color, anchor="mm", stroke_width=0, font=font, align="center")
        return img

    def createOverlayImageSmallLog(self, message:str, your_language:str, translation:str="", target_language:Optional[str]=None) -> Image.Image:
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
    def getUiSizeLargeLog() -> Dict[str, int]:
        """Returns UI size parameters for the large log overlay."""
        return {
            "width": 960,       # Base width for text rendering
            "font_size_large": 30,
            "font_size_small": 20,
            "margin": 25,       # Margin around the entire log block
            "radius": 25,       # Corner radius for the background
            "padding": 10,      # Padding within text boxes
            "clause_margin": 20 # Margin between log entries
        }

    @staticmethod
    def getUiColorLargeLog() -> Dict[str, Tuple[int, int, int]]:
        return {
            "background_color": (41, 42, 45),
            "background_outline_color": (41, 42, 45),
            "text_color_large": (223, 223, 223),
            "text_color_small": (190, 190, 190),
            "text_color_send": (97, 151, 180),
            "text_color_receive": (168, 97, 180),
            "text_color_time": (120, 120, 120)
        }

    def createTextImageLargeLog(self, message_type: str, size_category: str, text: str, language: str) -> Image.Image:
        """
        Creates a text image for a part of the large log (e.g., original message or translation).

        Args:
            message_type: "send" or "receive", determines alignment and color.
            size_category: "large" or "small", determines font size and color.
            text: The text content.
            language: Language of the text for font selection.

        Returns:
            A PIL Image.Image object for the text block.
        """
        ui_size = self.getUiSizeLargeLog()
        font_size = ui_size["font_size_large"] if size_category == "large" else ui_size["font_size_small"]
        
        # Determine text color based on size_category, not message_type for main text.
        # Message type specific colors are usually for accents or headers.
        text_color_map = self.getUiColorLargeLog()
        text_color = text_color_map.get(f"text_color_{size_category}", text_color_map["text_color_large"]) # Fallback to large

        anchor = "lm" if message_type == "receive" else "rm"
        text_x = 0 if message_type == "receive" else ui_size["width"]
        align = "left" if message_type == "receive" else "right"
        font_family = self.LANGUAGES.get(language, self.DEFAULT_FONT)

        # Font loading logic (similar to createTextboxSmallLog)
        font: ImageFont.FreeTypeFont
        try:
            font_dir = os_path.join(os_path.dirname(__file__), "..", "..", "..", "fonts")
            font_path = os_path.join(font_dir, f"{font_family}.ttf")
            font = ImageFont.truetype(font_path, font_size)
        except IOError:
            errorLogging(f"Failed to load font: {font_family} from {font_path}. Falling back to default.")
            default_font_path = os_path.join(font_dir, f"{self.DEFAULT_FONT}.ttf")
            try:
                font = ImageFont.truetype(default_font_path, font_size)
            except IOError:
                errorLogging(f"Failed to load default font: {self.DEFAULT_FONT}. Using PIL default.")
                font = ImageFont.load_default()
        except Exception as e:
            errorLogging(f"An unexpected error occurred while loading font {font_family}: {e}")
            font = ImageFont.load_default()

        # Text wrapping and height calculation (similar to createTextboxSmallLog)
        final_text = text
        if text:
            img_calc = Image.new("RGBA", (1,1), (0,0,0,0)) # Minimal image for draw object
            draw_calc = ImageDraw.Draw(img_calc)
            text_width_calc = draw_calc.textlength(text, font=font)
            avg_char_width = text_width_calc / len(text) if len(text) > 0 else font_size
            if avg_char_width == 0: avg_char_width = font_size
            
            character_line_num = max(1, int((ui_size["width"] / avg_char_width) -1)) # -1 for some buffer
            
            if len(text) > character_line_num:
                wrapped_lines = [text[i:i + character_line_num] for i in range(0, len(text), character_line_num)]
                final_text = "\n".join(wrapped_lines)
            else:
                wrapped_lines = [text]
            
            num_lines = len(wrapped_lines)
            text_height = font_size * num_lines + ui_size["padding"]
        else:
            text_height = font_size + ui_size["padding"]


        img = Image.new("RGBA", (ui_size["width"], text_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        text_y = text_height // 2 # Anchor mm vertically centers this
        draw.multiline_text((text_x, text_y), final_text, fill=text_color, anchor=anchor+"m", stroke_width=0, font=font, align=align) # anchor uses 'm' for middle
        return img

    def createTextImageMessageType(self, message_type:str, date_time:str) -> Image.Image:
        """Creates an image strip showing the message type (Send/Receive) and timestamp."""
        ui_size = self.getUiSizeLargeLog()
        font_size = ui_size["font_size_small"]
        ui_padding = ui_size["padding"] # Vertical padding for this strip

        ui_colors = self.getUiColorLargeLog()
        text_color = ui_colors.get(f"text_color_{message_type}", ui_colors["text_color_small"])
        text_color_time = ui_colors["text_color_time"]

        anchor_type = "lm" if message_type == "receive" else "rm" # Horizontal anchor for type text
        anchor_time = "lm" if message_type == "receive" else "rm" # Horizontal anchor for time text
        
        text_content = "Receive" if message_type == "receive" else "Send"

        # Font loading (default to NotoSans-Regular if JP fails or is not needed)
        font: ImageFont.FreeTypeFont
        try:
            font_dir = os_path.join(os_path.dirname(__file__), "..", "..", "..", "fonts")
            # Using a generic font for this part, as language is not the primary content
            font_path = os_path.join(font_dir, f"{self.DEFAULT_FONT}.ttf") 
            font = ImageFont.truetype(font_path, font_size)
        except IOError:
            errorLogging(f"Failed to load font for message type: {self.DEFAULT_FONT}. Using PIL default.")
            font = ImageFont.load_default()
        except Exception as e:
            errorLogging(f"An unexpected error occurred while loading font for message type: {e}")
            font = ImageFont.load_default()

        # Calculate dimensions
        text_height = font_size + ui_padding
        
        # Create image
        img = Image.new("RGBA", (ui_size["width"], text_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        text_y = text_height // 2 # Vertically centered
        
        # Draw time and type based on message_type alignment
        if message_type == "receive":
            # Time on left, Type next to it
            time_bbox = draw.textbbox((0, text_y), date_time, font=font, anchor=anchor_time+"m")
            draw.text((0, text_y), date_time, fill=text_color_time, font=font, anchor=anchor_time+"m")
            
            type_text_x = time_bbox[2] + ui_size["padding"] # Add padding between time and type
            draw.text((type_text_x, text_y), text_content, fill=text_color, font=font, anchor="lm") # type always lm from time
        else: # "send"
            # Type on right, Time to its left
            type_bbox = draw.textbbox((ui_size["width"], text_y), text_content, font=font, anchor=anchor_type+"m")
            draw.text((ui_size["width"], text_y), text_content, fill=text_color, font=font, anchor=anchor_type+"m")

            time_text_x = type_bbox[0] - ui_size["padding"]
            draw.text((time_text_x, text_y), date_time, fill=text_color_time, font=font, anchor="rm") # time rm from type

        return img

    def createTextboxLargeLog(self, message_type:str, message:str, your_language:str, translation:Optional[str], target_language:Optional[str], date_time:str) -> Image.Image:
        message_type_img = self.createTextImageMessageType(message_type, date_time)
        if translation and target_language:
            img = self.createTextImageLargeLog(message_type, "small", message, your_language)
            translation_img = self.createTextImageLargeLog(message_type, "large", translation, target_language)
            img = self.concatenateImagesVertically(img, translation_img)
        else:
            img = self.createTextImageLargeLog(message_type, "large", message, your_language)
        return self.concatenateImagesVertically(message_type_img, img)

    def createOverlayImageLargeLog(self, message_type:str, message:str, your_language:str, translation:str="", target_language:Optional[str]=None) -> Image.Image:
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