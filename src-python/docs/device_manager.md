# device_manager.py 設計書

## 概要

`device_manager.py` は VRCT アプリケーションの音声デバイス管理を担当するモジュールであり、マイクとスピーカーデバイスの検出、監視、自動選択機能を提供する。Windows の WASAPI や pycaw ライブラリを使用してリアルタイムなデバイス変更を検知し、登録されたコールバック関数を通じてアプリケーションに通知する。シングルトンパターンで実装され、遅延初期化により import 時のパフォーマンス低下を回避している。

## アーキテクチャ上の位置づけ

```
┌─────────────┐
│controller.py│ (Business Logic Control Layer)
└──────┬──────┘
       │ Callback Registration & Query
┌──────▼──────────┐
│device_manager.py│ ◄── このファイル
└──────┬──────────┘
       │ Device Monitoring & Enumeration
┌──────▼─────────────────────────────┐
│ OS Audio Subsystems                │
│ - PyAudio (PortAudio wrapper)      │
│ - pyaudiowpatch (WASAPI loopback)  │
│ - pycaw (COM notifications)        │
│ - comtypes (COM initialization)    │
└────────────────────────────────────┘
```

## 主要コンポーネント

### 1. Client クラス

**責務:** Windows の COM イベントコールバックを受け取り、デバイス変更を検知

**継承:** `pycaw.callbacks.MMNotificationClient`

**設計パターン:** Observer パターンのコールバック実装

#### コンストラクタ `__init__()`

**処理:**
```python
try:
    super().__init__()
except Exception:
    pass  # 非 Windows 環境ではプレースホルダーオブジェクトのため例外を無視
self.loop: bool = True
```

**`self.loop` フラグ:** 
- True: デバイス変更なし、監視継続
- False: デバイス変更検知、監視ループを中断

#### イベントハンドラー

##### `on_default_device_changed(*args, **kwargs) -> None`
デフォルトデバイスが変更された時に Windows から呼び出される。

##### `on_device_added(*args, **kwargs) -> None`
新しいデバイスが接続された時に呼び出される。

##### `on_device_removed(*args, **kwargs) -> None`
デバイスが取り外された時に呼び出される。

##### `on_device_state_changed(*args, **kwargs) -> None`
デバイスの状態（有効/無効/存在しない等）が変更された時に呼び出される。

**すべてのハンドラーの動作:**
```python
self.loop = False  # 監視ループに変更を通知
```

**コメントアウトされたメソッド:**
```python
# def on_property_value_changed(self, device_id, key):
#     self.loop = False
```
デバイスプロパティの変更イベント。使用しない理由は不明だが、頻繁なイベント発火によるパフォーマンス低下を避けるためと推測される。

---

### 2. DeviceManager クラス

**責務:** アプリケーション全体のデバイス管理機能を提供

**パターン:** シングルトン（`__new__` で制御）

**プラットフォーム対応:** 
- Windows: 完全な機能サポート（COM イベント監視、WASAPI loopback）
- 非 Windows: グレースフルデグレード（デフォルト値を返却、監視機能は制限的）

---

### 3. 初期化メソッド

#### `__new__(cls) -> DeviceManager`

**責務:** シングルトンインスタンスの生成と軽量な初期化

**処理フロー:**
1. **インスタンスチェック:**
   ```python
   if cls._instance is None:
       cls._instance = super(DeviceManager, cls).__new__(cls)
   ```
2. **軽量な初期化:**
   ```python
   cls._instance._initialized = False
   try:
       cls._instance.init()
   except Exception:
       try:
           errorLogging()
       except Exception:
           pass  # import 時のクラッシュを絶対に避ける
   ```
3. **既存インスタンスの返却:**
   ```python
   return cls._instance
   ```

**設計思想:**
- `__new__` では重い初期化を避ける（スレッド起動、OS API アクセスなし）
- `init()` を呼び出すが、監視スレッドは起動しない
- エラー時も必ずインスタンスを返却（防御的プログラミング）

#### `init() -> None`

**責務:** 内部状態の初期化とデバイス情報の初回取得

**処理フロー:**

**1. 初期化済みチェック:**
```python
if getattr(self, "_initialized", False):
    return  # 既に初期化済みなら何もしない
```

**2. デバイス情報の初期化（デフォルト値）:**
```python
self.mic_devices: Dict[str, List[Dict[str, Any]]] = {
    "NoHost": [{"index": -1, "name": "NoDevice"}]
}
self.default_mic_device: Dict[str, Any] = {
    "host": {"index": -1, "name": "NoHost"},
    "device": {"index": -1, "name": "NoDevice"}
}
self.speaker_devices: List[Dict[str, Any]] = [
    {"index": -1, "name": "NoDevice"}
]
self.default_speaker_device: Dict[str, Any] = {
    "device": {"index": -1, "name": "NoDevice"}
}
```

