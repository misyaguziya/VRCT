# controller.py 設計書

## 概要

`controller.py` は VRCT アプリケーションのビジネスロジック層であり、フロントエンド（UI）とバックエンド（Model）の間の制御フローを担当する。音声認識、翻訳、OSC通信、オーバーレイ表示など、VRCT の全機能の調整役として動作し、各種設定の取得・更新、デバイス管理、エラーハンドリングを提供する。

## アーキテクチャ上の位置づけ

```
┌─────────────┐
│ Frontend    │ (Tauri/React)
│ (UI Layer)  │
└──────┬──────┘
       │ JSON-RPC (stdin/stdout)
┌──────▼──────┐
│ mainloop.py │ (Communication Layer)
└──────┬──────┘
       │ Function Calls
┌──────▼──────┐
│controller.py│ ◄── このファイル
└──────┬──────┘
       │ Facade Pattern
┌──────▼──────┐
│  model.py   │ (Business Logic Facade)
└──────┬──────┘
       │
┌──────▼──────┐
│ Subsystems  │ (transcription, translation, osc, overlay, etc.)
└─────────────┘
```

## 主要コンポーネント

### 1. Controllerクラス

#### コンストラクタ `__init__()`

**責務:** Controller インスタンスの初期化と依存関係のセットアップ

**初期化処理:**
1. **マッピング辞書の初期化:**
   - `init_mapping`: 初期化時に実行するエンドポイント群
   - `run_mapping`: フロントエンドへの通知用エンドポイント
2. **コールバック関数の設定:**
   - `run`: フロントエンドへの通知を送信する関数（デフォルトは no-op）
3. **Model の初期化:**
   - `model.init()` を呼び出し、サブシステムを準備
   - 失敗時は `errorLogging()` でログ記録して継続
4. **デバイスアクセス状態:**
   - `device_access_status`: デバイスへの排他アクセス制御用フラグ

**型ヒント:**
```python
self.init_mapping: dict
self.run_mapping: dict
self.run: Callable[[int, str, Any], None]
self.device_access_status: bool
```

#### セットアップメソッド

##### `setInitMapping(init_mapping: dict) -> None`
初期化時に実行するエンドポイントマッピングを設定。`mainloop.py` から呼び出される。

##### `setRunMapping(run_mapping: dict) -> None`
フロントエンド通知用のエンドポイントマッピングを設定。

##### `setRun(run: Callable[[int, str, Any], None]) -> None`
フロントエンドへの通知関数を設定。`mainloop.py` の `printResponse()` ラッパーが渡される。

#### ヘルパーメソッド

##### `_is_overlay_available() -> bool`
オーバーレイ機能が利用可能かを安全にチェック。Model が未初期化の場合の `AttributeError` を回避。

**実装:**
```python
try:
    overlay = getattr(model, "overlay", None)
    return overlay is not None and getattr(overlay, "initialized", False)
except Exception:
    errorLogging()
    return False
```

---

### 2. 通知メソッド（Response Functions）

フロントエンドに状態変化を通知するメソッド群。すべて `self.run()` を介して JSON を stdout に送信。

#### ネットワーク関連

##### `connectedNetwork() -> None`
ネットワーク接続を検出したことを通知。

##### `disconnectedNetwork() -> None`
ネットワーク切断を検出したことを通知。

#### AI モデル関連

##### `enableAiModels() -> None`
AI モデル（CTranslate2/Whisper）が利用可能であることを通知。

##### `disableAiModels() -> None`
AI モデルが利用不可（ダウンロード失敗等）であることを通知。

#### デバイス管理関連

##### `updateMicHostList() -> None`
マイクホスト一覧（MME/WASAPI等）を更新。

##### `updateMicDeviceList() -> None`
マイクデバイス一覧を更新。

##### `updateSpeakerDeviceList() -> None`
スピーカーデバイス一覧を更新。

##### `updateSelectedMicDevice(host: str, device: str) -> None`
選択されたマイクデバイスを通知。自動デバイス選択時に使用。

##### `updateSelectedSpeakerDevice(device: str) -> None`
選択されたスピーカーデバイスを通知。

#### エネルギーレベル通知

##### `progressBarMicEnergy(energy: Union[bool, int]) -> None`
マイクの音量レベルを通知。`False` の場合はデバイスエラーを送信。

##### `progressBarSpeakerEnergy(energy: Union[bool, int]) -> None`
スピーカーの音量レベルを通知。

#### 設定同期

##### `updateConfigSettings() -> None`
初期化完了時に全設定値をフロントエンドに送信。`init_mapping` の全エンドポイントを実行。

---

### 3. デバイス制御メソッド

#### 再起動系

##### `restartAccessMicDevices() -> None`
マイクアクセスを再起動。以下の条件で各機能を開始:
- `config.ENABLE_TRANSCRIPTION_SEND` が True: 音声認識開始
- `config.ENABLE_CHECK_ENERGY_SEND` が True: 音量監視開始

##### `restartAccessSpeakerDevices() -> None`
スピーカーアクセスを再起動。

#### 停止系

##### `stopAccessMicDevices() -> None`
マイク関連機能を停止。

##### `stopAccessSpeakerDevices() -> None`
スピーカー関連機能を停止。

**使用場面:**
- デバイス変更時
- 自動デバイス選択によるデバイス切り替え時
- アプリケーション終了時

---

### 4. メッセージ処理メソッド

#### `micMessage(result: dict) -> None`

**責務:** マイク音声認識結果の処理と配信

