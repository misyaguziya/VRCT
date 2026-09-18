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
    def test_first_sighting_is_not_on_cooldown(self) -> None:
        cache = _DedupCache()
        h = _textHash("hello")
        self.assertFalse(cache.seenRecently(h, "hello", cooldown_sec=8, now=0.0))

    def test_recorded_entry_is_on_cooldown_until_it_elapses(self) -> None:
        cache = _DedupCache()
        h = _textHash("hello")
        cache.record(h, "hello", (0, 0), now=0.0)
        self.assertTrue(cache.seenRecently(h, "hello", cooldown_sec=8, now=3.0))
        self.assertFalse(cache.seenRecently(h, "hello", cooldown_sec=8, now=20.0))

    def test_seen_recently_refreshes_timestamp_so_lingering_bubbles_stay_suppressed(self) -> None:
        # 吹き出しが画面に残り続ける限り(=毎tick seenRecentlyが呼ばれ続ける限り)、
        # クールダウン秒数ごとに再送されるのではなく、抑制され続けるべき。
        # 注意: seenRecently自体が「見かけた」タイムスタンプを更新するので、
        # このチェックの呼び出し自体も次の基準点になる。
        cache = _DedupCache()
        h = _textHash("hello")
        cache.record(h, "hello", (0, 0), now=0.0)
        last_seen = 0.0
        for t in (3.0, 6.0, 9.0, 12.0):
            self.assertTrue(cache.seenRecently(h, "hello", cooldown_sec=8, now=t))
            last_seen = t
        # 吹き出しが消え、以後 seenRecently が呼ばれなくなったとする。最後に
        # 見かけた時刻(last_seen=12.0)からクールダウン秒数未満ならまだ抑制。
        self.assertTrue(cache.seenRecently(h, "hello", cooldown_sec=8, now=last_seen + 7.0))

    def test_seen_recently_expires_after_the_bubble_truly_disappears(self) -> None:
        # 上のテストと異なり、ここでは「最後に見かけた後、二度と seenRecently が
        # 呼ばれない(=吹き出しが消えた)」状態を1回だけ離れた時刻でチェックする。
        # seenRecently 自体がタイムスタンプを更新してしまうため、経過確認は
        # 一度きりの呼び出しで行う必要がある。
        cache = _DedupCache()
        h = _textHash("hello")
        cache.record(h, "hello", (0, 0), now=0.0)  # last seen at t=0.0
        self.assertFalse(cache.seenRecently(h, "hello", cooldown_sec=8, now=8.5))

    def test_near_duplicate_text_is_treated_as_the_same_entry(self) -> None:
        cache = _DedupCache()
        cache.record(_textHash("hello world"), "hello world", (0, 0), now=0.0)
        # OCRのブレで1文字違うテキスト(別ハッシュ)でも、編集距離2以内なら
        # 既存エントリのクールダウンにヒットする。
        self.assertTrue(
            cache.seenRecently(_textHash("hallo world"), "hallo world", cooldown_sec=8, now=1.0)
        )

    def test_unrelated_text_is_not_suppressed(self) -> None:
        cache = _DedupCache()
        cache.record(_textHash("hello world"), "hello world", (0, 0), now=0.0)
        self.assertFalse(
            cache.seenRecently(_textHash("completely different"), "completely different", cooldown_sec=8, now=1.0)
        )

    def test_evict_stale_removes_old_entries(self) -> None:
        cache = _DedupCache(evict_after_sec=30.0)
        cache.record(_textHash("old"), "old", (0, 0), now=0.0)
        cache.evictStale(now=31.0)
        self.assertFalse(cache.seenRecently(_textHash("old"), "old", cooldown_sec=8, now=31.0))

    def test_evict_stale_keeps_fresh_entries(self) -> None:
        cache = _DedupCache(evict_after_sec=30.0)
        cache.record(_textHash("fresh"), "fresh", (0, 0), now=0.0)
        cache.evictStale(now=10.0)
        # evictStale(30秒しきい値)では消されていないこと。cooldown_sec(8)自体は
        # 別の話なので、ここでは cooldown_sec を elapsed 以上にして確認する。
        self.assertTrue(cache.seenRecently(_textHash("fresh"), "fresh", cooldown_sec=20, now=10.0))

    def test_max_items_bound_evicts_oldest_first(self) -> None:
        # 短い1文字テキストだと _similar() の編集距離2判定で別テキスト同士でも
        # 「近似重複」とみなされてしまうため、ここでは明確に非類似な文字列を使う。
        cache = _DedupCache(max_items=2, evict_after_sec=9999.0)
        cache.record(_textHash("alpha bravo"), "alpha bravo", (0, 0), now=0.0)
        cache.record(_textHash("charlie delta"), "charlie delta", (0, 0), now=1.0)
        cache.record(_textHash("echo foxtrot"), "echo foxtrot", (0, 0), now=2.0)
        cache.evictStale(now=2.0)
        # "alpha bravo" is oldest and should have been evicted to keep max_items=2.
        self.assertFalse(
            cache.seenRecently(_textHash("alpha bravo"), "alpha bravo", cooldown_sec=8, now=2.0)
        )
        self.assertTrue(
            cache.seenRecently(_textHash("echo foxtrot"), "echo foxtrot", cooldown_sec=8, now=2.0)
        )


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