**3. 前回状態のトラッカー:**
```python
self.prev_mic_host: List[str] = [host for host in self.mic_devices]
self.prev_mic_devices: Dict[str, List[Dict[str, Any]]] = self.mic_devices
self.prev_default_mic_device: Dict[str, Any] = self.default_mic_device
self.prev_speaker_devices: List[Dict[str, Any]] = self.speaker_devices
self.prev_default_speaker_device: Dict[str, Any] = self.default_speaker_device
```

**4. 更新フラグ:**
```python
self.update_flag_default_mic_device: bool = False
self.update_flag_default_speaker_device: bool = False
self.update_flag_host_list: bool = False
self.update_flag_mic_device_list: bool = False
self.update_flag_speaker_device_list: bool = False
```

**5. コールバック関数:**
```python
self.callback_default_mic_device: Optional[Callable[..., None]] = None
self.callback_default_speaker_device: Optional[Callable[..., None]] = None
self.callback_host_list: Optional[Callable[..., None]] = None
self.callback_mic_device_list: Optional[Callable[..., None]] = None
self.callback_speaker_device_list: Optional[Callable[..., None]] = None
self.callback_process_before_update_mic_devices: Optional[Callable[..., None]] = None
self.callback_process_after_update_mic_devices: Optional[Callable[..., None]] = None
self.callback_process_before_update_speaker_devices: Optional[Callable[..., None]] = None
self.callback_process_after_update_speaker_devices: Optional[Callable[..., None]] = None
```

**6. 監視制御:**
```python
self.monitoring_flag: bool = False
self.th_monitoring: Optional[Thread] = None
```

**7. 初期化完了フラグ:**
```python
self._initialized = True
```

**8. ベストエフォートのデバイス情報取得:**
```python
try:
    if PyAudio is not None:
        try:
            self.update()  # 実デバイス情報を取得
        except Exception:
            errorLogging()
except Exception:
    pass  # 初期化失敗でもクラッシュしない
```

**設計思想:**
- すべての属性をデフォルト値で初期化（未初期化エラーを回避）
- `update()` の失敗は許容（デバイスがない環境でも動作）
- エラーは記録するが、例外を外部に投げない

---

### 4. デバイス情報更新メソッド

#### `update() -> None`

**責務:** 現在の音声デバイス一覧とデフォルトデバイスを取得

**処理フロー:**

**1. バッファの初期化:**
```python
buffer_mic_devices: Dict[str, List[Dict[str, Any]]] = {}
buffer_default_mic_device: Dict[str, Any] = {
    "host": {"index": -1, "name": "NoHost"},
    "device": {"index": -1, "name": "NoDevice"}
}
buffer_speaker_devices: List[Dict[str, Any]] = []
buffer_default_speaker_device: Dict[str, Any] = {
    "device": {"index": -1, "name": "NoDevice"}
}
```

**2. PyAudio 可用性チェック:**
```python
if PyAudio is None:
    # デフォルト値のまま終了
    self.mic_devices = buffer_mic_devices or {"NoHost": [{"index": -1, "name": "NoDevice"}]}
    # ... 他のデバイス情報も設定
    return
```

**3. マイクデバイスの収集:**
```python
with PyAudio() as p:
    for host_index in range(p.get_host_api_count()):
        host = p.get_host_api_info_by_index(host_index)
        device_count = host.get('deviceCount', 0)
        for device_index in range(device_count):
            device = p.get_device_info_by_host_api_device_index(host_index, device_index)
            # 入力チャンネルがあり、ループバックではないデバイス
            if device.get("maxInputChannels", 0) > 0 and not device.get("isLoopbackDevice", True):
                buffer_mic_devices.setdefault(host["name"], []).append(device)
```

**ホスト API の例:**
- Windows: "MME", "Windows DirectSound", "Windows WASAPI"
- Linux: "ALSA", "PulseAudio"
- macOS: "Core Audio"

**4. デフォルトマイクデバイスの取得:**
```python
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
```

**5. スピーカーループバックデバイスの収集:**
```python
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
                        # ループバックデバイスを検索
                        for loopback in p.get_loopback_device_info_generator():
                            if device.get("name") in loopback.get("name", ""):
                                speaker_devices.append(loopback)
    except Exception:
        pass  # WASAPI が利用できない場合は無視
```

**ループバックデバイスとは:**
- スピーカーから出力される音声を「録音」できる仮想デバイス
- "Stereo Mix" や "What U Hear" のような名前
- VRChat の相手の音声を認識するために使用

**6. 重複排除とソート:**
```python
speaker_devices = [dict(t) for t in {tuple(d.items()) for d in speaker_devices}] or [{"index": -1, "name": "NoDevice"}]
buffer_speaker_devices = sorted(speaker_devices, key=lambda d: d.get('index', -1))
```

