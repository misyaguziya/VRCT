from typing import Callable, Any, List, Optional
from subprocess import Popen
from threading import Thread, Lock
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
import copy
import functools
import re
import time
from device_manager import device_manager
from config import config, ConfigValidationError
from model import model
from utils import removeLog, printLog, errorLogging, isConnectedNetwork, isValidIpAddress, isWildcardBindAddress, isAvailableWebSocketServer
from errors import ErrorCode, VRCTError
from models.transcription.transcription_openai_compatible import TRANSCRIPTION_MODEL_KEYWORDS, TRANSCRIPTION_API_ENGINES
from models.translation.translation_providers import TRANSLATION_PROVIDER_REGISTRY, CONNECTION_PROVIDER_REGISTRY
from models.message_pipeline import MessageDirectionSpec, MIC_MESSAGE_SPEC, SPEAKER_MESSAGE_SPEC, CHAT_MESSAGE_SPEC

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

# モデルダウンロード進捗の間引きしきい値。translation_utils.downloadFile /
# transcription_whisper.downloadFile は 2MB チャンクごとに progressBar を
# 呼ぶため、~2GB の重みで 900+ 回の logging バーストが発生する。
# CTranslate2 と Whisper が同時にダウンロードされると process.log の
# ハンドラロック競合で feedWatchdog が 35s 遅延するのを freeze_trace.log で
# 2026-08-20 に観測した。前回報告から MIN_DELTA 以上進んだ、または
# MIN_INTERVAL_SEC 以上経過した場合のみ forward する (0% / 100% は必ず送る)。
_DOWNLOAD_PROGRESS_MIN_DELTA = 0.01
_DOWNLOAD_PROGRESS_MIN_INTERVAL_SEC = 0.5

# shutdown() が mic/speaker_lifecycle_lock を待つ上限。model.py の
# TRANSCRIPT_STOP_JOIN_TIMEOUT (15s) + PyAudio open の _MIC_OPEN_TIMEOUT_SEC
# (8s) など、ロック保持中に自然完了しうる最長の単発処理より余裕を持たせつつ、
# 万一ロックが本当に返ってこない場合でも終了処理自体を無期限に止めない。
_SHUTDOWN_LIFECYCLE_LOCK_TIMEOUT_SEC = 20.0

# shutdown() が OSC/WebSocket/OBS Browser Source/Overlay の各停止関数を
# 待つ上限(フェーズ4項目30)。いずれも自前でタイムアウト付きjoinを持つ設計
# (OSCは serve_forever(0.5) 化により概ね0.5秒以内、WebSocket/OBSは
# join(timeout=2.0)) だが、唯一 Overlay.shutdownOverlay() の
# thread_overlay.join() だけは現状無タイムアウトのまま(フェーズ4項目31で
# 対応予定)。ここで一律に境界を設けることで、万一そのいずれかが想定外に
# 詰まっても shutdown() 自体は無期限にハングしない(_stopLockedForShutdownと
# 同じ考え方)。タイムアウトした場合、対象スレッドはdaemonのまま走らせて
# 諦める(=リソースはプロセス終了が最終的に片付ける)。
_SHUTDOWN_SERVICE_STOP_TIMEOUT_SEC = 5.0

# TRANSLATION_PROVIDER_REGISTRY (フェーズ3項目17) 登録エンジンの
# 「認証/モデル一覧取得/モデル変更/クライアント更新」を model.py の
# どのメソッド"名"に委譲するかの対応表。エンジンを1つレジストリに追加する際、
# ここに4行足すだけで Controller._setTranslationEngineAuthKey 等の
# 共通実装から使えるようになる (model.py 自体の各メソッドはこれまで通り
# 個別に存在する — Translator ファサード層 (layer 1) は
# authenticationRegistryAuthKey 等で既にレジストリ駆動になっているが、
# model.py (layer 2) は薄い1行委譲のみで書き換える理由に乏しいため、
# この対応表で拾う形にした)。
#
# 値をメソッド"名" (str) にしているのは、既存テストが
# `@patch("controller.model")` で model シングルトンを丸ごとモックに
# 差し替える方式に依存しているため。呼び出し時に `getattr(model, name)`
# で毎回引き直すことで、モジュールロード時に実体の bound method を
# キャッシュしてしまい patch が効かなくなる事故を避ける。
_ENGINE_MODEL_BINDINGS = {
    "Plamo_API": {
        "authenticate": "authenticationTranslatorPlamoAuthKey",
        "get_model_list": "getTranslatorPlamoModelList",
        "set_model": "setTranslatorPlamoModel",
        "update_client": "updateTranslatorPlamoClient",
    },
    "Gemini_API": {
        "authenticate": "authenticationTranslatorGeminiAuthKey",
        "get_model_list": "getTranslatorGeminiModelList",
        "set_model": "setTranslatorGeminiModel",
        "update_client": "updateTranslatorGeminiClient",
    },
    "OpenAI_API": {
        "authenticate": "authenticationTranslatorOpenAIAuthKey",
        "get_model_list": "getTranslatorOpenAIModelList",
        "set_model": "setTranslatorOpenAIModel",
        "update_client": "updateTranslatorOpenAIClient",
    },
    "Groq_API": {
        "authenticate": "authenticationTranslatorGroqAuthKey",
        "get_model_list": "getTranslatorGroqModelList",
        "set_model": "setTranslatorGroqModel",
        "update_client": "updateTranslatorGroqClient",
    },
    "OpenRouter_API": {
        "authenticate": "authenticationTranslatorOpenRouterAuthKey",
        "get_model_list": "getTranslatorOpenRouterModelList",
        "set_model": "setTranslatorOpenRouterModel",
        "update_client": "updateTranslatorOpenRouterClient",
    },
    # CONNECTION_PROVIDER_REGISTRY (疎通確認型) 用。"authenticate" は
    # 「接続を確認する」呼び出しに読み替える (LMStudioはbase_url必須、
    # Ollamaは引数なし — 呼び出し時の connect_kwargs で吸収する)。
    "LMStudio": {
        "authenticate": "authenticationTranslatorLMStudio",
        "get_model_list": "getTranslatorLMStudioModelList",
        "set_model": "setTranslatorLMStudioModel",
        "update_client": "updateTranslatorLMStudioClient",
    },
    "Ollama": {
        "authenticate": "authenticationTranslatorOllama",
        "get_model_list": "getTranslatorOllamaModelList",
        "set_model": "setTranslatorOllamaModel",
        "update_client": "updateTranslatorOllamaClient",
    },
}


