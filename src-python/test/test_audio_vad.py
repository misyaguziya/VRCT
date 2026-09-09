import unittest

import numpy as np

from models.transcription.audio_vad import (
    FRAME_SAMPLES,
    Pcm16MonoNormalizer,
    SileroFrameProbability,
    VadRecognizerAdapter,
    VadSegmenter,
)


class ProbabilitySequence:
    """テスト用の疑似 VAD エンジン。reset() 呼び出し回数も記録する。"""

    def __init__(self, values: list[float]) -> None:
        self.values = iter(values)
        self.reset_count = 0

    def __call__(self, _frame: np.ndarray) -> float:
        return next(self.values)

    def reset(self) -> None:
        self.reset_count += 1


def frame(value: int = 1000) -> bytes:
    return np.full(FRAME_SAMPLES, value, dtype="<i2").tobytes()


class TestPcm16MonoNormalizer(unittest.TestCase):
    def test_downmixes_stereo_without_clipping(self) -> None:
        stereo = np.array([[1000, 3000], [-3000, -1000]], dtype="<i2").tobytes()

        result = Pcm16MonoNormalizer(16000, 2, 2).process(stereo)

        self.assertEqual(np.frombuffer(result, dtype="<i2").tolist(), [2000, -2000])

    def test_resamples_continuous_chunks_to_16khz(self) -> None:
        normalizer = Pcm16MonoNormalizer(48000, 2, 1)
        source = np.arange(4800, dtype=np.int16).tobytes()

        result = normalizer.process(source[:4800]) + normalizer.process(source[4800:])

        self.assertAlmostEqual(len(result) // 2, 1600, delta=1)


class TestSileroFrameProbability(unittest.TestCase):
    def test_rejects_invalid_frame_shape(self) -> None:
        with self.assertRaisesRegex(ValueError, "Expected"):
            SileroFrameProbability()(np.zeros(128, dtype=np.float32))


class TestVadSegmenterBasics(unittest.TestCase):
    def test_no_segment_emitted_below_threshold(self) -> None:
        segmenter = VadSegmenter(
            ProbabilitySequence([0.05] * 10),
            hangover_frames=2,
            min_speech_frames=2,
            pre_speech_pad_frames=1,
        )

        segments = segmenter.process(frame() * 10)

        self.assertEqual(segments, [])
        self.assertFalse(segmenter.speaking)

    def test_short_misfire_is_discarded(self) -> None:
        # 発話確率が一瞬だけ上がるがすぐ下がる (VAD misfire) ケース。
        # min_speech_frames に届かないので speaking に遷移しない。
        segmenter = VadSegmenter(
            ProbabilitySequence([0.3, 0.05, 0.05, 0.05]),
            hangover_frames=2,
            min_speech_frames=2,
            pre_speech_pad_frames=1,
        )

        segments = segmenter.process(frame() * 4)

        self.assertEqual(segments, [])

    def test_natural_silence_ends_segment_with_silence_reason(self) -> None:
        # hangover_frames=2 は「無音に転じたフレームから 2 フレーム経過」
        # の意味 (anchor 方式)。無音に転じた1フレーム目自身は diff=0 な
        # ので、発火には無音フレームが計3つ (anchor + 2) 必要。
        segmenter = VadSegmenter(
            ProbabilitySequence([0.9, 0.9, 0.05, 0.05, 0.05]),
            hangover_frames=2,
            min_speech_frames=2,
            pre_speech_pad_frames=0,
        )

        segments = segmenter.process(frame() * 5)

        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].reason, "silence")

    def test_pre_roll_is_included_in_committed_segment(self) -> None:
        # positive_threshold に達する前のフレーム (pre-roll) も
        # 確定セグメントの音声に含まれること。
        segmenter = VadSegmenter(
            ProbabilitySequence([0.05, 0.9, 0.9, 0.05, 0.05, 0.05]),
            hangover_frames=2,
            min_speech_frames=2,
            pre_speech_pad_frames=3,
        )

        segments = segmenter.process(frame() * 6)

        self.assertEqual(len(segments), 1)
        # pre-roll 1 frame + trigger 2 frames + hangover 判定までの
        # trailing 3 frames (post-roll、silero-vad の speech_pad_ms と
        # 同じ意図で末尾も少し含む) = 6 frames 分の音声。
        self.assertEqual(len(segments[0].audio), FRAME_SAMPLES * 2 * 6)
        # 先頭 (pre-roll) が実際に含まれていることも確認する。
        self.assertTrue(segments[0].audio.startswith(frame()))


