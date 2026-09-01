import atexit
import copy
import asyncio
import faulthandler
import json
from subprocess import Popen
from os import makedirs as os_makedirs
from os import path as os_path
from os import getppid as os_getppid
from os import _exit as os_exit
from os import remove as os_remove
from os import stat as os_stat
from psutil import Process as psutil_Process
from datetime import datetime
from time import sleep
from queue import Queue
from threading import Thread
from requests import get as requests_get
from typing import Callable, Optional, cast
from packaging.version import parse
from dataclasses import dataclass

from flashtext import KeywordProcessor

from device_manager import device_manager
from config import config

from models.translation.translation_translator import Translator
from models.osc.osc import OSCHandler
from models.transcription.transcription_recorder import SelectedMicEnergyAndAudioRecorder, SelectedSpeakerEnergyAndAudioRecorder
from models.transcription.transcription_transcriber import AudioTranscriber
from models.translation.translation_languages import translation_lang
from models.transcription.transcription_languages import transcription_lang
from models.translation.translation_utils import checkCTranslate2Weight, downloadCTranslate2Weight, downloadCTranslate2Tokenizer, backwardCompatibleRenameWeightsDir
from models.transcription.transcription_whisper import checkWhisperWeight, downloadWhisperWeight
from models.transliteration.transliteration_transliterator import Transliterator
from models.overlay.overlay import Overlay
from models.overlay.overlay_image import OverlayImage
from models.watchdog.watchdog import Watchdog
from models.websocket.websocket_server import WebSocketServer
from models.obs.obs_browser_source_server import ObsBrowserSourceServer
from models.clipboard.clipboard import Clipboard
from models.telemetry import Telemetry
from utils import errorLogging, setupLogger, printLog

TRANSCRIPT_STOP_JOIN_TIMEOUT = 15

# GitHub API 呼び出し / setup.exe ダウンロードの (connect, read) タイムアウト。
# 無指定だと「接続はするが応答しない」相手に requests が無期限にブロック
# しうる。checkSoftwareUpdated()/listAvailableReleases() は
# Controller.init() から呼ばれるため、これが起きると初期化そのものが
# 固まる。translation_utils.py/transcription_whisper.py の
# _DOWNLOAD_TIMEOUT と同じ値を使う (大きめの read 側はモデル重みと同様、
# setup.exe のダウンロードにも余裕を持たせるため)。
_HTTP_TIMEOUT = (10, 60)

# フリーズ調査用の恒久計装。mainloop.py の faulthandler.enable() は
# ネイティブフォルト (access violation 等) 発生時にしか全スレッドの
# コールスタックを記録しない。今回問題になっている「クラッシュではなく
# 無応答のまま固まる」ケースはネイティブフォルトを伴わないため、それとは
# 別に dump_traceback_later でタイムアウト検知のスタックダンプを取る。
# feedWatchdog() が呼ばれるたびにタイマーを再武装し (呼び出しは
# フロントエンドから ~WATCHDOG_INTERVAL 秒ごとに来る)、その周期を超えて
# 次の feed が来なければ、その時点の全スレッドスタックを
# freeze_trace.log に書き出す (exit=False なのでプロセスは落とさない)。
# faulthandler は enable/dump_traceback_later 時点で fd を掴むため
# 遅延 open できず、フリーズ無しの通常終了でも 0 バイトのファイルが
# 残る。運用上のゴミ化を避けるため atexit で「書き込みが無ければ削除」する。
_freeze_trace_path = "freeze_trace.log"
_freeze_trace_file = open(_freeze_trace_path, "a", encoding="utf-8")
_FREEZE_DUMP_MARGIN_SEC = 15


def _cleanupFreezeTraceIfEmpty() -> None:
    try:
        _freeze_trace_file.close()
    except Exception:
        pass
    try:
        if os_path.exists(_freeze_trace_path) and os_stat(_freeze_trace_path).st_size == 0:
            os_remove(_freeze_trace_path)
    except Exception:
        pass


atexit.register(_cleanupFreezeTraceIfEmpty)


@dataclass
class ReleaseInfo:
    tag: str
    version: str
    is_prerelease: bool
    published_at: str


class _DiscardQueue(Queue):
    """Queue that silently drops everything put into it.

    Energy-meter-only recording uses SelectedMic/SpeakerEnergyAndAudioRecorder,
    whose listener always pushes audio chunks into the audio_queue argument
    even when nobody wants the audio (only the energy_queue is consumed).
    Passing this instead of a real Queue avoids an unbounded memory leak
    from chunks nobody ever drains.
    """

    def put(self, *args, **kwargs) -> None:
        pass


class threadFnc(Thread):
    """A tiny Thread wrapper that repeatedly calls a function.

    Usage: threadFnc(fnc, end_fnc=None, daemon=True, *args, **kwargs)
    The target function will be called repeatedly inside run().
    """
    def __init__(self, fnc, end_fnc=None, daemon: bool = True, *args, **kwargs):
        # Do not pass target to super; manage call explicitly so we can
        # store args/kwargs on the instance for later use.
        super(threadFnc, self).__init__(daemon=daemon)
        self.fnc = fnc
        self.end_fnc = end_fnc
        self.loop = True
        self._pause = False
        self._args = args
        self._kwargs = kwargs

    def stop(self) -> None:
        self.loop = False

    def pause(self) -> None:
        self._pause = True

    def resume(self) -> None:
        self._pause = False

    def run(self) -> None:
        try:
            while self.loop:
                try:
                    self.fnc(*self._args, **self._kwargs)
                except Exception:
                    # Protect the thread from terminating on user exceptions
                    errorLogging()
                while self._pause:
                    sleep(0.1)
        finally:
            if callable(self.end_fnc):
                try:
                    self.end_fnc()
                except Exception:
                    errorLogging()
        return


class AudioLifecycleWorker:
    """デバイス変化に伴う recorder の stop/start を専用スレッドで直列実行する。

    device_manager.monitoring() は Before/After コールバック
    (Controller.stopAccess*Devices / restartAccess*Devices) を自分の
    スレッド上で同期的に呼んでいた。これらは mic/speaker の
    stop (最大 TRANSCRIPT_STOP_JOIN_TIMEOUT 秒の join) や PyAudio open を
    含む重い処理のため、monitoring スレッドがその間ブロックされ、次の
    COM デバイス通知を取りこぼす窓ができていた。
    ここに enqueue することで monitoring スレッドは即座に呼び出しから
    戻れる。関数は FIFO で 1 つずつ実行されるため、
    Before → (デバイス列挙) → After の順序自体は保たれる。
    """

    def __init__(self) -> None:
        self._queue: "Queue[Callable[[], None]]" = Queue()
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

    def enqueue(self, fn: Callable[[], None]) -> None:
        self._queue.put(fn)

    def _run(self) -> None:
        while True:
            fn = self._queue.get()
            try:
                fn()
            except Exception:
                errorLogging()


