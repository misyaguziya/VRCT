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

import threading
import unittest
from queue import Queue
from unittest.mock import patch, MagicMock

from speech_recognition import AudioSource

from models.transcription.transcription_recorder import (
    BaseEnergyAndAudioRecorder,
    _create_microphone,
    _LockedAudioSource,
    SelectedMicEnergyAndAudioRecorder,
    SelectedSpeakerEnergyAndAudioRecorder,
)
from device_manager import pyaudio_op_lock


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

        # _create_microphone は生の source を _LockedAudioSource でラップして
        # 返す (open/close を pyaudio_op_lock で直列化するため、詳細は
        # TestLockedAudioSource 参照)。中身の同一性で検証する。
        self.assertIs(source._source, default_source)
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

    def test_raises_timeout_error_instead_of_blocking_forever(self) -> None:
        """直前に force-stop した直後の同一デバイス再オープンで
        PyAudio.open() がハングすると (WASAPI 側の解放待ち)、
        _create_microphone はタイムアウトして OSError を投げる必要がある。
        mainloop のハンドラワーカーは少数しかなく、ここで無期限に
        ブロックするとアプリ全体が無応答になるため (実機で確認済み)。
        """
        never_returns = threading.Event()

        class HangingSource:
            def __enter__(self):
                never_returns.wait()  # 呼び出し元のタイムアウトより確実に長く待つ
                return self

            def __exit__(self, exc_type, exc_value, traceback) -> None:
                pass

        with patch(
            "models.transcription.transcription_recorder.Microphone",
            return_value=HangingSource(),
        ):
            with patch(
                "models.transcription.transcription_recorder._MIC_OPEN_TIMEOUT_SEC",
                0.05,
            ):
                with self.assertRaisesRegex(OSError, "Timed out"):
                    _create_microphone({}, device_index=10)

        never_returns.set()  # リークしたバックグラウンドスレッドを解放する


class TestLockedAudioSource(unittest.TestCase):
    """mic/speaker の listener スレッドが本番ストリームを open する瞬間
    (`with source as s:` = __enter__/__exit__) を pyaudio_op_lock で
    直列化できているかを検証する。この保護が無いと、mic と speaker の
    listener が起動タイミング次第で完全に無保護で並行 open し、WASAPI
    が壊れて access violation (プロセスクラッシュ) を起こすことを
    faulthandler の crash_trace.log で実際に確認済み (2026-08-19)。
    """

    def test_is_recognized_as_an_audio_source(self) -> None:
        # speech_recognition.listen_energy_and_audio_in_background は
        # `assert isinstance(source, AudioSource)` で弾くため、ラッパー
        # 自身が AudioSource のサブクラスである必要がある。
        wrapped = _LockedAudioSource(FakeAudioSource(opens=True))
        self.assertIsInstance(wrapped, AudioSource)

    def test_enter_exit_hold_pyaudio_op_lock(self) -> None:
        inner = FakeAudioSource(opens=True)
        lock_held_during_enter = []
        lock_held_during_exit = []

        original_enter = FakeAudioSource.__enter__
        original_exit = FakeAudioSource.__exit__

        def spying_enter(self):
            lock_held_during_enter.append(pyaudio_op_lock.locked())
            return original_enter(self)

        def spying_exit(self, exc_type, exc_value, traceback):
            lock_held_during_exit.append(pyaudio_op_lock.locked())
            return original_exit(self, exc_type, exc_value, traceback)

        with patch.object(FakeAudioSource, "__enter__", spying_enter):
            with patch.object(FakeAudioSource, "__exit__", spying_exit):
                wrapped = _LockedAudioSource(inner)
                with wrapped as s:
                    self.assertIs(s, inner)
                    # 読み取りループの間は解放されている (open/close の
                    # 瞬間だけを絞る設計であり、ずっと保持しない)。
                    self.assertFalse(pyaudio_op_lock.locked())

        self.assertEqual(lock_held_during_enter, [True])
        self.assertEqual(lock_held_during_exit, [True])
        self.assertFalse(pyaudio_op_lock.locked())

    def test_attribute_access_proxies_to_wrapped_source(self) -> None:
        inner = FakeAudioSource(opens=True)
        inner.SAMPLE_RATE = 48000
        wrapped = _LockedAudioSource(inner)

        self.assertEqual(wrapped.SAMPLE_RATE, 48000)
        with wrapped:
            self.assertIs(wrapped.stream, inner.stream)