**7. デフォルトスピーカーデバイスの取得:**
```python
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
        pass
```

**8. エラーハンドリングと最終設定:**
```python
except Exception:
    errorLogging()

self.mic_devices = buffer_mic_devices
self.default_mic_device = buffer_default_mic_device
self.speaker_devices = buffer_speaker_devices
self.default_speaker_device = buffer_default_speaker_device
```

**デバイス情報の構造例:**
```python
# マイクデバイス
self.mic_devices = {
    "Windows WASAPI": [
        {"index": 0, "name": "Microphone (Realtek)", "maxInputChannels": 2, ...},
        {"index": 3, "name": "Line In (USB Audio)", "maxInputChannels": 2, ...}
    ],
    "MME": [
        {"index": 10, "name": "マイク (Realtek)", "maxInputChannels": 2, ...}
    ]
}

# デフォルトマイクデバイス
self.default_mic_device = {
    "host": {"index": 0, "name": "Windows WASAPI", ...},
    "device": {"index": 0, "name": "Microphone (Realtek)", ...}
}
```

---

### 5. 変更検出メソッド

#### `checkUpdate() -> bool`

**責務:** 前回取得したデバイス情報との差分を検出し、更新フラグを設定

**処理:**

**1. デフォルトマイクデバイスの変更チェック:**
```python
if self.prev_default_mic_device["device"]["name"] != self.default_mic_device["device"]["name"]:
    self.update_flag_default_mic_device = True
    self.prev_default_mic_device = self.default_mic_device
```

**2. デフォルトスピーカーデバイスの変更チェック:**
```python
if self.prev_default_speaker_device["device"]["name"] != self.default_speaker_device["device"]["name"]:
    self.update_flag_default_speaker_device = True
    self.prev_default_speaker_device = self.default_speaker_device
```

**3. マイクホストリストの変更チェック:**
```python
if self.prev_mic_host != [host for host in self.mic_devices]:
    self.update_flag_host_list = True
    self.prev_mic_host = [host for host in self.mic_devices]
```

**4. マイクデバイスリストの変更チェック:**
```python
if ({key: [device['name'] for device in devices] for key, devices in self.prev_mic_devices.items()} !=
    {key: [device['name'] for device in devices] for key, devices in self.mic_devices.items()}):
    self.update_flag_mic_device_list = True
    self.prev_mic_devices = self.mic_devices
```

**比較方法:**
- デバイス名のリストのみを比較（`index` の変化は無視）
- ホストごとにグループ化して比較

**5. スピーカーデバイスリストの変更チェック:**
```python
if [device['name'] for device in self.prev_speaker_devices] != [device['name'] for device in self.speaker_devices]:
    self.update_flag_speaker_device_list = True
    self.prev_speaker_devices = self.speaker_devices
```

**6. 総合的な更新フラグの判定:**
```python
update_flag = (
    self.update_flag_default_mic_device or
    self.update_flag_default_speaker_device or
    self.update_flag_host_list or
    self.update_flag_mic_device_list or
    self.update_flag_speaker_device_list
)
return update_flag
```

**戻り値:**
- `True`: いずれかのデバイス情報が変更された
- `False`: すべてのデバイス情報が前回と同一

---

### 6. 監視メソッド

#### `monitoring() -> None`

**責務:** バックグラウンドでデバイス変更を監視し、変更時にコールバックを実行

**実行環境:** 別スレッド（`startMonitoring()` で起動）

**処理フロー:**

**1. 監視ループ:**
```python
try:
    while self.monitoring_flag is True:
        try:
            # 監視処理
        except Exception:
            errorLogging()
except Exception:
    errorLogging()
```

**2. COM イベント監視（Windows のみ）:**
```python
if comtypes is not None and AudioUtilities is not None:
    try:
        comtypes.CoInitialize()  # COM の初期化
        cb = Client()
        enumerator = AudioUtilities.GetDeviceEnumerator()
        enumerator.RegisterEndpointNotificationCallback(cb)
        
        while cb.loop is True and self.monitoring_flag is True:
            sleep(1)  # イベント待機
        
        try:
            enumerator.UnregisterEndpointNotificationCallback(cb)
        except Exception:
            pass  # ベストエフォート
        comtypes.CoUninitialize()
    except Exception:
        errorLogging()
```

**COM 監視の動作:**
- `Client` クラスのイベントハンドラーがデバイス変更を検知
- `cb.loop` が `False` になるとループを抜ける
- COM が利用できない場合はポーリングにフォールバック

