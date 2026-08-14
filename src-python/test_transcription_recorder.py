"""Tests for transcription_recorder.

`BaseEnergyAndAudioRecorder` は speech_recognition.Recognizer を用いた
`listen_in_background` に発話区間検出とフレーズ境界を委ねる (ADR-0004)。
このため統合的な入力→キュー投入までの検証は listen_in_background 側の
ロジックに寄りかかるが、ここでは以下のみを直接テストする:

- `_create_microphone` の fallback 動作
- 公開 API (`recordIntoQueue`) が listen_in_background 側の stop/pause/resume を
  正しく self.stop/self.pause/self.resume に受け取ること
- audio callback 内で SAMPLE_WIDTH と audioop.rms が接続されていること
"""

import unittest
from queue import Queue
from unittest.mock import patch, MagicMock

from models.transcription.transcription_recorder import BaseEnergyAndAudioRecorder, _create_microphone


class FakeAudioSource:
    def __init__(self, opens: bool) -> None:
        self.opens = opens
        self.stream = None
        self.exit_called = False

    def __enter__(self):
        if self.opens:
            self.stream = object()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.exit_called = True
        if self.stream is None:
            raise AttributeError("'NoneType' object has no attribute 'close'")
        self.stream = None


class RecorderAudioSource:
    SAMPLE_RATE = 48000
    SAMPLE_WIDTH = 2
    channels = 2


class TestCreateMicrophone(unittest.TestCase):
    def test_falls_back_without_closing_unopened_stream(self) -> None:
        selected_source = FakeAudioSource(opens=False)
        default_source = FakeAudioSource(opens=True)

        with patch(
            "models.transcription.transcription_recorder.Microphone",
            side_effect=[selected_source, default_source],
        ):
            source = _create_microphone({}, device_index=10)

        self.assertIs(source, default_source)
        self.assertFalse(selected_source.exit_called)
        self.assertTrue(default_source.exit_called)

    def test_raises_clear_error_when_no_device_opens(self) -> None:
        selected_source = FakeAudioSource(opens=False)
        default_source = FakeAudioSource(opens=False)

        with patch(
            "models.transcription.transcription_recorder.Microphone",
            side_effect=[selected_source, default_source],
        ):
            with self.assertRaisesRegex(OSError, "audio devices could not be opened"):
                _create_microphone({}, device_index=10)

        self.assertFalse(selected_source.exit_called)
        self.assertFalse(default_source.exit_called)


class TestRecorderPipeline(unittest.TestCase):
    def test_exposes_source_sample_format(self) -> None:
        recorder = BaseEnergyAndAudioRecorder(
            RecorderAudioSource(),
            energy_threshold=300,
            dynamic_energy_threshold=False,
            phrase_time_limit=3,
            record_timeout=5,
        )

        self.assertEqual(recorder.SAMPLE_RATE, 48000)
        self.assertEqual(recorder.SAMPLE_WIDTH, 2)
        self.assertEqual(recorder.channels, 2)

    def test_recordIntoQueue_wires_listen_in_background_control_handles(self) -> None:
        recorder = BaseEnergyAndAudioRecorder(
            RecorderAudioSource(),
            energy_threshold=300,
            dynamic_energy_threshold=False,
            phrase_time_limit=3,
            record_timeout=5,
        )
        stop = MagicMock(name="stop")
        pause = MagicMock(name="pause")
        resume = MagicMock(name="resume")
        recorder.recorder = MagicMock()
        recorder.recorder.listen_in_background = MagicMock(return_value=(stop, pause, resume))

        recorder.recordIntoQueue(Queue())

        self.assertIs(recorder.stop, stop)
        self.assertIs(recorder.pause, pause)
        self.assertIs(recorder.resume, resume)
        recorder.recorder.listen_in_background.assert_called_once()
        _, kwargs = recorder.recorder.listen_in_background.call_args
        self.assertEqual(kwargs.get("phrase_time_limit"), 3)

    def test_audio_callback_pushes_raw_bytes_and_energy(self) -> None:
        recorder = BaseEnergyAndAudioRecorder(
            RecorderAudioSource(),
            energy_threshold=300,
            dynamic_energy_threshold=False,
            phrase_time_limit=3,
            record_timeout=5,
        )
        captured_callback: dict = {}

        def fake_listen(_source, callback, phrase_time_limit=None):
            captured_callback["fn"] = callback
            return (MagicMock(), MagicMock(), MagicMock())

        recorder.recorder = MagicMock()
        recorder.recorder.listen_in_background = fake_listen

        audio_queue: Queue = Queue()
        energy_queue: Queue = Queue()
        recorder.recordIntoQueue(audio_queue, energy_queue)

        # Simulate a callback invocation with a fake AudioData-like object
        raw = b"\x10\x00" * 8
        fake_audio = MagicMock()
        fake_audio.get_raw_data.return_value = raw
        captured_callback["fn"](None, fake_audio)

        audio, recorded_at = audio_queue.get(timeout=1)
        self.assertEqual(audio, raw)
        self.assertIsNotNone(recorded_at)
        self.assertIsInstance(energy_queue.get(timeout=1), int)

    def test_device_error_flagged_when_listen_raises(self) -> None:
        recorder = BaseEnergyAndAudioRecorder(
            RecorderAudioSource(),
            energy_threshold=300,
            dynamic_energy_threshold=False,
            phrase_time_limit=3,
            record_timeout=5,
        )
        recorder.recorder = MagicMock()
        recorder.recorder.listen_in_background = MagicMock(side_effect=OSError("device gone"))

        with self.assertRaises(OSError):
            recorder.recordIntoQueue(Queue())
        self.assertTrue(recorder.device_error_event.is_set())


if __name__ == "__main__":
    unittest.main()