**処理フロー:**
1. **結果の検証:**
   - `result["text"]` と `result["language"]` を取得
   - `False` の場合はデバイスエラーを通知して終了
2. **フィルタリング:**
   - `model.checkKeywords()`: 禁止ワードチェック
   - `model.detectRepeatSendMessage()`: 重複メッセージチェック
3. **翻訳処理:**
   - `config.ENABLE_TRANSLATION` が True の場合:
     - `model.getInputTranslate()` で翻訳実行
     - 翻訳エンジンエラー時は CTranslate2 に切り替え
     - VRAM不足エラー時は翻訳機能を無効化
4. **音訳処理:**
   - `config.CONVERT_MESSAGE_TO_HIRAGANA/ROMAJI` が True の場合:
     - `model.convertMessageToTransliteration()` で変換
5. **配信処理:**
   - **VRChat OSC:** `config.SEND_MESSAGE_TO_VRC` が True の場合
     - `messageFormatter()` でフォーマット
     - `model.oscSendMessage()` で送信
   - **UI通知:** `self.run()` で transcription_mic エンドポイントに通知
   - **オーバーレイ:** `config.OVERLAY_LARGE_LOG` が True の場合
     - `model.createOverlayImageLargeLog()` で画像生成
     - `model.updateOverlayLargeLog()` で表示更新
   - **WebSocket:** サーバーが起動中の場合
     - `model.websocketSendMessage()` でブロードキャスト
   - **ログファイル:** `config.LOGGER_FEATURE` が True の場合

**VRAM エラーハンドリング:**
```python
try:
    translation, success = model.getInputTranslate(message, source_language=language)
except Exception as e:
    is_vram_error, error_message = model.detectVRAMError(e)
    if is_vram_error:
        # 翻訳機能を無効化
        self.setDisableTranslation()
        self.run(400, self.run_mapping["error_translation_mic_vram_overflow"], {...})
        return
```

#### `speakerMessage(result: dict) -> None`

**責務:** スピーカー音声認識結果の処理と配信

**処理フロー:** `micMessage()` と同様だが、以下の違いがある:
- **オーバーレイ:**
  - Small Log: 受信メッセージ用の小さなログウィンドウ
  - Large Log: 送受信両方を表示するログウィンドウ
- **OSC送信:** `config.SEND_RECEIVED_MESSAGE_TO_VRC` の設定に依存
- **翻訳:** `model.getOutputTranslate()` を使用（受信メッセージ用）

#### `chatMessage(data: dict) -> dict`

**責務:** UI のチャットボックスからのメッセージ処理

**パラメータ:**
- `data["id"]`: メッセージ ID（UI でのレスポンスマッピング用）
- `data["message"]`: 送信メッセージ

**特殊処理:**
- **除外ワード処理:**
  - `config.USE_EXCLUDE_WORDS` が True の場合
  - `replaceExclamationsWithRandom()`: `![word]` を一時的なトークンに置換
  - 翻訳後に `restoreText()` で復元
  - 最終メッセージから `![...]` を削除
- **同期レスポンス:** 
  - 他のメッセージ処理と異なり、結果を `dict` で返却
  - UI が翻訳結果を待機する必要があるため

**レスポンス形式:**
```python
{
    "status": 200,
    "result": {
        "id": "msg-123",
        "original": {
            "message": "Hello",
            "transliteration": ["he", "ro"]
        },
        "translations": [
            {
                "message": "こんにちは",
                "transliteration": ["ko", "n", "ni", "chi", "wa"]
            }
        ]
    }
}
```

---

### 5. メッセージフォーマット

#### `messageFormatter(format_type: str, translation: list, message: str) -> str`

**責務:** OSC 送信用メッセージの整形

**パラメータ:**
- `format_type`: "SEND" または "RECEIVED"
- `translation`: 翻訳結果のリスト
- `message`: 元のメッセージ

**処理ロジック:**
1. フォーマット設定を取得:
   - `config.SEND_MESSAGE_FORMAT_PARTS` または `config.RECEIVED_MESSAGE_FORMAT_PARTS`
2. 各部分を構築:
   - `message_part`: prefix + message + suffix
   - `translation_part`: prefix + separator.join(translation) + suffix
3. 組み合わせ:
   - 両方存在: `translation_first` の設定に応じて順序決定
   - 翻訳のみ: translation_part のみ
   - メッセージのみ: message_part のみ

**設定例:**
```python
config.SEND_MESSAGE_FORMAT_PARTS = {
    "message": {"prefix": "[", "suffix": "] "},
    "translation": {"prefix": "", "suffix": "", "separator": " / "},
    "translation_first": False,
    "separator": ""
}
# 出力例: [Hello] こんにちは / 你好
```

---

### 6. 除外ワード処理

#### `replaceExclamationsWithRandom(text: str) -> Tuple[str, dict]`

**責務:** 翻訳対象外の単語を保護

**処理:**
1. `![word]` パターンを検出
2. 各マッチを `$<hex番号>` に置換（4096から連番）
3. 置換マップを辞書で返却

**用途:** 固有名詞や翻訳不要な単語を保護

#### `restoreText(escaped_text: str, escape_dict: dict) -> str`

**責務:** 翻訳後のテキストに元の単語を復元

**処理:** 正規表現で `$<hex番号>` を検出し、元の単語に置換（大文字小文字を無視）

#### `removeExclamations(text: str) -> str`

**責務:** 最終メッセージから `![...]` マーカーを削除

**処理:** `![word]` を `word` に置換

---

### 7. 設定取得・更新メソッド（GET/SET）

