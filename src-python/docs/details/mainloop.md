# mainloop.py - VRCTメインループモジュール

## 概要

VRCTアプリケーションのメインイベントループを管理するモジュールです。標準入力からのJSONリクエストを処理し、適切なコントローラーメソッドを呼び出してレスポンスを返す、アプリケーションの中枢的な役割を担います。

## 最近の更新 (2025-10-20)

### 新規エンドポイントと run_mapping 拡張

- VRAM 関連エラー通知エンドポイント追加: `/run/error_translation_chat_vram_overflow` など 5 種類 (翻訳/音声認識送受信別)
- ローカル LLM (LMStudio/Ollama) モデルリスト通知: `/run/selectable_lmstudio_model_list`, `/run/selectable_ollama_model_list` と選択モデル `/run/selected_*_model`
- 従来の Plamo/Gemini/OpenAI モデル取得通知と形式統一
- LMStudio/Ollama 接続確認エンドポイント: `/get/data/lmstudio_connection`, `/get/data/ollama_connection` を `/run/lmstudio_connection`, `/run/ollama_connection` に移動して非同期通知統一
- 文字変換エンドポイント追加: `/set/data/convert_message_to_romaji`, `/set/data/convert_message_to_hiragana`, `/set/enable/convert_message_to_romaji`, `/set/enable/convert_message_to_hiragana`, `/set/disable/convert_message_to_romaji`, `/set/disable/convert_message_to_hiragana` で音訳機能制御

### エンドポイントロックキー正規化

- `/set/enable/*` `/set/disable/*` の競合を `/lock/set/<name>` に正規化し排他制御強化
- ロック取得失敗時は再キュー投入し軽量リトライでデッドロック防止

### 並列ワーカー処理の安定化

- ハンドラ処理後に短い `sleep(0.2)` により大量高速連続要求時のスレッド飢餓を緩和
- 423 (Locked) ステータス時に指数的ではなく固定短期リトライ採用で応答時間予測性向上

### VRAM エラーフォールバック連携

- Controller が VRAM 検出し翻訳 OFF / CTranslate2 フォールバック後、run_mapping 経由で UI へ状態反映
- ハンドラはエラー時でもスレッド継続し `Internal error` を 500 応答で返しつつログ出力

### モデルリスト動的更新通知

- 認証・接続成功後に対象モデルリスト/選択モデルを run で逐次通知 (Plamo/Gemini/OpenAI/LMStudio/Ollama)

### 影響

| 項目 | 内容 |
|------|------|
| 安定性 | 排他制御と再キュー投入で競合時の落ち込み回避 |
| 可観測性 | VRAM/ダウンロード進捗/モデル更新イベントを run 経由で即時通知 |
| 拡張性 | 新規ローカル LLM エンジン追加に伴う汎用モデル通知フォーマット統一 |
| 応答予測性 | 固定リトライ戦略で待ち時間が読みやすい |
| フォールバック | VRAM エラー時の自動翻訳停止と CTranslate2 への切替連携 |

## 主要機能

### リクエスト処理システム

- JSON形式の標準入力からのリクエスト受信
- エンドポイントベースのルーティング
- 非同期・並列処理対応

### エンドポイント管理

- RESTライクなエンドポイント構造
- 機能別のエンドポイント分類
- 排他制御によるスレッドセーフティ

### 初期化システム

- アプリケーション設定の初期化
- コンポーネント間の依存関係解決
- 段階的な機能有効化

## クラス構造

### Main クラス

```python
class Main:
    def __init__(self, controller_instance: Controller, mapping_data: dict, worker_count: int = 3)
```

- メインループの制御
- ワーカースレッドプール管理  
- エンドポイント排他制御

## エンドポイント分類

### 機能制御系

```text
/set/enable/*   - 各機能の有効化
/set/disable/*  - 各機能の無効化
```

### データ操作系

```text
/get/data/*     - 設定データの取得
/set/data/*     - 設定データの更新
/delete/data/*  - データの削除
```

### 実行系

```text
/run/*          - 各種処理の実行
```

## 主要エンドポイント

### 翻訳機能

- `/set/enable/translation`: 翻訳機能の有効化
- `/set/disable/translation`: 翻訳機能の無効化
- `/set/data/selected_translation_engines`: 翻訳エンジンの選択
- `/run/send_message_box`: メッセージ送信

### 音声認識機能

- `/set/enable/transcription_send`: 送信音声認識の有効化
- `/set/enable/transcription_receive`: 受信音声認識の有効化
- `/set/data/selected_transcription_engine`: 音声認識エンジン選択

### VR機能

- `/set/data/overlay_small_log_settings`: 小型オーバーレイ設定
- `/set/data/overlay_large_log_settings`: 大型オーバーレイ設定

### WebSocket機能

- `/set/enable/websocket_server`: WebSocketサーバー有効化
- `/set/data/websocket_host`: サーバーホスト設定
- `/set/data/websocket_port`: サーバーポート設定

### クリップボード機能

