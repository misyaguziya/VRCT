import unittest
from unittest.mock import patch

from controller import Controller
from models.transcription.transcription_transcriber import _should_use_vad_filter


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