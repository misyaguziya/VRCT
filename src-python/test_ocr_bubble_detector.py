"""Tests for models.ocr.ocr_bubble_detector.BubbleDetector.

`detect()` の実体は「cv2の画像処理パイプライン(cvtColor→blur→adaptiveThreshold
→morphologyEx→findContours)」と「その結果の輪郭に対する幾何フィルタ(面積比・
アスペクト比・端マージン・下部HUD除外・ソート)」の2段構成。前者はOpenCV自体の
アルゴリズムで、合成画像でも閾値の効き方が実際のVRChatスクショと一致する保証が
無く再現性の低いテストになりやすい。後者はVRCT側で書かれた実際にバグが起こり
得るロジックなので、ここでは `cv2.findContours`/`cv2.boundingRect` をモックし、
狙った (x, y, w, h) の輪郭を直接与えることで、幾何フィルタだけを決定的に検証する。
"""

import unittest
from unittest.mock import patch

import numpy as np

from models.ocr.ocr_bubble_detector import BubbleDetector


def _frame(h: int = 600, w: int = 800) -> np.ndarray:
    return np.zeros((h, w, 3), dtype=np.uint8)


def _detect_with_contours(detector: BubbleDetector, frame: np.ndarray, bboxes):
    """`bboxes` (list of (x, y, w, h)) を輪郭検出結果として与えて detect() を実行する。"""
    with patch("models.ocr.ocr_bubble_detector.cv2") as mock_cv2:
        mock_cv2.findContours.return_value = (list(range(len(bboxes))), None)
        mock_cv2.boundingRect.side_effect = list(bboxes)
        # cvtColor/GaussianBlur/adaptiveThreshold/morphologyEx/getStructuringElement
        # の戻り値自体は findContours に渡らない (findContours もモック済み) ので
        # 中身は問わない。MagicMock の自動生成に任せる。
        return detector.detect(frame)


class TestBubbleDetectorGeometryFilters(unittest.TestCase):
    """frame=800x600 (frame_area=480000) 基準。既定パラメータでの境界値:
    min_area=384 / max_area=96000, min_aspect=1.2 / max_aspect=20.0,
    margin_x=24 / margin_y=18, bottom_hud_y=510。
    """

    def setUp(self) -> None:
        self.detector = BubbleDetector()
        self.frame = _frame()

    def test_accepts_a_well_formed_centered_candidate(self) -> None:
        results = _detect_with_contours(self.detector, self.frame, [(200, 200, 200, 40)])
        self.assertEqual(len(results), 1)
        bbox, crop = results[0]
        # pad=4 が四辺に足される。
        self.assertEqual(bbox, (196, 196, 208, 48))
        self.assertEqual(crop.shape, (48, 208, 3))

    def test_rejects_area_below_minimum(self) -> None:
        results = _detect_with_contours(self.detector, self.frame, [(200, 200, 10, 10)])
        self.assertEqual(results, [])

    def test_rejects_area_above_maximum(self) -> None:
        results = _detect_with_contours(self.detector, self.frame, [(50, 50, 700, 150)])
        self.assertEqual(results, [])

    def test_rejects_aspect_too_square(self) -> None:
        results = _detect_with_contours(self.detector, self.frame, [(200, 200, 50, 50)])
        self.assertEqual(results, [])

    def test_rejects_aspect_too_elongated(self) -> None:
        results = _detect_with_contours(self.detector, self.frame, [(100, 200, 600, 10)])
        self.assertEqual(results, [])

    def test_rejects_left_edge_candidate(self) -> None:
        results = _detect_with_contours(self.detector, self.frame, [(0, 200, 200, 40)])
        self.assertEqual(results, [])

    def test_rejects_top_edge_candidate(self) -> None:
        results = _detect_with_contours(self.detector, self.frame, [(200, 0, 200, 40)])
        self.assertEqual(results, [])

    def test_rejects_right_edge_candidate(self) -> None:
        results = _detect_with_contours(self.detector, self.frame, [(700, 200, 100, 40)])
        self.assertEqual(results, [])

    def test_rejects_bottom_hud_candidate(self) -> None:
        results = _detect_with_contours(self.detector, self.frame, [(200, 550, 200, 40)])
        self.assertEqual(results, [])

    def test_sorts_results_by_area_descending(self) -> None:
        big = (200, 100, 300, 60)   # area=18000
        small = (200, 300, 150, 30)  # area=4500
        # 輪郭の入力順は「小さい方が先」にしてもソートで逆転することを確認する。
        results = _detect_with_contours(self.detector, self.frame, [small, big])
        self.assertEqual(len(results), 2)
        (first_bbox, _), (second_bbox, _) = results
        first_area = first_bbox[2] * first_bbox[3]
        second_area = second_bbox[2] * second_bbox[3]
        self.assertGreaterEqual(first_area, second_area)
        # 大きい方 (big) が先頭に来ていること。
        self.assertEqual(first_bbox, (196, 96, 308, 68))

    def test_zero_size_bounding_rect_is_skipped_without_crashing(self) -> None:
        results = _detect_with_contours(self.detector, self.frame, [(200, 200, 0, 40)])
        self.assertEqual(results, [])

    def test_multiple_candidates_mixed_valid_and_invalid(self) -> None:
        valid = (200, 200, 200, 40)
        too_small = (10, 10, 5, 5)
        results = _detect_with_contours(self.detector, self.frame, [too_small, valid])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], (196, 196, 208, 48))


