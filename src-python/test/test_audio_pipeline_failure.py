"""音声パイプラインの停止・通知・rollback の結合テスト。"""

import threading
import unittest
from unittest.mock import MagicMock, patch

import model as model_module
from errors import AudioPipelineError, AudioPipelineFailure, ErrorCode
from model import MicSession


DEVICE = {"name": "MicA", "index": 3}


class _FakeRecorder:
    def __init__(self, failure=None, stop_fn=None) -> None:
        self.device_error_event = threading.Event()
        self.device_error_info = failure
        self.resume = MagicMock()
        self.stop = stop_fn or MagicMock()
        self.audio_queue = None

    def recordIntoQueue(self, audio_queue, _energy_queue=None) -> None:
        self.audio_queue = audio_queue


class _PartiallyInitializedRecorder:
    """recordIntoQueue 失敗時の未初期化ハンドルを再現する。"""

    def __init__(self) -> None:
        self.device_error_event = threading.Event()
        self.device_error_info = None
        self.resume = None
        self.stop = None

    def recordIntoQueue(self, _audio_queue, _energy_queue=None) -> None:
        raise OSError("audio listener failed")


class _FakeTranscriber:
    last_recognition_error = False

    def getTranscript(self) -> dict:
        return {"text": "", "language": None}


class _FailingTranscriber(_FakeTranscriber):
    def transcribeAudioQueue(self, *_args, **_kwargs) -> bool:
        raise AudioPipelineError(
            AudioPipelineFailure(
                ErrorCode.ASR_ERROR,
                "asr",
                "mic",
                "Speech recognition failed",
                "RuntimeError",
            )
        )


class TestAudioPipelineFailure(unittest.TestCase):
    def test_recorder_creation_failure_rolls_back_and_notifies(self) -> None:
        received = []
        session = MicSession()
        session.transcript_fnc = received.append

        with patch.object(
            session, "_create_recorder", side_effect=OSError("device open failed")
        ):
            with self.assertRaises(OSError):
                session.reconfigure(transcript=True, device=DEVICE)

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["error_code"], ErrorCode.AUDIO_OPEN_ERROR.value)
        self.assertEqual(received[0]["stage"], "recording")
        self.assertEqual(received[0]["source"], "mic")
        self.assertEqual(session.features, set())
        self.assertIsNone(session._active_device)
        self.assertIsNone(session._recorder)

    def test_record_into_queue_failure_rolls_back_partial_recorder(self) -> None:
        recorder = _PartiallyInitializedRecorder()
        received = []
        session = MicSession()
        session.transcript_fnc = received.append

        with patch.object(session, "_create_recorder", return_value=recorder):
            with self.assertRaises(OSError):
                session.reconfigure(transcript=True, device=DEVICE)

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["error_code"], ErrorCode.AUDIO_READ_ERROR.value)
        self.assertEqual(received[0]["stage"], "recording")
        self.assertEqual(received[0]["source"], "mic")
        self.assertEqual(session.features, set())
        self.assertIsNone(session._active_device)
        self.assertIsNone(session._recorder)

    def test_transcriber_initialization_failure_rolls_back_and_notifies(self) -> None:
        recorder = _FakeRecorder()
        received = []
        session = MicSession()
        session.transcript_fnc = received.append

        with patch.object(session, "_create_recorder", return_value=recorder), patch.object(
            session, "_create_transcriber", side_effect=RuntimeError("model init failed")
        ):
            with self.assertRaises(RuntimeError):
                session.reconfigure(transcript=True, device=DEVICE)

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["error_code"], ErrorCode.TRANSCRIBER_INIT_ERROR.value)
        self.assertEqual(received[0]["stage"], "asr")
        self.assertEqual(received[0]["source"], "mic")
        self.assertFalse(received[0]["recoverable"])
        recorder.stop.assert_called_once_with(wait_for_stop=True)
        self.assertEqual(session.features, set())
        self.assertIsNone(session._recorder)

    def test_runtime_recorder_failure_stops_and_notifies_once(self) -> None:
        failure = AudioPipelineFailure(
            ErrorCode.AUDIO_READ_ERROR,
            "recording",
            "mic",
            "Mic audio capture failed",
            "OSError",
        )
        recorder = _FakeRecorder(failure=failure)
        recorder.device_error_event.set()
        received = []
        session = MicSession()
        session.transcript_fnc = received.append

        with patch.object(session, "_create_recorder", return_value=recorder), patch.object(
            session, "_create_transcriber", return_value=_FakeTranscriber()
        ):
            session.reconfigure(transcript=True, device=DEVICE)

        self.assertTrue(self._wait_for(lambda: len(received) == 1))
        self.assertEqual(received[0]["error_code"], ErrorCode.AUDIO_READ_ERROR.value)
        self.assertEqual(received[0]["stage"], "recording")
        recorder.stop.assert_called_once_with(wait_for_stop=True)
        self.assertEqual(session.features, set())

    def test_runtime_asr_failure_stops_and_notifies_once(self) -> None:
        recorder = _FakeRecorder()
        received = []
        session = MicSession()
        session.transcript_fnc = received.append

        with patch.object(session, "_create_recorder", return_value=recorder), patch.object(
            session, "_create_transcriber", return_value=_FailingTranscriber()
        ):
            session.reconfigure(transcript=True, device=DEVICE)

        self.assertTrue(self._wait_for(lambda: len(received) == 1))
        self.assertEqual(received[0]["error_code"], ErrorCode.ASR_ERROR.value)
        self.assertEqual(received[0]["stage"], "asr")
        self.assertEqual(received[0]["source"], "mic")
        recorder.stop.assert_called_once_with(wait_for_stop=True)
        self.assertEqual(session.features, set())

    def test_cleanup_timeout_is_reported_as_a_separate_error(self) -> None:
        release_stop = threading.Event()

        def blocked_stop(wait_for_stop=True) -> None:
            release_stop.wait()

        failure = AudioPipelineFailure(
            ErrorCode.AUDIO_READ_ERROR,
            "recording",
            "mic",
            "Mic audio capture failed",
            "OSError",
        )
        recorder = _FakeRecorder(failure=failure, stop_fn=blocked_stop)
        recorder.device_error_event.set()
        received = []
        session = MicSession()
        session.transcript_fnc = received.append

        try:
            with patch.object(model_module, "TRANSCRIPT_STOP_JOIN_TIMEOUT", 0.02), patch.object(
                session, "_create_recorder", return_value=recorder
            ), patch.object(session, "_create_transcriber", return_value=_FakeTranscriber()):
                session.reconfigure(transcript=True, device=DEVICE)
                self.assertTrue(self._wait_for(lambda: len(received) == 1))
                self.assertEqual(received[0]["error_code"], ErrorCode.CLEANUP_TIMEOUT.value)
                self.assertEqual(received[0]["stage"], "cleanup")
        finally:
            release_stop.set()

    @staticmethod
    def _wait_for(predicate, timeout: float = 2.0) -> bool:
        deadline = threading.Event()
        while not predicate():
            if deadline.wait(0.01):
                return False
            timeout -= 0.01
            if timeout <= 0:
                return False
        return True


if __name__ == "__main__":
    unittest.main()
