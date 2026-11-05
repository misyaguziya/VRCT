"""issue #121: 翻訳が空文字だと大ログの描画が 0 除算で落ち、直近5件を描き直す
ため後続のメッセージも巻き込んで失敗していた。"""

import unittest

from models.overlay.overlay_image import OverlayImage


class TestLargeLogEmptyText(unittest.TestCase):
    def test_empty_translation_does_not_break_following_messages(self) -> None:
        overlay_image = OverlayImage()
        for translation in ["", "hola", "adios"]:
            overlay_image.createOverlayImageLargeLog(
                "receive", "hello", "English", [translation], ["Spanish"], [], [[]]
            )


if __name__ == "__main__":
    unittest.main()
