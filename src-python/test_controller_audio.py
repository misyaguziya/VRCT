import unittest
from unittest.mock import patch

from controller import Controller


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