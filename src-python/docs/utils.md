# utils.py ドキュメント

## 概要
`utils.py` は VRCT アプリケーション全体で使用される汎用ユーティリティ関数とロギング機能を提供するモジュール。辞書構造の検証、ネットワーク接続確認、計算デバイス管理、Base64エンコーディング、構造化ログ出力など、複数のサブシステムで共有される基盤機能を集約している。

## 主要機能
- 辞書構造の厳密な検証
- ネットワーク接続状態の診断
- WebSocketサーバーのアドレス可用性チェック
- IPアドレスのバリデーション
- CUDA/CPU計算デバイスの検出と最適化
- 構造化ログ出力（process.log, error.log）
- Base64エンコード/デコード
- ログファイルのローテーション管理

## アーキテクチャ上の位置づけ

```
┌─────────────────┐
│ All Modules     │ (controller, model, device_manager, etc.)
└────────┬────────┘
         │ Import
┌────────▼────────┐
│   utils.py      │ ◄── このファイル
└─────────────────┘
         │
┌────────▼────────┐
│ External Deps   │ (torch, ctranslate2, requests, ipaddress)
└─────────────────┘
```

全てのモジュールから参照される共通基盤として機能し、循環参照を避けるため他の内部モジュールへの依存を持たない。

## 依存関係

### 標準ライブラリ
```python
import base64
import json
import traceback
import logging
from logging.handlers import RotatingFileHandler
from typing import Any, List, Dict, Optional
```

### サードパーティライブラリ（オプション依存）
```python
import torch  # GPU検出用（インポート失敗時はNoneにフォールバック）
from ctranslate2 import get_supported_compute_types  # 計算タイプ取得用
import requests  # ネットワーク接続確認用
import ipaddress  # IPアドレス検証用
import socket  # WebSocketサーバー可用性チェック用
```

**セーフガードインポート:**
```python
try:
    import torch
except Exception:
    torch = None  # type: ignore

try:
    from ctranslate2 import get_supported_compute_types
except Exception:
    def get_supported_compute_types(device: str, device_index: int) -> List[str]:
        return []
```

オプション依存が満たされない環境でもモジュールは正常にロード可能。

## 関数リファレンス

### 1. 辞書構造検証

#### `validateDictStructure(data: dict, structure: dict) -> bool`

**責務:** 辞書の構造と型が期待される仕様と完全に一致するかを検証

**アルゴリズム:**
1. 両方が辞書型であることを確認
2. キーの数と名前が完全一致するかチェック
3. 各キーの値について:
   - 期待値が辞書の場合: 再帰的に検証（多重入れ子対応）
   - 期待値が型オブジェクトの場合: `isinstance()` で型チェック

**引数:**
- `data` (dict): 検証対象の辞書
- `structure` (dict): 期待される構造定義
  - 値には型（str, int, bool等）または入れ子の辞書を指定

**返り値:**
- `True`: 構造が完全に一致
- `False`: 不一致（キー不足、余分なキー、型不一致等）

**使用例:**
```python
# 単純な構造検証
data = {"name": "Alice", "age": 30}
structure = {"name": str, "age": int}
assert validateDictStructure(data, structure) is True

# 入れ子構造の検証
data = {
    "user": {
        "id": 123,
        "profile": {"name": "Bob", "active": True}
    }
}
structure = {
    "user": {
        "id": int,
        "profile": {"name": str, "active": bool}
    }
}
assert validateDictStructure(data, structure) is True

# 不一致の検出
data = {"name": "Alice", "extra_key": "value"}
structure = {"name": str, "age": int}
assert validateDictStructure(data, structure) is False  # キーが不一致
```

**使用場面:**
- フロントエンドからのリクエストペイロード検証
- 設定ファイルのスキーマ検証
- API レスポンスの構造確認

---

### 2. ネットワーク診断

#### `isConnectedNetwork(url: str = "http://www.google.com", timeout: int = 3) -> bool`

**責務:** インターネット接続の可用性を高速チェック

**処理:**
1. 指定URLに HTTP GET リクエストを送信
2. `timeout` 秒以内に 200 OK レスポンスを受信したら接続あり
3. タイムアウトまたは例外発生時は接続なし

**引数:**
- `url` (str): 接続確認先URL（デフォルト: Google）
- `timeout` (int): タイムアウト時間（秒）

**返り値:**
- `True`: ネットワーク接続あり
- `False`: ネットワーク接続なし

