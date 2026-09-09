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
    BaseVadAndAudioRecorder,
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

    def test_record_timeout_zero_is_treated_as_unlimited(self) -> None:
        # issue #113: record_timeout=0 を渡すと custom_speech_recognition の
        # 録音ループ冒頭ガードで即 WaitTimeoutError になり音声が一切拾えない。
        # 非正値は inf に正規化して「無制限録音」として扱う。
        recorder = BaseEnergyAndAudioRecorder(
            RecorderAudioSource(),
            energy_threshold=300,
            dynamic_energy_threshold=False,
            phrase_time_limit=3,
            record_timeout=0,
        )
        self.assertEqual(recorder.record_timeout, float("inf"))

        stop = MagicMock(name="stop")
        recorder.recorder = MagicMock()
        recorder.recorder.listen_energy_and_audio_in_background = MagicMock(
            return_value=(stop, MagicMock(), MagicMock())
        )
        recorder.recordIntoQueue(Queue())
        _, kwargs = recorder.recorder.listen_energy_and_audio_in_background.call_args
        self.assertEqual(kwargs.get("record_timeout"), float("inf"))

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

    def test_audio_callback_drops_oldest_chunk_when_queue_is_full(self) -> None:
        """文字起こしが実時間に追いつけず audio_queue (有界) が満杯に
        なった場合、put でブロックすると listener スレッド (このcallback
        自体) が止まり録音が滞ってしまう。ブロックせず最も古いチャンクを
        1つ捨てて最新を積むこと (フェーズ3項目20)。"""
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
            return (MagicMock(), MagicMock(), MagicMock())

        recorder.recorder = MagicMock()
        recorder.recorder.listen_energy_and_audio_in_background = fake_listen

        audio_queue: Queue = Queue(maxsize=2)
        recorder.recordIntoQueue(audio_queue)

        def make_audio(raw: bytes):
            fake_audio = MagicMock()
            fake_audio.get_raw_data.return_value = raw
            return fake_audio

        callback = captured["audio_callback"]
        callback(None, make_audio(b"\x01"))
        callback(None, make_audio(b"\x02"))
        self.assertEqual(audio_queue.qsize(), 2)

        # キューは満杯。ブロックせず古い方 (\x01) を捨てて \x03 を積むはず。
        callback(None, make_audio(b"\x03"))

        self.assertEqual(audio_queue.qsize(), 2)
        remaining = [audio_queue.get_nowait()[0] for _ in range(2)]
        self.assertEqual(remaining, [b"\x02", b"\x03"])

    def test_audio_callback_logs_when_it_drops_a_chunk(self) -> None:
        """キューが満杯でチャンクを捨てる際は、無音のままにせず
        printLog に残すこと (レビュー指摘: 以前は完全にサイレントだった)。"""
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
            return (MagicMock(), MagicMock(), MagicMock())

        recorder.recorder = MagicMock()
        recorder.recorder.listen_energy_and_audio_in_background = fake_listen

        audio_queue: Queue = Queue(maxsize=1)
        recorder.recordIntoQueue(audio_queue)

        def make_audio(raw: bytes):
            fake_audio = MagicMock()
            fake_audio.get_raw_data.return_value = raw
            return fake_audio

        callback = captured["audio_callback"]
        with patch("models.transcription.transcription_recorder.printLog") as mock_print_log:
            callback(None, make_audio(b"\x01"))
            mock_print_log.assert_not_called()
            callback(None, make_audio(b"\x02"))  # ここで満杯になり \x01 を捨てる
            mock_print_log.assert_called_once()

    def test_energy_callback_drops_oldest_when_queue_is_full(self) -> None:
        """energy_queue はメーター表示用で直近の値のみ意味を持つため、
        満杯なら古い値を捨てて最新に置き換わること (レビュー指摘)。"""
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

        energy_queue: Queue = Queue(maxsize=1)
        recorder.recordIntoQueue(Queue(), energy_queue)

        captured["energy_callback"](111)
        captured["energy_callback"](222)  # 満杯 -> 111 を捨てて 222 に置き換わるはず

        self.assertEqual(energy_queue.qsize(), 1)
        self.assertEqual(energy_queue.get_nowait(), 222)

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


