# mainloop.py 設計書

## 概要

`mainloop.py` は VRCT アプリケーションのバックエンドエントリーポイントであり、stdin/stdout を介したフロントエンド（Tauri/React UI）との通信を担当する。JSON ベースのリクエスト/レスポンスプロトコルを実装し、複数のワーカースレッドによる並列処理と排他制御を提供する。

## 主要コンポーネント

### 1. グローバル変数

#### `run_mapping` (dict)
フロントエンドへの通知用エンドポイントマッピング。Controllerが `run()` コールバックを通じてフロントエンドに状態変化を通知する際に使用。

**主要なエンドポイント:**
- `/run/enable_translation` - 翻訳機能の有効/無効状態
- `/run/transcription_mic_message` - マイク音声認識結果
- `/run/transcription_speaker_message` - スピーカー音声認識結果
- `/run/error_*` - 各種エラー通知
- `/run/initialization_complete` - 初期化完了通知

#### `mapping` (dict)
フロントエンドからのリクエストを処理する関数マッピング。各エンドポイントに対して:
- `status`: ロック状態（True: 処理可能, False: ロック中）
- `variable`: 実行する Controller メソッド

**エンドポイント分類:**
- `/get/data/*` - 設定値の取得（初期化時に使用）
- `/set/data/*` - 設定値の更新
- `/set/enable/*` - 機能の有効化
- `/set/disable/*` - 機能の無効化
- `/run/*` - アクション実行（メッセージ送信、ダウンロード等）

#### `init_mapping` (dict)
初期化時に実行される `/get/data/*` エンドポイントのサブセット。アプリケーション起動時に全設定値をフロントエンドに送信するために使用。

### 2. Mainクラス

#### コンストラクタ `__init__(controller_instance, mapping_data, worker_count)`

**パラメータ:**
- `controller_instance`: Controller インスタンス
- `mapping_data`: エンドポイントマッピング辞書
- `worker_count`: ハンドラワーカースレッド数（デフォルト: 3）

**初期化処理:**
1. リクエストキュー (`Queue[Tuple[str, Any]]`) の作成
2. 停止イベント (`Event`) の作成
3. エンドポイント別 Lock の生成:
   - `/set/enable/xxx` と `/set/disable/xxx` を `/lock/set/xxx` に正規化
   - 同一機能の有効化/無効化リクエストが競合しないよう排他制御

**正規化ロジックの例:**
```python
"/set/enable/translation" → "/lock/set/translation"
"/set/disable/translation" → "/lock/set/translation"
# 両方が同じロックを共有 → 排他的に実行される
```

#### `receiver()` メソッド

**責務:** stdin から JSON リクエストを読み取り、キューに投入

**処理フロー:**
1. `sys.stdin.readline()` でブロッキング読み取り
2. JSON パース (`json.loads()`)
3. エンドポイントとデータを抽出
4. データが存在する場合は Base64 デコード (`encodeBase64()`)
5. ログ出力 (`printLog()`)
6. キューに投入 `self.queue.put((endpoint, data))`

**エラー処理:**
- JSON パースエラー: ログ出力して継続
- EOF 到達: 0.1秒待機して再試行
- その他の例外: `errorLogging()` でトレースバック記録

**スレッド:** デーモンスレッド `main_receiver` として起動

#### `handler()` メソッド

**責務:** キューからリクエストを取り出し、適切なロックを取得して処理

**処理フロー:**
1. キューから `(endpoint, data)` を取得（0.5秒タイムアウト）
2. エンドポイントを正規化キーに変換
3. 対応する Lock を取得試行（非ブロッキング）
   - 取得成功 → 処理実行 → ロック解放
   - 取得失敗 → 0.05秒待機して再キュー
4. `_call_handler(endpoint, data)` を呼び出し
5. レスポンスを stdout に出力 (`printResponse()`)

**排他制御の意義:**
- 例: 翻訳機能の有効化中に無効化リクエストが来た場合、無効化は待機
- 異なる機能のリクエストは並列実行可能

**再キューロジック:**
- status == 423 (Locked): 0.1秒待機して再キュー
- これにより、初期化中の設定変更リクエストが適切にリトライされる

