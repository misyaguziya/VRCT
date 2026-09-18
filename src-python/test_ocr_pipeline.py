"""Tests for models.ocr.ocr_pipeline: dedup cache, near-duplicate matching,
word merging, and OcrPipeline.__init__ の設定値クランプ。

capture/EasyOCR/cv2 本体のスレッドループ(_run/_tick)は実機依存が強いため対象外。
ここでは純粋ロジックのみを検証する。
"""

import unittest
from unittest.mock import Mock, patch

from models.ocr.ocr_pipeline import OcrPipeline, _DedupCache, _similar, _textHash

_mergeWords = OcrPipeline._mergeWords


class TestTextHash(unittest.TestCase):
    def test_same_text_hashes_the_same(self) -> None:
        self.assertEqual(_textHash("hello"), _textHash("hello"))

    def test_hash_is_case_insensitive(self) -> None:
        self.assertEqual(_textHash("Hello"), _textHash("hello"))
        self.assertEqual(_textHash("HELLO"), _textHash("hello"))

    def test_different_text_hashes_differently(self) -> None:
        self.assertNotEqual(_textHash("hello"), _textHash("world"))


class TestSimilar(unittest.TestCase):
    def test_identical_strings_are_similar(self) -> None:
        self.assertTrue(_similar("hello world", "hello world"))

    def test_one_character_typo_is_similar(self) -> None:
        self.assertTrue(_similar("hello world", "hallo world"))

    def test_two_character_edit_distance_is_still_similar(self) -> None:
        self.assertTrue(_similar("hello world", "hollo warld"))

    def test_beyond_max_distance_is_not_similar(self) -> None:
        self.assertFalse(_similar("hello world", "goodbye there"))

    def test_length_difference_beyond_budget_short_circuits(self) -> None:
        self.assertFalse(_similar("hi", "hello world"))

    def test_custom_max_distance_is_respected(self) -> None:
        self.assertFalse(_similar("hello", "hxllo world"[:5], max_distance=0))
        self.assertTrue(_similar("hello", "hello", max_distance=0))


class TestMergeWords(unittest.TestCase):
    def test_joins_word_dicts_with_spaces(self) -> None:
        words = [{"text": "hello", "confidence": 0.9}, {"text": "world", "confidence": 0.8}]
        self.assertEqual(_mergeWords(words), "hello world")

    def test_strips_and_skips_blank_entries(self) -> None:
        words = [{"text": "  hello  "}, {"text": ""}, {"text": "world"}]
        self.assertEqual(_mergeWords(words), "hello world")

    def test_skips_entries_with_non_string_text(self) -> None:
        words = [{"text": "hello"}, {"text": None}, {"confidence": 0.5}, {"text": "world"}]
        self.assertEqual(_mergeWords(words), "hello world")

    def test_empty_list_returns_empty_string(self) -> None:
        self.assertEqual(_mergeWords([]), "")


class TestDedupCache(unittest.TestCase):
    """覚えている間は同じ文を配送しないこと。

    以前は「最後に見てから一定時間で解禁」する方式で、画面に出続けている
    吹き出しでも解禁のたびに同じ文が流れていた (実機で再現、2026-09-18)。
    """

    def test_unknown_text_is_not_suppressed(self) -> None:
        cache = _DedupCache()
        self.assertFalse(cache.seen("h1", "こんにちは", 100.0))

    def test_remembered_text_is_suppressed_no_matter_how_much_time_passes(self) -> None:
        cache = _DedupCache()
        cache.record("h1", "こんにちは", (0, 0), 100.0)
        self.assertTrue(cache.seen("h1", "こんにちは", 100.5))
        self.assertTrue(cache.seen("h1", "こんにちは", 10_000.0))

    def test_sighting_refreshes_the_entry_so_a_lingering_bubble_is_never_forgotten(self) -> None:
        cache = _DedupCache()
        cache.record("h1", "こんにちは", (0, 0), 100.0)
        for t in range(101, 200, 5):  # 5秒おきに見え続ける
            self.assertTrue(cache.seen("h1", "こんにちは", float(t)))
            cache.evictStale(float(t), retention_sec=10.0)
        self.assertTrue(cache.seen("h1", "こんにちは", 200.0))

    def test_text_is_forgotten_after_it_disappears_for_the_retention_window(self) -> None:
        cache = _DedupCache()
        cache.record("h1", "こんにちは", (0, 0), 100.0)
        cache.evictStale(131.0, retention_sec=30.0)
        self.assertFalse(cache.seen("h1", "こんにちは", 131.0))

    def test_near_duplicate_text_is_treated_as_the_same_entry(self) -> None:
        # OCRのゆらぎで1〜2文字違うだけの同じ吹き出しを別物として配送しないため。
        cache = _DedupCache()
        cache.record("h1", "hello world", (0, 0), 100.0)
        self.assertTrue(cache.seen("h2", "hallo world", 101.0))

    def test_different_text_is_not_suppressed(self) -> None:
        cache = _DedupCache()
        cache.record("h1", "こんにちは", (0, 0), 100.0)
        self.assertFalse(cache.seen("h2", "ありがとうございます", 101.0))

    def test_oldest_entries_are_dropped_when_the_cache_is_full(self) -> None:
        cache = _DedupCache(max_items=2)
        for i, text in enumerate(("aaaaaaaa", "bbbbbbbb", "cccccccc")):
            cache.record(f"h{i}", text, (0, 0), 100.0 + i)
        cache.evictStale(102.0, retention_sec=30.0)
        self.assertFalse(cache.seen("h0", "aaaaaaaa", 102.0))
        self.assertTrue(cache.seen("h2", "cccccccc", 102.0))


