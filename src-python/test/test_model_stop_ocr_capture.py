"""model.stopOCRCapture() の停止処理のテスト。"""

import unittest
from unittest.mock import Mock, patch


class TestStopOcrCapture(unittest.TestCase):
    """停止処理が例外なく終わること。

    stopOCRCapture() は import していない gc を呼んでいて NameError になり、
    Controller が起こす stopOcrCapture スレッドが毎回落ちていた
    (2026-09-18 実機のstderrで発覚)。パイプラインの停止自体は先に済んでいたので
    実害は見えにくいが、後続の後始末が実行されない状態だった。
    そもそも別スレッドでの明示 gc はこのリポジトリでは禁止している
    (comtypes の COM ポインタが CoInitialize していないスレッドで Release されて
    access violation になる、model.py の _print_transcript のコメント参照)。
    """

    def test_stop_does_not_raise_and_stops_the_pipeline(self) -> None:
        from model import model
        from models.ocr import OcrPipeline

        pipeline = Mock(spec=OcrPipeline)
        with patch.object(model, "ensure_initialized"):
            model.ocr_pipeline = pipeline
            model.stopOCRCapture()

        pipeline.stop.assert_called_once()
        self.assertIsNone(model.ocr_pipeline)

    def test_stop_is_safe_when_nothing_is_running(self) -> None:
        from model import model

        with patch.object(model, "ensure_initialized"):
            model.ocr_pipeline = None
            model.stopOCRCapture()

        self.assertIsNone(model.ocr_pipeline)