class TestVadSegmenterMaxDuration(unittest.TestCase):
    def test_long_continuous_speech_without_silence_is_force_split(self) -> None:
        """ADR-0003 の回帰テスト: 無音を含まない長い連続発話が
        max_speech_frames で強制終端され、新しい segment_id で
        後続セグメントとして継続すること。旧実装ではこのケースで
        max_speech_duration_s が未配線のためセグメントが無限に伸び、
        Whisper/Google に渡す音声が肥大化して「最初の数語だけ認識され
        以降止まる」症状を引き起こしていた。
        """
        segmenter = VadSegmenter(
            ProbabilitySequence([0.9] * 30),
            hangover_frames=99,  # 無音による終端は発火させない
            min_speech_frames=2,
            pre_speech_pad_frames=0,
            max_speech_frames=5,
        )

        segments = segmenter.process(frame() * 20)

        self.assertGreaterEqual(len(segments), 2)
        for segment in segments:
            self.assertEqual(segment.reason, "max_duration")
        segment_ids = {s.segment_id for s in segments}
        self.assertEqual(len(segment_ids), len(segments), "各セグメントは新しい segment_id を持つ")

    def test_max_duration_does_not_reset_probability_engine(self) -> None:
        """PuriPuly-heart の VadGating に倣い、max_duration での強制終端は
        VAD の内部 state をリセットしない (発話者はまだ話し続けている
        ため、モデルの文脈を維持したまま継続させる)。
        """
        engine = ProbabilitySequence([0.9] * 10)
        segmenter = VadSegmenter(
            engine,
            hangover_frames=99,
            min_speech_frames=2,
            pre_speech_pad_frames=0,
            max_speech_frames=5,
        )

        segmenter.process(frame() * 10)

        self.assertEqual(engine.reset_count, 0)

    def test_silence_end_resets_probability_engine(self) -> None:
        engine = ProbabilitySequence([0.9, 0.9, 0.05, 0.05, 0.05])
        segmenter = VadSegmenter(
            engine,
            hangover_frames=2,
            min_speech_frames=2,
            pre_speech_pad_frames=0,
        )

        segmenter.process(frame() * 5)

        self.assertEqual(engine.reset_count, 1)

    def test_continuous_speech_resumes_quickly_after_max_duration_cut(self) -> None:
        """強制分割の直後も、話者が話し続けていれば
        min_speech_frames 分の短い遅延だけで次のセグメントが再始動する
        こと (エンジンリセットしないことの効果を確認)。
        """
        segmenter = VadSegmenter(
            ProbabilitySequence([0.9] * 12),
            hangover_frames=99,
            min_speech_frames=2,
            pre_speech_pad_frames=0,
            max_speech_frames=5,
        )

        segments = segmenter.process(frame() * 12)

        # 5フレームで最初の max_duration、そこから min_speech_frames=2 で
        # 再始動し、また max_speech_frames=5 溜まったところで2回目の
        # max_duration ... という周期になるはず。
        self.assertGreaterEqual(len(segments), 2)


class TestVadSegmenterFlushAndReset(unittest.TestCase):
    def test_flush_finalizes_uncommitted_speech(self) -> None:
        segmenter = VadSegmenter(
            ProbabilitySequence([0.9, 0.9, 0.9]),
            hangover_frames=99,
            min_speech_frames=2,
            pre_speech_pad_frames=0,
        )
        segmenter.process(frame() * 3)

        result = segmenter.flush()

        self.assertIsNotNone(result)
        self.assertEqual(result.reason, "flush")
        self.assertFalse(segmenter.speaking)

    def test_flush_without_active_speech_returns_none(self) -> None:
        segmenter = VadSegmenter(
            ProbabilitySequence([0.05, 0.05]),
            hangover_frames=2,
            min_speech_frames=2,
            pre_speech_pad_frames=0,
        )
        segmenter.process(frame() * 2)

        result = segmenter.flush()

        self.assertIsNone(result)

    def test_reset_clears_all_state_and_resets_engine(self) -> None:
        engine = ProbabilitySequence([0.9, 0.9, 0.9])
        segmenter = VadSegmenter(
            engine,
            hangover_frames=99,
            min_speech_frames=2,
            pre_speech_pad_frames=0,
        )
        segmenter.process(frame() * 3)
        self.assertTrue(segmenter.speaking)

        segmenter.reset()

        self.assertFalse(segmenter.speaking)
        self.assertEqual(engine.reset_count, 1)


