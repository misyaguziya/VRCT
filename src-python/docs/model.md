# model.py 設計書

## 概要

`model.py` は VRCT アプリケーションのビジネスロジックファサードとして機能し、音声認識、翻訳、オーバーレイ表示、OSC通信、WebSocket通信など、すべてのサブシステムへの統一されたインターフェースを提供する。シングルトンパターンで実装され、重い初期化処理を遅延実行することで、アプリケーションの起動時間を短縮している。

## アーキテクチャ上の位置づけ

```
┌─────────────┐
│controller.py│ (Business Logic Control Layer)
└──────┬──────┘
       │ Facade Pattern
┌──────▼──────┐
│  model.py   │ ◄── このファイル
└──────┬──────┘
       │ Aggregation & Delegation
┌──────▼────────────────────────────────┐
│ Subsystems                            │
│ - Translator                          │
│ - AudioTranscriber                    │
│ - Overlay / OverlayImage             │
│ - OSCHandler                          │
│ - WebSocketServer                     │
│ - Transliterator                      │
│ - Watchdog                            │
│ - DeviceManager (via device_manager)  │
└───────────────────────────────────────┘
```

## 主要コンポーネント

### 1. threadFnc クラス

**責務:** 関数を繰り返し実行するスレッドラッパー

**特徴:**
- デーモンスレッドとして動作
- ループ制御（停止・一時停止・再開）機能を提供
- 終了時のクリーンアップ関数をサポート

**メソッド:**

#### `__init__(fnc, end_fnc=None, daemon=True, *args, **kwargs)`

**パラメータ:**
- `fnc`: 繰り返し実行する関数
- `end_fnc`: スレッド終了時に実行する関数（オプション）
- `daemon`: デーモンフラグ（デフォルト: True）
- `*args, **kwargs`: `fnc` に渡す引数

#### `stop() -> None`
ループを停止し、スレッドを終了させる。

#### `pause() -> None`
ループを一時停止する（関数の実行を停止）。

#### `resume() -> None`
一時停止したループを再開する。

#### `run() -> None`
スレッドのメインループ。`self.loop` が True の間、`self.fnc()` を繰り返し呼び出す。

**使用例:**
```python
def print_message():
    print("Hello")
    sleep(1)

def cleanup():
    print("Thread ended")

th = threadFnc(print_message, end_fnc=cleanup)
th.start()
# ... しばらく実行 ...
th.stop()
th.join()
```

---

### 2. Model クラス

**責務:** アプリケーションのすべてのサブシステムへのファサードインターフェース

**パターン:** シングルトン（`__new__` で制御）

**初期化戦略:** 遅延初期化（Lazy Initialization）
- `__new__`: インスタンスの生成のみ（軽量）
- `init()`: 重い初期化処理（明示的な呼び出しが必要）
- `ensure_initialized()`: 初期化が必要なメソッドで自動的に呼び出される

---

### 3. 初期化メソッド

#### `__new__(cls) -> Model`

**責務:** シングルトンインスタンスの生成

**処理:**
1. `cls._instance` が None の場合のみ新規インスタンスを生成
2. `_inited` フラグを False に設定（実際の初期化は未実施）
3. 既存のインスタンスがあればそれを返却

**重要:** このメソッドでは重い初期化を行わない（import 時のパフォーマンス向上）

#### `init() -> None`

**責務:** すべてのサブシステムの初期化

**処理:**
1. **初期化済みチェック:** `_inited` フラグが True なら何もしない
2. **属性の初期化:**
   ```python
   self.logger = None
   self.mic_audio_queue = None
   self.mic_mute_status = None
   self.previous_send_message = ""
   self.previous_receive_message = ""
   ```
3. **サブシステムの初期化:**
   - `Translator()`: 翻訳エンジン
   - `KeywordProcessor()`: 禁止ワードフィルター
   - `Overlay()`: オーバーレイシステム
   - `OverlayImage()`: オーバーレイ画像生成
   - `Transliterator()`: 音訳（ひらがな・ローマ字変換）
   - `Watchdog()`: プロセス監視
   - `OSCHandler()`: OSC通信
   - `WebSocketServer()`: WebSocket通信
4. **コールバック関数の初期化:**
   ```python
   self.check_mic_energy_fnc: Callable[[float], None] = lambda v: None
   self.check_speaker_energy_fnc: Callable[[float], None] = lambda v: None
   ```
5. **初期化完了フラグ:** `_inited = True`

#### `ensure_initialized() -> None`

**責務:** 初期化が未実施の場合に `init()` を呼び出す

**使用箇所:** 初期化が必要なすべての public メソッド

**エラーハンドリング:**
```python
try:
    self.init()
except Exception:
    errorLogging()
```

---

### 4. 翻訳機能

#### モデルウェイト管理

