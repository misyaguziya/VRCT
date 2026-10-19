"""OCRのON (setEnableOcrCapture) のテスト。

翻訳のONと同じく、モデル読み込みまで済ませてから応答し、開始できなければ
OCR_DISABLED_* を /run/enable_ocr_capture へ通知してOFFに戻す
(UIは error_code を見て文言を出す。以前は理由なしで false が後から届くだけだった)。
"""

import unittest
from unittest.mock import Mock, patch

from config import config
from controller import Controller
from errors import ErrorCode, OcrStartError


class TestEnableOcrCapture(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        self.controller.run = Mock()
        self.controller.run_mapping = {"enable_ocr_capture": "/run/enable_ocr_capture"}
        self.addCleanup(setattr, config, "ENABLE_OCR_CAPTURE", False)
        config.ENABLE_OCR_CAPTURE = False

    def test_success_responds_true_after_start_and_pushes_nothing(self) -> None:
        with patch("controller.model.startOCRCapture", return_value=True) as start:
            response = self.controller.setEnableOcrCapture()

        start.assert_called_once()
        self.assertEqual(response, {"status": 200, "result": True})
        self.controller.run.assert_not_called()

    def test_failure_pushes_reason_code_and_turns_off(self) -> None:
        for code in (
            ErrorCode.OCR_DISABLED_ENGINE_UNAVAILABLE,
            ErrorCode.OCR_DISABLED_MODEL_LOAD_FAILED,
            ErrorCode.OCR_DISABLED_UNSUPPORTED_LANGUAGE,
        ):
            config.ENABLE_OCR_CAPTURE = False
            self.controller.run.reset_mock()
            with patch("controller.model.startOCRCapture", side_effect=OcrStartError(code)):
                response = self.controller.setEnableOcrCapture()

            self.assertEqual(response, {"status": 200, "result": False}, code)
            self.assertFalse(config.ENABLE_OCR_CAPTURE)
            status, endpoint, result = self.controller.run.call_args.args
            self.assertEqual((status, endpoint), (400, "/run/enable_ocr_capture"))
            self.assertEqual(result["error_code"], code.value)
            self.assertIs(result["data"], False)

    def test_unexpected_exception_is_reported_as_unknown(self) -> None:
        with patch("controller.model.startOCRCapture", side_effect=RuntimeError("boom")), \
                patch("controller.errorLogging"):
            response = self.controller.setEnableOcrCapture()

        self.assertEqual(response["result"], False)
        result = self.controller.run.call_args.args[2]
        self.assertEqual(result["error_code"], ErrorCode.OCR_DISABLED_UNKNOWN.value)


if __name__ == "__main__":
    unittest.main()
