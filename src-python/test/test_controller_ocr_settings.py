"""OCR設定エンドポイントのテスト。

見ているのは2点。
1. 読み取り言語はOCRエンジンが対応しているものだけ受け付ける
   (VRCTが翻訳できる言語の全てをOCRできるわけではないので、ここで弾かないと
   「設定はできたのに何も読めない」状態になる)。
2. 設定変更が実行中のパイプラインへ渡される
   (以前はconfigに書くだけで、OFF→ONしない限り反映されなかった。実機で
   「OCRをONにした後に言語を変えても英語のまま」という不具合が出ている)。
"""

import unittest
from unittest.mock import Mock, patch

from config import config
from controller import Controller
from models.ocr.ocr_languages import SELECTABLE_LANGUAGES


class TestOcrSourceLanguageEndpoint(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        self._original = config.OCR_SOURCE_LANGUAGE
        self.addCleanup(setattr, config, "OCR_SOURCE_LANGUAGE", self._original)

    def test_selectable_list_is_the_engine_supported_set(self) -> None:
        response = self.controller.getSelectableOcrSourceLanguages()
        self.assertEqual(response["status"], 200)
        self.assertEqual(response["result"], list(SELECTABLE_LANGUAGES))
        # autoはPP-OCRv6 smallが日英中+ラテンを1モデルで読むので正式な選択肢。
        self.assertIn("auto", response["result"])

    def test_supported_language_is_stored_and_pushed_to_the_pipeline(self) -> None:
        config.OCR_SOURCE_LANGUAGE = "auto"
        with patch("controller.model.updateOCRCaptureSettings") as update:
            response = self.controller.setOcrSourceLanguage("Korean")

        self.assertEqual(response["status"], 200)
        self.assertEqual(config.OCR_SOURCE_LANGUAGE, "Korean")
        update.assert_called_once()

    def test_unsupported_language_is_rejected_and_changes_nothing(self) -> None:
        config.OCR_SOURCE_LANGUAGE = "auto"
        for value in ("Klingon", "", "Japanese (Japan)"):
            with patch("controller.model.updateOCRCaptureSettings") as update:
                response = self.controller.setOcrSourceLanguage(value)

            self.assertEqual(response["status"], 400, value)
            self.assertEqual(config.OCR_SOURCE_LANGUAGE, "auto")
            update.assert_not_called()


class TestOtherOcrSettersReachTheRunningPipeline(unittest.TestCase):
    """言語以外のパラメータも、実行中に変更したら反映されること。"""

    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        for name in ("OCR_WINDOW_TITLE", "OCR_POLL_INTERVAL_MS", "OCR_MIN_CONFIDENCE",
                     "OCR_BUBBLE_MIN_TEXT_LENGTH"):
            self.addCleanup(setattr, config, name, getattr(config, name))

    def test_each_setter_pushes_the_new_value(self) -> None:
        cases = [
            (self.controller.setOcrWindowTitle, "VRChat (Other)"),
            (self.controller.setOcrPollIntervalMs, 300),
            (self.controller.setOcrMinConfidence, 0.4),
            (self.controller.setOcrBubbleMinTextLength, 3),
        ]
        for setter, value in cases:
            with patch("controller.model.updateOCRCaptureSettings") as update:
                response = setter(value)
            self.assertEqual(response["status"], 200, setter.__name__)
            update.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
