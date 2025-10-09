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
