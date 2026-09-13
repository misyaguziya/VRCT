import unittest
from threading import Lock
from unittest.mock import MagicMock, patch

import config as config_module
import controller as controller_module
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
        self.calls = []
        self.controller.run = lambda status, endpoint, result: self.calls.append((status, endpoint, result))

        self._original_vrc_mic_mute_sync = config.VRC_MIC_MUTE_SYNC
        self._original_enable_transcription_send = config.ENABLE_TRANSCRIPTION_SEND
        self._original_enable_transcription_receive = config.ENABLE_TRANSCRIPTION_RECEIVE
        config.VRC_MIC_MUTE_SYNC = False

    def tearDown(self) -> None:
        config.VRC_MIC_MUTE_SYNC = self._original_vrc_mic_mute_sync
        config.ENABLE_TRANSCRIPTION_SEND = self._original_enable_transcription_send
        config.ENABLE_TRANSCRIPTION_RECEIVE = self._original_enable_transcription_receive

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

    def test_structured_pipeline_error_is_forwarded_without_audio_payload(self) -> None:
        payload = {
            "error_code": "VAD_INFERENCE_ERROR",
            "stage": "vad",
            "source": "mic",
            "message": "Voice activity detection failed",
            "recoverable": False,
        }

        self.controller.micMessage({"recognition_error": True, **payload})

        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.calls[0], (200, "/set/disable/transcription_send", False))
        self.assertEqual(self.calls[1][2], payload)
        self.assertFalse(config.ENABLE_TRANSCRIPTION_SEND)

    def test_structured_speaker_pipeline_error_disables_receive(self) -> None:
        payload = {
            "error_code": "AUDIO_READ_ERROR",
            "stage": "recording",
            "source": "speaker",
            "message": "Audio capture failed",
            "recoverable": False,
        }

        self.controller.speakerMessage({"recognition_error": True, **payload})

        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.calls[0], (200, "/set/disable/transcription_receive", False))
        self.assertEqual(self.calls[1][2], payload)
        self.assertFalse(config.ENABLE_TRANSCRIPTION_RECEIVE)

    def test_pipeline_error_is_not_suppressed_while_mic_is_muted(self) -> None:
        payload = {
            "error_code": "AUDIO_READ_ERROR",
            "stage": "recording",
            "source": "mic",
            "message": "Audio capture failed",
            "recoverable": False,
        }
        config.VRC_MIC_MUTE_SYNC = True

        with patch("controller.model.mic_mute_status", True):
            self.controller.micMessage({"recognition_error": True, **payload})

        self.assertEqual(len(self.calls), 2)
        self.assertFalse(config.ENABLE_TRANSCRIPTION_SEND)


