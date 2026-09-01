import unittest
from threading import Lock
from unittest.mock import patch

from controller import Controller, config


class TestMicTranslationEngineLimitContract(unittest.TestCase):
    """Mic path must match the speaker/chat unified error contract (issue #91)."""

    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        self.controller.run_mapping = {"error_translation_engine": "error_translation_engine"}
        self.controller.changeToCTranslate2Process = lambda: None
        self.controller._pending_partial_transcripts = {}
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
    @patch("controller.model.telemetryTrackError", lambda *_: None)
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
        self.controller._pending_partial_transcripts = {}
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
        self.controller.mic_lifecycle_lock = Lock()
        self.controller.speaker_lifecycle_lock = Lock()
        self.controller.progressBarMicEnergy = lambda _: None
        self.controller.progressBarSpeakerEnergy = lambda _: None

    @patch("controller.model.startCheckMicEnergy", side_effect=OSError("mic failed"))
    def test_releases_device_access_when_mic_energy_check_fails(self, _) -> None:
        with self.assertRaisesRegex(OSError, "mic failed"):
            self.controller.startCheckMicEnergy()

        self.assertFalse(self.controller.mic_lifecycle_lock.locked())

    @patch("controller.model.startCheckSpeakerEnergy", side_effect=OSError("speaker failed"))
    def test_releases_device_access_when_speaker_energy_check_fails(self, _) -> None:
        with self.assertRaisesRegex(OSError, "speaker failed"):
            self.controller.startCheckSpeakerEnergy()

        self.assertFalse(self.controller.speaker_lifecycle_lock.locked())


class TestShutdownStopsAutoSelectTrackers(unittest.TestCase):
    """Auto Mic/Speaker Select 有効時、ActiveEndpointTracker は
    setMicAutoActive(False)/setSpeakerAutoActive(False) を呼ばない限り
    止まらない (stopMonitoring は別スレッドの監視ループのみを止める)。
    shutdown() でこれを呼ばずに終了すると、tracker が COM 呼び出しの
    途中でプロセスごと終了しうる (CoUninitialize されないまま COM
    ポインタが破棄され access violation につながる経路、実機で確認済み)。
    """

    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        # shutdown() は mic/speaker_lifecycle_lock を取得してから
        # 停止関数を呼ぶ (ロードマップ項目 5)。__init__ をバイパスしている
        # ためここで明示的にシードする。
        self.controller.mic_lifecycle_lock = Lock()
        self.controller.speaker_lifecycle_lock = Lock()

    @patch("controller.model.telemetryShutdown", return_value=None)
    @patch("controller.config.saveConfigToFile", return_value=None)
    @patch("controller.model.stopCheckSpeakerEnergy", return_value=None)
    @patch("controller.model.stopCheckMicEnergy", return_value=None)
    @patch("controller.model.stopSpeakerTranscript", return_value=None)
    @patch("controller.model.stopMicTranscript", return_value=None)
    @patch("controller.device_manager")
    def test_stops_both_trackers_before_stopping_monitoring(self, mock_device_manager, *_mocks) -> None:
        calls = []
        mock_device_manager.setMicAutoActive.side_effect = lambda active: calls.append(
            ("setMicAutoActive", active)
        )
        mock_device_manager.setSpeakerAutoActive.side_effect = lambda active: calls.append(
            ("setSpeakerAutoActive", active)
        )
        mock_device_manager.stopMonitoring.side_effect = lambda: calls.append(("stopMonitoring",))

        result = self.controller.shutdown()

        self.assertEqual(result, {"status": 200, "result": True})
        self.assertIn(("setMicAutoActive", False), calls)
        self.assertIn(("setSpeakerAutoActive", False), calls)
        # tracker を明示停止してから stopMonitoring() を呼ぶこと
        # (逆順だと _syncMonitoringLifecycle が「もう片方はまだ active」と
        # 見て監視スレッドを再起動してしまう、詳細は shutdown() のコメント参照)。
        self.assertLess(calls.index(("setMicAutoActive", False)), calls.index(("stopMonitoring",)))
        self.assertLess(calls.index(("setSpeakerAutoActive", False)), calls.index(("stopMonitoring",)))

    @patch("controller.errorLogging")
    @patch("controller.model.telemetryShutdown", return_value=None)
    @patch("controller.config.saveConfigToFile", return_value=None)
    @patch("controller.model.stopCheckSpeakerEnergy", return_value=None)
    @patch("controller.model.stopCheckMicEnergy", return_value=None)
    @patch("controller.model.stopSpeakerTranscript", return_value=None)
    @patch("controller.model.stopMicTranscript", return_value=None)
    @patch("controller.device_manager")
    def test_other_shutdown_steps_still_run_if_tracker_stop_raises(
        self, mock_device_manager, _mock_error_logging, *_mocks
    ) -> None:
        mock_device_manager.setMicAutoActive.side_effect = RuntimeError("boom")

        result = self.controller.shutdown()

        self.assertEqual(result, {"status": 200, "result": True})
        mock_device_manager.setSpeakerAutoActive.assert_called_once_with(False)
        mock_device_manager.stopMonitoring.assert_called_once()


if __name__ == "__main__":
    unittest.main()