class TestBubbleDetectorGracefulDegradation(unittest.TestCase):
    def test_is_available_reflects_cv2_presence(self) -> None:
        detector = BubbleDetector()
        with patch("models.ocr.ocr_bubble_detector.cv2", None):
            self.assertFalse(detector.isAvailable())

    def test_detect_returns_empty_list_when_cv2_unavailable(self) -> None:
        detector = BubbleDetector()
        with patch("models.ocr.ocr_bubble_detector.cv2", None):
            self.assertEqual(detector.detect(_frame()), [])

    def test_detect_returns_empty_list_for_none_frame(self) -> None:
        detector = BubbleDetector()
        self.assertEqual(detector.detect(None), [])

    def test_detect_returns_empty_list_for_empty_frame(self) -> None:
        detector = BubbleDetector()
        self.assertEqual(detector.detect(np.zeros((0, 0, 3), dtype=np.uint8)), [])

    def test_detect_swallows_exceptions_from_the_cv2_pipeline(self) -> None:
        detector = BubbleDetector()
        with patch("models.ocr.ocr_bubble_detector.cv2") as mock_cv2:
            mock_cv2.cvtColor.side_effect = RuntimeError("boom")
            self.assertEqual(detector.detect(_frame()), [])

    def test_detect_swallows_exceptions_from_find_contours(self) -> None:
        detector = BubbleDetector()
        with patch("models.ocr.ocr_bubble_detector.cv2") as mock_cv2:
            mock_cv2.findContours.side_effect = RuntimeError("boom")
            self.assertEqual(detector.detect(_frame()), [])


class TestBubbleDetectorRealOpenCvPipeline(unittest.TestCase):
    """モック無しの、実際にインストールされたcv2を使った緩い煙テスト。

    合成画像でのアダプティブ閾値の効き方は実データと一致する保証が無いため、
    ここでは「例外を出さず、bbox形式のリストを返す」ことだけを確認する
    (見つかる/見つからないの断定はしない)。
    """

    def test_runs_end_to_end_without_raising_on_a_textured_frame(self) -> None:
        detector = BubbleDetector()
        frame = _frame()
        # 局所コントラストのある縞模様を描き、実際のcv2パイプラインが
        # 例外を出さず一貫した形式の結果を返すことだけを確認する。
        frame[200:240, 300:500:2] = 255
        results = detector.detect(frame)
        self.assertIsInstance(results, list)
        for bbox, crop in results:
            self.assertEqual(len(bbox), 4)
            self.assertEqual(crop.ndim, 3)