def _configValidationErrorResponse(error_code: ErrorCode):
    """設定値のディスクリプタ (config.py の ManagedProperty/ValidatedProperty)
    が拒否した場合に `ConfigValidationError` を捕まえ、`VRCTError` の
    エラーレスポンスへ変換するデコレータ (フェーズ3項目24)。

    対象は「`config.X = data` して結果を返すだけ」の単純なエンドポイント
    (例: `setUiLanguage`) — これまでは不正な値を渡されても、ディスクリプタが
    サイレントに値を無視し、変化していない旧値を 200 (成功) で返していた
    (`setUiLanguage(bad_value)` が「成功したが何も変わっていない」レスポンスに
    なる、という誤った契約)。デコレータを付けるだけで、関数本体は一切
    書き換えずに正しいエラー契約に直せる。

    副作用を伴う (例: `self.run(...)` で他のpushを行う) エンドポイントには
    使わないこと — 拒否時、副作用がどこまで実行された状態で例外に
    なったかをこのデコレータは関知しない。
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ConfigValidationError as e:
                return VRCTError.create_error_response(error_code, data=e.value)
        return wrapper
    return decorator


def _shouldEmitDownloadProgress(handler: Any, progress: float) -> bool:
    """DownloadCTranslate2 / DownloadWhisper の progressBar 用スロットル。

    handler は `_last_progress: float` と `_last_time: float` 属性を持つ
    インスタンス。100% 到達時は必ず True を返す (完了通知が抜けないよう)。
    """
    now = time.monotonic()
    if (
        progress >= 1.0
        or (progress - handler._last_progress) >= _DOWNLOAD_PROGRESS_MIN_DELTA
        or (now - handler._last_time) >= _DOWNLOAD_PROGRESS_MIN_INTERVAL_SEC
    ):
        handler._last_progress = progress
        handler._last_time = now
        return True
    return False


# config.py の値をそのまま返すだけの単純なgetterエンドポイント
# (フェーズ3項目23)。エンドポイントメソッド名 -> config属性名の対応表。
# 実際のメソッド生成・Controllerクラスへの登録は
# _registerSimpleConfigGetters() 参照 (ファイル末尾)。
_SIMPLE_CONFIG_GETTERS = {
    "getVersion": "VERSION",
    "getComputeMode": "COMPUTE_MODE",
    "getComputeDeviceList": "SELECTABLE_COMPUTE_DEVICE_LIST",
    "getSelectedTranslationComputeDevice": "SELECTED_TRANSLATION_COMPUTE_DEVICE",
    "getSelectableCtranslate2WeightTypeDict": "SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT",
    "getSelectedTranscriptionComputeDevice": "SELECTED_TRANSCRIPTION_COMPUTE_DEVICE",
    "getSelectedTabNo": "SELECTED_TAB_NO",
    "getSelectedTranslationEngines": "SELECTED_TRANSLATION_ENGINES",
    "getSelectedYourLanguages": "SELECTED_YOUR_LANGUAGES",
    "getSelectedTargetLanguages": "SELECTED_TARGET_LANGUAGES",
    "getSelectedTranscriptionEngine": "SELECTED_TRANSCRIPTION_ENGINE",
    "getGroqWhisperModelList": "SELECTABLE_GROQ_WHISPER_MODEL_LIST",
    "getGroqWhisperModel": "SELECTED_GROQ_WHISPER_MODEL",
    "getOpenAIWhisperModelList": "SELECTABLE_OPENAI_WHISPER_MODEL_LIST",
    "getOpenAIWhisperModel": "SELECTED_OPENAI_WHISPER_MODEL",
    "getCustomWhisperURL": "TRANSCRIPTION_CUSTOM_URL",
    "getCustomWhisperModelList": "SELECTABLE_CUSTOM_WHISPER_MODEL_LIST",
    "getCustomWhisperModel": "SELECTED_CUSTOM_WHISPER_MODEL",
    "getDeepgramModelList": "SELECTABLE_DEEPGRAM_MODEL_LIST",
    "getDeepgramModel": "SELECTED_DEEPGRAM_MODEL",
    "getSelectableReleaseChannels": "SELECTABLE_RELEASE_CHANNEL_LIST",
    "getSelectedReleaseChannel": "SELECTED_RELEASE_CHANNEL",
    "getConvertMessageToRomaji": "CONVERT_MESSAGE_TO_ROMAJI",
    "getConvertMessageToHiragana": "CONVERT_MESSAGE_TO_HIRAGANA",
    "getMainWindowSidebarCompactMode": "MAIN_WINDOW_SIDEBAR_COMPACT_MODE",
    "getTransparency": "TRANSPARENCY",
    "getUiScaling": "UI_SCALING",
    "getTextboxUiScaling": "TEXTBOX_UI_SCALING",
    "getMessageBoxRatio": "MESSAGE_BOX_RATIO",
    "getSendMessageButtonType": "SEND_MESSAGE_BUTTON_TYPE",
    "getShowResendButton": "SHOW_RESEND_BUTTON",
    "getFontFamily": "FONT_FAMILY",
    "getUiLanguage": "UI_LANGUAGE",
    "getMainWindowGeometry": "MAIN_WINDOW_GEOMETRY",
    "getAutoMicSelect": "AUTO_MIC_SELECT",
    "getSelectedMicHost": "SELECTED_MIC_HOST",
    "getSelectedMicDevice": "SELECTED_MIC_DEVICE",
    "getMicThreshold": "MIC_THRESHOLD",
    "getMicAutomaticThreshold": "MIC_AUTOMATIC_THRESHOLD",
    "getMicRecordTimeout": "MIC_RECORD_TIMEOUT",
    "getMicPhraseTimeout": "MIC_PHRASE_TIMEOUT",
    "getMicMaxPhrases": "MIC_MAX_PHRASES",
    "getMicWordFilter": "MIC_WORD_FILTER",
    "getMicAvgLogprob": "MIC_AVG_LOGPROB",
    "getMicNoSpeechProb": "MIC_NO_SPEECH_PROB",
    "getAutoSpeakerSelect": "AUTO_SPEAKER_SELECT",
    "getSelectedSpeakerDevice": "SELECTED_SPEAKER_DEVICE",
    "getSpeakerThreshold": "SPEAKER_THRESHOLD",
    "getSpeakerAutomaticThreshold": "SPEAKER_AUTOMATIC_THRESHOLD",
    "getSpeakerRecordTimeout": "SPEAKER_RECORD_TIMEOUT",
    "getSpeakerPhraseTimeout": "SPEAKER_PHRASE_TIMEOUT",
    "getSpeakerMaxPhrases": "SPEAKER_MAX_PHRASES",
    "getHotkeys": "HOTKEYS",
    "getPluginsStatus": "PLUGINS_STATUS",
    "getSpeakerAvgLogprob": "SPEAKER_AVG_LOGPROB",
    "getSpeakerNoSpeechProb": "SPEAKER_NO_SPEECH_PROB",
    "getOscIpAddress": "OSC_IP_ADDRESS",
    "getOscPort": "OSC_PORT",
    "getNotificationVrcSfx": "NOTIFICATION_VRC_SFX",
    "getTranslatorLMStudioURL": "LMSTUDIO_URL",
    "getOpenAICompatibleURL": "OPENAI_COMPATIBLE_URL",
    "getOpenAICompatibleModelList": "SELECTABLE_OPENAI_COMPATIBLE_MODEL_LIST",
    "getOpenAICompatibleModel": "SELECTED_OPENAI_COMPATIBLE_MODEL",
    "getCtranslate2WeightType": "CTRANSLATE2_WEIGHT_TYPE",
    "getSelectedTranslationComputeType": "SELECTED_TRANSLATION_COMPUTE_TYPE",
    "getWhisperWeightType": "WHISPER_WEIGHT_TYPE",
    "getSelectedTranscriptionComputeType": "SELECTED_TRANSCRIPTION_COMPUTE_TYPE",
    "getSendMessageFormatParts": "SEND_MESSAGE_FORMAT_PARTS",
    "getReceivedMessageFormatParts": "RECEIVED_MESSAGE_FORMAT_PARTS",
    "getAutoClearMessageBox": "AUTO_CLEAR_MESSAGE_BOX",
    "getSendOnlyTranslatedMessages": "SEND_ONLY_TRANSLATED_MESSAGES",
    "getOverlaySmallLog": "OVERLAY_SMALL_LOG",
    "getOverlaySmallLogSettings": "OVERLAY_SMALL_LOG_SETTINGS",
    "getOverlayLargeLog": "OVERLAY_LARGE_LOG",
    "getOverlayLargeLogSettings": "OVERLAY_LARGE_LOG_SETTINGS",
    "getOverlayShowOnlyTranslatedMessages": "OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES",
    "getSendMessageToVrc": "SEND_MESSAGE_TO_VRC",
    "getSendReceivedMessageToVrc": "SEND_RECEIVED_MESSAGE_TO_VRC",
    "getLoggerFeature": "LOGGER_FEATURE",
    "getVrcMicMuteSync": "VRC_MIC_MUTE_SYNC",
    "getTelemetry": "ENABLE_TELEMETRY",
    "getWebSocketHost": "WEBSOCKET_HOST",
    "getWebSocketPort": "WEBSOCKET_PORT",
    "getWebSocketServer": "WEBSOCKET_SERVER",
    "getObsBrowserSource": "OBS_BROWSER_SOURCE",
    "getObsBrowserSourcePort": "OBS_BROWSER_SOURCE_PORT",
    "getObsBrowserSourceMaxMessages": "OBS_BROWSER_SOURCE_MAX_MESSAGES",
    "getObsBrowserSourceDisplayDuration": "OBS_BROWSER_SOURCE_DISPLAY_DURATION",
    "getObsBrowserSourceFadeoutDuration": "OBS_BROWSER_SOURCE_FADEOUT_DURATION",
    "getObsBrowserSourceFontSize": "OBS_BROWSER_SOURCE_FONT_SIZE",
    "getObsBrowserSourceFontColor": "OBS_BROWSER_SOURCE_FONT_COLOR",
    "getObsBrowserSourceFontOutlineThickness": "OBS_BROWSER_SOURCE_FONT_OUTLINE_THICKNESS",
    "getObsBrowserSourceFontOutlineColor": "OBS_BROWSER_SOURCE_FONT_OUTLINE_COLOR",
    "getClipboard": "ENABLE_CLIPBOARD",
}

class Controller:
    def __init__(self, config_override=None, model_override=None) -> None:
        """
        `config_override`/`model_override` はデフォルト引数注入
        (フェーズ3項目22)。既定 (未指定) では、このモジュールが `from
        config import config` / `from model import model` した
        シングルトンをその場で (呼び出し時に) 参照するため、既存の全呼び出し
        (`Controller()`) は無変更で動き、`@patch("controller.model")` の
        ようなモジュール属性差し替えにも追従する。

        NOTE: `def __init__(self, config=config, model=model)` のように
        引数名をモジュールレベル名と揃えて既定値にする書き方は避けた —
        デフォルト値は関数定義時 (＝モジュール import 時) に1回だけ評価
        されるため、後から `@patch("controller.model")` で
        `controller.model` を差し替えても、既に固定された既定値には反映
        されない (実際にこれで既存テストを壊しかけた)。`config`/`model` を
        関数本体側で毎回参照する今の形なら、呼び出し時点の最新の値を拾える。

        テストや将来の DI 移行 (項目23) のために差し替えられるよう
        `self._config`/`self._model` として保持するが、これはコンストラクタ
        自体の足場に留まる: このクラスの残り数千行は引き続き裸のモジュール
        レベル `config`/`model` を直接参照しており、今回それらを
        `self._config`/`self._model` 経由に書き換えることはしていない
        (影響範囲が大きすぎるため項目23の対象)。現時点で `self._model` を
        実際に使っているのは `_bootstrapModel()` (下記) のみ。
        """
        self._config = config_override if config_override is not None else config
        self._model = model_override if model_override is not None else model
        # typed attributes to satisfy static type checkers
        self.init_mapping: dict = {}
        self.run_mapping: dict = {}
        # initialize with a no-op callable so callers can safely call self.run
        def _noop_run(status: int, endpoint: str, payload: Any = None) -> None:
            return None
        self.run: Callable[[int, str, Any], None] = _noop_run
        # マイク/スピーカーそれぞれの文字起こし・エナジー計測の start/stop を
        # 直列化するロック。mic/speaker で分離しているのは、片方の重い
        # open/close 中にもう片方が待たされないようにするため。
        # 非再入の Lock を使う。VRAM エラー発生時に start*Message の except節
        # が同一スレッド上で停止処理を行う必要があるが、そこでは
        # _stopTranscriptionSendMessageLocked のようなロック不要の内部版を
        # 呼ぶことで再入を避けている (公開の stop*Message は自前でロックを
        # 取るため、start*Message の中から呼ぶとデッドロックする)。
        self.mic_lifecycle_lock: Lock = Lock()
        self.speaker_lifecycle_lock: Lock = Lock()

    def _is_overlay_available(self) -> bool:
        """Safe check whether overlay is present and initialized.

        This avoids AttributeError when `model` was not fully initialized.
        """
        try:
            overlay = getattr(model, "overlay", None)
            return overlay is not None and getattr(overlay, "initialized", False)
        except Exception:
            errorLogging()
            return False

    def setInitMapping(self, init_mapping:dict) -> None:
        self.init_mapping = init_mapping

    def setRunMapping(self, run_mapping:dict) -> None:
        self.run_mapping = run_mapping

    def setRun(self, run:Callable[[int, str, Any], None]) -> None:
        self.run = run

    def _stopLockedForShutdown(self, lock: Lock, stop_fn: Callable[[], None], label: str) -> None:
        """shutdown() 専用: lock を取得してから stop_fn() を呼ぶ。

        通常経路 (stopTranscriptionSendMessage 等) と同じロックを使うが、
        shutdown() は他の全ての mic/speaker_lifecycle_lock 保持経路
        (start/stop 系, AudioLifecycleWorker 経由のデバイス切替等) と
        直列化されないまま model.* を直接叩いていたため、_stop() と
        _start() が同一 Session に対して並行実行され得た。取得を
        acquire(timeout=...) にしているのは、終了処理自体がロック待ちで
        無期限にハングしないようにするため (ロックが返らない場合は
        ログを残してこの停止だけスキップし、後続の停止処理は続行する)。
        """
        acquired = lock.acquire(timeout=_SHUTDOWN_LIFECYCLE_LOCK_TIMEOUT_SEC)
        if not acquired:
            printLog(f"shutdown: {label} のロック取得が {_SHUTDOWN_LIFECYCLE_LOCK_TIMEOUT_SEC}s でタイムアウトしたため、この停止処理をスキップします")
            return
        try:
            stop_fn()
        except Exception:
            errorLogging()
        finally:
            lock.release()

    @staticmethod
    def _stopWorkerForShutdown(worker) -> None:
        """shutdown() 専用: AudioLifecycleWorker.stop() の例外を握りつぶす。

        mic/speaker で独立したワーカーなので、shutdown() 側では
        ThreadPoolExecutor で並行に stop() することで、直列に呼んだ場合の
        最大2倍の待ち時間 (各最大 _SHUTDOWN_LIFECYCLE_LOCK_TIMEOUT_SEC 秒)
        を避ける (コードレビュー指摘)。
        """
        try:
            worker.stop(timeout=_SHUTDOWN_LIFECYCLE_LOCK_TIMEOUT_SEC)
        except Exception:
            errorLogging()

    @staticmethod
    def _stopServiceForShutdown(stop_fn: Callable[[], None], label: str) -> None:
        """shutdown() 専用: stop_fn() を最大 _SHUTDOWN_SERVICE_STOP_TIMEOUT_SEC
        秒の別スレッドで実行する。OSC/WebSocket/OBS Browser Source/Overlayの
        各停止処理を、詰まっても shutdown() 自体を道連れにしない形で呼ぶための
        共通ヘルパー(フェーズ4項目30)。
        """
        def _run() -> None:
            try:
                stop_fn()
            except Exception:
                errorLogging()

        thread = Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=_SHUTDOWN_SERVICE_STOP_TIMEOUT_SEC)
        if thread.is_alive():
            printLog(
                f"shutdown: {label} の停止が {_SHUTDOWN_SERVICE_STOP_TIMEOUT_SEC}s "
                "でタイムアウトしました(プロセス終了時に破棄されます)"
            )

    def shutdown(self, *args, **kwargs) -> dict:
        """Shutdown controller and model (including telemetry).

        Returns:
            dict with status 200 and result True on success.
        """
        # デバイス監視・録音系スレッドを明示的に停止する。これを怠ると
        # PyAudio/WASAPI ストリームが open されたままプロセスが終了し、
        # デバイスハンドルがリークしたり、次回起動時の初期化に影響し得る。
        # 各停止は個別に例外を握りつぶし、1つの失敗が他の停止処理を
        # ブロックしないようにする。
        #
        # Auto Mic/Speaker Select の ActiveEndpointTracker は
        # setMicAutoActive(False)/setSpeakerAutoActive(False) を呼ばない
        # 限り止まらない (stopMonitoring は別スレッドの監視ループのみを
        # 止める)。ここで止めずに終了すると、tracker が COM 呼び出しの
        # 途中でプロセスごと終了することになり、CoUninitialize されない
        # まま COM ポインタが破棄されて access violation
        # (Exception ignored in: _compointer_base.__del__) を起こす経路が
        # 残る。stopMonitoring() より前に呼ぶ: 後で呼ぶと
        # _syncMonitoringLifecycleLocked() が「もう片方はまだ active」と見て
        # 監視スレッドを再起動してしまう。
        try:
            device_manager.setMicAutoActive(False)
        except Exception:
            errorLogging()
        try:
            device_manager.setSpeakerAutoActive(False)
        except Exception:
            errorLogging()
        try:
            device_manager.stopMonitoring()
        except Exception:
            errorLogging()
        # mic/speaker_lifecycle_worker を止め、以後の enqueue を無視する。
        # ここで止めておかないと、シャットダウン中に届いた古いデバイス
        # 通知やミュート同期の再送が、直後の _stopLockedForShutdown による
        # リソース解放と競合しうる (フェーズ3項目21)。mic/speakerは互いに
        # 無関係なので、直列ではなく並行に stop() する (コードレビュー指摘:
        # 直列だと最大 _SHUTDOWN_LIFECYCLE_LOCK_TIMEOUT_SEC 秒の2倍を
        # 待ちうる。ここは watchdog の強制終了デッドライン
        # [mainloop._WATCHDOG_GRACE_PERIOD_SEC] と競争している区間)。
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(self._stopWorkerForShutdown, model.mic_lifecycle_worker),
                executor.submit(self._stopWorkerForShutdown, model.speaker_lifecycle_worker),
            ]
            for future in futures:
                future.result()
        # 以下の4つは他の全ての start/stop 系 (mic/speaker_lifecycle_lock を
        # 保持する) と直列化する必要がある。ロック未取得のまま model.* を
        # 直接叩くと、AudioLifecycleWorker がまだ実行中の
        # restartAccessMicDevices 等と _stop()/_start() が並行実行され、
        # 片方が代入した新しい Recorder をもう片方が知らずに破棄する形で
        # listener スレッドと PyAudio ストリームが宙に浮いたままプロセスが
        # 終了しうる。
        self._stopLockedForShutdown(self.mic_lifecycle_lock, model.stopMicTranscript, "mic transcript")
        self._stopLockedForShutdown(self.speaker_lifecycle_lock, model.stopSpeakerTranscript, "speaker transcript")
        self._stopLockedForShutdown(self.mic_lifecycle_lock, model.stopCheckMicEnergy, "mic energy")
        self._stopLockedForShutdown(self.speaker_lifecycle_lock, model.stopCheckSpeakerEnergy, "speaker energy")
        # OSC / WebSocket / OBS Browser Source / Overlay も明示的に停止する
        # (フェーズ4項目30)。以前はここが抜けており daemon thread としての
        # プロセス終了任せになっていた: OSCQueryはzeroconfでサービス広告を
        # 出しているため、close()無しの終了は他アプリ側に無効なレコードを
        # 残す。呼び出し順は「依存する側を先に」— OBS Browser SourceはWebSocket
        # サーバ経由でメッセージを受け取るため、OBSを先に止める。
        self._stopServiceForShutdown(model.stopReceiveOSC, "OSC receive server")
        self._stopServiceForShutdown(model.stopObsBrowserSourceServer, "OBS browser source server")
        self._stopServiceForShutdown(model.stopWebSocketServer, "WebSocket server")
        self._stopServiceForShutdown(model.shutdownOverlay, "Overlay")
        try:
            # A setting changed in the last few seconds may still be sitting
            # in the debounce timer rather than on disk; flush it now so a
            # normal app close never silently drops the change.
            config.saveConfigToFile()
        except Exception:
            errorLogging()
        try:
            model.telemetryShutdown()
            return {"status": 200, "result": True}
        except Exception:
            errorLogging()
            return {"status": 500, "result": False}

    # response functions
    def connectedNetwork(self) -> None:
        self.run(
            200,
            self.run_mapping["connected_network"],
            True,
        )

    def disconnectedNetwork(self) -> None:
        self.run(
            200,
            self.run_mapping["connected_network"],
            False,
        )

    def enableAiModels(self) -> None:
        self.run(
            200,
            self.run_mapping["enable_ai_models"],
            True,
        )

    def disableAiModels(self) -> None:
        self.run(
            200,
            self.run_mapping["enable_ai_models"],
            False,
        )

    def updateMicHostList(self) -> None:
        self.run(
            200,
            self.run_mapping["selectable_mic_host_list"],
            model.getListMicHost(),
        )

    def updateMicDeviceList(self) -> None:
        self.run(
            200,
            self.run_mapping["selectable_mic_device_list"],
            model.getListMicDevice(),
        )

    def updateSpeakerDeviceList(self) -> None:
        self.run(
            200,
            self.run_mapping["selectable_speaker_device_list"],
            model.getListSpeakerDevice(),
        )

    def updateConfigSettings(self) -> None:
        settings = {}
        for endpoint, dict_data in self.init_mapping.items():
            response = dict_data["variable"](None)
            result = response.get("result", None)
            settings[endpoint] = result
        self.run(
            200,
            self.run_mapping["initialization_complete"],
            settings,
        )

    def restartAccessMicDevices(self) -> None:
        if config.ENABLE_TRANSCRIPTION_SEND is True:
            self.startTranscriptionSendMessage()
        if config.ENABLE_CHECK_ENERGY_SEND is True:
            self.startCheckMicEnergy()

    def restartAccessSpeakerDevices(self) -> None:
        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            self.startTranscriptionReceiveMessage()
        if config.ENABLE_CHECK_ENERGY_RECEIVE is True:
            self.startCheckSpeakerEnergy()

    def stopAccessMicDevices(self) -> None:
        if config.ENABLE_TRANSCRIPTION_SEND is True:
            self.stopTranscriptionSendMessage()
        if config.ENABLE_CHECK_ENERGY_SEND is True:
            self.stopCheckMicEnergy()

    def stopAccessSpeakerDevices(self) -> None:
        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            self.stopTranscriptionReceiveMessage()
        if config.ENABLE_CHECK_ENERGY_RECEIVE is True:
            self.stopCheckSpeakerEnergy()

    def updateSelectedMicDevice(self, host, device) -> None:
        config.SELECTED_MIC_HOST = host
        config.SELECTED_MIC_DEVICE = device
        self.run(200, self.run_mapping["selected_mic_host"], config.SELECTED_MIC_HOST)
        self.run(200, self.run_mapping["selected_mic_device"], config.SELECTED_MIC_DEVICE)

    def updateSelectedSpeakerDevice(self, device) -> None:
        config.SELECTED_SPEAKER_DEVICE = device
        self.run(
            200,
            self.run_mapping["selected_speaker_device"],
            device,
        )

    def progressBarMicEnergy(self, energy) -> None:
        if energy is False:
            error_response = VRCTError.create_error_response(
                ErrorCode.DEVICE_NO_MIC,
                data=None
            )
            self.run(
                error_response["status"],
                self.run_mapping["error_device"],
                error_response["result"],
            )
        else:
            self.run(
                200,
                self.run_mapping["check_mic_volume"],
                energy,
            )

    def progressBarSpeakerEnergy(self, energy) -> None:
        if energy is False:
            error_response = VRCTError.create_error_response(
                ErrorCode.DEVICE_NO_SPEAKER,
                data=None
            )
            self.run(
                error_response["status"],
                self.run_mapping["error_device"],
                error_response["result"],
            )
        else:
            self.run(
                200,
                self.run_mapping["check_speaker_volume"],
                energy,
            )

    class DownloadCTranslate2:
        def __init__(self, run_mapping:dict,  weight_type:str, run:Callable[[int, str, Any], None]) -> None:
            self.run_mapping = run_mapping
            self.weight_type = weight_type
            self.run = run
            self._last_progress = -1.0
            self._last_time = 0.0

        def progressBar(self, progress) -> None:
            if not _shouldEmitDownloadProgress(self, progress):
                return
            printLog("CTranslate2 Weight Download Progress", progress)
            self.run(
                200,
                self.run_mapping["download_progress_ctranslate2_weight"],
                {"weight_type": self.weight_type, "progress": progress},
            )

        def downloaded(self) -> None:
            if model.checkTranslatorCTranslate2ModelWeight(self.weight_type) is True:
                config.SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT[self.weight_type] = True

                self.run(
                    200,
                    self.run_mapping["downloaded_ctranslate2_weight"],
                    self.weight_type,
                )
            else:
                error_response = VRCTError.create_error_response(
                    ErrorCode.WEIGHT_CTRANSLATE2_DOWNLOAD,
                    data=None
                )
                self.run(
                    error_response["status"],
                    self.run_mapping["error_ctranslate2_weight"],
                    error_response["result"],
                )

    class DownloadWhisper:
        def __init__(self, run_mapping:dict, weight_type:str, run:Callable[[int, str, Any], None]) -> None:
            self.run_mapping = run_mapping
            self.weight_type = weight_type
            self.run = run
            self._last_progress = -1.0
            self._last_time = 0.0

        def progressBar(self, progress) -> None:
            if not _shouldEmitDownloadProgress(self, progress):
                return
            printLog("Whisper Weight Download Progress", progress)
            self.run(
                200,
                self.run_mapping["download_progress_whisper_weight"],
                {"weight_type": self.weight_type, "progress": progress},
            )

        def downloaded(self) -> None:
            if model.checkTranscriptionWhisperModelWeight(self.weight_type) is True:
                config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT[self.weight_type] = True

                self.run(
                    200,
                    self.run_mapping["downloaded_whisper_weight"],
                    self.weight_type,
                )
            else:
                error_response = VRCTError.create_error_response(
                    ErrorCode.WEIGHT_WHISPER_DOWNLOAD,
                    data=None
                )
                self.run(
                    error_response["status"],
                    self.run_mapping["error_whisper_weight"],
                    error_response["result"],
                )

    def _processMessage(
        self,
        spec: MessageDirectionSpec,
        message: str,
        language: Optional[str],
        msg_id: Optional[str] = None,
    ) -> Optional[dict]:
        """mic/speaker/chatMessage共通のパイプライン(バックエンドレビュー
        フェーズ3項目25、`MessageDirectionSpec`参照)。

        「ワードフィルタ→繰り返し検出→翻訳→transliteration→OSC送信→
        オーバーレイ更新→(mic限定)クリップボード→UI配信→WebSocket送信→
        ロガー→履歴記録」を`spec`の差分だけで吸収する。呼び出し元は
        非空メッセージであることを保証してから呼ぶこと。

        `spec.delivery=="push"`の場合は内部で`self.run()`を呼び`None`を
        返す。`"return"`(chat)の場合は`{"id", "original", "translations"}`
        を返す(呼び出し元が`{"status":200,"result":...}`に包む)。
        ワードフィルタ・繰り返し検出・VRAMエラーで早期returnした場合は
        `model.addTranslationHistory`を呼ばない(旧実装の挙動を踏襲)。
        """
        if spec.has_word_filter and model.checkKeywords(message):
            self.run(
                200,
                self.run_mapping["word_filter"],
                {"message": f"Detected by word filter: {message}"},
            )
            return None

        if spec.repeat_detector_attr is not None and getattr(model, spec.repeat_detector_attr)(message):
            return None

        translation: list = []
        if config.ENABLE_TRANSLATION is False:
            pass
        else:
            try:
                translate = getattr(model, spec.translate_attr)
                translation, success = translate(message, source_language=language)
                if all(success) is not True:
                    self.changeToCTranslate2Process()
                    error_response = VRCTError.create_error_response(
                        ErrorCode.TRANSLATION_ENGINE_LIMIT,
                        data=None
                    )
                    self.run(
                        error_response["status"],
                        self.run_mapping["error_translation_engine"],
                        error_response["result"],
                    )
            except Exception as e:
                # VRAM不足エラーの検出
                is_vram_error, error_message = model.detectVRAMError(e)
                if not is_vram_error:
                    # その他のエラーは通常通り処理
                    raise
                error_response = VRCTError.create_error_response(
                    spec.vram_error_code,
                    data=error_message
                )
                self.run(
                    error_response["status"],
                    self.run_mapping[spec.vram_run_mapping_key],
                    error_response["result"],
                )
                # 翻訳機能をOFFにする
                self.setDisableTranslation()
                disable_response = VRCTError.create_error_response(
                    ErrorCode.TRANSLATION_DISABLED_VRAM,
                    data=False
                )
                self.run(
                    disable_response["status"],
                    self.run_mapping["enable_translation"],
                    disable_response["result"],
                )
                if spec.delivery == "return":
                    # エラー時は翻訳なしで返す
                    return {
                        "id": msg_id,
                        "original": {"message": message, "transliteration": []},
                        "translations": [
                            {"message": "", "transliteration": []}
                            for _ in config.SELECTED_TAB_TARGET_LANGUAGES_NO_LIST
                        ],
                    }
                return None

        transliteration_message: List[Any] = []
        transliteration_translation: list = []
        if config.CONVERT_MESSAGE_TO_HIRAGANA is True or config.CONVERT_MESSAGE_TO_ROMAJI is True:
            if spec.own_transliteration_source == "your_language":
                own_message_is_japanese = config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]["language"] == "Japanese"
            else:
                own_message_is_japanese = language == "Japanese"
            if own_message_is_japanese:
                transliteration_message = model.convertMessageToTransliteration(
                    message,
                    hiragana=config.CONVERT_MESSAGE_TO_HIRAGANA,
                    romaji=config.CONVERT_MESSAGE_TO_ROMAJI
                )

            if spec.multi_target:
                for i, no in enumerate(config.SELECTED_TAB_TARGET_LANGUAGES_NO_LIST):
                    if (config.ENABLE_TRANSLATION is True and
                        config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO][no]["language"] == "Japanese" and
                        config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO][no]["enable"] is True
                        ):
                        transliteration_translation.append(
                            model.convertMessageToTransliteration(
                                translation[i],
                                hiragana=config.CONVERT_MESSAGE_TO_HIRAGANA,
                                romaji=config.CONVERT_MESSAGE_TO_ROMAJI
                            )
                        )
                    else:
                        transliteration_translation.append([])
            else:
                if (config.ENABLE_TRANSLATION is True and
                    config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]["language"] == "Japanese"
                    ):
                    transliteration_translation.append(
                        model.convertMessageToTransliteration(
                            translation[0],
                            hiragana=config.CONVERT_MESSAGE_TO_HIRAGANA,
                            romaji=config.CONVERT_MESSAGE_TO_ROMAJI
                        )
                    )
                else:
                    transliteration_translation.append([])
        else:
            if spec.multi_target:
                transliteration_translation = [[] for _ in config.SELECTED_TAB_TARGET_LANGUAGES_NO_LIST]
            else:
                transliteration_translation = [[]]

        payload = {
            "original": {
                "message": message,
                "transliteration": transliteration_message
            },
            "translations": [
                {
                    "message": translation_message,
                    "transliteration": transliteration
                } for translation_message, transliteration in zip(translation, transliteration_translation)
            ]
        }

        if spec.feature_gate_attr is None or getattr(config, spec.feature_gate_attr) is True:
            if getattr(config, spec.osc_send_gate_attr) is True:
                if config.SEND_ONLY_TRANSLATED_MESSAGES is True:
                    if config.ENABLE_TRANSLATION is False:
                        osc_message = self.messageFormatter(spec.osc_format_type, [], message)
                    else:
                        osc_message = self.messageFormatter(spec.osc_format_type, translation, "")
                else:
                    osc_message = self.messageFormatter(spec.osc_format_type, translation, message)
                model.oscSendMessage(osc_message)

            if spec.overlay_small_log and config.OVERLAY_SMALL_LOG is True and self._is_overlay_available():
                if config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES is True:
                    if len(translation) > 0:
                        overlay_image = model.createOverlayImageSmallLog(
                            None,
                            None,
                            translation,
                            config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO],
                            transliteration_message,
                            transliteration_translation
                        )
                        model.updateOverlaySmallLog(overlay_image)
                else:
                    overlay_image = model.createOverlayImageSmallLog(
                        message,
                        language,
                        translation,
                        config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO],
                        transliteration_message,
                        transliteration_translation
                    )
                    model.updateOverlaySmallLog(overlay_image)

            if config.OVERLAY_LARGE_LOG is True and self._is_overlay_available():
                if spec.overlay_direction == "send":
                    overlay_own_language = config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]["language"]
                    overlay_language_list = config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO]
                else:
                    overlay_own_language = language
                    overlay_language_list = config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]
                if config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES is True:
                    if len(translation) > 0:
                        overlay_image = model.createOverlayImageLargeLog(
                            spec.overlay_direction,
                            None,
                            None,
                            translation,
                            overlay_language_list,
                            transliteration_message,
                            transliteration_translation
                        )
                        model.updateOverlayLargeLog(overlay_image)
                else:
                    overlay_image = model.createOverlayImageLargeLog(
                        spec.overlay_direction,
                        message,
                        overlay_own_language,
                        translation,
                        overlay_language_list,
                        transliteration_message,
                        transliteration_translation
                    )
                    model.updateOverlayLargeLog(overlay_image)

            if spec.clipboard and config.ENABLE_CLIPBOARD is True:
                clipboard_message = self.messageFormatter(spec.osc_format_type, translation, message)
                model.setCopyToClipboardAndPasteFromClipboard(clipboard_message)

            if spec.delivery == "push":
                self.run(200, self.run_mapping[spec.run_mapping_key], payload)

            if model.checkWebSocketServerAlive() is True:
                model.websocketSendMessage(
                    {
                        "type": spec.ws_type,
                        "src_languages": getattr(config, spec.ws_src_languages_attr)[config.SELECTED_TAB_NO],
                        "dst_languages": getattr(config, spec.ws_dst_languages_attr)[config.SELECTED_TAB_NO],
                        "message": message,
                        "translation": translation,
                        "transliteration": transliteration_translation
                    }
                )

            if config.LOGGER_FEATURE is True:
                translation_text = f" ({'/'.join(translation)})" if translation else ""
                model.logger.info(f"{spec.logger_prefix} {message}{translation_text}")

        model.addTranslationHistory(spec.kind, message)

        if spec.delivery == "return":
            return {"id": msg_id, **payload}
        return None

    def micMessage(self, result: dict) -> None:
        if config.VRC_MIC_MUTE_SYNC is True and model.mic_mute_status is True:
            return

        if result.get("recognition_error") is True:
            self.run(
                200,
                self.run_mapping["transcription_recognition_error"],
                {"message": "Mic speech recognition request failed. Check your network connection.", "data": None},
            )

        message = result["text"]
        language = result["language"]
        if isinstance(message, bool) and message is False:
            self.run(
                400,
                self.run_mapping["error_device"],
                {
                    "message":"No mic device detected",
                    "data": None
                },
            )
        elif isinstance(message, str) and len(message) > 0:
            self._processMessage(MIC_MESSAGE_SPEC, message, language)

    def speakerMessage(self, result:dict) -> None:
        if result.get("recognition_error") is True:
            self.run(
                200,
                self.run_mapping["transcription_recognition_error"],
                {"message": "Speaker speech recognition request failed. Check your network connection.", "data": None},
            )

        message = result["text"]
        language = result["language"]
        if isinstance(message, bool) and message is False:
            self.run(
                400,
                self.run_mapping["error_device"],
                {
                    "message":"No speaker device detected",
                    "data": None
                },
            )
        elif isinstance(message, str) and len(message) > 0:
            self._processMessage(SPEAKER_MESSAGE_SPEC, message, language)

    def chatMessage(self, data) -> dict:
        msg_id = data["id"]
        message = data["message"]
        if len(message) == 0:
            # 既知のバグ修正: 以前はここで translation/transliteration_* が
            # 未初期化のまま戻り値の構築に使われ UnboundLocalError になっていた。
            model.addTranslationHistory("chat", message)
            return {
                "status": 200,
                "result": {
                    "id": msg_id,
                    "original": {"message": message, "transliteration": []},
                    "translations": []
                },
            }
        result = self._processMessage(CHAT_MESSAGE_SPEC, message, None, msg_id=msg_id)
        return {"status": 200, "result": result}


    def checkSoftwareUpdated(self) -> dict:
        software_update_info = model.checkSoftwareUpdated()
        self.run(
            200,
            self.run_mapping["software_update_info"],
            software_update_info,
        )
        return {"status":200, "result": software_update_info}




    def setSelectedTranslationComputeDevice(self, device:str, *args, **kwargs) -> dict:
        printLog("setSelectedTranslationComputeDevice", device)
        config.SELECTED_TRANSLATION_COMPUTE_DEVICE = device
        config.SELECTED_TRANSLATION_COMPUTE_TYPE = "auto"
        self.run(200, self.run_mapping["selected_translation_compute_type"], config.SELECTED_TRANSLATION_COMPUTE_TYPE)
        model.setChangedTranslatorParameters(True)
        return {"status":200,"result":config.SELECTED_TRANSLATION_COMPUTE_DEVICE}



    def setSelectedTranscriptionComputeDevice(self, device:str, *args, **kwargs) -> dict:
        printLog("setSelectedTranscriptionComputeDevice", device)
        config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE = device
        config.SELECTED_TRANSCRIPTION_COMPUTE_TYPE = "auto"
        self.run(200, self.run_mapping["selected_transcription_compute_type"], config.SELECTED_TRANSCRIPTION_COMPUTE_TYPE)
        return {"status":200,"result":config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE}

    @staticmethod
    def getSelectableWhisperWeightTypeDict(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT}

    # @staticmethod
    # def getMaxMicThreshold(*args, **kwargs) -> dict:
    #     return {"status":200, "result":config.MAX_MIC_THRESHOLD}

    # @staticmethod
    # def getMaxSpeakerThreshold(*args, **kwargs) -> dict:
    #     return {"status":200, "result":config.MAX_SPEAKER_THRESHOLD}

    def setEnableTranslation(self, *args, **kwargs) -> dict:
        if config.ENABLE_TRANSLATION is False:
            if model.isLoadedCTranslate2Model() is False or model.isChangedTranslatorParameters() is True:
                try:
                    model.changeTranslatorCTranslate2Model()
                    model.setChangedTranslatorParameters(False)
                    config.ENABLE_TRANSLATION = True
                except Exception as e:
                    # VRAM不足エラーの検出（デバイス切り替え時）
                    is_vram_error, error_message = model.detectVRAMError(e)
                    if is_vram_error:
                        # Defaultのデバイス設定に戻す
                        printLog("VRAM error detected, reverting device setting")
                        error_response = VRCTError.create_error_response(
                            ErrorCode.TRANSLATION_VRAM_ENABLE,
                            data=error_message
                        )
                        self.run(
                            error_response["status"],
                            self.run_mapping["error_translation_enable_vram_overflow"],
                            error_response["result"],
                        )
                        self.setDisableTranslation()
                        disable_response = VRCTError.create_error_response(
                            ErrorCode.TRANSLATION_DISABLED_VRAM,
                            data=False
                        )
                        self.run(
                            disable_response["status"],
                            self.run_mapping["enable_translation"],
                            disable_response["result"],
                        )
                        model.changeTranslatorCTranslate2Model()
                        model.setChangedTranslatorParameters(False)
                    else:
                        # その他のエラーは通常通り処理
                        errorLogging()
            else:
                config.ENABLE_TRANSLATION = True
        return {"status":200, "result":config.ENABLE_TRANSLATION}

    @staticmethod
    def setDisableTranslation(*args, **kwargs) -> dict:
        if config.ENABLE_TRANSLATION is True:
            config.ENABLE_TRANSLATION = False
        return {"status":200, "result":config.ENABLE_TRANSLATION}

    @staticmethod
    def setEnableForeground(*args, **kwargs) -> dict:
        if config.ENABLE_FOREGROUND is False:
            config.ENABLE_FOREGROUND = True
        return {"status":200, "result":config.ENABLE_FOREGROUND}

    @staticmethod
    def setDisableForeground(*args, **kwargs) -> dict:
        if config.ENABLE_FOREGROUND is True:
            config.ENABLE_FOREGROUND = False
        return {"status":200, "result":config.ENABLE_FOREGROUND}


    def setSelectedTabNo(self, selected_tab_no:str, *args, **kwargs) -> dict:
        printLog("setSelectedTabNo", selected_tab_no)
        config.SELECTED_TAB_NO = selected_tab_no
        self.updateTranslationEngineAndEngineList()
        return {"status":200, "result":config.SELECTED_TAB_NO}

    @staticmethod
    def getTranslationEngines(*args, **kwargs) -> dict:
        engines = model.findTranslationEngines(
            config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO],
            config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO],
            config.SELECTABLE_TRANSLATION_ENGINE_STATUS,
            )

        your_language = config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]
        for target_language in config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO].values():
            if your_language["language"] == target_language["language"] and target_language["enable"] is True:
                if config.SELECTABLE_TRANSLATION_ENGINE_STATUS["CTranslate2"] is True:
                    engines = ["CTranslate2"]
                else:
                    engines = []

        return {"status":200, "result":engines}

    @staticmethod
    def getListLanguageAndCountry(*args, **kwargs) -> dict:
        return {"status":200, "result": model.getListLanguageAndCountry()}

    @staticmethod
    def getMicHostList(*args, **kwargs) -> dict:
        return {"status":200, "result": model.getListMicHost()}

    @staticmethod
    def getMicDeviceList(*args, **kwargs) -> dict:
        return {"status":200, "result": model.getListMicDevice()}

    @staticmethod
    def getSpeakerDeviceList(*args, **kwargs) -> dict:
        return {"status":200, "result": model.getListSpeakerDevice()}


    def setSelectedTranslationEngines(self, data:dict, *args, **kwargs) -> dict:
        config.SELECTED_TRANSLATION_ENGINES = data
        # Resolves the engine (availability / same-language checks can still
        # downgrade it to CTranslate2) and then validates the language
        # against whichever engine actually ends up active.
        self.updateTranslationEngineAndEngineList()
        return {"status":200,"result":config.SELECTED_TRANSLATION_ENGINES}


    def setSelectedYourLanguages(self, select:dict, *args, **kwargs) -> dict:
        config.SELECTED_YOUR_LANGUAGES = select
        self.updateTranslationEngineAndEngineList()
        return {"status":200, "result":config.SELECTED_YOUR_LANGUAGES}


    def setSelectedTargetLanguages(self, select:dict, *args, **kwargs) -> dict:
        config.SELECTED_TARGET_LANGUAGES = select
        self.updateTranslationEngineAndEngineList()
        return {"status":200, "result":config.SELECTED_TARGET_LANGUAGES}

    @staticmethod
    def getTranscriptionEngines(*args, **kwargs) -> dict:
        engines = [key for key, value in config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS.items() if value is True]
        return {"status":200, "result":engines}


    def setSelectedTranscriptionEngine(self, data, *args, **kwargs) -> dict:
        # setSelectedTranslationEngines() -> updateTranslationEngineAndEngineList()
        # と同じパターン: 希望値をまず渡し、可用性チェック・言語フォールバック・
        # 言語リストのpushは updateTranscriptionEngine() 側に集約する。
        self.updateTranscriptionEngine(requested_engine=str(data))
        return {"status":200, "result":config.SELECTED_TRANSCRIPTION_ENGINE}

    def fallbackUnsupportedLanguagesForTranscriptionEngine(self, engine: str) -> bool:
        """文字起こしエンジンが切り替わった際、既に選択されている言語が
        新しいエンジンで対応していなければデフォルト言語 (日本語/英語) へ
        リセットする (翻訳側の fallbackUnsupportedLanguagesForEngine の
        文字起こしエンジン版)。

        SELECTED_TRANSCRIPTION_ENGINE はタブ横断のグローバル設定
        (SELECTED_TRANSLATION_ENGINES と違いタブごとではない) なので、
        全タブについて確認する。

        Returns True if any language was reset.
        """
        changed = False

        your_languages = copy.deepcopy(config.SELECTED_YOUR_LANGUAGES)
        target_languages = copy.deepcopy(config.SELECTED_TARGET_LANGUAGES)

        for tab_no in your_languages.keys():
            your_language = your_languages[tab_no]["1"]
            enabled_target_languages = {
                target_language["language"]
                for target_language in target_languages.get(tab_no, {}).values()
                if target_language["enable"] is True
            }
            if not model.isLanguageSupportedByTranscriptionEngine(engine, your_language["language"], your_language["country"]):
                default = model.pickDefaultLanguageAndCountryForTranscriptionEngine(engine, enabled_target_languages)
                if default is not None:
                    your_languages[tab_no]["1"] = {**default, "enable": True}
                    changed = True
                    your_language = your_languages[tab_no]["1"]

            taken_languages = {your_language["language"]}
            for target_language in target_languages.get(tab_no, {}).values():
                if target_language["enable"] is not True:
                    continue
                if model.isLanguageSupportedByTranscriptionEngine(engine, target_language["language"], target_language["country"]):
                    taken_languages.add(target_language["language"])
                    continue
                default = model.pickDefaultLanguageAndCountryForTranscriptionEngine(engine, taken_languages)
                if default is not None:
                    target_language["language"] = default["language"]
                    target_language["country"] = default["country"]
                    changed = True
                taken_languages.add(target_language["language"])

        if changed:
            config.SELECTED_YOUR_LANGUAGES = your_languages
            config.SELECTED_TARGET_LANGUAGES = target_languages
            self.run(200, self.run_mapping["selected_your_languages"], config.SELECTED_YOUR_LANGUAGES)
            self.run(200, self.run_mapping["selected_target_languages"], config.SELECTED_TARGET_LANGUAGES)

        return changed

    # ------------------------------------------------------------------
    # Transcription API engines (Groq Whisper / OpenAI Whisper / カスタムサーバー)
    #
    # 翻訳側のエンジンと違い、文字起こし側にはエンジンごとの永続クライアント
    # オブジェクトが存在しない (AudioTranscriber がセッション開始のたびに
    # config の現在値からプロバイダを都度組み立てる設計のため、
    # model.updateTranslatorXClient() に相当する呼び出しは不要)。
    # モデル選択の検証も、翻訳側のようにクライアントへ問い合わせる
    # model.setTranslatorXModel(...) 相当は行わず、
    # SELECTABLE_*_MODEL_LIST に含まれているかどうかだけで判定する。
    # ------------------------------------------------------------------
    @staticmethod
    def getGroqWhisperAuthKey(*args, **kwargs) -> dict:
        return {"status":200, "result":config.TRANSCRIPTION_AUTH_KEYS["Groq_Whisper"]}

    def setGroqWhisperAuthKey(self, data, *args, **kwargs) -> dict:
        printLog("Set Groq Whisper Auth Key")
        engine = "Groq_Whisper"
        try:
            data = str(data).strip()
            if len(data) == 0:
                response = VRCTError.create_error_response(
                    ErrorCode.TRANSCRIPTION_API_AUTH_FAILED,
                    data=None
                )
            else:
                result = model.authenticationTranscriptionApiKey(api_key=data, base_url=config.GROQ_WHISPER_BASE_URL)
                if result is True:
                    model_list = model.getTranscriptionApiModelList(
                        api_key=data, base_url=config.GROQ_WHISPER_BASE_URL, keyword_filter=TRANSCRIPTION_MODEL_KEYWORDS,
                    )
                    if len(model_list) == 0:
                        response = VRCTError.create_error_response(
                            ErrorCode.TRANSCRIPTION_API_AUTH_FAILED,
                            data=None
                        )
                    else:
                        auth_keys = config.TRANSCRIPTION_AUTH_KEYS
                        auth_keys[engine] = data
                        config.TRANSCRIPTION_AUTH_KEYS = auth_keys
                        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS[engine] = True
                        config.SELECTABLE_GROQ_WHISPER_MODEL_LIST = model_list
                        self.run(200, self.run_mapping["selectable_groq_whisper_model_list"], config.SELECTABLE_GROQ_WHISPER_MODEL_LIST)
                        if config.SELECTED_GROQ_WHISPER_MODEL not in config.SELECTABLE_GROQ_WHISPER_MODEL_LIST:
                            config.SELECTED_GROQ_WHISPER_MODEL = config.SELECTABLE_GROQ_WHISPER_MODEL_LIST[0]
                        self.run(200, self.run_mapping["selected_groq_whisper_model"], config.SELECTED_GROQ_WHISPER_MODEL)
                        self.updateTranscriptionEngine()
                        response = {"status":200, "result":config.TRANSCRIPTION_AUTH_KEYS[engine]}
                else:
                    response = VRCTError.create_error_response(
                        ErrorCode.TRANSCRIPTION_API_AUTH_FAILED,
                        data=None
                    )
        except Exception as e:
            errorLogging()
            response = VRCTError.create_exception_error_response(
                e,
                data=None
            )
        if response["status"] == 400:
            self.delGroqWhisperAuthKey()
        return response

    def delGroqWhisperAuthKey(self, *args, **kwargs) -> dict:
        engine = "Groq_Whisper"
        auth_keys = config.TRANSCRIPTION_AUTH_KEYS
        auth_keys[engine] = None
        config.TRANSCRIPTION_AUTH_KEYS = auth_keys
        config.SELECTABLE_GROQ_WHISPER_MODEL_LIST = []
        config.SELECTED_GROQ_WHISPER_MODEL = None
        self.run(200, self.run_mapping["selectable_groq_whisper_model_list"], config.SELECTABLE_GROQ_WHISPER_MODEL_LIST)
        self.run(200, self.run_mapping["selected_groq_whisper_model"], config.SELECTED_GROQ_WHISPER_MODEL)
        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS[engine] = False
        self.updateTranscriptionEngine()
        return {"status":200, "result":config.TRANSCRIPTION_AUTH_KEYS[engine]}



    @staticmethod
    def setGroqWhisperModel(data, *args, **kwargs) -> dict:
        printLog("Set Groq Whisper Model", data)
        data = str(data)
        if data in config.SELECTABLE_GROQ_WHISPER_MODEL_LIST:
            config.SELECTED_GROQ_WHISPER_MODEL = data
            return {"status":200, "result":config.SELECTED_GROQ_WHISPER_MODEL}
        return VRCTError.create_error_response(
            ErrorCode.MODEL_TRANSCRIPTION_INVALID,
            data=config.SELECTED_GROQ_WHISPER_MODEL
        )

    @staticmethod
    def getOpenAIWhisperAuthKey(*args, **kwargs) -> dict:
        return {"status":200, "result":config.TRANSCRIPTION_AUTH_KEYS["OpenAI_Whisper"]}

    def setOpenAIWhisperAuthKey(self, data, *args, **kwargs) -> dict:
        printLog("Set OpenAI Whisper Auth Key")
        engine = "OpenAI_Whisper"
        try:
            data = str(data).strip()
            if len(data) == 0:
                response = VRCTError.create_error_response(
                    ErrorCode.TRANSCRIPTION_API_AUTH_FAILED,
                    data=None
                )
            else:
                result = model.authenticationTranscriptionApiKey(api_key=data, base_url=config.OPENAI_WHISPER_BASE_URL)
                if result is True:
                    model_list = model.getTranscriptionApiModelList(
                        api_key=data, base_url=config.OPENAI_WHISPER_BASE_URL, keyword_filter=TRANSCRIPTION_MODEL_KEYWORDS,
                    )
                    if len(model_list) == 0:
                        response = VRCTError.create_error_response(
                            ErrorCode.TRANSCRIPTION_API_AUTH_FAILED,
                            data=None
                        )
                    else:
                        auth_keys = config.TRANSCRIPTION_AUTH_KEYS
                        auth_keys[engine] = data
                        config.TRANSCRIPTION_AUTH_KEYS = auth_keys
                        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS[engine] = True
                        config.SELECTABLE_OPENAI_WHISPER_MODEL_LIST = model_list
                        self.run(200, self.run_mapping["selectable_openai_whisper_model_list"], config.SELECTABLE_OPENAI_WHISPER_MODEL_LIST)
                        if config.SELECTED_OPENAI_WHISPER_MODEL not in config.SELECTABLE_OPENAI_WHISPER_MODEL_LIST:
                            config.SELECTED_OPENAI_WHISPER_MODEL = config.SELECTABLE_OPENAI_WHISPER_MODEL_LIST[0]
                        self.run(200, self.run_mapping["selected_openai_whisper_model"], config.SELECTED_OPENAI_WHISPER_MODEL)
                        self.updateTranscriptionEngine()
                        response = {"status":200, "result":config.TRANSCRIPTION_AUTH_KEYS[engine]}
                else:
                    response = VRCTError.create_error_response(
                        ErrorCode.TRANSCRIPTION_API_AUTH_FAILED,
                        data=None
                    )
        except Exception as e:
            errorLogging()
            response = VRCTError.create_exception_error_response(
                e,
                data=None
            )
        if response["status"] == 400:
            self.delOpenAIWhisperAuthKey()
        return response

    def delOpenAIWhisperAuthKey(self, *args, **kwargs) -> dict:
        engine = "OpenAI_Whisper"
        auth_keys = config.TRANSCRIPTION_AUTH_KEYS
        auth_keys[engine] = None
        config.TRANSCRIPTION_AUTH_KEYS = auth_keys
        config.SELECTABLE_OPENAI_WHISPER_MODEL_LIST = []
        config.SELECTED_OPENAI_WHISPER_MODEL = None
        self.run(200, self.run_mapping["selectable_openai_whisper_model_list"], config.SELECTABLE_OPENAI_WHISPER_MODEL_LIST)
        self.run(200, self.run_mapping["selected_openai_whisper_model"], config.SELECTED_OPENAI_WHISPER_MODEL)
        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS[engine] = False
        self.updateTranscriptionEngine()
        return {"status":200, "result":config.TRANSCRIPTION_AUTH_KEYS[engine]}



    @staticmethod
    def setOpenAIWhisperModel(data, *args, **kwargs) -> dict:
        printLog("Set OpenAI Whisper Model", data)
        data = str(data)
        if data in config.SELECTABLE_OPENAI_WHISPER_MODEL_LIST:
            config.SELECTED_OPENAI_WHISPER_MODEL = data
            return {"status":200, "result":config.SELECTED_OPENAI_WHISPER_MODEL}
        return VRCTError.create_error_response(
            ErrorCode.MODEL_TRANSCRIPTION_INVALID,
            data=config.SELECTED_OPENAI_WHISPER_MODEL
        )

    @staticmethod
    def getCustomWhisperAuthKey(*args, **kwargs) -> dict:
        return {"status":200, "result":config.TRANSCRIPTION_AUTH_KEYS["Custom_Whisper"]}

    def setCustomWhisperAuthKey(self, data, *args, **kwargs) -> dict:
        printLog("Set Custom Whisper Auth Key")
        engine = "Custom_Whisper"
        try:
            data = str(data).strip()
            if len(data) == 0:
                response = VRCTError.create_error_response(
                    ErrorCode.TRANSCRIPTION_API_AUTH_FAILED,
                    data=None
                )
            else:
                result = model.authenticationTranscriptionApiKey(api_key=data, base_url=config.TRANSCRIPTION_CUSTOM_URL)
                if result is True:
                    # カスタムサーバーはどんなモデル名を使っているか分からないため絞り込まない
                    model_list = model.getTranscriptionApiModelList(api_key=data, base_url=config.TRANSCRIPTION_CUSTOM_URL)
                    if len(model_list) == 0:
                        response = VRCTError.create_error_response(
                            ErrorCode.TRANSCRIPTION_API_AUTH_FAILED,
                            data=None
                        )
                    else:
                        auth_keys = config.TRANSCRIPTION_AUTH_KEYS
                        auth_keys[engine] = data
                        config.TRANSCRIPTION_AUTH_KEYS = auth_keys
                        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS[engine] = True
                        config.SELECTABLE_CUSTOM_WHISPER_MODEL_LIST = model_list
                        self.run(200, self.run_mapping["selectable_custom_whisper_model_list"], config.SELECTABLE_CUSTOM_WHISPER_MODEL_LIST)
                        if config.SELECTED_CUSTOM_WHISPER_MODEL not in config.SELECTABLE_CUSTOM_WHISPER_MODEL_LIST:
                            config.SELECTED_CUSTOM_WHISPER_MODEL = config.SELECTABLE_CUSTOM_WHISPER_MODEL_LIST[0]
                        self.run(200, self.run_mapping["selected_custom_whisper_model"], config.SELECTED_CUSTOM_WHISPER_MODEL)
                        self.updateTranscriptionEngine()
                        response = {"status":200, "result":config.TRANSCRIPTION_AUTH_KEYS[engine]}
                else:
                    response = VRCTError.create_error_response(
                        ErrorCode.TRANSCRIPTION_API_AUTH_FAILED,
                        data=None
                    )
        except Exception as e:
            errorLogging()
            response = VRCTError.create_exception_error_response(
                e,
                data=None
            )
        if response["status"] == 400:
            self.delCustomWhisperAuthKey()
        return response

    def delCustomWhisperAuthKey(self, *args, **kwargs) -> dict:
        engine = "Custom_Whisper"
        auth_keys = config.TRANSCRIPTION_AUTH_KEYS
        auth_keys[engine] = None
        config.TRANSCRIPTION_AUTH_KEYS = auth_keys
        config.SELECTABLE_CUSTOM_WHISPER_MODEL_LIST = []
        config.SELECTED_CUSTOM_WHISPER_MODEL = None
        self.run(200, self.run_mapping["selectable_custom_whisper_model_list"], config.SELECTABLE_CUSTOM_WHISPER_MODEL_LIST)
        self.run(200, self.run_mapping["selected_custom_whisper_model"], config.SELECTED_CUSTOM_WHISPER_MODEL)
        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS[engine] = False
        self.updateTranscriptionEngine()
        return {"status":200, "result":config.TRANSCRIPTION_AUTH_KEYS[engine]}


    def setCustomWhisperURL(self, data, *args, **kwargs) -> dict:
        """URL 変更時は「認証成功後に URL を確定」する順序を守る
        (翻訳側の OpenAI互換エンジンの setOpenAICompatibleURL と同じ)。

        Auth Key が未設定の場合は URL だけ保存して終わる (次回 Auth Key 入力時に検証される)。
        """
        printLog("Set Custom Whisper URL", data)
        engine = "Custom_Whisper"
        try:
            data = str(data).strip()
            auth_key = config.TRANSCRIPTION_AUTH_KEYS[engine]

            if not auth_key:
                config.TRANSCRIPTION_CUSTOM_URL = data
                return {"status":200, "result":config.TRANSCRIPTION_CUSTOM_URL}

            result = model.authenticationTranscriptionApiKey(api_key=auth_key, base_url=data)
            if result is True:
                model_list = model.getTranscriptionApiModelList(api_key=auth_key, base_url=data)
                if len(model_list) == 0:
                    config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS[engine] = False
                    config.SELECTABLE_CUSTOM_WHISPER_MODEL_LIST = []
                    config.SELECTED_CUSTOM_WHISPER_MODEL = None
                    self.run(200, self.run_mapping["selectable_custom_whisper_model_list"], config.SELECTABLE_CUSTOM_WHISPER_MODEL_LIST)
                    self.run(200, self.run_mapping["selected_custom_whisper_model"], config.SELECTED_CUSTOM_WHISPER_MODEL)
                    self.updateTranscriptionEngine()
                    response = VRCTError.create_error_response(
                        ErrorCode.CONNECTION_TRANSCRIPTION_CUSTOM_URL_INVALID,
                        data=config.TRANSCRIPTION_CUSTOM_URL
                    )
                else:
                    config.TRANSCRIPTION_CUSTOM_URL = data
                    config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS[engine] = True
                    config.SELECTABLE_CUSTOM_WHISPER_MODEL_LIST = model_list
                    self.run(200, self.run_mapping["selectable_custom_whisper_model_list"], config.SELECTABLE_CUSTOM_WHISPER_MODEL_LIST)
                    if config.SELECTED_CUSTOM_WHISPER_MODEL not in config.SELECTABLE_CUSTOM_WHISPER_MODEL_LIST:
                        config.SELECTED_CUSTOM_WHISPER_MODEL = config.SELECTABLE_CUSTOM_WHISPER_MODEL_LIST[0]
                    self.run(200, self.run_mapping["selected_custom_whisper_model"], config.SELECTED_CUSTOM_WHISPER_MODEL)
                    self.updateTranscriptionEngine()
                    response = {"status":200, "result":config.TRANSCRIPTION_CUSTOM_URL}
            else:
                config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS[engine] = False
                config.SELECTABLE_CUSTOM_WHISPER_MODEL_LIST = []
                config.SELECTED_CUSTOM_WHISPER_MODEL = None
                self.run(200, self.run_mapping["selectable_custom_whisper_model_list"], config.SELECTABLE_CUSTOM_WHISPER_MODEL_LIST)
                self.run(200, self.run_mapping["selected_custom_whisper_model"], config.SELECTED_CUSTOM_WHISPER_MODEL)
                self.updateTranscriptionEngine()
                response = VRCTError.create_error_response(
                    ErrorCode.CONNECTION_TRANSCRIPTION_CUSTOM_URL_INVALID,
                    data=config.TRANSCRIPTION_CUSTOM_URL
                )
        except Exception as e:
            errorLogging()
            response = VRCTError.create_exception_error_response(
                e,
                data=config.TRANSCRIPTION_CUSTOM_URL
            )
        return response



    @staticmethod
    def setCustomWhisperModel(data, *args, **kwargs) -> dict:
        printLog("Set Custom Whisper Model", data)
        data = str(data)
        if data in config.SELECTABLE_CUSTOM_WHISPER_MODEL_LIST:
            config.SELECTED_CUSTOM_WHISPER_MODEL = data
            return {"status":200, "result":config.SELECTED_CUSTOM_WHISPER_MODEL}
        return VRCTError.create_error_response(
            ErrorCode.MODEL_TRANSCRIPTION_INVALID,
            data=config.SELECTED_CUSTOM_WHISPER_MODEL
        )

    @staticmethod
    def getDeepgramAuthKey(*args, **kwargs) -> dict:
        return {"status":200, "result":config.TRANSCRIPTION_AUTH_KEYS["Deepgram"]}

    def setDeepgramAuthKey(self, data, *args, **kwargs) -> dict:
        printLog("Set Deepgram Auth Key")
        engine = "Deepgram"
        try:
            data = str(data).strip()
            if len(data) == 0:
                response = VRCTError.create_error_response(
                    ErrorCode.TRANSCRIPTION_API_AUTH_FAILED,
                    data=None
                )
            else:
                result = model.authenticationDeepgramApiKey(api_key=data)
                if result is True:
                    models_detailed = model.getDeepgramModelListDetailed(api_key=data)
                    model_list = [m["name"] for m in models_detailed]
                    if len(model_list) == 0:
                        response = VRCTError.create_error_response(
                            ErrorCode.TRANSCRIPTION_API_AUTH_FAILED,
                            data=None
                        )
                    else:
                        auth_keys = config.TRANSCRIPTION_AUTH_KEYS
                        auth_keys[engine] = data
                        config.TRANSCRIPTION_AUTH_KEYS = auth_keys
                        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS[engine] = True
                        config.SELECTABLE_DEEPGRAM_MODEL_LIST = model_list
                        config.DEEPGRAM_MODEL_LANGUAGES = {m["name"]: m["languages"] for m in models_detailed}
                        self.run(200, self.run_mapping["selectable_deepgram_model_list"], config.SELECTABLE_DEEPGRAM_MODEL_LIST)
                        if config.SELECTED_DEEPGRAM_MODEL not in config.SELECTABLE_DEEPGRAM_MODEL_LIST:
                            config.SELECTED_DEEPGRAM_MODEL = config.SELECTABLE_DEEPGRAM_MODEL_LIST[0]
                        self.run(200, self.run_mapping["selected_deepgram_model"], config.SELECTED_DEEPGRAM_MODEL)
                        self.updateTranscriptionEngine()
                        response = {"status":200, "result":config.TRANSCRIPTION_AUTH_KEYS[engine]}
                else:
                    response = VRCTError.create_error_response(
                        ErrorCode.TRANSCRIPTION_API_AUTH_FAILED,
                        data=None
                    )
        except Exception as e:
            errorLogging()
            response = VRCTError.create_exception_error_response(
                e,
                data=None
            )
        if response["status"] == 400:
            self.delDeepgramAuthKey()
        return response

    def delDeepgramAuthKey(self, *args, **kwargs) -> dict:
        engine = "Deepgram"
        auth_keys = config.TRANSCRIPTION_AUTH_KEYS
        auth_keys[engine] = None
        config.TRANSCRIPTION_AUTH_KEYS = auth_keys
        config.SELECTABLE_DEEPGRAM_MODEL_LIST = []
        config.DEEPGRAM_MODEL_LANGUAGES = {}
        config.SELECTED_DEEPGRAM_MODEL = None
        self.run(200, self.run_mapping["selectable_deepgram_model_list"], config.SELECTABLE_DEEPGRAM_MODEL_LIST)
        self.run(200, self.run_mapping["selected_deepgram_model"], config.SELECTED_DEEPGRAM_MODEL)
        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS[engine] = False
        self.updateTranscriptionEngine()
        return {"status":200, "result":config.TRANSCRIPTION_AUTH_KEYS[engine]}



    def setDeepgramModel(self, data, *args, **kwargs) -> dict:
        printLog("Set Deepgram Model", data)
        data = str(data)
        if data in config.SELECTABLE_DEEPGRAM_MODEL_LIST:
            config.SELECTED_DEEPGRAM_MODEL = data
            # 対応言語はモデルごとに異なるため、Deepgramが現在選択中の
            # 文字起こしエンジンである場合のみ、表示中の言語リストと
            # 既存の言語選択への影響を反映する。
            if config.SELECTED_TRANSCRIPTION_ENGINE == "Deepgram":
                self.fallbackUnsupportedLanguagesForTranscriptionEngine("Deepgram")
                self.run(200, self.run_mapping["selectable_language_list"], model.getListLanguageAndCountry())
            return {"status":200, "result":config.SELECTED_DEEPGRAM_MODEL}
        return VRCTError.create_error_response(
            ErrorCode.MODEL_TRANSCRIPTION_INVALID,
            data=config.SELECTED_DEEPGRAM_MODEL
        )



    @staticmethod
    @_configValidationErrorResponse(ErrorCode.VALIDATION_CONFIG_VALUE_INVALID)
    def setSelectedReleaseChannel(data, *args, **kwargs) -> dict:
        config.SELECTED_RELEASE_CHANNEL = str(data)
        return {"status":200, "result":config.SELECTED_RELEASE_CHANNEL}

    @staticmethod
    def listAvailableReleases(*args, **kwargs) -> dict:
        releases = model.listAvailableReleases()
        return {"status":200, "result":[asdict(r) for r in releases]}


    @staticmethod
    def setEnableConvertMessageToRomaji(*args, **kwargs) -> dict:
        if config.CONVERT_MESSAGE_TO_ROMAJI is False:
            if config.CONVERT_MESSAGE_TO_HIRAGANA is False:
                model.startTransliteration()
            config.CONVERT_MESSAGE_TO_ROMAJI = True
        return {"status":200, "result":config.CONVERT_MESSAGE_TO_ROMAJI}

    @staticmethod
    def setDisableConvertMessageToRomaji(*args, **kwargs) -> dict:
        if config.CONVERT_MESSAGE_TO_ROMAJI is True:
            if config.CONVERT_MESSAGE_TO_HIRAGANA is False:
                model.stopTransliteration()
            config.CONVERT_MESSAGE_TO_ROMAJI = False
        return {"status":200, "result":config.CONVERT_MESSAGE_TO_ROMAJI}


    @staticmethod
    def setEnableConvertMessageToHiragana(*args, **kwargs) -> dict:
        if config.CONVERT_MESSAGE_TO_HIRAGANA is False:
            if config.CONVERT_MESSAGE_TO_ROMAJI is False:
                model.startTransliteration()
            config.CONVERT_MESSAGE_TO_HIRAGANA = True
        return {"status":200, "result":config.CONVERT_MESSAGE_TO_HIRAGANA}

    @staticmethod
    def setDisableConvertMessageToHiragana(*args, **kwargs) -> dict:
        if config.CONVERT_MESSAGE_TO_HIRAGANA is True:
            if config.CONVERT_MESSAGE_TO_ROMAJI is False:
                model.stopTransliteration()
            config.CONVERT_MESSAGE_TO_HIRAGANA = False
        return {"status":200, "result":config.CONVERT_MESSAGE_TO_HIRAGANA}


    @staticmethod
    def setEnableMainWindowSidebarCompactMode(*args, **kwargs) -> dict:
        if config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE is False:
            config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE = True
        return {"status":200, "result":config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE}

    @staticmethod
    def setDisableMainWindowSidebarCompactMode(*args, **kwargs) -> dict:
        if config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE is True:
            config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE = False
        return {"status":200, "result":config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE}


    @staticmethod
    def setTransparency(data, *args, **kwargs) -> dict:
        try:
            value = int(data)
        except Exception:
            return VRCTError.create_error_response(
                ErrorCode.GENERAL_EXCEPTION,
                data=config.TRANSPARENCY,
                custom_message="Transparency must be a number",
            )
        config.TRANSPARENCY = value
        return {"status":200, "result":config.TRANSPARENCY}


    @staticmethod
    def setUiScaling(data, *args, **kwargs) -> dict:
        try:
            value = int(data)
        except Exception:
            return VRCTError.create_error_response(
                ErrorCode.GENERAL_EXCEPTION,
                data=config.UI_SCALING,
                custom_message="UI scaling must be a number",
            )
        config.UI_SCALING = value
        return {"status":200, "result":config.UI_SCALING}


    @staticmethod
    def setTextboxUiScaling(data, *args, **kwargs) -> dict:
        try:
            value = int(data)
        except Exception:
            return VRCTError.create_error_response(
                ErrorCode.GENERAL_EXCEPTION,
                data=config.TEXTBOX_UI_SCALING,
                custom_message="Textbox UI scaling must be a number",
            )
        config.TEXTBOX_UI_SCALING = value
        return {"status":200, "result":config.TEXTBOX_UI_SCALING}


    @staticmethod
    @_configValidationErrorResponse(ErrorCode.VALIDATION_CONFIG_VALUE_INVALID)
    def setMessageBoxRatio(data, *args, **kwargs) -> dict:
        config.MESSAGE_BOX_RATIO = data
        return {"status":200, "result":config.MESSAGE_BOX_RATIO}


    @staticmethod
    @_configValidationErrorResponse(ErrorCode.VALIDATION_CONFIG_VALUE_INVALID)
    def setSendMessageButtonType(data, *args, **kwargs) -> dict:
        config.SEND_MESSAGE_BUTTON_TYPE = data
        return {"status":200, "result":config.SEND_MESSAGE_BUTTON_TYPE}


    @staticmethod
    def setEnableShowResendButton(*args, **kwargs) -> dict:
        if config.SHOW_RESEND_BUTTON is False:
            config.SHOW_RESEND_BUTTON = True
        return {"status":200, "result":config.SHOW_RESEND_BUTTON}

    @staticmethod
    def setDisableShowResendButton(*args, **kwargs) -> dict:
        if config.SHOW_RESEND_BUTTON is True:
            config.SHOW_RESEND_BUTTON = False
        return {"status":200, "result":config.SHOW_RESEND_BUTTON}


    @staticmethod
    @_configValidationErrorResponse(ErrorCode.VALIDATION_CONFIG_VALUE_INVALID)
    def setFontFamily(data, *args, **kwargs) -> dict:
        config.FONT_FAMILY = data
        return {"status":200, "result":config.FONT_FAMILY}


    @staticmethod
    @_configValidationErrorResponse(ErrorCode.VALIDATION_CONFIG_VALUE_INVALID)
    def setUiLanguage(data, *args, **kwargs) -> dict:
        config.UI_LANGUAGE = data
        return {"status":200, "result":config.UI_LANGUAGE}


    @staticmethod
    @_configValidationErrorResponse(ErrorCode.VALIDATION_CONFIG_VALUE_INVALID)
    def setMainWindowGeometry(data, *args, **kwargs) -> dict:
        config.MAIN_WINDOW_GEOMETRY = data
        return {"status":200, "result":config.MAIN_WINDOW_GEOMETRY}


    def applyAutoMicSelect(self) -> None:
        # stopAccessMicDevices/restartAccessMicDevices は mic_lifecycle_lock
        # を取得しつつ recorder の stop や PyAudio open を行う重い処理。
        # device_manager.monitoring() 自身のスレッドで直接実行すると、その間
        # monitoring が次の COM デバイス通知を取りこぼす。
        # model.mic_lifecycle_worker 経由で専用スレッドに投げることで
        # monitoring は即座に呼び出しから戻れる。Before/After は同じ worker の
        # FIFO キューで順序が保たれる。speaker 側とはワーカーを分けており
        # (フェーズ3項目21)、mic の重い処理が無関係な speaker 側の操作を
        # 足止めしない。
        device_manager.setCallbackProcessBeforeUpdateMicDevices(
            lambda: model.mic_lifecycle_worker.enqueue(self.stopAccessMicDevices)
        )
        device_manager.setCallbackDefaultMicDevice(self.updateSelectedMicDevice)
        device_manager.setCallbackProcessAfterUpdateMicDevices(
            lambda: model.mic_lifecycle_worker.enqueue(self.restartAccessMicDevices)
        )
        # マイクの Auto Select は OS 既定デバイス追従のみ。speaker と違い
        # ActiveEndpointTracker (peak 追従) は使わないため、endpoint 切替
        # 起点の Recorder 差し替え callback は登録しない
        # (device_manager.setMicAutoActive の docstring 参照。develop側の
        # 6596c629で撤去された経緯があり、フェーズ3項目21のcoalesce_key
        # 拡張はspeaker側の_reconfigureSpeakerDeviceLockedにのみ適用する)。
        device_manager.forceUpdateAndSetMicDevices()
        # monitoring スレッドの起動判断は DeviceManager 側に集約
        # (speaker 側の状態を controller で気にする必要はもう無い)
        device_manager.setMicAutoActive(True)

    def setEnableAutoMicSelect(self, *args, **kwargs) -> dict:
        if config.AUTO_MIC_SELECT is False:
            self.applyAutoMicSelect()
            config.AUTO_MIC_SELECT = True
        return {"status":200, "result":config.AUTO_MIC_SELECT}

    @staticmethod
    def setDisableAutoMicSelect(*args, **kwargs) -> dict:
        if config.AUTO_MIC_SELECT is True:
            device_manager.clearCallbackProcessBeforeUpdateMicDevices()
            device_manager.clearCallbackDefaultMicDevice()
            device_manager.clearCallbackProcessAfterUpdateMicDevices()
            # monitoring の停止判断は DeviceManager 側に委譲。
            # speaker 側が active なら monitoring は継続、両方 inactive で
            # 初めて thread が停止する。以前ここで AUTO_SPEAKER_SELECT を
            # 見てから stopMonitoring を叩いていた相互参照は不要になった。
            device_manager.setMicAutoActive(False)
            config.AUTO_MIC_SELECT = False
        return {"status":200, "result":config.AUTO_MIC_SELECT}


    def setSelectedMicHost(self, data, *args, **kwargs) -> dict:
        previously_selected_device = config.SELECTED_MIC_DEVICE
        config.SELECTED_MIC_HOST = data
        # Keep using the same physical device if it is also exposed under the
        # newly selected host (device names are often duplicated across host
        # APIs). Only fall back to the host's first device when the
        # previously selected one isn't available there, so switching hosts
        # doesn't silently swap the currently used device for an unrelated
        # "Default Device" entry.
        if previously_selected_device in model.getListMicDevice():
            config.SELECTED_MIC_DEVICE = previously_selected_device
        else:
            config.SELECTED_MIC_DEVICE = model.getMicDefaultDevice()
        self._reopenMicAudioOnDeviceChange()
        # host が切り替わると新ホストの selectable_mic_device_list を
        # UI に push しないと、ドロップダウンが旧ホストのデバイス名一覧の
        # ままになり、そこから選ばれた名前は新ホストの
        # _mic_device_validator で弾かれて config が更新されない
        # (setSelectedMicDevice が事実上 no-op になる)。selected_mic_device
        # と一緒に必ずリストも再送する。
        self.run(200, self.run_mapping["selectable_mic_device_list"], model.getListMicDevice())
        self.run(200, self.run_mapping["selected_mic_device"], config.SELECTED_MIC_DEVICE)
        return {"status":200, "result":config.SELECTED_MIC_HOST}


    def setSelectedMicDevice(self, data, *args, **kwargs) -> dict:
        config.SELECTED_MIC_DEVICE = data
        self._reopenMicAudioOnDeviceChange()
        return {"status":200, "result": config.SELECTED_MIC_DEVICE}

    def _reopenMicAudioOnDeviceChange(self) -> None:
        # デバイス切替時、稼働中のマイク Session を Session.reconfigure 経由で
        # 新デバイスに差し替える。旧実装は feature 単位で stop→start を 2 段
        # (transcription + energy) 呼んでいたため、両方 ON のときは Recorder が
        # 2 回 close/open されていた。Session に device 差分検知を入れた今は
        # 1 呼び出しで済み、config 上のデバイスと現在開いているデバイスが
        # 同じなら no-op になる。
        # config は呼び出し元 (setSelectedMicHost/Device) が既に書き換え済み。
        with self.mic_lifecycle_lock:
            model.reconfigureMicDevice()

    def _changeMicTranscriptStatusLocked(self) -> None:
        # OSC ミュート同期 (Model.changeHandlerMute) からのみ呼ばれる
        # (model.setMicMuteStatusChangeCallback 経由で __init__ が登録)。
        # 任意の OSC 受信スレッドで走るため、他の mic_lifecycle_lock
        # 保持経路 (start/stop 系, Auto Select のデバイス切替) と
        # 直列化されていなかった (壊れた Recorder への pause()/resume()
        # で TypeError になったり、resume() が新しい _audio_queue を drain
        # して録音済み音声を取りこぼす原因になっていた)。
        with self.mic_lifecycle_lock:
            model.changeMicTranscriptStatus()


    @staticmethod
    def setMicThreshold(data, *args, **kwargs) -> dict:
        try:
            data = int(data)
            if 0 <= data <= config.MAX_MIC_THRESHOLD:
                config.MIC_THRESHOLD = data
                status = 200
            else:
                raise ValueError()
        except Exception:
            response = VRCTError.create_error_response(
                ErrorCode.VALIDATION_MIC_THRESHOLD,
                data=config.MIC_THRESHOLD
            )
        else:
            response = {"status":status, "result":config.MIC_THRESHOLD}
        return response


    @staticmethod
    def setEnableMicAutomaticThreshold(*args, **kwargs) -> dict:
        if config.MIC_AUTOMATIC_THRESHOLD is False:
            config.MIC_AUTOMATIC_THRESHOLD = True
        return {"status":200, "result":config.MIC_AUTOMATIC_THRESHOLD}

    @staticmethod
    def setDisableMicAutomaticThreshold(*args, **kwargs) -> dict:
        if config.MIC_AUTOMATIC_THRESHOLD is True:
            config.MIC_AUTOMATIC_THRESHOLD = False
        return {"status":200, "result":config.MIC_AUTOMATIC_THRESHOLD}


    @staticmethod
    def setMicRecordTimeout(data, *args, **kwargs) -> dict:
        printLog("Set Mic Record Timeout", data)
        try:
            data = int(data)
            if 0 <= data <= config.MIC_PHRASE_TIMEOUT:
                config.MIC_RECORD_TIMEOUT = data
            else:
                raise ValueError()
        except Exception:
            response = VRCTError.create_error_response(
                ErrorCode.VALIDATION_MIC_RECORD_TIMEOUT,
                data=config.MIC_RECORD_TIMEOUT
            )
        else:
            response = {"status":200, "result":config.MIC_RECORD_TIMEOUT}
        return response


    @staticmethod
    def setMicPhraseTimeout(data, *args, **kwargs) -> dict:
        try:
            data = int(data)
            if data >= config.MIC_RECORD_TIMEOUT:
                config.MIC_PHRASE_TIMEOUT = data
            else:
                raise ValueError()
        except Exception:
            response = VRCTError.create_error_response(
                ErrorCode.VALIDATION_MIC_PHRASE_TIMEOUT,
                data=config.MIC_PHRASE_TIMEOUT
            )
        else:
            response = {"status":200, "result":config.MIC_PHRASE_TIMEOUT}
        return response


    @staticmethod
    def setMicMaxPhrases(data, *args, **kwargs) -> dict:
        try:
            data = int(data)
            if 0 <= data:
                config.MIC_MAX_PHRASES = data
            else:
                raise ValueError()
        except Exception:
            response = VRCTError.create_error_response(
                ErrorCode.VALIDATION_MIC_MAX_PHRASES,
                data=config.MIC_MAX_PHRASES
            )
        else:
            response = {"status":200, "result":config.MIC_MAX_PHRASES}
        return response


    @staticmethod
    def setMicWordFilter(data, *args, **kwargs) -> dict:
        config.MIC_WORD_FILTER = sorted(set(data), key=data.index)
        model.resetKeywordProcessor()
        model.addKeywords()
        return {"status":200, "result":config.MIC_WORD_FILTER}


    @staticmethod
    def setMicAvgLogprob(data, *args, **kwargs) -> dict:
        try:
            value = float(data)
        except Exception:
            return VRCTError.create_error_response(
                ErrorCode.GENERAL_EXCEPTION,
                data=config.MIC_AVG_LOGPROB,
                custom_message="Mic average logprob must be a number",
            )
        config.MIC_AVG_LOGPROB = value
        return {"status":200, "result":config.MIC_AVG_LOGPROB}


    @staticmethod
    def setMicNoSpeechProb(data, *args, **kwargs) -> dict:
        try:
            value = float(data)
        except Exception:
            return VRCTError.create_error_response(
                ErrorCode.GENERAL_EXCEPTION,
                data=config.MIC_NO_SPEECH_PROB,
                custom_message="Mic no-speech probability must be a number",
            )
        config.MIC_NO_SPEECH_PROB = value
        return {"status":200, "result":config.MIC_NO_SPEECH_PROB}


    def applyAutoSpeakerSelect(self) -> None:
        # 詳細は applyAutoMicSelect のコメント参照:
        # monitoring スレッドをブロックしないよう worker 経由で実行する。
        # mic とはワーカーを分けている (フェーズ3項目21)。
        device_manager.setCallbackProcessBeforeUpdateSpeakerDevices(
            lambda: model.speaker_lifecycle_worker.enqueue(self.stopAccessSpeakerDevices)
        )
        device_manager.setCallbackDefaultSpeakerDevice(self.updateSelectedSpeakerDevice)
        device_manager.setCallbackProcessAfterUpdateSpeakerDevices(
            lambda: model.speaker_lifecycle_worker.enqueue(self.restartAccessSpeakerDevices)
        )
        # 詳細は applyAutoMicSelect のコメント参照 (ActiveEndpointTracker 連携・coalesce_key)
        device_manager.setCallbackEndpointReconfiguredSpeaker(
            lambda: model.speaker_lifecycle_worker.enqueue(
                self._reconfigureSpeakerDeviceLocked, coalesce_key="speaker_reconfigure"
            )
        )
        device_manager.forceUpdateAndSetSpeakerDevices()
        device_manager.setSpeakerAutoActive(True)

    def setEnableAutoSpeakerSelect(self, *args, **kwargs) -> dict:
        if config.AUTO_SPEAKER_SELECT is False:
            self.applyAutoSpeakerSelect()
            config.AUTO_SPEAKER_SELECT = True
        return {"status":200, "result":config.AUTO_SPEAKER_SELECT}

    @staticmethod
    def setDisableAutoSpeakerSelect(*args, **kwargs) -> dict:
        if config.AUTO_SPEAKER_SELECT is True:
            device_manager.clearCallbackProcessBeforeUpdateSpeakerDevices()
            device_manager.clearCallbackDefaultSpeakerDevice()
            device_manager.clearCallbackProcessAfterUpdateSpeakerDevices()
            device_manager.clearCallbackEndpointReconfiguredSpeaker()
            # 詳細は setDisableAutoMicSelect のコメント参照:
            # monitoring の停止判断は DeviceManager 側に委譲。
            device_manager.setSpeakerAutoActive(False)
            config.AUTO_SPEAKER_SELECT = False
        return {"status":200, "result":config.AUTO_SPEAKER_SELECT}


    def setSelectedSpeakerDevice(self, data, *args, **kwargs) -> dict:
        config.SELECTED_SPEAKER_DEVICE = data
        self._reopenSpeakerAudioOnDeviceChange()
        return {"status":200, "result":config.SELECTED_SPEAKER_DEVICE}

    def _reopenSpeakerAudioOnDeviceChange(self) -> None:
        # マイクと同様、Session.reconfigure 1 回に縮退。詳細は
        # _reopenMicAudioOnDeviceChange のコメント参照。
        with self.speaker_lifecycle_lock:
            model.reconfigureSpeakerDevice()

    def _reconfigureSpeakerDeviceLocked(self) -> None:
        # ActiveEndpointTracker (render) からの通知
        # (setCallbackEndpointReconfiguredSpeaker) は他の speaker_lifecycle_lock
        # 保持経路 (start/stop 系) と直列化されていないため、ここで明示的に
        # ロックを取る。
        with self.speaker_lifecycle_lock:
            model.reconfigureSpeakerDevice()


    @staticmethod
    def setSpeakerThreshold(data, *args, **kwargs) -> dict:
        printLog("Set Speaker Energy Threshold", data)
        try:
            data = int(data)
            if 0 <= data <= config.MAX_SPEAKER_THRESHOLD:
                config.SPEAKER_THRESHOLD = data
            else:
                raise ValueError()
        except Exception:
            response = VRCTError.create_error_response(
                ErrorCode.VALIDATION_SPEAKER_THRESHOLD,
                data=config.SPEAKER_THRESHOLD
            )
        else:
            response = {"status":200, "result":config.SPEAKER_THRESHOLD}
        return response


    @staticmethod
    def setEnableSpeakerAutomaticThreshold(*args, **kwargs) -> dict:
        if config.SPEAKER_AUTOMATIC_THRESHOLD is False:
            config.SPEAKER_AUTOMATIC_THRESHOLD = True
        return {"status":200, "result":config.SPEAKER_AUTOMATIC_THRESHOLD}

    @staticmethod
    def setDisableSpeakerAutomaticThreshold(*args, **kwargs) -> dict:
        if config.SPEAKER_AUTOMATIC_THRESHOLD is True:
            config.SPEAKER_AUTOMATIC_THRESHOLD = False
        return {"status":200, "result":config.SPEAKER_AUTOMATIC_THRESHOLD}


    @staticmethod
    def setSpeakerRecordTimeout(data, *args, **kwargs) -> dict:
        try:
            data = int(data)
            if 0 <= data <= config.SPEAKER_PHRASE_TIMEOUT:
                config.SPEAKER_RECORD_TIMEOUT = data
            else:
                raise ValueError()
        except Exception:
            response = VRCTError.create_error_response(
                ErrorCode.VALIDATION_SPEAKER_RECORD_TIMEOUT,
                data=config.SPEAKER_RECORD_TIMEOUT
            )
        else:
            response = {"status":200, "result":config.SPEAKER_RECORD_TIMEOUT}
        return response


    @staticmethod
    def setSpeakerPhraseTimeout(data, *args, **kwargs) -> dict:
        try:
            data = int(data)
            if 0 <= data and data >= config.SPEAKER_RECORD_TIMEOUT:
                config.SPEAKER_PHRASE_TIMEOUT = data
            else:
                raise ValueError()
        except Exception:
            response = VRCTError.create_error_response(
                ErrorCode.VALIDATION_SPEAKER_PHRASE_TIMEOUT,
                data=config.SPEAKER_PHRASE_TIMEOUT
            )
        else:
            response = {"status":200, "result":config.SPEAKER_PHRASE_TIMEOUT}
        return response


    @staticmethod
    def setSpeakerMaxPhrases(data, *args, **kwargs) -> dict:
        printLog("Set Speaker Max Phrases", data)
        try:
            data = int(data)
            if 0 <= data:
                config.SPEAKER_MAX_PHRASES = data
            else:
                raise ValueError()
        except Exception:
            response = VRCTError.create_error_response(
                ErrorCode.VALIDATION_SPEAKER_MAX_PHRASES,
                data=config.SPEAKER_MAX_PHRASES
            )
        else:
            response = {"status":200, "result":config.SPEAKER_MAX_PHRASES}
        return response


    @staticmethod
    @_configValidationErrorResponse(ErrorCode.VALIDATION_CONFIG_VALUE_INVALID)
    def setHotkeys(data, *args, **kwargs) -> dict:
        config.HOTKEYS = data
        return {"status":200, "result":config.HOTKEYS}


    @staticmethod
    @_configValidationErrorResponse(ErrorCode.VALIDATION_CONFIG_VALUE_INVALID)
    def setPluginsStatus(data, *args, **kwargs) -> dict:
        config.PLUGINS_STATUS = data
        return {"status":200, "result":config.PLUGINS_STATUS}


    @staticmethod
    def setSpeakerAvgLogprob(data, *args, **kwargs) -> dict:
        try:
            value = float(data)
        except Exception:
            return VRCTError.create_error_response(
                ErrorCode.GENERAL_EXCEPTION,
                data=config.SPEAKER_AVG_LOGPROB,
                custom_message="Speaker average logprob must be a number",
            )
        config.SPEAKER_AVG_LOGPROB = value
        return {"status":200, "result":config.SPEAKER_AVG_LOGPROB}


    @staticmethod
    def setSpeakerNoSpeechProb(data, *args, **kwargs) -> dict:
        try:
            value = float(data)
        except Exception:
            return VRCTError.create_error_response(
                ErrorCode.GENERAL_EXCEPTION,
                data=config.SPEAKER_NO_SPEECH_PROB,
                custom_message="Speaker no-speech probability must be a number",
            )
        config.SPEAKER_NO_SPEECH_PROB = value
        return {"status":200, "result":config.SPEAKER_NO_SPEECH_PROB}


    def setOscIpAddress(self, data, *args, **kwargs) -> dict:
        if isValidIpAddress(data) is False:
            response = VRCTError.create_error_response(
                ErrorCode.VALIDATION_INVALID_IP,
                data=config.OSC_IP_ADDRESS
            )
        else:
            try:
                model.setOscIpAddress(data)
                config.OSC_IP_ADDRESS = data
                if model.getIsOscQueryEnabled() is True:
                    self.enableOscQuery()
                else:
                    mute_sync_info_flag = False
                    if config.VRC_MIC_MUTE_SYNC is True:
                        self.setDisableVrcMicMuteSync()
                        mute_sync_info_flag = True
                    self.disableOscQuery(mute_sync_info=mute_sync_info_flag)

                response = {"status":200, "result":config.OSC_IP_ADDRESS}
            except Exception:
                model.setOscIpAddress(config.OSC_IP_ADDRESS)
                response = VRCTError.create_error_response(
                    ErrorCode.VALIDATION_CANNOT_SET_IP,
                    data=config.OSC_IP_ADDRESS
                )
        return response


    @staticmethod
    def setOscPort(data, *args, **kwargs) -> dict:
        try:
            port = int(data)
        except Exception:
            return VRCTError.create_error_response(
                ErrorCode.VALIDATION_OSC_PORT_INVALID,
                data=config.OSC_PORT,
                custom_message="OSC port must be a number",
            )
        config.OSC_PORT = port
        model.setOscPort(config.OSC_PORT)
        return {"status":200, "result":config.OSC_PORT}


    @staticmethod
    def setEnableNotificationVrcSfx(*args, **kwargs) -> dict:
        if config.NOTIFICATION_VRC_SFX is False:
            config.NOTIFICATION_VRC_SFX = True
        return {"status":200, "result":config.NOTIFICATION_VRC_SFX}

    @staticmethod
    def setDisableNotificationVrcSfx(*args, **kwargs) -> dict:
        if config.NOTIFICATION_VRC_SFX is True:
            config.NOTIFICATION_VRC_SFX = False
        return {"status":200, "result":config.NOTIFICATION_VRC_SFX}

    # --- フェーズ3項目17: 翻訳エンジンレジストリ (TRANSLATION_PROVIDER_REGISTRY
    # =認証キー型、CONNECTION_PROVIDER_REGISTRY=疎通確認型) 向け共通CRUD実装。
    # エンジン固有の get/set/delXAuthKey・getXModelList・get/setXModel・
    # checkXConnection は全てこれらへの1行委譲になる
    # (詳細は translation_providers.py 参照)。

    def _resolveEngineSpec(self, engine_key: str):
        """`engine_key` がどちらのレジストリに属していても対応するスペックを返す。

        `_getTranslationEngineModelList` 等モデル管理系の3メソッドは
        `selectable_model_list_attr`/`selected_model_attr`/`error_model_invalid`
        という共通フィールド名だけを使うため、どちらのレジストリのスペックでも
        区別せず動く。
        """
        if engine_key in TRANSLATION_PROVIDER_REGISTRY:
            return TRANSLATION_PROVIDER_REGISTRY[engine_key]
        return CONNECTION_PROVIDER_REGISTRY[engine_key]

    def _getTranslationEngineAuthKey(self, engine_key: str) -> dict:
        return {"status":200, "result":config.AUTH_KEYS[engine_key]}

    def _setTranslationEngineAuthKey(self, engine_key: str, data) -> dict:
        spec = TRANSLATION_PROVIDER_REGISTRY[engine_key]
        bindings = _ENGINE_MODEL_BINDINGS[engine_key]
        display_name = engine_key[:-len("_API")] if engine_key.endswith("_API") else engine_key
        printLog(f"Set {display_name} Auth Key")
        try:
            data = str(data)
            if spec.auth_validate(data):
                result = getattr(model, bindings["authenticate"])(auth_key=data)
                if result is True:
                    auth_keys = config.AUTH_KEYS
                    auth_keys[engine_key] = data
                    config.AUTH_KEYS = auth_keys
                    config.SELECTABLE_TRANSLATION_ENGINE_STATUS[engine_key] = True
                    model_list = getattr(model, bindings["get_model_list"])()
                    setattr(config, spec.selectable_model_list_attr, model_list)
                    self.run(200, self.run_mapping[spec.run_mapping_selectable_key], model_list)
                    if getattr(config, spec.selected_model_attr) not in model_list:
                        setattr(config, spec.selected_model_attr, model_list[0])
                    getattr(model, bindings["set_model"])(model=getattr(config, spec.selected_model_attr))
                    self.run(200, self.run_mapping[spec.run_mapping_selected_key], getattr(config, spec.selected_model_attr))
                    getattr(model, bindings["update_client"])()
                    self.updateTranslationEngineAndEngineList()
                    response = {"status":200, "result":config.AUTH_KEYS[engine_key]}
                else:
                    response = VRCTError.create_error_response(
                        spec.error_auth_failed,
                        data=None
                    )
            else:
                response = VRCTError.create_error_response(
                    spec.error_auth_invalid,
                    data=None
                )
        except Exception as e:
            errorLogging()
            response = VRCTError.create_exception_error_response(
                e,
                data=None
            )
        if response["status"] == 400:
            self._delTranslationEngineAuthKey(engine_key)
        return response

    def _delTranslationEngineAuthKey(self, engine_key: str) -> dict:
        spec = TRANSLATION_PROVIDER_REGISTRY[engine_key]
        auth_keys = config.AUTH_KEYS
        auth_keys[engine_key] = None
        config.AUTH_KEYS = auth_keys
        setattr(config, spec.selectable_model_list_attr, [])
        setattr(config, spec.selected_model_attr, None)
        self.run(200, self.run_mapping[spec.run_mapping_selectable_key], getattr(config, spec.selectable_model_list_attr))
        self.run(200, self.run_mapping[spec.run_mapping_selected_key], getattr(config, spec.selected_model_attr))
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS[engine_key] = False
        self.updateTranslationEngineAndEngineList()
        return {"status":200, "result":config.AUTH_KEYS[engine_key]}

    def _getTranslationEngineModelList(self, engine_key: str) -> dict:
        spec = self._resolveEngineSpec(engine_key)
        return {"status":200, "result": getattr(config, spec.selectable_model_list_attr)}

    def _getTranslationEngineModel(self, engine_key: str) -> dict:
        spec = self._resolveEngineSpec(engine_key)
        return {"status":200, "result":getattr(config, spec.selected_model_attr)}

    def _setTranslationEngineModel(self, engine_key: str, data) -> dict:
        spec = self._resolveEngineSpec(engine_key)
        bindings = _ENGINE_MODEL_BINDINGS[engine_key]
        display_name = engine_key[:-len("_API")] if engine_key.endswith("_API") else engine_key
        printLog(f"Set {display_name} Model", data)
        try:
            data = str(data)
            result = getattr(model, bindings["set_model"])(model=data)
            if result is True:
                setattr(config, spec.selected_model_attr, data)
                getattr(model, bindings["set_model"])(model=getattr(config, spec.selected_model_attr))
                getattr(model, bindings["update_client"])()
                response = {"status":200, "result":getattr(config, spec.selected_model_attr)}
            else:
                response = VRCTError.create_error_response(
                    spec.error_model_invalid,
                    data=getattr(config, spec.selected_model_attr)
                )
        except Exception as e:
            errorLogging()
            response = VRCTError.create_exception_error_response(
                e,
                data=getattr(config, spec.selected_model_attr)
            )
        return response

    def _checkTranslationEngineConnection(self, engine_key: str, connect_kwargs: dict) -> dict:
        """CONNECTION_PROVIDER_REGISTRY 登録エンジン (LMStudio/Ollama) 共通の
        疎通確認処理。`connect_kwargs` は接続呼び出しに渡す追加引数
        (LMStudio: `{"base_url": config.LMSTUDIO_URL}`、Ollama: `{}`)。

        NOTE: 接続には成功したがモデル一覧が空だった場合、既存実装を
        そのまま踏襲して `raise Exception(...)` で下の except に処理させている
        (専用のエラーコードではなく GENERAL_EXCEPTION 応答になる、既存の
        LMStudio/Ollama の挙動と同じ)。
        """
        spec = CONNECTION_PROVIDER_REGISTRY[engine_key]
        bindings = _ENGINE_MODEL_BINDINGS[engine_key]
        printLog(f"Check Translator {engine_key} Connection")
        try:
            result = getattr(model, bindings["authenticate"])(**connect_kwargs)
            if result is True:
                config.SELECTABLE_TRANSLATION_ENGINE_STATUS[engine_key] = True
                model_list = getattr(model, bindings["get_model_list"])()
                setattr(config, spec.selectable_model_list_attr, model_list)
                self.run(200, self.run_mapping[spec.run_mapping_selectable_key], model_list)
                if len(model_list) == 0:
                    raise Exception(f"No {engine_key} models available")
                if getattr(config, spec.selected_model_attr) not in model_list:
                    setattr(config, spec.selected_model_attr, model_list[0])
                getattr(model, bindings["set_model"])(model=getattr(config, spec.selected_model_attr))
                self.run(200, self.run_mapping[spec.run_mapping_selected_key], getattr(config, spec.selected_model_attr))
                getattr(model, bindings["update_client"])()
                self.updateTranslationEngineAndEngineList()
                response = {"status":200, "result":True}
            else:
                config.SELECTABLE_TRANSLATION_ENGINE_STATUS[engine_key] = False
                setattr(config, spec.selectable_model_list_attr, [])
                setattr(config, spec.selected_model_attr, None)
                self.run(200, self.run_mapping[spec.run_mapping_selectable_key], getattr(config, spec.selectable_model_list_attr))
                self.run(200, self.run_mapping[spec.run_mapping_selected_key], getattr(config, spec.selected_model_attr))
                self.updateTranslationEngineAndEngineList()
                response = VRCTError.create_error_response(
                    spec.error_connection_failed,
                    data=False
                )
        except Exception as e:
            errorLogging()
            config.SELECTABLE_TRANSLATION_ENGINE_STATUS[engine_key] = False
            setattr(config, spec.selectable_model_list_attr, [])
            setattr(config, spec.selected_model_attr, None)
            self.run(200, self.run_mapping[spec.run_mapping_selectable_key], getattr(config, spec.selectable_model_list_attr))
            self.run(200, self.run_mapping[spec.run_mapping_selected_key], getattr(config, spec.selected_model_attr))
            self.updateTranslationEngineAndEngineList()
            response = VRCTError.create_exception_error_response(
                e,
                data=False
            )
        return response

    @staticmethod
    def getDeepLAuthKey(*args, **kwargs) -> dict:
        return {"status":200, "result":config.AUTH_KEYS["DeepL_API"]}

    def setDeeplAuthKey(self, data, *args, **kwargs) -> dict:
        printLog("Set DeepL Auth Key")
        translator_name = "DeepL_API"
        try:
            data = str(data)
            if len(data) == 36 or len(data) == 39:
                result = model.authenticationTranslatorDeepLAuthKey(auth_key=data)
                if result is True:
                    key = data
                    auth_keys = config.AUTH_KEYS
                    auth_keys[translator_name] = key
                    config.AUTH_KEYS = auth_keys
                    config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = True
                    self.updateTranslationEngineAndEngineList()
                    response = {"status":200, "result":config.AUTH_KEYS[translator_name]}
                else:
                    response = VRCTError.create_error_response(
                        ErrorCode.AUTH_DEEPL_FAILED,
                        data=config.AUTH_KEYS[translator_name]
                    )
            else:
                response = VRCTError.create_error_response(
                    ErrorCode.AUTH_DEEPL_LENGTH,
                    data=config.AUTH_KEYS[translator_name]
                )
        except Exception as e:
            errorLogging()
            response = VRCTError.create_exception_error_response(
                e,
                data=config.AUTH_KEYS[translator_name]
            )
        return response

    def delDeeplAuthKey(self, *args, **kwargs) -> dict:
        translator_name = "DeepL_API"
        auth_keys = config.AUTH_KEYS
        auth_keys[translator_name] = None
        config.AUTH_KEYS = auth_keys
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = False
        self.updateTranslationEngineAndEngineList()
        return {"status":200, "result":config.AUTH_KEYS[translator_name]}

    def getPlamoAuthKey(self, *args, **kwargs) -> dict:
        return self._getTranslationEngineAuthKey("Plamo_API")

    def setPlamoAuthKey(self, data, *args, **kwargs) -> dict:
        return self._setTranslationEngineAuthKey("Plamo_API", data)

    def delPlamoAuthKey(self, *args, **kwargs) -> dict:
        return self._delTranslationEngineAuthKey("Plamo_API")

    def getPlamoModelList(self, *args, **kwargs) -> dict:
        return self._getTranslationEngineModelList("Plamo_API")

    def getPlamoModel(self, *args, **kwargs) -> dict:
        return self._getTranslationEngineModel("Plamo_API")

    def setPlamoModel(self, data, *args, **kwargs) -> dict:
        return self._setTranslationEngineModel("Plamo_API", data)

    def getGeminiAuthKey(self, *args, **kwargs) -> dict:
        return self._getTranslationEngineAuthKey("Gemini_API")

    def setGeminiAuthKey(self, data, *args, **kwargs) -> dict:
        return self._setTranslationEngineAuthKey("Gemini_API", data)

    def delGeminiAuthKey(self, *args, **kwargs) -> dict:
        return self._delTranslationEngineAuthKey("Gemini_API")

    def getGeminiModelList(self, *args, **kwargs) -> dict:
        return self._getTranslationEngineModelList("Gemini_API")

    def getGeminiModel(self, *args, **kwargs) -> dict:
        return self._getTranslationEngineModel("Gemini_API")

    def setGeminiModel(self, data, *args, **kwargs) -> dict:
        return self._setTranslationEngineModel("Gemini_API", data)

    def getOpenAIAuthKey(self, *args, **kwargs) -> dict:
        return self._getTranslationEngineAuthKey("OpenAI_API")

    def setOpenAIAuthKey(self, data, *args, **kwargs) -> dict:
        return self._setTranslationEngineAuthKey("OpenAI_API", data)

    def delOpenAIAuthKey(self, *args, **kwargs) -> dict:
        return self._delTranslationEngineAuthKey("OpenAI_API")

    def getOpenAIModelList(self, *args, **kwargs) -> dict:
        return self._getTranslationEngineModelList("OpenAI_API")

    def getOpenAIModel(self, *args, **kwargs) -> dict:
        return self._getTranslationEngineModel("OpenAI_API")

    def setOpenAIModel(self, data, *args, **kwargs) -> dict:
        return self._setTranslationEngineModel("OpenAI_API", data)

    def getGroqAuthKey(self, *args, **kwargs) -> dict:
        return self._getTranslationEngineAuthKey("Groq_API")

    def setGroqAuthKey(self, data, *args, **kwargs) -> dict:
        return self._setTranslationEngineAuthKey("Groq_API", data)

    def delGroqAuthKey(self, *args, **kwargs) -> dict:
        return self._delTranslationEngineAuthKey("Groq_API")

    def getGroqModelList(self, *args, **kwargs) -> dict:
        return self._getTranslationEngineModelList("Groq_API")

    def getGroqModel(self, *args, **kwargs) -> dict:
        return self._getTranslationEngineModel("Groq_API")

    def setGroqModel(self, data, *args, **kwargs) -> dict:
        return self._setTranslationEngineModel("Groq_API", data)

    def getOpenRouterAuthKey(self, *args, **kwargs) -> dict:
        return self._getTranslationEngineAuthKey("OpenRouter_API")

    def setOpenRouterAuthKey(self, data, *args, **kwargs) -> dict:
        return self._setTranslationEngineAuthKey("OpenRouter_API", data)

    def delOpenRouterAuthKey(self, *args, **kwargs) -> dict:
        return self._delTranslationEngineAuthKey("OpenRouter_API")

    def getOpenRouterModelList(self, *args, **kwargs) -> dict:
        return self._getTranslationEngineModelList("OpenRouter_API")

    def getOpenRouterModel(self, *args, **kwargs) -> dict:
        return self._getTranslationEngineModel("OpenRouter_API")

    def setOpenRouterModel(self, data, *args, **kwargs) -> dict:
        return self._setTranslationEngineModel("OpenRouter_API", data)

    def getTranslatorLMStudioConnection(self, *args, **kwargs) -> dict:
        return {"status":200, "result":model.getTranslatorLMStudioConnected()}

    def checkTranslatorLMStudioConnection(self, *args, **kwargs) -> dict:
        return self._checkTranslationEngineConnection("LMStudio", connect_kwargs={"base_url": config.LMSTUDIO_URL})


    def setTranslatorLMStudioURL(self, data, *args, **kwargs) -> dict:
        printLog("Set Translator LMStudio URL", data)
        translator_name = "LMStudio"
        try:
            data = str(data)
            result = model.authenticationTranslatorLMStudio(base_url=data)
            if result is True:
                config.LMSTUDIO_URL = data
                config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = True
                config.SELECTABLE_LMSTUDIO_MODEL_LIST = model.getTranslatorLMStudioModelList()
                self.run(200, self.run_mapping["selectable_lmstudio_model_list"], config.SELECTABLE_LMSTUDIO_MODEL_LIST)
                if len(config.SELECTABLE_LMSTUDIO_MODEL_LIST) == 0:
                    raise Exception("No LMStudio models available")
                if config.SELECTED_LMSTUDIO_MODEL not in config.SELECTABLE_LMSTUDIO_MODEL_LIST:
                    config.SELECTED_LMSTUDIO_MODEL = config.SELECTABLE_LMSTUDIO_MODEL_LIST[0]
                model.setTranslatorLMStudioModel(model=config.SELECTED_LMSTUDIO_MODEL)
                self.run(200, self.run_mapping["selected_lmstudio_model"], config.SELECTED_LMSTUDIO_MODEL)
                model.updateTranslatorLMStudioClient()
                self.updateTranslationEngineAndEngineList()
                response = {"status":200, "result":config.LMSTUDIO_URL}
            else:
                config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = False
                config.SELECTABLE_LMSTUDIO_MODEL_LIST = []
                config.SELECTED_LMSTUDIO_MODEL = None
                self.run(200, self.run_mapping["selectable_lmstudio_model_list"], config.SELECTABLE_LMSTUDIO_MODEL_LIST)
                self.run(200, self.run_mapping["selected_lmstudio_model"], config.SELECTED_LMSTUDIO_MODEL)
                self.updateTranslationEngineAndEngineList()
                response = VRCTError.create_error_response(
                    ErrorCode.CONNECTION_LMSTUDIO_URL_INVALID,
                    data=config.LMSTUDIO_URL
                )
        except Exception as e:
            errorLogging()
            config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = False
            config.SELECTABLE_LMSTUDIO_MODEL_LIST = []
            config.SELECTED_LMSTUDIO_MODEL = None
            self.run(200, self.run_mapping["selectable_lmstudio_model_list"], config.SELECTABLE_LMSTUDIO_MODEL_LIST)
            self.run(200, self.run_mapping["selected_lmstudio_model"], config.SELECTED_LMSTUDIO_MODEL)
            self.updateTranslationEngineAndEngineList()
            response = VRCTError.create_exception_error_response(
                e,
                data=config.LMSTUDIO_URL
            )
        return response

    def getTranslatorLMStudioModelList(self, *args, **kwargs) -> dict:
        # 認証キー型5エンジンの getXModelList と異なり、ここは config の
        # キャッシュ値ではなく model 経由でクライアントに都度問い合わせる
        # (ローカルサーバーでモデルが動的に増減しうる LMStudio/Ollama 固有の
        # 設計) ため、_getTranslationEngineModelList には委譲せず既存の実装の
        # まま残す。
        model_list = model.getTranslatorLMStudioModelList()
        return {"status":200, "result": model_list}

    def getTranslatorLMStudioModel(self, *args, **kwargs) -> dict:
        return self._getTranslationEngineModel("LMStudio")

    def setTranslatorLMStudioModel(self, data, *args, **kwargs) -> dict:
        return self._setTranslationEngineModel("LMStudio", data)

    # ------------------------------------------------------------------
    # OpenAI-compatible endpoint (URL + Auth Key)
    # ------------------------------------------------------------------
    @staticmethod
    def getOpenAICompatibleAuthKey(*args, **kwargs) -> dict:
        return {"status":200, "result":config.AUTH_KEYS["OpenAI_Compatible"]}

    def setOpenAICompatibleAuthKey(self, data, *args, **kwargs) -> dict:
        printLog("Set OpenAI Compatible Auth Key")
        translator_name = "OpenAI_Compatible"
        try:
            data = str(data).strip()
            if len(data) == 0:
                response = VRCTError.create_error_response(
                    ErrorCode.AUTH_OPENAI_COMPATIBLE_INVALID,
                    data=None
                )
            else:
                result = model.authenticationTranslatorOpenAICompatibleAuthKey(
                    auth_key=data,
                    base_url=config.OPENAI_COMPATIBLE_URL,
                )
                if result is True:
                    model_list = model.getTranslatorOpenAICompatibleModelList()
                    if len(model_list) == 0:
                        response = VRCTError.create_error_response(
                            ErrorCode.AUTH_OPENAI_COMPATIBLE_FAILED,
                            data=None
                        )
                    else:
                        auth_keys = config.AUTH_KEYS
                        auth_keys[translator_name] = data
                        config.AUTH_KEYS = auth_keys
                        config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = True
                        config.SELECTABLE_OPENAI_COMPATIBLE_MODEL_LIST = model_list
                        self.run(200, self.run_mapping["selectable_openai_compatible_model_list"], config.SELECTABLE_OPENAI_COMPATIBLE_MODEL_LIST)
                        if config.SELECTED_OPENAI_COMPATIBLE_MODEL not in config.SELECTABLE_OPENAI_COMPATIBLE_MODEL_LIST:
                            config.SELECTED_OPENAI_COMPATIBLE_MODEL = config.SELECTABLE_OPENAI_COMPATIBLE_MODEL_LIST[0]
                        model.setTranslatorOpenAICompatibleModel(model=config.SELECTED_OPENAI_COMPATIBLE_MODEL)
                        self.run(200, self.run_mapping["selected_openai_compatible_model"], config.SELECTED_OPENAI_COMPATIBLE_MODEL)
                        model.updateTranslatorOpenAICompatibleClient()
                        self.updateTranslationEngineAndEngineList()
                        response = {"status":200, "result":config.AUTH_KEYS[translator_name]}
                else:
                    response = VRCTError.create_error_response(
                        ErrorCode.AUTH_OPENAI_COMPATIBLE_FAILED,
                        data=None
                    )
        except Exception as e:
            errorLogging()
            response = VRCTError.create_exception_error_response(
                e,
                data=None
            )
        if response["status"] == 400:
            self.delOpenAICompatibleAuthKey()
        return response

    def delOpenAICompatibleAuthKey(self, *args, **kwargs) -> dict:
        translator_name = "OpenAI_Compatible"
        auth_keys = config.AUTH_KEYS
        auth_keys[translator_name] = None
        config.AUTH_KEYS = auth_keys
        config.SELECTABLE_OPENAI_COMPATIBLE_MODEL_LIST = []
        config.SELECTED_OPENAI_COMPATIBLE_MODEL = None
        self.run(200, self.run_mapping["selectable_openai_compatible_model_list"], config.SELECTABLE_OPENAI_COMPATIBLE_MODEL_LIST)
        self.run(200, self.run_mapping["selected_openai_compatible_model"], config.SELECTED_OPENAI_COMPATIBLE_MODEL)
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = False
        self.updateTranslationEngineAndEngineList()
        return {"status":200, "result":config.AUTH_KEYS[translator_name]}


    def setOpenAICompatibleURL(self, data, *args, **kwargs) -> dict:
        """URL 変更時は「認証成功後に URL を確定」する順序を守る。

        Auth Key が未設定の場合は URL だけ保存して終わる（次回 Auth Key 入力時に検証される）。
        """
        printLog("Set OpenAI Compatible URL", data)
        translator_name = "OpenAI_Compatible"
        try:
            data = str(data).strip()
            if len(data) == 0:
                data = "https://api.openai.com/v1"

            auth_key = config.AUTH_KEYS[translator_name]

            if not auth_key:
                # Auth Key 未設定：URL のみ更新して終了
                config.OPENAI_COMPATIBLE_URL = data
                return {"status":200, "result":config.OPENAI_COMPATIBLE_URL}

            result = model.authenticationTranslatorOpenAICompatibleAuthKey(
                auth_key=auth_key,
                base_url=data,
            )
            if result is True:
                model_list = model.getTranslatorOpenAICompatibleModelList()
                if len(model_list) == 0:
                    # URL は疎通したが翻訳可能モデルが 0 件
                    config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = False
                    config.SELECTABLE_OPENAI_COMPATIBLE_MODEL_LIST = []
                    config.SELECTED_OPENAI_COMPATIBLE_MODEL = None
                    self.run(200, self.run_mapping["selectable_openai_compatible_model_list"], config.SELECTABLE_OPENAI_COMPATIBLE_MODEL_LIST)
                    self.run(200, self.run_mapping["selected_openai_compatible_model"], config.SELECTED_OPENAI_COMPATIBLE_MODEL)
                    self.updateTranslationEngineAndEngineList()
                    response = VRCTError.create_error_response(
                        ErrorCode.AUTH_OPENAI_COMPATIBLE_FAILED,
                        data=config.OPENAI_COMPATIBLE_URL
                    )
                else:
                    config.OPENAI_COMPATIBLE_URL = data
                    config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = True
                    config.SELECTABLE_OPENAI_COMPATIBLE_MODEL_LIST = model_list
                    self.run(200, self.run_mapping["selectable_openai_compatible_model_list"], config.SELECTABLE_OPENAI_COMPATIBLE_MODEL_LIST)
                    if config.SELECTED_OPENAI_COMPATIBLE_MODEL not in config.SELECTABLE_OPENAI_COMPATIBLE_MODEL_LIST:
                        config.SELECTED_OPENAI_COMPATIBLE_MODEL = config.SELECTABLE_OPENAI_COMPATIBLE_MODEL_LIST[0]
                    model.setTranslatorOpenAICompatibleModel(model=config.SELECTED_OPENAI_COMPATIBLE_MODEL)
                    self.run(200, self.run_mapping["selected_openai_compatible_model"], config.SELECTED_OPENAI_COMPATIBLE_MODEL)
                    model.updateTranslatorOpenAICompatibleClient()
                    self.updateTranslationEngineAndEngineList()
                    response = {"status":200, "result":config.OPENAI_COMPATIBLE_URL}
            else:
                config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = False
                config.SELECTABLE_OPENAI_COMPATIBLE_MODEL_LIST = []
                config.SELECTED_OPENAI_COMPATIBLE_MODEL = None
                self.run(200, self.run_mapping["selectable_openai_compatible_model_list"], config.SELECTABLE_OPENAI_COMPATIBLE_MODEL_LIST)
                self.run(200, self.run_mapping["selected_openai_compatible_model"], config.SELECTED_OPENAI_COMPATIBLE_MODEL)
                self.updateTranslationEngineAndEngineList()
                response = VRCTError.create_error_response(
                    ErrorCode.CONNECTION_OPENAI_COMPATIBLE_URL_INVALID,
                    data=config.OPENAI_COMPATIBLE_URL
                )
        except Exception as e:
            errorLogging()
            response = VRCTError.create_exception_error_response(
                e,
                data=config.OPENAI_COMPATIBLE_URL
            )
        return response



    def setOpenAICompatibleModel(self, data, *args, **kwargs) -> dict:
        printLog("Set OpenAI Compatible Model", data)
        try:
            data = str(data)
            result = model.setTranslatorOpenAICompatibleModel(model=data)
            if result is True:
                config.SELECTED_OPENAI_COMPATIBLE_MODEL = data
                model.setTranslatorOpenAICompatibleModel(model=config.SELECTED_OPENAI_COMPATIBLE_MODEL)
                model.updateTranslatorOpenAICompatibleClient()
                response = {"status":200, "result":config.SELECTED_OPENAI_COMPATIBLE_MODEL}
            else:
                response = VRCTError.create_error_response(
                    ErrorCode.MODEL_OPENAI_COMPATIBLE_INVALID,
                    data=config.SELECTED_OPENAI_COMPATIBLE_MODEL
                )
        except Exception as e:
            errorLogging()
            response = VRCTError.create_exception_error_response(
                e,
                data=config.SELECTED_OPENAI_COMPATIBLE_MODEL
            )
        return response

    def getTranslatorOllamaConnection(self, *args, **kwargs) -> dict:
        return {"status":200, "result":model.getTranslatorOllamaConnected()}

    def checkTranslatorOllamaConnection(self, *args, **kwargs) -> dict:
        return self._checkTranslationEngineConnection("Ollama", connect_kwargs={})

    def getTranslatorOllamaModelList(self, *args, **kwargs) -> dict:
        model_list = model.getTranslatorOllamaModelList()
        return {"status":200, "result": model_list}

    def getTranslatorOllamaModel(self, *args, **kwargs) -> dict:
        return self._getTranslationEngineModel("Ollama")

    def setTranslatorOllamaModel(self, data, *args, **kwargs) -> dict:
        return self._setTranslationEngineModel("Ollama", data)


    @staticmethod
    def setCtranslate2WeightType(data, *args, **kwargs) -> dict:
        config.CTRANSLATE2_WEIGHT_TYPE = str(data)
        model.setChangedTranslatorParameters(True)
        return {"status":200, "result":config.CTRANSLATE2_WEIGHT_TYPE}


    @staticmethod
    def setSelectedTranslationComputeType(data, *args, **kwargs) -> dict:
        config.SELECTED_TRANSLATION_COMPUTE_TYPE = str(data)
        model.setChangedTranslatorParameters(True)
        return {"status":200, "result":config.SELECTED_TRANSLATION_COMPUTE_TYPE}


    @staticmethod
    @_configValidationErrorResponse(ErrorCode.VALIDATION_CONFIG_VALUE_INVALID)
    def setWhisperWeightType(data, *args, **kwargs) -> dict:
        config.WHISPER_WEIGHT_TYPE = str(data)
        return {"status":200, "result": config.WHISPER_WEIGHT_TYPE}


    @staticmethod
    @_configValidationErrorResponse(ErrorCode.VALIDATION_CONFIG_VALUE_INVALID)
    def setSelectedTranscriptionComputeType(data, *args, **kwargs) -> dict:
        config.SELECTED_TRANSCRIPTION_COMPUTE_TYPE = str(data)
        return {"status":200, "result":config.SELECTED_TRANSCRIPTION_COMPUTE_TYPE}


    @staticmethod
    @_configValidationErrorResponse(ErrorCode.VALIDATION_CONFIG_VALUE_INVALID)
    def setSendMessageFormatParts(data, *args, **kwargs) -> dict:
        config.SEND_MESSAGE_FORMAT_PARTS = dict(data)
        return {"status":200, "result":config.SEND_MESSAGE_FORMAT_PARTS}


    @staticmethod
    @_configValidationErrorResponse(ErrorCode.VALIDATION_CONFIG_VALUE_INVALID)
    def setReceivedMessageFormatParts(data, *args, **kwargs) -> dict:
        config.RECEIVED_MESSAGE_FORMAT_PARTS = dict(data)
        return {"status":200, "result":config.RECEIVED_MESSAGE_FORMAT_PARTS}


    @staticmethod
    def setEnableAutoClearMessageBox(*args, **kwargs) -> dict:
        if config.AUTO_CLEAR_MESSAGE_BOX is False:
            config.AUTO_CLEAR_MESSAGE_BOX = True
        return {"status":200, "result":config.AUTO_CLEAR_MESSAGE_BOX}

    @staticmethod
    def setDisableAutoClearMessageBox(*args, **kwargs) -> dict:
        if config.AUTO_CLEAR_MESSAGE_BOX is True:
            config.AUTO_CLEAR_MESSAGE_BOX = False
        return {"status":200, "result":config.AUTO_CLEAR_MESSAGE_BOX}


    @staticmethod
    def setEnableSendOnlyTranslatedMessages(*args, **kwargs) -> dict:
        if config.SEND_ONLY_TRANSLATED_MESSAGES is False:
            config.SEND_ONLY_TRANSLATED_MESSAGES = True
        return {"status":200, "result":config.SEND_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def setDisableSendOnlyTranslatedMessages(*args, **kwargs) -> dict:
        if config.SEND_ONLY_TRANSLATED_MESSAGES is True:
            config.SEND_ONLY_TRANSLATED_MESSAGES = False
        return {"status":200, "result":config.SEND_ONLY_TRANSLATED_MESSAGES}


    @staticmethod
    def setEnableOverlaySmallLog(*args, **kwargs) -> dict:
        if config.OVERLAY_SMALL_LOG is False:
            if config.OVERLAY_LARGE_LOG is False:
                model.startOverlay()
            config.OVERLAY_SMALL_LOG = True
        return {"status":200, "result":config.OVERLAY_SMALL_LOG}

    @staticmethod
    def setDisableOverlaySmallLog(*args, **kwargs) -> dict:
        if config.OVERLAY_SMALL_LOG is True:
            model.clearOverlayImageSmallLog()
            if config.OVERLAY_LARGE_LOG is False:
                model.shutdownOverlay()
            config.OVERLAY_SMALL_LOG = False
        return {"status":200, "result":config.OVERLAY_SMALL_LOG}


    @staticmethod
    def setOverlaySmallLogSettings(data, *args, **kwargs) -> dict:
        config.OVERLAY_SMALL_LOG_SETTINGS = data
        model.updateOverlaySmallLogSettings()
        return {"status":200, "result":config.OVERLAY_SMALL_LOG_SETTINGS}


    @staticmethod
    def setEnableOverlayLargeLog(*args, **kwargs) -> dict:
        if config.OVERLAY_LARGE_LOG is False:
            if config.OVERLAY_SMALL_LOG is False:
                model.startOverlay()
            config.OVERLAY_LARGE_LOG = True
        return {"status":200, "result":config.OVERLAY_LARGE_LOG}

    @staticmethod
    def setDisableOverlayLargeLog(*args, **kwargs) -> dict:
        if config.OVERLAY_LARGE_LOG is True:
            model.clearOverlayImageLargeLog()
            if config.OVERLAY_SMALL_LOG is False:
                model.shutdownOverlay()
            config.OVERLAY_LARGE_LOG = False
        return {"status":200, "result":config.OVERLAY_LARGE_LOG}


    @staticmethod
    def setOverlayLargeLogSettings(data, *args, **kwargs) -> dict:
        config.OVERLAY_LARGE_LOG_SETTINGS = data
        model.updateOverlayLargeLogSettings()
        return {"status":200, "result":config.OVERLAY_LARGE_LOG_SETTINGS}


    @staticmethod
    def setEnableOverlayShowOnlyTranslatedMessages(*args, **kwargs) -> dict:
        if config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES is False:
            config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES = True
        return {"status":200, "result":config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def setDisableOverlayShowOnlyTranslatedMessages(*args, **kwargs) -> dict:
        if config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES is True:
            config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES = False
        return {"status":200, "result":config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES}


    @staticmethod
    def setEnableSendMessageToVrc(*args, **kwargs) -> dict:
        if config.SEND_MESSAGE_TO_VRC is False:
            config.SEND_MESSAGE_TO_VRC = True
        return {"status":200, "result":config.SEND_MESSAGE_TO_VRC}

    @staticmethod
    def setDisableSendMessageToVrc(*args, **kwargs) -> dict:
        if config.SEND_MESSAGE_TO_VRC is True:
            config.SEND_MESSAGE_TO_VRC = False
        return {"status":200, "result":config.SEND_MESSAGE_TO_VRC}


    @staticmethod
    def setEnableSendReceivedMessageToVrc(*args, **kwargs) -> dict:
        if config.SEND_RECEIVED_MESSAGE_TO_VRC is False:
            config.SEND_RECEIVED_MESSAGE_TO_VRC = True
        return {"status":200, "result":config.SEND_RECEIVED_MESSAGE_TO_VRC}

    @staticmethod
    def setDisableSendReceivedMessageToVrc(*args, **kwargs) -> dict:
        if config.SEND_RECEIVED_MESSAGE_TO_VRC is True:
            config.SEND_RECEIVED_MESSAGE_TO_VRC = False
        return {"status":200, "result":config.SEND_RECEIVED_MESSAGE_TO_VRC}


    @staticmethod
    def setEnableLoggerFeature(*args, **kwargs) -> dict:
        if config.LOGGER_FEATURE is False:
            model.startLogger()
            config.LOGGER_FEATURE = True
        return {"status":200, "result":config.LOGGER_FEATURE}

    @staticmethod
    def setDisableLoggerFeature(*args, **kwargs) -> dict:
        if config.LOGGER_FEATURE is True:
            model.stopLogger()
            config.LOGGER_FEATURE = False
        return {"status":200, "result":config.LOGGER_FEATURE}


    @staticmethod
    def setEnableVrcMicMuteSync(*args, **kwargs) -> dict:
        if config.VRC_MIC_MUTE_SYNC is False:
            if model.getIsOscQueryEnabled() is True:
                config.VRC_MIC_MUTE_SYNC = True
                model.setMuteSelfStatus()
                model.changeMicTranscriptStatus()
                response = {"status":200, "result":config.VRC_MIC_MUTE_SYNC}
            else:
                response = VRCTError.create_error_response(
                    ErrorCode.VRC_MIC_MUTE_SYNC_OSC_DISABLED,
                    data=config.VRC_MIC_MUTE_SYNC
                )
        else:
            response = {"status":200, "result":config.VRC_MIC_MUTE_SYNC}
        return response

    @staticmethod
    def setDisableVrcMicMuteSync(*args, **kwargs) -> dict:
        if config.VRC_MIC_MUTE_SYNC is True:
            config.VRC_MIC_MUTE_SYNC = False
            model.changeMicTranscriptStatus()
        return {"status":200, "result":config.VRC_MIC_MUTE_SYNC}

    def setEnableCheckSpeakerThreshold(self, *args, **kwargs) -> dict:
        if config.ENABLE_CHECK_ENERGY_RECEIVE is False:
            self.startCheckSpeakerEnergy()
            config.ENABLE_CHECK_ENERGY_RECEIVE = True
        return {"status":200, "result":config.ENABLE_CHECK_ENERGY_RECEIVE}

    def setDisableCheckSpeakerThreshold(self, *args, **kwargs) -> dict:
        if config.ENABLE_CHECK_ENERGY_RECEIVE is True:
            self.stopCheckSpeakerEnergy()
            config.ENABLE_CHECK_ENERGY_RECEIVE = False
        return {"status":200, "result":config.ENABLE_CHECK_ENERGY_RECEIVE}

    def setEnableCheckMicThreshold(self, *args, **kwargs) -> dict:
        if config.ENABLE_CHECK_ENERGY_SEND is False:
            self.startCheckMicEnergy()
            config.ENABLE_CHECK_ENERGY_SEND = True
        return {"status":200, "result":config.ENABLE_CHECK_ENERGY_SEND}

    def setDisableCheckMicThreshold(self, *args, **kwargs) -> dict:
        if config.ENABLE_CHECK_ENERGY_SEND is True:
            self.stopCheckMicEnergy()
            config.ENABLE_CHECK_ENERGY_SEND = False
        return {"status":200, "result":config.ENABLE_CHECK_ENERGY_SEND}

    @staticmethod
    def openFilepathLogs(*args, **kwargs) -> dict:
        Popen(['explorer', config.PATH_LOGS.replace('/', '\\')], shell=True)
        return {"status":200, "result":True}

    @staticmethod
    def openFilepathConfigFile(*args, **kwargs) -> dict:
        Popen(['explorer', config.PATH_LOCAL.replace('/', '\\')], shell=True)
        return {"status":200, "result":True}

    def setEnableTranscriptionSend(self, *args, **kwargs) -> dict:
        if config.ENABLE_TRANSCRIPTION_SEND is False:
            self.startTranscriptionSendMessage()
            config.ENABLE_TRANSCRIPTION_SEND = True
        return {"status":200, "result":config.ENABLE_TRANSCRIPTION_SEND}

    def setDisableTranscriptionSend(self, *args, **kwargs) -> dict:
        if config.ENABLE_TRANSCRIPTION_SEND is True:
            self.stopTranscriptionSendMessage()
            config.ENABLE_TRANSCRIPTION_SEND = False
        return {"status":200, "result":config.ENABLE_TRANSCRIPTION_SEND}

    def setEnableTranscriptionReceive(self, *args, **kwargs) -> dict:
        if config.ENABLE_TRANSCRIPTION_RECEIVE is False:
            self.startTranscriptionReceiveMessage()
            config.ENABLE_TRANSCRIPTION_RECEIVE = True
        return {"status":200, "result":config.ENABLE_TRANSCRIPTION_RECEIVE}

    def setDisableTranscriptionReceive(self, *args, **kwargs) -> dict:
        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            self.stopTranscriptionReceiveMessage()
            config.ENABLE_TRANSCRIPTION_RECEIVE = False
        return {"status":200, "result":config.ENABLE_TRANSCRIPTION_RECEIVE}

    def sendMessageBox(self, data, *args, **kwargs) -> dict:
        response = self.chatMessage(data)
        return response

    @staticmethod
    def typingMessageBox(*args, **kwargs) -> dict:
        if config.SEND_MESSAGE_TO_VRC is True:
            model.oscStartSendTyping()
        return {"status":200, "result":True}

    @staticmethod
    def stopTypingMessageBox(*args, **kwargs) -> dict:
        if config.SEND_MESSAGE_TO_VRC is True:
            model.oscStopSendTyping()
        return {"status":200, "result":True}

    @staticmethod
    def sendTextOverlay(data, *args, **kwargs) -> dict:
        if config.OVERLAY_SMALL_LOG is True:
            if model.overlay.initialized is True:
                overlay_image = model.createOverlayImageSmallMessage(data)
                model.updateOverlaySmallLog(overlay_image)

        if config.OVERLAY_LARGE_LOG is True:
            if model.overlay.initialized is True:
                overlay_image = model.createOverlayImageLargeMessage(data)
                model.updateOverlayLargeLog(overlay_image)
        return {"status":200, "result":data}


    @staticmethod
    def setEnableTelemetry(*args, **kwargs) -> dict:
        if config.ENABLE_TELEMETRY is False:
            config.ENABLE_TELEMETRY = True
            model.telemetryInit(enabled=True, app_version=config.VERSION)
        return {"status":200, "result":config.ENABLE_TELEMETRY}

    @staticmethod
    def setDisableTelemetry(*args, **kwargs) -> dict:
        if config.ENABLE_TELEMETRY is True:
            config.ENABLE_TELEMETRY = False
            model.telemetryShutdown()
        return {"status":200, "result":config.ENABLE_TELEMETRY}

    def swapYourLanguageAndTargetLanguage(self, *args, **kwargs) -> dict:
        your_languages = config.SELECTED_YOUR_LANGUAGES
        your_language_temp = your_languages[config.SELECTED_TAB_NO]["1"]

        target_languages = config.SELECTED_TARGET_LANGUAGES
        target_language_temp = target_languages[config.SELECTED_TAB_NO]["1"]

        your_languages[config.SELECTED_TAB_NO]["1"] = target_language_temp
        target_languages[config.SELECTED_TAB_NO]["1"] = your_language_temp

        self.setSelectedYourLanguages(your_languages)
        self.setSelectedTargetLanguages(target_languages)
        return {
            "status":200,
            "result":{
                "your":config.SELECTED_YOUR_LANGUAGES,
                "target":config.SELECTED_TARGET_LANGUAGES,
                }
            }

    def updateSoftware(self, data:Optional[str]=None, *args, **kwargs) -> dict:
        target_version = str(data) if data else None
        th_start_update_software = Thread(target=model.updateSoftware, args=(target_version,))
        th_start_update_software.daemon = True
        th_start_update_software.start()
        return {"status":200, "result":True}

    def updateCudaSoftware(self, data:Optional[str]=None, *args, **kwargs) -> dict:
        target_version = str(data) if data else None
        th_start_update_cuda_software = Thread(target=model.updateCudaSoftware, args=(target_version,))
        th_start_update_cuda_software.daemon = True
        th_start_update_cuda_software.start()
        return {"status":200, "result":True}

    def downloadCtranslate2Weight(self, data:str, asynchronous:bool=True, *args, **kwargs) -> dict:
        weight_type = str(data)
        download_ctranslate2 = self.DownloadCTranslate2(
            self.run_mapping,
            weight_type,
            self.run
            )

        if asynchronous is True:
            self.startThreadingDownloadCtranslate2Weight(
                weight_type,
                download_ctranslate2.progressBar,
                download_ctranslate2.downloaded,
                )
        else:
            model.downloadCTranslate2ModelWeight(weight_type, download_ctranslate2.progressBar, download_ctranslate2.downloaded)
        model.downloadCTranslate2ModelTokenizer(weight_type)
        return {"status":200, "result":True}

    def downloadWhisperWeight(self, data:str, asynchronous:bool=True, *args, **kwargs) -> dict:
        weight_type = str(data)
        download_whisper = self.DownloadWhisper(
            self.run_mapping,
            weight_type,
            self.run
        )
        if asynchronous is True:
            self.startThreadingDownloadWhisperWeight(
                weight_type,
                download_whisper.progressBar,
                download_whisper.downloaded,
                )
        else:
            model.downloadWhisperModelWeight(weight_type, download_whisper.progressBar, download_whisper.downloaded)
        return {"status":200, "result":True}

    @staticmethod
    def messageFormatter(format_type:str, translation:list, message:str) -> str:
        if format_type == "RECEIVED":
            format_parts = config.RECEIVED_MESSAGE_FORMAT_PARTS
        elif format_type == "SEND":
            format_parts = config.SEND_MESSAGE_FORMAT_PARTS
        else:
            raise ValueError("format_type is not found", format_type)

        message_part = format_parts["message"]["prefix"] + message + format_parts["message"]["suffix"]
        translation_part = format_parts["translation"]["prefix"] + format_parts["translation"]["separator"].join(translation) + format_parts["translation"]["suffix"]

        if len(translation) > 0 and message != "":
            # 翻訳とメッセージの順序を決定
            if format_parts["translation_first"]:
                osc_message = translation_part + format_parts["separator"] + message_part
            else:
                osc_message = message_part + format_parts["separator"] + translation_part
        elif len(translation) > 0 and message == "":
            osc_message = translation_part
        else:
            osc_message = message_part
        return osc_message

    def changeToCTranslate2Process(self) -> None:
        selected_engines = config.SELECTED_TRANSLATION_ENGINES[config.SELECTED_TAB_NO]
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS[selected_engines] = False
        # SELECTED_TRANSLATION_ENGINES は ValidatedProperty (生参照を返さない) なので
        # read → 変更 → 再代入する必要がある。以前は config.X[...] = ... の直接代入で
        # バリデータを一切通さずに内部状態を書き換えていた (P0-3 の生参照バグに依存していた
        # 唯一の呼び出し箇所)。
        engines = config.SELECTED_TRANSLATION_ENGINES
        engines[config.SELECTED_TAB_NO] = "CTranslate2"
        config.SELECTED_TRANSLATION_ENGINES = engines
        selectable_engines = self.getTranslationEngines()["result"]
        self.run(200, self.run_mapping["selected_translation_engines"], config.SELECTED_TRANSLATION_ENGINES)
        self.run(200, self.run_mapping["translation_engines"], selectable_engines)

    def startTranscriptionSendMessage(self) -> None:
        with self.mic_lifecycle_lock:
            try:
                model.startMicTranscript(self.micMessage)
            except Exception as e:
                # VRAM不足エラーの検出
                is_vram_error, error_message = model.detectVRAMError(e)
                if is_vram_error:
                    response = VRCTError.create_error_response(
                        ErrorCode.TRANSCRIPTION_VRAM_MIC,
                        data=error_message
                    )
                    self.run(
                        response["status"],
                        self.run_mapping["error_transcription_mic_vram_overflow"],
                        response["result"],
                    )
                    # ここでマイクの音声認識を停止。mic_lifecycle_lock を既に
                    # 保持しているため、ロックを取り直す公開版
                    # (stopTranscriptionSendMessage) ではなく内部版を呼ぶ。
                    self._stopTranscriptionSendMessageLocked()
                    disable_response = VRCTError.create_error_response(
                        ErrorCode.TRANSCRIPTION_SEND_DISABLED_VRAM,
                        data=False
                    )
                    self.run(
                        disable_response["status"],
                        self.run_mapping["enable_transcription_send"],
                        disable_response["result"],
                    )
                else:
                    # その他のエラーは通常通り処理
                    errorLogging()

    def _stopTranscriptionSendMessageLocked(self) -> None:
        """mic_lifecycle_lock を既に保持している呼び出し元専用。"""
        model.stopMicTranscript()

    def stopTranscriptionSendMessage(self) -> None:
        with self.mic_lifecycle_lock:
            self._stopTranscriptionSendMessageLocked()

    def startTranscriptionReceiveMessage(self) -> None:
        with self.speaker_lifecycle_lock:
            try:
                model.startSpeakerTranscript(self.speakerMessage)
            except Exception as e:
                # VRAM不足エラーの検出
                is_vram_error, error_message = model.detectVRAMError(e)
                if is_vram_error:
                    response = VRCTError.create_error_response(
                        ErrorCode.TRANSCRIPTION_VRAM_SPEAKER,
                        data=error_message
                    )
                    self.run(
                        response["status"],
                        self.run_mapping["error_transcription_speaker_vram_overflow"],
                        response["result"],
                    )
                    # ここでスピーカーの音声認識を停止 (内部版、詳細は
                    # startTranscriptionSendMessage 側のコメント参照)
                    self._stopTranscriptionReceiveMessageLocked()
                    disable_response = VRCTError.create_error_response(
                        ErrorCode.TRANSCRIPTION_RECEIVE_DISABLED_VRAM,
                        data=False
                    )
                    self.run(
                        disable_response["status"],
                        self.run_mapping["enable_transcription_receive"],
                        disable_response["result"],
                    )
                else:
                    # その他のエラーは通常通り処理
                    errorLogging()

    def _stopTranscriptionReceiveMessageLocked(self) -> None:
        """speaker_lifecycle_lock を既に保持している呼び出し元専用。"""
        model.stopSpeakerTranscript()

    def stopTranscriptionReceiveMessage(self) -> None:
        with self.speaker_lifecycle_lock:
            self._stopTranscriptionReceiveMessageLocked()

    def updateDownloadedCTranslate2ModelWeight(self) -> None:
        # キャッシュされた結果を使用（起動時の重複チェックを回避）
        if hasattr(self, '_ctranslate2_available_cache'):
            # 起動時のキャッシュを使用: 選択中の重みタイプのみ設定
            config.SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT[config.CTRANSLATE2_WEIGHT_TYPE] = self._ctranslate2_available_cache
        
        # すべての重みタイプをチェック（キャッシュされていないものだけ）
        for weight_type in config.SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT.keys():
            # 選択中のウェイトはキャッシュで設定済みなのでスキップ
            if hasattr(self, '_ctranslate2_available_cache') and weight_type == config.CTRANSLATE2_WEIGHT_TYPE:
                continue
            config.SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT[weight_type] = model.checkTranslatorCTranslate2ModelWeight(weight_type)

    def updateTranslationEngineAndEngineList(self):
        engines = config.SELECTED_TRANSLATION_ENGINES
        engine = engines[config.SELECTED_TAB_NO]
        selectable_engines = self.getTranslationEngines()["result"]
        if engine not in selectable_engines:
            engine = "CTranslate2"
        engines[config.SELECTED_TAB_NO] = engine
        config.SELECTED_TRANSLATION_ENGINES = engines

        your_language = config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]
        for target_language in config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO].values():
            if your_language["language"] == target_language["language"] and target_language["enable"] is True:
                engine = "CTranslate2"
                engines[config.SELECTED_TAB_NO] = engine
                config.SELECTED_TRANSLATION_ENGINES = engines
                break

        # CTranslate2 is the engine everything above falls back to, but it
        # doesn't support every language either (e.g. Arabic isn't in the
        # nllb-200 weight tables). When even CTranslate2 can't handle the
        # current language selection, there's no further engine to fall
        # back to - reset the language itself instead, or the UI ends up
        # with a selected engine that's simultaneously shown as
        # unavailable/greyed out.
        if self.fallbackUnsupportedLanguagesForEngine(config.SELECTED_TAB_NO, engine):
            selectable_engines = self.getTranslationEngines()["result"]

        self.run(200, self.run_mapping["selected_translation_engines"], config.SELECTED_TRANSLATION_ENGINES)
        self.run(200, self.run_mapping["translation_engines"], selectable_engines)

    def fallbackUnsupportedLanguagesForEngine(self, tab_no: str, engine: str) -> bool:
        """Reset any language on `tab_no` that `engine` doesn't support back
        to a default language `engine` does support (preferring Japanese
        source / English target, the app's own defaults).

        This is the mirror of updateTranslationEngineAndEngineList(), which
        falls the ENGINE back to CTranslate2 when the LANGUAGE changes to
        something the current engine doesn't support. Without this,
        changing the engine first and leaving an unsupported language in
        place goes unnoticed until a translation is actually attempted.

        The default is chosen to avoid the tab's other enabled language
        slots: resetting the source straight to "Japanese" while an enabled
        target is already "Japanese" would make source == target, which
        updateTranslationEngineAndEngineList() treats as a reason to force
        the engine back to CTranslate2 - silently undoing the very engine
        selection this fallback exists to preserve.

        Returns True if any language was reset.
        """
        changed = False

        your_languages = copy.deepcopy(config.SELECTED_YOUR_LANGUAGES)
        target_languages = copy.deepcopy(config.SELECTED_TARGET_LANGUAGES)

        your_language = your_languages[tab_no]["1"]
        enabled_target_languages = {
            target_language["language"]
            for target_language in target_languages[tab_no].values()
            if target_language["enable"] is True
        }
        if not model.isLanguageSupportedByEngine(engine, your_language["language"]):
            default = model.pickDefaultLanguageForEngine(engine, enabled_target_languages)
            if default is not None:
                your_languages[tab_no]["1"] = {**default, "enable": True}
                config.SELECTED_YOUR_LANGUAGES = your_languages
                changed = True
                your_language = your_languages[tab_no]["1"]

        target_changed = False
        # Accumulate languages already spoken for as we go, so two
        # simultaneously-unsupported enabled targets can't both get reset
        # to the same default language.
        taken_languages = {your_language["language"]}
        for target_language in target_languages[tab_no].values():
            if target_language["enable"] is not True:
                continue
            if model.isLanguageSupportedByEngine(engine, target_language["language"]):
                taken_languages.add(target_language["language"])
                continue
            default = model.pickDefaultLanguageForEngine(engine, taken_languages)
            if default is not None:
                target_language["language"] = default["language"]
                target_language["country"] = default["country"]
                target_changed = True
            taken_languages.add(target_language["language"])
        if target_changed:
            config.SELECTED_TARGET_LANGUAGES = target_languages
            changed = True

        if changed:
            self.run(200, self.run_mapping["selected_your_languages"], config.SELECTED_YOUR_LANGUAGES)
            self.run(200, self.run_mapping["selected_target_languages"], config.SELECTED_TARGET_LANGUAGES)

        return changed

    def updateDownloadedWhisperModelWeight(self) -> None:
        # キャッシュされた結果を使用（起動時の重複チェックを回避）
        if hasattr(self, '_whisper_available_cache'):
            # 起動時のキャッシュを使用: 選択中の重みタイプのみ設定
            config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT[config.WHISPER_WEIGHT_TYPE] = self._whisper_available_cache
        
        # すべての重みタイプをチェック（キャッシュされていないものだけ）
        for weight_type in config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT.keys():
            # 選択中のウェイトはキャッシュで設定済みなのでスキップ
            if hasattr(self, '_whisper_available_cache') and weight_type == config.WHISPER_WEIGHT_TYPE:
                continue
            config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT[weight_type] = model.checkTranscriptionWhisperModelWeight(weight_type)

    def updateTranscriptionEngine(self, requested_engine: Optional[str] = None) -> None:
        """SELECTED_TRANSCRIPTION_ENGINE を検証・更新する。

        `requested_engine` を渡すと、まずそれを希望値として設定してから
        検証する (setSelectedTranscriptionEngine からの明示的な変更用。
        setSelectedTranslationEngines() -> updateTranslationEngineAndEngineList()
        と同じパターン)。渡さなければ現在の値をそのまま検証する
        (キー無効化等による自動フォールバック用。controller.init() や
        setGroqWhisperAuthKey/delDeepgramAuthKey 等、多数の呼び出し元から
        使われる)。

        エンジンが実際に変化した場合、文字起こしエンジンごとに対応言語が
        異なりうるため (Deepgram等)、選択中の言語をフォールバックさせ、
        更新後の言語一覧を毎回 selectable_language_list でUIへpushする。
        呼び出し元ごとに重複させず、「エンジンが変わる場所」であるここ
        一箇所に集約することで、どの経路でエンジンが変わっても確実に
        UIの言語リストが追従するようにする。
        """
        previous_engine = config.SELECTED_TRANSCRIPTION_ENGINE
        if requested_engine is not None:
            config.SELECTED_TRANSCRIPTION_ENGINE = requested_engine

        weight_type = config.WHISPER_WEIGHT_TYPE
        weight_type_dict = config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT
        weight_available = bool(weight_type_dict.get(weight_type))
        current_engine = config.SELECTED_TRANSCRIPTION_ENGINE
        selected_engines = [key for key, value in config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS.items() if value is True]

        # 選択可能なエンジンがなければ、Whisper に変更
        if current_engine in {"Whisper", "Google"}:
            if current_engine not in selected_engines:
                if weight_available:
                    alternate = "Google" if current_engine == "Whisper" else "Whisper"
                    config.SELECTED_TRANSCRIPTION_ENGINE = alternate if alternate in selected_engines else None
                else:
                    config.SELECTED_TRANSCRIPTION_ENGINE = "Whisper"
        elif current_engine in TRANSCRIPTION_API_ENGINES or current_engine == "Deepgram":
            # Groq/OpenAI/カスタムサーバー/Deepgramはキー無効化等で使えなく
            # なった場合のみ、ローカル Whisper (オフラインで最も安定) へ
            # フォールバックする。まだ有効なら維持する (この elif が無いと
            # 下の else に落ちて、新エンジンを選択した直後にここが呼ばれる
            # たびに意図せず Whisper へ巻き戻ってしまう)。
            if current_engine not in selected_engines:
                config.SELECTED_TRANSCRIPTION_ENGINE = "Whisper"
        else:
            config.SELECTED_TRANSCRIPTION_ENGINE = "Whisper"

        if config.SELECTED_TRANSCRIPTION_ENGINE != previous_engine:
            self.fallbackUnsupportedLanguagesForTranscriptionEngine(config.SELECTED_TRANSCRIPTION_ENGINE)
            self.run(200, self.run_mapping["selectable_language_list"], model.getListLanguageAndCountry())

    def startCheckMicEnergy(self) -> None:
        with self.mic_lifecycle_lock:
            model.startCheckMicEnergy(self.progressBarMicEnergy)

    def stopCheckMicEnergy(self) -> None:
        with self.mic_lifecycle_lock:
            model.stopCheckMicEnergy()

    def startCheckSpeakerEnergy(self) -> None:
        with self.speaker_lifecycle_lock:
            model.startCheckSpeakerEnergy(self.progressBarSpeakerEnergy)

    def stopCheckSpeakerEnergy(self) -> None:
        with self.speaker_lifecycle_lock:
            model.stopCheckSpeakerEnergy()

    @staticmethod
    def startThreadingDownloadCtranslate2Weight(weight_type:str, callback:Callable[[float], None], end_callback:Optional[Callable[..., None]] = None) -> None:
        th_download = Thread(target=model.downloadCTranslate2ModelWeight, args=(weight_type, callback, end_callback))
        th_download.daemon = True
        th_download.start()

    @staticmethod
    def startThreadingDownloadWhisperWeight(weight_type:str, callback:Callable[[float], None], end_callback:Optional[Callable[..., None]] = None) -> None:
        th_download = Thread(target=model.downloadWhisperModelWeight, args=(weight_type, callback, end_callback))
        th_download.daemon = True
        th_download.start()

    @staticmethod
    def startWatchdog(*args, **kwargs) -> dict:
        model.startWatchdog()
        return {"status":200, "result":True}

    @staticmethod
    def feedWatchdog(*args, **kwargs) -> dict:
        model.feedWatchdog()
        return {"status":200, "result":True}

    @staticmethod
    def setWatchdogCallback(callback) -> dict:
        model.setWatchdogCallback(callback)
        return {"status":200, "result":True}

    @staticmethod
    def stopWatchdog(*args, **kwargs) -> dict:
        model.stopWatchdog()
        return {"status":200, "result":True}


    @staticmethod
    def setWebSocketHost(data, *args, **kwargs) -> dict:
        # 0.0.0.0/:: (ワイルドカードアドレス) は「マシンが持つ全インター
        # フェースで listen する」ことを意味し、WebSocket サーバーは
        # 認証 (token) を導入済みとはいえ、同一 LAN 上の第三者からの
        # 到達性まで許してしまう。特定の LAN IP を明示的に選ぶのとは
        # リスクの性質が異なるため、他の IP 検証と分けて拒否する。
        if isValidIpAddress(data) is False or isWildcardBindAddress(data) is True:
            response = VRCTError.create_error_response(
                ErrorCode.VALIDATION_INVALID_IP,
                data=config.WEBSOCKET_HOST
            )
        else:
            if model.checkWebSocketServerAlive() is False:
                config.WEBSOCKET_HOST = data
                response = {"status":200, "result":config.WEBSOCKET_HOST}
            else:
                if data == config.WEBSOCKET_HOST:
                    response = {"status":200, "result":config.WEBSOCKET_HOST}
                elif isAvailableWebSocketServer(data, config.WEBSOCKET_PORT):
                    model.stopWebSocketServer()
                    model.startWebSocketServer(data, config.WEBSOCKET_PORT)
                    config.WEBSOCKET_HOST = data
                    # The OBS overlay's HTTP server must stay bound to the
                    # same host the WebSocket server now listens on, or the
                    # overlay page it serves will point at a dead address.
                    if config.OBS_BROWSER_SOURCE is True:
                        model.stopObsBrowserSourceServer()
                        model.startObsBrowserSourceServer(data, int(config.OBS_BROWSER_SOURCE_PORT))
                    response = {"status":200, "result":config.WEBSOCKET_HOST}
                else:
                    response = VRCTError.create_error_response(
                        ErrorCode.WEBSOCKET_HOST_INVALID,
                        data=config.WEBSOCKET_HOST
                    )

        return response


    @staticmethod
    def setWebSocketPort(data, *args, **kwargs) -> dict:
        try:
            port = int(data)
        except Exception:
            return VRCTError.create_error_response(
                ErrorCode.WEBSOCKET_PORT_INVALID,
                data=config.WEBSOCKET_PORT,
                custom_message="WebSocket port must be a number",
            )

        if model.checkWebSocketServerAlive() is False:
            config.WEBSOCKET_PORT = port
            response = {"status":200, "result":config.WEBSOCKET_PORT}
        else:
            if port == config.WEBSOCKET_PORT:
                return {"status":200, "result":config.WEBSOCKET_PORT}
            elif isAvailableWebSocketServer(config.WEBSOCKET_HOST, port) is True:
                model.stopWebSocketServer()
                model.startWebSocketServer(config.WEBSOCKET_HOST, port)
                config.WEBSOCKET_PORT = port
                response = {"status":200, "result":config.WEBSOCKET_PORT}
            else:
                response = VRCTError.create_error_response(
                    ErrorCode.WEBSOCKET_PORT_UNAVAILABLE,
                    data=config.WEBSOCKET_PORT
                )
        return response

    @staticmethod
    def getWebSocketAuthToken(*args, **kwargs) -> dict:
        """WebSocket サーバーへの接続に必要なトークンを返す。

        OBS Browser Source はサーバー側が生成するページに自動で埋め込むため
        これを直接使う必要はないが、VRCT-TTS のように接続 URL をユーザーが
        手動入力する外部連携ツール向けに、UI 側で
        `ws://{host}:{port}/?token={token}` をコピーできるようにするために
        公開する。
        """
        return {"status":200, "result":config.WEBSOCKET_AUTH_TOKEN}


    @staticmethod
    def setEnableWebSocketServer(*args, **kwargs) -> dict:
        if config.WEBSOCKET_SERVER is False:
            if isAvailableWebSocketServer(config.WEBSOCKET_HOST, config.WEBSOCKET_PORT) is True:
                model.startWebSocketServer(config.WEBSOCKET_HOST, config.WEBSOCKET_PORT)
                config.WEBSOCKET_SERVER = True
                response = {"status":200, "result":config.WEBSOCKET_SERVER}
            else:
                response = VRCTError.create_error_response(
                    ErrorCode.WEBSOCKET_SERVER_UNAVAILABLE,
                    data=config.WEBSOCKET_SERVER
                )
        else:
            response = {"status":200, "result":config.WEBSOCKET_SERVER}
        return response

    @staticmethod
    def setDisableWebSocketServer(*args, **kwargs) -> dict:
        if config.WEBSOCKET_SERVER is True:
            # OBS Browser Source overlay receives its messages through this
            # WebSocket server; stopping the server without also disabling
            # OBS Browser Source would leave config.OBS_BROWSER_SOURCE stuck
            # at True while the overlay silently stops updating.
            if config.OBS_BROWSER_SOURCE is True:
                config.OBS_BROWSER_SOURCE = False
                model.stopObsBrowserSourceServer()
            config.WEBSOCKET_SERVER = False
            model.stopWebSocketServer()
        return {"status":200, "result":config.WEBSOCKET_SERVER}

    # OBS Browser Source (local overlay for OBS)

    @staticmethod
    def setEnableObsBrowserSource(*args, **kwargs) -> dict:
        if config.OBS_BROWSER_SOURCE is True:
            return {"status":200, "result":config.OBS_BROWSER_SOURCE}

        # OBS overlay depends on the WebSocket server to receive messages.
        if model.checkWebSocketServerAlive() is False:
            if isAvailableWebSocketServer(config.WEBSOCKET_HOST, config.WEBSOCKET_PORT) is True:
                model.startWebSocketServer(config.WEBSOCKET_HOST, config.WEBSOCKET_PORT)
                config.WEBSOCKET_SERVER = True
            else:
                return VRCTError.create_error_response(
                    ErrorCode.OBS_BROWSER_SOURCE_SERVER_UNAVAILABLE,
                    data=config.OBS_BROWSER_SOURCE,
                    custom_message="WebSocket server host or port is not available",
                )

        obs_host = config.WEBSOCKET_HOST
        obs_port = int(config.OBS_BROWSER_SOURCE_PORT)

        if isAvailableWebSocketServer(obs_host, obs_port) is not True:
            return VRCTError.create_error_response(
                ErrorCode.OBS_BROWSER_SOURCE_PORT_UNAVAILABLE,
                data=config.OBS_BROWSER_SOURCE_PORT
            )

        model.startObsBrowserSourceServer(obs_host, obs_port)

        if model.checkObsBrowserSourceServerAlive() is not True:
            return VRCTError.create_error_response(
                ErrorCode.OBS_BROWSER_SOURCE_SERVER_UNAVAILABLE,
                data=config.OBS_BROWSER_SOURCE
            )

        config.OBS_BROWSER_SOURCE = True
        return {"status":200, "result":config.OBS_BROWSER_SOURCE}

    @staticmethod
    def setDisableObsBrowserSource(*args, **kwargs) -> dict:
        if config.OBS_BROWSER_SOURCE is True:
            config.OBS_BROWSER_SOURCE = False
            model.stopObsBrowserSourceServer()
        return {"status":200, "result":config.OBS_BROWSER_SOURCE}


    @staticmethod
    def setObsBrowserSourcePort(data, *args, **kwargs) -> dict:
        try:
            port = int(data)
        except Exception:
            return VRCTError.create_error_response(
                ErrorCode.OBS_BROWSER_SOURCE_PORT_UNAVAILABLE,
                data=config.OBS_BROWSER_SOURCE_PORT,
                custom_message="OBS Browser Source port must be a number",
            )

        if model.checkObsBrowserSourceServerAlive() is not True:
            config.OBS_BROWSER_SOURCE_PORT = port
            return {"status":200, "result":config.OBS_BROWSER_SOURCE_PORT}

        if port == config.OBS_BROWSER_SOURCE_PORT:
            return {"status":200, "result":config.OBS_BROWSER_SOURCE_PORT}

        if isAvailableWebSocketServer(config.WEBSOCKET_HOST, port) is not True:
            return VRCTError.create_error_response(
                ErrorCode.OBS_BROWSER_SOURCE_PORT_UNAVAILABLE,
                data=config.OBS_BROWSER_SOURCE_PORT
            )

        model.stopObsBrowserSourceServer()
        model.startObsBrowserSourceServer(config.WEBSOCKET_HOST, port)
        if model.checkObsBrowserSourceServerAlive() is not True:
            config.OBS_BROWSER_SOURCE = False
            return VRCTError.create_error_response(
                ErrorCode.OBS_BROWSER_SOURCE_SERVER_UNAVAILABLE,
                data=config.OBS_BROWSER_SOURCE
            )

        config.OBS_BROWSER_SOURCE_PORT = port
        return {"status":200, "result":config.OBS_BROWSER_SOURCE_PORT}

    def _pushObsBrowserSourceSettings(self) -> None:
        """Notify any already-open OBS overlay pages that display settings
        changed, so they can apply them live instead of waiting for the
        next page load (OBS Browser Sources normally cache the page and
        never refetch it on their own).
        """
        if config.OBS_BROWSER_SOURCE is not True:
            return
        if model.checkWebSocketServerAlive() is not True:
            return
        model.websocketSendMessage({
            "type": "SETTINGS_UPDATED",
            "settings": {
                "maxMessages": config.OBS_BROWSER_SOURCE_MAX_MESSAGES,
                "displayDuration": config.OBS_BROWSER_SOURCE_DISPLAY_DURATION,
                "fadeoutDuration": config.OBS_BROWSER_SOURCE_FADEOUT_DURATION,
                "fontSize": config.OBS_BROWSER_SOURCE_FONT_SIZE,
                "fontColor": config.OBS_BROWSER_SOURCE_FONT_COLOR,
                "outlineThickness": config.OBS_BROWSER_SOURCE_FONT_OUTLINE_THICKNESS,
                "outlineColor": config.OBS_BROWSER_SOURCE_FONT_OUTLINE_COLOR,
            },
        })


    def setObsBrowserSourceMaxMessages(self, data, *args, **kwargs) -> dict:
        try:
            value = int(data)
        except Exception:
            return VRCTError.create_error_response(
                ErrorCode.OBS_BROWSER_SOURCE_MAX_MESSAGES_INVALID,
                data=config.OBS_BROWSER_SOURCE_MAX_MESSAGES,
                custom_message="OBS Browser Source max messages must be a number",
            )
        config.OBS_BROWSER_SOURCE_MAX_MESSAGES = value
        self._pushObsBrowserSourceSettings()
        return {"status":200, "result":config.OBS_BROWSER_SOURCE_MAX_MESSAGES}


    def setObsBrowserSourceDisplayDuration(self, data, *args, **kwargs) -> dict:
        try:
            value = int(data)
        except Exception:
            return VRCTError.create_error_response(
                ErrorCode.OBS_BROWSER_SOURCE_DISPLAY_DURATION_INVALID,
                data=config.OBS_BROWSER_SOURCE_DISPLAY_DURATION,
                custom_message="OBS Browser Source display duration must be a number",
            )
        config.OBS_BROWSER_SOURCE_DISPLAY_DURATION = value
        self._pushObsBrowserSourceSettings()
        return {"status":200, "result":config.OBS_BROWSER_SOURCE_DISPLAY_DURATION}


    def setObsBrowserSourceFadeoutDuration(self, data, *args, **kwargs) -> dict:
        try:
            value = int(data)
        except Exception:
            return VRCTError.create_error_response(
                ErrorCode.OBS_BROWSER_SOURCE_FADEOUT_DURATION_INVALID,
                data=config.OBS_BROWSER_SOURCE_FADEOUT_DURATION,
                custom_message="OBS Browser Source fadeout duration must be a number",
            )
        config.OBS_BROWSER_SOURCE_FADEOUT_DURATION = value
        self._pushObsBrowserSourceSettings()
        return {"status":200, "result":config.OBS_BROWSER_SOURCE_FADEOUT_DURATION}


    def setObsBrowserSourceFontSize(self, data, *args, **kwargs) -> dict:
        try:
            value = int(data)
        except Exception:
            return VRCTError.create_error_response(
                ErrorCode.OBS_BROWSER_SOURCE_FONT_SIZE_INVALID,
                data=config.OBS_BROWSER_SOURCE_FONT_SIZE,
                custom_message="OBS Browser Source font size must be a number",
            )
        config.OBS_BROWSER_SOURCE_FONT_SIZE = value
        self._pushObsBrowserSourceSettings()
        return {"status":200, "result":config.OBS_BROWSER_SOURCE_FONT_SIZE}


    def setObsBrowserSourceFontColor(self, data, *args, **kwargs) -> dict:
        color = str(data).strip()
        if not _HEX_COLOR_RE.match(color):
            return VRCTError.create_error_response(
                ErrorCode.OBS_BROWSER_SOURCE_FONT_COLOR_INVALID,
                data=config.OBS_BROWSER_SOURCE_FONT_COLOR,
            )
        config.OBS_BROWSER_SOURCE_FONT_COLOR = color.upper()
        self._pushObsBrowserSourceSettings()
        return {"status":200, "result":config.OBS_BROWSER_SOURCE_FONT_COLOR}


    def setObsBrowserSourceFontOutlineThickness(self, data, *args, **kwargs) -> dict:
        try:
            value = int(data)
        except Exception:
            return VRCTError.create_error_response(
                ErrorCode.OBS_BROWSER_SOURCE_FONT_OUTLINE_THICKNESS_INVALID,
                data=config.OBS_BROWSER_SOURCE_FONT_OUTLINE_THICKNESS,
                custom_message="OBS Browser Source outline thickness must be a number",
            )
        config.OBS_BROWSER_SOURCE_FONT_OUTLINE_THICKNESS = value
        self._pushObsBrowserSourceSettings()
        return {"status":200, "result":config.OBS_BROWSER_SOURCE_FONT_OUTLINE_THICKNESS}


    def setObsBrowserSourceFontOutlineColor(self, data, *args, **kwargs) -> dict:
        color = str(data).strip()
        if not _HEX_COLOR_RE.match(color):
            return VRCTError.create_error_response(
                ErrorCode.OBS_BROWSER_SOURCE_FONT_OUTLINE_COLOR_INVALID,
                data=config.OBS_BROWSER_SOURCE_FONT_OUTLINE_COLOR,
            )
        config.OBS_BROWSER_SOURCE_FONT_OUTLINE_COLOR = color.upper()
        self._pushObsBrowserSourceSettings()
        return {"status":200, "result":config.OBS_BROWSER_SOURCE_FONT_OUTLINE_COLOR}

    # Clipboard control

    @staticmethod
    def setEnableClipboard(*args, **kwargs) -> dict:
        if config.ENABLE_CLIPBOARD is False:
            config.ENABLE_CLIPBOARD = True
        return {"status":200, "result":config.ENABLE_CLIPBOARD}

    @staticmethod
    def setDisableClipboard(*args, **kwargs) -> dict:
        if config.ENABLE_CLIPBOARD is True:
            config.ENABLE_CLIPBOARD = False
        return {"status":200, "result":config.ENABLE_CLIPBOARD}

    def initializationProgress(self, progress):
        self.run(200, self.run_mapping["initialization_progress"], progress)

    def enableOscQuery(self):
        self.run(
            200,
            self.run_mapping["enable_osc_query"],
            {
                "data": True,
                "disabled_functions": []
            }
        )

    def disableOscQuery(self, mute_sync_info:bool=False):
        disabled_functions = []
        if mute_sync_info is True:
            disabled_functions.append("vrc_mic_mute_sync")
        self.run(200, self.run_mapping["enable_osc_query"], {
            "data": False,
            "disabled_functions": disabled_functions
        })

    def _initVrcMicMuteSync(self) -> None:
        """VRC_MIC_MUTE_SYNC が有効な場合の、起動時のミュート状態初期同期。

        `model.setMuteSelfStatus()` はVRChatのOSCQueryサービスへの
        その場限りの一発勝負の問い合わせ。VRCTがVRChatより先に起動していると
        これは失敗し (`model.mic_mute_status` が `None` のまま)、
        `changeHandlerMute` (model.py) 側のガード条件が `None` からは
        絶対に遷移できない構造になっているため、二度とミュート同期が
        機能しなくなる不具合があった (VRChatを先に起動していれば問題は
        起きない、という起動順序依存のバグとして実機で確認済み)。

        ここで諦めず、VRChatのOSCQueryサービスがmDNSで後から現れた瞬間に
        `_retryMuteSelfStatusOnceVrchatFound()` を呼ぶよう監視を仕込むことで、
        起動順序に関わらずミュート同期を確立できるようにする。
        """
        model.setMuteSelfStatus()
        if model.mic_mute_status is not None:
            model.changeMicTranscriptStatus()
        else:
            model.watchForVrchatOscQueryConnection(self._retryMuteSelfStatusOnceVrchatFound)

    def _retryMuteSelfStatusOnceVrchatFound(self) -> None:
        """VRChatのOSCQueryサービスが後から見つかった際のコールバック
        (`_initVrcMicMuteSync()` 参照)。zeroconf自身のバックグラウンド
        スレッドから呼ばれる。
        """
        try:
            model.setMuteSelfStatus()
            model.changeMicTranscriptStatus()
        except Exception:
            errorLogging()

    def _bootstrapModel(self) -> None:
        """`model.init()` + ミュート同期コールバック登録 (フェーズ3項目22)。

        以前は `Controller.__init__` (`Controller()` 構築時、本番では
        mainloop.py のモジュールimport時) に前倒しで実行していたが、
        `model.init()` 自身が「import時には呼ばない、ensure_initialized()
        で遅延初期化する」設計であることに合わせて `init()` 側に移動した。

        経緯: 一度この移動を実装した際、実機検証で「VRCTをVRChatより先に
        起動するとOSCQueryが接続されずミュート同期が壊れる」回帰が見つかり
        タイミングを一旦元に戻した。その後の調査で、この回帰は今回の
        タイミング変更とは無関係の既存バグ (起動時1回きりの
        `model.setMuteSelfStatus()` がVRChat未起動時に失敗すると
        `model.mic_mute_status` が `None` のまま二度と回復しない構造的な
        問題) と判明し、`_VrchatOscQueryFoundListener`
        (`models/osc/osc.py`) による別修正で解決済み。タイミング変更自体は
        無罪と確認できたため、改めてここに移動した。

        `init()` 本体から切り出したのは、この2行だけを (残り400行超の
        ネットワーク確認・重みダウンロード等を実行せずに) 単体テストで
        検証できるようにするため。

        順序が重要: `model.init()` は
        `model.mic_mute_status_change_callback` を `None` にリセットする
        ため、先に `model.init()` を終わらせてからコールバックを登録しないと
        登録した値が消えてしまう。
        """
        try:
            self._model.init()
        except Exception:
            # In test or headless environments initialization may fail; log and continue.
            errorLogging()
        try:
            # OSC ミュート同期 (Model.changeHandlerMute, 任意の OSC 受信
            # スレッドで走る) が pause()/resume() を mic_lifecycle_lock 配下
            # で実行できるよう、ロック付きラッパーを Model 側のコールバック
            # スロットへ登録する。
            self._model.setMicMuteStatusChangeCallback(self._changeMicTranscriptStatusLocked)
        except Exception:
            errorLogging()

    def init(self, *args, **kwargs) -> None:
        removeLog()
        printLog("Start Initialization")

        self._bootstrapModel()

        # watchdog を初期化処理の先頭で起動する。以前は init() の最終行に
        # あったため、モデル重みのダウンロードや外部 API 呼び出しが
        # (バグ等で) 無期限にハングした場合、watchdog 自体がまだ起動して
        # おらず自動復旧が一切効かなかった。フロントエンドは Python
        # プロセスを spawn した直後から 20s 間隔で /run/feed_watchdog を
        # 送り続けており (StartPythonController.jsx)、このエンドポイントは
        # 初期化中でも処理可能 (mainloop.py の "status": True) なため、
        # init() をメインスレッドで実行している間も 3 本のハンドラワーカー
        # がフィードを処理できる。よってここで起動しても安全。
        self.startWatchdog()

        # Network check
        connected_network = isConnectedNetwork()
        if connected_network is True:
            self.connectedNetwork()
        else:
            self.disconnectedNetwork()
        printLog(f"Connected Network: {connected_network}")

        self.initializationProgress(1)

        # Download weights
        # 事前チェックの結果（Noneは「未実施」、True/Falseは「ロード検証済み」）。
        # ダウンロードが発生しなかった場合はこの結果をそのまま使い、後続の
        # availabilityチェックで同じ重みを二重にロードして検証するのを避ける。
        ctranslate2_pre_available: Optional[bool] = None
        whisper_pre_available: Optional[bool] = None
        if connected_network is True:
            printLog("Download CTranslate2 Model Weight")
            # 後方互換用
            model.backwardCompatibleTranslatorCTranslate2ModelRenameWeightsDir()

            weight_type = config.CTRANSLATE2_WEIGHT_TYPE
            th_download_ctranslate2 = None
            ctranslate2_pre_available = model.checkTranslatorCTranslate2ModelWeight(weight_type)
            if ctranslate2_pre_available is False:
                th_download_ctranslate2 = Thread(target=self.downloadCtranslate2Weight, args=(weight_type, False))
                th_download_ctranslate2.daemon = True
                th_download_ctranslate2.start()

            printLog("Download Whisper Model Weight")
            weight_type = config.WHISPER_WEIGHT_TYPE
            th_download_whisper = None
            whisper_pre_available = model.checkTranscriptionWhisperModelWeight(weight_type)
            if whisper_pre_available is False:
                th_download_whisper = Thread(target=self.downloadWhisperWeight, args=(weight_type, False))
                th_download_whisper.daemon = True
                th_download_whisper.start()

            # join() にタイムアウトを設ける: downloadCTranslate2Weight/
            # downloadWhisperWeight は HTTP タイムアウト+リトライ (最大 3 回
            # × 最大 70s + バックオフ) を持つため 1 ファイルあたりの worst
            # case は数分程度で収まるが、重みセットが複数ファイルにまたがる
            # ため、理論上の合計 worst case はさらに長くなりうる。無制限
            # join だと万一そのバジェットを超えて本当にハングした場合に
            # init() (ひいてはアプリの起動) が無期限に固まる。ここでの
            # タイムアウトは「異常系での最終防波堤」として十分長く
            # (30 分) 取り、正常系の低速回線でのリトライを誤って
            # 中断しないようにする。タイムアウトした場合はダウンロード
            # スレッド (daemon) をバックグラウンドで走らせたまま
            # 初期化を先へ進める。
            _WEIGHT_DOWNLOAD_JOIN_TIMEOUT_SEC = 1800
            if isinstance(th_download_ctranslate2, Thread):
                th_download_ctranslate2.join(timeout=_WEIGHT_DOWNLOAD_JOIN_TIMEOUT_SEC)
                if th_download_ctranslate2.is_alive():
                    printLog(
                        f"CTranslate2 weight download did not finish within "
                        f"{_WEIGHT_DOWNLOAD_JOIN_TIMEOUT_SEC}s; continuing "
                        "initialization without waiting further (download "
                        "continues in the background)"
                    )
                # ダウンロードを行った場合は結果が変わるため再検証が必要
                ctranslate2_pre_available = None
            if isinstance(th_download_whisper, Thread):
                th_download_whisper.join(timeout=_WEIGHT_DOWNLOAD_JOIN_TIMEOUT_SEC)
                if th_download_whisper.is_alive():
                    printLog(
                        f"Whisper weight download did not finish within "
                        f"{_WEIGHT_DOWNLOAD_JOIN_TIMEOUT_SEC}s; continuing "
                        "initialization without waiting further (download "
                        "continues in the background)"
                    )
                whisper_pre_available = None

        # Check and disable/enable AI models (parallel)
        # 上の事前チェックで「ロード検証済みかつダウンロード不要」と分かっている場合は
        # 同じ重みファイルをもう一度ロードして検証するのを避け、その結果を再利用する。

        def check_ctranslate2() -> bool:
            if ctranslate2_pre_available is True:
                return True
            return model.checkTranslatorCTranslate2ModelWeight(config.CTRANSLATE2_WEIGHT_TYPE) is True

        def check_whisper() -> bool:
            if whisper_pre_available is True:
                return True
            return model.checkTranscriptionWhisperModelWeight(config.WHISPER_WEIGHT_TYPE) is True

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_ctranslate2 = executor.submit(check_ctranslate2)
            future_whisper = executor.submit(check_whisper)
            ctranslate2_available = future_ctranslate2.result()
            whisper_available = future_whisper.result()

        # 初回ダウンロード後もまだロードできない重みがある場合、ユーザーに
        # 「AIモデル未検出。VRCTを再起動してください」通知を出して手動再起動を
        # 促す前に、アプリ自身が最大1回だけ同期的に再ダウンロードを試みる。
        # (list_repo_files の一時失敗などで初回ダウンロードスレッドが丸ごと
        #  取りこぼしたケースを吸収する)
        if connected_network is True and (not ctranslate2_available or not whisper_available):
            if not ctranslate2_available:
                printLog("CTranslate2 weight unavailable after first download; retrying once")
                self.downloadCtranslate2Weight(config.CTRANSLATE2_WEIGHT_TYPE, False)
            if not whisper_available:
                printLog("Whisper weight unavailable after first download; retrying once")
                self.downloadWhisperWeight(config.WHISPER_WEIGHT_TYPE, False)

            with ThreadPoolExecutor(max_workers=2) as executor:
                future_ctranslate2 = executor.submit(
                    lambda: ctranslate2_available or model.checkTranslatorCTranslate2ModelWeight(config.CTRANSLATE2_WEIGHT_TYPE) is True
                )
                future_whisper = executor.submit(
                    lambda: whisper_available or model.checkTranscriptionWhisperModelWeight(config.WHISPER_WEIGHT_TYPE) is True
                )
                ctranslate2_available = future_ctranslate2.result()
                whisper_available = future_whisper.result()

        # インスタンス変数にキャッシュ（後続の処理で再利用）
        self._ctranslate2_available_cache = ctranslate2_available
        self._whisper_available_cache = whisper_available

        if not ctranslate2_available or not whisper_available:
            self.disableAiModels()
        else:
            self.enableAiModels()

        # Init Translation Engine Status (with parallel processing)
        printLog("Init Translation Engine Status")

        def check_translation_engine(engine: str) -> tuple:
            """翻訳エンジンのステータスをチェック（並列実行用）"""
            status = False
            auth_key_invalid = False
            model_list = None
            selected_model = None

            try:
                match engine:
                    case "CTranslate2":
                        # 既に前のステップでチェック済み、結果を再利用
                        status = ctranslate2_available
                    case "DeepL_API":
                        if config.AUTH_KEYS[engine] is None:
                            status = False
                        else:
                            if model.authenticationTranslatorDeepLAuthKey(auth_key=config.AUTH_KEYS[engine]) is True:
                                status = True
                            else:
                                auth_key_invalid = True
                    case "Plamo_API":
                        if config.AUTH_KEYS[engine] is None:
                            status = False
                        else:
                            if model.authenticationTranslatorPlamoAuthKey(auth_key=config.AUTH_KEYS[engine]) is True:
                                model_list = model.getTranslatorPlamoModelList()
                                selected_model = config.SELECTED_PLAMO_MODEL if config.SELECTED_PLAMO_MODEL in model_list else model_list[0]
                                status = True
                            else:
                                auth_key_invalid = True
                    case "Gemini_API":
                        if config.AUTH_KEYS[engine] is None:
                            status = False
                        else:
                            if model.authenticationTranslatorGeminiAuthKey(auth_key=config.AUTH_KEYS[engine]) is True:
                                model_list = model.getTranslatorGeminiModelList()
                                selected_model = config.SELECTED_GEMINI_MODEL if config.SELECTED_GEMINI_MODEL in model_list else model_list[0]
                                status = True
                            else:
                                auth_key_invalid = True
                    case "OpenAI_API":
                        if config.AUTH_KEYS[engine] is None:
                            status = False
                        else:
                            if model.authenticationTranslatorOpenAIAuthKey(auth_key=config.AUTH_KEYS[engine]) is True:
                                model_list = model.getTranslatorOpenAIModelList()
                                selected_model = config.SELECTED_OPENAI_MODEL if config.SELECTED_OPENAI_MODEL in model_list else model_list[0]
                                status = True
                            else:
                                auth_key_invalid = True
                    case "Groq_API":
                        if config.AUTH_KEYS[engine] is None:
                            status = False
                        else:
                            if model.authenticationTranslatorGroqAuthKey(auth_key=config.AUTH_KEYS[engine]) is True:
                                model_list = model.getTranslatorGroqModelList()
                                selected_model = config.SELECTED_GROQ_MODEL if config.SELECTED_GROQ_MODEL in model_list else model_list[0]
                                status = True
                            else:
                                auth_key_invalid = True
                    case "OpenRouter_API":
                        if config.AUTH_KEYS[engine] is None:
                            status = False
                        else:
                            if model.authenticationTranslatorOpenRouterAuthKey(auth_key=config.AUTH_KEYS[engine]) is True:
                                model_list = model.getTranslatorOpenRouterModelList()
                                selected_model = config.SELECTED_OPENROUTER_MODEL if config.SELECTED_OPENROUTER_MODEL in model_list else model_list[0]
                                status = True
                            else:
                                auth_key_invalid = True
                    case "LMStudio":
                        if config.LMSTUDIO_URL is not None:
                            if model.authenticationTranslatorLMStudio(base_url=config.LMSTUDIO_URL) is True:
                                model_list = model.getTranslatorLMStudioModelList()
                                if len(model_list) > 0:
                                    selected_model = config.SELECTED_LMSTUDIO_MODEL if config.SELECTED_LMSTUDIO_MODEL in model_list else model_list[0]
                                    status = True
                    case "OpenAI_Compatible":
                        auth_key = config.AUTH_KEYS.get("OpenAI_Compatible")
                        if auth_key and config.OPENAI_COMPATIBLE_URL:
                            if model.authenticationTranslatorOpenAICompatibleAuthKey(
                                auth_key=auth_key,
                                base_url=config.OPENAI_COMPATIBLE_URL,
                            ) is True:
                                model_list = model.getTranslatorOpenAICompatibleModelList()
                                if len(model_list) > 0:
                                    selected_model = config.SELECTED_OPENAI_COMPATIBLE_MODEL if config.SELECTED_OPENAI_COMPATIBLE_MODEL in model_list else model_list[0]
                                    status = True
                            else:
                                auth_key_invalid = True
                    case "Ollama":
                        if model.authenticationTranslatorOllama() is True:
                            model_list = model.getTranslatorOllamaModelList()
                            if len(model_list) > 0:
                                selected_model = config.SELECTED_OLLAMA_MODEL if config.SELECTED_OLLAMA_MODEL in model_list else model_list[0]
                                status = True
                    case _:
                        status = connected_network is True
            except Exception as e:
                printLog(f"Error checking engine {engine}: {str(e)}")
                errorLogging()
                status = False

            return engine, status, auth_key_invalid, model_list, selected_model

        engine_results = {}
        engines_to_check = list(config.SELECTABLE_TRANSLATION_ENGINE_LIST)

        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_engine = {executor.submit(check_translation_engine, engine): engine 
                              for engine in engines_to_check}

            for future in as_completed(future_to_engine):
                engine, status, auth_key_invalid, model_list, selected_model = future.result()
                engine_results[engine] = (status, auth_key_invalid, model_list, selected_model)

        # 結果を順番に適用（メインスレッドで実行）
        for engine in engines_to_check:
            if engine not in engine_results:
                continue

            status, auth_key_invalid, model_list, selected_model = engine_results[engine]

            # ログ出力
            printLog(f"Start check {engine}")

            # ステータス設定
            config.SELECTABLE_TRANSLATION_ENGINE_STATUS[engine] = status

            # 認証キー無効化
            if auth_key_invalid:
                auth_keys = config.AUTH_KEYS
                auth_keys[engine] = None
                config.AUTH_KEYS = auth_keys
                printLog(f"{engine} auth key is invalid")
            elif status:
                printLog(f"{engine} is valid/available")

            if engine == "LMStudio" and not status:
                config.SELECTABLE_LMSTUDIO_MODEL_LIST = []
                config.SELECTED_LMSTUDIO_MODEL = None
            if engine == "OpenAI_Compatible" and not status:
                config.SELECTABLE_OPENAI_COMPATIBLE_MODEL_LIST = []
                config.SELECTED_OPENAI_COMPATIBLE_MODEL = None
            if engine == "Ollama" and not status:
                config.SELECTABLE_OLLAMA_MODEL_LIST = []
                config.SELECTED_OLLAMA_MODEL = None

            # モデルリストと選択モデルの設定
            if model_list is not None and status:
                match engine:
                    case "Plamo_API":
                        config.SELECTABLE_PLAMO_MODEL_LIST = model_list
                        config.SELECTED_PLAMO_MODEL = selected_model
                        model.setTranslatorPlamoModel(selected_model)
                        model.updateTranslatorPlamoClient()
                    case "Gemini_API":
                        config.SELECTABLE_GEMINI_MODEL_LIST = model_list
                        config.SELECTED_GEMINI_MODEL = selected_model
                        model.setTranslatorGeminiModel(selected_model)
                        model.updateTranslatorGeminiClient()
                    case "OpenAI_API":
                        config.SELECTABLE_OPENAI_MODEL_LIST = model_list
                        config.SELECTED_OPENAI_MODEL = selected_model
                        model.setTranslatorOpenAIModel(selected_model)
                        model.updateTranslatorOpenAIClient()
                    case "Groq_API":
                        config.SELECTABLE_GROQ_MODEL_LIST = model_list
                        config.SELECTED_GROQ_MODEL = selected_model
                        model.setTranslatorGroqModel(selected_model)
                        model.updateTranslatorGroqClient()
                    case "OpenRouter_API":
                        config.SELECTABLE_OPENROUTER_MODEL_LIST = model_list
                        config.SELECTED_OPENROUTER_MODEL = selected_model
                        model.setTranslatorOpenRouterModel(selected_model)
                        model.updateTranslatorOpenRouterClient()
                    case "LMStudio":
                        config.SELECTABLE_LMSTUDIO_MODEL_LIST = model_list
                        config.SELECTED_LMSTUDIO_MODEL = selected_model
                        model.setTranslatorLMStudioModel(selected_model)
                        model.updateTranslatorLMStudioClient()
                    case "OpenAI_Compatible":
                        config.SELECTABLE_OPENAI_COMPATIBLE_MODEL_LIST = model_list
                        config.SELECTED_OPENAI_COMPATIBLE_MODEL = selected_model
                        model.setTranslatorOpenAICompatibleModel(selected_model)
                        model.updateTranslatorOpenAICompatibleClient()
                    case "Ollama":
                        config.SELECTABLE_OLLAMA_MODEL_LIST = model_list
                        config.SELECTED_OLLAMA_MODEL = selected_model
                        model.setTranslatorOllamaModel(selected_model)
                        model.updateTranslatorOllamaClient()

            printLog(f"{engine} check completed")

        printLog("Translation Engine Status Init completed")

        # Init Transcription Engine Status
        printLog("Init Transcription Engine Status")

        # Deepgram のモデル名 -> 対応言語一覧。check_transcription_engine() は
        # 全エンジン共通の戻り値シェイプ (model_list は list[str]) を持つため、
        # Deepgram だけが持つ追加メタデータ (言語一覧) はここに直接書き込む
        # (Deepgram のケースはスレッドプール中で高々1回しか実行されないため
        # 競合の心配はない)。
        deepgram_model_languages: dict = {}

        def check_transcription_engine(engine: str) -> tuple:
            """文字起こしエンジンのステータスをチェック（並列実行用）。

            Groq/OpenAI/カスタムサーバーは翻訳側の OpenAI互換エンジンと同じ
            「認証キーでモデル一覧が取得できるか」で可用性を判定する。
            実際に文字起こしを1回試すより軽量で、起動時の検証に向く。
            """
            status = False
            auth_key_invalid = False
            model_list = None
            selected_model = None

            try:
                match engine:
                    case "Whisper":
                        # キャッシュされた結果を使用（重複チェックを回避）
                        status = self._whisper_available_cache
                    case "Groq_Whisper":
                        api_key = config.TRANSCRIPTION_AUTH_KEYS.get(engine)
                        if not api_key:
                            status = False
                        else:
                            base_url = config.GROQ_WHISPER_BASE_URL
                            if model.authenticationTranscriptionApiKey(api_key=api_key, base_url=base_url) is True:
                                model_list = model.getTranscriptionApiModelList(
                                    api_key=api_key, base_url=base_url, keyword_filter=TRANSCRIPTION_MODEL_KEYWORDS,
                                )
                                if len(model_list) > 0:
                                    selected_model = config.SELECTED_GROQ_WHISPER_MODEL if config.SELECTED_GROQ_WHISPER_MODEL in model_list else model_list[0]
                                    status = True
                            else:
                                auth_key_invalid = True
                    case "OpenAI_Whisper":
                        api_key = config.TRANSCRIPTION_AUTH_KEYS.get(engine)
                        if not api_key:
                            status = False
                        else:
                            base_url = config.OPENAI_WHISPER_BASE_URL
                            if model.authenticationTranscriptionApiKey(api_key=api_key, base_url=base_url) is True:
                                model_list = model.getTranscriptionApiModelList(
                                    api_key=api_key, base_url=base_url, keyword_filter=TRANSCRIPTION_MODEL_KEYWORDS,
                                )
                                if len(model_list) > 0:
                                    selected_model = config.SELECTED_OPENAI_WHISPER_MODEL if config.SELECTED_OPENAI_WHISPER_MODEL in model_list else model_list[0]
                                    status = True
                            else:
                                auth_key_invalid = True
                    case "Custom_Whisper":
                        api_key = config.TRANSCRIPTION_AUTH_KEYS.get(engine)
                        base_url = config.TRANSCRIPTION_CUSTOM_URL
                        if not api_key or not base_url:
                            status = False
                        else:
                            if model.authenticationTranscriptionApiKey(api_key=api_key, base_url=base_url) is True:
                                # カスタムサーバーはどんなモデル名を使っているか分からないため絞り込まない
                                model_list = model.getTranscriptionApiModelList(api_key=api_key, base_url=base_url)
                                if len(model_list) > 0:
                                    selected_model = config.SELECTED_CUSTOM_WHISPER_MODEL if config.SELECTED_CUSTOM_WHISPER_MODEL in model_list else model_list[0]
                                    status = True
                            else:
                                auth_key_invalid = True
                    case "Deepgram":
                        api_key = config.TRANSCRIPTION_AUTH_KEYS.get(engine)
                        if not api_key:
                            status = False
                        else:
                            if model.authenticationDeepgramApiKey(api_key=api_key) is True:
                                models_detailed = model.getDeepgramModelListDetailed(api_key=api_key)
                                model_list = [m["name"] for m in models_detailed]
                                deepgram_model_languages.update({m["name"]: m["languages"] for m in models_detailed})
                                if len(model_list) > 0:
                                    selected_model = config.SELECTED_DEEPGRAM_MODEL if config.SELECTED_DEEPGRAM_MODEL in model_list else model_list[0]
                                    status = True
                            else:
                                auth_key_invalid = True
                    case _:
                        # Google 等、ネットワーク接続のみが条件のエンジン
                        status = connected_network is True
            except Exception as e:
                printLog(f"Error checking transcription engine {engine}: {str(e)}")
                errorLogging()
                status = False

            return engine, status, auth_key_invalid, model_list, selected_model

        transcription_engine_results = {}
        transcription_engines_to_check = list(config.SELECTABLE_TRANSCRIPTION_ENGINE_LIST)

        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_transcription_engine = {
                executor.submit(check_transcription_engine, engine): engine
                for engine in transcription_engines_to_check
            }
            for future in as_completed(future_to_transcription_engine):
                engine, status, auth_key_invalid, model_list, selected_model = future.result()
                transcription_engine_results[engine] = (status, auth_key_invalid, model_list, selected_model)

        for engine in transcription_engines_to_check:
            if engine not in transcription_engine_results:
                continue

            status, auth_key_invalid, model_list, selected_model = transcription_engine_results[engine]

            config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS[engine] = status

            if auth_key_invalid:
                auth_keys = config.TRANSCRIPTION_AUTH_KEYS
                auth_keys[engine] = None
                config.TRANSCRIPTION_AUTH_KEYS = auth_keys
                printLog(f"{engine} transcription auth key is invalid")
            elif status:
                printLog(f"{engine} transcription engine is valid/available")

            if engine == "Groq_Whisper" and not status:
                config.SELECTABLE_GROQ_WHISPER_MODEL_LIST = []
                config.SELECTED_GROQ_WHISPER_MODEL = None
            if engine == "OpenAI_Whisper" and not status:
                config.SELECTABLE_OPENAI_WHISPER_MODEL_LIST = []
                config.SELECTED_OPENAI_WHISPER_MODEL = None
            if engine == "Custom_Whisper" and not status:
                config.SELECTABLE_CUSTOM_WHISPER_MODEL_LIST = []
                config.SELECTED_CUSTOM_WHISPER_MODEL = None
            if engine == "Deepgram" and not status:
                config.SELECTABLE_DEEPGRAM_MODEL_LIST = []
                config.DEEPGRAM_MODEL_LANGUAGES = {}
                config.SELECTED_DEEPGRAM_MODEL = None

            if model_list is not None and status:
                match engine:
                    case "Groq_Whisper":
                        config.SELECTABLE_GROQ_WHISPER_MODEL_LIST = model_list
                        config.SELECTED_GROQ_WHISPER_MODEL = selected_model
                    case "OpenAI_Whisper":
                        config.SELECTABLE_OPENAI_WHISPER_MODEL_LIST = model_list
                        config.SELECTED_OPENAI_WHISPER_MODEL = selected_model
                    case "Deepgram":
                        config.SELECTABLE_DEEPGRAM_MODEL_LIST = model_list
                        config.DEEPGRAM_MODEL_LANGUAGES = deepgram_model_languages
                        config.SELECTED_DEEPGRAM_MODEL = selected_model
                    case "Custom_Whisper":
                        config.SELECTABLE_CUSTOM_WHISPER_MODEL_LIST = model_list
                        config.SELECTED_CUSTOM_WHISPER_MODEL = selected_model

        printLog("Transcription Engine Status Init completed")
        self.initializationProgress(2)

        # Set Translation Engine
        printLog("Set Translation Engine")
        self.updateDownloadedCTranslate2ModelWeight()
        self.updateTranslationEngineAndEngineList()

        # Set Transcription Engine
        printLog("Set Transcription Engine")
        self.updateDownloadedWhisperModelWeight()
        self.updateTranscriptionEngine()

        # Set Transliteration
        printLog("Set Transliteration")
        if config.CONVERT_MESSAGE_TO_ROMAJI is True or config.CONVERT_MESSAGE_TO_HIRAGANA is True:
            model.startTransliteration()

        self.initializationProgress(3)

        # Set Word Filter
        printLog("Set Word Filter")
        model.addKeywords()

        # Check Software Updated (Background)
        printLog("Check Software Updated (Background)")

        def check_software_updated_background():
            """ソフトウェア更新チェックをバックグラウンドで実行"""
            try:
                self.checkSoftwareUpdated()
                printLog("[Background] Software update check completed")
            except Exception:
                errorLogging()
                printLog("[Background] Software update check failed")

        bg_thread = Thread(target=check_software_updated_background)
        bg_thread.daemon = True
        bg_thread.start()

        # Init Logger
        printLog("Init Logger")
        if config.LOGGER_FEATURE is True:
            model.startLogger()

        self.initializationProgress(4)

        # Init OSC Receive (Background)
        printLog("Init OSC Receive (Background)")

        def init_osc_receive_background():
            """OSC Receiveの初期化をバックグラウンドで実行"""
            try:
                model.startReceiveOSC()
                osc_query_enabled = model.getIsOscQueryEnabled()
                if osc_query_enabled is True:
                    self.enableOscQuery()
                    if config.VRC_MIC_MUTE_SYNC is True:
                        self._initVrcMicMuteSync()
                else:
                    # OSC Query is disabled, so disable VRC some features
                    mute_sync_info_flag = False
                    if config.VRC_MIC_MUTE_SYNC is True:
                        self.setDisableVrcMicMuteSync()
                        mute_sync_info_flag = True
                    self.disableOscQuery(mute_sync_info=mute_sync_info_flag)
                printLog("[Background] OSC Receive initialization completed")
            except Exception:
                errorLogging()
                printLog("[Background] OSC Receive initialization failed")

        bg_thread = Thread(target=init_osc_receive_background)
        bg_thread.daemon = True
        bg_thread.start()

        # Init Device Manager
        printLog("Init Device Manager")
        device_manager.setCallbackHostList(self.updateMicHostList)
        device_manager.setCallbackMicDeviceList(self.updateMicDeviceList)
        device_manager.setCallbackSpeakerDeviceList(self.updateSpeakerDeviceList)

        printLog("Init Auto Device Selection")
        if config.AUTO_MIC_SELECT is True:
            self.applyAutoMicSelect()
        if config.AUTO_SPEAKER_SELECT is True:
            self.applyAutoSpeakerSelect()

        # Init Overlay
        printLog("Init Overlay")
        if (config.OVERLAY_SMALL_LOG is True or config.OVERLAY_LARGE_LOG is True):
            model.startOverlay()

        # Init WebSocket Server
        printLog("Init WebSocket Server")
        # OBS Browser Source depends on WebSocket Server to receive messages.
        if config.OBS_BROWSER_SOURCE is True and config.WEBSOCKET_SERVER is False:
            config.WEBSOCKET_SERVER = True

        if config.WEBSOCKET_SERVER is True:
            if isAvailableWebSocketServer(config.WEBSOCKET_HOST, config.WEBSOCKET_PORT) is True:
                model.startWebSocketServer(config.WEBSOCKET_HOST, config.WEBSOCKET_PORT)
            else:
                config.WEBSOCKET_SERVER = False
                model.stopWebSocketServer()
                printLog("WebSocket server host or port is not available")

        # Init OBS Browser Source Server
        printLog("Init OBS Browser Source Server")
        if config.OBS_BROWSER_SOURCE is True:
            if config.WEBSOCKET_SERVER is not True:
                config.OBS_BROWSER_SOURCE = False
                model.stopObsBrowserSourceServer()
                printLog("OBS Browser Source requires WebSocket Server")
            elif isAvailableWebSocketServer(config.WEBSOCKET_HOST, config.OBS_BROWSER_SOURCE_PORT) is True:
                model.startObsBrowserSourceServer(config.WEBSOCKET_HOST, config.OBS_BROWSER_SOURCE_PORT)
            else:
                config.OBS_BROWSER_SOURCE = False
                model.stopObsBrowserSourceServer()
                printLog("OBS Browser Source server host or port is not available")

        # Revalidate Selected Models
        printLog("Revalidate Selected Models")
        config.revalidate_selected_models()

        # telemetry Init
        printLog("Telemetry Init")
        if config.ENABLE_TELEMETRY is True:
            model.telemetryInit(enabled=config.ENABLE_TELEMETRY, app_version=config.VERSION)

        # Update Settings
        printLog("Update settings")
        self.updateConfigSettings()

        printLog("End Initialization")


def _makeSimpleConfigGetter(attr_name: str):
    """`_SIMPLE_CONFIG_GETTERS` の1エントリから、単純なgetterを生成する
    (フェーズ3項目23)。以前はこの形の94個のメソッドが`controller.py`に
    個別の`def`として並んでいた:

        @staticmethod
        def getUiLanguage(*args, **kwargs) -> dict:
            return {"status":200, "result":config.UI_LANGUAGE}

    ロジックが完全に同一な94個の関数定義を、1個のジェネレータ+
    テーブルへ集約する。生成したメソッドは通常の`def`と同じ名前で
    `Controller`クラスへ登録するため (`_registerSimpleConfigGetters()`
    参照)、`mainloop.py`のルーティング (`controller.getUiLanguage`) や
    既存テストからの直接呼び出しは一切変更不要。
    """
    def getter(*args, **kwargs) -> dict:
        return {"status": 200, "result": getattr(config, attr_name)}
    return getter


def _registerSimpleConfigGetters() -> None:
    for method_name, attr_name in _SIMPLE_CONFIG_GETTERS.items():
        getter = _makeSimpleConfigGetter(attr_name)
        getter.__name__ = method_name
        getter.__qualname__ = f"Controller.{method_name}"
        setattr(Controller, method_name, staticmethod(getter))


_registerSimpleConfigGetters()