Controller には約200個の設定項目に対する getter/setter が定義されている。以下、代表的なパターンを示す。

#### パターン1: 単純な設定値

```python
@staticmethod
def getTransparency(*args, **kwargs) -> dict:
    return {"status": 200, "result": config.TRANSPARENCY}

@staticmethod
def setTransparency(data, *args, **kwargs) -> dict:
    config.TRANSPARENCY = int(data)
    return {"status": 200, "result": config.TRANSPARENCY}
```

#### パターン2: 有効/無効の切り替え

```python
@staticmethod
def getOverlaySmallLog(*args, **kwargs) -> dict:
    return {"status": 200, "result": config.OVERLAY_SMALL_LOG}

@staticmethod
def setEnableOverlaySmallLog(*args, **kwargs) -> dict:
    if config.OVERLAY_SMALL_LOG is False:
        if config.OVERLAY_LARGE_LOG is False:
            model.startOverlay()  # 副作用: オーバーレイシステムを起動
        config.OVERLAY_SMALL_LOG = True
    return {"status": 200, "result": config.OVERLAY_SMALL_LOG}

@staticmethod
def setDisableOverlaySmallLog(*args, **kwargs) -> dict:
    if config.OVERLAY_SMALL_LOG is True:
        model.clearOverlayImageSmallLog()
        if config.OVERLAY_LARGE_LOG is False:
            model.shutdownOverlay()  # 副作用: オーバーレイシステムを停止
        config.OVERLAY_SMALL_LOG = False
    return {"status": 200, "result": config.OVERLAY_SMALL_LOG}
```

#### パターン3: バリデーション付き設定

```python
@staticmethod
def setMicThreshold(data, *args, **kwargs) -> dict:
    try:
        data = int(data)
        if 0 <= data <= config.MAX_MIC_THRESHOLD:
            config.MIC_THRESHOLD = data
            status = 200
        else:
            raise ValueError()
    except Exception:
        response = {
            "status": 400,
            "result": {
                "message": "Mic energy threshold value is out of range",
                "data": config.MIC_THRESHOLD
            }
        }
    else:
        response = {"status": status, "result": config.MIC_THRESHOLD}
    return response
```

#### パターン4: 依存関係のある設定

```python
def setSelectedTranslationComputeDevice(self, device: str, *args, **kwargs) -> dict:
    config.SELECTED_TRANSLATION_COMPUTE_DEVICE = device
    config.SELECTED_TRANSLATION_COMPUTE_TYPE = "auto"
    # 依存する設定を自動更新
    self.run(200, self.run_mapping["selected_translation_compute_type"], 
             config.SELECTED_TRANSLATION_COMPUTE_TYPE)
    # モデルの再読み込みフラグを設定
    model.setChangedTranslatorParameters(True)
    return {"status": 200, "result": config.SELECTED_TRANSLATION_COMPUTE_DEVICE}
```

---

### 8. 翻訳機能制御

#### `setEnableTranslation(*args, **kwargs) -> dict`

**責務:** 翻訳機能の有効化とモデルのロード

**処理フロー:**
1. 既に有効な場合は何もしない
2. モデル未ロードまたはパラメータ変更時:
   - `model.changeTranslatorCTranslate2Model()` でモデルをロード
   - VRAM不足エラーの場合:
     - デフォルト設定に戻す
     - エラー通知を送信
     - 翻訳を無効化
3. `config.ENABLE_TRANSLATION = True` に設定

**エラーハンドリング:**
```python
try:
    model.changeTranslatorCTranslate2Model()
except Exception as e:
    is_vram_error, error_message = model.detectVRAMError(e)
    if is_vram_error:
        self.run(400, self.run_mapping["error_translation_enable_vram_overflow"], {...})
        self.setDisableTranslation()
```

#### `setDisableTranslation(*args, **kwargs) -> dict`

**責務:** 翻訳機能の無効化（メモリ解放）

#### `changeToCTranslate2Process() -> None`

**責務:** 外部翻訳APIエラー時に CTranslate2 へ切り替え

**処理:**
1. 現在の翻訳エンジンを無効化
2. CTranslate2 に切り替え
3. フロントエンドに通知

---

### 9. 音声認識制御

#### スレッド管理メソッド

##### `startTranscriptionSendMessage() -> None`
マイク音声認識を開始。デバイスアクセスの排他制御を行う。

**排他制御:**
```python
while self.device_access_status is False:
    sleep(1)  # 他の処理がデバイスを使用中なら待機
self.device_access_status = False  # ロック取得
try:
    model.startMicTranscript(self.micMessage)
finally:
    self.device_access_status = True  # ロック解放
```

**VRAMエラーハンドリング:**
- `model.detectVRAMError()` でエラーを検出
- 音声認識を停止
- フロントエンドに通知

##### `stopTranscriptionSendMessage() -> None`
マイク音声認識を停止。

##### `startThreadingTranscriptionSendMessage() -> None`
別スレッドで音声認識を開始。

##### `stopThreadingTranscriptionSendMessage() -> None`
別スレッドで音声認識を停止し、完了を待機（`join()`）。

**対応するスピーカー用メソッド:**
- `startTranscriptionReceiveMessage()`
- `stopTranscriptionReceiveMessage()`
- `startThreadingTranscriptionReceiveMessage()`
- `stopThreadingTranscriptionReceiveMessage()`

---

### 10. エネルギー監視

#### `startCheckMicEnergy() -> None`
マイクの音量レベル監視を開始。`progressBarMicEnergy()` をコールバックとして渡す。

