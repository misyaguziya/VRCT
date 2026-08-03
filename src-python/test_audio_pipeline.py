import unittest

import numpy as np

from models.transcription.audio_pipeline import (
    FRAME_SAMPLES,
    Pcm16MonoNormalizer,
    SileroFrameProbability,
    StreamingVadSegmenter,
)


class ProbabilitySequence:
    def __init__(self, values: list[float]) -> None:
        self.values = iter(values)

    def __call__(self, _) -> float:
        return next(self.values)


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


class TestStreamingVadSegmenter(unittest.TestCase):
    def test_rejects_invalid_silero_frame_shape(self) -> None:
        with self.assertRaisesRegex(ValueError, "Expected"):
            SileroFrameProbability()(np.zeros(128, dtype=np.float32))

    def test_emits_partial_snapshot_and_final_segment(self) -> None:
        probabilities = [0.0, 0.3, 0.4, 0.5, 0.05, 0.05]
        segmenter = StreamingVadSegmenter(
            ProbabilitySequence(probabilities),
            redemption_frames=2,
            min_speech_frames=2,
            pre_speech_pad_frames=1,
        )
        frame = np.full(FRAME_SAMPLES, 1000, dtype="<i2").tobytes()

        self.assertEqual(segmenter.process(frame * 3), [])
        partial = segmenter.snapshot()
        final = segmenter.process(frame * 3)

        self.assertIsNotNone(partial)
        self.assertFalse(partial.is_final)
        self.assertEqual(len(final), 1)
        self.assertTrue(final[0].is_final)
        self.assertEqual(final[0].segment_id, partial.segment_id)

    def test_discards_short_vad_misfire(self) -> None:
        segmenter = StreamingVadSegmenter(
            ProbabilitySequence([0.3, 0.05]),
            redemption_frames=1,
            min_speech_frames=2,
        )
        frame = bytes(FRAME_SAMPLES * 2)

        result = segmenter.process(frame * 2, final_input=True)

        self.assertEqual(result, [])

    def test_advances_segment_when_partial_is_discarded(self) -> None:
        segmenter = StreamingVadSegmenter(
            ProbabilitySequence([0.0, 0.3, 0.4, 0.0, 0.3, 0.4]),
            min_speech_frames=2,
            pre_speech_pad_frames=1,
        )
        frame = bytes(FRAME_SAMPLES * 2)
        segmenter.process(frame * 3)
        first = segmenter.snapshot()

        segmenter.reset(advance_segment=True)
        segmenter.process(frame * 3)
        second = segmenter.snapshot()

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertNotEqual(first.segment_id, second.segment_id)


if __name__ == "__main__":
    unittest.main()