**3. ポーリングと更新サイクル:**
```python
# 更新前の処理
self.runProcessBeforeUpdateMicDevices()
self.runProcessBeforeUpdateSpeakerDevices()

sleep(2)  # デバイス状態の安定を待つ

# 最大10回（20秒間）ポーリング
for _ in range(10):
    self.update()
    if self.checkUpdate():
        break  # 変更を検知したら終了
    sleep(2)

# コールバック通知
self.noticeUpdateDevices()

# 更新後の処理
self.runProcessAfterUpdateMicDevices()
self.runProcessAfterUpdateSpeakerDevices()
```

**ポーリング戦略:**
- 初回 2 秒待機: デバイスの接続/切断後の不安定期間を回避
- 最大 10 回ポーリング: デバイス変更を見逃さない
- 変更検知後は即座に次の処理へ

**4. 監視サイクルの繰り返し:**
```python
# while self.monitoring_flag is True の先頭に戻る
```

#### `startMonitoring() -> None`

**責務:** 監視スレッドの起動

**処理:**
```python
if self.monitoring_flag:
    return  # 既に起動中
self.monitoring_flag = True
self.th_monitoring = Thread(target=self.monitoring)
self.th_monitoring.daemon = True
self.th_monitoring.start()
```

**デーモンスレッド:**
- メインスレッド終了時に自動的に終了
- アプリケーション終了を妨げない

#### `stopMonitoring() -> None`

**責務:** 監視スレッドの停止

**処理:**
```python
self.monitoring_flag = False
if getattr(self, "th_monitoring", None) is not None:
    try:
        self.th_monitoring.join(timeout=5)  # 最大5秒待機
    except Exception:
        pass  # ベストエフォート
```

**タイムアウト設定:**
- 5 秒以内に終了しない場合は待機を諦める
- スレッドの join に失敗してもエラーを無視（防御的）

---

### 7. コールバック管理メソッド

#### デフォルトデバイス変更コールバック

##### `setCallbackDefaultMicDevice(callback: Callable[..., None]) -> None`
デフォルトマイクデバイス変更時のコールバックを登録。

**コールバックシグネチャ:**
```python
def callback(host_name: str, device_name: str) -> None:
    pass
```

##### `clearCallbackDefaultMicDevice() -> None`
コールバックをクリア。

##### `setCallbackDefaultSpeakerDevice(callback: Callable[..., None]) -> None`
デフォルトスピーカーデバイス変更時のコールバックを登録。

**コールバックシグネチャ:**
```python
def callback(device_name: str) -> None:
    pass
```

##### `clearCallbackDefaultSpeakerDevice() -> None`
コールバックをクリア。

#### デバイスリスト変更コールバック

##### `setCallbackHostList(callback: Callable[..., None]) -> None`
マイクホストリスト変更時のコールバックを登録。

##### `clearCallbackHostList() -> None`
コールバックをクリア。

##### `setCallbackMicDeviceList(callback: Callable[..., None]) -> None`
マイクデバイスリスト変更時のコールバックを登録。

##### `clearCallbackMicDeviceList() -> None`
コールバックをクリア。

##### `setCallbackSpeakerDeviceList(callback: Callable[..., None]) -> None`
スピーカーデバイスリスト変更時のコールバックを登録。

##### `clearCallbackSpeakerDeviceList() -> None`
コールバックをクリア。

#### 処理フックコールバック

##### `setCallbackProcessBeforeUpdateMicDevices(callback: Callable[..., None]) -> None`
マイクデバイス更新前の処理を登録。

**使用例:** 音声認識を停止してデバイスを解放

##### `clearCallbackProcessBeforeUpdateMicDevices() -> None`
コールバックをクリア。

##### `setCallbackProcessAfterUpdateMicDevices(callback: Callable[..., None]) -> None`
マイクデバイス更新後の処理を登録。

**使用例:** 新しいデバイスで音声認識を再開

##### `clearCallbackProcessAfterUpdateMicDevices() -> None`
コールバックをクリア。

##### `setCallbackProcessBeforeUpdateSpeakerDevices(callback: Callable[..., None]) -> None`
スピーカーデバイス更新前の処理を登録。

##### `clearCallbackProcessBeforeUpdateSpeakerDevices() -> None`
コールバックをクリア。

##### `setCallbackProcessAfterUpdateSpeakerDevices(callback: Callable[..., None]) -> None`
スピーカーデバイス更新後の処理を登録。

##### `clearCallbackProcessAfterUpdateSpeakerDevices() -> None`
コールバックをクリア。

---

### 8. コールバック実行メソッド

#### `runProcessBeforeUpdateMicDevices() -> None`

**責務:** マイクデバイス更新前の処理コールバックを実行

**処理:**
```python
if isinstance(self.callback_process_before_update_mic_devices, Callable):
    try:
        self.callback_process_before_update_mic_devices()
    except Exception:
        errorLogging()
```

