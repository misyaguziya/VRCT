import unittest
from unittest.mock import patch

from models.transcription.transcription_evaluation import (
    character_error_rate,
    evaluate_case,
    summarize,
    word_error_rate,
)


class TestTranscriptionMetrics(unittest.TestCase):
    def test_computes_unicode_normalized_cer(self) -> None:
        self.assertEqual(character_error_rate("ＶＲＣＴ です", "vrctです"), 0.0)
        self.assertAlmostEqual(character_error_rate("こんにちは", "こんばんは"), 2 / 5)

    def test_computes_wer(self) -> None:
        self.assertAlmostEqual(word_error_rate("hello vr chat", "hello chat"), 1 / 3)

    @patch("models.transcription.transcription_evaluation.time.perf_counter", side_effect=[1.0, 1.12])
    def test_measures_latency_and_real_time_factor(self, _) -> None:
        result = evaluate_case(
            "case-1",
            "hello",
            1000.0,
            lambda: {"text": "hello", "end_to_result_ms": 80.0},
        )

        self.assertAlmostEqual(result.processing_ms, 120.0)
        self.assertEqual(result.end_to_result_ms, 80.0)
        self.assertAlmostEqual(result.real_time_factor, 0.12)
        self.assertEqual(summarize([result])["mean_cer"], 0.0)


if __name__ == "__main__":
    unittest.main()