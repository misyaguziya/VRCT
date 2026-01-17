# model.py - VRCTコアモデルクラス

## 概要

VRCTアプリケーションの中核となるModelクラスを定義するモジュールです。音声認識、翻訳、VRオーバーレイ、OSC通信、WebSocketサーバーなどの主要機能を統合管理し、システム全体の動作を制御します。

## 最近の更新 (2026-01-11)

### クリップボード機能

- `clipboard` インスタンスを Model 内に保持
- `setCopyToClipboard(text: str) -> bool`: 翻訳結果をクリップボードにコピー
- `setPasteFromClipboard() -> bool`: Ctrl+V でペースト実行（VRChat ウィンドウ自動フォーカス）
- OpenVR による VRChat アプリ名の自動検出

### テレメトリ機能

- `telemetryInit(enabled: bool, app_version: str)`: Aptabase を用いたテレメトリ初期化
- `telemetryShutdown()`: テレメトリのシャットダウン（app_closed イベント送信）
- `telemetryTouchActivity()`: ユーザーアクティビティの記録
- `telemetry.*()`: イベント送信メソッド群
- デフォルト有効、ユーザー制御可能な設計

### その他の更新

## 最近の更新 (2025-10-20)

### VRAMエラー検出とフォールバック

- `detectVRAMError()` を追加し CUDA メモリ関連メッセージ/独自例外 `VRAM_OUT_OF_MEMORY` を判別
- 翻訳/音声認識実行中に VRAM エラー検出時、Controller 側で翻訳機能を無効化し CTranslate2 へフォールバックする運用を支援
- エラー詳細文字列を UI へ通知するためのメッセージ抽出を標準化

### CTranslate2 言語マッピングネスト対応

- `getListLanguageAndCountry()` / `findTranslationEngines()` が `translation_lang['CTranslate2'][CTRANSLATE2_WEIGHT_TYPE]['source']` を参照するネスト構造へ更新
- ウェイト種別切替時に対応言語集合が動的に変化しエンジン再判定をトリガー

### ローカル LLM 翻訳エンジン統合

- LMStudio / Ollama 用クライアント初期化・モデルリスト取得メソッド追加: `authenticationTranslatorLMStudio()`, `getTranslatorLMStudioModelList()`, `setTranslatorLMStudioModel()`, `updateTranslatorLMStudioClient()` など
- Ollama も同様のインターフェースで統一 (`getTranslatorOllamaModelList`, `setTranslatorOllamaModel`, `updateTranslatorOllamaClient`)
- Plamo / Gemini / OpenAI と同一フォーマットでモデル選択ロジックを実装し Controller からの呼び出しを簡素化

### トークナイザ・リソース取得安定化

- CTranslate2 トークナイザダウンロード処理を `downloadCTranslate2ModelTokenizer()` で明示化し PyInstaller パス周りの不整合回避
- フォントパス探索は OverlayImage 側へ委譲 (`OverlayImage(config.PATH_LOCAL)`) し Model は生成と更新呼び出しのみ保持

### 翻訳失敗時のフェールセーフ再試行

- `getTranslate()` 内で翻訳失敗（非文字列）時に CTranslate2 をリトライループして安定した結果を返却
- 成功判定フラグを返却し上位層でエンジン制限エラー検出/フォールバックを容易化

### キーワードフィルタ再初期化改善

- `resetKeywordProcessor()` でインスタンス再生成し `addKeywords()` により設定変更後のフィルタ更新即時反映

### WebSocket サーバー管理強化

- 非同期サーバー起動を `asyncio.run` ラッパースレッドで安定化
- ループフラグ `websocket_server_loop` と状態フラグ `websocket_server_alive` を追加し安全な停止処理と存活確認を標準化

### 影響

