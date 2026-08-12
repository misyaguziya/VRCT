import threading
import unittest
from unittest.mock import patch

import model as model_module
from model import model, config


class _FakeAudioTranscriber:
    """Stand-in for AudioTranscriber that satisfies the isinstance() checks
    in model.py while letting the test control transcribeAudioQueue/getTranscript."""

    last_recognition_error = True

    def __init__(self, *args, **kwargs) -> None:
        pass

    def transcribeAudioQueue(self, *args, **kwargs) -> bool:
        return True

    def getTranscript(self) -> dict:
        return {"text": "", "language": None}


class _FakeAudioRecorder:
    """Stand-in for SelectedMic/SpeakerEnergyAndAudioRecorder.

    model.py checks `isinstance(recorder, SelectedMic/SpeakerEnergyAndAudioRecorder)`
    in several places (device_error_event polling, stop/resume/pause). Patching
    the class itself with a plain MagicMock breaks those isinstance() checks
    (MagicMock instances aren't usable as an isinstance() second argument), so
    tests substitute this real dummy class instead.
    """

    def __init__(self, *args, **kwargs) -> None:
        self.device_error_event = threading.Event()

    def recordIntoQueue(self, *args, **kwargs) -> None:
        pass

    def resume(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def stop(self, *args, **kwargs) -> None:
        pass


class _CapturingThreadFnc:
    """Stand-in for model.threadFnc that captures the worker callable instead
    of starting a real background thread."""

    instances = []

    def __init__(self, fnc, end_fnc=None, daemon=True, *args, **kwargs):
        self.fnc = fnc
        self.end_fnc = end_fnc
        self.daemon = daemon
        _CapturingThreadFnc.instances.append(self)

    def start(self) -> None:
        pass


class TestTranscriptResultCarriesRecognitionError(unittest.TestCase):
    """Issue #103: the last_recognition_error flag set on AudioTranscriber
    must actually reach the controller callback via the result dict, not
    just exist in isolation on the transcriber."""

    def setUp(self) -> None:
        _CapturingThreadFnc.instances.clear()
        self._ensure_initialized_patch = patch.object(model, "ensure_initialized", lambda: None)
        self._ensure_initialized_patch.start()

        # ensure_initialized() is stubbed above, so model.init()'s attribute
        # setup (mic_print_transcript, mic_audio_recorder, etc.) never runs.
        # startMicTranscript/startSpeakerTranscript now call stopMicTranscript/
        # stopSpeakerTranscript defensively before opening a new device, which
        # reads these attributes, so seed them here rather than relying on
        # another test in the suite having already called model.init().
        model.mic_print_transcript = None
        model.mic_audio_recorder = None
        model.mic_transcriber = None
        model.speaker_print_transcript = None
        model.speaker_audio_recorder = None
        model.speaker_transcriber = None

        # SELECTED_MIC_* / SELECTED_SPEAKER_DEVICE are ValidatedProperty
        # descriptors that reject values not present in the real device list.
        # Bypass validation by writing the private attribute directly so the
        # test is independent of whatever hardware/config.json this machine has.
        self._original_mic_host = config._SELECTED_MIC_HOST
        self._original_mic_device = config._SELECTED_MIC_DEVICE
        self._original_speaker_device = config._SELECTED_SPEAKER_DEVICE
        config._SELECTED_MIC_HOST = "TestMicHost"
        config._SELECTED_MIC_DEVICE = "TestMicDevice"
        config._SELECTED_SPEAKER_DEVICE = "TestSpeakerDevice"

    def tearDown(self) -> None:
        self._ensure_initialized_patch.stop()
        config._SELECTED_MIC_HOST = self._original_mic_host
        config._SELECTED_MIC_DEVICE = self._original_mic_device
        config._SELECTED_SPEAKER_DEVICE = self._original_speaker_device
        model.mic_print_transcript = None
        model.mic_audio_recorder = None
        model.speaker_print_transcript = None
        model.speaker_audio_recorder = None
        model.mic_transcriber = None
        model.speaker_transcriber = None

    @patch.object(model_module, "threadFnc", _CapturingThreadFnc)
    @patch("model.AudioTranscriber", _FakeAudioTranscriber)
    @patch("model.SelectedMicEnergyAndAudioRecorder", _FakeAudioRecorder)
    @patch("model.device_manager")
    def test_mic_result_includes_recognition_error_flag(self, mock_device_manager) -> None:
        mock_device_manager.getMicDevices.return_value = {"TestMicHost": [{"name": "TestMicDevice"}]}

        received = []
        with patch.object(model, "changeMicTranscriptStatus", lambda: None):
            model.startMicTranscript(lambda result: received.append(result))

        self.assertEqual(len(_CapturingThreadFnc.instances), 1)
        _CapturingThreadFnc.instances[0].fnc()

        self.assertEqual(len(received), 1)
        self.assertTrue(received[0]["recognition_error"])

    @patch.object(model_module, "threadFnc", _CapturingThreadFnc)
    @patch("model.AudioTranscriber", _FakeAudioTranscriber)
    @patch("model.SelectedSpeakerEnergyAndAudioRecorder", _FakeAudioRecorder)
    @patch("model.device_manager")
    def test_speaker_result_includes_recognition_error_flag(self, mock_device_manager) -> None:
        mock_device_manager.getSpeakerDevices.return_value = [{"name": "TestSpeakerDevice"}]

        received = []
        model.startSpeakerTranscript(lambda result: received.append(result))

        self.assertEqual(len(_CapturingThreadFnc.instances), 1)
        _CapturingThreadFnc.instances[0].fnc()

        self.assertEqual(len(received), 1)
        self.assertTrue(received[0]["recognition_error"])


if __name__ == "__main__":
    unittest.main()