class TestOcrPipelineInitClamping(unittest.TestCase):
    def _pipeline(self, **overrides) -> OcrPipeline:
        kwargs = dict(callback=lambda result: None)
        kwargs.update(overrides)
        return OcrPipeline(**kwargs)

    def test_poll_interval_ms_converts_to_seconds(self) -> None:
        pipeline = self._pipeline(poll_interval_ms=750)
        self.assertAlmostEqual(pipeline._poll_interval, 0.75)

    def test_poll_interval_has_a_floor(self) -> None:
        pipeline = self._pipeline(poll_interval_ms=0)
        self.assertGreaterEqual(pipeline._poll_interval, 0.1)

    def test_min_text_length_has_a_floor_of_one(self) -> None:
        pipeline = self._pipeline(min_text_length=0)
        self.assertEqual(pipeline._min_text_length, 1)

    def test_dedup_cooldown_has_a_floor_of_one(self) -> None:
        pipeline = self._pipeline(dedup_cooldown_sec=0)
        self.assertEqual(pipeline._dedup_cooldown, 1)

    def test_blank_source_language_falls_back_to_auto(self) -> None:
        pipeline = self._pipeline(source_language="")
        self.assertEqual(pipeline._source_language, "auto")

    def test_blank_window_title_falls_back_to_vrchat(self) -> None:
        pipeline = self._pipeline(window_title="")
        self.assertEqual(pipeline._window_title, "VRChat")


if __name__ == "__main__":
    unittest.main()


class TestDedupWithSlowTicks(unittest.TestCase):
    """OCRが遅くてtick間隔が保持時間を超えても、覚えた文を忘れないこと。

    実機で保持1秒 / tick 1〜2.6秒のとき、画面に出続けている吹き出しの同じ文が
    繰り返し配送された (2026-09-18)。保持時間はtick間隔の2倍を下限にしている。
    """

    def _pipeline(self, **kwargs):
        return OcrPipeline(callback=lambda payload: None, source_language="auto", **kwargs)

    def test_retention_is_at_least_twice_the_tick_interval(self) -> None:
        pipeline = self._pipeline(dedup_cooldown_sec=1)
        used = []
        pipeline._dedup = Mock()
        pipeline._dedup.evictStale.side_effect = lambda now, retention_sec: used.append(retention_sec)
        pipeline._dedup.seen.return_value = True
        pipeline._capture = Mock()
        pipeline._capture.get.return_value = "frame"
        pipeline._reader = object()
        pipeline._detector = Mock()
        pipeline._detector.detect.return_value = [((0, 0, 10, 10), "crop")]

        with patch("models.ocr.ocr_pipeline.ocr_engine.readtext_bgr",
                   return_value=[{"text": "こんにちは", "confidence": 0.9}]),                 patch("models.ocr.ocr_pipeline.time.monotonic", side_effect=[100.0, 100.0, 100.0,
                                                                            103.0, 103.0, 103.0]):
            pipeline._tick()   # 1回目: 間隔が測れないので設定値のまま
            pipeline._tick()   # 2回目: 間隔3秒 -> 6秒まで引き上げ

        self.assertEqual(used, [1, 6.0])