| 項目 | 内容 |
|------|------|
| 安定性 | VRAM 検出とフェールセーフ再試行で異常終了回避 |
| 拡張性 | ローカル LLM 統合によりネットワーク不要環境対応 |
| 柔軟性 | CTranslate2 ウェイト種別に応じた言語集合動的切替 |
| 保守性 | トークナイザ/フォント取得責務分離で可読性向上 |
| 観測性 | エラー詳細標準化により UI/ログでの診断容易 |

## 主要機能

### シングルトンパターン

- アプリケーション全体で単一のModelインスタンスを保証
- 遅延初期化による軽量なインポート

### 音声認識機能

- マイク音声のリアルタイム文字起こし
- スピーカー出力の音声認識
- エネルギーレベル監視
- 複数言語対応

### 翻訳機能

- 複数の翻訳エンジン対応（DeepL、Google、CTranslate2等）
- 言語自動検出
- バッチ翻訳処理

### VRオーバーレイ

- OpenVR統合
- 小型・大型ログオーバーレイ
- 動的配置・透明度制御

### OSC通信

- VRChatとのOSC通信
- タイピング状態の同期
- ミュート状態の監視

### WebSocketサーバー

- 外部アプリケーションとの通信
- リアルタイムメッセージ配信

## クラス構造

### threadFnc クラス

```python
class threadFnc(Thread):
    def __init__(self, fnc, end_fnc=None, daemon: bool = True, *args, **kwargs)
```

- 関数を繰り返し実行するスレッドラッパー
- 一時停止・再開機能
- エラー保護機能

### Model クラス

```python
class Model:
    def __new__(cls)  # シングルトンパターン
    def init(self)    # 重い初期化処理
    def ensure_initialized(self)  # 遅延初期化
```

## 主要メソッド

### 初期化・管理

```python
init() -> None
```

- 全コンポーネントの初期化
- 重い処理のため明示的に呼び出し

```python
ensure_initialized() -> None
```

- 必要時の自動初期化
- 安全な遅延初期化

### 翻訳機能メソッド

```python
getInputTranslate(message, source_language=None) -> Tuple[List[str], List[bool]]
```

- 入力メッセージの多言語翻訳
- 成功フラグも同時に返却

```python
getOutputTranslate(message, source_language=None) -> Tuple[List[str], List[bool]]
```

- 出力メッセージの翻訳（逆方向）

```python
authenticationTranslatorDeepLAuthKey(auth_key) -> bool
```

- DeepL APIキーの認証

### 音声認識機能メソッド

```python
startMicTranscript(fnc: Callable) -> None
```

- マイク音声認識の開始
- コールバック関数で結果を通知

```python
startSpeakerTranscript(fnc: Callable) -> None
```

- スピーカー音声認識の開始

```python
pauseMicTranscript() -> None
resumeMicTranscript() -> None
```

- 音声認識の一時停止・再開

```python
startCheckMicEnergy(fnc: Callable) -> None
startCheckSpeakerEnergy(fnc: Callable) -> None
```

- 音声エネルギーレベルの監視

### VRオーバーレイ機能

```python
createOverlayImageSmallLog(message, your_language, translation, target_language) -> Image
```

- 小型ログオーバーレイ画像の生成

```python
createOverlayImageLargeLog(message_type, message, your_language, translation, target_language) -> Image
```

- 大型ログオーバーレイ画像の生成

```python
updateOverlaySmallLogSettings() -> None
updateOverlayLargeLogSettings() -> None
```

- オーバーレイ設定の更新

### OSC通信機能

```python
oscSendMessage(message: str) -> None
```

- VRChatへのメッセージ送信

```python
oscStartSendTyping() -> None
oscStopSendTyping() -> None
```

- タイピング状態の通知

```python
setMuteSelfStatus() -> None
```

- VRChatミュート状態の取得

### WebSocket機能

```python
startWebSocketServer(host: str, port: int) -> None
```

- WebSocketサーバーの起動

```python
websocketSendMessage(message_dict: dict) -> bool
```

