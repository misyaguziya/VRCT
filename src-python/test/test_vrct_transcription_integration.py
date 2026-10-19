"""CI-safe tests for the VRCT transcription integration boundary."""

import unittest
from datetime import datetime
from queue import Queue
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from models.transcription.transcription_transcriber import AudioTranscriber


class FakeAudioSource:
    SAMPLE_RATE = 16000
    SAMPLE_WIDTH = 2
    channels = 1


class TestVrctTranscriptionIntegration(unittest.TestCase):
    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_audio_transcriber_drains_vad_segment_and_stores_transcript(self, _) -> None:
        transcriber = AudioTranscriber(
            False,
            FakeAudioSource(),
            phrase_timeout=3,
            max_phrases=10,
            transcription_engine="Whisper",
            vad_segmented=True,
        )
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = SimpleNamespace(
            transcribe=lambda *_args, **_kwargs: (
                [SimpleNamespace(text="これはVRCTのテストです", avg_logprob=-0.1, no_speech_prob=0.1)],
                SimpleNamespace(language="ja", language_probability=0.95),
            )
        )
        queue = Queue()
        queue.put((b"\x01\x00" * 1600, datetime.now(), "silence"))

        result = transcriber.transcribeAudioQueue(queue, ["Japanese"], ["Japan"])
        transcript = transcriber.getTranscript()

        self.assertTrue(result)
        self.assertTrue(queue.empty())
        self.assertEqual(transcript["text"], "これはVRCTのテストです")
        self.assertEqual(transcriber.asr_attempts, 1)
        self.assertEqual(transcriber.asr_successes, 1)

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_audio_transcriber_reports_asr_failure_after_vad_segment(self, _) -> None:
        transcriber = AudioTranscriber(
            False,
            FakeAudioSource(),
            phrase_timeout=3,
            max_phrases=10,
            transcription_engine="Whisper",
            vad_segmented=True,
        )
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = SimpleNamespace(
            transcribe=lambda *_args, **_kwargs: (
                [],
                SimpleNamespace(language="ja", language_probability=0.0),
            )
        )
        queue = Queue()
        queue.put((b"\x01\x00" * 1600, datetime.now(), "flush"))

        result = transcriber.transcribeAudioQueue(queue, ["Japanese"], ["Japan"])

        self.assertTrue(result)
        self.assertTrue(queue.empty())
        self.assertEqual(transcriber.asr_attempts, 1)
        self.assertEqual(transcriber.asr_successes, 0)

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_google_engine_uses_vrct_transcriber_path_and_stores_result(self, _) -> None:
        transcriber = AudioTranscriber(
            False,
            FakeAudioSource(),
            phrase_timeout=3,
            max_phrases=10,
            transcription_engine="Google",
            vad_segmented=True,
        )
        transcriber.audio_recognizer.recognize_google = MagicMock(
            return_value=("これはGoogle経路のテストです", 0.9)
        )
        queue = Queue()
        queue.put((b"\x01\x00" * 1600, datetime.now(), "silence"))

        result = transcriber.transcribeAudioQueue(queue, ["Japanese"], ["Japan"])
        transcript = transcriber.getTranscript()

        self.assertTrue(result)
        self.assertEqual(transcript["text"], "これはGoogle経路のテストです")
        transcriber.audio_recognizer.recognize_google.assert_called_once()
        _, kwargs = transcriber.audio_recognizer.recognize_google.call_args
        self.assertEqual(kwargs["language"], "ja-JP")
        self.assertTrue(kwargs["join_all_results"])


if __name__ == "__main__":
    unittest.main()
