## utils モジュール（src-python/utils.py）

このドキュメントは `src-python/utils.py` に対する最近のリファクタ内容、公開 API、利用上の注意点、テスト方法をまとめたものです。

### 概要
- `utils.py` はプロジェクト全体で使われる汎用ユーティリティ群を提供します。主な内容:
  - ネットワーク接続チェック (`isConnectedNetwork`)
  - ソケットの空きポート確認 (`isAvailableWebSocketServer`)
  - IP アドレス検証 (`isValidIpAddress`)
  - 計算デバイス一覧取得 (`getComputeDeviceList` / `getBestComputeType`)
  - Base64 デコード (JSON) (`encodeBase64`)
  - ロガー設定/ログ出力ヘルパー (`setupLogger`, `printLog`, `printResponse`, `errorLogging`)

### 今回のリファクタ（要点）
- Optional 依存へのフォールバック: `torch` と `ctranslate2` が存在しない環境でも動作するよう、import をガードし、安全なデフォルトを返す実装にしました。
- 型注釈と docstring を追加して可読性を向上させました。
- ログ設定の重複ハンドラ追加を防ぐチェックを導入しました。
- `encodeBase64` はデコード失敗時に例外を投げず空辞書を返すように（安全側）変更しました。
- `getComputeDeviceList` は GPU 情報取得で失敗しても CPU 情報を返すように例外保護を行いました。

### 重要な利用上の注意（breaking/behavior changes）
- Optional 依存
  - `torch` が無い環境では GPU 情報は取得できません（`getComputeDeviceList` は CPU エントリのみ返します）。
  - `ctranslate2` の `get_supported_compute_types` が無い場合は空リストを返します。
  → 環境に依存する挙動を想定して、呼び出し側は存在チェックやフォールバックを実装してください。

- `encodeBase64` の挙動
  - 不正な base64/JSON を入力した場合、例外を投げず `{}` を返します。既存コードが例外を期待している場合は注意してください。

- `isAvailableWebSocketServer` の仕様
  - 指定した host:port に対して bind が成功すれば True を返します（「使用中かどうか」を判定する用途と逆の意味合いになることがあるため注意）。

- ロギング
  - `setupLogger` は同じログファイルに対するハンドラを重複して追加しません。`errorLogging()` はログ書き込みに失敗した場合でも最後に trace を stdout に出力するフォールバックがあります。

### API 使い方（短い例）

```python
from utils import getComputeDeviceList, encodeBase64, printResponse

devices = getComputeDeviceList()
print(devices)

obj = encodeBase64('eyAia2V5IjogInZhbHVlIiB9')  # -> {'key': 'value'}

printResponse(200, '/health', {'status': 'ok'})
```

### テスト方針
- optional 依存の違いを扱うため、ユニットテストは `torch` と `ctranslate2` をモックして行うことを推奨します。
- 例: `getComputeDeviceList()` は GPU がない環境でも CPU のエントリを返すことを確認するテスト。

### トラブルシュート
- ログファイルの書き込みエラー: 権限やディスク容量を確認してください。`error.log` と `process.log` の存在と権限をチェックします。
- `getComputeDeviceList()` が空しか返さない場合、`torch` または `ctranslate2` のインストールを確認してください。

### 変更履歴
- 2025-10-09: 型注釈・docstring 追加、optional import ガード、ロギング堅牢化。
# utils.py — 関数一覧と使用例
目的: 共通ユーティリティ（ログ、JSON 出力、ネットワーク/ポート検査、デバイス/計算タイプ列挙、バリデーション等）を提供します。

主要関数とシグネチャ:
- validateDictStructure(data: dict, structure: dict) -> bool
- isConnectedNetwork(url: str = "http://www.google.com", timeout: int = 3) -> bool
- isAvailableWebSocketServer(host: str, port: int) -> bool
- isValidIpAddress(ip_address: str) -> bool
- getComputeDeviceList() -> dict
- getBestComputeType(device: str, device_index: int) -> str
- encodeBase64(data: str) -> dict
- removeLog() -> None
- setupLogger(name, log_file, level=logging.INFO) -> logging.Logger
- printLog(log: str, data: Any = None) -> None
- printResponse(status: int, endpoint: str, result: Any = None) -> None
- errorLogging() -> None

使用例:

```python
from utils import printResponse, getComputeDeviceList, validateDictStructure

# JSON 形式で mainloop に応答を返す
printResponse(200, '/get/data/version', {'version': '3.2.2'})

# 利用可能な計算デバイス一覧を取得
devices = getComputeDeviceList()
print(devices)

# 辞書構造のバリデーション
data = {'a': 1, 'b': {'c': 'x'}}
structure = {'a': int, 'b': {'c': str}}
ok = validateDictStructure(data, structure)
print('valid:', ok)
```

注意点:
- `printResponse` は stdout に JSON を出力しつつログファイルにも書き込みます。大きなオブジェクトは json.dumps で失敗する可能性があるため、例外処理が含まれています。

# utils.py — 詳細設計

目的: 小さなユーティリティ関数群。ロギング、ネットワーク検査、型検証、計算デバイス列挙など。

主要関数/変数:
- validateDictStructure(data: dict, structure: dict) -> bool
  - 説明: 辞書が期待される構造（キーセットと値の型／入れ子）に完全一致するか検証する。
  - 入力: data（検証対象）, structure（期待構造: 値が型または入れ子 dict）
  - 出力: bool
  - 例外: 型不一致や欠落時は False を返す（例外は投げない）。

- isConnectedNetwork(url="http://www.google.com", timeout=3) -> bool
  - 説明: 指定 URL に HTTP GET して接続可否を判定。requests を使用。

- isAvailableWebSocketServer(host: str, port: int) -> bool
  - 説明: 指定ポートへ bind できるかを試し、使用中かを判別する（True=利用可能）。

- isValidIpAddress(ip_address: str) -> bool
  - 説明: ipaddress.ip_address で検証。

- getComputeDeviceList() -> dict
  - 説明: CPU と CUDA（利用可能なら）を列挙し、各デバイスでサポートされる compute types を取得する。
  - 依存: torch, ctranslate2.get_supported_compute_types

- getBestComputeType(device: str, device_index: int) -> str
  - 説明: デバイス名に基づき優先 compute_type を選び、利用可能なものを返す。デフォルトは "float32"。

- setupLogger(name, log_file, level=logging.INFO) -> Logger
  - 説明: RotatingFileHandler を使って UTF-8 ログを作る。10MB ローテーション。

- printLog / printResponse / errorLogging
  - 説明: mainloop と通信するために標準出力へ JSON を flush するユーティリティ。内部で file ログへも書く。

注意点:
- ネットワーク検査やファイル生成で例外が発生した場合、errorLogging() を呼んでトレースを error.log に保存する。