- `/get/data/clipboard`: クリップボード機能の状態取得（`config.ENABLE_CLIPBOARD` の値）
- `/set/enable/clipboard`: `config.ENABLE_CLIPBOARD` を True に設定
- `/set/disable/clipboard`: `config.ENABLE_CLIPBOARD` を False に設定

### テレメトリ機能

- `/get/data/telemetry`: テレメトリの状態取得
- `/set/enable/telemetry`: テレメトリの有効化（Aptabase初期化）
- `/set/disable/telemetry`: テレメトリの無効化（シャットダウン）

### システム管理

- `/run/update_software`: ソフトウェアアップデート
- `/run/download_ctranslate2_weight`: 翻訳モデルダウンロード
- `/run/download_whisper_weight`: 音声認識モデルダウンロード

## 主要メソッド

### リクエスト処理

```python
receiver() -> None
```

- 標準入力からのJSONリクエスト受信
- パースエラーの適切な処理

```python
handleRequest(endpoint: str, data: Any = None) -> tuple
```

- エンドポイント処理の実行
- ステータスコードと結果の返却

```python
handler() -> None
```

- ワーカースレッドのメイン処理
- キューからのリクエスト取得・処理

### スレッド管理

```python
startReceiver() -> None
```

- レシーバースレッドの起動

```python
startHandler() -> None
```

- ハンドラースレッドプールの起動

```python
start() -> None
```

- 全スレッドの起動

```python
stop(wait: float = 2.0) -> None
```

- 全スレッドの安全な停止

## 使用方法

### 基本的な使い方

```python
from mainloop import main_instance

# メインループの開始
main_instance.start()

# ウォッチドッグコールバックの設定
main_instance.controller.setWatchdogCallback(main_instance.stop)

# コントローラーの初期化
main_instance.controller.init()
```

### 直接リクエスト処理

```python
# エンドポイントの直接呼び出し
result, status = main_instance.handleRequest("/get/data/version", None)
print(f"バージョン: {result}")

# 翻訳機能の有効化
result, status = main_instance.handleRequest("/set/enable/translation", None)
```

### 標準入力からの処理

```json
{
    "endpoint": "/run/send_message_box",
    "data": "eyJpZCI6ICIxMjMiLCAibWVzc2FnZSI6ICJIZWxsbyBXb3JsZCJ9"
}
```

## リクエスト形式

### 入力形式

```json
{
    "endpoint": "string",     // 必須：処理対象のエンドポイント
    "data": "string|null"     // オプション：Base64エンコード済みデータ
}
```

### 出力形式

```json
{
    "status": 200,           // HTTPステータスコード
    "endpoint": "string",    // 処理されたエンドポイント
    "result": "any"         // 処理結果
}
```

## ステータスコード

- `200`: 成功
- `400`: 不正なリクエスト
- `404`: 存在しないエンドポイント
- `423`: ロック中（機能が無効化されている）
- `500`: 内部エラー

## 排他制御

### ロック機能

- enable/disableペアは同一ロックキーを共有
- 同一機能の同時実行を防止
- デッドロックを回避する設計

### ロックキー正規化

```python
/set/enable/translation  -> /lock/set/translation
/set/disable/translation -> /lock/set/translation
```

## 初期化プロセス

### 段階的初期化

1. コントローラーの初期化
2. デバイスマネージャーの初期化
3. モデルの初期化
4. 各機能の段階的有効化

### 初期化mapping

- `/get/data/*`エンドポイントから初期化設定を自動抽出
- システム起動時の設定復元

## ログ機能

### プロセスログ

- 全リクエスト・レスポンスの記録
- JSON形式での構造化ログ

### エラーログ

- 例外の詳細記録
- スタックトレースの保存

## 依存関係

### 直接依存

- `controller`: ビジネスロジック制御
- `utils`: ユーティリティ機能（ログ、エンコード等）

### 間接依存

- `config`: 設定管理
- `model`: コアモデル機能
- `device_manager`: デバイス管理

## 設定項目

### ワーカー数

```python
DEFAULT_WORKER_COUNT = 3  # 並列処理スレッド数
```

### タイムアウト

- キュー待機タイムアウト: 0.5秒
- スレッド停止待機: 2.0秒
- 処理安定化待機: 0.2秒

## エラーハンドリング

- JSONパースエラーの適切な処理
- エンドポイント実行エラーのキャッチ
- スレッドセーフなエラーログ記録
- グレースフルシャットダウン

## パフォーマンス特性

### スループット

- 複数ワーカーによる並列処理
- ノンブロッキングI/O

### レイテンシ

- キューイング遅延の最小化
- 排他制御による一時的な遅延あり

### メモリ使用量

- リクエストキューのサイズ制限なし（要注意）
- スレッドプールによる固定オーバーヘッド

## 注意事項

- 標準入力をブロッキングで読み取るため、パイプ経由での使用を想定
- エンドポイント名の大文字小文字は区別される
- Base64データは自動的にデコードされる
- 長時間のブロッキング処理は他のリクエストに影響する可能性