##### `checkTranslatorCTranslate2ModelWeight(weight_type: str) -> bool`
指定されたモデルウェイトが存在するかチェック。

**パラメータ:**
- `weight_type`: "tiny", "small", "medium", "large" 等

**戻り値:** モデルが存在する場合 True

##### `downloadCTranslate2ModelWeight(weight_type, callback=None, end_callback=None) -> bool`

**責務:** CTranslate2 モデルウェイトのダウンロード

**パラメータ:**
- `weight_type`: モデルタイプ
- `callback`: 進捗通知用コールバック（`progress: float` を受け取る）
- `end_callback`: 完了時のコールバック

**実装:** `downloadCTranslate2Weight()` ユーティリティ関数に委譲

##### `downloadCTranslate2ModelTokenizer(weight_type) -> bool`
トークナイザーファイルのダウンロード。

#### 翻訳モデル制御

##### `changeTranslatorCTranslate2Model() -> None`

**責務:** 翻訳モデルの変更・再ロード

**処理:**
```python
self.translator.changeCTranslate2Model(
    path=config.PATH_LOCAL,
    model_type=config.CTRANSLATE2_WEIGHT_TYPE,
    device=config.SELECTED_TRANSLATION_COMPUTE_DEVICE["device"],
    device_index=config.SELECTED_TRANSLATION_COMPUTE_DEVICE["device_index"],
    compute_type=config.SELECTED_TRANSLATION_COMPUTE_TYPE
)
```

**VRAMエラー:** `ValueError("VRAM_OUT_OF_MEMORY")` を送出する可能性がある

##### `isLoadedCTranslate2Model() -> bool`
CTranslate2 モデルがロード済みかチェック。

##### `isChangedTranslatorParameters() -> bool`
翻訳パラメータが変更されたかチェック。

##### `setChangedTranslatorParameters(is_changed: bool) -> None`
翻訳パラメータ変更フラグを設定。

#### DeepL 認証

##### `authenticationTranslatorDeepLAuthKey(auth_key: str) -> bool`

**責務:** DeepL API キーの検証

**処理:** `translator.authenticationDeepLAuthKey()` に委譲

**戻り値:** 認証成功時 True

---

#### Groq API 統合

##### `authenticationTranslatorGroqAuthKey(auth_key: str) -> bool`

**責務:** Groq API キーの検証

**処理:** `translator.authenticationGroqAuthKey()` に委譲し、`root_path=config.PATH_LOCAL` を渡す

**戻り値:** 認証成功時 True

##### `getTranslatorGroqModelList() -> list[str]`

**責務:** 利用可能な Groq モデルリストの取得

**処理:** `translator.getGroqModelList()` に委譲

**戻り値:** モデル名のリスト（例: `["llama3-8b-8192", "mixtral-8x7b-32768"]`）

##### `setTranslatorGroqModel(model: str) -> bool`

**責務:** 使用する Groq モデルの設定

**処理:** `translator.setGroqModel(model)` に委譲

**戻り値:** 設定成功時 True（モデルが利用可能リストに含まれない場合 False）

##### `updateTranslatorGroqClient() -> None`

**責務:** Groq クライアントの更新（モデル変更後に呼び出し）

**処理:** `translator.updateGroqClient()` に委譲し、新しいモデルで LangChain `ChatOpenAI` インスタンスを再生成

---

#### OpenRouter API 統合

##### `authenticationTranslatorOpenRouterAuthKey(auth_key: str) -> bool`

**責務:** OpenRouter API キーの検証

**処理:** `translator.authenticationOpenRouterAuthKey()` に委譲し、`root_path=config.PATH_LOCAL` を渡す

**戻り値:** 認証成功時 True

##### `getTranslatorOpenRouterModelList() -> list[str]`

**責務:** 利用可能な OpenRouter モデルリストの取得

**処理:** `translator.getOpenRouterModelList()` に委譲

**戻り値:** モデル名のリスト（例: `["anthropic/claude-3-sonnet", "google/gemini-pro"]`）

##### `setTranslatorOpenRouterModel(model: str) -> bool`

**責務:** 使用する OpenRouter モデルの設定

**処理:** `translator.setOpenRouterModel(model)` に委譲

**戻り値:** 設定成功時 True（モデルが利用可能リストに含まれない場合 False）

##### `updateTranslatorOpenRouterClient() -> None`

**責務:** OpenRouter クライアントの更新（モデル変更後に呼び出し）

**処理:** `translator.updateOpenRouterClient()` に委譲し、新しいモデルで LangChain `ChatOpenAI` インスタンスを再生成

---

#### 翻訳実行

##### `getTranslate(translator_name, source_language, target_language, target_country, message) -> Tuple[str, bool]`

**責務:** メッセージの翻訳