**使用例:**
```python
if isConnectedNetwork():
    # モデルウェイトをダウンロード
    downloadModelWeights()
else:
    # オフラインモードで動作
    useLocalModels()
```

**注意事項:**
- ファイアウォールやプロキシ環境では正しく動作しない場合がある
- 初期化時の1回のみチェックを推奨（頻繁な呼び出しは避ける）

---

#### `isAvailableWebSocketServer(host: str, port: int) -> bool`

**責務:** 指定したホスト/ポートでWebSocketサーバーが起動可能かを確認

**処理:**
1. TCP ソケットを作成
2. `SO_REUSEADDR` オプションを設定
3. `bind()` を試行
4. 成功 → アドレス利用可能、失敗 → アドレス使用中

**引数:**
- `host` (str): バインドするIPアドレス
- `port` (int): バインドするポート番号

**返り値:**
- `True`: アドレスが利用可能
- `False`: アドレスが使用中

**使用例:**
```python
if isAvailableWebSocketServer("127.0.0.1", 8080):
    startWebSocketServer("127.0.0.1", 8080)
else:
    print("Port 8080 is already in use")
```

**注意事項:**
- `SO_REUSEADDR` により、TIME_WAIT 状態のアドレスも利用可能と判定される
- 管理者権限が必要なポート（1024未満）では失敗する場合がある

---

#### `isValidIpAddress(ip_address: str) -> bool`

**責務:** IPv4/IPv6アドレスの妥当性を検証

**処理:**
- `ipaddress.ip_address()` でパース
- 成功 → 有効なIPアドレス、失敗 → 無効

**引数:**
- `ip_address` (str): 検証対象のIPアドレス文字列

**返り値:**
- `True`: 有効なIPアドレス
- `False`: 無効なIPアドレス

**使用例:**
```python
assert isValidIpAddress("127.0.0.1") is True
assert isValidIpAddress("2001:db8::1") is True
assert isValidIpAddress("invalid") is False
```

**サポート形式:**
- IPv4: "192.168.1.1", "127.0.0.1"
- IPv6: "2001:db8::1", "fe80::1"

---

### 3. 計算デバイス管理

#### `getComputeDeviceList() -> List[Dict[str, Any]]`

**責務:** 利用可能な計算デバイス（CPU/GPU）とサポートされる計算タイプを列挙

**返り値構造:**
```python
[
    {
        "device": "cpu",
        "device_index": 0,
        "device_name": "cpu",
        "compute_types": ["auto", "float32", "int8", ...]
    },
    {
        "device": "cuda",
        "device_index": 0,
        "device_name": "NVIDIA GeForce RTX 3090",
        "compute_types": ["auto", "int8_bfloat16", "int8_float16", ...]
    },
    ...
]
```

**処理フロー:**
1. CPU デバイスを常に追加（最低限の計算環境を保証）
2. PyTorch と CUDA が利用可能な場合:
   - 全GPUデバイスを列挙
   - 各GPUの計算タイプを `get_supported_compute_types()` で取得
   - GPU アーキテクチャに応じて計算タイプを制限:
     - **GTX シリーズ**: `int8_bfloat16`, `bfloat16`, `float16`, `int8` を除外
     - **RTX, Tesla, A100, Quadro**: 全計算タイプをサポート
     - **その他**: `float32` のみ

**GPU別の計算タイプ制限:**
```python
if "GTX" in gpu_device_name:
    unsupported_types = {"int8_bfloat16", "bfloat16", "float16", "int8"}
    gpu_compute_types = [t for t in gpu_compute_types if t not in unsupported_types]
elif not any(keyword in gpu_device_name for keyword in ["RTX", "Tesla", "A100", "Quadro"]):
    gpu_compute_types = ["float32"]
```

**使用例:**
```python
devices = getComputeDeviceList()
for device in devices:
    print(f"{device['device_name']}: {', '.join(device['compute_types'])}")

# 出力例:
# cpu: auto, float32, int8
# NVIDIA GeForce RTX 3090: auto, int8_bfloat16, int8_float16, int8, bfloat16, float16, int8_float32, float32
```

**エラーハンドリング:**
- GPU検出中の例外は `errorLogging()` でログ記録し、CPU デバイスのみ返却

---

#### `getBestComputeType(device: str, device_index: int) -> str`

**責務:** デバイスアーキテクチャに最適な計算タイプを自動選択

