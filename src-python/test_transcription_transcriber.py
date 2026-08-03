import unittest
import copy
from datetime import datetime, timedelta
from queue import Queue
from unittest.mock import MagicMock, patch

import numpy as np

from speech_recognition.exceptions import RequestError

from models.transcription.transcription_transcriber import (
    AudioTranscriber,
    GOOGLE_RECOGNIZE_TIMEOUT_SECONDS,
    _should_use_vad_filter,
)
from models.transcription.audio_pipeline import AudioQueueItem
from config import _DEFAULT_VAD_PARAMETERS, _LEGACY_VAD_PARAMETERS, _migrate_vad_defaults


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


class TestWhisperVadFilter(unittest.TestCase):
    def test_enables_vad_for_turbo_models(self) -> None:
        self.assertTrue(_should_use_vad_filter(False, "large-v3-turbo"))
        self.assertTrue(_should_use_vad_filter(False, "large-v3-turbo-int8"))

    def test_preserves_vad_setting_for_other_models(self) -> None:
        self.assertFalse(_should_use_vad_filter(False, "large-v3"))
        self.assertTrue(_should_use_vad_filter(True, "large-v3"))

    def test_migrates_untouched_legacy_vad_defaults(self) -> None:
        config_data = {
            "MIC_VAD_FILTER": False,
            "MIC_VAD_PARAMETERS": copy.deepcopy(_LEGACY_VAD_PARAMETERS),
            "SPEAKER_VAD_FILTER": False,
            "SPEAKER_VAD_PARAMETERS": copy.deepcopy(_LEGACY_VAD_PARAMETERS),
        }

        _migrate_vad_defaults(config_data)

        self.assertTrue(config_data["MIC_VAD_FILTER"])
        self.assertEqual(config_data["MIC_VAD_PARAMETERS"], _DEFAULT_VAD_PARAMETERS)
        self.assertTrue(config_data["SPEAKER_VAD_FILTER"])
        self.assertEqual(config_data["SPEAKER_VAD_PARAMETERS"], _DEFAULT_VAD_PARAMETERS)

    def test_preserves_custom_vad_settings(self) -> None:
        custom_parameters = copy.deepcopy(_LEGACY_VAD_PARAMETERS)
        custom_parameters["threshold"] = 0.4
        config_data = {
            "MIC_VAD_FILTER": False,
            "MIC_VAD_PARAMETERS": custom_parameters,
        }

        _migrate_vad_defaults(config_data)

        self.assertFalse(config_data["MIC_VAD_FILTER"])
        self.assertEqual(config_data["MIC_VAD_PARAMETERS"], custom_parameters)