**パラメータ:**
- `translator_name`: "CTranslate2", "DeepL", "DeepL_API" 等
- `source_language`: 元言語（"ja", "en" 等）
- `target_language`: 翻訳先言語
- `target_country`: 翻訳先国（方言対応用）
- `message`: 翻訳するテキスト

**戻り値:**
- `translation`: 翻訳結果（文字列）
- `success_flag`: 成功時 True

**エラーハンドリング:**
```python
translation = self.translator.translate(...)
if isinstance(translation, str):
    success_flag = True
else:
    # 翻訳失敗時のリトライロジック
    while True:
        # フェールセーフ処理
```

##### `getInputTranslate(message, source_language=None) -> Tuple[list, list]`

**責務:** 送信メッセージの翻訳（複数言語対応）

**処理:**
1. `config.SELECTED_TRANSLATION_ENGINES[config.SELECTED_TAB_NO]` で翻訳エンジンを取得
2. `config.SELECTED_TARGET_LANGUAGES` で翻訳先言語リストを取得
3. 有効な各言語について `getTranslate()` を呼び出し

**戻り値:**
- `translations`: 翻訳結果のリスト
- `success_flags`: 各翻訳の成功フラグのリスト

##### `getOutputTranslate(message, source_language=None) -> Tuple[list, list]`

**責務:** 受信メッセージの翻訳（単一言語）

**処理:** `getInputTranslate()` と同様だが、翻訳先が自分の言語（1つ）のみ

---

### 5. 音声認識機能

#### Whisper モデル管理

##### `checkTranscriptionWhisperModelWeight(weight_type: str) -> bool`
Whisper モデルウェイトの存在確認。

##### `downloadWhisperModelWeight(weight_type, callback=None, end_callback=None) -> bool`
Whisper モデルウェイトのダウンロード。

#### マイク音声認識

##### `startMicTranscript(fnc: Callable[[dict], None]) -> None`

**責務:** マイク音声認識の開始

**パラメータ:**
- `fnc`: 認識結果を受け取るコールバック関数

**処理フロー:**
1. **デバイス取得:**
   ```python
   mic_host_name = config.SELECTED_MIC_HOST
   mic_device_name = config.SELECTED_MIC_DEVICE
   mic_device_list = device_manager.getMicDevices().get(mic_host_name, [...])
   selected_mic_device = [device for device in mic_device_list if device["name"] == mic_device_name]
   ```
2. **デバイス検証:**
   - デバイスがない場合、`fnc({"text": False, "language": None})` を呼び出して終了
3. **音声キューの作成:**
   ```python
   self.mic_audio_queue = Queue()
   ```
4. **レコーダーの初期化:**
   ```python
   self.mic_audio_recorder = SelectedMicEnergyAndAudioRecorder(
       device=mic_device,
       energy_threshold=config.MIC_THRESHOLD,
       dynamic_energy_threshold=config.MIC_AUTOMATIC_THRESHOLD,
       phrase_time_limit=config.MIC_RECORD_TIMEOUT,
   )
   self.mic_audio_recorder.recordIntoQueue(self.mic_audio_queue, None)
   ```
5. **文字起こし器の初期化:**
   ```python
   self.mic_transcriber = AudioTranscriber(
       speaker=False,
       source=self.mic_audio_recorder.source,
       phrase_timeout=config.MIC_PHRASE_TIMEOUT,
       max_phrases=config.MIC_MAX_PHRASES,
       transcription_engine=config.SELECTED_TRANSCRIPTION_ENGINE,
       root=config.PATH_LOCAL,
       whisper_weight_type=config.WHISPER_WEIGHT_TYPE,
       device=config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE["device"],
       device_index=config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE["device_index"],
       compute_type=config.SELECTED_TRANSCRIPTION_COMPUTE_TYPE,
   )
   ```
6. **文字起こしスレッドの起動:**
   ```python
   def sendMicTranscript():
       # キューから音声データを取得
       # AudioTranscriber で文字起こし
       # fnc() で結果を送信
   
   def endMicTranscript():
       # クリーンアップ処理
   
   self.mic_print_transcript = threadFnc(sendMicTranscript, end_fnc=endMicTranscript)
   self.mic_print_transcript.start()
   ```
7. **ミュート状態の同期:**
   ```python
   self.changeMicTranscriptStatus()
   ```

##### `resumeMicTranscript() -> None`

**責務:** 一時停止したマイク音声認識の再開

**処理:**
1. 音声キューをクリア
2. レコーダーを再開: `self.mic_audio_recorder.resume()`

##### `pauseMicTranscript() -> None`

**責務:** マイク音声認識の一時停止

**処理:** `self.mic_audio_recorder.pause()`

##### `changeMicTranscriptStatus() -> None`

**責務:** VRChat のマイクミュート状態に応じて音声認識を制御