**ワーカー数:** `worker_count` 個のスレッド `main_handler_0`, `main_handler_1`, ... として起動

#### `_call_handler(endpoint, data)` メソッド

**責務:** 実際のビジネスロジック実行

**処理フロー:**
1. `mapping` から対応するハンドラを取得
2. エンドポイントが存在しない → status 404
3. ハンドラの `status` が False → status 423 (Locked)
4. ハンドラの `variable` 関数を実行 → `response = handler["variable"](data)`
5. 0.2秒待機（処理安定化のため）
6. status と result を抽出して返却

**エラー処理:**
- 例外発生時: `errorLogging()` でトレースバック記録、status 500 を返却

#### `start()` / `stop(wait)` メソッド

**start():**
- `startReceiver()` - stdin 読み取りスレッド起動
- `startHandler()` - ハンドラワーカースレッド起動

**stop(wait):**
- `_stop_event.set()` - 全スレッドに停止シグナル送信
- 各スレッドを `join(timeout=remaining)` で待機（最大 `wait` 秒）

### 3. 初期化シーケンス

**`if __name__ == "__main__":` ブロック:**

1. `main_instance` 作成
2. `startReceiver()` - stdin リスニング開始
3. `startHandler()` - リクエスト処理開始
4. **Watchdog 設定:**
   - `controller.setWatchdogCallback(main_instance.stop)` 
   - Watchdog がタイムアウトした場合にプロセス全体を停止
5. **Controller 初期化:**
   - `controller.init()` 
   - Model の遅延初期化、デバイス列挙、ネットワーク接続チェック
   - `init_mapping` のすべてのエンドポイントを実行して初期設定をフロントエンドに送信
6. **マッピングのアンロック:**
   - すべての `mapping[key]["status"]` を True に設定
   - これにより初期化中だった機能が利用可能になる
7. `main_instance.start()` - 実質的には何もしない（既に起動済み）

## 並列処理とスレッドセーフティ

### スレッド構成

| スレッド名 | 役割 | 生存期間 |
|-----------|------|---------|
| `main_receiver` | stdin からの JSON 読み取り | プロセス終了まで |
| `main_handler_0` ~ `main_handler_N` | リクエスト処理ワーカー | プロセス終了まで |

### 同期メカニズム

1. **キュー (`Queue`):**
   - スレッドセーフな FIFO キュー
   - receiver → handler への通信チャネル

2. **エンドポイント別 Lock (`dict[str, Lock]`):**
   - 同一リソースへの競合アクセスを防止
   - 正規化キーによる enable/disable ペアの統合

3. **停止イベント (`Event`):**
   - グレースフルシャットダウン用のシグナル

### デッドロック回避

- **非ブロッキング Lock 取得:** `lock.acquire(blocking=False)`
- **失敗時の再キュー:** ロック取得失敗時は即座に諦めて再キュー
- **タイムアウト付きキュー取得:** `queue.get(timeout=0.5)` で無限待機を回避

## プロトコル仕様

### リクエストフォーマット (stdin)

```json
{
  "endpoint": "/set/data/transparency",
  "data": "ODU="  // Base64 encoded: "85"
}
```

**フィールド:**
- `endpoint`: 実行するエンドポイント（必須）
- `data`: パラメータ（オプション、Base64 エンコード）

### レスポンスフォーマット (stdout)

```json
{
  "status": 200,
  "endpoint": "/set/data/transparency",
  "result": 85
}
```

**フィールド:**
- `status`: HTTP ステータスコード相当
  - 200: 成功
  - 400: バリデーションエラー
  - 404: 無効なエンドポイント
  - 423: ロック中（リトライされる）
  - 500: 内部エラー
- `endpoint`: リクエストされたエンドポイント
- `result`: 処理結果（型はエンドポイントに依存）

### ログフォーマット (stdout)

```json
{
  "status": 348,  // 専用ステータスコード
  "log": "setSelectedTabNo",
  "data": "1"
}
```

## エラーハンドリング

### 1. JSON パースエラー
- **発生箇所:** `receiver()` の `json.loads()`
- **処理:** `errorLogging()` でトレースバック記録、リクエストをスキップ

