"""Tests for transcription_recorder.

`BaseEnergyAndAudioRecorder` は speech_recognition.Recognizer を用いた
`listen_energy_and_audio_in_background` に発話区間検出とフレーズ境界を委ねる
(ADR-0004)。このため統合的な入力→キュー投入までの検証は
listen_energy_and_audio_in_background 側のロジックに寄りかかるが、ここでは
以下のみを直接テストする:

- `_create_microphone` の fallback 動作
- 公開 API (`recordIntoQueue`) が listen_energy_and_audio_in_background 側の
  stop/pause/resume を正しく self.stop/self.pause/self.resume に受け取ること
- audio callback が audio_queue に生データを積むこと
- callback_energy が energy_queue にエナジー値を積むこと (フレーズ確定を
  待たずリアルタイムに呼ばれる想定)
"""

import unittest
from queue import Queue
from unittest.mock import patch, MagicMock

from models.transcription.transcription_recorder import (
    BaseEnergyAndAudioRecorder,
    _create_microphone,
)


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

    def test_recordIntoQueue_wires_listen_energy_and_audio_in_background_control_handles(
        self,
    ) -> None:
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
        recorder.recorder.listen_energy_and_audio_in_background = MagicMock(
            return_value=(stop, pause, resume)
        )

        recorder.recordIntoQueue(Queue())

        self.assertIs(recorder.stop, stop)
        self.assertIs(recorder.pause, pause)
        self.assertIs(recorder.resume, resume)
        recorder.recorder.listen_energy_and_audio_in_background.assert_called_once()
        _, kwargs = recorder.recorder.listen_energy_and_audio_in_background.call_args
        self.assertEqual(kwargs.get("phrase_time_limit"), 3)
        self.assertEqual(kwargs.get("record_timeout"), 5)
        self.assertIsNone(kwargs.get("callback_energy"))

    def test_audio_callback_pushes_raw_bytes(self) -> None:
        recorder = BaseEnergyAndAudioRecorder(
            RecorderAudioSource(),
            energy_threshold=300,
            dynamic_energy_threshold=False,
            phrase_time_limit=3,
            record_timeout=5,
        )
        captured: dict = {}

        def fake_listen(
            source,
            callback,
            phrase_time_limit=None,
            callback_energy=None,
            phrase_timeout=1,
            record_timeout=5,
        ):
            captured["audio_callback"] = callback
            captured["energy_callback"] = callback_energy
            return (MagicMock(), MagicMock(), MagicMock())

        recorder.recorder = MagicMock()
        recorder.recorder.listen_energy_and_audio_in_background = fake_listen

        audio_queue: Queue = Queue()
        recorder.recordIntoQueue(audio_queue)

        # Simulate a callback invocation with a fake AudioData-like object
        raw = b"\x10\x00" * 8
        fake_audio = MagicMock()
        fake_audio.get_raw_data.return_value = raw
        captured["audio_callback"](None, fake_audio)

        audio, recorded_at = audio_queue.get(timeout=1)
        self.assertEqual(audio, raw)
        self.assertIsNotNone(recorded_at)
        # energy_queue が指定されていない場合、callback_energy は渡されない
        self.assertIsNone(captured["energy_callback"])

    def test_energy_callback_pushes_energy_without_waiting_for_phrase(self) -> None:
        """callback_energy はフレーズ確定を待たず、生チャンクの読み取りの
        たびに呼ばれる想定 (config パネルの音量メーターのリアルタイム更新に
        必要)。ここでは recordIntoQueue が callback_energy を正しく energy_queue
        に接続することだけを検証する。"""
        recorder = BaseEnergyAndAudioRecorder(
            RecorderAudioSource(),
            energy_threshold=300,
            dynamic_energy_threshold=False,
            phrase_time_limit=3,
            record_timeout=5,
        )
        captured: dict = {}

        def fake_listen(
            source,
            callback,
            phrase_time_limit=None,
            callback_energy=None,
            phrase_timeout=1,
            record_timeout=5,
        ):
            captured["energy_callback"] = callback_energy
            return (MagicMock(), MagicMock(), MagicMock())

        recorder.recorder = MagicMock()
        recorder.recorder.listen_energy_and_audio_in_background = fake_listen

        energy_queue: Queue = Queue()
        recorder.recordIntoQueue(Queue(), energy_queue)

        # フレーズが確定していない (audio_callback は一度も呼ばれていない)
        # 状態でも energy_callback 単体でエナジー値を積めること
        captured["energy_callback"](123)
        captured["energy_callback"](456)

        self.assertEqual(energy_queue.get(timeout=1), 123)
        self.assertEqual(energy_queue.get(timeout=1), 456)

    def test_device_error_flagged_when_listen_raises(self) -> None:
        recorder = BaseEnergyAndAudioRecorder(
            RecorderAudioSource(),
            energy_threshold=300,
            dynamic_energy_threshold=False,
            phrase_time_limit=3,
            record_timeout=5,
        )
        recorder.recorder = MagicMock()
        recorder.recorder.listen_energy_and_audio_in_background = MagicMock(
            side_effect=OSError("device gone")
        )

        with self.assertRaises(OSError):
            recorder.recordIntoQueue(Queue())
        self.assertTrue(recorder.device_error_event.is_set())


if __name__ == "__main__":
    unittest.main()