**優先順位:**
```python
preferred_types = {
    "default": [
        "int8_bfloat16",   # 最も効率的（対応GPUのみ）
        "int8_float16",    # 2番目に効率的
        "int8",            # 整数演算高速化
        "bfloat16",        # 混合精度
        "float16",         # 半精度浮動小数点
        "int8_float32",    # 互換性重視
        "float32"          # フォールバック
    ],
    "GTX": ["float32"],  # GTXシリーズは制限あり
    "RTX": ["int8_bfloat16", "int8_float16", ...],
    "Tesla": [...],
    "A100": [...],
    "Quadro": [...]
}
```

**処理フロー:**
1. `get_supported_compute_types()` で利用可能な計算タイプを取得
2. デバイス名に基づいて優先リストを選択
3. 優先順に計算タイプをチェックし、最初に利用可能なものを返却
4. 全て利用不可の場合は `"float32"` を返却（安全なフォールバック）

**引数:**
- `device` (str): "cpu" または "cuda"
- `device_index` (int): GPUデバイスのインデックス（CPUの場合は0）

**返り値:**
- 最適な計算タイプ文字列（例: "int8_bfloat16", "float32"）

**使用例:**
```python
best_type = getBestComputeType("cuda", 0)
model.load_model(compute_type=best_type)
```

**計算タイプの特性:**

| 計算タイプ | メモリ使用量 | 速度 | 精度 | 対応GPU |
|----------|------------|------|------|--------|
| int8_bfloat16 | 最小 | 最速 | 高 | RTX 30xx以降 |
| int8_float16 | 最小 | 最速 | 高 | RTX 20xx以降 |
| int8 | 小 | 高速 | 中 | 多くのGPU |
| bfloat16 | 中 | 高速 | 高 | RTX 30xx以降 |
| float16 | 中 | 高速 | 高 | RTX 20xx以降 |
| float32 | 大 | 標準 | 最高 | 全GPU/CPU |

---

### 4. エンコーディング

#### `encodeBase64(data: str) -> Dict[str, Any]`

**責務:** Base64エンコードされたJSON文字列をデコードしてパース

**処理:**
1. Base64デコード
2. UTF-8文字列に変換
3. JSON パース
4. 失敗時は空の辞書を返却

**引数:**
- `data` (str): Base64エンコードされたJSON文字列

**返り値:**
- パース成功: JSON オブジェクト
- パース失敗: `{}`（空の辞書）

**使用例:**
```python
# エンコード例（参考）
import base64
import json
payload = {"message": "Hello", "id": 123}
encoded = base64.b64encode(json.dumps(payload).encode('utf-8')).decode('utf-8')

# デコード
decoded = encodeBase64(encoded)
assert decoded == {"message": "Hello", "id": 123}
```

**エラーハンドリング:**
- 不正なBase64文字列
- 不正なJSON形式
- 文字エンコーディングエラー

全て `errorLogging()` でログ記録し、空の辞書を返却。

**注意事項:**
- 関数名が `encodeBase64` だが、実際には**デコード**を行う（命名の歴史的経緯）
- セキュリティ: Base64は暗号化ではないため、機密情報の保護には使用しない

---

### 5. ロギング

#### `removeLog() -> None`

**責務:** プロセスログファイル（process.log）を初期化

**処理:**
- `process.log` を空の内容で上書き
- ファイルが存在しない場合は新規作成

**使用例:**
```python
# アプリケーション起動時にログをクリア
removeLog()
printLog("Application started")
```

**エラーハンドリング:**
- ファイル書き込み失敗時は `errorLogging()` でエラーログに記録

---

#### `setupLogger(name: str, log_file: str, level: int = logging.INFO) -> logging.Logger`

**責務:** ローテーション機能付きロガーインスタンスを生成

**設定:**
- **最大ログサイズ**: 10MB
- **バックアップ数**: 1（最大2ファイル）
- **ローテーション動作**: 10MB到達時に `.1` バックアップを作成し、新規ログを開始
- **エンコーディング**: UTF-8
- **遅延書き込み**: `delay=True`（最初の書き込み時にファイルを開く）

**引数:**
- `name` (str): ロガー名（例: "process", "error"）
- `log_file` (str): ログファイルパス
- `level` (int): ログレベル（デフォルト: `logging.INFO`）

**返り値:**
- 設定済み `logging.Logger` インスタンス

**ログフォーマット:**
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

**出力例:**
```
2025-10-13 14:30:45,123 - process - INFO - Application started
2025-10-13 14:30:46,456 - error - ERROR - Connection failed
```