class TestRecorderChunkSize(unittest.TestCase):
    """SelectedSpeakerEnergyAndAudioRecorder は以前
    `chunk_size=get_sample_size(paInt16)` (=2, 1サンプルのバイト数であって
    フレーム数ではない) を渡していた。Microphone のデフォルト chunk_size
    は 1024 フレームだが、これにより speaker 側だけ 1 回の read が 2
    フレームに縮小し、極端に細切れな audioop.rms() 計算になって音量
    メーターが激しくばらついていた (mic 側は chunk_size を渡していない
    ため影響を受けない、実機で確認済みの症状と一致)。
    Microphone に渡る chunk_size が意図せず小さくならないことを保証する。
    """

    def test_speaker_recorder_does_not_override_chunk_size(self) -> None:
        selected_source = FakeAudioSource(opens=True)
        selected_source.SAMPLE_RATE = 48000
        selected_source.SAMPLE_WIDTH = 2
        selected_source.channels = 2

        with patch(
            "models.transcription.transcription_recorder.Microphone"
        ) as mock_microphone:
            mock_microphone.return_value = selected_source
            SelectedSpeakerEnergyAndAudioRecorder(
                device={"index": 3, "defaultSampleRate": 48000, "maxInputChannels": 2},
                energy_threshold=300,
                dynamic_energy_threshold=False,
                phrase_time_limit=3,
            )

        _args, kwargs = mock_microphone.call_args
        self.assertNotIn("chunk_size", kwargs)

    def test_mic_and_speaker_recorders_use_the_same_chunk_size(self) -> None:
        """マイク側は元々 chunk_size を渡していない (=デフォルト 1024)。
        スピーカー側もそれに揃えるべきなので、Microphone に渡る kwargs の
        差分が chunk_size に関するものではないことを確認する。"""
        mic_source = FakeAudioSource(opens=True)
        mic_source.SAMPLE_RATE = 16000
        mic_source.SAMPLE_WIDTH = 2
        mic_source.channels = 1
        speaker_source = FakeAudioSource(opens=True)
        speaker_source.SAMPLE_RATE = 48000
        speaker_source.SAMPLE_WIDTH = 2
        speaker_source.channels = 2

        with patch(
            "models.transcription.transcription_recorder.Microphone"
        ) as mock_microphone:
            mock_microphone.side_effect = [mic_source, speaker_source]

            SelectedMicEnergyAndAudioRecorder(
                device={"index": 1, "defaultSampleRate": 16000},
                energy_threshold=300,
                dynamic_energy_threshold=False,
                phrase_time_limit=3,
            )
            SelectedSpeakerEnergyAndAudioRecorder(
                device={"index": 2, "defaultSampleRate": 48000, "maxInputChannels": 2},
                energy_threshold=300,
                dynamic_energy_threshold=False,
                phrase_time_limit=3,
            )

        mic_kwargs = mock_microphone.call_args_list[0].kwargs
        speaker_kwargs = mock_microphone.call_args_list[1].kwargs
        self.assertNotIn("chunk_size", mic_kwargs)
        self.assertNotIn("chunk_size", speaker_kwargs)


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

        # self.stop は生の stop をそのまま公開するのではなく、
        # Pa_StopStream で read() の詰まりを解いてから委譲するラッパ
        # (stopper) になる (無限 join のハング対策、詳細はテスト
        # test_stop_force_stops_stream_before_delegating 参照)。
        self.assertIsNot(recorder.stop, stop)
        self.assertIs(recorder.pause, pause)
        self.assertIs(recorder.resume, resume)
        recorder.recorder.listen_energy_and_audio_in_background.assert_called_once()
        _, kwargs = recorder.recorder.listen_energy_and_audio_in_background.call_args
        self.assertEqual(kwargs.get("phrase_time_limit"), 3)
        self.assertEqual(kwargs.get("record_timeout"), 5)
        self.assertIsNone(kwargs.get("callback_energy"))

        recorder.stop()
        stop.assert_called_once_with(wait_for_stop=True)

    def test_stop_force_stops_stream_before_delegating(self) -> None:
        """listener が stream.read() でブロックしていると、speech_recognition
        側の stop (listener_thread.join() にタイムアウト無し) が永久に
        返らない (WASAPI ループバック無音時などで実際に発生を確認済み、
        過去に 9665bb5a で修正されたが VAD 実装ごとの revert で失われて
        いた)。stop() は委譲前に Pa_StopStream で read() の詰まりを解く
        必要がある。"""
        recorder = BaseEnergyAndAudioRecorder(
            RecorderAudioSource(),
            energy_threshold=300,
            dynamic_energy_threshold=False,
            phrase_time_limit=3,
            record_timeout=5,
        )
        stop = MagicMock(name="stop")
        recorder.recorder = MagicMock()
        recorder.recorder.listen_energy_and_audio_in_background = MagicMock(
            return_value=(stop, MagicMock(), MagicMock())
        )
        recorder.recordIntoQueue(Queue())

        pyaudio_stream = MagicMock(name="pyaudio_stream")
        pyaudio_stream.is_stopped.return_value = False
        recorder.source.stream = MagicMock(pyaudio_stream=pyaudio_stream)

        recorder.stop(wait_for_stop=False)

        pyaudio_stream.stop_stream.assert_called_once()
        stop.assert_called_once_with(wait_for_stop=False)

    def test_stop_tolerates_missing_stream(self) -> None:
        """まだ source.stream が None (listener 起動直後など) でも
        stop() が例外を出さずに委譲まで進むこと。"""
        recorder = BaseEnergyAndAudioRecorder(
            RecorderAudioSource(),
            energy_threshold=300,
            dynamic_energy_threshold=False,
            phrase_time_limit=3,
            record_timeout=5,
        )
        stop = MagicMock(name="stop")
        recorder.recorder = MagicMock()
        recorder.recorder.listen_energy_and_audio_in_background = MagicMock(
            return_value=(stop, MagicMock(), MagicMock())
        )
        recorder.recordIntoQueue(Queue())
        recorder.source.stream = None

        recorder.stop()

        stop.assert_called_once_with(wait_for_stop=True)

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