class _AudioDeviceSession:
    """1つの物理デバイス (マイクまたはスピーカー) に対する Recorder の
    ライフサイクルを、features ("transcript"/"energy") 単位で統合管理する。

    以前は文字起こし用と音量メーター用でそれぞれ独立に
    SelectedMic/SpeakerEnergyAndAudioRecorder (= 独立した PyAudio
    Microphone) を生成・破棄しており、Config パネルで音量メーターを
    表示しながら文字起こしを ON にすると、同一物理デバイスに 2 つの
    Microphone が並立し得た。ここでは常に features の和集合に対して
    単一の Recorder を保持することでこれを防ぐ。

    このクラスは抽象基底で、マイク/スピーカー固有の設定 (config キー・
    Recorder クラス・AudioTranscriber の speaker フラグ) はサブクラスで
    _config / _recorder_cls 等として与える。

    呼び出し元 (Model) が Controller.mic/speaker_lifecycle_lock で
    直列化している前提とし、このクラス自体はロックを持たない。
    """

    _kind: str = ""  # "mic" / "speaker" — ログ・エラーメッセージ用

    def __init__(self) -> None:
        self.features: set[str] = set()
        self._recorder = None
        self._transcriber: Optional[AudioTranscriber] = None
        self._audio_queue: Optional[Queue] = None
        self._print_transcript: Optional[threadFnc] = None
        self._energy_progressbar: Optional[threadFnc] = None
        self.transcript_fnc: Optional[Callable[[dict], None]] = None
        self.energy_fnc: Callable[[float], None] = lambda v: None
        # 現在 Recorder が開いているデバイス (dict) を保持し、
        # reconfigure() で「同一デバイスかつ features 変化なし」なら no-op
        # にするために使う。
        self._active_device: Optional[dict] = None

    @staticmethod
    def _device_key(device: Optional[dict]) -> Optional[tuple]:
        """デバイスの同一性判定に使う key。

        pyaudio が返す dict は不安定なフィールド (defaultLowInputLatency 等) を
        含むため生 dict 比較は使えない。ホスト内で一意な (name, index) の
        タプルで判定する。
        """
        if device is None:
            return None
        return (device.get("name"), device.get("index"))

    # --- サブクラスが実装するフック -------------------------------------

    def _resolve_device(self, override: Optional[dict] = None) -> Optional[dict]:
        raise NotImplementedError

    def _create_recorder(self, device: dict):
        raise NotImplementedError

    def _create_transcriber(self) -> AudioTranscriber:
        raise NotImplementedError

    def _transcribe(self, transcriber: AudioTranscriber, queue: Queue) -> bool:
        raise NotImplementedError

    # --- 公開 API ---------------------------------------------------------

    def reconfigure(
        self,
        *,
        transcript: Optional[bool] = None,
        energy: Optional[bool] = None,
        device: Optional[dict] = None,
    ) -> None:
        """transcript/energy を True で有効化、False で無効化、None で現状維持。

        device を明示指定すると config を読まずそれを使う (Auto 選択で
        「実使用中エンドポイント」を渡すユースケース)。指定しなければ
        従来通り config (SELECTED_MIC_HOST/DEVICE 等) から解決する。

        差分検知: 「新 features == 現 features」かつ「解決したデバイス ==
        _active_device」なら no-op で早期 return。デバイスまたは features
        が変化した場合のみ stop→start する。これにより device 切替時に
        Recorder が二重に close/open されることを防ぐ。
        """
        new_features = set(self.features)
        if transcript is True:
            new_features.add("transcript")
        elif transcript is False:
            new_features.discard("transcript")
        if energy is True:
            new_features.add("energy")
        elif energy is False:
            new_features.discard("energy")

        # override が指定されなければ config から解決 (下位互換)
        resolved_device = self._resolve_device(override=device)

        same_features = new_features == self.features
        same_device = self._device_key(resolved_device) == self._device_key(self._active_device)
        # `_recorder is not None` だけでは、_start() が Recorder を生成した
        # 直後 (listener 起動前) に例外で失敗したケースを "起動済み" と誤認
        # してしまう (P0-2)。_start() は失敗時に必ず _recorder を None へ
        # 巻き戻すので通常はこの2つの判定は同じ結果になるが、"listener が
        # 実際に走っているか" という本来知りたい条件をそのまま書いておく。
        already_running = (not new_features) or (
            self._recorder is not None and self._recorder.stop is not None
        )
        if same_features and same_device and already_running:
            return

        self._stop()
        self.features = new_features
        if self.features:
            self._start(device=resolved_device)

    def pause(self) -> None:
        if self._recorder is not None and callable(self._recorder.pause):
            self._recorder.pause()

    def resume(self) -> None:
        if isinstance(self._audio_queue, Queue):
            while not self._audio_queue.empty():
                self._audio_queue.get()
        if self._recorder is not None and callable(self._recorder.resume):
            self._recorder.resume()

    @property
    def device_error_event(self):
        return self._recorder.device_error_event if self._recorder is not None else None

    # --- 内部実装 ---------------------------------------------------------

    def _start(self, *, device: Optional[dict]) -> None:
        # 呼び出し元 (reconfigure) が _resolve_device で解決済みの
        # デバイスを渡す。None は「使用可能なデバイス無し」を意味し、
        # ここで再解決はしない (再解決すると reconfigure の意図した
        # None → 停止のセマンティクスが壊れる)。
        if device is None:
            if "transcript" in self.features and callable(self.transcript_fnc):
                self.transcript_fnc({"text": False, "language": None})
            if "energy" in self.features:
                self.energy_fnc(False)
            self.features = set()
            self._active_device = None
            return

        # 現在開いているデバイスを記録 (reconfigure での差分検知に使用)
        self._active_device = device

        try:
            self._recorder = self._create_recorder(device)

            audio_queue = Queue() if "transcript" in self.features else _DiscardQueue()
            energy_queue: Optional[Queue] = Queue() if "energy" in self.features else None
            self._audio_queue = audio_queue
            self._recorder.recordIntoQueue(audio_queue, energy_queue)
        except Exception:
            # デバイスが処理中に切断される (実機で OSError: device gone を
            # 確認済み) 等で Recorder の生成/listener 起動が途中失敗すると、
            # 以前は self._recorder が非 None のまま残り、reconfigure() の
            # already_running 判定が「起動済み」と誤認してしまっていた
            # (P0-2)。ユーザーが文字起こしを OFF→ON しても永久に復帰しない
            # 原因だったため、自分が触った内部状態を全て「何も起動していない」
            # 状態へ巻き戻してから再送出する。
            #
            # features も合わせてリセットする: reconfigure() は _start() を
            # 呼ぶ前に self.features = new_features を代入済みだが、実際には
            # 何も起動できていないため、ここでリセットしないと
            # self._mic_session.features 等を直接参照する呼び出し元
            # (例: startMicTranscript) が「起動できた」と誤認しうる。
            self._recorder = None
            self._transcriber = None
            self._audio_queue = None
            self._active_device = None
            self.features = set()
            raise

        if "transcript" in self.features:
            self._transcriber = self._create_transcriber()
            transcriber = self._transcriber
            recorder = self._recorder

            def sendTranscript() -> None:
                try:
                    if recorder.device_error_event.is_set():
                        recorder.device_error_event.clear()
                        if callable(self.transcript_fnc):
                            self.transcript_fnc({"text": False, "language": None})
                        return
                    if self._transcribe(transcriber, audio_queue) and callable(self.transcript_fnc):
                        result = transcriber.getTranscript()
                        result["recognition_error"] = transcriber.last_recognition_error
                        self.transcript_fnc(result)
                except Exception:
                    errorLogging()

            def endTranscript() -> None:
                while not audio_queue.empty():
                    audio_queue.get()
                self._transcriber = None
                # 明示 gc.collect() は呼ばない: ActiveEndpointTracker が別スレッド
                # (CoInitialize 済み apartment) で保持している comtypes の COM
                # ポインタが、この _print_transcript スレッド (CoInitialize
                # していない) 上で __del__ → Release() されて access violation
                # を起こすことを crash_trace.log で 2026-08-19 に確認した。
                # 参照が実際に不要になれば通常の GC が回収する。

            self._print_transcript = threadFnc(sendTranscript, end_fnc=endTranscript)
            self._print_transcript.daemon = True
            self._print_transcript.start()

        if "energy" in self.features:
            def sendEnergy() -> None:
                if not energy_queue.empty():
                    energy = energy_queue.get()
                    try:
                        self.energy_fnc(energy)
                    except Exception:
                        errorLogging()
                sleep(0.01)

            self._energy_progressbar = threadFnc(sendEnergy)
            self._energy_progressbar.daemon = True
            self._energy_progressbar.start()

    def _stop(self) -> None:
        if isinstance(self._print_transcript, threadFnc):
            self._print_transcript.stop()
            self._print_transcript.join(timeout=TRANSCRIPT_STOP_JOIN_TIMEOUT)
            if self._print_transcript.is_alive():
                printLog(f"{self._kind.capitalize()} transcription thread did not terminate within timeout")
            self._print_transcript = None
        if isinstance(self._energy_progressbar, threadFnc):
            self._energy_progressbar.stop()
            self._energy_progressbar.join()
            self._energy_progressbar = None
        if self._recorder is not None:
            # _start() のロールバックにより通常はここに来ないはずだが、
            # 万一 recordIntoQueue() が listener 起動前に失敗した Recorder
            # (resume/stop がまだ None のまま) が渡ってきても TypeError で
            # _stop() 自体を失敗させないよう callable() で防御する。
            if callable(self._recorder.resume):
                self._recorder.resume()
            if callable(self._recorder.stop):
                self._recorder.stop()
            self._recorder = None
        self._transcriber = None
        self._audio_queue = None
        self._active_device = None


class MicSession(_AudioDeviceSession):
    _kind = "mic"

    def _resolve_device(self, override: Optional[dict] = None) -> Optional[dict]:
        if override is not None:
            # NoDevice が明示的に渡された場合は None (デバイス無し) 扱い
            if override.get("name") == "NoDevice":
                return None
            return override
        mic_host_name = config.SELECTED_MIC_HOST
        mic_device_name = config.SELECTED_MIC_DEVICE
        mic_device_list = device_manager.getMicDevices().get(mic_host_name, [{"name": "NoDevice"}])
        selected_mic_device = [d for d in mic_device_list if d["name"] == mic_device_name]
        if not selected_mic_device or mic_device_name == "NoDevice":
            return None
        return selected_mic_device[0]

    def _create_recorder(self, device: dict):
        record_timeout = config.MIC_RECORD_TIMEOUT
        phrase_timeout = config.MIC_PHRASE_TIMEOUT
        if record_timeout > phrase_timeout:
            record_timeout = phrase_timeout
        return SelectedMicEnergyAndAudioRecorder(
            device=device,
            energy_threshold=config.MIC_THRESHOLD,
            dynamic_energy_threshold=config.MIC_AUTOMATIC_THRESHOLD,
            phrase_time_limit=record_timeout,
            record_timeout=record_timeout,
        )

    def _create_transcriber(self) -> AudioTranscriber:
        phrase_timeout = config.MIC_PHRASE_TIMEOUT
        return AudioTranscriber(
            speaker=False,
            source=self._recorder,
            phrase_timeout=phrase_timeout,
            max_phrases=config.MIC_MAX_PHRASES,
            transcription_engine=config.SELECTED_TRANSCRIPTION_ENGINE,
            root=config.PATH_LOCAL,
            whisper_weight_type=config.WHISPER_WEIGHT_TYPE,
            device=config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE["device"],
            device_index=config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE["device_index"],
            compute_type=config.SELECTED_TRANSCRIPTION_COMPUTE_TYPE,
        )

    def _transcribe(self, transcriber: AudioTranscriber, queue: Queue) -> bool:
        selected_your_languages = config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]
        languages = [d["language"] for d in selected_your_languages.values() if d["enable"] is True]
        countries = [d["country"] for d in selected_your_languages.values() if d["enable"] is True]
        return transcriber.transcribeAudioQueue(
            queue,
            languages,
            countries,
            config.MIC_AVG_LOGPROB,
            config.MIC_NO_SPEECH_PROB,
            config.MIC_NO_REPEAT_NGRAM_SIZE,
        )