**型チェック:**
- `isinstance(callback, Callable)` で呼び出し可能性を確認
- `None` の場合は何もしない

#### `runProcessAfterUpdateMicDevices() -> None`
マイクデバイス更新後の処理コールバックを実行（同様の実装）。

#### `runProcessBeforeUpdateSpeakerDevices() -> None`
スピーカーデバイス更新前の処理コールバックを実行（同様の実装）。

#### `runProcessAfterUpdateSpeakerDevices() -> None`
スピーカーデバイス更新後の処理コールバックを実行（同様の実装）。

---

### 9. 通知メソッド

#### `noticeUpdateDevices() -> None`

**責務:** 更新フラグに応じて対応するコールバックを呼び出し、フラグをリセット

**処理:**
```python
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

# すべてのフラグをリセット
self.update_flag_default_mic_device = False
self.update_flag_default_speaker_device = False
self.update_flag_host_list = False
self.update_flag_mic_device_list = False
self.update_flag_speaker_device_list = False
```

#### `setMicDefaultDevice() -> None`

**責務:** デフォルトマイクデバイス変更コールバックの実行

**処理:**
```python
if isinstance(self.callback_default_mic_device, Callable):
    try:
        self.callback_default_mic_device(
            self.default_mic_device["host"]["name"],
            self.default_mic_device["device"]["name"]
        )
    except Exception:
        errorLogging()
```

#### `setSpeakerDefaultDevice() -> None`

**責務:** デフォルトスピーカーデバイス変更コールバックの実行

**処理:**
```python
if isinstance(self.callback_default_speaker_device, Callable):
    try:
        self.callback_default_speaker_device(
            self.default_speaker_device["device"]["name"]
        )
    except Exception:
        errorLogging()
```

#### `setMicHostList() -> None`
マイクホストリスト変更コールバックの実行（引数なし）。

#### `setMicDeviceList() -> None`
マイクデバイスリスト変更コールバックの実行（引数なし）。

#### `setSpeakerDeviceList() -> None`
スピーカーデバイスリスト変更コールバックの実行（引数なし）。

---

### 10. デバイス情報取得メソッド

#### `getMicDevices() -> Dict[str, List[Dict[str, Any]]]`

**責務:** マイクデバイス一覧を取得

**処理:**
```python
if not getattr(self, '_initialized', False):
    try:
        self.init()
    except Exception:
        try:
            errorLogging()
        except Exception:
            pass
return getattr(self, 'mic_devices', {"NoHost": [{"index": -1, "name": "NoDevice"}]})
```

**安全性:**
- 未初期化の場合は `init()` を呼び出す
- 失敗時はデフォルト値を返却

**戻り値の例:**
```python
{
    "Windows WASAPI": [
        {"index": 0, "name": "Microphone (Realtek)", ...},
        {"index": 3, "name": "Line In (USB Audio)", ...}
    ],
    "MME": [
        {"index": 10, "name": "マイク (Realtek)", ...}
    ]
}
```

#### `getDefaultMicDevice() -> Dict[str, Any]`

**責務:** デフォルトマイクデバイスを取得

**戻り値の例:**
```python
{
    "host": {"index": 0, "name": "Windows WASAPI", ...},
    "device": {"index": 0, "name": "Microphone (Realtek)", ...}
}
```

#### `getSpeakerDevices() -> List[Dict[str, Any]]`

**責務:** スピーカーデバイス一覧を取得

**戻り値の例:**
```python
[
    {"index": 5, "name": "Stereo Mix (Realtek)", "isLoopbackDevice": True, ...},
    {"index": 7, "name": "Speakers (USB Audio) [Loopback]", ...}
]
```

#### `getDefaultSpeakerDevice() -> Dict[str, Any]`

**責務:** デフォルトスピーカーデバイスを取得

**戻り値の例:**
```python
{
    "device": {"index": 5, "name": "Stereo Mix (Realtek)", ...}
}
```

---

### 11. 強制更新メソッド

#### `forceUpdateAndSetMicDevices() -> None`

**責務:** マイクデバイス情報を強制的に更新し、すべてのコールバックを実行

**処理:**
```python
self.update()
self.setMicHostList()
self.setMicDeviceList()
self.setMicDefaultDevice()
```

**使用場面:**
- 自動デバイス選択機能の初回適用時
- ユーザーが手動で更新を要求した時

#### `forceUpdateAndSetSpeakerDevices() -> None`

**責務:** スピーカーデバイス情報を強制的に更新

**処理:**
```python
self.update()
self.setSpeakerDeviceList()
self.setSpeakerDefaultDevice()
```

---

### 12. モジュールレベルの使用方法

#### シングルトンインスタンス

```python
device_manager = DeviceManager()
```

**モジュールをインポートするだけで使用可能:**
```python
from device_manager import device_manager

# デバイス情報取得
mic_devices = device_manager.getMicDevices()
```

