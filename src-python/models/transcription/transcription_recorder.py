"""Recorders that wrap speech_recognition microphone interfaces.

These classes provide small adapters that push raw audio bytes into queues.
They intentionally keep a thin API so the rest of the system can mock them
in tests.

デバイスライフサイクル整理と VAD ストリーミング撤退 (ADR-0004) の結果、
現在の設計は以下の通り:

- `BaseEnergyAndAudioRecorder` が mic/speaker 共通の唯一の Recorder として、
  音声データ (audio_queue) とエネルギー (energy_queue) の両方を同時に扱う。
  同一物理デバイスに対する PyAudio Microphone インスタンスは常に 1 つ。
- 発話区間検出・フレーズ境界・pause/resume/stop は `speech_recognition` の
  `listen_energy_and_audio_in_background` に完全に委任する (energy_threshold,
  phrase_time_limit)。独自 VAD/ストリーミング分割は行わない (ADR-0004 参照)。
  `callback_energy` フックにより、フレーズ確定を待たず生チャンクごとに
  エナジー値を取得できる (音量メーターのリアルタイム更新用)。
- PyAudio 操作は全て `pyaudio_op_lock` の下で行い、WASAPI ロック競合を防ぐ。
"""

import threading
from typing import Any
from speech_recognition import AudioSource, Recognizer, Microphone
from pyaudiowpatch import get_sample_size, paInt16
from datetime import datetime
from utils import errorLogging, printLog
from device_manager import pyaudio_op_lock

# 直前に同じ物理デバイスを force-stop した直後は、WASAPI 側の解放が
# 完了しておらず Microphone.__enter__ 内の PyAudio.open() がブロックし
# たまま返らないことがある (open() 自体にタイムアウトが無い)。
# mainloop のハンドラワーカーは少数 (DEFAULT_WORKER_COUNT) しかなく、
# ここで無期限にブロックすると mic/speaker 以外の操作も含めてアプリ
# 全体が無応答になる。そのため open() は別スレッドで実行し、規定時間
# 内に完了しなければタイムアウトとして扱う。
_MIC_OPEN_TIMEOUT_SEC = 8.0


def _validate_audio_source(source: Any) -> Any:
    # 呼び出し元 (_create_microphone) が既に pyaudio_op_lock を保持している
    # 前提の内部関数。ここではロックを取らない (再入不可の Lock で
    # 二重取得するとデッドロックするため)。
    source.__enter__()
    if source.stream is None:
        raise OSError("Audio device could not be opened")
    source.__exit__(None, None, None)
    return source


class _LockedAudioSource(AudioSource):
    """speech_recognition の AudioSource をラップし、`__enter__`/`__exit__`
    (実際の PyAudio ストリーム open/close) だけを pyaudio_op_lock で
    直列化する。

    `_create_microphone` は疎通確認用の使い捨て open/close
    (`_validate_audio_source`) を pyaudio_op_lock 配下で行うが、実際に
    listen で使う本番ストリームは別物で、`recordIntoQueue` が呼ぶ
    `listen_energy_and_audio_in_background` 内の `with source as s:`
    (listener スレッド自身) や `adjustForNoise` の `with self.source:`
    が個別に open/close する。ここは pyaudio_op_lock の外側だったため、
    mic と speaker の listener スレッドが起動タイミング次第で完全に
    無保護で並行 open し、WASAPI が壊れて `PyAudio.__init__` 内で
    access violation を起こすことを faulthandler の crash_trace.log で
    実際に確認した (2026-08-19)。読み取りループ自体は絞らず、open/close
    の瞬間だけをロックすることで、性能への影響を open/close 頻度のみに
    抑える。
    """

    def __init__(self, source: Any) -> None:
        # AudioSource を継承するのは listen_energy_and_audio_in_background
        # の `assert isinstance(source, AudioSource)` を通すためだけ。
        # AudioSource.__init__ は "抽象クラスです" として
        # NotImplementedError を送出するガードなので、意図的に呼ばない。
        self._source = source

    def __enter__(self) -> Any:
        with pyaudio_op_lock:
            self._source.__enter__()
        return self._source

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> Any:
        with pyaudio_op_lock:
            return self._source.__exit__(exc_type, exc_value, traceback)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._source, name)