**重複ハンドラー防止:**
```python
if not any(isinstance(h, RotatingFileHandler) and getattr(h, 'baseFilename', None) == getattr(file_handler, 'baseFilename', None) for h in logger.handlers):
    logger.addHandler(file_handler)
```

同じファイルへの重複ハンドラー追加を防止し、複数回呼び出されても安全。

---

#### `printLog(log: str, data: Any = None) -> None`

**責務:** 構造化プロセスログの出力

**出力先:**
1. `process.log` ファイル
2. 標準出力（JSON形式）

**出力形式:**
```python
{
    "status": 348,  # プロセスログ専用ステータス
    "log": "User action performed",
    "data": "additional context"
}
```

**引数:**
- `log` (str): ログメッセージ
- `data` (Any): 追加のコンテキスト情報（オプション）

**使用例:**
```python
printLog("Model loading started", {"model_type": "whisper", "weight": "medium"})
# 出力（stdout）:
# {"status": 348, "log": "Model loading started", "data": "{'model_type': 'whisper', 'weight': 'medium'}"}
```

**実装の詳細:**
```python
global process_logger
if process_logger is None:
    process_logger = setupLogger("process", "process.log", logging.INFO)

response = {
    "status": 348,
    "log": log,
    "data": str(data),
}
process_logger.info(response)
serialized = json.dumps(response)
print(serialized, flush=True)
```

**注意事項:**
- `data` は `str()` で文字列化されるため、複雑なオブジェクトは読みにくくなる可能性がある
- `flush=True` により即座に出力（バッファリングを無効化）

---

#### `printResponse(status: int, endpoint: str, result: Any = None) -> None`

**責務:** 構造化APIレスポンスの出力

**出力先:**
1. `process.log` ファイル
2. 標準出力（JSON形式）

**出力形式:**
```python
{
    "status": 200,
    "endpoint": "/get/config/version",
    "result": {"version": "3.3.0"}
}
```

**引数:**
- `status` (int): HTTPステータスコード風のステータス番号
- `endpoint` (str): エンドポイント識別子
- `result` (Any): レスポンスペイロード（オプション）

**使用例:**
```python
printResponse(200, "/set/config/language", {"language": "ja"})
printResponse(400, "/set/config/threshold", {"error": "Value out of range"})
```

**JSONシリアライズエラーハンドリング:**
```python
try:
    serialized_response = json.dumps(response)
except Exception as e:
    errorLogging()  # 完全なトレースバックをログ
    process_logger.error(f"Problematic response object: {response}")
    process_logger.error(f"Exception during json.dumps: {e}")
    # フォールバックエラーペイロード
    error_json = json.dumps({
        "status": 500,
        "endpoint": endpoint,
        "result": {"error": "Failed to serialize response", "details": str(e)},
    })
    print(error_json, flush=True)
else:
    print(serialized_response, flush=True)
```

**シリアライズ不可能なオブジェクトの例:**
- `datetime` オブジェクト
- カスタムクラスインスタンス
- 循環参照を持つ辞書

**対策:**
- `result` を構築する際に JSON シリアライズ可能な型のみ使用
- 必要に応じて `str()` や専用のシリアライザーで変換

---

#### `errorLogging() -> None`

**責務:** 現在の例外トレースバックをエラーログに記録

**処理:**
1. `error.log` ファイルにトレースバックを出力
2. ロガー初期化失敗時は標準出力にフォールバック

**使用例:**
```python
try:
    risky_operation()
except Exception:
    errorLogging()  # トレースバックをerror.logに記録
    # 必要に応じて追加処理
```

**出力例（error.log）:**
```
2025-10-13 14:35:12,789 - error - ERROR - Traceback (most recent call last):
  File "model.py", line 123, in loadModel
    model.load()
  File "ctranslate2/model.py", line 456, in load
    raise RuntimeError("CUDA out of memory")
RuntimeError: CUDA out of memory
```

**注意事項:**
- **例外コンテキスト内でのみ呼び出し可能**（`traceback.format_exc()` を使用）
- 例外をキャッチせずに呼び出すと空のトレースバックが記録される

**ベストプラクティス:**
```python
try:
    dangerous_function()
except SpecificException as e:
    errorLogging()  # 詳細をログ
    # ユーザーフレンドリーなエラー処理
    printResponse(400, endpoint, {"error": "Operation failed"})
except Exception:
    errorLogging()  # 予期しないエラーもログ
    raise  # 上位へ伝播
```

---

## グローバル変数