#### デモスクリプト

```python
if __name__ == "__main__":
    print("DeviceManager demo. Call device_manager.init() and device_manager.startMonitoring() to run live monitoring.")
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        print("exiting")
```

**実行方法:**
```powershell
python device_manager.py
```

---

## 依存関係

### 外部ライブラリ

```python
from typing import Callable, Dict, List, Optional, Any
from time import sleep
from threading import Thread
```

### オプショナル依存（Windows 専用）

```python
import comtypes  # COM 初期化・終了
from pyaudiowpatch import PyAudio, paWASAPI  # WASAPI loopback サポート
from pycaw.callbacks import MMNotificationClient  # デバイス変更イベント
from pycaw.utils import AudioUtilities  # デバイス列挙
```

**非 Windows 環境での動作:**
- すべてのオプショナル依存は `try-except` でガード
- インポート失敗時は `None` または placeholder を設定
- デフォルト値（`NoDevice`）を返す機能は維持

### 内部モジュール

```python
from utils import errorLogging
```

---

## 自動デバイス選択の動作フロー

### Controller 側の設定（例）

```python
# controller.py の applyAutoMicSelect() メソッド

def applyAutoMicSelect(self) -> None:
    # 1. 更新前の処理: デバイス使用中の機能を停止
    device_manager.setCallbackProcessBeforeUpdateMicDevices(
        self.stopAccessMicDevices
    )
    
    # 2. デフォルトデバイス変更時: 新しいデバイスを選択
    device_manager.setCallbackDefaultMicDevice(
        self.updateSelectedMicDevice
    )
    
    # 3. 更新後の処理: 新しいデバイスで機能を再開
    device_manager.setCallbackProcessAfterUpdateMicDevices(
        self.restartAccessMicDevices
    )
    
    # 4. 初回実行
    device_manager.forceUpdateAndSetMicDevices()
    
    # 5. 監視開始
    device_manager.startMonitoring()
```

### デバイス変更時のシーケンス図

```
[ユーザーがヘッドセットを接続]
        ↓
[Windows がデフォルトデバイスを変更]
        ↓
[pycaw の Client.on_device_added() が呼ばれる]
        ↓
[client.loop = False に設定]
        ↓
[monitoring() の COM 監視ループが終了]
        ↓
[runProcessBeforeUpdateMicDevices() 実行]
        ↓
[controller.stopAccessMicDevices()]
   - 音声認識を停止
   - デバイスを解放
        ↓
[update() でデバイス情報を更新]
        ↓
[checkUpdate() で変更を検出]
        ↓
[noticeUpdateDevices() でコールバック呼び出し]
        ↓
[setMicDefaultDevice() 実行]
        ↓
[controller.updateSelectedMicDevice(host, device)]
   - 設定を更新
   - フロントエンドに通知
        ↓
[runProcessAfterUpdateMicDevices() 実行]
        ↓
[controller.restartAccessMicDevices()]
   - 新しいデバイスで音声認識を開始
        ↓
[COM 監視ループが再開]
```

---

## エラーハンドリング戦略

### 1. import 時のエラー

**問題:** Windows 専用ライブラリが非 Windows 環境でインポートされる

**対策:**
```python
try:
    import comtypes
except Exception:
    comtypes = None  # type: ignore
```

**結果:**
- インポートエラーは発生しない
- `comtypes is None` で可用性を判定
- 機能は制限されるがアプリケーションは動作

### 2. 初期化時のエラー

**問題:** デバイス情報の取得に失敗

**対策:**
```python
try:
    if PyAudio is not None:
        try:
            self.update()
        except Exception:
            errorLogging()
except Exception:
    pass  # デフォルト値のまま継続
```

**結果:**
- 初期化は完了（`_initialized = True`）
- デバイス情報はデフォルト値（`NoDevice`）
- ログにエラーを記録

### 3. 監視スレッド内のエラー

**問題:** デバイス更新中の予期しない例外

**対策:**
```python
try:
    while self.monitoring_flag is True:
        try:
            # 監視処理
        except Exception:
            errorLogging()  # ログに記録して継続
except Exception:
    errorLogging()  # 外側のループでもキャッチ
```

**結果:**
- エラーが発生しても監視は継続
- ログにエラーを記録
- スレッドはクラッシュしない

### 4. コールバック実行時のエラー

**問題:** 登録されたコールバック関数内で例外が発生

**対策:**
```python
if isinstance(self.callback_default_mic_device, Callable):
    try:
        self.callback_default_mic_device(host_name, device_name)
    except Exception:
        errorLogging()  # ログに記録して継続
```

**結果:**
- コールバックのエラーは分離される
- 他のコールバックには影響しない
- デバイス監視は継続

