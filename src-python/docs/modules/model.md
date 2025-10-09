# model.py — クラスと主要メソッド
目的: アプリケーションの中核オーケストレータ。翻訳器 (Translator)、オーバーレイ、トランスクリプタ、OSC、WebSocket、Watchdog などのインスタンスを保持し、これらの起動/停止/操作を担います。`model` は `Model` のシングルトンインスタンスです。

主要クラスとシグネチャ:
- class threadFnc(Thread)
  - __init__(self, fnc, end_fnc=None, daemon=True, *args, **kwargs)
  - stop(self) -> None
  - pause(self) -> None
  - resume(self) -> None

- class Model
  - __new__(cls) -> Model
  - init(self) -> None
  - checkTranslatorCTranslate2ModelWeight(self, weight_type: str) -> bool
  - changeTranslatorCTranslate2Model(self) -> None
  - downloadCTranslate2ModelWeight(self, weight_type, callback=None, end_callback=None) -> Any
  - isLoadedCTranslate2Model(self) -> bool
  - getListLanguageAndCountry(self) -> list
  - getTranslate(self, translator_name, source_language, target_language, target_country, message) -> tuple
  - getInputTranslate(self, message, source_language=None) -> (list, list)
  - getOutputTranslate(self, message, source_language=None) -> (list, list)
  - startMicTranscript(self, fnc) -> None
  - stopMicTranscript(self) -> None
  - startSpeakerTranscript(self, fnc: Optional[Callable[[dict], None]] = None) -> None
  - stopSpeakerTranscript(self) -> None
  - startWebSocketServer(self, host, port) -> None
  - stopWebSocketServer(self) -> None
  - websocketSendMessage(self, message_dict: dict) -> bool

  変更点（2025-10-09）:

  - startCheckMicEnergy(self, fnc: Optional[Callable[[float], None]] = None) -> None
    - 説明: 進捗/エネルギー表示用のコールバックを受け取ります。fnc が None の場合は内部で no-op を使い、呼び出し前に callable チェックを行います。これにより呼び出し側が None を渡しても安全になりました。

  - startCheckSpeakerEnergy(self, fnc: Optional[Callable[[float], None]] = None) -> None
    - 説明: 同上（fnc を Optional として受け取り、呼び出し時に callable を確認します）。内部では Queue を作成して録音データを受け取り、定期的にコールバックを呼びます。

  - convertMessageToTransliteration(self, message: str, hiragana: bool = True, romaji: bool = True) -> list
    - 説明: 以前は単一の文字列や別形を返す箇所がありましたが、現在は常にリスト（トークン単位の dict を要素とする list）を返します。hiragana/romaji の両方が False の場合は空リストを返します。

  - createOverlayImageLargeLog(self, message_type: str, message: Optional[str], your_language: Optional[str], translation: list, target_language: Optional[dict] = None) -> object
    - 説明: `target_language` は辞書形式で渡される場合があり、内部で言語リストに正規化されます（enabled な言語のみ抽出）。`message` / `your_language` は Optional となり、`None` を渡して翻訳のみのログを作ることが可能です。

使用例（簡易）:

```python
from model import model

# 翻訳を呼び出す
translation, success = model.getTranslate('CTranslate2', 'Japanese', 'English', 'United States', 'こんにちは')
print(translation, success)

# マイク文字起こしの開始（コールバックで結果を受け取る）
def on_mic_transcript(result):
    print('mic transcript:', result)

model.startMicTranscript(on_mic_transcript)

# WebSocket サーバー起動
model.startWebSocketServer('127.0.0.1', 2231)

```

注意点:
- `Model` は多くの外部リソース（GPU、ファイル、ネットワーク）に依存するため、各操作は例外処理で保護されています。
- 大きなモデルのロードで VRAM OOM を検出する `detectVRAMError` を備え、Controller 側でのフォールバック処理に使われます。

## 詳細設計

### 2025-10-09 のリファクタリング要約

- 遅延初期化 (lazy-init): `Model` のコンストラクタで重い初期化を行わず、`model.init()` を明示的に呼ぶか、各メソッド先頭で呼ばれる `ensure_initialized()` によって必要時に初期化する設計に変更しました。これによりインポート時の副作用（外部環境依存の初期化）が抑止されます。

- `threadFnc` の堅牢化: スレッドユーティリティは args/kwargs をインスタンスで保持し、内部で発生する例外を捕捉して `utils.errorLogging()` に委ねるようになりました。これによりバックグラウンドスレッドが例外で終了するリスクを減らしています。

- `device_manager` 呼び出しのガード: `getListMicHost()` / `getListMicDevice()` / `getMicDefaultDevice()` / `getListSpeakerDevice()` など、`device_manager` を参照する箇所は try/except で保護され、失敗時は安全なデフォルト（空リストや `"NoDevice"`）を返すようになりました。

- WebSocket/Overlay/Watchdog 等の起動系メソッドは `ensure_initialized()` を先頭に呼ぶようになり、遅延初期化の恩恵を受けるようになっています。

これらの変更は非破壊で既存の API を維持することを目的としていますが、起動フローで確実にリソースを確保したい場合はアプリ起動時に `model.init()` を呼ぶことを推奨します。


目的: 各モデル（翻訳/転写/Overlay/Watchdog/OSC/WebSocket 等）のインスタンスを保持し、高レベルの操作を提供するファサード。

主要クラス/変数:
- class threadFnc(Thread)
  - 説明: ループする関数をバックグラウンドで呼ぶヘルパ。pause/stop/end callback をサポート。

- class Model
  - シングルトン: ファイル末で `model = Model()` として公開。
  - 主な属性:
    - translator (Translator)
    - overlay (Overlay)
    - overlay_image (OverlayImage)
    - mic_audio_queue, mic_audio_recorder, mic_transcriber
    - speaker_audio_queue, speaker_audio_recorder, speaker_transcriber
    - watchdog (Watchdog)
    - osc_handler (OSCHandler)
    - websocket_server (WebSocketServer)
  - 主なメソッド:
    - start/stop logger, overlay, watchdog
    - startMicTranscript / stopMicTranscript: 録音、transcriber の起動とキュー処理
    - startSpeakerTranscript / stopSpeakerTranscript
    - startCheckMicEnergy / stopCheckMicEnergy
    - startCheckSpeakerEnergy / stopCheckSpeakerEnergy
    - getTranslate / getInputTranslate / getOutputTranslate: Translator を利用する高レベル関数
    - createOverlayImage* / updateOverlay* : OverlayImage と Overlay を結合して VR 表示を作成
    - startWebSocketServer / stopWebSocketServer / websocketSendMessage

エラー処理:
- 音声認識や翻訳で VRAM エラーが発生した場合、detectVRAMError() で特殊な例外内容を検査し、Controller 経由で翻訳機能を OFF にする処理がある。

非同期/リソース:
- Recorder/Transcriber/Overlay/Watchdog/WebSocket はそれぞれ別スレッドで動作する。Model はそれらの開始/停止を管理する。

依存:
- models/translation, models/transcription, models/overlay, models/osc, models/websocket