class TestApplyConfig(unittest.TestCase):
    """設定変更がOFF→ONを挟まずに効くこと。

    実機で「OCRをONにした後に言語をJapaneseへ変えても英語モデルのまま」
    という不具合が出たための回帰テスト。_applyPending はワーカースレッドが
    呼ぶ想定なので、ここではスレッドを起こさず直接呼んで確認する。
    """

    def _pipeline(self, **kwargs) -> OcrPipeline:
        return OcrPipeline(callback=lambda payload: None, **{"source_language": "auto", **kwargs})

    def test_scalar_settings_take_effect_on_the_next_tick(self) -> None:
        pipeline = self._pipeline(poll_interval_ms=750, min_confidence=0.55,
                                  min_text_length=2, dedup_cooldown_sec=8)
        pipeline.applyConfig({
            "poll_interval_ms": 250,
            "min_confidence": 0.3,
            "min_text_length": 5,
            "dedup_cooldown_sec": 1,
        })
        pipeline._applyPending()

        self.assertAlmostEqual(pipeline._poll_interval, 0.25)
        self.assertAlmostEqual(pipeline._tick_budget, 0.25 * 0.8)
        self.assertAlmostEqual(pipeline._min_confidence, 0.3)
        self.assertEqual(pipeline._min_text_length, 5)
        self.assertEqual(pipeline._dedup_cooldown, 1)

    def test_language_change_swaps_the_model(self) -> None:
        pipeline = self._pipeline()
        pipeline._reader = "reader-for-auto"
        with patch("models.ocr.ocr_pipeline.ocr_engine.getReader",
                   return_value="reader-for-ko") as get_reader:
            pipeline.applyConfig({"source_language": "Korean"})
            pipeline._applyPending()

        spec = get_reader.call_args[0][0]
        self.assertEqual((spec.ocr_version, spec.lang_rec), ("PP-OCRv5", "korean"))
        self.assertEqual(pipeline._reader, "reader-for-ko")
        self.assertEqual(pipeline._source_language, "Korean")

    def test_switching_to_a_language_the_multilingual_model_covers_keeps_one_model(self) -> None:
        # Japanese も auto も PP-OCRv6 small なので、同じ推論器が使い回される。
        pipeline = self._pipeline(source_language="auto")
        pipeline._reader = "reader-for-auto"
        with patch("models.ocr.ocr_pipeline.ocr_engine.getReader",
                   return_value="reader-for-auto") as get_reader:
            pipeline.applyConfig({"source_language": "Japanese"})
            pipeline._applyPending()

        spec = get_reader.call_args[0][0]
        self.assertEqual((spec.ocr_version, spec.lang_rec), ("PP-OCRv6", None))
        self.assertEqual(pipeline._source_language, "Japanese")

    def test_unsupported_language_keeps_the_current_reader(self) -> None:
        pipeline = self._pipeline()
        pipeline._reader = "reader-for-auto"
        with patch("models.ocr.ocr_pipeline.ocr_engine.getReader") as get_reader:
            pipeline.applyConfig({"source_language": "Klingon"})
            pipeline._applyPending()

        get_reader.assert_not_called()
        self.assertEqual(pipeline._reader, "reader-for-auto")
        self.assertEqual(pipeline._source_language, "auto")

    def test_reader_failure_keeps_the_current_reader(self) -> None:
        pipeline = self._pipeline()
        pipeline._reader = "reader-for-auto"
        with patch("models.ocr.ocr_pipeline.ocr_engine.getReader", return_value=None):
            pipeline.applyConfig({"source_language": "Korean"})
            pipeline._applyPending()

        self.assertEqual(pipeline._reader, "reader-for-auto")
        self.assertEqual(pipeline._source_language, "auto")

    def test_language_change_clears_the_dedup_cache(self) -> None:
        pipeline = self._pipeline()
        pipeline._dedup.record("hash", "こんにちは", (0, 0), 100.0)
        with patch("models.ocr.ocr_pipeline.ocr_engine.getReader", return_value="reader"):
            pipeline.applyConfig({"source_language": "Korean"})
            pipeline._applyPending()

        self.assertFalse(pipeline._dedup.seen("hash", "こんにちは", 101.0))

    def test_window_title_change_reopens_the_capture(self) -> None:
        pipeline = self._pipeline()
        old_capture = Mock()
        pipeline._capture = old_capture
        with patch("models.ocr.ocr_pipeline.OcrCapture", return_value="new-capture") as capture_cls:
            pipeline.applyConfig({"window_title": "VRChat (Other)"})
            pipeline._applyPending()

        old_capture.close.assert_called_once()
        capture_cls.assert_called_once_with(window_title="VRChat (Other)")
        self.assertEqual(pipeline._capture, "new-capture")

    def test_unchanged_values_touch_nothing(self) -> None:
        pipeline = self._pipeline()
        pipeline._capture = Mock()
        with patch("models.ocr.ocr_pipeline.ocr_engine.getReader") as get_reader, \
                patch("models.ocr.ocr_pipeline.OcrCapture") as capture_cls:
            pipeline.applyConfig({"source_language": "auto", "window_title": "VRChat"})
            pipeline._applyPending()

        get_reader.assert_not_called()
        capture_cls.assert_not_called()

    def test_pending_is_consumed_once(self) -> None:
        pipeline = self._pipeline(poll_interval_ms=750)
        pipeline.applyConfig({"poll_interval_ms": 250})
        pipeline._applyPending()
        pipeline._poll_interval = 9.9
        pipeline._applyPending()

        self.assertAlmostEqual(pipeline._poll_interval, 9.9)

    def test_garbage_values_are_ignored_without_breaking_the_loop(self) -> None:
        pipeline = self._pipeline(poll_interval_ms=750)
        pipeline.applyConfig({"poll_interval_ms": "fast", "min_confidence": None})
        pipeline._applyPending()

        self.assertAlmostEqual(pipeline._poll_interval, 0.75)
