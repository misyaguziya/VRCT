import unittest
from datetime import datetime, timedelta
from queue import Queue
from unittest.mock import MagicMock, patch

import numpy as np

from speech_recognition.exceptions import RequestError, UnknownValueError

from errors import ErrorCode
from models.transcription.transcription_providers import TranscriptionApiError
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


class TestApiTranscriptionEngines(unittest.TestCase):
    """Groq/OpenAI/カスタムサーバー (OpenAICompatibleTranscriptionProvider) 経由の
    ディスパッチ。プロバイダ自体の挙動 (SDK呼び出し詳細) は
    test_transcription_providers.py で検証済みのため、ここでは
    AudioTranscriber 側の配線・エラー伝播・複数言語候補ループのみを見る。
    """

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    @patch("models.transcription.transcription_transcriber.OpenAICompatibleTranscriptionProvider")
    def test_constructs_provider_with_engine_specific_credentials(self, provider_cls, _) -> None:
        AudioTranscriber(
            False, FakeAudioSource(), 3, 10, "Groq_Whisper",
            api_key="sk-groq", base_url="https://api.groq.com/openai/v1", api_model="whisper-large-v3",
        )

        provider_cls.assert_called_once_with(
            api_key="sk-groq",
            base_url="https://api.groq.com/openai/v1",
            model="whisper-large-v3",
            engine_name="Groq_Whisper",
        )

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    @patch("models.transcription.transcription_transcriber.OpenAICompatibleTranscriptionProvider")
    def test_transcribes_via_api_provider_and_updates_transcript(self, provider_cls, _) -> None:
        provider_cls.return_value.transcribe.return_value = ("hello", 0.9, True)
        transcriber = AudioTranscriber(
            False, FakeAudioSource(), 3, 10, "OpenAI_Whisper",
            api_key="sk-openai", base_url="https://api.openai.com/v1", api_model="whisper-1",
        )
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", datetime.now()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertEqual(transcriber.getTranscript()["text"], "hello")

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    @patch("models.transcription.transcription_transcriber.OpenAICompatibleTranscriptionProvider")
    def test_api_error_sets_recognition_error_and_error_code(self, provider_cls, _) -> None:
        provider_cls.return_value.transcribe.side_effect = TranscriptionApiError(
            ErrorCode.TRANSCRIPTION_API_AUTH_FAILED
        )
        transcriber = AudioTranscriber(
            False, FakeAudioSource(), 3, 10, "Custom_Whisper",
            api_key="", base_url="http://localhost:8000/v1", api_model="whisper",
        )
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", datetime.now()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertTrue(transcriber.last_recognition_error)
        self.assertEqual(transcriber.last_api_error_code, ErrorCode.TRANSCRIPTION_API_AUTH_FAILED)

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    @patch("models.transcription.transcription_transcriber.OpenAICompatibleTranscriptionProvider")
    def test_clears_previous_error_state_before_a_successful_call(self, provider_cls, _) -> None:
        provider_cls.return_value.transcribe.return_value = ("hello", 0.9, True)
        transcriber = AudioTranscriber(
            False, FakeAudioSource(), 3, 10, "Groq_Whisper",
            api_key="sk-groq", base_url="https://api.groq.com/openai/v1", api_model="whisper-large-v3",
        )
        transcriber.last_recognition_error = True
        transcriber.last_api_error_code = ErrorCode.TRANSCRIPTION_API_TIMEOUT
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", datetime.now()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertFalse(transcriber.last_recognition_error)
        self.assertIsNone(transcriber.last_api_error_code)

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    @patch("models.transcription.transcription_transcriber.OpenAICompatibleTranscriptionProvider")
    def test_definitive_result_stops_trying_further_language_candidates(self, provider_cls, _) -> None:
        provider_cls.return_value.transcribe.return_value = ("hello", 0.9, True)
        transcriber = AudioTranscriber(
            False, FakeAudioSource(), 3, 10, "Groq_Whisper",
            api_key="sk-groq", base_url="https://api.groq.com/openai/v1", api_model="whisper-large-v3",
        )
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", datetime.now()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese", "English"], ["Japan", "United States"])

        self.assertEqual(provider_cls.return_value.transcribe.call_count, 1)

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    @patch("models.transcription.transcription_transcriber.OpenAICompatibleTranscriptionProvider")
    def test_keeps_trying_remaining_candidates_when_not_definitive(self, provider_cls, _) -> None:
        provider_cls.return_value.transcribe.side_effect = [
            ("low", 0.2, False),
            ("high", 0.8, False),
        ]
        transcriber = AudioTranscriber(
            False, FakeAudioSource(), 3, 10, "Groq_Whisper",
            api_key="sk-groq", base_url="https://api.groq.com/openai/v1", api_model="whisper-large-v3",
        )
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", datetime.now()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese", "English"], ["Japan", "United States"])

        self.assertEqual(provider_cls.return_value.transcribe.call_count, 2)
        self.assertEqual(transcriber.getTranscript()["text"], "high")