class SpeakerSession(_AudioDeviceSession):
    _kind = "speaker"

    def _resolve_device(self, override: Optional[dict] = None) -> Optional[dict]:
        if override is not None:
            if override.get("name") == "NoDevice":
                return None
            return override
        speaker_device_name = config.SELECTED_SPEAKER_DEVICE
        speaker_device_list = device_manager.getSpeakerDevices()
        selected_speaker_device = [d for d in speaker_device_list if d["name"] == speaker_device_name]
        if not selected_speaker_device or speaker_device_name == "NoDevice":
            return None
        return selected_speaker_device[0]

    def _create_recorder(self, device: dict):
        record_timeout = config.SPEAKER_RECORD_TIMEOUT
        phrase_timeout = config.SPEAKER_PHRASE_TIMEOUT
        if record_timeout > phrase_timeout:
            record_timeout = phrase_timeout
        return SelectedSpeakerEnergyAndAudioRecorder(
            device=device,
            energy_threshold=config.SPEAKER_THRESHOLD,
            dynamic_energy_threshold=config.SPEAKER_AUTOMATIC_THRESHOLD,
            phrase_time_limit=record_timeout,
            record_timeout=record_timeout,
        )

    def _create_transcriber(self) -> AudioTranscriber:
        phrase_timeout = config.SPEAKER_PHRASE_TIMEOUT
        return AudioTranscriber(
            speaker=True,
            source=self._recorder,
            phrase_timeout=phrase_timeout,
            max_phrases=config.SPEAKER_MAX_PHRASES,
            transcription_engine=config.SELECTED_TRANSCRIPTION_ENGINE,
            root=config.PATH_LOCAL,
            whisper_weight_type=config.WHISPER_WEIGHT_TYPE,
            device=config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE["device"],
            device_index=config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE["device_index"],
            compute_type=config.SELECTED_TRANSCRIPTION_COMPUTE_TYPE,
        )

    def _transcribe(self, transcriber: AudioTranscriber, queue: Queue) -> bool:
        selected_target_languages = config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO]
        languages = [d["language"] for d in selected_target_languages.values() if d["enable"] is True]
        countries = [d["country"] for d in selected_target_languages.values() if d["enable"] is True]
        return transcriber.transcribeAudioQueue(
            queue,
            languages,
            countries,
            config.SPEAKER_AVG_LOGPROB,
            config.SPEAKER_NO_SPEECH_PROB,
            config.SPEAKER_NO_REPEAT_NGRAM_SIZE,
        )