#### `stopCheckMicEnergy() -> None`
マイクの音量レベル監視を停止。

#### `startThreadingCheckMicEnergy() -> None`
別スレッドでエネルギー監視を開始。

#### `stopThreadingCheckMicEnergy() -> None`
別スレッドでエネルギー監視を停止し、完了を待機。

**対応するスピーカー用メソッド:**
- `startCheckSpeakerEnergy()`
- `stopCheckSpeakerEnergy()`
- `startThreadingCheckSpeakerEnergy()`
- `stopThreadingCheckSpeakerEnergy()`

---

### 11. モデルウェイト管理

#### DownloadCTranslate2 クラス

**責務:** CTranslate2 モデルのダウンロード進捗管理

**メソッド:**
- `progressBar(progress: float)`: 進捗率をフロントエンドに通知
- `downloaded()`: ダウンロード完了時の処理
  - モデルの存在確認
  - 選択可能モデルリストに追加
  - フロントエンドに通知

#### DownloadWhisper クラス

**責務:** Whisper モデルのダウンロード進捗管理（CTranslate2 と同様の構造）

#### `downloadCtranslate2Weight(data: str, asynchronous: bool = True, *args, **kwargs) -> dict`

**責務:** CTranslate2 モデルのダウンロード開始

**パラメータ:**
- `data`: モデルタイプ（"tiny", "small", "medium" 等）
- `asynchronous`: 非同期ダウンロードの有効化

**処理:**
1. `DownloadCTranslate2` インスタンスを作成
2. `asynchronous` が True の場合:
   - `startThreadingDownloadCtranslate2Weight()` で別スレッド実行
3. `asynchronous` が False の場合:
   - `model.downloadCTranslate2ModelWeight()` で同期実行（初期化時に使用）
4. トークナイザーのダウンロード

#### `downloadWhisperWeight(data: str, asynchronous: bool = True, *args, **kwargs) -> dict`

**責務:** Whisper モデルのダウンロード開始（CTranslate2 と同様の構造）

---

### 12. 自動デバイス選択

#### `applyAutoMicSelect() -> None`

**責務:** マイクの自動選択機能を適用

**処理:**
1. コールバック設定:
   - `device_manager.setCallbackProcessBeforeUpdateMicDevices(self.stopAccessMicDevices)`
   - `device_manager.setCallbackDefaultMicDevice(self.updateSelectedMicDevice)`
   - `device_manager.setCallbackProcessAfterUpdateMicDevices(self.restartAccessMicDevices)`
2. デバイス更新を強制実行: `device_manager.forceUpdateAndSetMicDevices()`
3. 監視開始: `device_manager.startMonitoring()`

**動作フロー:**
```
デバイス変更検出
  ↓
stopAccessMicDevices() ← デバイス使用中の処理を停止
  ↓
updateSelectedMicDevice() ← 新しいデフォルトデバイスを選択
  ↓
restartAccessMicDevices() ← 新しいデバイスで処理を再開
```

#### `setEnableAutoMicSelect(*args, **kwargs) -> dict`
自動マイク選択を有効化。

#### `setDisableAutoMicSelect(*args, **kwargs) -> dict`
自動マイク選択を無効化。両方の自動選択が無効になった場合のみ監視を停止。

**対応するスピーカー用メソッド:**
- `applyAutoSpeakerSelect()`
- `setEnableAutoSpeakerSelect()`
- `setDisableAutoSpeakerSelect()`

---

### 13. 言語・翻訳エンジン管理

#### `updateTranslationEngineAndEngineList() -> None`

**責務:** 選択された言語に応じて利用可能な翻訳エンジンを更新

**処理:**
1. 現在のタブの選択エンジンを取得
2. `getTranslationEngines()` で利用可能なエンジンリストを取得
3. 選択中のエンジンが利用不可の場合、CTranslate2 にフォールバック
4. **特殊ケース:** 入力言語と出力言語が同一の場合:
   - CTranslate2 のみ利用可能（音訳のみ）
5. フロントエンドに通知

#### `getTranslationEngines(*args, **kwargs) -> dict`

**責務:** 現在の言語設定で利用可能な翻訳エンジンを返却

**ロジック:**
1. `model.findTranslationEngines()` で言語ペアをサポートするエンジンを検索
2. 入力言語と出力言語が同一の場合:
   - CTranslate2 が有効なら ["CTranslate2"]
   - それ以外は []

#### `setSelectedYourLanguages(select: dict, *args, **kwargs) -> dict`
入力言語を設定し、`updateTranslationEngineAndEngineList()` を呼び出す。

#### `setSelectedTargetLanguages(select: dict, *args, **kwargs) -> dict`
出力言語を設定し、`updateTranslationEngineAndEngineList()` を呼び出す。

#### `swapYourLanguageAndTargetLanguage(*args, **kwargs) -> dict`

**責務:** 入力言語と出力言語を入れ替え

**処理:**
1. 現在のタブの入力言語と出力言語（最初の1つ）を取得
2. 相互に入れ替え
3. `setSelectedYourLanguages()` と `setSelectedTargetLanguages()` を呼び出し
4. 両方の結果を返却

---

### 14. 音声認識エンジン管理

#### `updateTranscriptionEngine() -> None`

**責務:** Whisper モデルの利用可能状況に応じて音声認識エンジンを更新

**処理:**
1. 現在選択されている Whisper モデルの存在確認
2. 利用可能なエンジンリストを取得
3. 現在のエンジンが利用不可の場合:
   - Whisper ⇔ Google で切り替え
   - どちらも利用不可なら Whisper にフォールバック

