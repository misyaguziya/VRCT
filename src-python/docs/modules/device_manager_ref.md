# device_manager.py — デバイス検出と監視 (改訂版)

### 概要
`device_manager.py` はローカルのマイク（入力）とスピーカー（ループバックから抽出）を列挙し、デフォルトデバイスの変更やデバイスリストの変化を監視してコールバックで通知するユーティリティです。

設計上のポイント:
- Windows 固有の依存 (`comtypes`, `pyaudiowpatch` (PyAudio + WASAPI), `pycaw`) はオプショナルです。モジュールを import してもこれらが無ければ例外にならず、プレースホルダ値を返すようになっています。
- モジュールの import 時点では監視は開始されません。リソースやスレッドの副作用を避けるため、`init()` と `startMonitoring()` は呼び出し側で明示的に実行してください。

---

### 使い方（簡単な流れ）

1. モジュールをインポート

```py
from device_manager import device_manager
```

2. 初期化（内部状態のセットアップ）

```py
device_manager.init()
```

3. 監視の開始（バックグラウンドスレッド）

```py
device_manager.startMonitoring()
```

4. 停止（アプリ終了時など）

```py
device_manager.stopMonitoring()
```

---

### 主な API

- `device_manager.init()`
  - internal state の初期化。import 後に必ず呼ぶ必要はないが、実機デバイスを取得する前に呼ぶことを推奨します。
- `device_manager.startMonitoring()` / `device_manager.stopMonitoring()`
  - 監視の開始 / 停止。`startMonitoring()` はデーモンスレッドを作成します。`stopMonitoring()` は best-effort で join を試みます。
- `device_manager.getMicDevices()`
  - ホストごとにグループ化された入力デバイスの辞書を返します。例: `{ 'Realtek': [ {index: 2, name: 'Microphone (Realtek)'} ] }`。
- `device_manager.getDefaultMicDevice()` / `device_manager.getSpeakerDevices()` / `device_manager.getDefaultSpeakerDevice()`
  - デフォルトデバイスやスピーカーループバックの情報を返します。
- `device_manager.forceUpdateAndSetMicDevices()` / `device_manager.forceUpdateAndSetSpeakerDevices()`
  - 即時に update() を実行して対応するコールバックを呼びます。

---

### コールバック登録（例）

コールバックは例外を内部で捕捉してログを出すため、コールバック実装側でもエラーハンドリングしてください。

- `setCallbackDefaultMicDevice(callback)` — デフォルト入力が変わったときに `callback(host_name, device_name)` が呼ばれます。
- `setCallbackDefaultSpeakerDevice(callback)` — デフォルト出力が変わったときに `callback(device_name)` が呼ばれます。
- `setCallbackHostList(callback)` / `setCallbackMicDeviceList(callback)` / `setCallbackSpeakerDeviceList(callback)` — それぞれ list 変更時に `callback()` が呼ばれます。
- `setCallbackProcessBeforeUpdateMicDevices(callback)` / `setCallbackProcessAfterUpdateMicDevices(callback)` — 更新の前後に呼ばれるフックです。

簡単な例:

```py
from device_manager import device_manager

def on_default_mic(host, device):
    print('default mic changed', host, device)

device_manager.init()
device_manager.setCallbackDefaultMicDevice(on_default_mic)
device_manager.startMonitoring()

# 後で停止
# device_manager.stopMonitoring()
```

---

### 注意点 / トラブルシュート

- Windows 固有の依存が無い場合、`getMicDevices()` などはデフォルトのプレースホルダ（`NoHost` / `NoDevice`）を返します。実機のデバイス検出や WASAPI によるループバック検出は Windows 環境でのみ保証されます。
- `startMonitoring()` は監視用のデーモンスレッドを作るため、アプリケーションの終了時には `stopMonitoring()` を呼ぶかプロセスを終了してください。`stopMonitoring()` は join を行いますが、失敗した場合でも致命的にならないよう best-effort 実装です。
- コールバック内部で例外が発生してもモジュール側で捕捉してログ出力します（`utils.errorLogging()`）。コールバック側で詳細なハンドリングやリトライが必要な場合は呼び出し側で行ってください。

---

### 実装メモ

- `monitoring()` は可能なら Windows の COM (pycaw / MMNotificationClient) を使ってイベント駆動で待ち受け、失敗時や非Windows 環境では PyAudio を使ったポーリング（定期的な update()) にフォールバックします。
- 外部ライブラリが原因の例外は内部で捕捉し、`errorLogging()` を呼んで記録する設計です。
