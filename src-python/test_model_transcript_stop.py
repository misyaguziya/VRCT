import time
import unittest
from threading import Event
from unittest.mock import patch

import model as model_module
from model import model, threadFnc


class TestTranscriptStopJoinTimeout(unittest.TestCase):
    """Issue #63: stopping transcription must not block forever when the
    recognition worker is stuck (e.g. Google recognizer hanging on a bad
    network)."""

    def setUp(self) -> None:
        self._ensure_initialized_patch = patch.object(model, "ensure_initialized", lambda: None)
        self._ensure_initialized_patch.start()
        self._never_stop = Event()

    def tearDown(self) -> None:
        self._never_stop.set()
        self._ensure_initialized_patch.stop()
        model.mic_print_transcript = None
        model.speaker_print_transcript = None

    def _start_stuck_thread(self) -> threadFnc:
        def blocking_fn() -> None:
            self._never_stop.wait()

        thread = threadFnc(blocking_fn)
        thread.daemon = True
        thread.start()
        time.sleep(0.05)
        return thread

    @patch.object(model_module, "TRANSCRIPT_STOP_JOIN_TIMEOUT", 0.2)
    @patch("model.printLog")
    def test_stop_mic_transcript_returns_when_worker_is_stuck(self, mock_print_log) -> None:
        model.mic_print_transcript = self._start_stuck_thread()
        model.mic_audio_recorder = None

        started = time.perf_counter()
        model.stopMicTranscript()
        elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 2)
        mock_print_log.assert_called_once()

    @patch.object(model_module, "TRANSCRIPT_STOP_JOIN_TIMEOUT", 0.2)
    @patch("model.printLog")
    def test_stop_speaker_transcript_returns_when_worker_is_stuck(self, mock_print_log) -> None:
        model.speaker_print_transcript = self._start_stuck_thread()
        model.speaker_audio_recorder = None

        started = time.perf_counter()
        model.stopSpeakerTranscript()
        elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 2)
        mock_print_log.assert_called_once()


if __name__ == "__main__":
    unittest.main()