class TestWhisperQueueProcessing(unittest.TestCase):
    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_accepts_structured_partial_queue_item(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Google")
        recorded_at = datetime.now()

        transcriber._update_from_queue_item(AudioQueueItem(
            audio=b"\x01\x00",
            recorded_at=recorded_at,
            is_final=False,
            segment_id=8,
        ))

        self.assertEqual(transcriber.audio_sources["last_sample"], b"\x01\x00")
        self.assertEqual(transcriber.audio_sources["segment_id"], 8)
        self.assertFalse(transcriber.audio_sources["is_final"])

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_coalesces_queued_audio_before_transcribing(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Google")
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        transcriber.whisper_model.transcribe.return_value = ([], MagicMock(language_probability=1.0))
        audio_queue = Queue()
        now = datetime.now()
        audio_queue.put((b"\x01\x00", now))
        audio_queue.put((b"\x02\x00", now + timedelta(milliseconds=100)))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        self.assertTrue(audio_queue.empty())
        audio = transcriber.whisper_model.transcribe.call_args.args[0]
        self.assertEqual(audio.tolist(), [1 / 32768, 2 / 32768])

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_coalescing_preserves_phrase_boundaries(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Google")
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        transcriber.whisper_model.transcribe.return_value = ([], MagicMock(language_probability=1.0))
        audio_queue = Queue()
        now = datetime.now()
        audio_queue.put((b"\x01\x00", now))
        audio_queue.put((b"\x02\x00", now + timedelta(seconds=4)))

        transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"])

        audio = transcriber.whisper_model.transcribe.call_args.args[0]
        self.assertEqual(audio.tolist(), [2 / 32768])

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_passes_configured_thresholds_to_whisper(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Google")
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

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_preserves_multiple_structured_final_segments_in_order(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Google")
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        transcriber.whisper_model.transcribe.side_effect = [
            ([MagicMock(text="first", avg_logprob=0.0, no_speech_prob=0.0)], MagicMock(language_probability=1.0)),
            ([MagicMock(text="second", avg_logprob=0.0, no_speech_prob=0.0)], MagicMock(language_probability=1.0)),
        ]
        audio_queue = Queue()
        now = datetime.now()
        audio_queue.put(AudioQueueItem(audio=b"\x01\x00", recorded_at=now, is_final=True, segment_id=1, speech_ended_at=now))
        audio_queue.put(AudioQueueItem(audio=b"\x02\x00", recorded_at=now, is_final=True, segment_id=2, speech_ended_at=now))

        self.assertTrue(transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"]))
        first = transcriber.getTranscript()
        self.assertEqual(first["text"], "first")

        self.assertTrue(transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"]))
        second = transcriber.getTranscript()
        self.assertEqual(second["text"], "second")

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_replaces_stale_partial_with_final_for_same_segment(self, _) -> None:
        transcriber = AudioTranscriber(False, FakeAudioSource(), 3, 10, "Google")
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        transcriber.whisper_model.transcribe.return_value = (
            [MagicMock(text="final", avg_logprob=0.0, no_speech_prob=0.0)],
            MagicMock(language_probability=1.0),
        )
        audio_queue = Queue()
        now = datetime.now()
        audio_queue.put(AudioQueueItem(audio=b"\x01\x00", recorded_at=now, is_final=False, segment_id=3))
        audio_queue.put(AudioQueueItem(audio=b"\x02\x00", recorded_at=now, is_final=True, segment_id=3, speech_ended_at=now))

        self.assertTrue(transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"]))
        result = transcriber.getTranscript()

        self.assertEqual(result["text"], "final")
        audio = transcriber.whisper_model.transcribe.call_args.args[0]
        self.assertEqual(audio.tolist(), [2 / 32768])

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_speaker_preserves_multiple_structured_final_segments_in_order(self, _) -> None:
        transcriber = AudioTranscriber(True, FakeAudioSource(), 3, 10, "Google")
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        transcriber.whisper_model.transcribe.side_effect = [
            ([MagicMock(text="speaker first", avg_logprob=0.0, no_speech_prob=0.0)], MagicMock(language_probability=1.0)),
            ([MagicMock(text="speaker second", avg_logprob=0.0, no_speech_prob=0.0)], MagicMock(language_probability=1.0)),
        ]
        audio_queue = Queue()
        now = datetime.now()
        audio_queue.put(AudioQueueItem(audio=b"\x01\x00", recorded_at=now, is_final=True, segment_id=11, speech_ended_at=now))
        audio_queue.put(AudioQueueItem(audio=b"\x02\x00", recorded_at=now, is_final=True, segment_id=12, speech_ended_at=now))

        self.assertTrue(transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"]))
        first = transcriber.getTranscript()
        self.assertEqual(first["text"], "speaker first")

        self.assertTrue(transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"]))
        second = transcriber.getTranscript()
        self.assertEqual(second["text"], "speaker second")

    @patch("models.transcription.transcription_transcriber.checkWhisperWeight", return_value=False)
    def test_speaker_replaces_stale_partial_with_final_for_same_segment(self, _) -> None:
        transcriber = AudioTranscriber(True, FakeAudioSource(), 3, 10, "Google")
        transcriber.transcription_engine = "Whisper"
        transcriber.whisper_model = MagicMock()
        transcriber.whisper_model.transcribe.return_value = (
            [MagicMock(text="speaker final", avg_logprob=0.0, no_speech_prob=0.0)],
            MagicMock(language_probability=1.0),
        )
        audio_queue = Queue()
        now = datetime.now()
        audio_queue.put(AudioQueueItem(audio=b"\x01\x00", recorded_at=now, is_final=False, segment_id=13))
        audio_queue.put(AudioQueueItem(audio=b"\x02\x00", recorded_at=now, is_final=True, segment_id=13, speech_ended_at=now))

        self.assertTrue(transcriber.transcribeAudioQueue(audio_queue, ["Japanese"], ["Japan"]))
        result = transcriber.getTranscript()

        self.assertEqual(result["text"], "speaker final")
        audio = transcriber.whisper_model.transcribe.call_args.args[0]
        self.assertEqual(audio.tolist(), [2 / 32768])


class TestMutedMicMessage(unittest.TestCase):
    @patch("controller.model")
    @patch("controller.config")
    def test_discards_queued_result_while_vrc_mic_is_muted(
        self,
        config,
        model,
    ) -> None:
        from controller import Controller

        config.VRC_MIC_MUTE_SYNC = True
        model.mic_mute_status = True

        Controller.__new__(Controller).micMessage({})

        self.assertEqual(model.method_calls, [])

    @patch("controller.model")
    @patch("controller.config")
    def test_partial_mic_result_only_updates_partial_ui(self, config, model) -> None:
        from controller import Controller

        config.VRC_MIC_MUTE_SYNC = False
        config.ENABLE_TRANSCRIPTION_SEND = True
        controller = Controller.__new__(Controller)
        controller.run_mapping = {"transcription_mic_partial": "/run/mic_partial"}
        controller.run = MagicMock()

        controller.micMessage({
            "text": "partial",
            "language": "Japanese",
            "is_final": False,
            "segment_id": 4,
            "inference_ms": 12.0,
            "audio_duration_ms": 1000.0,
        })

        controller.run.assert_called_once()
        self.assertEqual(controller.run.call_args.args[1], "/run/mic_partial")
        self.assertEqual(controller.run.call_args.args[2]["id"], "transcription-mic-4")
        self.assertEqual(model.method_calls, [])

    @patch("controller.model")
    @patch("controller.config")
    def test_partial_mic_result_respects_transcription_toggle(self, config, model) -> None:
        from controller import Controller

        config.VRC_MIC_MUTE_SYNC = False
        config.ENABLE_TRANSCRIPTION_SEND = False
        controller = Controller.__new__(Controller)
        controller.run_mapping = {"transcription_mic_partial": "/run/mic_partial"}
        controller.run = MagicMock()

        controller.micMessage({
            "text": "partial",
            "language": "Japanese",
            "is_final": False,
            "segment_id": 4,
        })

        controller.run.assert_not_called()
        self.assertEqual(model.method_calls, [])

    @patch("controller.model")
    @patch("controller.config")
    def test_empty_final_mic_result_dismisses_partial_ui(self, config, model) -> None:
        from controller import Controller

        config.VRC_MIC_MUTE_SYNC = False
        controller = Controller.__new__(Controller)
        controller.run_mapping = {"transcription_mic_partial": "/run/mic_partial"}
        controller.run = MagicMock()

        controller.micMessage({
            "text": "",
            "language": "Japanese",
            "is_final": True,
            "segment_id": 4,
        })

        controller.run.assert_called_once_with(
            200,
            "/run/mic_partial",
            {"id": "transcription-mic-4", "dismiss": True},
        )
        self.assertEqual(model.method_calls, [])


class TestSpeakerMessage(unittest.TestCase):
    @patch("controller.model")
    @patch("controller.config")
    def test_partial_speaker_result_only_updates_partial_ui(self, config, model) -> None:
        from controller import Controller

        config.ENABLE_TRANSCRIPTION_RECEIVE = True
        controller = Controller.__new__(Controller)
        controller.run_mapping = {"transcription_speaker_partial": "/run/speaker_partial"}
        controller.run = MagicMock()

        controller.speakerMessage({
            "text": "partial speaker",
            "language": "Japanese",
            "is_final": False,
            "segment_id": 7,
            "inference_ms": 10.0,
            "audio_duration_ms": 900.0,
        })

        controller.run.assert_called_once()
        self.assertEqual(controller.run.call_args.args[1], "/run/speaker_partial")
        self.assertEqual(controller.run.call_args.args[2]["id"], "transcription-speaker-7")
        self.assertEqual(model.method_calls, [])

    @patch("controller.model")
    @patch("controller.config")
    def test_partial_speaker_result_respects_transcription_toggle(self, config, model) -> None:
        from controller import Controller

        config.ENABLE_TRANSCRIPTION_RECEIVE = False
        controller = Controller.__new__(Controller)
        controller.run_mapping = {"transcription_speaker_partial": "/run/speaker_partial"}
        controller.run = MagicMock()

        controller.speakerMessage({
            "text": "partial speaker",
            "language": "Japanese",
            "is_final": False,
            "segment_id": 7,
        })

        controller.run.assert_not_called()
        self.assertEqual(model.method_calls, [])

    @patch("controller.model")
    @patch("controller.config")
    def test_empty_final_speaker_result_dismisses_partial_ui(self, config, model) -> None:
        from controller import Controller

        controller = Controller.__new__(Controller)
        controller.run_mapping = {"transcription_speaker_partial": "/run/speaker_partial"}
        controller.run = MagicMock()

        controller.speakerMessage({
            "text": "",
            "language": "Japanese",
            "is_final": True,
            "segment_id": 7,
        })

        controller.run.assert_called_once_with(
            200,
            "/run/speaker_partial",
            {"id": "transcription-speaker-7", "dismiss": True},
        )
        self.assertEqual(model.method_calls, [])

    @patch("controller.model")
    @patch("controller.config")
    def test_repeated_speaker_text_with_new_segment_still_translates(self, config, model) -> None:
        from controller import Controller

        config.ENABLE_TRANSLATION = True
        config.ENABLE_TRANSCRIPTION_RECEIVE = True
        config.CONVERT_MESSAGE_TO_HIRAGANA = False
        config.CONVERT_MESSAGE_TO_ROMAJI = False
        config.OVERLAY_SMALL_LOG = False
        config.OVERLAY_LARGE_LOG = False
        config.SEND_RECEIVED_MESSAGE_TO_VRC = False
        config.LOGGER_FEATURE = False
        config.SELECTED_TAB_NO = 0
        config.SELECTED_YOUR_LANGUAGES = {0: {"1": {"language": "Japanese", "enable": True}}}
        model.checkKeywords.return_value = False
        model.detectRepeatReceiveMessage.side_effect = [False, False]
        model.getOutputTranslate.return_value = (["translated"], [True])
        controller = Controller.__new__(Controller)
        controller.run_mapping = {"transcription_speaker": "/run/speaker"}
        controller.run = MagicMock()
        controller._is_overlay_available = MagicMock(return_value=False)

        payload = {
            "text": "let's go for a walk",
            "language": "English",
            "is_final": True,
        }
        controller.speakerMessage({**payload, "segment_id": 21})
        controller.speakerMessage({**payload, "segment_id": 22})

        self.assertEqual(model.detectRepeatReceiveMessage.call_args_list[0].args, ("let's go for a walk", 21))
        self.assertEqual(model.detectRepeatReceiveMessage.call_args_list[1].args, ("let's go for a walk", 22))
        self.assertEqual(model.getOutputTranslate.call_count, 2)


class TestRepeatDetection(unittest.TestCase):
    def test_receive_repeat_allows_same_text_for_new_segment(self) -> None:
        from model import Model

        model = Model.__new__(Model)
        model.previous_receive_message = ""
        model.previous_receive_segment_id = None

        self.assertFalse(model.detectRepeatReceiveMessage("same text", 1))
        self.assertFalse(model.detectRepeatReceiveMessage("same text", 2))
        self.assertTrue(model.detectRepeatReceiveMessage("same text", 2))

    def test_receive_repeat_blocks_same_segment_even_if_text_changes(self) -> None:
        from model import Model

        model = Model.__new__(Model)
        model.previous_receive_message = ""
        model.previous_receive_segment_id = None

        self.assertFalse(model.detectRepeatReceiveMessage("first text", 10))
        self.assertTrue(model.detectRepeatReceiveMessage("updated text", 10))

    def test_send_repeat_allows_same_text_for_new_segment(self) -> None:
        from model import Model

        model = Model.__new__(Model)
        model.previous_send_message = ""
        model.previous_send_segment_id = None

        self.assertFalse(model.detectRepeatSendMessage("same text", 1))
        self.assertFalse(model.detectRepeatSendMessage("same text", 2))
        self.assertTrue(model.detectRepeatSendMessage("same text", 2))

    def test_send_repeat_blocks_same_segment_even_if_text_changes(self) -> None:
        from model import Model

        model = Model.__new__(Model)
        model.previous_send_message = ""
        model.previous_send_segment_id = None

        self.assertFalse(model.detectRepeatSendMessage("first text", 10))
        self.assertTrue(model.detectRepeatSendMessage("updated text", 10))


if __name__ == "__main__":
    unittest.main()