class TestVadRecorderPipeline(unittest.TestCase):
    """BaseVadAndAudioRecorder は BaseEnergyAndAudioRecorder と同じ
    open/close・停止/一時停止の仕組み (_create_microphone,
    _wrapStopperWithBlockingReadUnblock) を共有し、フレーズ区切りの
    判定方法だけが異なる (VadRecognizerAdapter 経由の VAD)。
    """

    def test_exposes_the_queued_audio_format_not_the_native_device_format(self) -> None:
        """AudioTranscriber は self.SAMPLE_RATE/SAMPLE_WIDTH/channels を、
        audio_queue に積まれる生バイト列の実際の形式としてそのまま
        AudioData の再構成に使う (processMicData/processSpeakerData)。
        VAD 経由の音声は vad_adapter が正規化した 16kHz/16bit/mono に
        なるため、ここはネイティブなデバイスのフォーマット
        (RecorderAudioSource の 48kHz/2ch) ではなく、常に 16kHz/16bit/mono
        を公開しなければならない。実機で「エネルギーは取れるのに認識だけ
        できない」(サンプルレート不一致で音声が歪む) 形で確認された不具合
        の回帰テスト。
        """
        recorder = BaseVadAndAudioRecorder(RecorderAudioSource(), record_timeout=5)

        self.assertEqual(recorder.SAMPLE_RATE, 16000)
        self.assertEqual(recorder.SAMPLE_WIDTH, 2)
        self.assertEqual(recorder.channels, 1)
        self.assertEqual(recorder.vad_adapter.sample_rate, 16000)
        self.assertEqual(recorder.vad_adapter.sample_width, 2)
        # VadRecognizerAdapter 自体はネイティブフォーマット (48kHz/2ch) で
        # 初期化されていること (リサンプリング元の情報として必要)。
        self.assertEqual(recorder.vad_adapter._normalizer.sample_rate, 48000)
        self.assertEqual(recorder.vad_adapter._normalizer.channels, 2)

    def test_max_speech_frames_is_a_fixed_puripuly_referenced_value_not_record_timeout(
        self,
    ) -> None:
        """max_speech_frames を record_timeout に連動させていた時期があったが、
        実機検証で「無音を挟まない継続発話が record_timeout 秒ごとに
        強制打ち切りされ、単独送信された断片がエンジン側の信頼度フィルタで
        丸ごと棄却される」regressionが判明した (2026-09-06)。
        reason=="max_duration" の断片は AudioTranscriber 側で単独送信せず
        蓄積するようになったため、この値は record_timeout の大小と無関係な
        固定の安全弁 (PuriPuly-heart の PEER_MAX_SEGMENT_MS=7秒 を参考値と
        して採用) に戻したことを確認する。"""
        recorder_short = BaseVadAndAudioRecorder(RecorderAudioSource(), record_timeout=3)
        recorder_long = BaseVadAndAudioRecorder(RecorderAudioSource(), record_timeout=30)

        # 7秒 / 32ms(1フレーム) ≒ 219 フレーム。record_timeout の値に
        # 関わらず同じ (連動していない) こと。
        self.assertEqual(
            recorder_short.vad_adapter.segmenter.max_speech_frames,
            recorder_long.vad_adapter.segmenter.max_speech_frames,
        )
        self.assertAlmostEqual(recorder_short.vad_adapter.segmenter.max_speech_frames, 219, delta=2)

    def test_wires_diagnostic_logging_with_a_kind_specific_label(self) -> None:
        """体感の遅さ (モデル初回ロード・hangover 待ち等) を実機ログから
        切り分けられるよう、speech_start/speech_end が process.log に
        記録されるようになっていること。mic/speaker を区別できるラベルも
        併せて確認する。"""
        mic_recorder = BaseVadAndAudioRecorder(RecorderAudioSource(), record_timeout=5, label="mic")
        speaker_recorder = BaseVadAndAudioRecorder(RecorderAudioSource(), record_timeout=5, label="speaker")

        mic_segmenter = mic_recorder.vad_adapter.segmenter
        speaker_segmenter = speaker_recorder.vad_adapter.segmenter

        self.assertIsNotNone(mic_segmenter.diagnostic_callback)
        self.assertEqual(mic_segmenter.diagnostic_label, "mic")
        self.assertIsNotNone(speaker_segmenter.diagnostic_callback)
        self.assertEqual(speaker_segmenter.diagnostic_label, "speaker")

    def test_recordIntoQueue_wires_listen_with_segmenter_in_background_control_handles(
        self,
    ) -> None:
        recorder = BaseVadAndAudioRecorder(RecorderAudioSource(), record_timeout=5)
        stop = MagicMock(name="stop")
        pause = MagicMock(name="pause")
        resume = MagicMock(name="resume")
        recorder.recorder = MagicMock()
        recorder.recorder.listen_with_segmenter_in_background = MagicMock(
            return_value=(stop, pause, resume)
        )

        recorder.recordIntoQueue(Queue())

        # BaseEnergyAndAudioRecorder と同じく、self.stop は生の stop では
        # なく Pa_StopStream 経由のラッパになる。
        self.assertIsNot(recorder.stop, stop)
        self.assertIs(recorder.pause, pause)
        self.assertIs(recorder.resume, resume)
        recorder.recorder.listen_with_segmenter_in_background.assert_called_once()
        _, kwargs = recorder.recorder.listen_with_segmenter_in_background.call_args
        self.assertIs(kwargs.get("segmenter"), recorder.vad_adapter)
        self.assertEqual(kwargs.get("record_timeout"), 5)
        self.assertIsNone(kwargs.get("callback_energy"))

        recorder.stop()
        stop.assert_called_once_with(wait_for_stop=True)

    def test_stop_force_stops_stream_before_delegating(self) -> None:
        """BaseEnergyAndAudioRecorder と同じブロッキング read 対策
        (_wrapStopperWithBlockingReadUnblock) が VAD 側でも効いていること。"""
        recorder = BaseVadAndAudioRecorder(RecorderAudioSource(), record_timeout=5)
        stop = MagicMock(name="stop")
        recorder.recorder = MagicMock()
        recorder.recorder.listen_with_segmenter_in_background = MagicMock(
            return_value=(stop, MagicMock(), MagicMock())
        )
        recorder.recordIntoQueue(Queue())

        pyaudio_stream = MagicMock(name="pyaudio_stream")
        pyaudio_stream.is_stopped.return_value = False
        recorder.source.stream = MagicMock(pyaudio_stream=pyaudio_stream)

        recorder.stop(wait_for_stop=False)

        pyaudio_stream.stop_stream.assert_called_once()
        stop.assert_called_once_with(wait_for_stop=False)

    def test_audio_callback_pushes_raw_bytes_and_segment_reason(self) -> None:
        """VAD 経由のキューアイテムはエネルギー閾値方式と異なり
        (raw_bytes, recorded_at, reason) の3要素タプル。reason は
        AudioData.segment_reason (custom_speech_recognition フォークが
        segmenter の SpeechSegment.reason を伝播したもの) からそのまま
        引き継がれる (AudioTranscriber が max_duration/自然な区切りを
        区別するために必要、2026-09-06)。"""
        recorder = BaseVadAndAudioRecorder(RecorderAudioSource(), record_timeout=5)
        captured: dict = {}

        def fake_listen(source, callback, segmenter, callback_energy=None, record_timeout=5):
            captured["audio_callback"] = callback
            captured["energy_callback"] = callback_energy
            return (MagicMock(), MagicMock(), MagicMock())

        recorder.recorder = MagicMock()
        recorder.recorder.listen_with_segmenter_in_background = fake_listen

        audio_queue: Queue = Queue()
        recorder.recordIntoQueue(audio_queue)

        raw = b"\x10\x00" * 8
        fake_audio = MagicMock()
        fake_audio.get_raw_data.return_value = raw
        fake_audio.segment_reason = "max_duration"
        captured["audio_callback"](None, fake_audio)

        audio, recorded_at, reason = audio_queue.get(timeout=1)
        self.assertEqual(audio, raw)
        self.assertIsNotNone(recorded_at)
        self.assertEqual(reason, "max_duration")
        self.assertIsNone(captured["energy_callback"])

    def test_audio_callback_defaults_reason_to_none_when_segment_reason_is_absent(self) -> None:
        """segment_reason 属性が無い AudioData (フォーク未更新など) でも
        壊れず None になること。"""
        recorder = BaseVadAndAudioRecorder(RecorderAudioSource(), record_timeout=5)
        captured: dict = {}

        def fake_listen(source, callback, segmenter, callback_energy=None, record_timeout=5):
            captured["audio_callback"] = callback
            return (MagicMock(), MagicMock(), MagicMock())

        recorder.recorder = MagicMock()
        recorder.recorder.listen_with_segmenter_in_background = fake_listen

        audio_queue: Queue = Queue()
        recorder.recordIntoQueue(audio_queue)

        fake_audio = MagicMock(spec=["get_raw_data"])
        fake_audio.get_raw_data.return_value = b"\x01\x00"
        captured["audio_callback"](None, fake_audio)

        _audio, _recorded_at, reason = audio_queue.get(timeout=1)
        self.assertIsNone(reason)

    def test_audio_callback_drops_oldest_chunk_when_queue_is_full(self) -> None:
        """BaseEnergyAndAudioRecorder と同じ有界化 (フェーズ3項目20)。
        VAD 経由でも文字起こしが実時間に追いつけない状況は起こり得るため、
        ブロックせず最も古いチャンクを1つ捨てて追いつく。"""
        recorder = BaseVadAndAudioRecorder(RecorderAudioSource(), record_timeout=5)
        captured: dict = {}

        def fake_listen(source, callback, segmenter, callback_energy=None, record_timeout=5):
            captured["audio_callback"] = callback
            return (MagicMock(), MagicMock(), MagicMock())

        recorder.recorder = MagicMock()
        recorder.recorder.listen_with_segmenter_in_background = fake_listen

        audio_queue: Queue = Queue(maxsize=2)
        recorder.recordIntoQueue(audio_queue)

        def make_audio(raw: bytes):
            fake_audio = MagicMock()
            fake_audio.get_raw_data.return_value = raw
            fake_audio.segment_reason = None
            return fake_audio

        callback = captured["audio_callback"]
        callback(None, make_audio(b"\x01"))
        callback(None, make_audio(b"\x02"))
        self.assertEqual(audio_queue.qsize(), 2)

        callback(None, make_audio(b"\x03"))

        self.assertEqual(audio_queue.qsize(), 2)
        remaining = [audio_queue.get_nowait()[0] for _ in range(2)]
        self.assertEqual(remaining, [b"\x02", b"\x03"])

    def test_device_error_flagged_when_listen_raises(self) -> None:
        recorder = BaseVadAndAudioRecorder(RecorderAudioSource(), record_timeout=5)
        recorder.recorder = MagicMock()
        recorder.recorder.listen_with_segmenter_in_background = MagicMock(
            side_effect=OSError("device gone")
        )

        with self.assertRaises(OSError):
            recorder.recordIntoQueue(Queue())
        self.assertTrue(recorder.device_error_event.is_set())


if __name__ == "__main__":
    unittest.main()