class TestApplyConfig(unittest.TestCase):
    """設定変更がOFF→ONを挟まずに効くこと。

    実機で「OCRをONにした後に言語をJapaneseへ変えても英語モデルのまま」
    という不具合が出たための回帰テスト。_applyPending はワーカースレッドが
    呼ぶ想定なので、ここではスレッドを起こさず直接呼んで確認する。
    """

    def _pipeline(self, **kwargs) -> OcrPipeline:
        return OcrPipeline(callback=lambda payload: None, source_language="Japanese", **kwargs)

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

    def test_language_change_swaps_the_reader(self) -> None:
        pipeline = self._pipeline()
        pipeline._reader = "reader-for-ja"
        with patch("models.ocr.ocr_pipeline.easyocr_engine.getReader",
                   return_value="reader-for-ko") as get_reader:
            pipeline.applyConfig({"source_language": "Korean"})
            pipeline._applyPending()

        get_reader.assert_called_once_with(["ko", "en"], True)  # use_gpu の既定値
        self.assertEqual(pipeline._reader, "reader-for-ko")
        self.assertEqual(pipeline._source_language, "Korean")

    def test_unsupported_language_keeps_the_current_reader(self) -> None:
        pipeline = self._pipeline()
        pipeline._reader = "reader-for-ja"
        with patch("models.ocr.ocr_pipeline.easyocr_engine.getReader") as get_reader:
            pipeline.applyConfig({"source_language": "Klingon"})
            pipeline._applyPending()

        get_reader.assert_not_called()
        self.assertEqual(pipeline._reader, "reader-for-ja")
        self.assertEqual(pipeline._source_language, "Japanese")

    def test_reader_failure_keeps_the_current_reader(self) -> None:
        pipeline = self._pipeline()
        pipeline._reader = "reader-for-ja"
        with patch("models.ocr.ocr_pipeline.easyocr_engine.getReader", return_value=None):
            pipeline.applyConfig({"source_language": "Korean"})
            pipeline._applyPending()

        self.assertEqual(pipeline._reader, "reader-for-ja")
        self.assertEqual(pipeline._source_language, "Japanese")

    def test_language_change_clears_the_dedup_cache(self) -> None:
        pipeline = self._pipeline()
        pipeline._dedup.record("hash", "こんにちは", (0, 0), 100.0)
        with patch("models.ocr.ocr_pipeline.easyocr_engine.getReader", return_value="reader"):
            pipeline.applyConfig({"source_language": "Korean"})
            pipeline._applyPending()

        self.assertFalse(pipeline._dedup.seenRecently("hash", "こんにちは", 8, 101.0))

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
        with patch("models.ocr.ocr_pipeline.easyocr_engine.getReader") as get_reader, \
                patch("models.ocr.ocr_pipeline.OcrCapture") as capture_cls:
            pipeline.applyConfig({"source_language": "Japanese", "window_title": "VRChat"})
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