class TestBubbleDetectorCollarFilter(unittest.TestCase):
    """VRChat自身の吹き出しパネル(単色フラット)と、ワールド側UI(木目/紙等の
    テクスチャに直接乗ったテキスト)を、bboxのすぐ外側の細い縁の色ばらつきで
    区別するフィルタ (2026-09-07、実機で工場ゲームのUIパネルを吹き出しと
    誤認するregressionを受けて追加)。実データ80枚での較正: 本物の吹き出しの
    縁std中央値2.0、他候補の縁std中央値9.8、閾値5.0(既定)。
    """

    def _frame_with_uniform_patch(self, h, w, patch_region, color=(10, 12, 15), seed=0):
        rng = np.random.default_rng(seed)
        frame = rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)
        px, py, pw, ph = patch_region
        frame[py:py + ph, px:px + pw] = color
        return frame

    def test_keeps_a_candidate_with_a_flat_uniform_surrounding_panel(self) -> None:
        # bbox本体+周囲を広めに単色で塗り、VRChat自身のフラットな吹き出し
        # パネルを模す。
        frame = self._frame_with_uniform_patch(600, 800, patch_region=(280, 180, 240, 80))
        detector = BubbleDetector()
        results = _detect_with_contours(detector, frame, [(300, 200, 200, 40)])
        self.assertEqual(len(results), 1)

    def test_rejects_a_candidate_sitting_on_noisy_world_texture(self) -> None:
        # パッチを塗らない = 候補の周囲もランダムノイズ(木目等のテクスチャを模す)。
        rng = np.random.default_rng(0)
        frame = rng.integers(0, 256, size=(600, 800, 3), dtype=np.uint8)
        detector = BubbleDetector()
        results = _detect_with_contours(detector, frame, [(300, 200, 200, 40)])
        self.assertEqual(results, [])

    def test_mixed_candidates_keeps_only_the_flat_panel_one(self) -> None:
        # 同じ形状・同じ幾何フィルタ通過条件の2候補のうち、片方だけ周囲が
        # フラットなパネル(本物の吹き出し役)、もう片方はノイズ(ワールドUI役)。
        frame = self._frame_with_uniform_patch(600, 800, patch_region=(280, 180, 240, 80))
        bubble_bbox = (300, 200, 200, 40)
        world_ui_bbox = (300, 350, 200, 40)
        detector = BubbleDetector()
        results = _detect_with_contours(detector, frame, [world_ui_bbox, bubble_bbox])
        self.assertEqual(len(results), 1)
        bbox, _ = results[0]
        # pad=4 が四辺に足された bubble_bbox のみが残るはず。
        self.assertEqual(bbox, (296, 196, 208, 48))

    def test_collar_std_is_none_when_region_too_small_to_measure(self) -> None:
        detector = BubbleDetector()
        frame = np.zeros((10, 10, 3), dtype=np.uint8)
        # フレームぎりぎりの極小領域では、周囲の測定ピクセル数が足りず None
        # (判定不能=フィルタしない) を返すべき。
        result = detector._collarStd(frame, 0, 0, 10, 10)
        self.assertIsNone(result)

    def test_collar_std_measures_zero_for_a_perfectly_flat_frame(self) -> None:
        detector = BubbleDetector()
        frame = np.full((100, 100, 3), 50, dtype=np.uint8)
        result = detector._collarStd(frame, 40, 40, 60, 60)
        self.assertAlmostEqual(result, 0.0, places=5)

    def test_custom_max_collar_std_threshold_is_respected(self) -> None:
        # 閾値を極端に厳しくすれば、多少のノイズがある「実質フラット」な
        # 候補も弾かれるようになる。
        frame = self._frame_with_uniform_patch(
            600, 800, patch_region=(280, 180, 240, 80), color=(10, 12, 15),
        )
        # パッチ内にわずかなノイズを混ぜて完全なゼロ分散にしない。
        rng = np.random.default_rng(1)
        noise = rng.integers(-3, 4, size=(80, 240, 3))
        patched = frame[180:260, 280:520].astype(int) + noise
        frame[180:260, 280:520] = np.clip(patched, 0, 255).astype(np.uint8)

        lenient = BubbleDetector(max_collar_std=50.0)
        strict = BubbleDetector(max_collar_std=0.01)
        bbox_list = [(300, 200, 200, 40)]
        self.assertEqual(len(_detect_with_contours(lenient, frame, bbox_list)), 1)
        self.assertEqual(_detect_with_contours(strict, frame, bbox_list), [])


class TestBubbleDetectorPositionScoring(unittest.TestCase):
    """同面積の候補同士では、画面中央/上寄りの候補が優先されるべき
    (ハード排除ではなくソート順のみに影響する)。"""

    def test_centered_upper_candidate_outranks_equally_sized_edge_candidate(self) -> None:
        # 全て真っ黒(collar_std=0で両方フィルタは必ず通過)なフレームを使い、
        # 純粋にスコアリングの違いだけを見る。
        frame = _frame(h=600, w=800)
        detector = BubbleDetector()
        centered_upper = (300, 60, 200, 40)   # 画面中央付近、上寄り
        off_center_lower = (50, 400, 200, 40)  # 画面端寄り、下寄り
        # 検出順はあえて逆にしておく(ソートで正しく並び替わることを確認するため)。
        results = _detect_with_contours(detector, frame, [off_center_lower, centered_upper])
        self.assertEqual(len(results), 2)
        first_bbox, _ = results[0]
        self.assertEqual(first_bbox, (296, 56, 208, 48))  # centered_upper (padded)

    def test_much_larger_edge_candidate_can_still_outrank_a_tiny_centered_one(self) -> None:
        # ソート補正は「軽い優先」であってハード排除ではないため、面積差が
        # 十分大きければ画面端の候補が上位に来ることもある。
        frame = _frame(h=600, w=800)
        detector = BubbleDetector()
        tiny_centered = (380, 60, 40, 20)      # area=800, 中央上寄り
        huge_edge = (500, 380, 260, 40)        # area=10400, 端・下寄り
        results = _detect_with_contours(detector, frame, [tiny_centered, huge_edge])
        self.assertEqual(len(results), 2)
        first_bbox, _ = results[0]
        self.assertEqual(first_bbox, (496, 376, 268, 48))  # huge_edge (padded)


if __name__ == "__main__":
    unittest.main()
