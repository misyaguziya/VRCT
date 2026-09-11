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
from typing import Any, Callable, Optional
from speech_recognition import AudioSource, Recognizer, Microphone
from datetime import datetime
from errors import AudioPipelineFailure, ERROR_METADATA, ErrorCode
from utils import errorLogging, printLog, putDroppingOldestOnFull
from device_manager import pyaudio_op_lock
from models.transcription.audio_vad import FRAME_DURATION_MS, VadRecognizerAdapter, VadSegmenter

# 直前に同じ物理デバイスを force-stop した直後は、WASAPI 側の解放が
# 完了しておらず Microphone.__enter__ 内の PyAudio.open() がブロックし
# たまま返らないことがある (open() 自体にタイムアウトが無い)。
# mainloop のハンドラワーカーは少数 (DEFAULT_WORKER_COUNT) しかなく、
# ここで無期限にブロックすると mic/speaker 以外の操作も含めてアプリ
# 全体が無応答になる。そのため open() は別スレッドで実行し、規定時間
# 内に完了しなければタイムアウトとして扱う。
_MIC_OPEN_TIMEOUT_SEC = 8.0


class _ReadErrorReportingStream:
    """MicrophoneStream の read 例外を Recorder へ返す薄いプロキシ。"""

    def __init__(self, stream: Any, handler: Callable[[Exception], None]) -> None:
        self._stream = stream
        self._handler = handler

    def read(self, *args: Any, **kwargs: Any) -> Any:
        try:
            return self._stream.read(*args, **kwargs)
        except Exception as error:  # noqa: BLE001 - report and preserve original behavior
            self._handler(error)
            raise

    def __getattr__(self, name: str) -> Any:
        return getattr(self._stream, name)


class _ErrorReportingSegmenter:
    """VAD adapter の process/flush 例外を Recorder へ返すプロキシ。"""

    def __init__(self, segmenter: Any, handler: Callable[[Exception], None]) -> None:
        self._segmenter = segmenter
        self._handler = handler

    def process(self, pcm_bytes: bytes) -> Any:
        try:
            return self._segmenter.process(pcm_bytes)
        except Exception as error:  # noqa: BLE001 - report and preserve original behavior
            self._handler(error)
            raise

    def flush(self) -> Any:
        try:
            return self._segmenter.flush()
        except Exception as error:  # noqa: BLE001 - report and preserve original behavior
            self._handler(error)
            raise

    def __getattr__(self, name: str) -> Any:
        return getattr(self._segmenter, name)


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
        self._read_error_handler: Optional[Callable[[Exception], None]] = None

    def set_read_error_handler(self, handler: Callable[[Exception], None]) -> None:
        self._read_error_handler = handler

    def __enter__(self) -> Any:
        with pyaudio_op_lock:
            self._source.__enter__()
            stream = getattr(self._source, "stream", None)
            if (
                stream is not None
                and self._read_error_handler is not None
                and not isinstance(stream, _ReadErrorReportingStream)
            ):
                self._source.stream = _ReadErrorReportingStream(stream, self._read_error_handler)
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
    cancelled = threading.Event()
    state_lock = threading.Lock()

    def _close_late_source(source: Any) -> None:
        """Timeout後に open が完了した source を回収する。"""
        try:
            with pyaudio_op_lock:
                stream = getattr(source, "stream", None)
                if stream is not None:
                    source.__exit__(None, None, None)
                else:
                    audio = getattr(source, "audio", None)
                    if audio is not None:
                        audio.terminate()
        except Exception:
            errorLogging()

    def _run() -> None:
        try:
            source = _open_with_fallback(fallback_kwargs, **device_kwargs)
            with state_lock:
                if cancelled.is_set():
                    late_source = source
                else:
                    result["source"] = source
                    late_source = None
            if late_source is not None:
                _close_late_source(late_source)
        except Exception as error:  # noqa: BLE001 - re-raised on the caller's thread below
            with state_lock:
                if not cancelled.is_set():
                    result["error"] = error
        finally:
            done.set()

    # daemon=True: PyAudio.open() 自体を安全に中断できない場合でも、
    # 呼び出し元はタイムアウトで復帰できるようにする。遅れて open が完了
    # した source は _run() 側で cancelled を確認して回収する。
    threading.Thread(target=_run, daemon=True, name="mic-open").start()

    if not done.wait(timeout=_MIC_OPEN_TIMEOUT_SEC):
        with state_lock:
            cancelled.set()
            late_source = result.pop("source", None)
        if late_source is not None:
            _close_late_source(late_source)
        printLog(
            f"Timed out after {_MIC_OPEN_TIMEOUT_SEC}s opening audio device "
            f"(device_kwargs={device_kwargs})"
        )
        raise OSError("Timed out opening audio device")

    if "error" in result:
        raise result["error"]
    return _LockedAudioSource(result["source"])