#### `updateDownloadedWhisperModelWeight() -> None`

**責務:** ダウンロード済み Whisper モデルの一覧を更新

**処理:**
全てのモデルタイプについて `model.checkTranscriptionWhisperModelWeight()` で存在確認。

---

### 15. OSC 通信制御

#### `setOscIpAddress(data, *args, **kwargs) -> dict`

**責務:** VRChat への送信先 IP アドレスを設定

**処理:**
1. `isValidIpAddress()` でバリデーション
2. `model.setOscIpAddress()` で設定を適用
3. OSC Query の状態に応じて再初期化:
   - 有効な場合: `enableOscQuery()` を呼び出し
   - 無効な場合: `disableOscQuery()` を呼び出し
   - マイクミュート同期が有効だった場合は無効化して通知

**エラーハンドリング:**
- IP アドレスが無効: status 400
- 設定適用失敗: 元の IP に戻して status 400

#### `setOscPort(data, *args, **kwargs) -> dict`
OSC ポート番号を設定。

#### `enableOscQuery() -> None`
OSC Query 機能が有効になったことをフロントエンドに通知。

#### `disableOscQuery(mute_sync_info: bool = False) -> None`
OSC Query 機能が無効になったことを通知。無効化された機能リストも送信。

---

### 16. DeepL API 認証

#### `setDeeplAuthKey(data, *args, **kwargs) -> dict`

**責務:** DeepL API キーを設定し、認証を実行

**処理:**
1. キー長のバリデーション（36 または 39 文字）
2. `model.authenticationTranslatorDeepLAuthKey()` で認証
3. 認証成功時:
   - `config.AUTH_KEYS["DeepL_API"]` に保存
   - `config.SELECTABLE_TRANSLATION_ENGINE_STATUS["DeepL_API"]` を True に
   - `updateTranslationEngineAndEngineList()` を呼び出し
4. 認証失敗時: status 400 を返却

#### `delDeeplAuthKey(*args, **kwargs) -> dict`

**責務:** DeepL API キーを削除

**処理:**
1. `config.AUTH_KEYS["DeepL_API"]` を None に
2. `config.SELECTABLE_TRANSLATION_ENGINE_STATUS["DeepL_API"]` を False に
3. `updateTranslationEngineAndEngineList()` を呼び出し

---

### 16-1. Groq API 認証・モデル管理

#### `setGroqAuthKey(data, *args, **kwargs) -> dict`

**責務:** Groq API キーを設定し、認証を実行

**処理:**
1. キー長のバリデーション（`gsk` で始まり40文字以上）
2. `model.authenticationTranslatorGroqAuthKey()` で認証
3. 認証成功時:
   - `config.AUTH_KEYS["Groq_API"]` に保存
   - `config.SELECTABLE_TRANSLATION_ENGINE_STATUS["Groq_API"]` を True に
   - `config.SELECTABLE_GROQ_MODEL_LIST` を取得
   - 未選択の場合は先頭モデルを自動選択
   - `model.updateTranslatorGroqClient()` でクライアント更新
   - `updateTranslationEngineAndEngineList()` を呼び出し
4. 認証失敗時: status 400 を返却

**API キー検証失敗時の処理:**
- モデルリストをクリア (`config.SELECTABLE_GROQ_MODEL_LIST = []`)
- 選択モデルをクリア (`config.SELECTED_GROQ_MODEL = None`)
- フロントエンドに通知

#### `delGroqAuthKey(*args, **kwargs) -> dict`

**責務:** Groq API キーを削除

**処理:**
1. `config.AUTH_KEYS["Groq_API"]` を None に
2. `config.SELECTABLE_TRANSLATION_ENGINE_STATUS["Groq_API"]` を False に
3. モデルリストと選択モデルをクリア
4. `updateTranslationEngineAndEngineList()` を呼び出し

#### `getGroqAuthKey(*args, **kwargs) -> dict`
現在の Groq API キーを取得（マスク処理なし）。

#### `getGroqModelList(*args, **kwargs) -> dict`
利用可能な Groq モデルリストを取得。

#### `getGroqModel(*args, **kwargs) -> dict`
現在選択中の Groq モデルを取得。

#### `setGroqModel(data, *args, **kwargs) -> dict`

**責務:** 使用する Groq モデルを変更

**処理:**
1. モデル名のバリデーション（利用可能リスト内か確認）
2. `model.setTranslatorGroqModel()` でモデル設定
3. `model.updateTranslatorGroqClient()` でクライアント再生成
4. `config.SELECTED_GROQ_MODEL` を更新

---

### 16-2. OpenRouter API 認証・モデル管理

#### `setOpenRouterAuthKey(data, *args, **kwargs) -> dict`

**責務:** OpenRouter API キーを設定し、認証を実行

**処理:**
1. キー長のバリデーション（20文字以上）
2. `model.authenticationTranslatorOpenRouterAuthKey()` で認証
3. 認証成功時:
   - `config.AUTH_KEYS["OpenRouter_API"]` に保存
   - `config.SELECTABLE_TRANSLATION_ENGINE_STATUS["OpenRouter_API"]` を True に
   - `config.SELECTABLE_OPENROUTER_MODEL_LIST` を取得
   - 未選択の場合は先頭モデルを自動選択
   - `model.updateTranslatorOpenRouterClient()` でクライアント更新
   - `updateTranslationEngineAndEngineList()` を呼び出し
4. 認証失敗時: status 400 を返却