### `process_logger: Optional[logging.Logger] = None`
プロセスログ用のグローバルロガーインスタンス。初回 `printLog()` または `printResponse()` 呼び出し時に初期化される。

### `error_logger: Optional[logging.Logger] = None`
エラーログ用のグローバルロガーインスタンス。初回 `errorLogging()` 呼び出し時に初期化される。

**遅延初期化の理由:**
- モジュールインポート時のオーバーヘッド削減
- ファイルシステムへの不要なアクセスを回避

---

## エラーハンドリング戦略

### 1. 防御的プログラミング
全てのユーティリティ関数は例外を内部で処理し、呼び出し元に例外を伝播しない:

```python
def isConnectedNetwork(url="http://www.google.com", timeout=3) -> bool:
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except requests.RequestException:
        return False  # 例外をキャッチして安全な値を返却
```

### 2. フォールバック値
- `encodeBase64()`: パース失敗時は `{}`
- `getComputeDeviceList()`: GPU検出失敗時はCPUのみ
- `getBestComputeType()`: 全て失敗時は `"float32"`

### 3. ログ記録
全てのエラーは `errorLogging()` でトレースバックを記録し、デバッグを容易にする。

---

## パフォーマンス考慮事項

### 1. ネットワーク接続チェック
`isConnectedNetwork()` はブロッキング操作（最大3秒）のため、起動時の1回のみ実行を推奨:

```python
# 良い例
if isConnectedNetwork():
    downloadModels()

# 悪い例（UI フリーズの原因）
while True:
    if isConnectedNetwork():  # 毎回3秒待機
        processData()
```

### 2. ログローテーション
10MB のログファイルローテーションにより、ディスク容量を制御（最大20MB）。

### 3. グローバルロガーの遅延初期化
ロガーは初回使用時に初期化されるため、インポート時のオーバーヘッドを最小化。

---

## 使用パターン

### パターン1: ネットワーク依存機能の初期化
```python
def initialize_online_features():
    if not isConnectedNetwork():
        printLog("Offline mode: skipping model download")
        return

    printLog("Online mode: downloading models")
    downloadModels()
```

### パターン2: デバイス自動選択
```python
devices = getComputeDeviceList()
if len(devices) > 1:
    # GPU利用可能
    best_device = devices[1]  # 最初のGPU
    best_type = getBestComputeType(best_device["device"], best_device["device_index"])
    printLog(f"Using GPU: {best_device['device_name']}", {"compute_type": best_type})
else:
    # CPUのみ
    printLog("No GPU detected, using CPU")
    best_type = "float32"
```

### パターン3: 構造化リクエスト検証
```python
def handle_request(payload):
    expected_structure = {
        "action": str,
        "data": {
            "id": int,
            "value": str
        }
    }

    if not validateDictStructure(payload, expected_structure):
        printResponse(400, "/handle_request", {"error": "Invalid request structure"})
        return

    # 処理続行
    printLog("Valid request received", payload)
```

### パターン4: WebSocketサーバー起動
```python
def start_websocket(host, port):
    if not isValidIpAddress(host):
        printResponse(400, "/websocket/start", {"error": "Invalid IP address"})
        return

    if not isAvailableWebSocketServer(host, port):
        printResponse(400, "/websocket/start", {"error": f"Port {port} is in use"})
        return

    # サーバー起動
    printLog(f"Starting WebSocket server", {"host": host, "port": port})
    startServer(host, port)
```

---

## テスト推奨事項

### 単体テスト例

**辞書構造検証:**
```python
def test_validate_dict_structure_simple():
    data = {"name": "Alice", "age": 30}
    structure = {"name": str, "age": int}
    assert validateDictStructure(data, structure) is True

def test_validate_dict_structure_nested():
    data = {"user": {"id": 1, "active": True}}
    structure = {"user": {"id": int, "active": bool}}
    assert validateDictStructure(data, structure) is True

def test_validate_dict_structure_invalid():
    data = {"name": "Alice"}
    structure = {"name": str, "age": int}  # 'age'キーが不足
    assert validateDictStructure(data, structure) is False
```

**ネットワーク診断:**
```python
def test_network_connection():
    # 実際のネットワーク接続をテスト
    result = isConnectedNetwork()
    assert isinstance(result, bool)

def test_network_timeout():
    # タイムアウト動作を確認
    result = isConnectedNetwork(url="http://192.0.2.1", timeout=1)
    assert result is False
```