def _wrapStopperWithBlockingReadUnblock(
    source: Any,
    raw_stop: Callable[..., None],
    before_stop: Optional[Callable[[], None]] = None,
) -> Callable[..., None]:
    """`listen_energy_and_audio_in_background`/`listen_with_segmenter_in_background`
    が返す生の stopper を、ブロッキング中の `stream.read()` を強制的に
    解除してから呼ぶようにラップする。エネルギー閾値方式/VAD方式の
    両 Recorder に共通する問題への対処なので、ここに集約して二重実装に
    よるドリフトを避ける。

    speech_recognition 側の stopper は listener スレッドの join() に
    タイムアウトを持たない。listener は self.source.stream.read() で
    ブロックしており、WASAPI ループバックの無音時などデータが来なく
    なると read() は返らず、stop() が永久にブロックしてしまう。
    Pa_StopStream (pyaudio_stream.stop_stream) は稼働中のストリームを
    別スレッドから止める用途の API で、進行中の read を強制的に返させる。
    Pa_CloseStream と異なり別スレッドから呼んでもデッドロックしない。
    self.source.stream は speech_recognition の MicrophoneStream ラッパで、
    実 PyAudio stream は .pyaudio_stream 属性経由でアクセスする。
    """

    def stopper(wait_for_stop: bool = True) -> None:
        if before_stop is not None:
            before_stop()
        try:
            with pyaudio_op_lock:
                sr_stream = getattr(source, "stream", None)
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
        raw_stop(wait_for_stop=wait_for_stop)

    return stopper


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
        label: str = "mic",
    ) -> None:
        self.recorder = Recognizer()
        self.recorder.energy_threshold = energy_threshold
        self.recorder.dynamic_energy_threshold = dynamic_energy_threshold
        self.phrase_time_limit = phrase_time_limit
        # record_timeout=0 (以下) は「無制限録音」の意図として扱う (issue #113)。
        # custom_speech_recognition 3.10.4.3 以降は録音ループ冒頭で
        #   if time.time() - record_start_time > record_timeout: raise WaitTimeoutError
        # というガードが入り、0 を渡すとループ突入直後に必ず真になって
        # 1 バッファも読めないまま録音が中断され、音声が一切拾えなくなる。
        # v3.1.0 時代の実質挙動 (record_timeout 無視) に合わせ、非正値は
        # 事実上の無制限 (inf) に正規化する。フレーズ終端は energy ベースの
        # 無音検出 (と phrase_time_limit) が引き続き担う。
        if not record_timeout or record_timeout <= 0:
            self.record_timeout = float("inf")
        else:
            self.record_timeout = record_timeout
        self.stop = None
        self.pause = None
        self.resume = None

        if source is None:
            raise ValueError("audio source can't be None")

        self.source = source
        self.label = label
        self._stop_requested = threading.Event()
        self._device_error_lock = threading.Lock()
        self.device_error_info: Optional[AudioPipelineFailure] = None
        self.SAMPLE_RATE = source.SAMPLE_RATE
        self.SAMPLE_WIDTH = source.SAMPLE_WIDTH
        self.channels = getattr(source, "channels", 1)
        # Set when the background listener thread dies from an unexpected
        # stream error (e.g. the device was unplugged) rather than a normal
        # stop() call, so callers can surface a "device lost" notice instead
        # of silently going quiet.
        self.device_error_event = threading.Event()
        set_read_error_handler = getattr(source, "set_read_error_handler", None)
        if callable(set_read_error_handler):
            set_read_error_handler(self._on_stream_read_error)

    def _recording_error_code(self) -> ErrorCode:
        return ErrorCode.AUDIO_READ_ERROR

    def _set_device_error(self, error: Exception, error_code: Optional[ErrorCode] = None) -> None:
        if self._stop_requested.is_set():
            return
        with self._device_error_lock:
            if self.device_error_event.is_set():
                return
            code = error_code or self._recording_error_code()
            self.device_error_info = AudioPipelineFailure(
                error_code=code,
                stage="recording",
                source=self.label,
                message=ERROR_METADATA[code]["message"],
                exception_type=type(error).__name__,
            )
            errorLogging()
            self.device_error_event.set()

    def _on_stream_read_error(self, error: Exception) -> None:
        self._set_device_error(error)

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
                item = (raw, datetime.now())
                # 文字起こしが実時間に追いつけていない状況。ここでブロック
                # すると listener スレッド (このコールバック自体) が止まり
                # 録音が滞るため、非ブロッキングで積み、満杯なら最も古い
                # チャンクを1つ捨てて追いつく方を優先する (フェーズ3項目20)。
                # audio_queue に maxsize が無い場合 (_DiscardQueue 等) は
                # 常にFalseが返る (Fullが発生しないため)。
                if putDroppingOldestOnFull(audio_queue, item):
                    printLog("audio_queue is full; dropped the oldest queued chunk to keep up")
            except Exception as error:  # noqa: BLE001 - report and preserve callback failure
                self._set_device_error(error)

        def energy_callback(energy) -> None:
            try:
                # 音量メーター用途で直近の値のみ意味を持つため、
                # audio_queue と同じ理由で非ブロッキング化し、消費側
                # (sendEnergy) が追いつけない場合は古い値を捨てる
                # (フェーズ3項目20、energy_queue は maxsize=1 で構築される)。
                putDroppingOldestOnFull(energy_queue, energy)
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
        except Exception as error:  # noqa: BLE001 - report and preserve setup failure
            self._set_device_error(error)
            raise

        self.stop = _wrapStopperWithBlockingReadUnblock(
            self.source, stop, before_stop=self._stop_requested.set
        )
        self.pause = pause
        self.resume = resume