def _open_with_fallback(fallback_kwargs: dict[str, Any], **device_kwargs: Any) -> Any:
    # speech_recognition の Microphone.__init__ 自体が、コンストラクタ内で
    # 独自に PyAudio() を new し get_device_count()/get_device_info_by_index()
    # 等のデバイス列挙を行ってから terminate() する。この呼び出しが
    # pyaudio_op_lock の外側にあると、mic 側と speaker 側の Microphone(...)
    # コンストラクタが並行実行され、WASAPI 内部でデッドロックし得る
    # (実際に mic=CABLE Output, speaker=Steam Streaming Speakers を同時に
    # 有効化した際にハングを確認済み)。
    # そのため Microphone(...) の生成から _validate_audio_source による
    # open/close 疎通確認まで、一貫して同じ pyaudio_op_lock 区間で行う。
    with pyaudio_op_lock:
        try:
            return _validate_audio_source(Microphone(**device_kwargs))
        except Exception:
            try:
                return _validate_audio_source(Microphone(**fallback_kwargs))
            except Exception as fallback_error:
                raise OSError(
                    "Selected and default audio devices could not be opened"
                ) from fallback_error


def _create_microphone(fallback_kwargs: dict[str, Any], **device_kwargs: Any) -> Any:
    result: dict[str, Any] = {}
    done = threading.Event()

    def _run() -> None:
        try:
            result["source"] = _open_with_fallback(fallback_kwargs, **device_kwargs)
        except Exception as error:  # noqa: BLE001 - re-raised on the caller's thread below
            result["error"] = error
        finally:
            done.set()

    # daemon=True: タイムアウトした場合、このスレッドが実際に open() から
    # 返ってくる保証はない (PyAudio に安全な中断手段が無い)。join せず
    # 諦めて呼び出し元に制御を返す。稀にしか起きない想定なので、
    # 中断されなかったスレッドは daemon のままリークさせておく。
    threading.Thread(target=_run, daemon=True, name="mic-open").start()

    if not done.wait(timeout=_MIC_OPEN_TIMEOUT_SEC):
        printLog(
            f"Timed out after {_MIC_OPEN_TIMEOUT_SEC}s opening audio device "
            f"(device_kwargs={device_kwargs}); the previous stream on this "
            "device may still be releasing"
        )
        raise OSError("Timed out opening audio device")

    if "error" in result:
        raise result["error"]
    return _LockedAudioSource(result["source"])