class TestDeepgramTranscriptionEngine(unittest.TestCase):
    """Deepgram (DeepgramProvider) 経由のディスパッチ。base_url を持たない
    点が Groq/OpenAI/カスタムサーバーと異なる。"""

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    @patch("models.transcription.transcription_transcriber.DeepgramProvider")
    def test_constructs_provider_with_api_key_and_model_only(self, provider_cls, _) -> None:
        AudioTranscriber(
            False, FakeAudioSource(), 3, 10, "Deepgram",
            api_key="dg-test", api_model="nova-3",
        )

        provider_cls.assert_called_once_with(api_key="dg-test", model="nova-3")

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    @patch("models.transcription.transcription_transcriber.DeepgramProvider")
    def test_transcribes_via_provider_and_updates_transcript(self, provider_cls, _) -> None:
        provider_cls.return_value.transcribe.return_value = ("hello", 0.9, True)
        transcriber = AudioTranscriber(
            False, FakeAudioSource(), 3, 10, "Deepgram",
            api_key="dg-test", api_model="nova-3",
        )
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", datetime.now()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertEqual(transcriber.getTranscript()["text"], "hello")

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    @patch("models.transcription.transcription_transcriber.DeepgramProvider")
    def test_api_error_sets_recognition_error_and_error_code(self, provider_cls, _) -> None:
        provider_cls.return_value.transcribe.side_effect = TranscriptionApiError(
            ErrorCode.TRANSCRIPTION_API_AUTH_FAILED
        )
        transcriber = AudioTranscriber(
            False, FakeAudioSource(), 3, 10, "Deepgram",
            api_key="dg-bad", api_model="nova-3",
        )
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", datetime.now()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertTrue(transcriber.last_recognition_error)
        self.assertEqual(transcriber.last_api_error_code, ErrorCode.TRANSCRIPTION_API_AUTH_FAILED)

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    @patch("models.transcription.transcription_transcriber.DeepgramProvider")
    def test_single_call_regardless_of_candidate_language_count(self, provider_cls, _) -> None:
        # DeepgramProvider は常に is_definitive=True を返す (1回の呼び出しで
        # 自動言語検出が完結するため)。複数候補言語を渡しても1回しか
        # 呼ばれないことを確認する。
        provider_cls.return_value.transcribe.return_value = ("hello", 0.9, True)
        transcriber = AudioTranscriber(
            False, FakeAudioSource(), 3, 10, "Deepgram",
            api_key="dg-test", api_model="nova-3",
        )
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", datetime.now()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese", "English"], ["Japan", "United States"])

        self.assertEqual(provider_cls.return_value.transcribe.call_count, 1)


class TestWhisperResilienceAcrossCandidates(unittest.TestCase):
    """ローカル Whisper は1候補目で例外が出ても2候補目を試す
    (エラーハンドリングを Google/API系と共通化した副次効果)。
    """

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_continues_to_next_language_after_an_error(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Whisper")
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        transcriber.whisper_model.transcribe.side_effect = [
            RuntimeError("boom"),
            ([], MagicMock(text="ok", language_probability=0.7, language="ja")),
        ]
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", datetime.now()))

        with patch("models.transcription.transcription_transcriber.errorLogging"):
            transcriber.transcribeAudioQueue(audio_queue, ["Japanese", "English"], ["Japan", "United States"])

        self.assertTrue(transcriber.last_recognition_error)
        self.assertEqual(transcriber.whisper_model.transcribe.call_count, 2)

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_does_not_reset_error_flag_at_start_of_call(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Whisper")
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        transcriber.whisper_model.transcribe.return_value = ([], MagicMock(language_probability=1.0, language="ja"))
        transcriber.last_recognition_error = True
        audio_queue = Queue()
        audio_queue.put((b"\x01\x00", datetime.now()))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertTrue(transcriber.last_recognition_error)


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