class TestVadSegmenterMidBandHysteresis(unittest.TestCase):
    def test_mid_band_probability_does_not_reset_or_extend_silence_anchor(self) -> None:
        """silero-vad 公式 VADIterator と同じ anchor 方式であることの検証。
        中間確率帯 (negative_threshold <= prob < speech_threshold) の
        フレームが挟まっても、無音 anchor は最初に無音へ転じたフレームの
        ままであり続け、hangover_frames はそこからの経過フレーム数で
        判定されること (＝中間帯フレームで無音判定が引き延ばされたり、
        逆に据え置きのまま復帰が遅れたりしない)。
        """
        # threshold=0.25, negative=0.10。中間帯 (0.10〜0.25) のフレームは
        # anchor に一切触れない (公式 VADIterator と同じ)。hangover=4 は
        # 「anchor セット後、frame_count で4進むまで」の意味なので、
        # 中間帯フレームで経過フレーム数自体は進むが判定自体は
        # anchor 復帰後の低確率フレームでまとめて確認される。
        segmenter = VadSegmenter(
            ProbabilitySequence([0.9, 0.9, 0.05, 0.15, 0.15, 0.05, 0.05]),
            speech_threshold=0.25,
            negative_threshold=0.10,
            hangover_frames=4,
            min_speech_frames=2,
            pre_speech_pad_frames=0,
        )

        segments = segmenter.process(frame() * 7)

        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].reason, "silence")

    def test_returning_above_threshold_cancels_silence_anchor(self) -> None:
        segmenter = VadSegmenter(
            ProbabilitySequence([0.9, 0.9, 0.05, 0.9, 0.05, 0.05, 0.05]),
            speech_threshold=0.25,
            negative_threshold=0.10,
            hangover_frames=2,
            min_speech_frames=2,
            pre_speech_pad_frames=0,
        )

        segments = segmenter.process(frame() * 7)

        # frame3 で anchor セット→frame4 で 0.9 に復帰しキャンセル→
        # frame5 で新たに anchor セットされ、2フレーム経過 (frame7) で終端。
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].reason, "silence")


class TestVadSegmenterDiagnosticCallback(unittest.TestCase):
    """PuriPuly-heart の diagnostic_event_callback に倣って追加した診断
    ログフック。フレーム単位ではなく speech_start/speech_end の状態
    遷移でのみ呼ばれ、失敗しても VAD 自体を止めない。
    """

    def test_emits_speech_start_and_speech_end_events(self) -> None:
        messages: list[str] = []
        segmenter = VadSegmenter(
            ProbabilitySequence([0.9, 0.9, 0.05, 0.05, 0.05]),
            hangover_frames=2,
            min_speech_frames=2,
            pre_speech_pad_frames=0,
            diagnostic_callback=messages.append,
            diagnostic_label="mic",
        )

        segments = segmenter.process(frame() * 5)

        self.assertEqual(len(segments), 1)
        start_messages = [m for m in messages if "speech_start" in m]
        end_messages = [m for m in messages if "speech_end" in m]
        self.assertEqual(len(start_messages), 1)
        self.assertEqual(len(end_messages), 1)
        self.assertIn("[VAD][mic]", start_messages[0])
        self.assertIn(f"segment_id={segments[0].segment_id}", end_messages[0])
        self.assertIn("reason=silence", end_messages[0])

    def test_does_not_emit_events_for_discarded_misfires(self) -> None:
        messages: list[str] = []
        segmenter = VadSegmenter(
            ProbabilitySequence([0.3, 0.05, 0.05, 0.05]),
            hangover_frames=2,
            min_speech_frames=2,
            pre_speech_pad_frames=1,
            diagnostic_callback=messages.append,
        )

        segmenter.process(frame() * 4)

        self.assertEqual(messages, [])

    def test_a_broken_callback_does_not_break_vad_processing(self) -> None:
        def raising_callback(_message: str) -> None:
            raise RuntimeError("boom")

        segmenter = VadSegmenter(
            ProbabilitySequence([0.9, 0.9, 0.05, 0.05, 0.05]),
            hangover_frames=2,
            min_speech_frames=2,
            pre_speech_pad_frames=0,
            diagnostic_callback=raising_callback,
        )

        segments = segmenter.process(frame() * 5)

        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].reason, "silence")