---

## スレッド構成

### メインスレッド
- アプリケーションのメインループ

### 監視スレッド（`th_monitoring`）
- `monitoring()` メソッドを実行
- デーモンスレッド（メインスレッド終了時に自動終了）
- `startMonitoring()` で起動
- `stopMonitoring()` で停止

### スレッド同期

**監視フラグ:**
```python
self.monitoring_flag: bool = False
```

**動作:**
- `True`: 監視継続
- `False`: 監視停止（次回ループで終了）

**停止時の安全性:**
```python
self.monitoring_flag = False  # フラグを False に
if self.th_monitoring is not None:
    self.th_monitoring.join(timeout=5)  # 最大5秒待機
```

---

## パフォーマンス考慮事項

### 1. 遅延初期化

**戦略:**
- `__new__`: 軽量（インスタンス生成のみ）
- `init()`: 中程度（デバイス情報の初回取得）
- `startMonitoring()`: 重い（スレッド起動、COM 初期化）

**利点:**
- `import device_manager` は高速
- アプリケーション起動時のレスポンス向上
- 使用しない機能のリソースを消費しない

### 2. COM イベント vs ポーリング

**COM イベント:**
- リアルタイム検知（即座に反応）
- CPU 使用率が低い（イベント待機）
- Windows 専用

**ポーリング:**
- 最大 20 秒の遅延（10 回 × 2 秒）
- CPU 使用率がやや高い（定期的な `update()` 呼び出し）
- クロスプラットフォーム

**ハイブリッド方式:**
- COM が利用可能ならイベント駆動
- COM が失敗またはポーリングにフォールバック

### 3. デバイス情報のキャッシング

**戦略:**
```python
self.mic_devices  # キャッシュ
self.prev_mic_devices  # 前回の状態
```

**利点:**
- `getMicDevices()` は `update()` を呼ばない（高速）
- 変更検出が効率的（差分のみ処理）

### 4. ポーリングの最適化

**初回待機（2 秒）:**
```python
sleep(2)
```
- デバイス接続後の不安定期間を回避
- デバイスドライバーの初期化を待つ

**最大 10 回ポーリング:**
```python
for _ in range(10):
    self.update()
    if self.checkUpdate():
        break  # 変更検出後は即座に終了
    sleep(2)
```
- 不要なポーリングを削減
- 変更検出後は即座に次の処理へ

---

## テストシナリオ

### 1. 初期化テスト

**ケース:**
- PyAudio が利用可能
- PyAudio が利用不可（非 Windows 環境）
- デバイスが1つもない環境

**確認項目:**
- `_initialized` フラグが `True` になるか
- デバイス情報がデフォルト値または実デバイスで設定されているか
- エラーが適切にログされているか

### 2. デバイス検出テスト

**ケース:**
- 複数のホスト API（MME、WASAPI 等）
- 複数のマイクデバイス
- WASAPI ループバックデバイス

**確認項目:**
- すべてのデバイスが検出されるか
- デフォルトデバイスが正しく識別されるか
- ループバックデバイスが正しく識別されるか

### 3. 変更検出テスト

**ケース:**
- デフォルトデバイスの変更
- デバイスの接続・切断
- ホスト API の変更

**確認項目:**
- 変更が正しく検出されるか
- 適切なフラグが設定されるか
- コールバックが呼び出されるか

### 4. 監視スレッドテスト

**ケース:**
- 監視の起動・停止
- デバイス変更時の動作
- エラー発生時の継続性

**確認項目:**
- スレッドが正しく起動・停止するか
- デバイス変更が検知されるか
- エラー発生時もスレッドが継続するか

### 5. 自動デバイス選択テスト

**ケース:**
- デフォルトデバイスの変更
- デバイスの接続中に音声認識が動作中
- コールバック内でエラーが発生

**確認項目:**
- デバイス変更前に処理が停止されるか
- デバイス変更後に処理が再開されるか
- エラーが分離されるか

---

## 制限事項

### 1. Windows 依存機能

**問題:** COM イベント監視と WASAPI ループバックは Windows 専用

**影響:**
- 非 Windows 環境ではポーリングのみ
- リアルタイム性が低下
- ループバックデバイスが利用不可

**緩和策:**
- グレースフルデグレード（デフォルト値を返却）
- プラットフォーム固有のコードを分離

### 2. デバイス名の曖昧性

**問題:** デバイス名に特殊文字やロケール依存の名前が含まれる

**影響:**
- 名前による比較が不正確になる可能性
- ループバックデバイスのマッチングが失敗する可能性

**緩和策:**
- `index` による識別も併用
- 部分一致でループバックデバイスを検索

### 3. ポーリング遅延

**問題:** 最大 20 秒の遅延が発生する可能性