class TestTranscriptionEnableFailureState(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        self.controller.mic_lifecycle_lock = Lock()
        self.controller.speaker_lifecycle_lock = Lock()
        self._original_send = config.ENABLE_TRANSCRIPTION_SEND
        self._original_receive = config.ENABLE_TRANSCRIPTION_RECEIVE
        config.ENABLE_TRANSCRIPTION_SEND = False
        config.ENABLE_TRANSCRIPTION_RECEIVE = False

    def tearDown(self) -> None:
        config.ENABLE_TRANSCRIPTION_SEND = self._original_send
        config.ENABLE_TRANSCRIPTION_RECEIVE = self._original_receive

    @patch("controller.model.startMicTranscript", return_value=False)
    def test_mic_enable_returns_false_when_model_did_not_start(self, start_mic) -> None:
        response = self.controller.setEnableTranscriptionSend()

        self.assertEqual(response, {"status": 200, "result": False})
        self.assertFalse(config.ENABLE_TRANSCRIPTION_SEND)
        start_mic.assert_called_once()

    @patch("controller.model.startSpeakerTranscript", return_value=False)
    def test_speaker_enable_returns_false_when_model_did_not_start(self, start_speaker) -> None:
        response = self.controller.setEnableTranscriptionReceive()

        self.assertEqual(response, {"status": 200, "result": False})
        self.assertFalse(config.ENABLE_TRANSCRIPTION_RECEIVE)
        start_speaker.assert_called_once()


class TestTranscriptionVramStartFailureState(unittest.TestCase):
    """音声認識開始時の VRAM エラーが専用通知と OFF 同期を行う契約。"""

    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        self.controller.mic_lifecycle_lock = Lock()
        self.controller.speaker_lifecycle_lock = Lock()
        self.controller.run_mapping = {
            "error_transcription_mic_vram_overflow": "/run/error_transcription_mic_vram_overflow",
            "error_transcription_speaker_vram_overflow": "/run/error_transcription_speaker_vram_overflow",
            "disable_transcription_send": "/set/disable/transcription_send",
            "disable_transcription_receive": "/set/disable/transcription_receive",
        }
        self.run_calls = []
        self.controller.run = lambda status, endpoint, result: self.run_calls.append(
            (status, endpoint, result)
        )
        self._original_send = config.ENABLE_TRANSCRIPTION_SEND
        self._original_receive = config.ENABLE_TRANSCRIPTION_RECEIVE

    def tearDown(self) -> None:
        config.ENABLE_TRANSCRIPTION_SEND = self._original_send
        config.ENABLE_TRANSCRIPTION_RECEIVE = self._original_receive

    @patch("controller.model.stopMicTranscript")
    @patch("controller.model.detectVRAMError", return_value=(True, "out of memory"))
    @patch("controller.model.startMicTranscript", side_effect=RuntimeError("CUDA out of memory"))
    def test_mic_vram_failure_notifies_and_disables(self, _start, _detect, stop_mic) -> None:
        config.ENABLE_TRANSCRIPTION_SEND = True

        result = self.controller.startTranscriptionSendMessage()

        self.assertFalse(result)
        self.assertFalse(config.ENABLE_TRANSCRIPTION_SEND)
        self.assertEqual(self.run_calls[0][0:2], (400, "/run/error_transcription_mic_vram_overflow"))
        self.assertEqual(self.run_calls[0][2]["error_code"], "TRANSCRIPTION_VRAM_MIC")
        self.assertEqual(self.run_calls[1], (200, "/set/disable/transcription_send", False))
        stop_mic.assert_called_once_with()

    @patch("controller.model.stopSpeakerTranscript")
    @patch("controller.model.detectVRAMError", return_value=(True, "out of memory"))
    @patch("controller.model.startSpeakerTranscript", side_effect=RuntimeError("CUDA out of memory"))
    def test_speaker_vram_failure_notifies_and_disables(self, _start, _detect, stop_speaker) -> None:
        config.ENABLE_TRANSCRIPTION_RECEIVE = True

        result = self.controller.startTranscriptionReceiveMessage()

        self.assertFalse(result)
        self.assertFalse(config.ENABLE_TRANSCRIPTION_RECEIVE)
        self.assertEqual(
            self.run_calls[0][0:2],
            (400, "/run/error_transcription_speaker_vram_overflow"),
        )
        self.assertEqual(self.run_calls[0][2]["error_code"], "TRANSCRIPTION_VRAM_SPEAKER")
        self.assertEqual(self.run_calls[1], (200, "/set/disable/transcription_receive", False))
        stop_speaker.assert_called_once_with()


class TestDeviceSelectionRecovery(unittest.TestCase):
    """デバイス抜去後に stale な選択値を残さない契約。"""

    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        self.controller.mic_lifecycle_lock = Lock()
        self.controller.speaker_lifecycle_lock = Lock()
        self.controller.run_mapping = {
            "selected_mic_host": "/run/selected_mic_host",
            "selected_mic_device": "/run/selected_mic_device",
            "selected_speaker_device": "/run/selected_speaker_device",
            "selectable_mic_device_list": "/run/selectable_mic_device_list",
            "selectable_speaker_device_list": "/run/selectable_speaker_device_list",
            "disable_transcription_send": "/set/disable/transcription_send",
            "disable_transcription_receive": "/set/disable/transcription_receive",
            "disable_check_mic_threshold": "/set/disable/check_mic_threshold",
            "disable_check_speaker_threshold": "/set/disable/check_speaker_threshold",
        }
        self.calls = []
        self.controller.run = lambda status, endpoint, result: self.calls.append(
            (status, endpoint, result)
        )
        self._original = {
            "mic_host": config._SELECTED_MIC_HOST,
            "mic_device": config._SELECTED_MIC_DEVICE,
            "speaker_device": config._SELECTED_SPEAKER_DEVICE,
            "auto_mic": config.AUTO_MIC_SELECT,
            "auto_speaker": config.AUTO_SPEAKER_SELECT,
            "send": config.ENABLE_TRANSCRIPTION_SEND,
            "receive": config.ENABLE_TRANSCRIPTION_RECEIVE,
            "mic_energy": config.ENABLE_CHECK_ENERGY_SEND,
            "speaker_energy": config.ENABLE_CHECK_ENERGY_RECEIVE,
        }

    def tearDown(self) -> None:
        config._SELECTED_MIC_HOST = self._original["mic_host"]
        config._SELECTED_MIC_DEVICE = self._original["mic_device"]
        config._SELECTED_SPEAKER_DEVICE = self._original["speaker_device"]
        config.AUTO_MIC_SELECT = self._original["auto_mic"]
        config.AUTO_SPEAKER_SELECT = self._original["auto_speaker"]
        config.ENABLE_TRANSCRIPTION_SEND = self._original["send"]
        config.ENABLE_TRANSCRIPTION_RECEIVE = self._original["receive"]
        config.ENABLE_CHECK_ENERGY_SEND = self._original["mic_energy"]
        config.ENABLE_CHECK_ENERGY_RECEIVE = self._original["speaker_energy"]

    def test_mic_auto_select_follows_detected_default(self) -> None:
        mock_device_manager = MagicMock()
        mock_device_manager.getMicDevices.return_value = {
            "HostB": [{"name": "MicB", "index": 2}],
        }
        mock_device_manager.getDefaultMicDevice.return_value = {
            "host": {"name": "HostB"},
            "device": {"name": "MicB"},
        }
        config._SELECTED_MIC_HOST = "HostA"
        config._SELECTED_MIC_DEVICE = "MicA"
        config.AUTO_MIC_SELECT = True

        with patch.object(controller_module, "device_manager", mock_device_manager), \
             patch.object(config_module, "device_manager", mock_device_manager), \
             patch.object(controller_module.model, "getListMicDevice", return_value=["MicB"]):
            self.controller.updateMicDeviceList()

        self.assertEqual(config.SELECTED_MIC_HOST, "HostB")
        self.assertEqual(config.SELECTED_MIC_DEVICE, "MicB")
        self.assertNotIn(
            (200, "/set/disable/transcription_send", False),
            self.calls,
        )

    def test_mic_auto_select_falls_back_to_detected_device_when_default_is_missing(self) -> None:
        mock_device_manager = MagicMock()
        mock_device_manager.getMicDevices.return_value = {
            "HostB": [{"name": "MicB", "index": 2}],
        }
        mock_device_manager.getDefaultMicDevice.return_value = {
            "host": {"name": "NoHost"},
            "device": {"name": "NoDevice"},
        }
        config._SELECTED_MIC_HOST = "HostA"
        config._SELECTED_MIC_DEVICE = "MicA"
        config.AUTO_MIC_SELECT = True

        with patch.object(controller_module, "device_manager", mock_device_manager), \
             patch.object(config_module, "device_manager", mock_device_manager), \
             patch.object(controller_module.model, "getListMicDevice", return_value=["MicB"]):
            self.controller.updateMicDeviceList()

        self.assertEqual(config.SELECTED_MIC_HOST, "HostB")
        self.assertEqual(config.SELECTED_MIC_DEVICE, "MicB")
        self.assertNotIn(
            (200, "/set/disable/transcription_send", False),
            self.calls,
        )

    def test_mic_manual_select_switches_to_detected_device(self) -> None:
        mock_device_manager = MagicMock()
        mock_device_manager.getMicDevices.return_value = {
            "HostB": [{"name": "MicB", "index": 2}],
        }
        config._SELECTED_MIC_HOST = "HostA"
        config._SELECTED_MIC_DEVICE = "MicA"
        config.AUTO_MIC_SELECT = False
        config.ENABLE_TRANSCRIPTION_SEND = True
        config.ENABLE_CHECK_ENERGY_SEND = False
        mock_worker = MagicMock()

        with patch.object(controller_module, "device_manager", mock_device_manager), \
             patch.object(config_module, "device_manager", mock_device_manager), \
             patch.object(controller_module.model, "mic_lifecycle_worker", mock_worker, create=True), \
             patch.object(controller_module.model, "getListMicDevice", return_value=["MicB"]):
            self.controller.updateMicDeviceList()

        self.assertEqual(config.SELECTED_MIC_HOST, "HostB")
        self.assertEqual(config.SELECTED_MIC_DEVICE, "MicB")
        self.assertTrue(config.ENABLE_TRANSCRIPTION_SEND)
        self.assertNotIn((200, "/set/disable/transcription_send", False), self.calls)
        mock_worker.enqueue.assert_called_once()

    def test_speaker_auto_select_follows_detected_default(self) -> None:
        mock_device_manager = MagicMock()
        mock_device_manager.getSpeakerDevices.return_value = [
            {"name": "SpeakerB", "index": 2},
        ]
        mock_device_manager.getDefaultSpeakerDevice.return_value = {
            "device": {"name": "SpeakerB"},
        }
        config._SELECTED_SPEAKER_DEVICE = "SpeakerA"
        config.AUTO_SPEAKER_SELECT = True

        with patch.object(controller_module, "device_manager", mock_device_manager), \
             patch.object(config_module, "device_manager", mock_device_manager), \
             patch.object(controller_module.model, "getListSpeakerDevice", return_value=["SpeakerB"]):
            self.controller.updateSpeakerDeviceList()

        self.assertEqual(config.SELECTED_SPEAKER_DEVICE, "SpeakerB")
        self.assertNotIn(
            (200, "/set/disable/transcription_receive", False),
            self.calls,
        )

    def test_speaker_auto_select_falls_back_to_detected_device_when_default_is_missing(self) -> None:
        mock_device_manager = MagicMock()
        mock_device_manager.getSpeakerDevices.return_value = [
            {"name": "SpeakerB", "index": 2},
        ]
        mock_device_manager.getDefaultSpeakerDevice.return_value = {
            "device": {"name": "NoDevice"},
        }
        config._SELECTED_SPEAKER_DEVICE = "SpeakerA"
        config.AUTO_SPEAKER_SELECT = True

        with patch.object(controller_module, "device_manager", mock_device_manager), \
             patch.object(config_module, "device_manager", mock_device_manager), \
             patch.object(controller_module.model, "getListSpeakerDevice", return_value=["SpeakerB"]):
            self.controller.updateSpeakerDeviceList()

        self.assertEqual(config.SELECTED_SPEAKER_DEVICE, "SpeakerB")
        self.assertNotIn(
            (200, "/set/disable/transcription_receive", False),
            self.calls,
        )

    def test_speaker_manual_select_switches_to_detected_device(self) -> None:
        mock_device_manager = MagicMock()
        mock_device_manager.getSpeakerDevices.return_value = [
            {"name": "SpeakerB", "index": 2},
        ]
        config._SELECTED_SPEAKER_DEVICE = "SpeakerA"
        config.AUTO_SPEAKER_SELECT = False
        config.ENABLE_TRANSCRIPTION_RECEIVE = True
        config.ENABLE_CHECK_ENERGY_RECEIVE = False
        mock_worker = MagicMock()

        with patch.object(controller_module, "device_manager", mock_device_manager), \
             patch.object(config_module, "device_manager", mock_device_manager), \
             patch.object(controller_module.model, "speaker_lifecycle_worker", mock_worker, create=True), \
             patch.object(controller_module.model, "getListSpeakerDevice", return_value=["SpeakerB"]):
            self.controller.updateSpeakerDeviceList()

        self.assertEqual(config.SELECTED_SPEAKER_DEVICE, "SpeakerB")
        self.assertTrue(config.ENABLE_TRANSCRIPTION_RECEIVE)
        self.assertNotIn((200, "/set/disable/transcription_receive", False), self.calls)
        mock_worker.enqueue.assert_called_once()


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
    # mic/speaker_lifecycle_worker はプロセス全体で共有される実インスタンス
    # (Model.__init__ で1回だけ生成)。ここを個別にpatchせずに shutdown() を
    # 呼ぶと、実物の .stop() が呼ばれて _stopped=True のまま元に戻せず、
    # 同じプロセス内で後から走る他のテストに影響しうる (コードレビュー指摘)。
    @patch("controller.model.speaker_lifecycle_worker")
    @patch("controller.model.mic_lifecycle_worker")
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
        # (逆順だと _syncMonitoringLifecycleLocked が「もう片方はまだ active」と
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
    @patch("controller.model.speaker_lifecycle_worker")
    @patch("controller.model.mic_lifecycle_worker")
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