class BaseVadAndAudioRecorder:
    """`BaseEnergyAndAudioRecorder` の VAD 版。フレーズ境界検出を
    `speech_recognition` の energy_threshold/pause_threshold ではなく、
    `VadRecognizerAdapter` (Silero VAD ベースの `VadSegmenter`) に委譲する。

    ストリームの open/close・停止/一時停止の仕組み (`_create_microphone`
    による同一デバイス二重オープン防止、`_wrapStopperWithBlockingReadUnblock`
    によるブロッキング read の強制解除) は `BaseEnergyAndAudioRecorder` と
    完全に同じものをそのまま流用する。差分は「フレーズ区切りの判定方法」
    だけに閉じている。

    VAD は発話開始前のプリロール (pre_speech_pad_frames) と、無音か
    どうかの実際の確率で終端を判定する anchor 方式のヒステリシスを持つ。
    これはエネルギー閾値方式の `phrase_time_limit` (record_timeout 秒で
    単語の途中でも問答無用で打ち切る) が引き起こす「文章の途中で切れる」
    「静かな出だしを取りこぼす」症状への対策として、2026-09-06に
    2度目の実機検証成功実装 (WIP commit 0e4a8d84) を土台に再導入した。

    オプトイン機能 (config.MIC_ENABLE_VAD/SPEAKER_ENABLE_VAD、既定 False) の実装で、既定の
    エネルギー閾値方式の挙動には一切影響しない。
    """

    def __init__(self, source: Any, record_timeout: int, label: str = "vad") -> None:
        self.recorder = Recognizer()
        self.record_timeout = float("inf") if record_timeout <= 0 else record_timeout
        self.stop = None
        self.pause = None
        self.resume = None

        if source is None:
            raise ValueError("audio source can't be None")

        self.source = source
        self.label = label
        self._stop_requested = threading.Event()
        self._device_error_lock = threading.Lock()
        self.device_error_info: Optional[AudioPipelineFailure] = None
        self.device_error_event = threading.Event()
        set_read_error_handler = getattr(source, "set_read_error_handler", None)
        if callable(set_read_error_handler):
            set_read_error_handler(self._on_stream_read_error)
        # max_speech_frames を record_timeout (既定3秒) に連動させていた
        # 時期があったが、実機検証で「長い連続発話ほど内容が丸ごと
        # 抜け落ちる」regressionを引き起こした (2026-09-06)。無音を挟まない
        # 継続発話で record_timeout 秒ごとに強制打ち切りが頻発し、単語の
        # 途中で始まり/終わる不自然な断片を単独でエンジンに送ることになる
        # 結果、境界の不自然さでエンジン側の信頼度フィルタ (Whisper の
        # avg_logprob/no_speech_prob、Google の recognize_google が返す
        # UnknownValueError) に断片ごと棄却されるケースが増えていた。
        # 強制打ち切り (reason="max_duration") された断片は
        # AudioTranscriber 側で単独送信せず蓄積するよう変更した (下記
        # audio_callback の reason 伝播、transcription_transcriber.py 参照)
        # ため、この値は「1回のエンジン呼び出しの粒度」ではなく純粋に
        #「無音が来ない場合の安全弁」の役割になった。PuriPuly-heart の
        # `VadGating.PEER_MAX_SEGMENT_MS` (7秒、docs/ref/PuriPuly-heart 参照)
        # を参考値としてそのまま採用する。
        #
        # 2026-09-07: Google (無料/非公式エンドポイント) 向けにこの値を
        # エンジン別に短縮する対策を一時的に試したが、実機検証で
        # 「呼び出し頻度が上がり過ぎて処理が悪化した」regressionが確認され
        # 撤回した。最終的には AudioTranscriber 側でクリップ前後に無音
        # パディングを付与するだけで無応答/内容欠落が解消したため
        # (transcription_transcriber.py の VAD_PRE_PAD_MS/VAD_POST_PAD_MS
        # 参照)、この値はエンジンを問わず常に固定 (7秒) のままでよい。
        _MAX_SPEECH_DURATION_MS = 7000
        max_speech_frames = max(1, round(_MAX_SPEECH_DURATION_MS / FRAME_DURATION_MS))
        # diagnostic_callback を printLog に繋いでおく。process.log に
        # speech_start/speech_end の実測タイミングが残るので、体感の遅さの
        # 原因 (hangover 待ち・モデル初回ロード・処理そのもの等) を
        # 実機ログから切り分けられるようにするため。
        self.vad_adapter = VadRecognizerAdapter(
            native_sample_rate=source.SAMPLE_RATE,
            native_sample_width=source.SAMPLE_WIDTH,
            native_channels=getattr(source, "channels", 1),
            segmenter=VadSegmenter(
                max_speech_frames=max_speech_frames,
                diagnostic_callback=printLog,
                diagnostic_label=label,
            ),
        )
        self._error_reporting_segmenter = _ErrorReportingSegmenter(
            self.vad_adapter, self._on_vad_error
        )
        # AudioTranscriber は self.SAMPLE_RATE/SAMPLE_WIDTH/channels を、
        # audio_queue に積まれる生バイト列 (last_sample) の実際の形式として
        # そのまま AudioData の再構成に使う (processMicData/processSpeakerData)。
        # VAD 経由の音声は常に vad_adapter が正規化した 16kHz/16bit/mono に
        # なっているため、ここはネイティブなデバイスのフォーマット
        # (source.SAMPLE_RATE 等) ではなく vad_adapter 側の値を公開する。
        # 混同するとサンプルレートが違う音声として再生/認識され、
        # 認識精度が壊滅的に低下する (実機で確認済みの不具合)。
        self.SAMPLE_RATE = self.vad_adapter.sample_rate
        self.SAMPLE_WIDTH = self.vad_adapter.sample_width
        self.channels = 1

    def _on_stream_read_error(self, error: Exception) -> None:
        if self._stop_requested.is_set():
            return
        with self._device_error_lock:
            if self.device_error_event.is_set():
                return
            code = ErrorCode.AUDIO_READ_ERROR
            self.device_error_info = AudioPipelineFailure(
                error_code=code,
                stage="recording",
                source=self.label,
                message=ERROR_METADATA[code]["message"],
                exception_type=type(error).__name__,
            )
            errorLogging()
            self.device_error_event.set()

    def _on_vad_error(self, error: Exception) -> None:
        if self._stop_requested.is_set():
            return
        with self._device_error_lock:
            if self.device_error_event.is_set():
                return
            self.device_error_info = AudioPipelineFailure(
                error_code=ErrorCode.VAD_INFERENCE_ERROR,
                stage="vad",
                source=self.label,
                message=ERROR_METADATA[ErrorCode.VAD_INFERENCE_ERROR]["message"],
                exception_type=type(error).__name__,
            )
            errorLogging()
            self.device_error_event.set()

    def adjustForNoise(self) -> None:
        # VAD はエネルギー閾値のキャリブレーションを必要としないため no-op。
        # BaseEnergyAndAudioRecorder と同じインターフェースを保つために存在する。
        pass

    def recordIntoQueue(self, audio_queue: Any, energy_queue: Any = None) -> None:
        """listen_with_segmenter_in_background で VAD が確定した発話区間ごとに
        audio を audio_queue に積む。audio_queue には
        (raw_bytes, recorded_at, reason) の3要素タプルを push する
        (BaseEnergyAndAudioRecorder の2要素タプルとは形が異なる点に注意)。

        reason は "silence"/"flush"/"max_duration"/None のいずれか
        (`audio_vad.SpeechSegment.reason`、custom_speech_recognition フォークの
        `AudioData.segment_reason` として伝播されたもの)。
        AudioTranscriber.transcribeAudioQueue は reason=="max_duration"
        (無音を挟まない強制打ち切り) の場合は単独で確定・送信せず蓄積し、
        それ以外 (自然な区切り) の場合だけ即座に確定・送信する
        (2026-09-06、実機で「強制打ち切り断片が単独送信され、エンジン側の
        信頼度フィルタで丸ごと棄却される」regressionが判明したための対策)。
        """

        def audio_callback(_, audio) -> None:
            try:
                raw = audio.get_raw_data()
                reason = getattr(audio, "segment_reason", None)
                item = (raw, datetime.now(), reason)
                # BaseEnergyAndAudioRecorder.audio_callback と同じ理由
                # (フェーズ3項目20)。VAD 経由でも文字起こしが実時間に
                # 追いつけない状況は起こり得るため同じ有界化を適用する。
                if putDroppingOldestOnFull(audio_queue, item):
                    printLog("audio_queue is full; dropped the oldest queued chunk to keep up")
            except Exception as error:  # noqa: BLE001 - report callback failure
                self._on_stream_read_error(error)

        def energy_callback(energy) -> None:
            try:
                putDroppingOldestOnFull(energy_queue, energy)
            except Exception:
                errorLogging()

        try:
            stop, pause, resume = self.recorder.listen_with_segmenter_in_background(
                source=self.source,
                callback=audio_callback,
                segmenter=self._error_reporting_segmenter,
                callback_energy=energy_callback if energy_queue is not None else None,
                record_timeout=self.record_timeout,
            )
        except Exception as error:  # noqa: BLE001 - report setup failure
            self._on_stream_read_error(error)
            raise

        self.stop = _wrapStopperWithBlockingReadUnblock(
            self.source, stop, before_stop=self._stop_requested.set
        )
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
            label="mic",
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
            channels=int(device.get("maxInputChannels", 1)),
        )
        super().__init__(
            source=source,
            energy_threshold=energy_threshold,
            dynamic_energy_threshold=dynamic_energy_threshold,
            phrase_time_limit=phrase_time_limit,
            record_timeout=record_timeout,
            label="speaker",
        )


class SelectedMicVadRecorder(BaseVadAndAudioRecorder):
    def __init__(self, device: dict, record_timeout: int = 5) -> None:
        source = _create_microphone(
            {},
            device_index=int(device.get("index", -1)),
            sample_rate=int(device.get("defaultSampleRate", 16000)),
        )
        super().__init__(source=source, record_timeout=record_timeout, label="mic")


class SelectedSpeakerVadRecorder(BaseVadAndAudioRecorder):
    def __init__(self, device: dict, record_timeout: int = 5) -> None:
        source = _create_microphone(
            {"speaker": True},
            speaker=True,
            device_index=int(device.get("index", -1)),
            sample_rate=int(device.get("defaultSampleRate", 16000)),
            channels=int(device.get("maxInputChannels", 1)),
        )
        super().__init__(source=source, record_timeout=record_timeout, label="speaker")
