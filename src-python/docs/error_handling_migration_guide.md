# エラーハンドリング統一システム移行ガイド

## 概要

`errors.py`で定義された統一エラーシステムを使用して、すべてのエラーハンドリングを標準化しました。

## 変更パターン

### 1. 基本的なエラーレスポンス

#### 修正前:
```python
response = {
    "status": 400,
    "result": {
        "message": "Error message",
        "data": some_value
    }
}
```

#### 修正後:
```python
from errors import ErrorCode, VRCTError

response = VRCTError.create_error_response(
    ErrorCode.APPROPRIATE_ERROR_CODE,
    data=some_value
)
```

### 2. run_mapping経由のエラー通知

#### 修正前:
```python
self.run(
    400,
    self.run_mapping["error_device"],
    {
        "message": "No mic device detected",
        "data": None
    },
)
```

#### 修正後:
```python
error_response = VRCTError.create_error_response(
    ErrorCode.DEVICE_NO_MIC,
    data=None
)
self.run(
    error_response["status"],
    self.run_mapping["error_device"],
    error_response["result"],
)
```

### 3. 例外からのエラー生成

#### 修正前:
```python
except Exception as e:
    errorLogging()
    response = {
        "status": 400,
        "result": {
            "message": f"Error {e}",
            "data": original_value
        }
    }
```

#### 修正後:
```python
except Exception as e:
    errorLogging()
    response = VRCTError.create_exception_error_response(
        e,
        data=original_value
    )
```

## 既に移行済みの箇所

### デバイスエラー
- ✅ `progressBarMicEnergy` - `ErrorCode.DEVICE_NO_MIC`
- ✅ `progressBarSpeakerEnergy` - `ErrorCode.DEVICE_NO_SPEAKER`

### ウェイトダウンロードエラー
- ✅ `DownloadCTranslate2.downloaded` - `ErrorCode.WEIGHT_CTRANSLATE2_DOWNLOAD`
- ✅ `DownloadWhisper.downloaded` - `ErrorCode.WEIGHT_WHISPER_DOWNLOAD`

### 翻訳エラー
- ✅ `micMessage` - `ErrorCode.TRANSLATION_ENGINE_LIMIT`, `ErrorCode.TRANSLATION_VRAM_MIC`, `ErrorCode.TRANSLATION_DISABLED_VRAM`
- ✅ `speakerMessage` - `ErrorCode.TRANSLATION_ENGINE_LIMIT`, `ErrorCode.TRANSLATION_VRAM_SPEAKER`, `ErrorCode.TRANSLATION_DISABLED_VRAM`
- ✅ `chatMessage` - `ErrorCode.TRANSLATION_ENGINE_LIMIT`, `ErrorCode.TRANSLATION_VRAM_CHAT`, `ErrorCode.TRANSLATION_DISABLED_VRAM`
- ✅ `setEnableTranslation` - `ErrorCode.TRANSLATION_VRAM_ENABLE`, `ErrorCode.TRANSLATION_DISABLED_VRAM`

### バリデーションエラー
- ✅ `setMicThreshold` - `ErrorCode.VALIDATION_MIC_THRESHOLD`
- ✅ `setSpeakerThreshold` - `ErrorCode.VALIDATION_SPEAKER_THRESHOLD`
- ✅ `setMicRecordTimeout` - `ErrorCode.VALIDATION_MIC_RECORD_TIMEOUT`
- ✅ `setMicPhraseTimeout` - `ErrorCode.VALIDATION_MIC_PHRASE_TIMEOUT`
- ✅ `setMicMaxPhrases` - `ErrorCode.VALIDATION_MIC_MAX_PHRASES`
- ✅ `setSpeakerRecordTimeout` - `ErrorCode.VALIDATION_SPEAKER_RECORD_TIMEOUT`
- ✅ `setSpeakerPhraseTimeout` - `ErrorCode.VALIDATION_SPEAKER_PHRASE_TIMEOUT`
- ✅ `setSpeakerMaxPhrases` - `ErrorCode.VALIDATION_SPEAKER_MAX_PHRASES`
- ✅ `setOscIpAddress` - `ErrorCode.VALIDATION_INVALID_IP`, `ErrorCode.VALIDATION_CANNOT_SET_IP`

### VRC連携エラー
- ✅ `setEnableVrcMicMuteSync` - `ErrorCode.VRC_MIC_MUTE_SYNC_OSC_DISABLED`

### 認証エラー
- ✅ `setDeeplAuthKey` - `ErrorCode.AUTH_DEEPL_LENGTH`, `ErrorCode.AUTH_DEEPL_FAILED`

## 未移行の箇所（要対応）

以下の箇所は同様のパターンで移行が必要です:

### 認証関連
- ⬜ `setPlamoAuthKey` - `ErrorCode.AUTH_PLAMO_LENGTH`, `ErrorCode.AUTH_PLAMO_FAILED`
- ⬜ `setPlamoModel` - `ErrorCode.MODEL_PLAMO_INVALID`
- ⬜ `setGeminiAuthKey` - `ErrorCode.AUTH_GEMINI_LENGTH`, `ErrorCode.AUTH_GEMINI_FAILED`
- ⬜ `setGeminiModel` - `ErrorCode.MODEL_GEMINI_INVALID`
- ⬜ `setOpenAIAuthKey` - `ErrorCode.AUTH_OPENAI_INVALID`, `ErrorCode.AUTH_OPENAI_FAILED`
- ⬜ `setOpenAIModel` - `ErrorCode.MODEL_OPENAI_INVALID`
- ⬜ `setGroqAuthKey` - `ErrorCode.AUTH_GROQ_INVALID`, `ErrorCode.AUTH_GROQ_FAILED`
- ⬜ `setGroqModel` - `ErrorCode.MODEL_GROQ_INVALID`
- ⬜ `setOpenRouterAuthKey` - `ErrorCode.AUTH_OPENROUTER_INVALID`, `ErrorCode.AUTH_OPENROUTER_FAILED`
- ⬜ `setOpenRouterModel` - `ErrorCode.MODEL_OPENROUTER_INVALID`

### 接続関連
- ⬜ `checkTranslatorLMStudioConnection` - `ErrorCode.CONNECTION_LMSTUDIO_FAILED`
- ⬜ `setTranslatorLMStudioURL` - `ErrorCode.CONNECTION_LMSTUDIO_URL_INVALID`
- ⬜ `setTranslatorLMStudioModel` - `ErrorCode.MODEL_LMSTUDIO_INVALID`
- ⬜ `checkTranslatorOllamaConnection` - `ErrorCode.CONNECTION_OLLAMA_FAILED`
- ⬜ `setTranslatorOllamaModel` - `ErrorCode.MODEL_OLLAMA_INVALID`

### WebSocket関連
- ⬜ `setWebSocketHost` - `ErrorCode.VALIDATION_INVALID_IP`, `ErrorCode.WEBSOCKET_HOST_INVALID`
- ⬜ `setWebSocketPort` - `ErrorCode.WEBSOCKET_PORT_UNAVAILABLE`
- ⬜ `setEnableWebSocketServer` - `ErrorCode.WEBSOCKET_SERVER_UNAVAILABLE`

### 音声認識VRAM関連
- ⬜ `startTranscriptionSendMessage` - `ErrorCode.TRANSCRIPTION_VRAM_MIC`, `ErrorCode.TRANSCRIPTION_SEND_DISABLED_VRAM`
- ⬜ `startTranscriptionReceiveMessage` - `ErrorCode.TRANSCRIPTION_VRAM_SPEAKER`, `ErrorCode.TRANSCRIPTION_RECEIVE_DISABLED_VRAM`

## エラーコードとエンドポイントの対応

`errors.py`の`ENDPOINT_ERROR_MAPPING`に、すべてのエンドポイントとエラーコードの対応が定義されています。
UI開発者はこのマッピングを参照して、各エンドポイントがどのようなエラーを返すか確認できます。

## エラーレスポンスの構造

統一されたエラーレスポンスは以下の構造を持ちます:

```python
{
    "status": 400,  # HTTPステータスコード
    "result": {
        "error_code": "ERROR_CODE_CONSTANT",  # エラーコード定数
        "message": "Human readable message",   # 人間が読めるメッセージ
        "data": None or original_value,       # エラー時に戻す値（通常は元の値）
        "details": {},                        # 追加情報（オプション）
        "category": "category_name",          # エラーカテゴリ
        "severity": "warning|error|critical", # 重要度
    }
}
```

## UI側での活用

UI側では`error_code`を使用して、エラーの種類を判定し、適切な処理を行うことができます:

```javascript
if (response.status === 400) {
    const { error_code, message, data, severity } = response.result;
    
    switch (error_code) {
        case "DEVICE_NO_MIC":
            // マイクデバイスエラーの処理
            break;
        case "VALIDATION_MIC_THRESHOLD":
            // バリデーションエラーの処理（元の値に戻す）
            setValue(data);
            break;
        // ...
    }
    
    // 重要度に応じた表示
    if (severity === "critical") {
        showCriticalError(message);
    }
}
```

## 移行作業の進め方

1. **パターンの確認**: 上記の変更パターンを参照
2. **エラーコードの特定**: `errors.py`から適切な`ErrorCode`を選択
3. **コードの置き換え**: 古いエラーハンドリングを新しいシステムに置き換え
4. **テスト**: エラーが正しく返されることを確認
5. **チェックリストの更新**: このドキュメントの✅を更新

## 注意事項

- すべてのエラーは`errors.py`に定義されたエラーコードを使用すること
- 新しいエラーが必要な場合は、まず`errors.py`に追加すること
- エラーメッセージは`ERROR_METADATA`で定義されたデフォルトメッセージを使用すること
  - カスタムメッセージが必要な場合は`custom_message`パラメータを使用
- `data`パラメータには、エラー時にUIが元の値に戻せるように、元の値を渡すこと