class BaseEnergyAndAudioRecorder:
    """Records audio and/or a raw energy stream from a single physical device.

    Energy-only callers (the config-panel volume meter) and transcription
    callers (mic/speaker send/receive) both go through this same recorder
    so a given physical device is only ever opened once. Every PyAudio
    operation is serialized via `pyaudio_op_lock`.

    フレーズ境界・エネルギー閾値による発話検出は `speech_recognition` の
    `listen_energy_and_audio_in_background` に完全委任する (energy_threshold /
    dynamic_energy_threshold / phrase_time_limit)。独自 VAD は使わない。
    この API は `listen_in_background` と同じ発話区間検出ロジックを使うが、
    追加で `callback_energy` フックを持ち、フレーズ確定を待たず生チャンク
    読み取りのたびにエナジー値を通知できる (config パネルの音量メーターを
    リアルタイム更新するために必要)。
    """

    def __init__(
        self,
        source: Any,
        energy_threshold: int,
        dynamic_energy_threshold: bool,
        phrase_time_limit: int,
        record_timeout: int,
    ) -> None:
        self.recorder = Recognizer()
        self.recorder.energy_threshold = energy_threshold
        self.recorder.dynamic_energy_threshold = dynamic_energy_threshold
        self.phrase_time_limit = phrase_time_limit
        self.record_timeout = record_timeout
        self.stop = None
        self.pause = None
        self.resume = None

        if source is None:
            raise ValueError("audio source can't be None")

        self.source = source
        self.SAMPLE_RATE = source.SAMPLE_RATE
        self.SAMPLE_WIDTH = source.SAMPLE_WIDTH
        self.channels = getattr(source, "channels", 1)
        # Set when the background listener thread dies from an unexpected
        # stream error (e.g. the device was unplugged) rather than a normal
        # stop() call, so callers can surface a "device lost" notice instead
        # of silently going quiet.
        self.device_error_event = threading.Event()

    def adjustForNoise(self) -> None:
        with self.source:
            self.recorder.adjust_for_ambient_noise(self.source)

    def recordIntoQueue(self, audio_queue: Any, energy_queue: Any = None) -> None:
        """listen_energy_and_audio_in_background で発話区間ごとに audio を
        audio_queue に積む。energy_queue が指定されていれば、フレーズ確定を
        待たず生チャンク読み取りのたびに RMS を積む (callback_energy)。

        audio_queue には (raw_bytes, recorded_at) タプルを push する。
        フレーズの区切りは phrase_time_limit と energy_threshold ベースの
        発話終端検出に委ねる (listen_in_background と同じロジック)。
        """

        def audio_callback(_, audio) -> None:
            try:
                raw = audio.get_raw_data()
                audio_queue.put((raw, datetime.now()))
            except Exception:
                # listener スレッドを絶対に殺さない (再入時に stream が
                # 停止するのを避けるため)
                errorLogging()

        def energy_callback(energy) -> None:
            try:
                energy_queue.put(energy)
            except Exception:
                errorLogging()

        try:
            stop, pause, resume = self.recorder.listen_energy_and_audio_in_background(
                source=self.source,
                callback=audio_callback,
                phrase_time_limit=self.phrase_time_limit,
                callback_energy=energy_callback if energy_queue is not None else None,
                phrase_timeout=1,
                record_timeout=self.record_timeout,
            )
        except Exception:
            self.device_error_event.set()
            errorLogging()
            raise

        def stopper(wait_for_stop: bool = True) -> None:
            # speech_recognition 側の stopper は listener スレッドの
            # join() にタイムアウトを持たない。listener は
            # self.source.stream.read() でブロックしており、WASAPI
            # ループバックの無音時などデータが来なくなると read() は
            # 返らず、stop() が永久にブロックしてしまう
            # (過去に 9665bb5a で判明・修正され、ADR-0004 の保持リスト
            #  でも forward-port 対象とされていたが、VAD 実装ごと revert
            #  された際に一緒に失われていた)。
            # Pa_StopStream (pyaudio_stream.stop_stream) は稼働中の
            # ストリームを別スレッドから止める用途の API で、進行中の
            # read を強制的に返させる。Pa_CloseStream と異なり別スレッド
            # から呼んでもデッドロックしない。self.source.stream は
            # speech_recognition の MicrophoneStream ラッパで、実 PyAudio
            # stream は .pyaudio_stream 属性経由でアクセスする。
            try:
                with pyaudio_op_lock:
                    sr_stream = getattr(self.source, "stream", None)
                    pa_stream = (
                        getattr(sr_stream, "pyaudio_stream", None)
                        if sr_stream is not None
                        else None
                    )
                    if pa_stream is not None and not pa_stream.is_stopped():
                        pa_stream.stop_stream()
            except Exception:
                # 既に停止済み等、想定内の失敗もあり得るが原因調査のため記録する
                errorLogging()
            stop(wait_for_stop=wait_for_stop)

        self.stop = stopper
        self.pause = pause
        self.resume = resume


class SelectedMicEnergyAndAudioRecorder(BaseEnergyAndAudioRecorder):
    def __init__(
        self,
        device: dict,
        energy_threshold: int,
        dynamic_energy_threshold: bool,
        phrase_time_limit: int,
        record_timeout: int = 5,
    ) -> None:
        source = _create_microphone(
            {},
            device_index=int(device.get("index", -1)),
            sample_rate=int(device.get("defaultSampleRate", 16000)),
        )
        super().__init__(
            source=source,
            energy_threshold=energy_threshold,
            dynamic_energy_threshold=dynamic_energy_threshold,
            phrase_time_limit=phrase_time_limit,
            record_timeout=record_timeout,
        )


class SelectedSpeakerEnergyAndAudioRecorder(BaseEnergyAndAudioRecorder):
    def __init__(
        self,
        device: dict,
        energy_threshold: int,
        dynamic_energy_threshold: bool,
        phrase_time_limit: int,
        record_timeout: int = 5,
    ) -> None:
        source = _create_microphone(
            {"speaker": True},
            speaker=True,
            device_index=int(device.get("index", -1)),
            sample_rate=int(device.get("defaultSampleRate", 16000)),
            chunk_size=get_sample_size(paInt16),
            channels=int(device.get("maxInputChannels", 1)),
        )
        super().__init__(
            source=source,
            energy_threshold=energy_threshold,
            dynamic_energy_threshold=dynamic_energy_threshold,
            phrase_time_limit=phrase_time_limit,
            record_timeout=record_timeout,
        )
