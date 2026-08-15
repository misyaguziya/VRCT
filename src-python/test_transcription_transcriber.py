import unittest
from datetime import datetime, timedelta
from queue import Queue
from unittest.mock import MagicMock, patch

import numpy as np

from speech_recognition.exceptions import RequestError

from models.transcription.transcription_transcriber import (
    AudioTranscriber,
    GOOGLE_RECOGNIZE_TIMEOUT_SECONDS,
)


class FakeAudioSource:
    SAMPLE_RATE = 16000
    SAMPLE_WIDTH = 2
    channels = 1


class TestAudioProcessingSelection(unittest.TestCase):
    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_selects_mic_processing_for_microphone(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Google")

        self.assertEqual(transcriber.audio_sources["process_data_func"], transcriber.processMicData)

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_selects_speaker_processing_for_speaker(self, _) -> None:
        transcriber = AudioTranscriber(True, FakeAudioSource(), 3, 10, "Google")

        self.assertEqual(transcriber.audio_sources["process_data_func"], transcriber.processSpeakerData)

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_reads_normalized_speaker_pcm_as_mono(self, _) -> None:
        transcriber = AudioTranscriber(True, FakeAudioSource(), 3, 10, "Google")
        pcm = np.array([1000, -1000], dtype="<i2").tobytes()
        transcriber.audio_sources["last_sample"] = pcm

        result = transcriber.processSpeakerData()

        self.assertEqual(result.get_raw_data(), pcm)


class TestGoogleRecognizerTimeout(unittest.TestCase):
    """Issue #63: Google recognition must not block indefinitely on a bad network."""

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_recognizer_has_finite_operation_timeout(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Google")

        self.assertEqual(transcriber.audio_recognizer.operation_timeout, GOOGLE_RECOGNIZE_TIMEOUT_SECONDS)

    @patch("models.transcription.transcription_transcriber.errorLogging")
    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_request_error_is_logged_instead_of_swallowed(self, _, mock_error_logging) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Google")
        transcriber.audio_recognizer.recognize_google = MagicMock(
            side_effect=RequestError("recognition connection failed: timed out")
        )
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", datetime.now()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        mock_error_logging.assert_called_once()

    @patch("models.transcription.transcription_transcriber.errorLogging")
    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_flags_recognition_error_for_ui_visibility(self, _, __) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Google")
        transcriber.audio_recognizer.recognize_google = MagicMock(
            side_effect=RequestError("recognition connection failed: timed out")
        )
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", datetime.now()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertTrue(transcriber.last_recognition_error)

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_clears_recognition_error_flag_after_a_successful_call(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Google")
        transcriber.last_recognition_error = True
        transcriber.audio_recognizer.recognize_google = MagicMock(return_value=("hello", 0.9))
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", datetime.now()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertFalse(transcriber.last_recognition_error)


class TestQueueProcessing(unittest.TestCase):
    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_drains_queued_audio_before_transcribing(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Whisper")
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        transcriber.whisper_model.transcribe.return_value = ([], MagicMock(language_probability=1.0))
        audio_queue = Queue()
        now = datetime.now()
        audio_queue.put((b"\x01\x00", now))
        audio_queue.put((b"\x02\x00", now + timedelta(milliseconds=100)))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        # Queue が空になっていて、直近サンプルがまとめて last_sample に反映されている
        self.assertTrue(audio_queue.empty())
        self.assertEqual(transcriber.audio_sources["last_sample"], b"\x01\x00\x02\x00")

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_phrase_timeout_resets_last_sample_across_a_gap(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Whisper")
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        transcriber.whisper_model.transcribe.return_value = ([], MagicMock(language_probability=1.0))
        audio_queue = Queue()
        now = datetime.now()
        audio_queue.put((b"\x01\x00", now))
        # phrase_timeout=3s より大きなギャップ = 新フレーズ扱いで last_sample がリセット
        audio_queue.put((b"\x02\x00", now + timedelta(seconds=5)))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertEqual(transcriber.audio_sources["last_sample"], b"\x02\x00")
        self.assertTrue(transcriber.audio_sources["new_phrase"])

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_passes_configured_thresholds_to_whisper(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Whisper")
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        transcriber.whisper_model.transcribe.return_value = ([], MagicMock(language_probability=1.0))
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", datetime.now()))

        transcriber.transcribeAudioQueue(
            audio_queue,
            ["Japanese"],
            ["Japan"],
            avg_logprob=-0.55,
            no_speech_prob=0.42,
        )

        kwargs = transcriber.whisper_model.transcribe.call_args.kwargs
        self.assertEqual(kwargs["log_prob_threshold"], -0.55)
        self.assertEqual(kwargs["no_speech_threshold"], 0.42)


class TestMutedMicMessage(unittest.TestCase):
    @patch("controller.model")
    @patch("controller.config")
    def test_discards_queued_result_while_vrc_mic_is_muted(self, config, model) -> None:
        from controller import Controller

        config.VRC_MIC_MUTE_SYNC = True
        model.mic_mute_status = True

        controller = Controller.__new__(Controller)
        controller.micMessage({"text": "anything", "language": "Japanese"})

        self.assertEqual(model.method_calls, [])


class TestRepeatDetection(unittest.TestCase):
    """VAD ストリーミング撤退 (ADR-0004) で segment_id が消えたため、
    連続同一メッセージは純粋にテキスト比較で抑制する。"""

    def test_receive_repeat_blocks_second_identical_text(self) -> None:
        from model import Model

        model = Model.__new__(Model)
        model.previous_receive_message = ""

        self.assertFalse(model.detectRepeatReceiveMessage("same text"))
        self.assertTrue(model.detectRepeatReceiveMessage("same text"))

    def test_receive_repeat_allows_different_text(self) -> None:
        from model import Model

        model = Model.__new__(Model)
        model.previous_receive_message = ""

        self.assertFalse(model.detectRepeatReceiveMessage("first"))
        self.assertFalse(model.detectRepeatReceiveMessage("second"))

    def test_send_repeat_blocks_second_identical_text(self) -> None:
        from model import Model

        model = Model.__new__(Model)
        model.previous_send_message = ""

        self.assertFalse(model.detectRepeatSendMessage("same text"))
        self.assertTrue(model.detectRepeatSendMessage("same text"))

    def test_send_repeat_allows_different_text(self) -> None:
        from model import Model

        model = Model.__new__(Model)
        model.previous_send_message = ""

        self.assertFalse(model.detectRepeatSendMessage("first"))
        self.assertFalse(model.detectRepeatSendMessage("second"))


if __name__ == "__main__":
    unittest.main()
