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
  `listen_in_background` に完全に委任する (energy_threshold, phrase_time_limit)。
  独自 VAD/ストリーミング分割は行わない (ADR-0004 参照)。
- PyAudio 操作は全て `pyaudio_op_lock` の下で行い、WASAPI ロック競合を防ぐ。
"""

import audioop
import threading
from typing import Any
from speech_recognition import Recognizer, Microphone
from pyaudiowpatch import get_sample_size, paInt16
from datetime import datetime
from utils import errorLogging
from device_manager import pyaudio_op_lock


def _validate_audio_source(source: Any) -> Any:
    # 呼び出し元 (_create_microphone) が既に pyaudio_op_lock を保持している
    # 前提の内部関数。ここではロックを取らない (再入不可の Lock で
    # 二重取得するとデッドロックするため)。
    source.__enter__()
    if source.stream is None:
        raise OSError("Audio device could not be opened")
    source.__exit__(None, None, None)
    return source


def _create_microphone(fallback_kwargs: dict[str, Any], **device_kwargs: Any) -> Any:
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
                raise OSError("Selected and default audio devices could not be opened") from fallback_error


class BaseEnergyAndAudioRecorder:
    """Records audio and/or a raw energy stream from a single physical device.

    Energy-only callers (the config-panel volume meter) and transcription
    callers (mic/speaker send/receive) both go through this same recorder
    so a given physical device is only ever opened once. Every PyAudio
    operation is serialized via `pyaudio_op_lock`.

    フレーズ境界・エネルギー閾値による発話検出は `speech_recognition` の
    `listen_in_background` に完全委任する (energy_threshold /
    dynamic_energy_threshold / phrase_time_limit)。独自 VAD は使わない。
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
        """listen_in_background で発話区間ごとに audio を audio_queue に、
        並行して energy_queue が指定されていれば RMS を積む。

        audio_queue には (raw_bytes, recorded_at) タプルを push する。
        フレーズの区切りは listen_in_background の phrase_time_limit と
        energy_threshold ベースの発話終端検出に委ねる。
        """

        def audio_callback(_, audio) -> None:
            try:
                raw = audio.get_raw_data()
                audio_queue.put((raw, datetime.now()))
                if energy_queue is not None:
                    energy_queue.put(audioop.rms(raw, self.SAMPLE_WIDTH))
            except Exception:
                # listener スレッドを絶対に殺さない (再入時に stream が
                # 停止するのを避けるため)
                errorLogging()

        try:
            self.stop, self.pause, self.resume = self.recorder.listen_in_background(
                self.source,
                audio_callback,
                phrase_time_limit=self.phrase_time_limit,
            )
        except Exception:
            self.device_error_event.set()
            errorLogging()
            raise


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
            device_index=int(device.get('index', -1)),
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
            device_index=int(device.get('index', -1)),
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