- 全クライアントへのメッセージ送信

```python
checkWebSocketServerAlive() -> bool
```

- サーバー稼働状態の確認

### ファイルダウンロード機能

```python
downloadCTranslate2ModelWeight(weight_type, callback=None, end_callback=None)
```

- 翻訳モデルのダウンロード

```python
downloadWhisperModelWeight(weight_type, callback=None, end_callback=None)
```

- 音声認識モデルのダウンロード

### ウォッチドッグ機能

```python
startWatchdog() -> None
feedWatchdog() -> None
setWatchdogCallback(callback: Callable) -> None
```

- システム監視とタイムアウト処理

## 使用方法

### 基本的な使い方

```python
from model import model

# 明示的な初期化（推奨）
model.init()

# または自動初期化
model.ensure_initialized()

# 翻訳機能の使用
translations, success_flags = model.getInputTranslate("Hello World")

# 音声認識の開始
def on_transcript_result(result):
    print(f"認識結果: {result}")

model.startMicTranscript(on_transcript_result)
```

### VRオーバーレイの使用

```python
# オーバーレイの開始
model.startOverlay()

# 画像の作成と更新
img = model.createOverlayImageSmallLog(
    message="Hello",
    your_language="English",
    translation=["こんにちは"],
    target_language={"1": {"language": "Japanese", "enable": True}}
)
model.updateOverlaySmallLog(img)
```

### WebSocketサーバーの使用

```python
# サーバー起動
model.startWebSocketServer("127.0.0.1", 8765)

# メッセージ送信
message = {"type": "translation", "text": "Hello", "translation": "こんにちは"}
success = model.websocketSendMessage(message)
```

### クリップボード機能の使用

```python
# テキストをクリップボードにコピー
text = "翻訳結果"
success = model.setCopyToClipboard(text)

# ペースト実行（VRChat ウィンドウに自動フォーカス）
success = model.setPasteFromClipboard()
```

### テレメトリの初期化・シャットダウン

```python
# テレメトリ初期化（アプリ起動時）
model.telemetryInit(enabled=config.ENABLE_TELEMETRY, app_version=config.VERSION)

# テレメトリシャットダウン（アプリ終了時）
model.telemetryShutdown()

# アクティビティ記録
model.telemetryTouchActivity()
```

## 依存関係

### 必須モジュール

- `controller`: アプリケーション制御
- `config`: 設定管理
- `device_manager`: デバイス管理

### 音声・翻訳関連

- `models.transcription.*`: 音声認識
- `models.translation.*`: 翻訳機能
- `models.transliteration.*`: 音写変換

### VR・通信関連

- `models.overlay.*`: VRオーバーレイ
- `models.osc.*`: OSC通信
- `models.websocket.*`: WebSocket通信

### ユーティリティ

- `models.watchdog.*`: 監視機能
- `utils`: 共通ユーティリティ
- `flashtext`: キーワードフィルタリング

## 設定依存関係

多くの機能がconfigモジュールの設定に依存：

- 音声認識設定（しきい値、タイムアウト等）
- 翻訳設定（エンジン選択、言語設定等）
- VR設定（オーバーレイ位置、透明度等）
- OSC設定（IPアドレス、ポート等）

## エラーハンドリング

- 初期化エラーの適切な処理
- VRAM不足エラーの検出と対応
- ネットワークエラーの回復機能
- スレッドセーフティの保証

## 注意事項

- 重い初期化処理のため、明示的な初期化を推奨
- OpenVR環境が必要（VRオーバーレイ使用時）
- CUDA環境推奨（高速な音声認識・翻訳）
- WebSocketサーバーは非同期で動作
- 音声デバイスのアクセス権限が必要

## パフォーマンス考慮事項

- 遅延初期化によるメモリ使用量の最適化
- スレッドプールによる並行処理
- モデルの重複読み込み防止
- キューイングによる非同期処理
