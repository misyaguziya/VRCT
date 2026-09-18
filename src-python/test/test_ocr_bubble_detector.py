"""Tests for models.ocr.ocr_bubble_detector.BubbleDetector (YOLOv8n ONNX).

検出そのものはONNXのモデルの仕事なので、ここで検証するのはVRCT側が書いた
「letterboxで縮めた1280x1280の座標を元画像の画素座標へ戻す」計算と、
閾値・信頼度順・画面端でのクリップの扱い。ここを間違えると、モデルが正しく
当てていてもOCRに渡す切り出し位置がずれる(実際に一度、エクスポート時に
NMSへ焼き込まれた信頼度が0.25で固定されていて、実行時に閾値を下げても
候補が増えない状態になっていた)。

推論そのものは、cv2とonnxruntimeが入っている環境でだけ動く煙テストで見る。
"""

import unittest
from os import path as os_path
from unittest.mock import patch

import numpy as np

from models.ocr.ocr_bubble_detector import (
    DEFAULT_IMAGE_SIZE,
    MODEL_FILE_NAME,
    BubbleDetector,
    findModelPath,
)

try:
    import cv2  # type: ignore
except Exception:
    cv2 = None

try:
    import onnxruntime  # type: ignore
except Exception:
    onnxruntime = None


class _FakeSession:
    """ONNXの出力 (1, N, 6) = [x1, y1, x2, y2, conf, cls] を返すだけの差し替え。"""

    def __init__(self, detections):
        self.detections = detections
        self.calls = 0

    def run(self, _outputs, feeds):
        self.calls += 1
        self.feeds = feeds
        return [np.asarray([self.detections], dtype=np.float32)]


def _fakeCv2():
    """_letterbox が使う分だけの cv2 差し替え。scale/dx/dy の計算は本物を通す。"""
    mock = patch("models.ocr.ocr_bubble_detector.cv2").start()
    mock.INTER_LINEAR = 1
    mock.COLOR_BGR2RGB = 4
    mock.resize.side_effect = lambda img, size, interpolation=None: np.zeros(
        (size[1], size[0], 3), dtype=np.uint8)
    mock.cvtColor.side_effect = lambda img, code: img
    return mock


PRESENT_FILE = findModelPath() or __file__  # 実体があれば何でもよい (中身は読まれない)


def _detectorWithSession(detections, frame_shape=(1455, 2575, 3), **kwargs):
    detector = BubbleDetector(model_path=PRESENT_FILE, **kwargs)
    detector._session = _FakeSession(detections)
    detector._input_name = "images"
    frame = np.zeros(frame_shape, dtype=np.uint8)
    return detector, frame


class TestModelIsBundled(unittest.TestCase):
    def test_model_file_sits_where_the_loader_looks_for_it(self) -> None:
        path = findModelPath()
        self.assertIsNotNone(path, "同梱モデルが見つからない (配置か spec/backend.spec の datas を確認)")
        self.assertTrue(os_path.isfile(path))
        self.assertTrue(path.endswith(MODEL_FILE_NAME))


class TestAvailability(unittest.TestCase):
    def test_unavailable_without_opencv(self) -> None:
        detector = BubbleDetector(model_path=PRESENT_FILE)
        with patch("models.ocr.ocr_bubble_detector.cv2", None):
            self.assertFalse(detector.isAvailable())
            self.assertEqual(detector.detect(np.zeros((10, 10, 3), np.uint8)), [])

    def test_unavailable_without_onnxruntime(self) -> None:
        detector = BubbleDetector(model_path=PRESENT_FILE)
        with patch("models.ocr.ocr_bubble_detector.ort", None):
            self.assertFalse(detector.isAvailable())

    def test_unavailable_when_the_model_file_is_missing(self) -> None:
        # 同梱漏れやパスのtypoで「OCRは動くが何も検出しない」状態にならないよう、
        # ファイルの実体まで見ていることを確認する。
        self.assertFalse(BubbleDetector(model_path="no_such_model.onnx").isAvailable())

    def test_unavailable_when_no_model_is_found_at_all(self) -> None:
        with patch("models.ocr.ocr_bubble_detector.findModelPath", return_value=None):
            self.assertFalse(BubbleDetector().isAvailable())

    def test_empty_frame_is_not_sent_to_the_model(self) -> None:
        detector, _ = _detectorWithSession([[0, 0, 10, 10, 0.9, 0]])
        self.addCleanup(patch.stopall)
        _fakeCv2()
        self.assertEqual(detector.detect(np.zeros((0, 0, 3), np.uint8)), [])
        self.assertEqual(detector._session.calls, 0)


