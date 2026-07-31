import unittest
from unittest.mock import patch

from controller import Controller
from models.transcription.transcription_transcriber import AudioTranscriber, _should_use_vad_filter


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


class TestWhisperVadFilter(unittest.TestCase):
    def test_enables_vad_for_turbo_models(self) -> None:
        self.assertTrue(_should_use_vad_filter(False, "large-v3-turbo"))
        self.assertTrue(_should_use_vad_filter(False, "large-v3-turbo-int8"))

    def test_preserves_vad_setting_for_other_models(self) -> None:
        self.assertFalse(_should_use_vad_filter(False, "large-v3"))
        self.assertTrue(_should_use_vad_filter(True, "large-v3"))


class TestMutedMicMessage(unittest.TestCase):
    @patch("controller.model")
    @patch("controller.config")
    def test_discards_queued_result_while_vrc_mic_is_muted(
        self,
        config,
        model,
    ) -> None:
        config.VRC_MIC_MUTE_SYNC = True
        model.mic_mute_status = True

        Controller.__new__(Controller).micMessage({})

        self.assertEqual(model.method_calls, [])


if __name__ == "__main__":
    unittest.main()