class TestVadRecognizerAdapter(unittest.TestCase):
    """`custom_speech_recognition` の listen_with_segmenter_in_background が
    要求する sample_rate/sample_width/process/flush プロトコルへ
    VadSegmenter を適合させるアダプタのテスト。
    """

    def test_exposes_16khz_16bit_regardless_of_native_format(self) -> None:
        adapter = VadRecognizerAdapter(native_sample_rate=48000, native_sample_width=2, native_channels=2)

        self.assertEqual(adapter.sample_rate, 16000)
        self.assertEqual(adapter.sample_width, 2)

    def test_process_resamples_native_audio_before_segmenting(self) -> None:
        # 48kHz ステレオのネイティブ入力を、十分な回数供給すれば
        # (2 陽性 → 持続的な陰性という確率列に対して) ちょうど1セグメント
        # だけ確定すること。audioop.ratecv はコール毎の出力サンプル数が
        # 厳密に一定ではないため、正規化後のフレーム数を厳密に予測せず、
        # 余裕を持った回数供給して最終的な確定数だけを検証する。
        segmenter = VadSegmenter(
            ProbabilitySequence([0.9, 0.9] + [0.05] * 40),
            hangover_frames=2,
            min_speech_frames=2,
            pre_speech_pad_frames=0,
        )
        adapter = VadRecognizerAdapter(
            native_sample_rate=48000, native_sample_width=2, native_channels=2, segmenter=segmenter,
        )

        native_frame = np.full((FRAME_SAMPLES * 3, 2), 1000, dtype="<i2")
        native_chunk = native_frame.tobytes()

        segments: list = []
        for _ in range(20):
            segments.extend(adapter.process(native_chunk))

        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].reason, "silence")

    def test_process_with_empty_normalized_output_returns_no_segments(self) -> None:
        # 極端に短いチャンクは正規化後に空バイト列になりうる。
        # segmenter.process が空バイトで呼ばれないこと (呼ぶと frame_bytes
        # に満たないままリマインダに溜まるだけで無害だが、明示的に
        # スキップすることで無駄な呼び出しを避ける)。
        adapter = VadRecognizerAdapter(native_sample_rate=48000, native_sample_width=2, native_channels=1)

        segments = adapter.process(b"")

        self.assertEqual(segments, [])

    def test_flush_delegates_to_segmenter_and_resets_normalizer(self) -> None:
        segmenter = VadSegmenter(
            ProbabilitySequence([0.9, 0.9, 0.9]),
            hangover_frames=99,
            min_speech_frames=2,
            pre_speech_pad_frames=0,
        )
        adapter = VadRecognizerAdapter(
            native_sample_rate=16000, native_sample_width=2, native_channels=1, segmenter=segmenter,
        )
        adapter.process(frame() * 3)

        result = adapter.flush()

        self.assertIsNotNone(result)
        self.assertEqual(result.reason, "flush")

    def test_reset_resets_both_normalizer_and_segmenter_engine(self) -> None:
        engine = ProbabilitySequence([0.9, 0.9, 0.9])
        segmenter = VadSegmenter(engine, hangover_frames=99, min_speech_frames=2, pre_speech_pad_frames=0)
        adapter = VadRecognizerAdapter(
            native_sample_rate=16000, native_sample_width=2, native_channels=1, segmenter=segmenter,
        )
        adapter.process(frame() * 3)
        self.assertTrue(segmenter.speaking)

        adapter.reset()

        self.assertFalse(segmenter.speaking)
        self.assertEqual(engine.reset_count, 1)


if __name__ == "__main__":
    unittest.main()