**処理:**
```python
if config.VRC_MIC_MUTE_SYNC is True:
    match self.mic_mute_status:
        case True:
            self.pauseMicTranscript()
        case False:
            self.resumeMicTranscript()
        case None:
            self.resumeMicTranscript()  # 不明な場合は一時停止しない
else:
    self.resumeMicTranscript()
```

##### `stopMicTranscript() -> None`

**責務:** マイク音声認識の停止とリソース解放

**処理:**
1. 文字起こしスレッドの停止
2. レコーダーの再開（一時停止中の場合）と停止
3. インスタンスの破棄

**VRAMエラー検出:**

##### `detectVRAMError(error: Exception) -> Tuple[bool, Optional[str]]`

**責務:** VRAM不足エラーの検出

**処理:**
```python
error_str = str(error)
if isinstance(error, ValueError) and len(error.args) > 0 and error.args[0] == "VRAM_OUT_OF_MEMORY":
    return True, error_str
if "CUDA out of memory" in error_str or "CUBLAS_STATUS_ALLOC_FAILED" in error_str:
    return True, error_str
return False, None
```

**使用箇所:**
- 翻訳実行時
- 音声認識開始時

#### スピーカー音声認識

以下のメソッドはマイク音声認識と同様の構造:
- `startSpeakerTranscript(fnc)`
- `stopSpeakerTranscript()`

**相違点:**
- `speaker=True` で AudioTranscriber を初期化
- `SelectedSpeakerEnergyAndAudioRecorder` を使用

#### エネルギーレベル監視

##### `startCheckMicEnergy(fnc: Optional[Callable[[float], None]] = None) -> None`

**責務:** マイクの音量レベル監視の開始

**処理:**
1. コールバック関数を設定: `self.check_mic_energy_fnc = fnc`
2. マイクデバイスを取得
3. エネルギーレコーダーを初期化:
   ```python
   mic_energy_queue = Queue()
   self.mic_energy_recorder = SelectedMicEnergyRecorder(mic_device)
   self.mic_energy_recorder.recordIntoQueue(mic_energy_queue)
   ```
4. エネルギー送信スレッドを起動:
   ```python
   def sendMicEnergy():
       if not mic_energy_queue.empty():
           energy = mic_energy_queue.get()
           self.check_mic_energy_fnc(energy)
       sleep(0.01)
   
   self.mic_energy_plot_progressbar = threadFnc(sendMicEnergy)
   self.mic_energy_plot_progressbar.start()
   ```

##### `stopCheckMicEnergy() -> None`
エネルギー監視の停止とリソース解放。

**対応するスピーカー用メソッド:**
- `startCheckSpeakerEnergy(fnc)`
- `stopCheckSpeakerEnergy()`

---

### 6. オーバーレイ機能

#### 画像生成

##### `createOverlayImageSmallLog(message, your_language, translation, target_language) -> object`

**責務:** 小さなログウィンドウ用の画像生成

**パラメータ:**
- `message`: 元のメッセージ（オプション）
- `your_language`: 元の言語（オプション）
- `translation`: 翻訳結果のリスト
- `target_language`: 翻訳先言語の辞書（オプション）

**処理:**
```python
target_language_list = []
if isinstance(target_language, dict):
    target_language_list = list(target_language.values())
return self.overlay_image.createOverlayImageSmallLog(
    message, your_language, translation, target_language_list
)
```

##### `createOverlayImageSmallMessage(message: str) -> object`

**責務:** 小さなメッセージウィンドウ用の画像生成（単一言語）

**処理:**
```python
ui_language = config.UI_LANGUAGE
convert_languages = {
    "en": "Default",
    "jp": "Japanese",
    "ko": "Korean",
    "zh-Hans": "Chinese Simplified",
    "zh-Hant": "Chinese Traditional",
}
language = convert_languages.get(ui_language, "Default")
return self.overlay_image.createOverlayImageSmallLog(message, language)
```

##### `createOverlayImageLargeLog(message_type, message, your_language, translation, target_language=None) -> object`

**責務:** 大きなログウィンドウ用の画像生成

**パラメータ:**
- `message_type`: "send" または "received"

**処理:** `createOverlayImageSmallLog()` と同様

##### `createOverlayImageLargeMessage(message: str) -> object`

**責務:** 大きなメッセージウィンドウ用の画像生成

**特殊処理:**
```python
overlay_image = OverlayImage(config.PATH_LOCAL)
for _ in range(2):
    # 2回繰り返して画像を生成（理由は不明、バグ修正のため？）
    overlay_image.createOverlayImageLargeLog("send", message, language)
return overlay_image.createOverlayImageLargeLog("send", message, language)
```

#### 表示制御

##### `clearOverlayImageSmallLog() -> None`
小さなログウィンドウをクリア。

##### `updateOverlaySmallLog(img: object) -> None`
小さなログウィンドウの画像を更新。

##### `updateOverlaySmallLogSettings() -> None`