**影響:**
- デバイス変更の検知が遅れる
- ユーザー体験の低下

**緩和策:**
- COM イベント監視を優先使用
- ポーリング間隔を短縮（2 秒）

### 4. エラーの握りつぶし

**問題:** 多くのエラーがログに記録されるのみで例外が投げられない

**影響:**
- デバッグが困難
- エラーの発生に気づきにくい

**緩和策:**
- 詳細なエラーログ（`errorLogging()`）
- 重要なエラーは status を返却（future work）

---

## 今後の改善案

### 1. クロスプラットフォーム対応の強化

**Linux (PulseAudio / ALSA):**
```python
# PulseAudio の D-Bus API でデバイス監視
# ALSA の udev イベントでデバイス変更を検知
```

**macOS (Core Audio):**
```python
# Core Audio の kAudioDevicePropertyDataSource 監視
# IOKit でデバイスイベントを検知
```

### 2. デバイス識別の改善

**問題:** 名前のみによる識別は不安定

**解決策:**
```python
device_id = {
    "index": device["index"],
    "name": device["name"],
    "host": host["name"],
    "unique_id": device.get("uniqueDeviceID", "")  # WASAPI 固有 ID
}
```

### 3. 非同期化（asyncio）

**問題:** スレッド管理の複雑性

**解決策:**
```python
async def monitoring_async(self):
    while self.monitoring_flag:
        await asyncio.sleep(2)
        await self.update_async()
        if self.checkUpdate():
            await self.noticeUpdateDevices_async()
```

**利点:**
- スレッド管理が不要
- エラーハンドリングが統一
- パフォーマンスの向上

### 4. イベントログの記録

**問題:** デバイス変更の履歴が残らない

**解決策:**
```python
device_change_history = []

def log_device_change(event_type, device_info):
    device_change_history.append({
        "timestamp": datetime.now(),
        "event": event_type,
        "device": device_info
    })
```

**利点:**
- デバッグが容易
- ユーザーサポートの向上

### 5. 設定の永続化

**問題:** 選択されたデバイスが再起動後に失われる

**解決策:**
```python
# config.py に保存
config.SELECTED_MIC_DEVICE_ID = {
    "host": "Windows WASAPI",
    "name": "Microphone (Realtek)",
    "unique_id": "{0.0.0.00000000}.{...}"
}

# 起動時に復元
def restore_selected_device():
    saved_id = config.SELECTED_MIC_DEVICE_ID
    current_devices = device_manager.getMicDevices()
    # unique_id でマッチング
```

---

## 関連ファイル

- **controller.py** - デバイス管理のコールバックを登録
- **model.py** - デバイス情報を使用して音声認識を開始
- **config.py** - デバイス選択の設定を保存
- **utils.py** - エラーロギング関数

---

## コーディング規約への準拠

### 命名規則

- クラス名: `DeviceManager`, `Client` (PascalCase)
- メソッド名: `startMonitoring`, `getMicDevices` (snake_case)
- 変数名: `mic_devices`, `default_mic_device` (snake_case)
- 定数: 使用していない（`config.py` で管理）

### 型注釈

**現状:**
```python
def init(self) -> None:
    self.mic_devices: Dict[str, List[Dict[str, Any]]] = {...}
```

**改善案:**
```python
DeviceInfo = Dict[str, Any]
DeviceList = List[DeviceInfo]
HostDeviceMap = Dict[str, DeviceList]

def init(self) -> None:
    self.mic_devices: HostDeviceMap = {...}
```

### Docstring

**現状:** 一部のメソッドのみ docstring あり

**改善案:**
```python
def getMicDevices(self) -> Dict[str, List[Dict[str, Any]]]:
    """Get the list of microphone devices grouped by host API.

    Returns:
        A dict mapping host names (e.g., "Windows WASAPI") to lists of device info dicts.
        Each device dict contains keys like "index", "name", "maxInputChannels", etc.
        If no devices are available, returns {"NoHost": [{"index": -1, "name": "NoDevice"}]}.
    """
```

---

## まとめ

`device_manager.py` は VRCT のデバイス管理機能を提供する重要なモジュールであり、以下の特徴を持つ:

1. **シングルトンパターン:** アプリケーション全体で1つのインスタンスのみ
2. **遅延初期化:** import 時のパフォーマンス低下を回避
3. **プラットフォーム対応:** Windows で完全な機能、非 Windows でもグレースフルデグレード
4. **リアルタイム監視:** COM イベントとポーリングのハイブリッド方式
5. **コールバックパターン:** 柔軟なイベント通知機構
6. **防御的プログラミング:** エラーが発生してもクラッシュしない

このモジュールは自動デバイス選択機能の中核として動作し、ユーザーがデバイスを切り替えた際に音声認識を自動的に再開することで、シームレスな体験を提供する。