**計算デバイス:**
```python
def test_get_compute_device_list():
    devices = getComputeDeviceList()
    assert len(devices) >= 1  # 最低限CPUが含まれる
    assert devices[0]["device"] == "cpu"

def test_get_best_compute_type():
    compute_type = getBestComputeType("cpu", 0)
    assert compute_type in ["float32", "int8"]
```

**ロギング:**
```python
def test_print_log(capsys):
    printLog("Test message", {"key": "value"})
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["status"] == 348
    assert output["log"] == "Test message"

def test_print_response(capsys):
    printResponse(200, "/test", {"result": "success"})
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["status"] == 200
    assert output["endpoint"] == "/test"
```

---

## セキュリティ考慮事項

### 1. IPアドレス検証
`isValidIpAddress()` はフォーマット検証のみで、プライベートアドレス範囲のチェックは行わない:

```python
# セキュリティを強化する場合
import ipaddress

def is_public_ip(ip_str):
    if not isValidIpAddress(ip_str):
        return False
    ip = ipaddress.ip_address(ip_str)
    return not (ip.is_private or ip.is_loopback or ip.is_reserved)
```

### 2. Base64デコード
`encodeBase64()` は入力検証を行わないため、信頼できないソースからのデータには注意:

```python
# 安全な使用例
if source_is_trusted:
    data = encodeBase64(base64_string)
else:
    # 追加の検証を実施
    pass
```

### 3. ログファイルへの機密情報記録
ログに機密情報（API キー、パスワード等）が含まれないよう注意:

```python
# 悪い例
printLog("API key loaded", api_key)

# 良い例
printLog("API key loaded", "***REDACTED***")
```

---

## 制限事項

1. **プラットフォーム依存性:**
   - GPU検出は CUDA 環境でのみ動作（ROCm/Metal非対応）

2. **ネットワークチェックの制限:**
   - ファイアウォール、プロキシ環境で誤判定の可能性
   - IPv6専用環境での動作は未検証

3. **ログファイルのスレッドセーフティ:**
   - `RotatingFileHandler` は基本的にスレッドセーフだが、高負荷時のローテーション中にログ損失の可能性

4. **計算タイプの最適化:**
   - `getBestComputeType()` の優先順位は一般的な推奨値であり、特定のモデルやタスクでは最適でない場合がある

---

## 依存モジュールとの関係

### controller.py
- デバイス管理の設定変更時にデバイスリスト取得
- エラー時のログ記録
- ネットワーク接続確認

### model.py
- 計算デバイスとタイプの決定
- エラー時のトレースバック記録

### config.py
- 起動時のネットワーク接続確認
- 計算デバイスリストの提供

### mainloop.py
- リクエスト/レスポンスの構造化ログ出力
- エラー時のトレースバック記録

---

## 今後の拡張性

### 1. 非同期ネットワークチェック
```python
import asyncio
import aiohttp

async def isConnectedNetworkAsync(url="http://www.google.com", timeout=3) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                return response.status == 200
    except Exception:
        return False
```

### 2. 構造化ログの拡張
```python
def printStructuredLog(level: str, message: str, context: dict = None):
    """
    より詳細な構造化ログ出力
    - timestamp
    - level
    - message
    - context (key-value pairs)
    - stack trace (error時)
    """
    pass
```

### 3. メトリクス収集
```python
def recordMetric(metric_name: str, value: float, tags: dict = None):
    """
    パフォーマンスメトリクスの記録
    - function execution time
    - memory usage
    - GPU utilization
    """
    pass
```

---

## 関連ドキュメント
- `controller.md`: Controller での utils 関数使用例
- `config.md`: Config での計算デバイス管理
- `model.md`: Model でのエラーハンドリング
- `コーディングルール.md`: ロギングとエラーハンドリングの規約

---

## ライセンス
プロジェクトのルートディレクトリの `LICENSE` ファイルを参照

---

## まとめ

`utils.py` は VRCT プロジェクトの基盤インフラストラクチャとして、以下の重要な責務を担う:

1. **安全性**: 全ての関数が例外を内部処理し、安全なフォールバック値を提供
2. **可観測性**: 構造化ログとローテーション機能により、問題の診断を容易化
3. **互換性**: オプション依存のセーフガードにより、様々な環境で動作
4. **最適化**: GPU アーキテクチャに応じた計算タイプの自動選択
5. **検証**: 辞書構造、IPアドレス、ネットワーク接続の厳密なバリデーション

全てのサブシステムから依存される中核モジュールとして、高い信頼性と保守性を維持している。
