# model.py — クラス一覧と使用例

以下は `model.py` で提供される主要クラスのシグネチャ概要と、簡単な呼び出し例です。

## クラス / 主要シグネチャ

- class threadFnc(Thread)
  - __init__(self, fnc: Callable, interval: float = 0.1, end_callback: Callable | None = None)
  - start(self) -> None
  - pause(self) -> None
  - resume(self) -> None
  - stop(self) -> None

- class Model
  - startLogger(self) -> None
  - stopLogger(self) -> None
  - startOverlay(self) -> None
  - shutdownOverlay(self) -> None
  - startMicTranscript(self, callback: Callable[[dict], None]) -> None
  - stopMicTranscript(self) -> None
  - startSpeakerTranscript(self, callback: Callable[[dict], None]) -> None
  - stopSpeakerTranscript(self) -> None
  - startCheckMicEnergy(self, progress_callback: Callable[[int], None]) -> None
  - stopCheckMicEnergy(self) -> None
  - startCheckSpeakerEnergy(self, progress_callback: Callable[[int], None]) -> None
  - stopCheckSpeakerEnergy(self) -> None
  - startWebSocketServer(self, host: str, port: int) -> None
  - stopWebSocketServer(self) -> None
  - websocketSendMessage(self, message: dict) -> None
  - getListMicHost(self) -> dict
  - getListMicDevice(self) -> list
  - getListSpeakerDevice(self) -> list
  - getInputTranslate(self, text: str, source_language: str = None) -> tuple[list[str], list[bool]]
  - getOutputTranslate(self, text: str, source_language: str = None) -> tuple[list[str], list[bool]]
  - detectVRAMError(self, exception: Exception) -> tuple[bool, str]

## サンプル（呼び出し例）

以下は Model の簡単な呼び出し例です。

```python
from model import model

# マイク転写のコールバック例
def on_mic_result(result: dict):
    # result の想定形: {"text": str|False, "language": str}
    text = result.get("text")
    language = result.get("language")
    print('mic:', text, language)

# マイク転写を開始（別スレッドで動く）
model.startMicTranscript(on_mic_result)

# 一度だけ翻訳を呼ぶ
translation, success = model.getInputTranslate('Hello', source_language='English')
print('translation:', translation, 'success:', success)

# WebSocket 経由で外部クライアントへイベント送信
model.websocketSendMessage({'type': 'INFO', 'message': 'VRCT ready'})
```