**責務:** 小さなログウィンドウの設定更新

**処理:** 設定の変更を検出し、オーバーレイに反映:
```python
size = "small"
if (self.overlay.settings[size]["x_pos"] != config.OVERLAY_SMALL_LOG_SETTINGS["x_pos"] or
    # ... 他の設定項目 ...):
    self.overlay.updateSettings(config.OVERLAY_SMALL_LOG_SETTINGS, size)
```

**設定項目:**
- 位置（x_pos, y_pos, z_pos）
- 回転（x_rotation, y_rotation, z_rotation）
- トラッカー（tracker）
- 表示時間（display_duration）
- フェードアウト時間（fadeout_duration）
- 透明度（opacity）
- UIスケーリング（ui_scaling）

##### `clearOverlayImageLargeLog() -> None`
大きなログウィンドウをクリア。

##### `updateOverlayLargeLog(img: object) -> None`
大きなログウィンドウの画像を更新。

##### `updateOverlayLargeLogSettings() -> None`
大きなログウィンドウの設定更新（`updateOverlaySmallLogSettings()` と同様）。

#### オーバーレイシステム制御

##### `startOverlay() -> None`
オーバーレイシステムを起動（OpenVR の初期化）。

##### `shutdownOverlay() -> None`
オーバーレイシステムを終了（リソース解放）。

---

### 7. OSC 通信機能

#### 設定

##### `setOscIpAddress(ip_address: str) -> None`
VRChat への送信先 IP アドレスを設定。

##### `setOscPort(port: int) -> None`
OSC ポート番号を設定。

#### メッセージ送信

##### `oscStartSendTyping() -> None`
タイピング中の通知を送信（VRChat のチャットボックスにインジケーターが表示される）。

##### `oscStopSendTyping() -> None`
タイピング終了の通知を送信。

##### `oscSendMessage(message: str) -> None`

**責務:** VRChat へメッセージを送信

**パラメータ:**
- `message`: 送信するテキスト

**処理:**
```python
self.osc_handler.sendMessage(
    message=message,
    notification=config.NOTIFICATION_VRC_SFX
)
```

#### OSC 受信

##### `setMuteSelfStatus() -> None`
VRChat の現在のマイクミュート状態を取得。

##### `startReceiveOSC() -> None`

**責務:** OSC パラメータの受信開始

**処理:**
```python
def changeHandlerMute(address, osc_arguments):
    if config.ENABLE_TRANSCRIPTION_SEND is True:
        self.mic_mute_status = osc_arguments[0]
        self.changeMicTranscriptStatus()

dict_filter_and_target = {
    self.osc_handler.osc_parameter_muteself: changeHandlerMute,
}
self.osc_handler.setDictFilterAndTarget(dict_filter_and_target)
self.osc_handler.receiveOscParameters()
```

**監視パラメータ:**
- `/avatar/parameters/MuteSelf`: マイクミュート状態

##### `stopReceiveOSC() -> None`
OSC 受信を停止。

##### `getIsOscQueryEnabled() -> bool`
OSC Query 機能が有効かチェック。

---

### 8. 音訳機能

#### 音訳システム制御

##### `startTransliteration() -> None`
音訳システムを起動（`Transliterator` インスタンスを生成）。

##### `stopTransliteration() -> None`
音訳システムを停止（インスタンスを破棄）。

#### 音訳実行

##### `convertMessageToTransliteration(message, hiragana=True, romaji=True) -> list`

**責務:** メッセージをひらがな・ローマ字に変換

**パラメータ:**
- `message`: 変換するテキスト
- `hiragana`: ひらがなを含める
- `romaji`: ローマ字を含める

**処理:**
```python
if hiragana is False and romaji is False:
    return []

keys_to_keep = {"orig"}
if hiragana:
    keys_to_keep.add("hira")
if romaji:
    keys_to_keep.add("hepburn")

if self.transliterator is None:
    self.startTransliteration()

data_list = self.transliterator.analyze(message, use_macron=False)
filtered_list = [
    {key: value for key, value in item.items() if key in keys_to_keep}
    for item in data_list
]
return filtered_list
```

**戻り値の例:**
```python
[
    {"orig": "こんにちは", "hira": "こんにちは", "hepburn": "konnichiwa"},
    {"orig": "世界", "hira": "せかい", "hepburn": "sekai"}
]
```

---

### 9. キーワードフィルター

#### フィルター管理

##### `resetKeywordProcessor() -> None`
キーワードプロセッサをリセット（すべてのキーワードを削除）。

##### `addKeywords() -> None`
禁止ワードをキーワードプロセッサに追加。

**処理:**
```python
for f in config.MIC_WORD_FILTER:
    self.keyword_processor.add_keyword(f)
```

#### フィルタリング

