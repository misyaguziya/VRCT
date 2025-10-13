# controller.py - VRCTコントローラーモジュール

## 概要

VRCTアプリケーションのビジネスロジックを制御するコントローラークラスです。UI層とモデル層の間に位置し、ユーザーの入力を適切な処理に変換し、結果を UI に返す役割を担います。全ての機能制御、設定管理、状態管理を一元的に行います。

## 主要機能

### 機能制御
- 翻訳機能の有効化・無効化
- 音声認識機能の制御
- VRオーバーレイの管理
- WebSocketサーバーの制御

### 設定管理
- アプリケーション設定の取得・更新
- デバイス設定の管理
- 言語・エンジン設定の制御

### 状態管理
- システム状態の監視
- エラー状態の管理
- 初期化プロセスの制御

### 通信制御
- OSC通信の管理
- WebSocket通信の制御
- 外部アプリケーション連携

## クラス構造

### Controller クラス
```python
class Controller:
    def __init__(self) -> None
```

中核となるコントローラークラス

### 内部ヘルパークラス

#### DownloadCTranslate2 クラス
```python
class DownloadCTranslate2:
    def progressBar(self, progress) -> None
    def downloaded(self) -> None
```
- 翻訳モデルのダウンロード進捗管理

#### DownloadWhisper クラス  
```python
class DownloadWhisper:
    def progressBar(self, progress) -> None
    def downloaded(self) -> None
```
- 音声認識モデルのダウンロード進捗管理

## 主要メソッド

### 初期化・設定

```python
init() -> None
```
- コントローラーの初期化
- 各コンポーネントの起動
- 初期設定の適用

```python
setInitMapping(init_mapping: dict) -> None
setRunMapping(run_mapping: dict) -> None
setRun(run: Callable) -> None
```
- エンドポイント・コールバック設定

### 翻訳機能制御

```python
setEnableTranslation(data) -> dict
setDisableTranslation(data) -> dict
```
- 翻訳機能の有効化・無効化

```python
setSelectedTranslationEngines(data) -> dict
getSelectedTranslationEngines(data) -> dict
```
- 翻訳エンジンの選択・取得

```python
setSelectedYourLanguages(data) -> dict
setSelectedTargetLanguages(data) -> dict
```
- 送信・受信言語の設定

```python
sendMessageBox(data) -> dict
```
- メッセージの翻訳・送信処理

### 音声認識機能制御

```python
setEnableTranscriptionSend(data) -> dict
setEnableTranscriptionReceive(data) -> dict
```
- 音声認識機能の有効化

```python
setSelectedTranscriptionEngine(data) -> dict
getSelectedTranscriptionEngine(data) -> dict
```
- 音声認識エンジンの選択・取得

```python
setSelectedMicDevice(data) -> dict
setSelectedSpeakerDevice(data) -> dict
```
- 音声デバイスの選択

```python
setMicThreshold(data) -> dict
setSpeakerThreshold(data) -> dict
```
- 音声しきい値の設定

### VRオーバーレイ制御

```python
setEnableOverlaySmallLog(data) -> dict
setEnableOverlayLargeLog(data) -> dict
```
- VRオーバーレイの有効化

```python
setOverlaySmallLogSettings(data) -> dict
setOverlayLargeLogSettings(data) -> dict
```
- オーバーレイ設定の更新

### WebSocket制御

```python
setEnableWebSocketServer(data) -> dict
setDisableWebSocketServer(data) -> dict
```
- WebSocketサーバーの制御

```python
setWebSocketHost(data) -> dict
setWebSocketPort(data) -> dict
```
- WebSocket接続設定

### システム管理

```python
updateSoftware(data) -> dict
updateCudaSoftware(data) -> dict
```
- ソフトウェアアップデート

```python
downloadCtranslate2Weight(data) -> dict
downloadWhisperWeight(data) -> dict
```
- AIモデルのダウンロード