**API キー検証失敗時の処理:**
- モデルリストをクリア (`config.SELECTABLE_OPENROUTER_MODEL_LIST = []`)
- 選択モデルをクリア (`config.SELECTED_OPENROUTER_MODEL = None`)
- フロントエンドに通知

#### `delOpenRouterAuthKey(*args, **kwargs) -> dict`

**責務:** OpenRouter API キーを削除

**処理:**
1. `config.AUTH_KEYS["OpenRouter_API"]` を None に
2. `config.SELECTABLE_TRANSLATION_ENGINE_STATUS["OpenRouter_API"]` を False に
3. モデルリストと選択モデルをクリア
4. `updateTranslationEngineAndEngineList()` を呼び出し

#### `getOpenRouterAuthKey(*args, **kwargs) -> dict`
現在の OpenRouter API キーを取得（マスク処理なし）。

#### `getOpenRouterModelList(*args, **kwargs) -> dict`
利用可能な OpenRouter モデルリストを取得。

#### `getOpenRouterModel(*args, **kwargs) -> dict`
現在選択中の OpenRouter モデルを取得。

#### `setOpenRouterModel(data, *args, **kwargs) -> dict`

**責務:** 使用する OpenRouter モデルを変更

**処理:**
1. モデル名のバリデーション（利用可能リスト内か確認）
2. `model.setTranslatorOpenRouterModel()` でモデル設定
3. `model.updateTranslatorOpenRouterClient()` でクライアント再生成
4. `config.SELECTED_OPENROUTER_MODEL` を更新

---

### 17. WebSocket サーバー制御

#### `setWebSocketHost(data, *args, **kwargs) -> dict`

**責務:** WebSocket サーバーのホストアドレスを変更

**処理:**
1. `isValidIpAddress()` でバリデーション
2. サーバーが停止中の場合:
   - 設定のみ変更
3. サーバーが起動中の場合:
   - 新しいホストが利用可能か確認（`isAvailableWebSocketServer()`）
   - サーバーを停止 → 再起動
   - 利用不可の場合は status 400

#### `setWebSocketPort(data, *args, **kwargs) -> dict`
WebSocket サーバーのポート番号を変更（ロジックは `setWebSocketHost()` と同様）。

#### `setEnableWebSocketServer(*args, **kwargs) -> dict`

**責務:** WebSocket サーバーを起動

**処理:**
1. 既に起動中なら何もしない
2. ホストとポートが利用可能か確認
3. `model.startWebSocketServer()` で起動
4. 利用不可の場合は status 400

#### `setDisableWebSocketServer(*args, **kwargs) -> dict`
WebSocket サーバーを停止。

---

### 18. VRChat マイクミュート同期

#### `setEnableVrcMicMuteSync(*args, **kwargs) -> dict`

**責務:** VRChat のマイクミュート状態と音声認識の連動を有効化

**前提条件:** OSC Query が有効であること

**処理:**
1. OSC Query が無効の場合は status 400 を返却
2. `model.setMuteSelfStatus()`: 現在のミュート状態を取得
3. `model.changeMicTranscriptStatus()`: ミュート状態に応じて音声認識を制御
4. `config.VRC_MIC_MUTE_SYNC = True`

#### `setDisableVrcMicMuteSync(*args, **kwargs) -> dict`
マイクミュート同期を無効化し、`model.changeMicTranscriptStatus()` を呼び出す。

---

### 19. Watchdog 管理

Watchdog は UI とバックエンド間の通信監視機能。UI からの定期的な "feed" 信号がない場合、バックエンドを強制終了する。

#### `startWatchdog(*args, **kwargs) -> dict`
Watchdog を起動。

#### `feedWatchdog(*args, **kwargs) -> dict`
Watchdog にハートビート信号を送信（UI が定期的に呼び出す）。

#### `setWatchdogCallback(callback) -> dict`
Watchdog タイムアウト時に呼び出すコールバック関数を設定。`mainloop.stop()` が渡される。

#### `stopWatchdog(*args, **kwargs) -> dict`
Watchdog を停止。

---

### 20. ソフトウェアアップデート

#### `checkSoftwareUpdated() -> dict`

**責務:** 最新バージョンの確認

**処理:**
1. `model.checkSoftwareUpdated()` でバージョン情報を取得
2. フロントエンドに通知（`software_update_info` エンドポイント）
3. 結果を返却

**バージョン情報形式:**
```python
{
    "current_version": "1.2.3",
    "latest_version": "1.2.4",
    "update_available": True,
    "download_url": "https://..."
}
```

#### `updateSoftware(*args, **kwargs) -> dict`

**責務:** 通常版のアップデートを実行

**処理:**
1. 別スレッドで `model.updateSoftware()` を起動（ブロッキングを避けるため）
2. 即座に status 200 を返却

#### `updateCudaSoftware(*args, **kwargs) -> dict`

**責務:** CUDA版のアップデートを実行

**処理:** `updateSoftware()` と同様だが、`model.updateCudaSoftware()` を呼び出す。

---

### 21. 初期化処理

#### `init(*args, **kwargs) -> None`

**責務:** アプリケーションの完全な初期化

**処理フロー:**

**1. ログのクリア**
```python
removeLog()
printLog("Start Initialization")
```

**2. ネットワーク接続確認**
```python
connected_network = isConnectedNetwork()
if connected_network:
    self.connectedNetwork()
else:
    self.disconnectedNetwork()
```