##### `checkKeywords(message: str) -> bool`
メッセージに禁止ワードが含まれているかチェック。

**戻り値:** 禁止ワードが含まれている場合 True

**実装:**
```python
return len(self.keyword_processor.extract_keywords(message)) != 0
```

---

### 10. 重複検出

##### `detectRepeatSendMessage(message: str) -> bool`

**責務:** 送信メッセージの重複検出

**処理:**
```python
repeat_flag = False
if self.previous_send_message == message:
    repeat_flag = True
self.previous_send_message = message
return repeat_flag
```

##### `detectRepeatReceiveMessage(message: str) -> bool`
受信メッセージの重複検出（`detectRepeatSendMessage()` と同様）。

---

### 11. デバイス管理

#### マイクデバイス

##### `getListMicHost() -> list`

**責務:** マイクホストのリスト取得

**戻り値:** ["MME", "WASAPI", ...] 等

**処理:**
```python
try:
    dm = device_manager.getMicDevices()
    result = [host for host in dm.keys()]
except Exception:
    errorLogging()
    result = []
return result
```

##### `getMicDefaultDevice() -> str`
選択されたホストのデフォルトマイクデバイス名を取得。

##### `getListMicDevice() -> list`
選択されたホストのマイクデバイス一覧を取得。

#### スピーカーデバイス

##### `getListSpeakerDevice() -> list`
スピーカーデバイス一覧を取得。

**処理:**
```python
try:
    sd = device_manager.getSpeakerDevices()
    result = [device["name"] for device in sd]
except Exception:
    errorLogging()
    result = ["NoDevice"]
return result
```

---

### 12. 言語管理

##### `getListLanguageAndCountry() -> list`

**責務:** 音声認識と翻訳の両方をサポートする言語・国のリスト取得

**処理:**
1. `transcription_lang` から音声認識サポート言語を取得
2. `translation_lang` から翻訳サポート言語を取得
3. 両方でサポートされている言語を抽出
4. 各言語の国バリエーションを列挙

**戻り値の例:**
```python
[
    {"language": "en", "country": "US"},
    {"language": "en", "country": "UK"},
    {"language": "ja", "country": "JP"},
    # ...
]
```

##### `findTranslationEngines(source_lang, target_lang, engines_status) -> list`

**責務:** 指定された言語ペアをサポートする翻訳エンジンの検索

**パラメータ:**
- `source_lang`: 元言語の辞書（複数の言語が有効化されている可能性）
- `target_lang`: 翻訳先言語の辞書
- `engines_status`: 各エンジンの有効/無効状態

**処理:**
```python
selectable_engines = [key for key, value in engines_status.items() if value is True]
compatible_engines = []
for engine in list(translation_lang.keys()):
    languages = translation_lang.get(engine, {}).get("source", {})
    source_langs = [e["language"] for e in list(source_lang.values()) if e["enable"] is True]
    target_langs = [e["language"] for e in list(target_lang.values()) if e["enable"] is True]
    language_list = list(languages.keys())

    if all(e in language_list for e in source_langs) and all(e in language_list for e in target_langs):
        if engine in selectable_engines:
            compatible_engines.append(engine)

return compatible_engines
```

---

### 13. ロギング

##### `startLogger() -> None`

**責務:** ファイルロギングの開始

**処理:**
```python
os_makedirs(config.PATH_LOGS, exist_ok=True)
file_name = os_path.join(config.PATH_LOGS, f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")
self.logger = setupLogger("log", file_name)
self.logger.disabled = False
```

**ログファイル名の例:** `2023-10-13_15-30-45.log`

##### `stopLogger() -> None`
ファイルロギングの停止。

---

### 14. ソフトウェアアップデート

##### `checkSoftwareUpdated() -> dict`

**責務:** 最新バージョンの確認

**処理:**
```python
update_flag = False
version = ""
try:
    # GitHub API 等から最新バージョン情報を取得
    # packaging.version.parse でバージョン比較
except Exception:
    errorLogging()
return {
    "is_update_available": update_flag,
    "new_version": version,
}
```

##### `updateSoftware() -> None`

**責務:** 通常版のアップデート実行

**処理:**
1. アップデーターをダウンロード（最大5回リトライ）
2. `Popen()` でアップデーターを起動
3. 現在のプロセスを終了

##### `updateCudaSoftware() -> None`
CUDA版のアップデート実行（`--cuda` オプション付きでアップデーターを起動）。

---

### 15. Watchdog 機能

##### `startWatchdog() -> None`

**責務:** Watchdog 監視スレッドの起動

**処理:**
```python
self.th_watchdog = threadFnc(self.watchdog.start)
self.th_watchdog.daemon = True
self.th_watchdog.start()
```

##### `feedWatchdog() -> None`
Watchdog にハートビート信号を送信（タイムアウトをリセット）。

