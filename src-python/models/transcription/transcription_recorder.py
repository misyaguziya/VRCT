"""Recorders that wrap speech_recognition microphone interfaces.

These classes provide small adapters that push raw audio bytes into queues.
They intentionally keep a thin API so the rest of the system can mock them
in tests.
"""

import audioop
import threading
import time
from typing import Any, Optional
from speech_recognition import Recognizer, Microphone
from datetime import datetime
from .audio_pipeline import AudioQueueItem, Pcm16MonoNormalizer, StreamingVadSegmenter
from utils import errorLogging, printLog
from device_manager import pyaudio_op_lock

# self.source.stream.read() is a blocking PyAudio call with no built-in
# timeout. Some devices (notably virtual/loopback devices such as Virtual
# Desktop Audio) can stop producing data without raising an error, which
# would otherwise hang the listener thread forever. If no audio has been
# read for this many seconds, the watchdog signals a device error so the
# pipeline can surface it instead of silently going quiet.
_STREAM_STALL_TIMEOUT_SEC = 10.0


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
    """Records audio (optionally VAD-segmented) and/or a raw energy stream
    from a single physical device.

    Energy-only callers (the config-panel volume meter) and
    transcription callers (mic/speaker send/receive) both go through this
    same recorder/listener so a given physical device is only ever opened
    once, and every PyAudio operation is serialized via pyaudio_op_lock —
    there is no separate SpeechRecognition-builtin-thread code path left
    that could race against it.
    """

    def __init__(
        self,
        source: Any,
        energy_threshold: int,
        dynamic_energy_threshold: bool,
        phrase_time_limit: int,
        phrase_timeout: int,
        record_timeout: int,
        vad_filter: bool = False,
        vad_parameters: Optional[dict[str, Any]] = None,
        enable_stall_watchdog: bool = True,
    ) -> None:
        self.recorder = Recognizer()
        self.recorder.energy_threshold = energy_threshold
        self.recorder.dynamic_energy_threshold = dynamic_energy_threshold
        self.phrase_time_limit = phrase_time_limit
        self.phrase_timeout = phrase_timeout
        self.record_timeout = record_timeout
        self.stop = None
        # スピーカー(WASAPIループバック)は再生していない間、読み取りが
        # 単にブロックし続けるだけで「デバイス停滞」ではない。無音を
        # デバイスエラーとして誤通知しないよう、スピーカー側では
        # False を渡して watchdog を無効化する。
        self.enable_stall_watchdog = enable_stall_watchdog

        if source is None:
            raise ValueError("audio source can't be None")

        self.source = source
        self.SAMPLE_RATE = 16000
        self.SAMPLE_WIDTH = 2
        self.channels = 1
        # Set when the background listener thread dies from an unexpected
        # stream error (e.g. the device was unplugged) rather than a normal
        # stop() call, so callers can surface a "device lost" notice instead
        # of silently going quiet.
        self.device_error_event = threading.Event()
        self.normalizer = Pcm16MonoNormalizer(
            sample_rate=source.SAMPLE_RATE,
            sample_width=source.SAMPLE_WIDTH,
            channels=getattr(source, "channels", 1),
        )
        parameters = vad_parameters or {}
        self.vad_segmenter = StreamingVadSegmenter(
            positive_threshold=float(parameters.get("threshold", 0.25)),
            negative_threshold=float(parameters.get("neg_threshold") or 0.10),
            redemption_frames=max(1, round(int(parameters.get("min_silence_duration_ms", 768)) / 32)),
            min_speech_frames=max(1, round(int(parameters.get("min_speech_duration_ms", 64)) / 32)),
            pre_speech_pad_frames=max(0, round(int(parameters.get("speech_pad_ms", 160)) / 32)),
        ) if vad_filter else None

    def adjustForNoise(self) -> None:
        with self.source:
            self.recorder.adjust_for_ambient_noise(self.source)

    def recordIntoQueue(self, audio_queue: Any, energy_queue: Any = None) -> None:
        self.stop, self.pause, self.resume = self._recordIntoQueueInternal(audio_queue, energy_queue)

    def _recordIntoQueueInternal(self, audio_queue: Any, energy_queue: Any = None):
        """Single listener loop used for every combination of VAD on/off and
        energy queue present/absent.

        With VAD enabled, segments are pushed as AudioQueueItem (partial and
        final, matching the streaming pipeline). With VAD disabled, each
        normalized chunk is pushed as a plain (audio_bytes, recorded_at)
        tuple — the same shape the old SpeechRecognition-builtin path used —
        and phrase boundaries are left entirely to AudioTranscriber's
        phrase_timeout logic on the consuming side, so no consumer code
        needed to change.
        """
        running = threading.Event()
        running.set()
        paused = threading.Event()
        stopped = threading.Event()
        last_read_at = [time.monotonic()]
        partial_interval_ms = max(250.0, float(self.phrase_time_limit or 1) * 1000)

        def emit_segment(segment, recorded_at: datetime) -> None:
            audio_queue.put(AudioQueueItem(
                audio=segment.audio,
                recorded_at=recorded_at,
                is_final=segment.is_final,
                segment_id=segment.segment_id,
                speech_ended_at=recorded_at if segment.is_final else None,
            ))

        def watchForStall() -> None:
            # stream.read() は timeout を持たないため、仮想/ループバックデバイス等で
            # データが来なくなると listener スレッドが read で永久ブロックする。
            # ここで stream.close() を別スレッドから叩くと、PyAudio/PortAudio (特に
            # Windows WASAPI) は read/close の同時実行が保証されておらず、
            # PortAudio 内部ロックでプロセス全体がデッドロックする。
            # そのため close は叩かず、device_error_event を立ててパイプライン側に
            # 「デバイスエラー」として通知するに留める。listener 自体は
            # 停止不能のままリークするが、UIには通常のデバイスエラーとして届き、
            # 停滞スピナー等は device_error_event 経路で解除される。
            while not stopped.wait(timeout=1.0):
                if time.monotonic() - last_read_at[0] > _STREAM_STALL_TIMEOUT_SEC:
                    printLog(
                        "Audio stream stalled (no data for "
                        f"{_STREAM_STALL_TIMEOUT_SEC}s); signaling device error"
                    )
                    self.device_error_event.set()
                    running.clear()
                    break

        def threadedListen() -> None:
            last_partial_duration_ms = 0.0
            was_paused = False
            # `with self.source:` を分解し、open/close 時のみ共有ロックを
            # 保持する。read ループ中は解放して device_manager 側の列挙が
            # 進行できるようにする。
            source_entered = False
            try:
                with pyaudio_op_lock:
                    self.source.__enter__()
                    source_entered = True
                while running.is_set():
                    raw_audio = self.source.stream.read(self.source.CHUNK)
                    last_read_at[0] = time.monotonic()
                    if paused.is_set():
                        if not was_paused and self.vad_segmenter is not None:
                            recorded_at = datetime.now()
                            segment = self.vad_segmenter.flush()
                            if segment is not None:
                                emit_segment(segment, recorded_at)
                            self.normalizer.reset()
                            last_partial_duration_ms = 0.0
                        was_paused = True
                        continue
                    was_paused = False

                    normalized_audio = self.normalizer.process(raw_audio)
                    if not normalized_audio:
                        continue
                    if energy_queue is not None:
                        energy_queue.put(audioop.rms(normalized_audio, 2))

                    recorded_at = datetime.now()
                    if self.vad_segmenter is not None:
                        for segment in self.vad_segmenter.process(normalized_audio):
                            emit_segment(segment, recorded_at)
                            last_partial_duration_ms = 0.0

                        partial = self.vad_segmenter.snapshot()
                        if partial is not None and partial.duration_ms >= last_partial_duration_ms + partial_interval_ms:
                            emit_segment(partial, recorded_at)
                            last_partial_duration_ms = partial.duration_ms
                    else:
                        # VAD 無効時は生チャンクをそのままキューに積む。
                        # フレーズの区切りは AudioTranscriber 側の
                        # phrase_timeout ロジックに委ねる。
                        audio_queue.put((normalized_audio, recorded_at))
            except EOFError:
                pass
            except Exception:
                self.device_error_event.set()
                errorLogging()
            finally:
                if source_entered:
                    try:
                        with pyaudio_op_lock:
                            self.source.__exit__(None, None, None)
                    except Exception:
                        errorLogging()
                if self.vad_segmenter is not None:
                    recorded_at = datetime.now()
                    segment = self.vad_segmenter.flush()
                    if segment is not None:
                        emit_segment(segment, recorded_at)
                self.normalizer.reset()
                paused.clear()
                running.clear()
                stopped.set()

        listener_thread = threading.Thread(target=threadedListen, daemon=True)
        listener_thread.start()
        watchdog_thread: Optional[threading.Thread] = None
        if self.enable_stall_watchdog:
            watchdog_thread = threading.Thread(target=watchForStall, daemon=True)
            watchdog_thread.start()

        def stopper(wait_for_stop: bool = True) -> None:
            running.clear()
            stopped.set()
            # listener が stream.read() でブロックしているとフラグを見に
            # 戻れず、join のタイムアウトまで最大数秒待たされる
            # (特に WASAPI ループバックの無音時)。
            # Pa_CloseStream は別スレッドから叩くとデッドロックするが、
            # Pa_StopStream (pyaudio_stream.stop_stream) は稼働中のストリームを
            # 別スレッドから止める用途の API で、進行中の read を返させる。
            # self.source.stream は speech_recognition の MicrophoneStream ラッパで、
            # 実 PyAudio stream は .pyaudio_stream 属性経由でアクセスする。
            try:
                with pyaudio_op_lock:
                    sr_stream = getattr(self.source, "stream", None)
                    pa_stream = getattr(sr_stream, "pyaudio_stream", None) if sr_stream is not None else None
                    if pa_stream is not None and not pa_stream.is_stopped():
                        pa_stream.stop_stream()
            except Exception:
                # 既に停止済み等、想定内の失敗もあり得るが原因調査のため記録する
                errorLogging()
            if wait_for_stop:
                listener_thread.join(timeout=5.0)
                if watchdog_thread is not None:
                    watchdog_thread.join(timeout=2.0)

        def pauser() -> None:
            paused.set()

        def resumer() -> None:
            paused.clear()

        return stopper, pauser, resumer