**3. モデルウェイトのダウンロード（進捗1/4）**
```python
self.initializationProgress(1)
if connected_network:
    # CTranslate2 と Whisper を並列ダウンロード
    th_download_ctranslate2 = Thread(target=self.downloadCtranslate2Weight, args=(weight_type, False))
    th_download_whisper = Thread(target=self.downloadWhisperWeight, args=(weight_type, False))
    th_download_ctranslate2.start()
    th_download_whisper.start()
    th_download_ctranslate2.join()
    th_download_whisper.join()
```

**4. AI モデル状態の確認**
```python
if (model.checkTranslatorCTranslate2ModelWeight(...) is False or
    model.checkTranscriptionWhisperModelWeight(...) is False):
    self.disableAiModels()
else:
    self.enableAiModels()
```

**5. 翻訳・音声認識エンジンの初期化（進捗2/4）**
```python
self.initializationProgress(2)
# 翻訳エンジン
for engine in config.SELECTABLE_TRANSLATION_ENGINE_LIST:
    match engine:
        case "CTranslate2":
            # モデルウェイトの存在確認
        case "DeepL_API":
            # API キーの認証
        case _:
            # ネットワーク接続が必要なエンジン

# 音声認識エンジン
for engine in config.SELECTABLE_TRANSCRIPTION_ENGINE_LIST:
    # 同様のロジック
```

**6. エンジンと音訳の設定（進捗3/4）**
```python
self.updateDownloadedCTranslate2ModelWeight()
self.updateTranslationEngineAndEngineList()
self.updateDownloadedWhisperModelWeight()
self.updateTranscriptionEngine()

if config.CONVERT_MESSAGE_TO_ROMAJI or config.CONVERT_MESSAGE_TO_HIRAGANA:
    model.startTransliteration()
```

**7. 周辺機能の初期化（進捗4/4）**
```python
self.initializationProgress(4)
model.addKeywords()  # ワードフィルター
self.checkSoftwareUpdated()  # バージョンチェック
if config.LOGGER_FEATURE:
    model.startLogger()  # ログ記録
model.startReceiveOSC()  # OSC 受信

# OSC Query
osc_query_enabled = model.getIsOscQueryEnabled()
if osc_query_enabled:
    self.enableOscQuery()
    if config.VRC_MIC_MUTE_SYNC:
        self.setEnableVrcMicMuteSync()
else:
    # マイクミュート同期を無効化
    self.disableOscQuery(...)
```

**8. デバイス管理の初期化**
```python
device_manager.setCallbackHostList(self.updateMicHostList)
device_manager.setCallbackMicDeviceList(self.updateMicDeviceList)
device_manager.setCallbackSpeakerDeviceList(self.updateSpeakerDeviceList)

if config.AUTO_MIC_SELECT:
    self.applyAutoMicSelect()
if config.AUTO_SPEAKER_SELECT:
    self.applyAutoSpeakerSelect()
```

**9. オーバーレイと WebSocket の起動**
```python
if config.OVERLAY_SMALL_LOG or config.OVERLAY_LARGE_LOG:
    model.startOverlay()

if config.WEBSOCKET_SERVER:
    if isAvailableWebSocketServer(...):
        model.startWebSocketServer(...)
```

**10. 設定の同期と完了**
```python
self.updateConfigSettings()  # 全設定をフロントエンドに送信
printLog("End Initialization")
self.startWatchdog()  # 監視開始
```

---

## エラーハンドリング戦略

### 1. VRAM不足エラー

**検出箇所:**
- 翻訳実行時（`micMessage()`, `speakerMessage()`, `chatMessage()`）
- 翻訳機能有効化時（`setEnableTranslation()`）
- 音声認識開始時（`startTranscriptionSendMessage()`, `startTranscriptionReceiveMessage()`）

**処理:**
1. `model.detectVRAMError(e)` で VRAM エラーを検出
2. 該当機能を無効化
3. フロントエンドにエラー通知
4. ログファイルに記録

**自動リカバリ:**
- 翻訳機能: 無効化して継続
- 音声認識: 停止して継続

### 2. デバイスアクセスエラー

**検出箇所:**
- マイク・スピーカーのアクセス時

**処理:**
1. `energy` が `False` の場合
2. `error_device` エンドポイントにエラー通知
3. 処理を継続（他の機能は影響を受けない）

### 3. ネットワークエラー

**検出箇所:**
- 翻訳APIの呼び出し時
- モデルウェイトのダウンロード時

**処理:**
1. 外部API エラー: `changeToCTranslate2Process()` で CTranslate2 に切り替え
2. ダウンロードエラー: エラー通知を送信、AI機能を無効化

### 4. 設定バリデーションエラー

**処理:**
- status 400 とエラーメッセージを返却
- 現在の有効な設定値を `data` フィールドに含める

**例:**
```python
{
    "status": 400,
    "result": {
        "message": "Mic energy threshold value is out of range",
        "data": 1000  # 現在の有効な値
    }
}
```

---

## スレッド安全性

### 排他制御

#### デバイスアクセス制御

**問題:** 複数の機能が同時にデバイスにアクセスすると衝突

**解決策:** `device_access_status` フラグによる排他制御
```python
while self.device_access_status is False:
    sleep(1)  # 待機
self.device_access_status = False  # ロック取得
try:
    # デバイスアクセス処理
finally:
    self.device_access_status = True  # ロック解放
```

**使用箇所:**
- `startTranscriptionSendMessage()`
- `startTranscriptionReceiveMessage()`
- `startCheckMicEnergy()`
- `startCheckSpeakerEnergy()`

### デーモンスレッド