### 2. ハンドラ実行エラー
- **発生箇所:** `_call_handler()` の `handler["variable"](data)`
- **処理:** 
  - `errorLogging()` でトレースバック記録
  - status 500 と "Internal error" を返却
  - プロセスは継続

### 3. JSON シリアライズエラー
- **発生箇所:** `printResponse()` の `json.dumps()`
- **処理:**
  - エラーログに詳細を記録
  - フォールバック JSON を出力（status 500）
  - プロセスは継続

### 4. EOF (stdin 終了)
- **発生箇所:** `receiver()` の `readline()`
- **処理:** 0.1秒待機して再試行（フロントエンドの再起動待ち）

## パフォーマンス最適化

### 1. 複数ワーカースレッド
- デフォルト3スレッドで並列処理
- CPU バウンドな処理（翻訳、文字起こし）を効率化

### 2. 非ブロッキングロック
- ロック競合時に即座に再キュー
- スレッドのブロッキング時間を最小化

### 3. 処理安定化待機
- 各ハンドラ実行後に 0.2秒待機
- 連続リクエストによる競合状態を回避

## 制限事項

### 1. 初期化中の制限
- `mapping[key]["status"] = False` の間はリクエストが 423 でリトライされる
- 初期化完了まで最大数秒のレイテンシが発生

### 2. stdin の単方向性
- stdin → キュー → ハンドラの一方向フロー
- 複数のフロントエンドからの同時接続は非対応

### 3. シリアル実行の保証
- 同一エンドポイントのリクエストは排他的に実行されるが、
- 異なるエンドポイントは並列実行される可能性がある
- 依存関係のある操作は呼び出し側で順序制御が必要

## デバッグとトラブルシューティング

### ログファイル

| ファイル名 | 内容 |
|-----------|------|
| `process.log` | 全リクエスト/レスポンスの記録 |
| `error.log` | 例外トレースバック |

### デバッグ手法

1. **リクエストトレース:**
   - `process.log` で endpoint と data を確認
   - Base64 デコードは `base64.b64decode(data).decode('utf-8')` で手動実行

2. **ロック競合の検出:**
   - 同一エンドポイントで status 423 が頻発する場合
   - `_canonical_lock_key()` の正規化ロジックを確認

3. **パフォーマンス分析:**
   - 各リクエストの処理時間は status 前後のタイムスタンプから算出
   - worker_count を増やして並列度を調整

## 今後の拡張性

### 1. 双方向通信
- WebSocket への移行でリアルタイム通知を改善
- stdin/stdout は互換性のため維持

### 2. 動的ワーカー数調整
- キューの深さに応じてスレッド数を自動調整
- CPU 負荷に応じた適応的なスケーリング

### 3. 優先度キュー
- 重要なリクエスト（エラー通知等）を優先処理
- `queue.PriorityQueue` への移行

## 関連ファイル

- `controller.py` - ビジネスロジック実装
- `model.py` - 機能ファサード
- `utils.py` - ログとユーティリティ
- `config.py` - 設定管理

## コーディング規約

本ファイルは以下の規約に従う:
- PEP 8 スタイルガイド
- 型ヒント (`typing` モジュール)
- Docstring は Google スタイル
- エラーハンドリングは防御的に実装

## テストシナリオ

### 1. 基本動作テスト
```python
# stdin に JSON を送信
echo '{"endpoint": "/get/data/version", "data": null}' | python mainloop.py
# 期待される出力: {"status": 200, "endpoint": "/get/data/version", "result": "1.0.0"}
```

### 2. 並列リクエストテスト
- 複数の設定変更リクエストを同時送信
- すべてが正常に処理されることを確認

### 3. ロック競合テスト
- 翻訳の有効化と無効化を連続送信
- 両方が排他的に実行されることを確認

### 4. エラー回復テスト
- 不正なJSON、無効なエンドポイント、不正なデータを送信
- プロセスがクラッシュせずエラーレスポンスを返すことを確認

## まとめ

`mainloop.py` は VRCT の中核となる通信レイヤーであり、stdin/stdout を介したフロントエンドとの JSON ベースプロトコルを実装する。複数のワーカースレッドと細粒度のロックにより、高い並列性と排他制御を両立させている。初期化シーケンスとエラーハンドリングは堅牢に設計されており、プロセスの安定稼働を保証する。