class SelectedMicEnergyAndAudioRecorder(BaseEnergyAndAudioRecorder):
    def __init__(
        self,
        device: dict,
        energy_threshold: int,
        dynamic_energy_threshold: bool,
        phrase_time_limit: int,
        phrase_timeout: int = 1,
        record_timeout: int = 5,
        vad_filter: bool = False,
        vad_parameters: Optional[dict[str, Any]] = None,
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
            phrase_timeout=phrase_timeout,
            record_timeout=record_timeout,
            vad_filter=vad_filter,
            vad_parameters=vad_parameters,
        )
        # self.adjustForNoise()


class SelectedSpeakerEnergyAndAudioRecorder(BaseEnergyAndAudioRecorder):
    def __init__(
        self,
        device: dict,
        energy_threshold: int,
        dynamic_energy_threshold: bool,
        phrase_time_limit: int,
        phrase_timeout: int = 1,
        record_timeout: int = 5,
        vad_filter: bool = False,
        vad_parameters: Optional[dict[str, Any]] = None,
    ) -> None:

        source = _create_microphone(
            {"speaker": True},
            speaker=True,
            device_index=int(device.get('index', -1)),
            sample_rate=int(device.get("defaultSampleRate", 16000)),
            chunk_size=1024,
            channels=int(device.get("maxInputChannels", 1)),
        )
        super().__init__(
            source=source,
            energy_threshold=energy_threshold,
            dynamic_energy_threshold=dynamic_energy_threshold,
            phrase_time_limit=phrase_time_limit,
            phrase_timeout=phrase_timeout,
            record_timeout=record_timeout,
            vad_filter=vad_filter,
            vad_parameters=vad_parameters,
            # WASAPI ループバックは再生がなければ何時間でも無音でブロックする。
            # これは正常な状態なので stall watchdog で「デバイスエラー」として
            # 上げないこと (誤って "No speaker device detected" が出る)。
            enable_stall_watchdog=False,
        )
        # self.adjustForNoise()
