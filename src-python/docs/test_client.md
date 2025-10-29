# test_client.py ドキュメント

## 概要
`test_client.py` は stdin/stdout 経由でバックエンド (`mainloop.py`) と通信し、各種 API エンドポイントを自動 / 半自動でテストするためのクライアントユーティリティ。初期化完了待機、ログ (status=348) 展開表示、サイレントモード、結果エクスポート(JSON/CSV)、Watchdog ハートビート送信 (/run/feed_watchdog) などの補助機能を備える。

## 主な責務
- バックエンドプロセス起動と初期化完了待機 (`/run/initialization_complete`)
- エンドポイント単発送信/応答待機 (Base64 エンコード/デコード)
- status=348 ログエントリの全文展開表示
- タイムアウト / 例外発生時の復旧メッセージ出力
- Watchdog ハートビート送信スレッド管理
- 自動テスター (`AutomatedEndpointTester`) による包括的エンドポイント試験
- テスト結果の JSON / CSV エクスポート (インタラクティブ指定)

## クラス構成
### `Color`
ANSIカラー定数を定義し、可読性の高い出力を実現。

### `TestClient`
バックエンドとの 1 プロセス・1 チャンネル通信を管理。

| 属性 | 役割 |
|------|------|
| `process` | 起動した Python バックエンド subprocess |
| `_watchdog_stop_event` | Watchdog スレッド停止制御用 Event |
| `_watchdog_thread` | /run/feed_watchdog 送信スレッド |

#### 初期化フロー
1. `subprocess.Popen([sys.executable, 'mainloop.py'], ...)` でバックエンド起動
2. `_wait_for_initialization()` を呼び出し `/run/initialization_complete` 受信まで待機
   - VRCT_INIT_TIMEOUT 環境変数があれば soft timeout として利用 (超過時 WARN のみ)
   - 30 秒間隔で進捗ログ (最後に受信した endpoint)
   - status=348 レコードは全文 JSON 展開
3. 初期化完了後 `_start_watchdog()` がバックグラウンドで /run/feed_watchdog を 30 秒間隔送信

#### 重要メソッド
- `send_request(endpoint, data=None, timeout=30.0, silent=False)`
  - リクエスト JSON を構築し送信
  - `data` は JSON シリアライズ → Base64 → `data` フィールド
  - 指定 endpoint のレスポンス行まで逐次読み取り (他 endpoint のログ行は通過)
  - status=348 の場合ログとして全文表示（silent=False のとき）
  - タイムアウト時 504 レスポンスを合成

- `_wait_for_initialization(timeout=None)`
  - 無期限または soft timeout 待機
  - プロセス死亡検知で RuntimeError

- `_start_watchdog()` / `cleanup()`
  - Watchdog スレッド開始と安全停止 (Event セット後 join)

### `AutomatedEndpointTester`
`backend_test.py` のロジック移植版（stdin/stdout プロトコル向け）。

| 属性 | 説明 |
|------|------|
| `silent` | True ならクライアント側詳細出力を抑制 |
| `export_path` | JSON エクスポート先 (None なら未出力) |
| `export_csv` | CSV 追加出力有無 |
| `results` | 収集したテストレコード一覧 |

#### エンドポイント分類 (ハードコード暫定)
- 有効/無効化: `/set/enable/*`, `/set/disable/*`
- 設定更新: `/set/data/*`
- 実行系: `/run/*`
- 削除系: `/delete/data/*`

#### 主メソッド
- `test_validity_single(endpoint)` 有効/無効化系単一試験
- `test_set_data_single(endpoint)` 設定更新系単一試験（事前に動的取得が必要な値は `/get/data/...` を呼び最新値をキャッシュ）
- `test_run_single(endpoint)` 実行系単一試験
- `test_delete_single(endpoint)` 削除系単一試験
- `run_all()` 全カテゴリ順次実行
- `run_random(count=1000)` 全エンドポイントプールからランダム選択
- `run_specific_random(category, count)` 指定カテゴリ内ランダム
- `summary()` 結果集計出力および必要な場合 JSON/CSV エクスポート

#### 結果レコード構造
```json
{
  "endpoint": "/set/data/transparency",
  "status": 200,
  "result": 85,
  "expected": "status==200"
}
```

CSV 例:
```
endpoint,status,expected,success
/set/data/transparency,200,status==200,True
```

## status=348 ログ取り扱い
- 初期化待機中: 展開してインデント付き表示
- リクエスト応答処理中: silent=False ならログエントリ全文を優先表示
- 通常 API 応答 (status != 348) との区別を明確化しデバッグ容易化

## Watchdog ハートビート
- 30 秒間隔で `/run/feed_watchdog` を送信 (fire-and-forget)
- 送信失敗時は警告を表示しループ終了
- クライアント終了時に停止イベントをセットしスレッド join でリーク防止

## エクスポート機能
### JSON エクスポート
- `export_path` が指定されていれば `results` を UTF-8 / ensure_ascii=False で整形出力
- フィールド: endpoint, status, result, expected, success

### CSV エクスポート
- JSON パスから拡張子置換（`.csv`）で派生 (内部 `_derive_csv_path` 相当ロジック)
- 成功判定: `status` と `expected` 文字列評価結果に依存 (単純比較)

## 例外 / エラー処理方針
| ケース | 対応 |
|--------|------|
| バックエンド終了検知 | 初期化待機中: RuntimeError を投げる / 通常通信: 500 レスポンス合成 |
| JSONDecodeError | ログ行扱いでスキップ (初期化中は進捗ログとして表示) |
| BrokenPipe / OSError | 通信切断とみなして 500 レスポンス返却 |
| タイムアウト | 504 レスポンス返却 (endpoint 同梱) |

## 制限事項
- エンドポイント一覧は動的取得ではなくハードコード (将来的改善余地)
- レスポンスの並行受信は未対応（1 リクエスト同期待ち）
- status=200 以外の詳細な意味的検証は限定的 (expected = 単純条件)
- Watchdog レスポンスは読み取らないため送信失敗検知は例外経路のみ

## 今後の改善候補
1. CLI 引数サポート (`--mode random --count 500 --silent --export result.json`)
2. 動的エンドポイント列挙 API 追加後の自動反映
3. リトライポリシー (指数バックオフ) 導入
4. 応答時間測定とパフォーマンスレポート出力
5. 並列テスト実行 (複数 subprocess / async IO)

## 参考
- `backend_test.py` : 元ロジック
- `utils.py` : status=348 ログ出力仕様
- `mainloop.md` : 通信プロトコル詳細

## まとめ
`test_client.py` は VRCT バックエンドに対する包括的なテストおよび運用補助を 1 ファイルで実現するツール。初期化待機の堅牢化（無期限 + soft timeout）、Watchdog ハートビート、ログ展開、静音化オプション、結果エクスポートにより長時間動作・回帰試験・CI への組み込みを容易にする基盤を提供する。
