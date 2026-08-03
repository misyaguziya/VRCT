import unittest
from unittest.mock import patch

from controller import Controller, config


class TestMicTranslationEngineLimitContract(unittest.TestCase):
    """Mic path must match the speaker/chat unified error contract (issue #91)."""

    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        self.controller.run_mapping = {"error_translation_engine": "error_translation_engine"}
        self.controller.changeToCTranslate2Process = lambda: None
        self.calls = []
        self.controller.run = lambda status, endpoint, result: self.calls.append((status, endpoint, result))

        self._original_config = {
            "VRC_MIC_MUTE_SYNC": config.VRC_MIC_MUTE_SYNC,
            "ENABLE_TRANSCRIPTION_SEND": config.ENABLE_TRANSCRIPTION_SEND,
            "ENABLE_TRANSLATION": config.ENABLE_TRANSLATION,
        }
        config.VRC_MIC_MUTE_SYNC = False
        config.ENABLE_TRANSCRIPTION_SEND = False
        config.ENABLE_TRANSLATION = True

    def tearDown(self) -> None:
        for key, value in self._original_config.items():
            setattr(config, key, value)

    @patch("controller.model.detectRepeatSendMessage", return_value=False)
    @patch("controller.model.checkKeywords", return_value=False)
    @patch("controller.model.telemetryTrackCoreFeature", lambda *_: None)
    @patch("controller.model.getInputTranslate", return_value=([], [False]))
    def test_mic_translation_limit_includes_error_code(self, *_mocks) -> None:
        self.controller.micMessage({"text": "hello", "language": "English", "is_final": True})

        self.assertEqual(len(self.calls), 1)
        status, endpoint, result = self.calls[0]
        self.assertEqual(status, 400)
        self.assertEqual(endpoint, "error_translation_engine")
        self.assertEqual(result.get("error_code"), "TRANSLATION_ENGINE_LIMIT")


class TestRecognitionErrorVisibility(unittest.TestCase):
    """Issue #103: surface Google recognition failures instead of silent drops."""

    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        self.controller.run_mapping = {"transcription_recognition_error": "transcription_recognition_error"}
        self.calls = []
        self.controller.run = lambda status, endpoint, result: self.calls.append((status, endpoint, result))

        self._original_vrc_mic_mute_sync = config.VRC_MIC_MUTE_SYNC
        config.VRC_MIC_MUTE_SYNC = False

    def tearDown(self) -> None:
        config.VRC_MIC_MUTE_SYNC = self._original_vrc_mic_mute_sync

    def test_mic_recognition_error_emits_system_notification(self) -> None:
        self.controller.micMessage({
            "text": "", "language": None, "is_final": True, "recognition_error": True,
        })

        self.assertEqual(len(self.calls), 1)
        status, endpoint, result = self.calls[0]
        self.assertEqual(status, 200)
        self.assertEqual(endpoint, "transcription_recognition_error")
        self.assertIn("Mic", result["message"])

    def test_speaker_recognition_error_emits_system_notification(self) -> None:
        self.controller.speakerMessage({
            "text": "", "language": None, "is_final": True, "recognition_error": True,
        })

        self.assertEqual(len(self.calls), 1)
        status, endpoint, result = self.calls[0]
        self.assertEqual(status, 200)
        self.assertEqual(endpoint, "transcription_recognition_error")
        self.assertIn("Speaker", result["message"])

    def test_no_notification_when_recognition_succeeds(self) -> None:
        self.controller.micMessage({
            "text": "", "language": None, "is_final": True, "recognition_error": False,
        })

        self.assertEqual(self.calls, [])


class TestAudioDeviceAccessLock(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        self.controller.device_access_status = True
        self.controller.progressBarMicEnergy = lambda _: None
        self.controller.progressBarSpeakerEnergy = lambda _: None

    @patch("controller.model.startCheckMicEnergy", side_effect=OSError("mic failed"))
    def test_releases_device_access_when_mic_energy_check_fails(self, _) -> None:
        with self.assertRaisesRegex(OSError, "mic failed"):
            self.controller.startCheckMicEnergy()

        self.assertTrue(self.controller.device_access_status)

    @patch("controller.model.startCheckSpeakerEnergy", side_effect=OSError("speaker failed"))
    def test_releases_device_access_when_speaker_energy_check_fails(self, _) -> None:
        with self.assertRaisesRegex(OSError, "speaker failed"):
            self.controller.startCheckSpeakerEnergy()

        self.assertTrue(self.controller.device_access_status)


if __name__ == "__main__":
    unittest.main()