##### `setWatchdogCallback(callback: Callable) -> None`
Watchdog タイムアウト時のコールバック関数を設定。

##### `stopWatchdog() -> None`
Watchdog を停止し、スレッドの終了を待機。

---

### 16. WebSocket サーバー

#### サーバー制御

##### `startWebSocketServer(host: str, port: int) -> None`

**責務:** WebSocket サーバーの起動

**処理:**
1. 既に起動中なら何もしない
2. `websocket_server_loop = True` に設定
3. 別スレッドで asyncio イベントループを実行:
   ```python
   async def WebSocketServerMain():
       self.websocket_server = WebSocketServer(host, port)
       self.websocket_server_alive = True
       await self.websocket_server.start()
       # ループ終了まで待機
       self.websocket_server_alive = False
   
   self.th_websocket_server = Thread(target=lambda: asyncio.run(WebSocketServerMain()))
   self.th_websocket_server.daemon = True
   self.th_websocket_server.start()
   ```

##### `stopWebSocketServer() -> None`

**責務:** WebSocket サーバーの停止

**処理:**
1. `websocket_server_loop = False` に設定
2. サーバーの停止を要求
3. スレッドの終了を待機（タイムアウト付き）

**エラーハンドリング:**
```python
try:
    # サーバー停止処理
except Exception:
    errorLogging()
finally:
    self.th_websocket_server = None
    self.websocket_server = None
    self.websocket_server_alive = False
```

##### `checkWebSocketServerAlive() -> bool`
WebSocket サーバーの稼働状態を確認。

#### メッセージ送信

##### `websocketSendMessage(message_dict: dict) -> bool`

**責務:** すべての接続クライアントにメッセージをブロードキャスト

**パラメータ:**
- `message_dict`: 送信する辞書（JSON にシリアライズされる）

**処理:**
```python
if not self.websocket_server_alive or not self.websocket_server:
    return False
try:
    self.websocket_server.broadcast(message_dict)
    return True
except Exception:
    errorLogging()
    return False
```

---

## 依存関係

### 外部ライブラリ

```python
from subprocess import Popen
from os import makedirs as os_makedirs
from os import path as os_path
from datetime import datetime
from time import sleep
from queue import Queue
from threading import Thread
from requests import get as requests_get
from typing import Callable, Optional, cast
from packaging.version import parse
from flashtext import KeywordProcessor
```

### 内部モジュール

```python
from device_manager import device_manager
from config import config
from models.translation.translation_translator import Translator
from models.osc.osc import OSCHandler
from models.transcription.transcription_recorder import SelectedMicEnergyAndAudioRecorder, SelectedSpeakerEnergyAndAudioRecorder
from models.transcription.transcription_recorder import SelectedMicEnergyRecorder, SelectedSpeakerEnergyRecorder
from models.transcription.transcription_transcriber import AudioTranscriber
from models.translation.translation_languages import translation_lang
from models.transcription.transcription_languages import transcription_lang
from models.translation.translation_utils import checkCTranslate2Weight, downloadCTranslate2Weight, downloadCTranslate2Tokenizer
from models.transcription.transcription_whisper import checkWhisperWeight, downloadWhisperWeight
from models.transliteration.transliteration_transliterator import Transliterator
from models.overlay.overlay import Overlay
from models.overlay.overlay_image import OverlayImage
from models.watchdog.watchdog import Watchdog
from models.websocket.websocket_server import WebSocketServer
from utils import errorLogging, setupLogger
```

---

## スレッド構成

### メインスレッド
- アプリケーションのメインループ（`mainloop.py` が管理）

### Model 管理のスレッド

#### 音声認識スレッド
- `mic_print_transcript`: マイク音声認識結果の処理
- `speaker_print_transcript`: スピーカー音声認識結果の処理

#### エネルギー監視スレッド
- `mic_energy_plot_progressbar`: マイクの音量レベル監視
- `speaker_energy_plot_progressbar`: スピーカーの音量レベル監視

#### その他のスレッド
- `th_watchdog`: Watchdog 監視
- `th_websocket_server`: WebSocket サーバー（asyncio イベントループ）

### サブシステム管理のスレッド
- `device_manager.th_monitoring`: デバイス変更監視
- `mic_audio_recorder.th_record`: マイク音声録音
- `speaker_audio_recorder.th_record`: スピーカー音声録音
- `osc_handler.th_receive`: OSC パラメータ受信

---

## エラーハンドリング

### VRAM不足エラー

**検出:**
```python
is_vram_error, error_message = self.detectVRAMError(e)
```

**対応:**
1. エラーを `ValueError("VRAM_OUT_OF_MEMORY")` として送出
2. Controller 側でキャッチして機能を無効化
3. ユーザーに通知

### デバイスアクセスエラー

**検出:**
- デバイスが見つからない場合: `NoDevice`
- アクセス失敗時: コールバックに `False` を渡す

