# device_manager.py — デバイス検出と監視（overwrite）

目的: システムのマイク/スピーカー（主に Windows の WASAPI）を列挙し、変更を監視してコールバックで通知する `DeviceManager` シングルトンを提供します。

主要コンポーネント:
- class Client(MMNotificationClient)
  - オーディオデバイスのシステムイベント（追加/削除/デフォルト変更）を受け取り、監視ループの再起動をトリガーします。

- class DeviceManager
  - シングルトンインスタンス: `device_manager`
  - 主要プロパティ:
    - `mic_devices` (dict): {host_name: [device_info, ...]}
    - `default_mic_device` (dict): {'host': {...}, 'device': {...}}
    - `speaker_devices` (list): [device_info, ...]
    - `default_speaker_device` (dict)
    - 各種 prev_/update_flag_: 差分検出用
    - callback 関連プロパティ: `callback_default_mic_device`, `callback_mic_device_list`, など多数

  - 主要メソッド (抜粋):
    - `update()` -> None: PyAudio を利用してホスト毎の入力デバイスとループバック（スピーカー）を列挙し内部状態を更新します。
    - `checkUpdate()` -> bool: 前回値との差分を計算して変更フラグを返します。
    - `monitoring()` -> None: pycaw/MMNotificationClient を使った長時間監視ループ。変化を検出すると各コールバックを呼び出す。
    - `startMonitoring()` / `stopMonitoring()`
    - `getMicDevices()` / `getDefaultMicDevice()` / `getSpeakerDevices()` / `getDefaultSpeakerDevice()`
    - `forceUpdateAndSetMicDevices()` / `forceUpdateAndSetSpeakerDevices()`

コールバックAPI（例）:
- `setCallbackMicDeviceList(callback)` — マイクデバイスリスト変更時に呼ばれる
- `setCallbackDefaultMicDevice(callback)` — デフォルトマイク変更時に呼ばれる
- `setCallbackProcessBeforeUpdateMicDevices(callback)` / `setCallbackProcessAfterUpdateMicDevices(callback)` — 更新前後のフック

例:

```python
from device_manager import device_manager

def on_default_mic(host_name, device_name):
    print('Default mic changed:', host_name, device_name)

device_manager.setCallbackDefaultMicDevice(on_default_mic)
device_manager.forceUpdateAndSetMicDevices()
```

注意点:
- Windows 固有のモジュール（PyAudio paWASAPI, pycaw）に依存します。クロスプラットフォーム対応が必要な場合は別実装が必要です。
- 監視スレッドは永続的に動作するため、アプリケーション終了時は `stopMonitoring()` を呼んで安全に停止してください。

変更点（2025-10-13）:
- `DeviceManager` のシングルトン生成時（`__new__`）に軽量な `init()` を実行するようになりました。これによりモジュールのインポート順に依存せず、最小限の内部構造が常に確立されます（※監視スレッドは自動で起動しません）。
- `init()` は監視スレッドを開始しませんが、PyAudio が利用可能な場合に限りベストエフォートで一度だけ `update()` を呼び、起動時に可能な限り実機デバイス情報を埋めるようになりました（例外は握り潰して安全性を維持）。
- アクセサ (`getDefaultMicDevice()` / `getDefaultSpeakerDevice()` など) は遅延初期化を行い、呼び出し時に `init()` が動いていない場合は安全に初期化されるようになりました。これにより `controller` と `config` がトップレベルインポートで互いに依存している状況でも、`config` に正しいデバイス情報が入るようになります。

推奨起動シーケンス:
- `controller.init()` でコールバック登録が完了した直後に、`mainloop` の起動シーケンス中で明示的に `device_manager.startMonitoring()` を呼ぶことを推奨します。これにより以降のデバイス変更がコールバックを通じて確実に届きます。なお、`startMonitoring()` は任意で、軽量にしたい場合は呼ばなくても構いません（ただし動的変化は検出されません）。

ドキュメントにおける重要な注意:
- この変更は "import-time に重大な副作用を持たせない" という方針を維持しつつ、インポート順の違いによる初期化漏れを解消するために行われています。`init()` は監視スレッドを開始しないため、インポートだけでスレッドが走ることはありません。

## 詳細設計

目的: ローカルの入力（マイク）と出力（ループバックから抽出されたスピーカー）デバイスを列挙し、変更を監視してコールバックで通知する。Windows の WASAPI 等に依存。

主要クラス/関数:
- class Client(MMNotificationClient)
  - Audio デバイスの変更イベントを受けると `loop = False` にして監視ループを再起動させる設計。

- class DeviceManager
  - シングルトン: `device_manager = DeviceManager()`
  - 主要属性:
    - mic_devices: {host: [device_info...]}
    - default_mic_device: {host, device}
    - speaker_devices: [device_info...]
    - default_speaker_device: {device}
    - 各種 prev_*, update_flag_*: 差分検出のために保持
    - コールバック属性: callback_default_mic_device, callback_host_list など
  - 主要メソッド:
    - update(): PyAudio を使ってホストごとにデバイス列挙。Loopback デバイスを speaker_devices に集める。
    - monitoring(): MMNotificationClient と組み合わせてデバイスの変化を検出し、コールバックを発行
    - set/clear Callback 系: UI や Controller が登録して自動選択や再起動をトリガーできる
    - forceUpdateAndSetMicDevices / forceUpdateAndSetSpeakerDevices: 即時更新とコールバック通知

注意点:
- Windows 固有の処理（paWASAPI, pycaw）に依存する。
- デバイス取得はリソースに依存するので try/except で例外を吸収し errorLogging() を呼ぶ。