class Model:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Model, cls).__new__(cls)
            # Do NOT call init() here to avoid heavy import-time work.
            # Callers should call `model.init()` explicitly or rely on
            # `ensure_initialized()` which will lazy-initialize on demand.
            cls._instance._inited = False
        return cls._instance

    def init(self):
        """Perform full initialization of resources.

        This method performs heavy construction (models, overlay, threads)
        and is intentionally not called at import time. Call explicitly
        or let `ensure_initialized()` call it lazily.
        """
        if getattr(self, '_inited', False):
            return

        self.logger = None
        self.th_check_device = None
        # マイク/スピーカーそれぞれの文字起こし・エナジー計測は
        # _AudioDeviceSession (MicSession/SpeakerSession) に集約されている。
        # 1 物理デバイスにつき Recorder (= PyAudio Microphone) が常に
        # 1 つだけになるよう、features (transcript/energy) の和集合を
        # session が管理する。
        self._mic_session = MicSession()
        self._speaker_session = SpeakerSession()
        self.audio_lifecycle_worker = AudioLifecycleWorker()

        self.previous_send_message = ""
        self.previous_receive_message = ""
        self.translator = Translator()
        self.keyword_processor = KeywordProcessor()
        self.translation_history: list[dict] = []
        self.translation_history_max_items = 20
        overlay_small_log_settings = copy.deepcopy(config.OVERLAY_SMALL_LOG_SETTINGS)
        overlay_large_log_settings = copy.deepcopy(config.OVERLAY_LARGE_LOG_SETTINGS)
        overlay_large_log_settings["ui_scaling"] = overlay_large_log_settings["ui_scaling"] * 0.25
        overlay_settings = {
            "small": overlay_small_log_settings,
            "large": overlay_large_log_settings,
        }
        self.overlay = Overlay(overlay_settings)
        self.overlay_image = OverlayImage(config.PATH_LOCAL)
        self.mic_mute_status = None
        # OSC ミュート同期 (changeHandlerMute) が実行する pause()/resume() を
        # Controller.mic_lifecycle_lock 配下で行うためのフック。
        # Controller.__init__ が setMicMuteStatusChangeCallback() で
        # 自身のロック付きラッパーを登録する。Model は Controller を知らない
        # ままこの間接呼び出しだけを持つ (transcript_fnc/energy_fnc と同じ
        # コールバック注入パターン)。未登録時は changeMicTranscriptStatus() を
        # 直接使うフォールバックとする。
        self.mic_mute_status_change_callback: Optional[Callable[[], None]] = None
        self.transliterator = None
        self.watchdog = Watchdog(config.WATCHDOG_TIMEOUT, config.WATCHDOG_INTERVAL)
        self.osc_handler = OSCHandler(config.OSC_IP_ADDRESS, config.OSC_PORT)
        self.websocket_server = None
        self.websocket_server_loop = False
        self.websocket_server_alive = False
        self.th_websocket_server = None
        self.obs_browser_source_server = None
        self.clipboard = Clipboard()
        self.telemetry = Telemetry()

        self._inited = True

    def ensure_initialized(self) -> None:
        """Ensure the model has been initialized. This is safe to call from
        public methods that require initialized resources.
        """
        if not getattr(self, '_inited', False):
            try:
                self.init()
            except Exception:
                # Log and continue; callers should handle missing features.
                errorLogging()

    def backwardCompatibleTranslatorCTranslate2ModelRenameWeightsDir(self):
        return backwardCompatibleRenameWeightsDir(config.PATH_LOCAL)
        
    def checkTranslatorCTranslate2ModelWeight(self, weight_type:str):
        return checkCTranslate2Weight(config.PATH_LOCAL, weight_type)

    def changeTranslatorCTranslate2Model(self):
        self.ensure_initialized()
        self.translator.changeCTranslate2Model(
            path=config.PATH_LOCAL,
            model_type=config.CTRANSLATE2_WEIGHT_TYPE,
            device=config.SELECTED_TRANSLATION_COMPUTE_DEVICE["device"],
            device_index=config.SELECTED_TRANSLATION_COMPUTE_DEVICE["device_index"],
            compute_type=config.SELECTED_TRANSLATION_COMPUTE_TYPE
            )

    def downloadCTranslate2ModelWeight(self, weight_type, callback=None, end_callback=None):
        return downloadCTranslate2Weight(config.PATH_LOCAL, weight_type, callback, end_callback)

    def downloadCTranslate2ModelTokenizer(self, weight_type):
        return downloadCTranslate2Tokenizer(config.PATH_LOCAL, weight_type)

    def isLoadedCTranslate2Model(self):
        self.ensure_initialized()
        return self.translator.isLoadedCTranslate2Model()

    def isChangedTranslatorParameters(self):
        self.ensure_initialized()
        return self.translator.isChangedTranslatorParameters()

    def setChangedTranslatorParameters(self, is_changed):
        self.ensure_initialized()
        self.translator.setChangedTranslatorParameters(is_changed)

    def checkTranscriptionWhisperModelWeight(self, weight_type:str):
        return checkWhisperWeight(config.PATH_LOCAL, weight_type)

    def downloadWhisperModelWeight(self, weight_type, callback=None, end_callback=None):
        return downloadWhisperWeight(config.PATH_LOCAL, weight_type, callback, end_callback)

    def resetKeywordProcessor(self):
        self.ensure_initialized()
        del self.keyword_processor
        self.keyword_processor = KeywordProcessor()

    def authenticationTranslatorDeepLAuthKey(self, auth_key: str) -> bool:
        self.ensure_initialized()
        result = self.translator.authenticationDeepLAuthKey(auth_key)
        return result

    def authenticationTranslatorPlamoAuthKey(self, auth_key: str) -> bool:
        result = self.translator.authenticationPlamoAuthKey(auth_key, root_path=config.PATH_LOCAL)
        return result

    def getTranslatorPlamoModelList(self) -> list[str]:
        self.ensure_initialized()
        return self.translator.getPlamoModelList()

    def setTranslatorPlamoModel(self, model: str) -> bool:
        self.ensure_initialized()
        result = self.translator.setPlamoModel(model=model)
        return result

    def updateTranslatorPlamoClient(self) -> None:
        self.ensure_initialized()
        self.translator.updatePlamoClient()

    def authenticationTranslatorGeminiAuthKey(self, auth_key: str) -> bool:
        result = self.translator.authenticationGeminiAuthKey(auth_key, root_path=config.PATH_LOCAL)
        return result

    def getTranslatorGeminiModelList(self) -> list[str]:
        self.ensure_initialized()
        return self.translator.getGeminiModelList()

    def setTranslatorGeminiModel(self, model: str) -> bool:
        self.ensure_initialized()
        result = self.translator.setGeminiModel(model=model)
        return result

    def updateTranslatorGeminiClient(self) -> None:
        self.ensure_initialized()
        self.translator.updateGeminiClient()

    def authenticationTranslatorOpenAIAuthKey(self, auth_key: str, base_url: Optional[str] = None) -> bool:
        result = self.translator.authenticationOpenAIAuthKey(auth_key, base_url=base_url, root_path=config.PATH_LOCAL)
        return result

    def getTranslatorOpenAIModelList(self) -> list[str]:
        self.ensure_initialized()
        return self.translator.getOpenAIModelList()

    def setTranslatorOpenAIModel(self, model: str) -> bool:
        self.ensure_initialized()
        result = self.translator.setOpenAIModel(model=model)
        return result

    def updateTranslatorOpenAIClient(self) -> None:
        self.ensure_initialized()
        self.translator.updateOpenAIClient()

    def authenticationTranslatorOpenAICompatibleAuthKey(self, auth_key: str, base_url: Optional[str] = None) -> bool:
        result = self.translator.authenticationOpenAICompatibleAuthKey(
            auth_key, base_url=base_url, root_path=config.PATH_LOCAL
        )
        return result

    def getTranslatorOpenAICompatibleModelList(self) -> list[str]:
        self.ensure_initialized()
        return self.translator.getOpenAICompatibleModelList()

    def setTranslatorOpenAICompatibleModel(self, model: str) -> bool:
        self.ensure_initialized()
        return self.translator.setOpenAICompatibleModel(model=model)

    def updateTranslatorOpenAICompatibleClient(self) -> None:
        self.ensure_initialized()
        self.translator.updateOpenAICompatibleClient()

    def authenticationTranslatorGroqAuthKey(self, auth_key: str) -> bool:
        result = self.translator.authenticationGroqAuthKey(auth_key, root_path=config.PATH_LOCAL)
        return result

    def getTranslatorGroqModelList(self) -> list[str]:
        self.ensure_initialized()
        return self.translator.getGroqModelList()

    def setTranslatorGroqModel(self, model: str) -> bool:
        self.ensure_initialized()
        result = self.translator.setGroqModel(model=model)
        return result

    def updateTranslatorGroqClient(self) -> None:
        self.ensure_initialized()
        self.translator.updateGroqClient()

    def authenticationTranslatorOpenRouterAuthKey(self, auth_key: str) -> bool:
        result = self.translator.authenticationOpenRouterAuthKey(auth_key, root_path=config.PATH_LOCAL)
        return result

    def getTranslatorOpenRouterModelList(self) -> list[str]:
        self.ensure_initialized()
        return self.translator.getOpenRouterModelList()

    def setTranslatorOpenRouterModel(self, model: str) -> bool:
        self.ensure_initialized()
        result = self.translator.setOpenRouterModel(model=model)
        return result

    def updateTranslatorOpenRouterClient(self) -> None:
        self.ensure_initialized()
        self.translator.updateOpenRouterClient()

    def getTranslatorLMStudioConnected(self) -> bool:
        self.ensure_initialized()
        return self.translator.getLMStudioConnected()

    def authenticationTranslatorLMStudio(self, base_url: str) -> bool:
        result = self.translator.setLMStudioClientURL(base_url=base_url, root_path=config.PATH_LOCAL)
        return result

    def getTranslatorLMStudioModelList(self) -> list[str]:
        self.ensure_initialized()
        return self.translator.getLMStudioModelList()

    def setTranslatorLMStudioModel(self, model: str) -> bool:
        self.ensure_initialized()
        return self.translator.setLMStudioModel(model=model)

    def updateTranslatorLMStudioClient(self) -> None:
        self.ensure_initialized()
        self.translator.updateLMStudioClient()

    def getTranslatorOllamaConnected(self) -> bool:
        self.ensure_initialized()
        return self.translator.getOllamaConnected()

    def authenticationTranslatorOllama(self) -> bool:
        result = self.translator.checkOllamaClient(root_path=config.PATH_LOCAL)
        return result

    def getTranslatorOllamaModelList(self) -> list[str]:
        self.ensure_initialized()
        return self.translator.getOllamaModelList()

    def setTranslatorOllamaModel(self, model: str) -> bool:
        self.ensure_initialized()
        return self.translator.setOllamaModel(model=model)

    def updateTranslatorOllamaClient(self) -> None:
        self.ensure_initialized()
        self.translator.updateOllamaClient()

    def startLogger(self):
        self.ensure_initialized()
        os_makedirs(config.PATH_LOGS, exist_ok=True)
        file_name = os_path.join(config.PATH_LOGS, f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")
        self.logger = setupLogger("log", file_name)
        self.logger.disabled = False

    def stopLogger(self):
        self.ensure_initialized()
        self.logger.disabled = True
        self.logger = None

    def getListLanguageAndCountry(self):
        """List every language any translation engine supports for the UI.

        Deliberately NOT filtered to the currently selected engine: a user
        should be able to pick any language up front, and if the selected
        engine doesn't support it, the engine falls back instead (see
        Controller.updateTranslationEngineAndEngineList()). Filtering this
        list by engine instead forces users to switch to a
        broadly-compatible engine first, pick the language, then switch
        back - exactly the friction this list avoids.
        """
        transcription_langs = list(transcription_lang.keys())
        translation_langs = []
        for tl_key in translation_lang.keys():
            translation_langs.extend(self.getTranslationLanguagesForEngine(tl_key))
        translation_langs = list(set(translation_langs))
        supported_langs = list(filter(lambda x: x in transcription_langs, translation_langs))

        languages = []
        for language in supported_langs:
            for country in transcription_lang[language]:
                languages.append(
                    {
                        "language" : language,
                        "country" : country,
                    }
                )
        languages = sorted(languages, key=lambda x: x['language'])
        return languages

    def getTranslationLanguagesForEngine(self, engine: str) -> list[str]:
        """Friendly language names `engine` supports as a source language."""
        if engine == "CTranslate2":
            languages = translation_lang.get(engine, {}).get(config.CTRANSLATE2_WEIGHT_TYPE, {}).get("source", {})
        else:
            languages = translation_lang.get(engine, {}).get("source", {})
        return list(languages.keys())

    def isLanguageSupportedByEngine(self, engine: str, language: str) -> bool:
        return language in self.getTranslationLanguagesForEngine(engine)

    def pickDefaultLanguageForEngine(self, engine: str, avoid_languages) -> dict:
        """Pick a language `engine` supports, preferring Japanese then
        English (the app's own defaults), and avoiding anything in
        `avoid_languages` so the pick can't collide with another slot
        (e.g. resetting the source language to the same value as an
        already-fine enabled target).
        """
        avoid_languages = set(avoid_languages)
        for language, country in (("Japanese", "Japan"), ("English", "United States")):
            if language not in avoid_languages and self.isLanguageSupportedByEngine(engine, language):
                return {"language": language, "country": country}
        for language in self.getTranslationLanguagesForEngine(engine):
            if language not in avoid_languages and language in transcription_lang:
                return {"language": language, "country": next(iter(transcription_lang[language]))}
        # Every language this engine supports is already taken by another
        # slot - nothing to pick that wouldn't collide.
        return None

    def findTranslationEngines(self, source_lang, target_lang, engines_status):
        selectable_engines = [key for key, value in engines_status.items() if value is True]
        compatible_engines = []
        for engine in list(translation_lang.keys()):
            language_list = self.getTranslationLanguagesForEngine(engine)
            source_langs = [e["language"] for e in list(source_lang.values()) if e["enable"] is True]
            target_langs = [e["language"] for e in list(target_lang.values()) if e["enable"] is True]

            if all(e in language_list for e in source_langs) and all(e in language_list for e in target_langs):
                if engine in selectable_engines:
                    compatible_engines.append(engine)

        return compatible_engines

    def addTranslationHistory(self, source: str, text: str) -> None:
        """Add a message to translation context history.
        
        Args:
            source: "chat" | "mic" | "speaker"
            text: message content
        """
        self.ensure_initialized()
        if not text or not text.strip():
            return
        
        history_item = {
            "source": source,
            "text": text.strip(),
            "timestamp": datetime.now().isoformat(),
        }
        self.translation_history.append(history_item)
        
        # 最大件数を超えた場合は古いものを削除
        if len(self.translation_history) > self.translation_history_max_items:
            self.translation_history = self.translation_history[-self.translation_history_max_items:]
    
    def getTranslationHistory(self, max_items: int = None) -> list[dict]:
        """Get recent translation context history.
        
        Args:
            max_items: Maximum number of items to return (newest first)
        
        Returns:
            List of history items
        """
        self.ensure_initialized()
        if max_items is None or max_items <= 0:
            return self.translation_history
        return self.translation_history[-max_items:]
    
    def clearTranslationHistory(self) -> None:
        """Clear all translation context history."""
        self.ensure_initialized()
        self.translation_history = []

    def getTranslate(self, translator_name, source_language, target_language, target_country, message):
        self.ensure_initialized()
        success_flag = False
        
        # Get context history for LLM-based translators
        history = self.getTranslationHistory()
        
        translation = self.translator.translate(
                        translator_name=translator_name,
                        weight_type=config.CTRANSLATE2_WEIGHT_TYPE,
                        source_language=source_language,
                        target_language=target_language,
                        target_country=target_country,
                        message=message,
                        context_history=history
                )

        # 翻訳失敗時のフェールセーフ処理
        # translation is None: 選択言語がこのエンジンで未対応（エンジン自体の障害ではない）
        # translation is False: エンジン側の実際の障害（レート制限・通信・認証・プロバイダエラー等）
        if isinstance(translation, str):
            success_flag = True
        else:
            max_retries = 20  # 0.1s間隔で最大2秒。CTranslate2が使用不可な場合の無限ループを防ぐ
            for _ in range(max_retries):
                translation = self.translator.translate(
                                    translator_name="CTranslate2",
                                    weight_type=config.CTRANSLATE2_WEIGHT_TYPE,
                                    source_language=source_language,
                                    target_language=target_language,
                                    target_country=target_country,
                                    message=message
                            )
                if isinstance(translation, str):
                    break
                if translation is None:
                    break  # CTranslate2もこの言語ペア未対応。リトライしても変わらない
                sleep(0.1)
            if isinstance(translation, str):
                success_flag = True
            elif translation is None:
                # どちらのエンジンもこの言語ペアに未対応なだけ。実障害ではない。
                success_flag = True
                translation = message
            else:
                # CTranslate2フォールバック自体が実際に失敗した。
                success_flag = False
                errorLogging()
                translation = message
        return translation, success_flag

    def getInputTranslate(self, message, source_language=None):
        self.ensure_initialized()
        translator_name=config.SELECTED_TRANSLATION_ENGINES[config.SELECTED_TAB_NO]
        if source_language is None:
            source_language=config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]["language"]
        target_languages=config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO]

        translations = []
        success_flags = []
        for value in target_languages.values():
            if value["enable"] is True:
                target_language = value["language"]
                target_country = value["country"]
                if target_language is not None or target_country is not None:
                    translation, success_flag = self.getTranslate(
                        translator_name,
                        source_language,
                        target_language,
                        target_country,
                        message
                        )
                    translations.append(translation)
                    success_flags.append(success_flag)

        return translations, success_flags

    def getOutputTranslate(self, message, source_language=None):
        self.ensure_initialized()
        translator_name=config.SELECTED_TRANSLATION_ENGINES[config.SELECTED_TAB_NO]
        if source_language is None:
            source_language=config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO]["1"]["language"]
        target_language=config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]["language"]
        target_country=config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]["country"]

        translation, success_flag = self.getTranslate(
            translator_name,
            source_language,
            target_language,
            target_country,
            message
            )
        return [translation], [success_flag]

    def addKeywords(self):
        self.ensure_initialized()
        for f in config.MIC_WORD_FILTER:
            self.keyword_processor.add_keyword(f)

    def checkKeywords(self, message):
        self.ensure_initialized()
        return len(self.keyword_processor.extract_keywords(message)) != 0

    def detectRepeatSendMessage(self, message):
        repeat_flag = self.previous_send_message == message
        self.previous_send_message = message
        return repeat_flag

    def detectRepeatReceiveMessage(self, message):
        repeat_flag = self.previous_receive_message == message
        self.previous_receive_message = message
        return repeat_flag

    def startTransliteration(self):
        self.ensure_initialized()
        if self.transliterator is None:
            self.transliterator = Transliterator()

    def stopTransliteration(self):
        self.ensure_initialized()
        if self.transliterator is not None:
            self.transliterator = None

    def convertMessageToTransliteration(self, message: str, hiragana: bool=True, romaji: bool=True) -> list:
        self.ensure_initialized()
        if hiragana is False and romaji is False:
            return []

        keys_to_keep = {"orig"}
        if hiragana:
            keys_to_keep.add("hira")
        if romaji:
            keys_to_keep.add("hepburn")

        if self.transliterator is None:
            self.startTransliteration()

        data_list = self.transliterator.analyze(message, use_macron=False)
        filtered_list = [
            {key: value for key, value in item.items() if key in keys_to_keep}
            for item in data_list
        ]
        return filtered_list

    def setOscIpAddress(self, ip_address):
        self.ensure_initialized()
        self.osc_handler.setOscIpAddress(ip_address)

    def setOscPort(self, port):
        self.ensure_initialized()
        self.osc_handler.setOscPort(port)

    def oscStartSendTyping(self):
        self.ensure_initialized()
        self.osc_handler.sendTyping(flag=True)

    def oscStopSendTyping(self):
        self.ensure_initialized()
        self.osc_handler.sendTyping(flag=False)

    def oscSendMessage(self, message:str):
        self.ensure_initialized()
        self.osc_handler.sendMessage(message=message, notification=config.NOTIFICATION_VRC_SFX)

    def setMuteSelfStatus(self):
        self.ensure_initialized()
        self.mic_mute_status = self.osc_handler.getOSCParameterMuteSelf()

    def setMicMuteStatusChangeCallback(self, fn: Optional[Callable[[], None]]) -> None:
        """OSC ミュート同期が pause()/resume() を実行する際に呼ぶ関数を登録する。

        Controller.__init__ が自身の mic_lifecycle_lock を取得する
        ラッパー (_changeMicTranscriptStatusLocked) を登録することで、
        OSC 受信スレッド発の pause()/resume() を他の全ての start/stop 系
        (mainloop ワーカーが直接呼ぶ startTranscriptionSendMessage 等も含む)
        と完全に排他制御する。未登録なら changeMicTranscriptStatus() を直接
        使う (Controller を経由しないテスト等でも壊れないようにするため)。
        """
        self.mic_mute_status_change_callback = fn

    def startReceiveOSC(self):
        self.ensure_initialized()
        def changeHandlerMute(address, osc_arguments):
            # ThreadingOSCUDPServer は受信メッセージごとに新しいスレッドを
            # 起こすため、ここはロックを一切持たない任意のスレッドで走る。
            # changeMicTranscriptStatus() を直接ここで呼ぶと、Auto Mic
            # Select のデバイス切替や mainloop ワーカーが直接呼ぶ
            # start/stop 系 (_stop()/_start() を実行中) と
            # _mic_session.pause()/resume() が無ロックで交錯し得る
            # (ミュート連打中にデバイスが切り替わると壊れた Recorder に
            # 触れる)。audio_lifecycle_worker.enqueue() で Auto Select の
            # 他のデバイス操作と同じ FIFO キューに直列化しつつ、実行される
            # 関数自体は mic_mute_status_change_callback (= Controller の
            # mic_lifecycle_lock 付きラッパー) にすることで、ロックを直接
            # 取得する経路とも完全に排他制御する。
            if config.VRC_MIC_MUTE_SYNC is True:
                if osc_arguments is True and self.mic_mute_status is False:
                    self.mic_mute_status = osc_arguments
                    self.audio_lifecycle_worker.enqueue(
                        self.mic_mute_status_change_callback or self.changeMicTranscriptStatus
                    )
                elif osc_arguments is False and self.mic_mute_status is True:
                    self.mic_mute_status = osc_arguments
                    self.audio_lifecycle_worker.enqueue(
                        self.mic_mute_status_change_callback or self.changeMicTranscriptStatus
                    )

        dict_filter_and_target = {
            self.osc_handler.osc_parameter_muteself: changeHandlerMute,
        }
        self.osc_handler.setDictFilterAndTarget(dict_filter_and_target)
        self.osc_handler.receiveOscParameters()

    def stopReceiveOSC(self):
        self.ensure_initialized()
        self.osc_handler.oscServerStop()

    def getIsOscQueryEnabled(self):
        self.ensure_initialized()
        return self.osc_handler.getIsOscQueryEnabled()

    @staticmethod
    def _isVersionSupported(version_str: str) -> bool:
        # VRCT 3.4.2 fails to start (fixed in 3.4.3); keep it out of both the
        # update-check comparison and the version picker.
        try:
            return parse(version_str) >= parse(config.MIN_SUPPORTED_VERSION)
        except Exception:
            return False

    @staticmethod
    def _fetchGithubReleases() -> list:
        # All releases (including prereleases), newest first, drafts excluded.
        # timeout 無しだと GitHub 側が「接続はするが応答しない」状態になった
        # 場合に無期限にブロックし、これを呼ぶ checkSoftwareUpdated() は
        # Controller.init() から呼ばれるため、初期化そのものが固まる。
        response = requests_get(config.GITHUB_RELEASES_LIST_URL, timeout=_HTTP_TIMEOUT)
        response.raise_for_status()
        releases = response.json()
        if not isinstance(releases, list):
            return []
        return [r for r in releases if isinstance(r, dict) and not r.get("draft", False)]

    @staticmethod
    def checkSoftwareUpdated():
        # check update
        update_flag = False
        version = ""
        try:
            if config.SELECTED_RELEASE_CHANNEL == "beta":
                candidates = [
                    r["name"] for r in Model._fetchGithubReleases()
                    if isinstance(r.get("name"), str) and Model._isVersionSupported(r["name"])
                ]
                version = candidates[0] if candidates else None
            else:
                response = requests_get(config.GITHUB_URL, timeout=_HTTP_TIMEOUT)
                json_data = response.json()
                version = json_data.get("name", None)
            if isinstance(version, str):
                new_version = parse(version)
                current_version = parse(config.VERSION)
                if new_version > current_version:
                    update_flag = True
        except Exception:
            errorLogging()
        return {
            "is_update_available": update_flag,
            "new_version": version,
        }

    @staticmethod
    def listAvailableReleases() -> list:
        # Version picker data source: all supported (>= MIN_SUPPORTED_VERSION)
        # releases across both channels, newest first.
        result = []
        try:
            for r in Model._fetchGithubReleases():
                version = r.get("name")
                tag = r.get("tag_name")
                if not isinstance(version, str) or not isinstance(tag, str):
                    continue
                if not Model._isVersionSupported(version):
                    continue
                result.append(ReleaseInfo(
                    tag=tag,
                    version=version,
                    is_prerelease=bool(r.get("prerelease", False)),
                    published_at=str(r.get("published_at", "")),
                ))
        except Exception:
            errorLogging()
        return result

    @staticmethod
    def _downloadSetup() -> bool:
        # try to download at most 5 times
        program_name = "VRCT_setup.exe"
        current_directory = config.PATH_LOCAL
        dest_path = os_path.join(current_directory, program_name)
        # minimum plausible size for a real NSIS installer; guards against
        # saving/executing a short HTML error page as the installer
        min_valid_size = 1024 * 1024
        for _ in range(5):
            try:
                res = requests_get(config.SETUP_DOWNLOAD_URL, stream=True, timeout=_HTTP_TIMEOUT)
                res.raise_for_status()
                downloaded_size = 0
                with open(dest_path, 'wb') as file:
                    for chunk in res.iter_content(chunk_size=1024*5):
                        file.write(chunk)
                        downloaded_size += len(chunk)
                if downloaded_size < min_valid_size:
                    raise ValueError(f"Downloaded setup file is too small ({downloaded_size} bytes); likely not a valid installer")
                return True
            except Exception:
                errorLogging()
                try:
                    if os_path.exists(dest_path):
                        os_remove(dest_path)
                except Exception:
                    errorLogging()
        return False

    @staticmethod
    def updateSoftware(target_version: Optional[str] = None):
        if target_version is not None and not Model._isVersionSupported(target_version):
            return
        if Model._downloadSetup() is False:
            return
        # run the NSIS setup wizard, preselecting the CPU edition; pin to
        # target_version when the user picked a specific release to install;
        # carry over the current UI language so the installer chrome and the
        # custom "UI Language" page start on the user's chosen language;
        # carry over the current release channel so the installer's channel
        # page defaults to what the user already has selected in VRCT.
        args = ["VRCT_setup.exe", "/EDITION=cpu", f"/UILANG={config.UI_LANGUAGE}", f"/CHANNEL={config.SELECTED_RELEASE_CHANNEL}"]
        if target_version:
            args.append(f"/VERSION={target_version}")
        Popen(args, cwd=config.PATH_LOCAL)
        Model._quitApp()

    @staticmethod
    def updateCudaSoftware(target_version: Optional[str] = None):
        if target_version is not None and not Model._isVersionSupported(target_version):
            return
        if Model._downloadSetup() is False:
            return
        # run the NSIS setup wizard, preselecting the GPU edition; pin to
        # target_version when the user picked a specific release to install;
        # carry over the current UI language so the installer chrome and the
        # custom "UI Language" page start on the user's chosen language;
        # carry over the current release channel so the installer's channel
        # page defaults to what the user already has selected in VRCT.
        args = ["VRCT_setup.exe", "/EDITION=gpu", f"/UILANG={config.UI_LANGUAGE}", f"/CHANNEL={config.SELECTED_RELEASE_CHANNEL}"]
        if target_version:
            args.append(f"/VERSION={target_version}")
        Popen(args, cwd=config.PATH_LOCAL)
        Model._quitApp()

    @staticmethod
    def _quitApp():
        # The setup wizard's own running-process check can only kill VRCT
        # silently or prompt the user for it; quit proactively here so the
        # app always closes as soon as the wizard has been launched, whether
        # this was a version update or a CPU/GPU switch.
        try:
            psutil_Process(os_getppid()).terminate()
        except Exception:
            errorLogging()
        finally:
            os_exit(0)

    def getListMicHost(self):
        self.ensure_initialized()
        try:
            dm = device_manager.getMicDevices()
            result = [host for host in dm.keys()]
        except Exception:
            errorLogging()
            result = []
        return result

    def getMicDefaultDevice(self):
        self.ensure_initialized()
        try:
            dm = device_manager.getMicDevices()
            result = dm.get(config.SELECTED_MIC_HOST, [{"name": "NoDevice"}])[0]["name"]
        except Exception:
            errorLogging()
            result = "NoDevice"
        return result

    def getListMicDevice(self):
        self.ensure_initialized()
        try:
            dm = device_manager.getMicDevices()
            result = [device["name"] for device in dm.get(config.SELECTED_MIC_HOST, [{"name": "NoDevice"}])]
        except Exception:
            errorLogging()
            result = ["NoDevice"]
        return result

    def getListSpeakerDevice(self):
        self.ensure_initialized()
        try:
            sd = device_manager.getSpeakerDevices()
            result = [device["name"] for device in sd]
        except Exception:
            errorLogging()
            result = ["NoDevice"]
        return result

    def startMicTranscript(self, fnc):
        self.ensure_initialized()
        self._mic_session.transcript_fnc = fnc
        self._mic_session.reconfigure(transcript=True)
        if "transcript" in self._mic_session.features:
            self.changeMicTranscriptStatus()

    def resumeMicTranscript(self):
        self.ensure_initialized()
        self._mic_session.resume()

    def pauseMicTranscript(self):
        self.ensure_initialized()
        self._mic_session.pause()

    # VRAM 不足エラーを検出するメソッドを追加
    def detectVRAMError(self, error):
        error_str = str(error)
        if isinstance(error, ValueError) and len(error.args) > 0 and error.args[0] == "VRAM_OUT_OF_MEMORY":
            return True, error.args[1] if len(error.args) > 1 else "VRAM out of memory"
        if "CUDA out of memory" in error_str or "CUBLAS_STATUS_ALLOC_FAILED" in error_str:
            return True, error_str
        return False, None

    def changeMicTranscriptStatus(self):
        if config.VRC_MIC_MUTE_SYNC is True:
            match self.mic_mute_status:
                case True:
                    self.pauseMicTranscript()
                case False:
                    self.resumeMicTranscript()
                case None:
                    # mute selfの状態が不明な場合は一時停止しない
                    self.resumeMicTranscript()
                case _:
                    pass
        else:
            self.resumeMicTranscript()

    def stopMicTranscript(self):
        self.ensure_initialized()
        self._mic_session.reconfigure(transcript=False)

    def startCheckMicEnergy(self, fnc:Optional[Callable[[float], None]]=None) -> None:
        self.ensure_initialized()
        # fnc may be None or a callable. Use cast after checking for None to satisfy type checker.
        if fnc is not None:
            self._mic_session.energy_fnc = cast(Callable[[float], None], fnc)
        self._mic_session.reconfigure(energy=True)

    def stopCheckMicEnergy(self):
        self.ensure_initialized()
        self._mic_session.reconfigure(energy=False)

    def startSpeakerTranscript(self, fnc:Optional[Callable[[dict], None]]=None) -> None:
        self.ensure_initialized()
        self._speaker_session.transcript_fnc = fnc
        self._speaker_session.reconfigure(transcript=True)

    def stopSpeakerTranscript(self):
        self.ensure_initialized()
        self._speaker_session.reconfigure(transcript=False)

    def startCheckSpeakerEnergy(self, fnc:Optional[Callable[[float], None]]=None) -> None:
        self.ensure_initialized()
        # Accept None as default and assign safely with cast after None-check
        if fnc is not None:
            self._speaker_session.energy_fnc = cast(Callable[[float], None], fnc)
        self._speaker_session.reconfigure(energy=True)

    def stopCheckSpeakerEnergy(self):
        self.ensure_initialized()
        self._speaker_session.reconfigure(energy=False)

    def reconfigureMicDevice(self, device: Optional[dict] = None) -> None:
        """稼働中の Mic Session を新デバイスに差し替える。

        features (transcript/energy) は現状維持。device が None の場合は
        config (SELECTED_MIC_HOST/DEVICE) から解決する。Session 内部で
        差分検知するため、同一デバイスなら no-op になる。

        Auto 追跡中は device_manager 側の ActiveEndpointTracker が 250ms
        周期で COM ポーリングしており、Recorder の open/close と並行実行
        されると WASAPI がデッドロックする (実測確認済み)。reconfigure の
        前後で tracker を pause/resume することで並行アクセスを排除する。
        Auto OFF 時は tracker が存在しないので pause/resume は no-op。
        """
        self.ensure_initialized()
        device_manager.pauseMicEndpointTracker()
        try:
            self._mic_session.reconfigure(device=device)
        finally:
            device_manager.resumeMicEndpointTracker()

    def reconfigureSpeakerDevice(self, device: Optional[dict] = None) -> None:
        """稼働中の Speaker Session を新デバイスに差し替える。詳細は
        reconfigureMicDevice のドキュメント参照。"""
        self.ensure_initialized()
        device_manager.pauseSpeakerEndpointTracker()
        try:
            self._speaker_session.reconfigure(device=device)
        finally:
            device_manager.resumeSpeakerEndpointTracker()

    def createOverlayImageSmallLog(self, message:Optional[str], your_language:Optional[str], translation:list, target_language:Optional[dict], transliteration_message:Optional[dict] = None, transliteration_translation:Optional[list] = None) -> object:
        self.ensure_initialized()
        # Normalize target_language dict -> list
        target_language_list = []
        if isinstance(target_language, dict):
            target_language_list = [data["language"] for data in target_language.values() if data.get("enable") is True]

        # 翻訳行ルビ (任意) が指定されていれば渡す。後方互換のため None / 不正型は空リストに。
        if not isinstance(transliteration_message, list):
            transliteration_message = []
        if not isinstance(transliteration_translation, list):
            transliteration_translation = [[] for _ in translation]

        return self.overlay_image.createOverlayImageSmallLog(
            message,
            your_language,
            translation,
            target_language_list,
            transliteration_message=transliteration_message,
            transliteration_translation=transliteration_translation,
        )

    def createOverlayImageSmallMessage(self, message):
        self.ensure_initialized()
        ui_language = config.UI_LANGUAGE
        convert_languages = {
            "en": "Default",
            "jp": "Japanese",
            "ko":"Korean",
            "zh-Hans":"Chinese Simplified",
            "zh-Hant":"Chinese Traditional",
        }
        language = convert_languages.get(ui_language, "Default")
        return self.overlay_image.createOverlayImageSmallLog(message, language)

    def clearOverlayImageSmallLog(self):
        self.ensure_initialized()
        self.overlay.clearImage("small")

    def updateOverlaySmallLog(self, img):
        self.ensure_initialized()
        self.overlay.updateImage(img, "small")

    def updateOverlaySmallLogSettings(self):
        self.ensure_initialized()
        size = "small"

        if (self.overlay.settings[size]["x_pos"] != config.OVERLAY_SMALL_LOG_SETTINGS["x_pos"] or
            self.overlay.settings[size]["y_pos"] != config.OVERLAY_SMALL_LOG_SETTINGS["y_pos"] or
            self.overlay.settings[size]["z_pos"] != config.OVERLAY_SMALL_LOG_SETTINGS["z_pos"] or
            self.overlay.settings[size]["x_rotation"] != config.OVERLAY_SMALL_LOG_SETTINGS["x_rotation"] or
            self.overlay.settings[size]["y_rotation"] != config.OVERLAY_SMALL_LOG_SETTINGS["y_rotation"] or
            self.overlay.settings[size]["z_rotation"] != config.OVERLAY_SMALL_LOG_SETTINGS["z_rotation"] or
            self.overlay.settings[size]["tracker"] != config.OVERLAY_SMALL_LOG_SETTINGS["tracker"]):
            self.overlay.updatePosition(
                config.OVERLAY_SMALL_LOG_SETTINGS["x_pos"],
                config.OVERLAY_SMALL_LOG_SETTINGS["y_pos"],
                config.OVERLAY_SMALL_LOG_SETTINGS["z_pos"],
                config.OVERLAY_SMALL_LOG_SETTINGS["x_rotation"],
                config.OVERLAY_SMALL_LOG_SETTINGS["y_rotation"],
                config.OVERLAY_SMALL_LOG_SETTINGS["z_rotation"],
                config.OVERLAY_SMALL_LOG_SETTINGS["tracker"],
                size,
            )
        if (self.overlay.settings[size]["display_duration"] != config.OVERLAY_SMALL_LOG_SETTINGS["display_duration"]):
            self.overlay.updateDisplayDuration(config.OVERLAY_SMALL_LOG_SETTINGS["display_duration"], size)
        if (self.overlay.settings[size]["fadeout_duration"] != config.OVERLAY_SMALL_LOG_SETTINGS["fadeout_duration"]):
            self.overlay.updateFadeoutDuration(config.OVERLAY_SMALL_LOG_SETTINGS["fadeout_duration"], size)
        if (self.overlay.settings[size]["opacity"] != config.OVERLAY_SMALL_LOG_SETTINGS["opacity"]):
            self.overlay.updateOpacity(config.OVERLAY_SMALL_LOG_SETTINGS["opacity"], size, True)
        if (self.overlay.settings[size]["ui_scaling"] != config.OVERLAY_SMALL_LOG_SETTINGS["ui_scaling"]):
            self.overlay.updateUiScaling(config.OVERLAY_SMALL_LOG_SETTINGS["ui_scaling"], size)

    def createOverlayImageLargeLog(self, message_type:str, message:Optional[str], your_language:Optional[str],  translation:list, target_language:Optional[dict]=None, transliteration_message:Optional[list]=None, transliteration_translation:Optional[list]=None) -> object:
        self.ensure_initialized()
        # normalize target_language dict -> list of language strings
        target_language_list = []
        if isinstance(target_language, dict):
            target_language_list = [data["language"] for data in target_language.values() if data.get("enable") is True]
        return self.overlay_image.createOverlayImageLargeLog(message_type, message, your_language, translation, target_language_list, transliteration_message, transliteration_translation)

    def createOverlayImageLargeMessage(self, message):
        self.ensure_initialized()
        ui_language = config.UI_LANGUAGE
        convert_languages = {
            "en": "Default",
            "jp": "Japanese",
            "ko":"Korean",
            "zh-Hans":"Chinese Simplified",
            "zh-Hant":"Chinese Traditional",
        }
        language = convert_languages.get(ui_language, "Default")
        overlay_image = OverlayImage(config.PATH_LOCAL)

        for _ in range(2):
            overlay_image.createOverlayImageLargeLog("send", message, language)
            overlay_image.createOverlayImageLargeLog("receive", message, language)
        return overlay_image.createOverlayImageLargeLog("send", message, language)

    def clearOverlayImageLargeLog(self):
        self.ensure_initialized()
        self.overlay.clearImage("large")

    def updateOverlayLargeLog(self, img):
        self.ensure_initialized()
        self.overlay.updateImage(img, "large")

    def updateOverlayLargeLogSettings(self):
        self.ensure_initialized()
        size = "large"
        if (self.overlay.settings[size]["x_pos"] != config.OVERLAY_LARGE_LOG_SETTINGS["x_pos"] or
            self.overlay.settings[size]["y_pos"] != config.OVERLAY_LARGE_LOG_SETTINGS["y_pos"] or
            self.overlay.settings[size]["z_pos"] != config.OVERLAY_LARGE_LOG_SETTINGS["z_pos"] or
            self.overlay.settings[size]["x_rotation"] != config.OVERLAY_LARGE_LOG_SETTINGS["x_rotation"] or
            self.overlay.settings[size]["y_rotation"] != config.OVERLAY_LARGE_LOG_SETTINGS["y_rotation"] or
            self.overlay.settings[size]["z_rotation"] != config.OVERLAY_LARGE_LOG_SETTINGS["z_rotation"] or
            self.overlay.settings[size]["tracker"] != config.OVERLAY_LARGE_LOG_SETTINGS["tracker"]):
            self.overlay.updatePosition(
                config.OVERLAY_LARGE_LOG_SETTINGS["x_pos"],
                config.OVERLAY_LARGE_LOG_SETTINGS["y_pos"],
                config.OVERLAY_LARGE_LOG_SETTINGS["z_pos"],
                config.OVERLAY_LARGE_LOG_SETTINGS["x_rotation"],
                config.OVERLAY_LARGE_LOG_SETTINGS["y_rotation"],
                config.OVERLAY_LARGE_LOG_SETTINGS["z_rotation"],
                config.OVERLAY_LARGE_LOG_SETTINGS["tracker"],
                size,
            )
        if (self.overlay.settings[size]["display_duration"] != config.OVERLAY_LARGE_LOG_SETTINGS["display_duration"]):
            self.overlay.updateDisplayDuration(config.OVERLAY_LARGE_LOG_SETTINGS["display_duration"], size)
        if (self.overlay.settings[size]["fadeout_duration"] != config.OVERLAY_LARGE_LOG_SETTINGS["fadeout_duration"]):
            self.overlay.updateFadeoutDuration(config.OVERLAY_LARGE_LOG_SETTINGS["fadeout_duration"], size)
        if (self.overlay.settings[size]["opacity"] != config.OVERLAY_LARGE_LOG_SETTINGS["opacity"]):
            self.overlay.updateOpacity(config.OVERLAY_LARGE_LOG_SETTINGS["opacity"], size, True)
        if (self.overlay.settings[size]["ui_scaling"] != config.OVERLAY_LARGE_LOG_SETTINGS["ui_scaling"]):
            self.overlay.updateUiScaling(config.OVERLAY_LARGE_LOG_SETTINGS["ui_scaling"] * 0.25, size)

    def startOverlay(self):
        self.ensure_initialized()
        self.overlay.startOverlay()

    def shutdownOverlay(self):
        self.ensure_initialized()
        self.overlay.shutdownOverlay()

    def startWatchdog(self):
        self.ensure_initialized()
        self.th_watchdog = threadFnc(self.watchdog.start)
        self.th_watchdog.daemon = True
        self.th_watchdog.start()
        self._armFreezeDump()

    def feedWatchdog(self):
        self.ensure_initialized()
        self.watchdog.feed()
        self._armFreezeDump()

    def _armFreezeDump(self):
        """次の feed が freeze 判定になるより前に、全スレッドスタックを
        freeze_trace.log へ書き出すタイマーを (再) 武装する。呼ぶたびに
        以前のタイマーは自動的に上書きされる (faulthandler の仕様)。
        """
        timeout = self.watchdog.interval + _FREEZE_DUMP_MARGIN_SEC
        try:
            faulthandler.dump_traceback_later(
                timeout, repeat=False, file=_freeze_trace_file, exit=False
            )
        except Exception:
            errorLogging()

    def setWatchdogCallback(self, callback):
        self.ensure_initialized()
        self.watchdog.setCallback(callback)

    def stopWatchdog(self):
        self.ensure_initialized()
        if isinstance(self.th_watchdog, threadFnc):
            self.th_watchdog.stop()
            self.th_watchdog.join()
            self.th_watchdog = None
        try:
            faulthandler.cancel_dump_traceback_later()
        except Exception:
            errorLogging()

    def message_handler(self, websocket, message):
        """WebSocketメッセージ受信時の処理"""
        pass

    def startWebSocketServer(self, host, port):
        """WebSocketサーバーを起動し、別スレッドで実行する"""
        self.ensure_initialized()
        if self.websocket_server_alive is True:
            # サーバーが既に起動している場合は何もしない
            return

        self.websocket_server_loop = True
        self.websocket_server_alive = False  # 初期状態を明示

        async def WebSocketServerMain():
            try:
                self.websocket_server = WebSocketServer(
                    host=host,
                    port=port,
                    token=config.WEBSOCKET_AUTH_TOKEN,
                )
                self.websocket_server.set_message_handler(self.message_handler)
                self.websocket_server.start()
                self.websocket_server_alive = True

                # イベントループが終了するまで待機
                while self.websocket_server_loop:
                    # self.websocket_server.send("Server is running...")
                    await asyncio.sleep(0.5)  # 応答性向上のため間隔短縮

            except Exception:
                errorLogging()
                # 具体的なエラー内容をログに残す場合
                # self.logger.error(f"WebSocket server error: {str(e)}")
            finally:
                # 確実にサーバーを停止
                if hasattr(self, 'websocket_server') and self.websocket_server:
                    self.websocket_server.stop()
                self.websocket_server_alive = False

        self.th_websocket_server = Thread(target=lambda: asyncio.run(WebSocketServerMain()))
        self.th_websocket_server.daemon = True
        self.th_websocket_server.start()

    def stopWebSocketServer(self):
        """WebSocketサーバーを停止する"""
        self.ensure_initialized()
        if not hasattr(self, 'th_websocket_server') or self.th_websocket_server is None:
            return

        self.websocket_server_loop = False

        try:
            # 一定時間待機してからタイムアウト
            self.th_websocket_server.join(timeout=2.0)

            if self.th_websocket_server.is_alive():
                # タイムアウト後もスレッドが生きている場合の処理
                self.logger.warning("WebSocket server thread did not terminate properly")
        except Exception:
            errorLogging()
        finally:
            self.th_websocket_server = None
            self.websocket_server = None
            self.websocket_server_alive = False

    def checkWebSocketServerAlive(self):
        """WebSocketサーバーの稼働状態を確認する"""
        self.ensure_initialized()
        return self.websocket_server_alive

    def startObsBrowserSourceServer(self, host: str, port: int) -> None:
        """Start the local HTTP server used as an OBS Browser Source."""
        self.ensure_initialized()

        try:
            if (
                isinstance(self.obs_browser_source_server, ObsBrowserSourceServer)
                and self.obs_browser_source_server.is_running
                and self.obs_browser_source_server.host == host
                and self.obs_browser_source_server.port == port
            ):
                return
        except Exception:
            # If anything goes wrong while checking state, restart.
            pass

        self.stopObsBrowserSourceServer()

        try:
            self.obs_browser_source_server = ObsBrowserSourceServer(host=host, port=port, ws_token=config.WEBSOCKET_AUTH_TOKEN)
            self.obs_browser_source_server.start()
        except Exception:
            errorLogging()
            self.obs_browser_source_server = None

    def stopObsBrowserSourceServer(self) -> None:
        self.ensure_initialized()
        try:
            if isinstance(self.obs_browser_source_server, ObsBrowserSourceServer):
                self.obs_browser_source_server.stop()
        except Exception:
            errorLogging()
        finally:
            self.obs_browser_source_server = None

    def checkObsBrowserSourceServerAlive(self) -> bool:
        self.ensure_initialized()
        try:
            return (
                isinstance(self.obs_browser_source_server, ObsBrowserSourceServer)
                and self.obs_browser_source_server.is_running
            )
        except Exception:
            errorLogging()
            return False

    def websocketSendMessage(self, message_dict:dict):
        """
        WebSocketサーバーから全クライアントにメッセージを送信する
        :param message_dict: 送信するメッセージの辞書
        :return: 送信成功したかどうか
        """
        self.ensure_initialized()
        if not self.websocket_server_alive or not self.websocket_server:
            return False
        try:
            message_json = json.dumps(message_dict)
            return self.websocket_server.send(message_json)
        except Exception:
            errorLogging()
            return False

    def setCopyToClipboardAndPasteFromClipboard(self, text:str) -> bool:
        self.ensure_initialized()
        try:
            if isinstance(self.clipboard, Clipboard):
                self.clipboard.copy_and_paste(text)
                return True
            else:
                return False
        except Exception:
            errorLogging()
            return False

    def telemetryInit(self, enabled: bool, app_version: str, storage_path: str = None):
        """Model 内で Telemetry を初期化"""
        if storage_path is None:
            try:
                storage_path = os_path.join(config.PATH_LOCAL, "telemetry_state.json")
            except Exception:
                storage_path = None
        self.telemetry.init(enabled=enabled, app_version=app_version, storage_path=storage_path)

    def telemetryShutdown(self):
        """Model cleanup on application shutdown."""
        if hasattr(self, "telemetry") and self.telemetry:
            self.telemetry.shutdown()

    def telemetryTrackError(self, error_code: str):
        """エラーコードのテレメトリ送信 (Model ラッパー)。日次デデュープ済み。"""
        if hasattr(self, "telemetry") and self.telemetry:
            self.telemetry.track_error(error_code)

    def telemetryTouchActivity(self):
        """テレメトリアクティビティ更新 (Model ラッパー)"""
        if hasattr(self, "telemetry") and self.telemetry:
            self.telemetry.touch_activity()

model = Model()

# エラー生成時にテレメトリへ通知するフックを登録する（日次デデュープ済み）
from errors import register_error_report_hook  # noqa: E402
register_error_report_hook(model.telemetryTrackError)
