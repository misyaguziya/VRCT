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

from utils import errorLogging

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

    def checkUpdate(self):
        """デバイス一覧の差分を検出し、update_flag_* を立てて prev_* を更新する。

        名前は "check" だが実際には副作用 (flag 立て + prev 上書き) を持つ。
        monitoring ループから 1 回のみ呼ばれる前提。他所から呼ぶと prev_* が
        意図せず上書きされ、次回の差分検知が不正確になる。
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

        update_flag = (
            self.update_flag_default_mic_device or
            self.update_flag_default_speaker_device or
            self.update_flag_host_list or
            self.update_flag_mic_device_list or
            self.update_flag_speaker_device_list
        )
        return update_flag

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
                    self.checkUpdate()
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
        # notify_event は monitoring スレッド起動と同時に用意する。
        # COM callback スレッドと monitoring スレッド間のイベント受け渡しに使う。
        self._notify_event = Event()
        self.th_monitoring = Thread(target=self.monitoring, daemon=True)
        self.th_monitoring.start()

    def setMicAutoActive(self, active: bool) -> None:
        """Auto Mic Select の有効/無効を DeviceManager 側で受け取る。

        監視スレッドの起動/停止判断はここで完結させ、controller 側が
        相手側 (speaker) の状態を見て判断する必要を無くす。
        """
        self._mic_auto_active = active
        self._syncMonitoringLifecycle()

    def setSpeakerAutoActive(self, active: bool) -> None:
        """Auto Speaker Select の有効/無効を DeviceManager 側で受け取る。
        詳細は setMicAutoActive のコメント参照。"""
        self._speaker_auto_active = active
        self._syncMonitoringLifecycle()

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
        # notify_event も併せて set しておくと、COM 通知待ちで止まっている
        # スレッドが即座に wait を抜ける。
        notify_event = getattr(self, "_notify_event", None)
        if isinstance(notify_event, Event):
            notify_event.set()
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