**対応:**
1. エラーをログに記録
2. Controller に通知
3. 処理を継続（他の機能に影響なし）

### ネットワークエラー

**検出:**
- 翻訳API呼び出し失敗
- モデルウェイトダウンロード失敗

**対応:**
1. リトライロジック（翻訳の場合）
2. フォールバック（CTranslate2 への切り替え）
3. エラー通知

---

## パフォーマンス最適化

### 1. 遅延初期化

重い初期化処理を `init()` に分離し、必要になるまで実行しない。

**利点:**
- アプリケーションの起動時間を短縮
- 未使用の機能のリソースを消費しない

### 2. シングルトンパターン

Model クラスはアプリケーション全体で1つのインスタンスのみ存在。

**利点:**
- メモリ使用量の削減
- 状態の一貫性

### 3. スレッドによる並列処理

音声認識、エネルギー監視、WebSocket サーバーなど、ブロッキング処理を別スレッドで実行。

**利点:**
- UI のレスポンス性向上
- 複数機能の同時実行

---

## テストシナリオ

### 1. 初期化テスト

**ケース:**
- 初回初期化
- 既に初期化済みの場合
- 初期化失敗時

**確認項目:**
- `_inited` フラグが正しく設定されているか
- すべてのサブシステムが初期化されているか
- エラーが適切にログされているか

### 2. 音声認識テスト

**ケース:**
- デバイスがない場合
- 音声認識開始・停止・一時停止・再開
- VRAMエラーの発生

**確認項目:**
- コールバックが正しく呼び出されているか
- スレッドが適切に管理されているか
- エラーが検出されているか

### 3. 翻訳テスト

**ケース:**
- 単一言語翻訳
- 複数言語翻訳
- 翻訳エンジンの切り替え
- API エラー

**確認項目:**
- 翻訳結果が正しいか
- エラー時のフォールバックが動作するか

### 4. オーバーレイテスト

**ケース:**
- 画像生成
- 設定更新
- オーバーレイの起動・停止

**確認項目:**
- 画像が正しく生成されるか
- 設定変更が反映されるか

---

## 制限事項

### 1. シングルトンの制約

**問題:** テストやマルチインスタンスが困難

**影響:**
- ユニットテストでモックが難しい
- 複数の VRChat インスタンスへの対応が不可能

### 2. グローバル状態依存

**問題:** `config` モジュールへの強い依存

**影響:**
- テスタビリティの低下
- 設定変更の追跡が困難

### 3. エラーハンドリングの不完全性

**問題:** 一部のエラーは握りつぶされる

**影響:**
- デバッグが困難
- ユーザーへの適切なエラー通知が不足

### 4. スレッドの管理複雑性

**問題:** 多数のスレッドとその状態管理

**影響:**
- デッドロックのリスク
- リソースリークの可能性

---

## 今後の改善案

### 1. 依存性注入（DI）の導入

```python
class Model:
    def __init__(self, config, device_manager, translator, ...):
        self.config = config
        self.device_manager = device_manager
        self.translator = translator
        # ...
```

**利点:**
- テスタビリティの向上
- モジュール間の疎結合

### 2. 非同期化（asyncio）

```python
async def startMicTranscript(self, callback):
    async for result in self.mic_transcriber.transcribe():
        await callback(result)
```

**利点:**
- スレッド管理の簡素化
- パフォーマンスの向上

### 3. イベント駆動アーキテクチャ

```python
class Model:
    def __init__(self):
        self.event_bus = EventBus()
    
    def on_transcription_result(self, result):
        self.event_bus.emit("transcription_result", result)
```

**利点:**
- モジュール間の疎結合
- 拡張性の向上

### 4. エラーハンドリングの統一

```python
class ModelError(Exception):
    pass

class VRAMError(ModelError):
    pass

class DeviceError(ModelError):
    pass
```

**利点:**
- エラーの分類と処理の統一
- エラー情報の追跡

---

## 関連ファイル

- **controller.py** - ビジネスロジック制御レイヤー
- **config.py** - 設定管理
- **device_manager.py** - デバイス監視・自動選択
- **mainloop.py** - 通信レイヤー
- **utils.py** - ログとユーティリティ関数
- **models/** - サブシステムの実装

---

## まとめ

`model.py` は VRCT のすべてのサブシステムへの統一されたファサードインターフェースを提供し、音声認識、翻訳、オーバーレイ、OSC通信、WebSocket通信など、複雑な機能を簡潔なAPIで公開する。シングルトンパターンと遅延初期化により、リソースの効率的な利用を実現している。スレッドを活用した並列処理により、複数の機能を同時に実行しながらUIのレスポンス性を維持している。VRAMエラーやデバイスエラーに対する適切なハンドリングにより、ユーザーエクスペリエンスを向上させている。