class TestCoordinateMapping(unittest.TestCase):
    """letterboxした1280x1280の座標を、元画像(2575x1455)の画素へ戻せているか。"""

    def setUp(self) -> None:
        self.addCleanup(patch.stopall)
        _fakeCv2()
        # 2575x1455 は scale=1280/2575≈0.4971、上下に (1280-724)//2=278 の余白。
        self.scale = DEFAULT_IMAGE_SIZE / 2575
        self.dy = (DEFAULT_IMAGE_SIZE - round(1455 * self.scale)) // 2

    def _toModelSpace(self, x0, y0, x1, y1):
        return [x0 * self.scale, y0 * self.scale + self.dy,
                x1 * self.scale, y1 * self.scale + self.dy]

    def test_box_comes_back_at_the_original_pixel_position(self) -> None:
        expected = (1892, 1081, 1974, 1181)  # 実データのフレーム000040の吹き出し
        box = self._toModelSpace(*expected)
        detector, frame = _detectorWithSession([box + [0.9, 0]], crop_padding=0)
        (x, y, w, h), crop = detector.detect(frame)[0]
        self.assertEqual((x, y, x + w, y + h), expected)
        self.assertEqual(crop.shape[:2], (h, w))

    def test_crop_padding_widens_the_box_and_the_crop_together(self) -> None:
        box = self._toModelSpace(1000, 500, 1100, 600)
        detector, frame = _detectorWithSession([box + [0.9, 0]], crop_padding=4)
        (x, y, w, h), crop = detector.detect(frame)[0]
        self.assertEqual((x, y, w, h), (996, 496, 108, 108))
        self.assertEqual(crop.shape[:2], (h, w))

    def test_box_running_off_the_frame_is_clipped(self) -> None:
        box = self._toModelSpace(2500, 1400, 2575, 1455)
        detector, frame = _detectorWithSession([box + [0.9, 0]], crop_padding=8)
        (x, y, w, h), crop = detector.detect(frame)[0]
        self.assertEqual(x + w, 2575)
        self.assertEqual(y + h, 1455)
        self.assertEqual(crop.shape[:2], (h, w))


class TestThresholdAndOrder(unittest.TestCase):
    def setUp(self) -> None:
        self.addCleanup(patch.stopall)
        _fakeCv2()

    def test_detections_below_the_threshold_are_dropped(self) -> None:
        detections = [[10, 300, 200, 400, 0.9, 0], [300, 300, 500, 400, 0.1, 0]]
        detector, frame = _detectorWithSession(detections, confidence=0.25)
        self.assertEqual(len(detector.detect(frame)), 1)

    def test_lowering_the_threshold_keeps_the_weak_one(self) -> None:
        detections = [[10, 300, 200, 400, 0.9, 0], [300, 300, 500, 400, 0.1, 0]]
        detector, frame = _detectorWithSession(detections, confidence=0.05)
        self.assertEqual(len(detector.detect(frame)), 2)

    def test_results_are_sorted_by_confidence(self) -> None:
        scale = DEFAULT_IMAGE_SIZE / 2575
        # 元画像の x=100 / 1000 / 2000 にある3つを、信頼度 0.4 / 0.9 / 0.6 で返す。
        detections = [[x * scale, 300, (x + 100) * scale, 400, conf, 0]
                      for x, conf in ((100, 0.4), (1000, 0.9), (2000, 0.6))]
        detector, frame = _detectorWithSession(detections, confidence=0.25, crop_padding=0)
        xs = [bbox[0] for bbox, _ in detector.detect(frame)]
        self.assertEqual(xs, [1000, 2000, 100])

    def test_degenerate_box_is_skipped(self) -> None:
        detector, frame = _detectorWithSession([[100, 100, 100, 100, 0.9, 0]], crop_padding=0)
        self.assertEqual(detector.detect(frame), [])


@unittest.skipIf(cv2 is None or onnxruntime is None, "cv2/onnxruntimeが無い環境ではスキップ")
class TestRealModelSmoke(unittest.TestCase):
    """同梱モデルを実際に読んで、例外を出さず期待した形式を返すことだけ見る。"""

    def test_runs_end_to_end_on_a_blank_frame(self) -> None:
        detector = BubbleDetector()
        self.assertTrue(detector.isAvailable())
        results = detector.detect(np.zeros((1455, 2575, 3), dtype=np.uint8))
        self.assertIsInstance(results, list)
        for (x, y, w, h), crop in results:
            self.assertGreater(w, 0)
            self.assertGreater(h, 0)
            self.assertEqual(crop.shape[:2], (h, w))


if __name__ == "__main__":
    unittest.main()
