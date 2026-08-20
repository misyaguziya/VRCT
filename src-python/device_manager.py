from typing import Callable, Dict, List, Optional, Any
from time import sleep
from threading import Thread, Lock, Event

# Optional, Windows-specific dependencies. Guard imports so module can be imported on non-Windows systems.
try:
    import comtypes
except Exception:  # pragma: no cover - optional runtime
    comtypes = None  # type: ignore

try:
    from pyaudiowpatch import PyAudio, paWASAPI
except Exception:  # pragma: no cover - optional runtime
    PyAudio = None  # type: ignore
    paWASAPI = None  # type: ignore

try:
    from pycaw.callbacks import MMNotificationClient
    from pycaw.utils import AudioUtilities
except Exception:  # pragma: no cover - optional runtime
    MMNotificationClient = object  # type: ignore
    AudioUtilities = None  # type: ignore

from utils import errorLogging, printLog
from active_endpoint_tracker import ActiveEndpointTracker

# pauseMicEndpointTracker/pauseSpeakerEndpointTracker のバリア待ちの上限。
# tracker の COM 呼び出し (Activate/GetPeakValue 等) には現状タイムアウトが
# 無く、理論上ハングし得る (active_endpoint_tracker.py の ActiveEndpointTracker
# クラスdocstring参照)。ハングした場合、このバリアを無期限待ちにしていると
# 呼び出し元 (mainloop のハンドラワーカースレッド、本数が限られている) が
# 永久にブロックされ、他の全リクエスト処理までアプリごと無応答になる。
# タイムアウトしても根本のロック保持スレッドが解放されるわけではない
# (COM 呼び出し自体は止められない) ため完全な解決ではないが、少なくとも
# ハンドラワーカーを解放してアプリの他機能を無応答にしないための緩和策。
_PAUSE_BARRIER_TIMEOUT_SEC = 5.0

# WASAPI/PortAudio 操作 (デバイス列挙・ストリーム open/close) を
# 直列化するためのプロセス共通ロック。
# 別スレッドから同一 WASAPI エンドポイントに対して並行にオペレーションを
# 発行すると PortAudio 内部で待ち合ってデッドロックすることがある
# (例: monitoring 側の update() でループバックデバイス列挙中に、
# transcription 側で同じデバイスの loopback stream を open すると hang)。
# device_manager.update() と recorder の Microphone open で共通に使う。
pyaudio_op_lock: Lock = Lock()


class Client(MMNotificationClient):
    """Callback client used by pycaw to detect device changes.

    COM のコールバックスレッドから呼ばれる。monitoring スレッドは
    `notify_event` を wait しており、いずれかのイベントで set されると
    デバイス一覧を再構築する。stop イベント (外部から `stop_event.set()`)
    でも wait は解ける (`Event.wait` は set 済みならすぐ True を返す)。
    """

    def __init__(self, notify_event: Event) -> None:
        # If MMNotificationClient is the placeholder object (non-windows), avoid calling super
        try:
            super().__init__()
        except Exception:
            pass
        self._notify_event = notify_event

    def on_default_device_changed(self, *args: Any, **kwargs: Any) -> None:
        self._notify_event.set()

    def on_device_added(self, *args: Any, **kwargs: Any) -> None:
        self._notify_event.set()

    def on_device_removed(self, *args: Any, **kwargs: Any) -> None:
        self._notify_event.set()

    def on_device_state_changed(self, *args: Any, **kwargs: Any) -> None:
        self._notify_event.set()

    # on_property_value_changed は登録しない: default endpoint 変更は
    # on_default_device_changed で拾えており、property イベントは
    # ボリューム変更などでも発火するため、拾うとポーリングが過剰になる。

class DeviceManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DeviceManager, cls).__new__(cls)
            # do NOT auto-init monitoring-heavy resources on import; require explicit init
            # Still perform a light-weight init so that callers observing the singleton
            # do not see uninitialized internal structures (which caused NoDevice to
            # be seen when import order differed).
            cls._instance._initialized = False
            try:
                # Call init() to populate internal containers. This will NOT start
                # the monitoring thread (startMonitoring must be called explicitly).
                cls._instance.init()
            except Exception:
                # Avoid import-time crashes; log and continue.
                try:
                    errorLogging()
                except Exception:
                    pass
        return cls._instance

    def init(self) -> None:
        """Initialize internal state. This is intentionally separate from object
        creation so importing the module won't start threads or access OS
        audio APIs. Call `device_manager.init()` and then
        `device_manager.startMonitoring()` explicitly when ready.
        """
        if getattr(self, "_initialized", False):
            return

        self.mic_devices: Dict[str, List[Dict[str, Any]]] = {"NoHost": [{"index": -1, "name": "NoDevice"}]}
        self.default_mic_device: Dict[str, Any] = {"host": {"index": -1, "name": "NoHost"}, "device": {"index": -1, "name": "NoDevice"}}
        self.speaker_devices: List[Dict[str, Any]] = [{"index": -1, "name": "NoDevice"}]
        self.default_speaker_device: Dict[str, Any] = {"device": {"index": -1, "name": "NoDevice"}}

        # Initialize previous state trackers
        self.prev_mic_host: List[str] = [host for host in self.mic_devices]
        self.prev_mic_devices: Dict[str, List[Dict[str, Any]]] = self.mic_devices
        self.prev_default_mic_device: Dict[str, Any] = self.default_mic_device
        self.prev_speaker_devices: List[Dict[str, Any]] = self.speaker_devices
        self.prev_default_speaker_device: Dict[str, Any] = self.default_speaker_device

        # Update flags
        self.update_flag_default_mic_device: bool = False
        self.update_flag_default_speaker_device: bool = False
        self.update_flag_host_list: bool = False
        self.update_flag_mic_device_list: bool = False
        self.update_flag_speaker_device_list: bool = False

        # Callbacks
        self.callback_default_mic_device: Optional[Callable[..., None]] = None
        self.callback_default_speaker_device: Optional[Callable[..., None]] = None
        self.callback_host_list: Optional[Callable[..., None]] = None
        self.callback_mic_device_list: Optional[Callable[..., None]] = None
        self.callback_speaker_device_list: Optional[Callable[..., None]] = None
        self.callback_process_before_update_mic_devices: Optional[Callable[..., None]] = None
        self.callback_process_after_update_mic_devices: Optional[Callable[..., None]] = None
        self.callback_process_before_update_speaker_devices: Optional[Callable[..., None]] = None
        self.callback_process_after_update_speaker_devices: Optional[Callable[..., None]] = None
        # ActiveEndpointTracker がエンドポイント切替を検知したとき、Session の
        # Recorder 差し替えをトリガするための callback (Auto 経路専用)。
        # 既存の default_mic_device callback は config 更新 + UI 通知のみで、
        # Recorder 側の再開はしない設計のため別チャネルにする。
        self.callback_endpoint_reconfigured_mic: Optional[Callable[..., None]] = None
        self.callback_endpoint_reconfigured_speaker: Optional[Callable[..., None]] = None

        # Monitoring control
        # `_stop_event` を set すると monitoring スレッドは wait を即抜けて終了する。
        # 従来の `monitoring_flag` (bool) は `sleep` 越しに参照するとタイムラグが
        # 生じ、stopMonitoring 側で最大 5s の join 待ちが発生していた。Event に
        # 置き換えたことで stop は即応する。
        self._stop_event: Event = Event()
        self._stop_event.set()  # 初期状態は「停止済み」
        # notify_event は startMonitoring の中で作り直されるが、
        # stopMonitoring が startMonitoring より先に呼ばれても落ちないよう
        # ここでダミーを 1 個用意しておく。
        self._notify_event: Event = Event()
        self.th_monitoring: Optional[Thread] = None

        # Auto Select 状態を mic/speaker で独立管理する。
        # 監視スレッド自体は 1 本 (update() が両方のリストを一括で refresh する
        # ため分けても大きな利点なし) だが、Before/After callback は各サイド
        # の active フラグに応じて選択的に発火する。従来は controller 側で
        # 「相手側が OFF なら monitoring 全体を止める」という相互参照ガードが
        # 必要だったが、DeviceManager にフラグを持たせることで撤去できる。
        self._mic_auto_active: bool = False
        self._speaker_auto_active: bool = False

        # 「実使用中エンドポイント」を追跡する tracker。Auto がアクティブな
        # ときのみ起動する。tracker の on_change コールバックは監視スレッド
        # (別スレッド) から呼ばれ、内部で updateSelectedMicDevice /
        # updateSelectedSpeakerDevice 相当の callback を発火する。
        # tracker が None (無音) を返す場合は既存の Multimedia default 検出
        # (update() → noticeUpdateDevices → setMicDefaultDevice) が生きているので
        # 何もしない = 前回選択を維持。
        self._mic_endpoint_tracker: Optional[ActiveEndpointTracker] = None
        self._speaker_endpoint_tracker: Optional[ActiveEndpointTracker] = None

        self._initialized = True

        # Best-effort single update: if PyAudio is available, attempt to populate
        # real device lists. Keep this short and ignore errors to avoid import-time
        # failures.
        try:
            if PyAudio is not None:
                try:
                    # update() is robust and will fall back to defaults if audio libs
                    # are missing or fail; do not let exceptions bubble up.
                    self.update()
                except Exception:
                    errorLogging()
        except Exception:
            # defensive: if errorLogging isn't available or other issues occur,
            # swallow to avoid breaking initialization
            pass

    def update(self):
        buffer_mic_devices: Dict[str, List[Dict[str, Any]]] = {}
        buffer_default_mic_device: Dict[str, Any] = {"host": {"index": -1, "name": "NoHost"}, "device": {"index": -1, "name": "NoDevice"}}
        buffer_speaker_devices: List[Dict[str, Any]] = []
        buffer_default_speaker_device: Dict[str, Any] = {"device": {"index": -1, "name": "NoDevice"}}

        if PyAudio is None:
            # PyAudio not available; leave defaults in place
            self.mic_devices = buffer_mic_devices or {"NoHost": [{"index": -1, "name": "NoDevice"}]}
            self.default_mic_device = buffer_default_mic_device
            self.speaker_devices = buffer_speaker_devices or [{"index": -1, "name": "NoDevice"}]
            self.default_speaker_device = buffer_default_speaker_device
            return

        try:
            # ロックで PortAudio/WASAPI の並行操作を防ぐ。
            # recorder 側の open と衝突するとデッドロックし得る。
            with pyaudio_op_lock, PyAudio() as p:
                # gather input devices grouped by host
                for host_index in range(p.get_host_api_count()):
                    host = p.get_host_api_info_by_index(host_index)
                    device_count = host.get('deviceCount', 0)
                    for device_index in range(device_count):
                        device = p.get_device_info_by_host_api_device_index(host_index, device_index)
                        if device.get("maxInputChannels", 0) > 0 and not device.get("isLoopbackDevice", True):
                            buffer_mic_devices.setdefault(host["name"], []).append(device)
                if not buffer_mic_devices:
                    buffer_mic_devices = {"NoHost": [{"index": -1, "name": "NoDevice"}]}

                api_info = p.get_default_host_api_info()
                default_mic_device = api_info.get("defaultInputDevice", -1)

                for host_index in range(p.get_host_api_count()):
                    host = p.get_host_api_info_by_index(host_index)
                    device_count = host.get('deviceCount', 0)
                    for device_index in range(device_count):
                        device = p.get_device_info_by_host_api_device_index(host_index, device_index)
                        if device.get("index") == default_mic_device:
                            buffer_default_mic_device = {"host": host, "device": device}
                            break
                    else:
                        continue
                    break

                # collect speaker loopback devices (requires WASAPI)
                speaker_devices: List[Dict[str, Any]] = []
                if paWASAPI is not None:
                    try:
                        wasapi_info = p.get_host_api_info_by_type(paWASAPI)
                        wasapi_name = wasapi_info.get("name")
                        for host_index in range(p.get_host_api_count()):
                            host = p.get_host_api_info_by_index(host_index)
                            if host.get("name") == wasapi_name:
                                device_count = host.get('deviceCount', 0)
                                for device_index in range(device_count):
                                    device = p.get_device_info_by_host_api_device_index(host_index, device_index)
                                    if not device.get("isLoopbackDevice", True):
                                        for loopback in p.get_loopback_device_info_generator():
                                            # match by name inclusion
                                            if device.get("name") in loopback.get("name", ""):
                                                speaker_devices.append(loopback)
                    except Exception:
                        # WASAPI not available or failed; ignore and continue
                        pass

                # deduplicate and sort
                speaker_devices = [dict(t) for t in {tuple(d.items()) for d in speaker_devices}] or [{"index": -1, "name": "NoDevice"}]
                buffer_speaker_devices = sorted(speaker_devices, key=lambda d: d.get('index', -1))

                # default speaker
                if paWASAPI is not None:
                    try:
                        wasapi_info = p.get_host_api_info_by_type(paWASAPI)
                        default_speaker_device_index = wasapi_info.get("defaultOutputDevice", -1)
                        for host_index in range(p.get_host_api_count()):
                            host_info = p.get_host_api_info_by_index(host_index)
                            device_count = host_info.get('deviceCount', 0)
                            for device_index in range(0, device_count):
                                device = p.get_device_info_by_host_api_device_index(host_index, device_index)
                                if device.get("index") == default_speaker_device_index:
                                    default_speakers = device
                                    if not default_speakers.get("isLoopbackDevice", True):
                                        for loopback in p.get_loopback_device_info_generator():
                                            if default_speakers.get("name") in loopback.get("name", ""):
                                                buffer_default_speaker_device = {"device": loopback}
                                                break
                                    break

                            if buffer_default_speaker_device["device"].get("name") != "NoDevice":
                                break
                    except Exception:
                        # best-effort; ignore failures
                        pass

        except Exception:
            errorLogging()

        self.mic_devices = buffer_mic_devices
        self.default_mic_device = buffer_default_mic_device
        self.speaker_devices = buffer_speaker_devices
        self.default_speaker_device = buffer_default_speaker_device

    def _applyDeviceDiffs(self) -> None:
        """update() 後の一覧と prev_* を比較して update_flag_* を立て、
        prev_* を最新に置き換える (副作用のみ、戻り値なし)。

        monitoring ループからのみ呼ばれる前提。他所から呼ぶと prev_* が
        意図せず上書きされ、次回の差分検知が不正確になる。以前は
        `checkUpdate` という副作用の無さそうな名前だったため rename した。
        """
        if self.prev_default_mic_device["device"]["name"] != self.default_mic_device["device"]["name"]:
            self.update_flag_default_mic_device = True
            self.prev_default_mic_device = self.default_mic_device
        if self.prev_default_speaker_device["device"]["name"] != self.default_speaker_device["device"]["name"]:
            self.update_flag_default_speaker_device = True
            self.prev_default_speaker_device = self.default_speaker_device
        if self.prev_mic_host != [host for host in self.mic_devices]:
            self.update_flag_host_list = True
            self.prev_mic_host = [host for host in self.mic_devices]
        if {key: [device['name'] for device in devices] for key, devices in self.prev_mic_devices.items()} != {key: [device['name'] for device in devices] for key, devices in self.mic_devices.items()}:
            self.update_flag_mic_device_list = True
            self.prev_mic_devices = self.mic_devices
        if [device['name'] for device in self.prev_speaker_devices] != [device['name'] for device in self.speaker_devices]:
            self.update_flag_speaker_device_list = True
            self.prev_speaker_devices = self.speaker_devices

    def monitoring(self):
        """デバイス変更を監視するスレッド本体。

        フロー:
          1. COM の endpoint 通知を待つ (通知またはポーリング fallback として最大 2s)
          2. 通知が来たら Before callback → update() → noticeUpdate → After callback
          3. stop_event が set されていれば即座に終了

        以前は「COM 通知後、20s ポーリングで変化を待つ」ループがあったが、
        (a) COM 通知が届いた時点でほぼ確実にデバイス一覧は変化済み、
        (b) 変化しないケースでは 20s 待ち続けてもリソース浪費なだけ、
        (c) その間 stop_event を見ないので OFF 応答が遅くなる、という
        3 点の理由で削除した。update() 一発と noticeUpdate で必要十分。
        """
        try:
            while not self._stop_event.is_set():
                try:
                    self._notify_event.clear()

                    # COM が使える環境では endpoint 通知で wait、そうでなければ
                    # 一定周期のポーリングで代替する。stop_event を wait 相手に
                    # 混ぜているのは、COM が反応しなくても stop で即抜けるため。
                    if comtypes is not None and AudioUtilities is not None:
                        try:
                            comtypes.CoInitialize()
                            cb = Client(self._notify_event)
                            enumerator = AudioUtilities.GetDeviceEnumerator()
                            enumerator.RegisterEndpointNotificationCallback(cb)
                            # 通知 or stop のいずれかで即抜ける。最長 2s の
                            # タイムアウトは COM が万一通知を落とした場合の保険。
                            while not self._notify_event.wait(timeout=2.0):
                                if self._stop_event.is_set():
                                    break
                            try:
                                enumerator.UnregisterEndpointNotificationCallback(cb)
                            except Exception:
                                # best-effort unregister
                                pass
                            comtypes.CoUninitialize()
                        except Exception:
                            # COM 監視が失敗したらポーリング fallback に落ちる
                            errorLogging()
                            self._stop_event.wait(timeout=2.0)
                    else:
                        # 非 Windows fallback: 単純ポーリング
                        self._stop_event.wait(timeout=2.0)

                    if self._stop_event.is_set():
                        break

                    # 通知を受けた直後のデバイス一覧再構築フェーズ。
                    # Before/After callback は Auto がアクティブな側のみ発火。
                    # 相手側の Auto は無効な状態でも、update() は両方の
                    # デバイスリストを refresh する (副作用の少ない読み取り
                    # なので always-run)。
                    if self._mic_auto_active:
                        self.runProcessBeforeUpdateMicDevices()
                    if self._speaker_auto_active:
                        self.runProcessBeforeUpdateSpeakerDevices()
                    self.update()
                    self._applyDeviceDiffs()
                    self.noticeUpdateDevices()
                    if self._mic_auto_active:
                        self.runProcessAfterUpdateMicDevices()
                    if self._speaker_auto_active:
                        self.runProcessAfterUpdateSpeakerDevices()
                except Exception:
                    errorLogging()
                    # 個別の例外で暴走ループにならないよう、短い wait を挟む
                    self._stop_event.wait(timeout=0.5)
        except Exception:
            errorLogging()

    def startMonitoring(self):
        # 既に稼働中なら何もしない (冪等)
        if not self._stop_event.is_set() and self.th_monitoring is not None and self.th_monitoring.is_alive():
            return
        self._stop_event.clear()
        # notify_event は init 時に作った同一インスタンスを再利用し
        # 状態だけ clear する。以前は毎回 Event() で作り直していたが、
        # startMonitoring と stopMonitoring が並行実行された場合に
        # stopMonitoring が古い Event を set し、新しく起動したスレッドは
        # 新 Event を wait したまま起きられない、という race が発生していた。
        self._notify_event.clear()
        self.th_monitoring = Thread(target=self.monitoring, daemon=True)
        self.th_monitoring.start()

    def setMicAutoActive(self, active: bool) -> None:
        """Auto Mic Select の有効/無効を DeviceManager 側で受け取る。

        監視スレッドの起動/停止判断はここで完結させ、controller 側が
        相手側 (speaker) の状態を見て判断する必要を無くす。同時に、
        アクティブエンドポイント追跡 tracker の起動/停止も切り替える。
        """
        self._mic_auto_active = active
        if active:
            self._startMicEndpointTracker()
        else:
            self._stopMicEndpointTracker()
        self._syncMonitoringLifecycle()

    def setSpeakerAutoActive(self, active: bool) -> None:
        """Auto Speaker Select の有効/無効を DeviceManager 側で受け取る。
        詳細は setMicAutoActive のコメント参照。"""
        self._speaker_auto_active = active
        if active:
            self._startSpeakerEndpointTracker()
        else:
            self._stopSpeakerEndpointTracker()
        self._syncMonitoringLifecycle()

    def _startMicEndpointTracker(self) -> None:
        if self._mic_endpoint_tracker is not None:
            return
        # pyaudio_op_lock を渡して、tracker の COM 呼び出しと Recorder の
        # open/close が同じ WASAPI エンドポイント上で並行実行されるのを防ぐ。
        tracker = ActiveEndpointTracker("capture", com_lock=pyaudio_op_lock)
        tracker.set_on_change_callback(self._onActiveMicEndpointChanged)
        tracker.start()
        self._mic_endpoint_tracker = tracker

    def _stopMicEndpointTracker(self) -> None:
        tracker = self._mic_endpoint_tracker
        self._mic_endpoint_tracker = None
        if tracker is not None:
            tracker.stop()

    def _startSpeakerEndpointTracker(self) -> None:
        if self._speaker_endpoint_tracker is not None:
            return
        tracker = ActiveEndpointTracker("render", com_lock=pyaudio_op_lock)
        tracker.set_on_change_callback(self._onActiveSpeakerEndpointChanged)
        tracker.start()
        self._speaker_endpoint_tracker = tracker

    def _stopSpeakerEndpointTracker(self) -> None:
        tracker = self._speaker_endpoint_tracker
        self._speaker_endpoint_tracker = None
        if tracker is not None:
            tracker.stop()

    def pauseMicEndpointTracker(self) -> None:
        """外部から tracker を一時停止し、進行中の COM 呼び出しが
        あれば完了を待つ (Session の reconfigure 前に使用)。

        pause() は次の poll の開始をブロックするだけで、既に走っている
        _com_lock 内の Activate/GetPeakValue は完了を待たない。ここで
        pyaudio_op_lock を一瞬 acquire/release することでバリアとして
        機能させ、以降 Session の Recorder open/close 中に tracker の
        COM が同時実行されないことを保証する。
        """
        tracker = self._mic_endpoint_tracker
        if tracker is None:
            return
        tracker.pause()
        # バリア: tracker が _com_lock (=pyaudio_op_lock) 保持中なら待つ
        # (上限あり、詳細は _PAUSE_BARRIER_TIMEOUT_SEC のコメント参照)
        acquired = pyaudio_op_lock.acquire(timeout=_PAUSE_BARRIER_TIMEOUT_SEC)
        if acquired:
            pyaudio_op_lock.release()
        else:
            printLog(
                f"pauseMicEndpointTracker: barrier timed out after "
                f"{_PAUSE_BARRIER_TIMEOUT_SEC}s waiting for pyaudio_op_lock; "
                "a COM call may be stuck. Proceeding without the barrier."
            )

    def resumeMicEndpointTracker(self) -> None:
        tracker = self._mic_endpoint_tracker
        if tracker is not None:
            tracker.resume()

    def pauseSpeakerEndpointTracker(self) -> None:
        """スピーカー側 tracker の一時停止。詳細は pauseMicEndpointTracker 参照。"""
        tracker = self._speaker_endpoint_tracker
        if tracker is None:
            return
        tracker.pause()
        acquired = pyaudio_op_lock.acquire(timeout=_PAUSE_BARRIER_TIMEOUT_SEC)
        if acquired:
            pyaudio_op_lock.release()
        else:
            printLog(
                f"pauseSpeakerEndpointTracker: barrier timed out after "
                f"{_PAUSE_BARRIER_TIMEOUT_SEC}s waiting for pyaudio_op_lock; "
                "a COM call may be stuck. Proceeding without the barrier."
            )

    def resumeSpeakerEndpointTracker(self) -> None:
        tracker = self._speaker_endpoint_tracker
        if tracker is not None:
            tracker.resume()

    def _onActiveMicEndpointChanged(self, endpoint_name: Optional[str]) -> None:
        """Tracker からのコールバック (別スレッド)。

        アクティブな capture エンドポイント名 (FriendlyName) を受け取り、
        現在のマイクデバイスリストからマッチする (host, device) を検索、
        以下の 2 段で反映する:
          1. callback_default_mic_device: config 更新 + UI 通知
          2. callback_endpoint_reconfigured_mic: Session の Recorder を新デバイスに差し替え
        マッチが無い場合は何もしない (Multimedia default 追跡が生きる)。
        """
        if endpoint_name is None:
            return
        try:
            host, device_name = self._findMicDeviceByName(endpoint_name)
        except Exception:
            errorLogging()
            return
        if host is None or device_name is None:
            return
        if isinstance(self.callback_default_mic_device, Callable):
            try:
                self.callback_default_mic_device(host, device_name)
            except Exception:
                errorLogging()
        if isinstance(self.callback_endpoint_reconfigured_mic, Callable):
            try:
                self.callback_endpoint_reconfigured_mic()
            except Exception:
                errorLogging()

    def _onActiveSpeakerEndpointChanged(self, endpoint_name: Optional[str]) -> None:
        """Tracker からのコールバック (別スレッド)。詳細は
        _onActiveMicEndpointChanged 参照。スピーカー側は loopback デバイス
        (末尾 " [Loopback]") とのマッピング調整が必要。
        """
        if endpoint_name is None:
            return
        try:
            device_name = self._findSpeakerDeviceByName(endpoint_name)
        except Exception:
            errorLogging()
            return
        if device_name is None:
            return
        if isinstance(self.callback_default_speaker_device, Callable):
            try:
                self.callback_default_speaker_device(device_name)
            except Exception:
                errorLogging()
        if isinstance(self.callback_endpoint_reconfigured_speaker, Callable):
            try:
                self.callback_endpoint_reconfigured_speaker()
            except Exception:
                errorLogging()

    def _findMicDeviceByName(self, endpoint_name: str) -> tuple:
        """FriendlyName に一致するマイクデバイスを (host, device_name) で返す。

        WASAPI ホストを優先する (pycaw の endpoint は WASAPI 世界の名称と
        1:1 対応、他ホストは名前がトランケートされる可能性)。WASAPI に
        無ければ全ホストから完全一致を探し、最後に前方一致で救う。
        比較は両サイドとも strip() 済みの文字列で行う (Realtek 系ドライバ
        などが device 名に trailing space を含む事例があるため)。
        """
        target = endpoint_name.strip()
        mic_devices = self.mic_devices
        wasapi_key = next(
            (host for host in mic_devices.keys() if "WASAPI" in host), None
        )
        if wasapi_key is not None:
            for d in mic_devices[wasapi_key]:
                if (d.get("name") or "").strip() == target:
                    return wasapi_key, d["name"]
        # WASAPI 外の完全一致
        for host, devs in mic_devices.items():
            for d in devs:
                if (d.get("name") or "").strip() == target:
                    return host, d["name"]
        # 前方一致 (MME 系はデバイス名が 31 文字で切られるため)
        for host, devs in mic_devices.items():
            for d in devs:
                name = (d.get("name") or "").strip()
                if name and target.startswith(name):
                    return host, d["name"]
        return None, None

    def _findSpeakerDeviceByName(self, endpoint_name: str) -> Optional[str]:
        """FriendlyName に一致するスピーカー (loopback) デバイス名を返す。

        pyaudiowpatch のスピーカーデバイス名は "<friendly> [Loopback]" 形式。
        pycaw の FriendlyName に " [Loopback]" を付けた候補が
        speaker_devices に存在するかを確認する。比較は両サイドとも
        strip() 済みで行う (詳細は _findMicDeviceByName 参照)。
        """
        target = endpoint_name.strip()
        loopback_target = f"{target} [Loopback]"
        for d in self.speaker_devices:
            if (d.get("name") or "").strip() == loopback_target:
                return d["name"]
        # 前方一致救済
        for d in self.speaker_devices:
            name = (d.get("name") or "").strip()
            if name and name.startswith(target):
                return d["name"]
        return None

    def _syncMonitoringLifecycle(self) -> None:
        """mic/speaker の active フラグに応じて monitoring スレッドを起動/停止。

        少なくとも 1 サイドが active なら起動、両方 inactive なら停止。
        個々の設定変更 (setMicAutoActive/setSpeakerAutoActive) の後に呼ぶ。
        """
        any_active = self._mic_auto_active or self._speaker_auto_active
        if any_active:
            self.startMonitoring()
        else:
            self.stopMonitoring()

    def stopMonitoring(self):
        """非ブロッキング stop。event を set して短時間だけ join を試みる。

        以前は join(timeout=5) だったが、内部ループが flag を最大 20s 見て
        いなかったため endpoint 呼び出しが 5s 丸ごとブロックされていた。
        現在は Event ベースなのでスレッドは即抜ける想定 (数十 ms 以内)。
        万一 COM 呼び出しなどで抜けが遅れても endpoint を待たせないよう、
        join タイムアウトは 0.5s に短縮した (daemon スレッドなのでプロセス
        終了時に確実に片付く)。
        """
        self._stop_event.set()
        # notify_event は init/startMonitoring で確実に生成済み (再代入は
        # startMonitoring では行わない設計に統一)。COM 通知待ちで止まって
        # いるスレッドを即座に起こす。
        self._notify_event.set()
        if getattr(self, "th_monitoring", None) is not None:
            try:
                self.th_monitoring.join(timeout=0.5)
            except Exception:
                # join がスレッド非依存の理由で失敗しても致命的ではない
                pass

    def setCallbackDefaultMicDevice(self, callback):
        self.callback_default_mic_device = callback

    def clearCallbackDefaultMicDevice(self):
        self.callback_default_mic_device = None

    def setCallbackDefaultSpeakerDevice(self, callback):
        self.callback_default_speaker_device = callback

    def clearCallbackDefaultSpeakerDevice(self):
        self.callback_default_speaker_device = None

    def setCallbackHostList(self, callback):
        self.callback_host_list = callback

    def clearCallbackHostList(self):
        self.callback_host_list = None

    def setCallbackMicDeviceList(self, callback):
        self.callback_mic_device_list = callback

    def clearCallbackMicDeviceList(self):
        self.callback_mic_device_list = None

    def setCallbackSpeakerDeviceList(self, callback):
        self.callback_speaker_device_list = callback

    def clearCallbackSpeakerDeviceList(self):
        self.callback_speaker_device_list = None

    def setCallbackProcessBeforeUpdateMicDevices(self, callback):
        self.callback_process_before_update_mic_devices = callback

    def clearCallbackProcessBeforeUpdateMicDevices(self):
        self.callback_process_before_update_mic_devices = None

    def runProcessBeforeUpdateMicDevices(self):
        if isinstance(self.callback_process_before_update_mic_devices, Callable):
            try:
                self.callback_process_before_update_mic_devices()
            except Exception:
                errorLogging()

    def setCallbackProcessAfterUpdateMicDevices(self, callback):
        self.callback_process_after_update_mic_devices = callback

    def clearCallbackProcessAfterUpdateMicDevices(self):
        self.callback_process_after_update_mic_devices = None

    def runProcessAfterUpdateMicDevices(self):
        if isinstance(self.callback_process_after_update_mic_devices, Callable):
            try:
                self.callback_process_after_update_mic_devices()
            except Exception:
                errorLogging()

    def setCallbackProcessBeforeUpdateSpeakerDevices(self, callback):
        self.callback_process_before_update_speaker_devices = callback

    def clearCallbackProcessBeforeUpdateSpeakerDevices(self):
        self.callback_process_before_update_speaker_devices = None

    def runProcessBeforeUpdateSpeakerDevices(self):
        if isinstance(self.callback_process_before_update_speaker_devices, Callable):
            try:
                self.callback_process_before_update_speaker_devices()
            except Exception:
                errorLogging()

    def setCallbackProcessAfterUpdateSpeakerDevices(self, callback):
        self.callback_process_after_update_speaker_devices = callback

    def clearCallbackProcessAfterUpdateSpeakerDevices(self):
        self.callback_process_after_update_speaker_devices = None

    def runProcessAfterUpdateSpeakerDevices(self):
        if isinstance(self.callback_process_after_update_speaker_devices, Callable):
            try:
                self.callback_process_after_update_speaker_devices()
            except Exception:
                errorLogging()

    def setCallbackEndpointReconfiguredMic(self, callback):
        self.callback_endpoint_reconfigured_mic = callback

    def clearCallbackEndpointReconfiguredMic(self):
        self.callback_endpoint_reconfigured_mic = None

    def setCallbackEndpointReconfiguredSpeaker(self, callback):
        self.callback_endpoint_reconfigured_speaker = callback

    def clearCallbackEndpointReconfiguredSpeaker(self):
        self.callback_endpoint_reconfigured_speaker = None

    def noticeUpdateDevices(self):
        if self.update_flag_default_mic_device is True:
            self.setMicDefaultDevice()
        if self.update_flag_default_speaker_device is True:
            self.setSpeakerDefaultDevice()
        if self.update_flag_host_list is True:
            self.setMicHostList()
        if self.update_flag_mic_device_list is True:
            self.setMicDeviceList()
        if self.update_flag_speaker_device_list is True:
            self.setSpeakerDeviceList()

        self.update_flag_default_mic_device = False
        self.update_flag_default_speaker_device = False
        self.update_flag_host_list = False
        self.update_flag_mic_device_list = False
        self.update_flag_speaker_device_list = False

    def setMicDefaultDevice(self):
        if isinstance(self.callback_default_mic_device, Callable):
            try:
                self.callback_default_mic_device(self.default_mic_device["host"]["name"], self.default_mic_device["device"]["name"])
            except Exception:
                errorLogging()

    def setSpeakerDefaultDevice(self):
        if isinstance(self.callback_default_speaker_device, Callable):
            try:
                self.callback_default_speaker_device(self.default_speaker_device["device"]["name"])
            except Exception:
                errorLogging()

    def setMicHostList(self):
        if isinstance(self.callback_host_list, Callable):
            try:
                self.callback_host_list()
            except Exception:
                errorLogging()

    def setMicDeviceList(self):
        if isinstance(self.callback_mic_device_list, Callable):
            try:
                self.callback_mic_device_list()
            except Exception:
                errorLogging()

    def setSpeakerDeviceList(self):
        if isinstance(self.callback_speaker_device_list, Callable):
            try:
                self.callback_speaker_device_list()
            except Exception:
                errorLogging()

    def getMicDevices(self):
        # Ensure initialized and return devices (safe default if still not populated)
        if not getattr(self, '_initialized', False):
            try:
                self.init()
            except Exception:
                try:
                    errorLogging()
                except Exception:
                    pass
        return getattr(self, 'mic_devices', {"NoHost": [{"index": -1, "name": "NoDevice"}]})

    def getDefaultMicDevice(self):
        # Ensure initialized and return default mic device (safe default if still not populated)
        if not getattr(self, '_initialized', False):
            try:
                self.init()
            except Exception:
                try:
                    errorLogging()
                except Exception:
                    pass
        return getattr(self, 'default_mic_device', {"host": {"index": -1, "name": "NoHost"}, "device": {"index": -1, "name": "NoDevice"}})

    def getSpeakerDevices(self):
        # Ensure initialized and return speaker devices (safe default if still not populated)
        if not getattr(self, '_initialized', False):
            try:
                self.init()
            except Exception:
                try:
                    errorLogging()
                except Exception:
                    pass
        return getattr(self, 'speaker_devices', [{"index": -1, "name": "NoDevice"}])

    def getDefaultSpeakerDevice(self):
        # Ensure initialized and return default speaker device (safe default if still not populated)
        if not getattr(self, '_initialized', False):
            try:
                self.init()
            except Exception:
                try:
                    errorLogging()
                except Exception:
                    pass
        return getattr(self, 'default_speaker_device', {"device": {"index": -1, "name": "NoDevice"}})

    def forceUpdateAndSetMicDevices(self):
        self.update()
        self.setMicHostList()
        self.setMicDeviceList()
        self.setMicDefaultDevice()

    def forceUpdateAndSetSpeakerDevices(self):
        self.update()
        self.setSpeakerDeviceList()
        self.setSpeakerDefaultDevice()

# Provide a module-level singleton. Call `device_manager.init()` explicitly to
# initialize audio resources and `device_manager.startMonitoring()` to begin
# background monitoring. This avoids side-effects during simple imports.
device_manager = DeviceManager()

if __name__ == "__main__":
    print("DeviceManager demo. Call device_manager.init() and device_manager.startMonitoring() to run live monitoring.")
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        print("exiting")