```python
feedWatchdog(data) -> dict
```
- ウォッチドッグの生存シグナル送信

## 使用方法

### 基本的な使い方

```python
from controller import Controller

# コントローラーの初期化
controller = Controller()
controller.init()

# 翻訳機能の有効化
result = controller.setEnableTranslation(None)
print(f"翻訳機能: {result}")

# メッセージ送信
message_data = {"id": "123", "message": "Hello World"}
result = controller.sendMessageBox(message_data)
```

### エンドポイント設定

```python
# マッピング設定
mapping = {
    "/set/enable/translation": controller.setEnableTranslation,
    "/get/data/version": controller.getVersion,
}

# 実行関数の設定
def run_callback(status, endpoint, result):
    print(f"Status: {status}, Endpoint: {endpoint}, Result: {result}")

controller.setRun(run_callback)
```

### 音声認識の設定

```python
# マイクデバイスの選択
host_data = "DirectSound"
result = controller.setSelectedMicHost(host_data)

device_data = "マイク (USB Audio Device)"
result = controller.setSelectedMicDevice(device_data)

# 音声認識の開始
result = controller.setEnableTranscriptionSend(None)
```

## レスポンス形式

全てのメソッドは統一されたレスポンス形式を返します：

```python
{
    "status": int,    # HTTPステータスコード(200, 400, 500等)
    "result": any     # 処理結果（成功時）または エラーメッセージ（失敗時）
}
```

### 成功レスポンス例
```python
{
    "status": 200,
    "result": "翻訳機能が有効化されました"
}
```

### エラーレスポンス例
```python
{
    "status": 400,
    "result": "Invalid device selection"
}
```

## 状態管理

### システム状態
- 各機能の有効・無効状態
- デバイスの接続状態
- ネットワーク接続状態

### エラー状態  
- デバイスエラー
- 翻訳エンジンエラー
- VRAMオーバーフローエラー

### 初期化状態
- 段階的な初期化プロセス
- 依存関係の解決状態

## イベント処理

### 音声認識イベント

```python
micMessage(result: dict) -> None
```
- マイク音声認識結果の処理
- 翻訳・フィルタリング・送信

```python
speakerMessage(result: dict) -> None  
```
- スピーカー音声認識結果の処理

### ダウンロードイベント
- 進捗通知
- 完了通知  
- エラー通知

### デバイス変更イベント
- マイク・スピーカーの選択変更
- 計算デバイスの変更

## 依存関係

### 直接依存
- `config`: 設定管理
- `model`: コアモデル機能  
- `device_manager`: デバイス管理
- `utils`: ユーティリティ機能

### 間接依存
- 各種モデルモジュール（翻訳、音声認識等）
- VRオーバーレイモジュール
- 通信モジュール

## エラーハンドリング

### VRAM不足エラー
- 自動的にCTranslate2への切り替え
- ユーザーへの適切な通知

### デバイスエラー
- デバイス接続状態の監視
- 自動復旧機能

### ネットワークエラー  
- 接続状態の定期確認
- オフライン機能への切り替え

### 設定エラー
- 設定値の妥当性チェック
- デフォルト値への復帰

## パフォーマンス考慮事項

### 遅延初期化
- 必要な時点での機能初期化
- メモリ使用量の最適化

### 非同期処理
- バックグラウンドでの重い処理
- UI の応答性維持

### キャッシュ機能
- 設定値のキャッシュ
- 翻訳結果のキャッシュ

## 注意事項

- すべてのメソッドは例外安全である
- 設定変更は即座に config に反映される
- 重い処理は別スレッドで実行される
- VR機能は適切な環境でのみ動作する
- ネットワーク機能はオフライン時に制限される

## セキュリティ考慮事項

- 外部入力の適切な検証
- APIキーの安全な管理
- ファイルアクセスの制限
- ネットワーク通信の暗号化（該当する場合）