**すべてのワーカースレッドは `daemon = True`:**
- メインスレッド終了時に自動的に終了
- 明示的な join は必要に応じて実行（停止処理等）

**例:**
```python
th_startTranscriptionSendMessage = Thread(target=self.startTranscriptionSendMessage)
th_startTranscriptionSendMessage.daemon = True
th_startTranscriptionSendMessage.start()
```

---

## パフォーマンス考慮事項

### 1. 非同期ダウンロード

**初期化時:** 同期ダウンロード（`asynchronous=False`）
- UI をブロックして確実にダウンロード完了を待つ

**ユーザー操作時:** 非同期ダウンロード（`asynchronous=True`）
- 別スレッドで実行し、進捗バーで通知

### 2. 並列初期化

CTranslate2 と Whisper のダウンロードを並列実行:
```python
th_download_ctranslate2.start()
th_download_whisper.start()
th_download_ctranslate2.join()
th_download_whisper.join()
```

### 3. モデルの遅延ロード

翻訳モデルは `setEnableTranslation()` が呼ばれるまでロードされない。

---

## 依存関係

### 外部モジュール

```python
from typing import Callable, Any, List, Optional
from time import sleep
from subprocess import Popen
from threading import Thread
import re
```

### 内部モジュール

```python
from device_manager import device_manager
from config import config
from model import model
from utils import removeLog, printLog, errorLogging, isConnectedNetwork, isValidIpAddress, isAvailableWebSocketServer
```

---

## 設定項目の分類

### UI関連（約20項目）
- 透明度、スケーリング、フォント、言語、ウィンドウ位置等

### 音声認識関連（約30項目）
- デバイス選択、閾値、タイムアウト、フィルター等

### 翻訳関連（約25項目）
- エンジン選択、言語ペア、モデルタイプ、計算デバイス等

### OSC通信関連（約15項目）
- IP アドレス、ポート、メッセージフォーマット、送信設定等

### オーバーレイ関連（約10項目）
- 表示設定、位置、サイズ、透明度等

### その他（約20項目）
- WebSocket、ログ、ホットキー、プラグイン等

**合計:** 約120の設定項目（getter/setter で約240メソッド）

---

## 制限事項

### 1. グローバル状態依存

すべての設定が `config` モジュールのグローバル変数として管理されている。
- **利点:** シンプルなアクセス
- **欠点:** テスタビリティの低下、並列実行時の競合リスク

### 2. 同期レスポンスの制限

ほとんどのメソッドが同期的にレスポンスを返すため、重い処理（モデルロード等）は UI をブロックする可能性がある。

**対策:** 重い処理は別スレッドで実行し、完了通知は `self.run()` で送信

### 3. エラー回復の限界

一部のエラー（VRAM不足等）は自動回復するが、設定ファイル破損やモデルファイル破損等は手動対処が必要。

---

## テストシナリオ

### 1. 初期化テスト

**ケース:**
- ネットワーク接続あり・なし
- モデルウェイトあり・なし
- 不正な設定値

**確認項目:**
- 全エンジンの状態が正しく設定されているか
- エラーがログに記録されているか
- フロントエンドに正しい初期設定が送信されているか

### 2. 音声認識テスト

**ケース:**
- デバイス切り替え中に音声認識
- VRAM不足エラーの発生
- 重複メッセージのフィルタリング

**確認項目:**
- 排他制御が正しく動作しているか
- エラー発生時に適切にリカバリしているか

### 3. 翻訳テスト

**ケース:**
- 複数の翻訳エンジンの切り替え
- API制限エラー
- 除外ワードの処理

**確認項目:**
- エンジン切り替えが正しく動作するか
- 除外ワードが正しく復元されるか

### 4. 設定変更テスト

**ケース:**
- 無効な値の設定
- 依存関係のある設定の変更
- 有効/無効の切り替え

**確認項目:**
- バリデーションが正しく動作するか
- 依存する設定が自動更新されるか

---

## 今後の拡張性

### 1. 非同期化の推進

`asyncio` への移行で UI ブロッキングを完全に排除。

### 2. 依存性注入

`config` と `model` を DI コンテナで管理し、テスタビリティを向上。

### 3. イベント駆動アーキテクチャ

設定変更時のイベントを発火し、各サブシステムが独立して反応。

### 4. エラーリカバリの強化

- 自動再試行メカニズム
- フォールバック設定の自動適用
- エラー発生時の部分的な機能継続

---

## 関連ファイル

- **mainloop.py** - 通信レイヤー、リクエストルーティング
- **model.py** - ビジネスロジックのファサード
- **config.py** - 設定管理
- **device_manager.py** - デバイス監視・自動選択
- **utils.py** - ログとユーティリティ関数

---

## コーディング規約

- **PEP 8 スタイルガイド**
- **型ヒント:** `typing` モジュールを使用
- **Docstring:** Google スタイル（一部未実装）
- **静的メソッド:** 状態を持たないメソッドは `@staticmethod`
- **エラーハンドリング:** 防御的プログラミングを徹底

---

## まとめ

`controller.py` は VRCT の中核となるビジネスロジック制御レイヤーであり、約120の設定項目と約200のエンドポイントを管理する。フロントエンドとバックエンドの橋渡しとして、設定の取得・更新、機能の有効化・無効化、エラーハンドリング、デバイス管理など、アプリケーション全体の動作を制御する。排他制御とスレッド管理により、複数の機能が同時に動作する環境でも安定性を保っている。VRAM不足エラーや外部APIエラーに対する自動リカバリ機能により、ユーザーエクスペリエンスの向上を実現している。
