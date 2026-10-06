"""Tests for models.ocr.ocr_bubble_detector.BubbleDetector (YOLOX-Tiny ONNX).

検出そのものはONNXのモデルの仕事なので、ここで検証するのはVRCT側が書いた
「letterboxで縮めた座標を元画像の画素座標へ戻す」計算と、入力の作り方・
閾値・NMS・信頼度順・画面端でのクリップの扱い。ここを間違えると、モデルが
正しく当てていてもOCRに渡す切り出し位置がずれる。

YOLOv8n から YOLOX へ載せ替えたときに前処理と後処理の両方が変わっている
(余白が中央寄せから左上寄せ、出力がNMS済みのxyxyからNMS前のcxcywh)。
座標の戻しとNMSはVRCT側のコードになったので、ここで押さえる。

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
    nonMaxSuppression,
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
    """ONNXの出力 (1, N, 6) = [cx, cy, w, h, 物体らしさ, クラス] を返すだけの差し替え。"""

    def __init__(self, detections):
        self.detections = detections
        self.calls = 0

    def run(self, _outputs, feeds):
        self.calls += 1
        self.feeds = feeds
        return [np.asarray([self.detections], dtype=np.float32)]


def _fakeCv2():
    """_letterbox が使う分だけの cv2 差し替え。scale の計算は本物を通す。"""
    mock = patch("models.ocr.ocr_bubble_detector.cv2").start()
    mock.INTER_LINEAR = 1
    mock.resize.side_effect = lambda img, size, interpolation=None: np.zeros(
        (size[1], size[0], 3), dtype=np.uint8)
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
        detector, _ = _detectorWithSession([[10, 10, 10, 10, 0.9, 0.9]])
        self.addCleanup(patch.stopall)
        _fakeCv2()
        self.assertEqual(detector.detect(np.zeros((0, 0, 3), np.uint8)), [])
        self.assertEqual(detector._session.calls, 0)


class TestPreprocessing(unittest.TestCase):
    """YOLOXの preproc と同じ形で渡せているか。ここがずれると学習時と別物になる。"""

    def setUp(self) -> None:
        self.addCleanup(patch.stopall)
        _fakeCv2()

    def test_frame_is_padded_to_the_top_left_without_normalization(self) -> None:
        detector, frame = _detectorWithSession([])
        detector.detect(frame)
        tensor = detector._session.feeds["images"]
        # 縮小後は 1280x723。下だけが余白(114)で、左上は画像(0)のまま。
        scale = DEFAULT_IMAGE_SIZE / 2575
        used = int(1455 * scale)
        self.assertEqual(tensor[0, 0, 0, 0], 0.0)
        self.assertEqual(tensor[0, 0, used + 1, 0], 114.0)  # 0-1に正規化していない

    def test_canvas_follows_the_window_shape_in_multiples_of_32(self) -> None:
        """VRChatのウィンドウはユーザーがリサイズできるので、入力の形は毎回変わる。

        正方形に合わせると使わない余白まで推論することになる(16:9で4割強)。
        縮尺は長辺で決まるので、形が変わっても吹き出しの大きさは変わらない。
        """
        # 長辺が 1280 になるので、アスペクト比が同じなら窓の大きさによらず同じ形になる
        # (小さい窓は拡大される)。吹き出しの見かけの大きさを揃えるためにこうしている。
        for (h, w), expected in (((1455, 2575), (736, 1280)),    # 実データの収集時
                                 ((1080, 1920), (736, 1280)),    # 16:9
                                 ((540, 960), (736, 1280)),      # 16:9 の小さい窓
                                 ((1400, 1000), (1280, 928)),    # 縦長のウィンドウ
                                 ((1024, 1024), (1280, 1280))):  # 正方形
            detector, frame = _detectorWithSession([], frame_shape=(h, w, 3))
            detector.detect(frame)
            shape = detector._session.feeds["images"].shape
            self.assertEqual(shape[2:], expected, f"{w}x{h} のウィンドウ")
            self.assertEqual((shape[2] % 32, shape[3] % 32), (0, 0), f"{w}x{h} のウィンドウ")


class TestCoordinateMapping(unittest.TestCase):
    """letterboxした1280x736の座標を、元画像(2575x1455)の画素へ戻せているか。"""

    def setUp(self) -> None:
        self.addCleanup(patch.stopall)
        _fakeCv2()
        # 2575x1455 は scale=1280/2575≈0.4971。余白は右と下だけなのでオフセットは無い。
        self.scale = DEFAULT_IMAGE_SIZE / 2575

    def _toModelSpace(self, x0, y0, x1, y1):
        return [(x0 + x1) / 2 * self.scale, (y0 + y1) / 2 * self.scale,
                (x1 - x0) * self.scale, (y1 - y0) * self.scale]

    def test_box_comes_back_at_the_original_pixel_position(self) -> None:
        expected = (1892, 1081, 1974, 1181)  # 実データのフレーム000040の吹き出し
        box = self._toModelSpace(*expected)
        detector, frame = _detectorWithSession([box + [0.9, 1.0]], crop_padding=0)
        (x, y, w, h), crop = detector.detect(frame)[0]
        self.assertEqual((x, y, x + w, y + h), expected)
        self.assertEqual(crop.shape[:2], (h, w))

    def test_crop_padding_widens_the_box_and_the_crop_together(self) -> None:
        box = self._toModelSpace(1000, 500, 1100, 600)
        detector, frame = _detectorWithSession([box + [0.9, 1.0]], crop_padding=4)
        (x, y, w, h), crop = detector.detect(frame)[0]
        self.assertEqual((x, y, w, h), (996, 496, 108, 108))
        self.assertEqual(crop.shape[:2], (h, w))

    def test_box_running_off_the_frame_is_clipped(self) -> None:
        box = self._toModelSpace(2500, 1400, 2575, 1455)
        detector, frame = _detectorWithSession([box + [0.9, 1.0]], crop_padding=8)
        (x, y, w, h), crop = detector.detect(frame)[0]
        self.assertEqual(x + w, 2575)
        self.assertEqual(y + h, 1455)
        self.assertEqual(crop.shape[:2], (h, w))


class TestThresholdAndOrder(unittest.TestCase):
    def setUp(self) -> None:
        self.addCleanup(patch.stopall)
        _fakeCv2()

    def test_detections_below_the_threshold_are_dropped(self) -> None:
        # 信頼度は「物体らしさ x クラス」。0.5 x 0.4 = 0.2 は 0.25 に届かない。
        detections = [[100, 350, 190, 100, 0.9, 1.0], [400, 350, 200, 100, 0.5, 0.4]]
        detector, frame = _detectorWithSession(detections, confidence=0.25)
        self.assertEqual(len(detector.detect(frame)), 1)

    def test_lowering_the_threshold_keeps_the_weak_one(self) -> None:
        detections = [[100, 350, 190, 100, 0.9, 1.0], [400, 350, 200, 100, 0.5, 0.4]]
        detector, frame = _detectorWithSession(detections, confidence=0.05)
        self.assertEqual(len(detector.detect(frame)), 2)

    def test_results_are_sorted_by_confidence(self) -> None:
        scale = DEFAULT_IMAGE_SIZE / 2575
        # 元画像の x=100 / 1000 / 2000 にある3つを、信頼度 0.4 / 0.9 / 0.6 で返す。
        detections = [[(x + 50) * scale, 350, 100 * scale, 100, conf, 1.0]
                      for x, conf in ((100, 0.4), (1000, 0.9), (2000, 0.6))]
        detector, frame = _detectorWithSession(detections, confidence=0.25, crop_padding=0)
        xs = [bbox[0] for bbox, _ in detector.detect(frame)]
        self.assertEqual(xs, [1000, 2000, 100])

    def test_overlapping_candidates_are_merged_by_nms(self) -> None:
        # YOLOXの出力はNMS前なので、同じ吹き出しに複数のアンカーが当たる。
        detections = [[500, 350, 100, 60, 0.9, 1.0], [505, 352, 100, 60, 0.7, 1.0]]
        detector, frame = _detectorWithSession(detections, confidence=0.25)
        self.assertEqual(len(detector.detect(frame)), 1)

    def test_separate_bubbles_survive_nms(self) -> None:
        detections = [[200, 350, 100, 60, 0.9, 1.0], [900, 350, 100, 60, 0.7, 1.0]]
        detector, frame = _detectorWithSession(detections, confidence=0.25)
        self.assertEqual(len(detector.detect(frame)), 2)

    def test_degenerate_box_is_skipped(self) -> None:
        detector, frame = _detectorWithSession([[100, 100, 0, 0, 0.9, 1.0]], crop_padding=0)
        self.assertEqual(detector.detect(frame), [])


class TestNonMaxSuppression(unittest.TestCase):
    def test_keeps_the_strongest_of_an_overlapping_pair(self) -> None:
        boxes = np.array([[0, 0, 100, 100], [5, 5, 105, 105]], dtype=np.float32)
        self.assertEqual(nonMaxSuppression(boxes, np.array([0.5, 0.9]), 0.65), [1])

    def test_keeps_both_when_they_barely_touch(self) -> None:
        boxes = np.array([[0, 0, 100, 100], [90, 90, 190, 190]], dtype=np.float32)
        self.assertEqual(nonMaxSuppression(boxes, np.array([0.9, 0.5]), 0.65), [0, 1])

    def test_empty_input_returns_nothing(self) -> None:
        self.assertEqual(
            nonMaxSuppression(np.zeros((0, 4), np.float32), np.zeros(0), 0.65), [])


@unittest.skipIf(cv2 is None or onnxruntime is None, "cv2/onnxruntimeが無い環境ではスキップ")
class TestRealModelSmoke(unittest.TestCase):
    """同梱モデルを実際に読んで、例外を出さず期待した形式を返すことだけ見る。"""

    def test_runs_end_to_end_on_any_window_shape(self) -> None:
        # 同梱モデルは入力可変でエクスポートしてある。固定サイズのモデルを
        # 置き換えてしまうと onnxruntime が形の不一致で落ち、detect() が
        # 例外を握りつぶして「OCRは動くが何も出ない」状態になる。
        detector = BubbleDetector()
        self.assertTrue(detector.isAvailable())
        for h, w in ((1455, 2575), (1080, 1920), (1400, 1000), (1024, 1024)):
            results = detector.detect(np.zeros((h, w, 3), dtype=np.uint8))
            self.assertIsInstance(results, list, f"{w}x{h}")
            for (x, y, bw, bh), crop in results:
                self.assertGreater(bw, 0)
                self.assertGreater(bh, 0)
                self.assertEqual(crop.shape[:2], (bh, bw))


if __name__ == "__main__":
    unittest.main()
