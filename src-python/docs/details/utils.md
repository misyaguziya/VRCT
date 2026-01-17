# utils.py - ユーティリティ関数モジュール

## 概要

VRCTアプリケーション全体で使用される汎用的なユーティリティ関数を提供するモジュールです。データ検証、ネットワーク接続確認、計算デバイス管理、ログ機能などの共通機能を集約しています。

## 主要機能

### データ検証機能

- 辞書構造の型安全な検証
- IPアドレス形式の検証
- WebSocketサーバーの可用性確認

### システム情報取得

- 利用可能な計算デバイス（CPU/CUDA）の一覧取得
- 最適な計算タイプの自動選択
- デバイス固有の制約対応

### ログ機能

- 構造化ログの出力
- ローテーションログファイル管理
- エラーログとプロセスログの分離

### ネットワーク機能

- インターネット接続状態の確認
- Base64エンコード/デコード処理

## 主要関数

### データ検証

```python
validateDictStructure(data: dict, structure: dict) -> bool
```

- 辞書とその期待される構造が完全に一致するかを判別
- 入れ子構造にも対応
- 型安全性を保証

### ネットワーク関連

```python
isConnectedNetwork(url="http://www.google.com", timeout=3) -> bool
```

- 指定URLへの接続可能性をチェック
- タイムアウト設定可能

```python
isAvailableWebSocketServer(host: str, port: int) -> bool
```

- WebSocketサーバーのバインド可能性を確認

```python
isValidIpAddress(ip_address: str) -> bool
```

- IPv4/IPv6アドレスの有効性を検証

### 計算デバイス管理

```python
getComputeDeviceList() -> List[Dict[str, Any]]
```

- 利用可能なCPU/CUDA計算デバイスの一覧を取得
- 各デバイスの計算タイプを含む詳細情報を提供

```python
getBestComputeType(device: str, device_index: int) -> str
```

- デバイスに最適な計算タイプを自動選択
- GPU固有の制約を考慮（GTX、RTX、Tesla、A100、Quadro等）

### ログ機能

```python
setupLogger(name: str, log_file: str, level: int = logging.INFO) -> logging.Logger
```

- ローテーション機能付きログの設定
- 10MBサイズでのローテーション
- UTF-8エンコード対応

```python
printLog(log: str, data: Any = None) -> None
```

- 構造化プロセスログの出力
- JSON形式での標準出力

```python
printResponse(status: int, endpoint: str, result: Any = None) -> None
```

- APIレスポンスの構造化出力
- シリアライゼーションエラーの安全な処理

```python
errorLogging() -> None
```

- 例外トレースバックのログ記録
- フォールバック機能付き

### その他のユーティリティ

```python
encodeBase64(data: str) -> Dict[str, Any]
```

- Base64エンコード済みJSON文字列のデコード
- エラー処理付き

```python
removeLog() -> None
```

- プロセスログファイルの初期化

## 使用方法

### 基本的な使い方

```python
from utils import validateDictStructure, isConnectedNetwork, printLog

# 辞書構造の検証
expected_structure = {"name": str, "age": int}
data = {"name": "test", "age": 25}
is_valid = validateDictStructure(data, expected_structure)

# ネットワーク接続確認
is_connected = isConnectedNetwork()

# ログ出力
printLog("処理開始", {"user_id": 123})
```

### 計算デバイス管理

```python
from utils import getComputeDeviceList, getBestComputeType

# 利用可能デバイス一覧
devices = getComputeDeviceList()

# 最適な計算タイプ選択
compute_type = getBestComputeType("cuda", 0)
```

### ログ設定

```python
from utils import setupLogger, errorLogging

# カスタムログの設定
logger = setupLogger("my_module", "my_module.log")
logger.info("処理完了")

# エラーログ記録
try:
    # 何らかの処理
    pass
except Exception:
    errorLogging()
```

## 依存関係

### 必須依存関係

- `json`: JSON処理
- `logging`: ログ機能
- `requests`: HTTP通信
- `ipaddress`: IPアドレス検証
- `socket`: ソケット通信

### オプション依存関係

- `torch`: CUDA計算デバイス情報取得
- `ctranslate2`: 計算タイプ情報取得

## デバイス別計算タイプ制約

### GTXシリーズ
- サポート: `float32`のみ
- 理由: 古いアーキテクチャによる制約

### RTX/Tesla/A100/Quadroシリーズ
- サポート: フル機能
- 優先順位: `int8_bfloat16` > `int8_float16` > `int8` > `bfloat16` > `float16` > `int8_float32` > `float32`

### CPU
- サポート: 全計算タイプ（ハードウェア依存）

## エラーハンドリング

- すべての関数は例外安全性を考慮
- オプション依存関係の欠如に対する適切なフォールバック
- ログ機能は多段階のフェールセーフ機構を持つ

## 注意事項

- 計算デバイス情報取得は初回実行時にやや時間がかかる場合がある
- ログローテーションは10MBサイズで自動実行
- ネットワーク接続確認はデフォルト3秒のタイムアウト設定