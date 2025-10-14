# transcription_transcriber.py - 音声文字起こしエンジン

## 概要

音声データを文字テキストに変換する音声認識エンジンのメインクラスです。Google Speech RecognitionとOpenAI Whisper（faster-whisper）の両方をサポートし、オンライン・オフラインの音声認識を統合的に管理します。キューベースの非同期処理により、リアルタイム音声認識を実現します。

## 主要機能

### 音声認識エンジン
- Google Speech Recognition（オンライン）
- OpenAI Whisper（faster-whisper、オフライン）
- エンジン自動切り替え機能

### リアルタイム処理
- 音声キューからの継続的データ処理
- 非同期音声認識処理
- 結果の即座通知

### 多言語対応
- 複数言語の同時認識
- 地域固有言語コードの対応
- 自動言語検出

### 音声品質制御
- 音声品質フィルタリング
- ノイズ除去機能
- 信頼度スコア評価

## クラス構造

### AudioTranscriber クラス
```python
class AudioTranscriber:
    def __init__(self, speaker: bool, source: Any, phrase_timeout: int, max_phrases: int,
                 transcription_engine: str, root: Optional[str] = None,
                 whisper_weight_type: Optional[str] = None, device: str = "cpu",
                 device_index: int = 0, compute_type: str = "auto")
```

音声認識の中核クラス

#### 初期化パラメータ
- **speaker**: スピーカー音声かマイク音声か
- **source**: 音声ソース
- **phrase_timeout**: フレーズタイムアウト（秒）
- **max_phrases**: 最大フレーズ数
- **transcription_engine**: 認識エンジン（"Google"/"Whisper"）
- **whisper_weight_type**: Whisperモデル種類
- **device**: 計算デバイス（"cpu"/"cuda"）
- **device_index**: デバイスインデックス
- **compute_type**: 計算精度タイプ

## 主要メソッド

### 音声認識処理

```python
transcribeAudioQueue(audio_queue: Queue, languages: List[str], countries: List[str],
                    avg_logprob: float = -0.8, no_speech_prob: float = 0.6) -> bool
```

音声キューからの継続的音声認識

#### パラメータ
- **audio_queue**: 音声データキュー
- **languages**: 認識対象言語リスト
- **countries**: 地域コードリスト  
- **avg_logprob**: Whisper平均対数確率しきい値
- **no_speech_prob**: Whisper無音判定しきい値

### 結果管理

```python
getTranscript() -> dict
```

最新の認識結果を取得

```python
updateTranscript(result: dict) -> None
```

認識結果の更新と通知

```python
clearTranscriptData() -> None
```

認識データのクリア

### 音声データ処理

```python
processMicData() -> AudioData
```

マイク音声データの前処理

```python
processSpeakerData() -> AudioData
```

スピーカー音声データの前処理

## 使用方法

### 基本的な音声認識

```python
from queue import Queue
from models.transcription.transcription_transcriber import AudioTranscriber

# 音声認識の初期化
transcriber = AudioTranscriber(
    speaker=False,              # マイク音声
    source=mic_source,          # 音声ソース
    phrase_timeout=3,           # 3秒のフレーズタイムアウト
    max_phrases=10,             # 最大10フレーズ
    transcription_engine="Google",  # Google音声認識
    device="cpu"
)

# 音声キューの準備
audio_queue = Queue()

# 認識対象言語の設定
languages = ["Japanese", "English"]
countries = ["Japan", "United States"]

# 音声認識の実行
def transcription_loop():
    while True:
        success = transcriber.transcribeAudioQueue(
            audio_queue, languages, countries
        )
        if success:
            result = transcriber.getTranscript()
            print(f"認識結果: {result['text']}")
            print(f"言語: {result['language']}")

# バックグラウンドで実行
import threading
thread = threading.Thread(target=transcription_loop)
thread.daemon = True
thread.start()
```

### Whisperエンジンの使用

```python
# Whisper音声認識の初期化
whisper_transcriber = AudioTranscriber(
    speaker=True,               # スピーカー音声
    source=speaker_source,
    phrase_timeout=5,
    max_phrases=5,
    transcription_engine="Whisper",
    whisper_weight_type="base",     # Whisperモデル
    device="cuda",                  # CUDA使用
    device_index=0,
    compute_type="float16"          # 半精度浮動小数点
)

# Whisper固有パラメータでの認識
success = whisper_transcriber.transcribeAudioQueue(
    audio_queue, languages, countries,
    avg_logprob=-0.5,          # より厳しい品質しきい値
    no_speech_prob=0.4         # より敏感な無音検出
)
```

### コールバック処理

```python
def on_transcription_result(result):
    """認識結果のコールバック処理"""
    if result["text"]:
        print(f"認識成功: {result['text']}")
        print(f"言語: {result['language']}")
        print(f"信頼度: {result.get('confidence', 'N/A')}")
    else:
        print("音声認識失敗")

# 結果通知の設定
transcriber.transcript_changed_event.set()  # イベント設定
```

### エラーハンドリング付きの使用

```python
def safe_transcription(transcriber, audio_queue, languages, countries):
    """安全な音声認識処理"""
    try:
        success = transcriber.transcribeAudioQueue(
            audio_queue, languages, countries
        )
        
        if success:
            result = transcriber.getTranscript()
            return result
        else:
            return {"text": False, "language": None, "error": "認識失敗"}
            
    except Exception as e:
        print(f"音声認識エラー: {e}")
        return {"text": False, "language": None, "error": str(e)}
```

## 認識エンジン比較

### Google Speech Recognition

#### 利点
- 高い認識精度
- 多言語対応
- リアルタイム処理
- ノイズ耐性

#### 制限
- インターネット接続必須
- API制限
- プライバシー懸念
- レイテンシ

### OpenAI Whisper（faster-whisper）

#### 利点
- オフライン動作
- プライバシー保護
- 高精度
- 多言語対応

#### 制限
- 初回起動時間
- メモリ使用量
- CUDA推奨
- モデルファイル必要

## 設定パラメータ

### フレーズ制御
- **phrase_timeout**: フレーズ間無音時間（秒）
- **max_phrases**: バッファ内最大フレーズ数

### Whisper品質設定
- **avg_logprob**: 平均対数確率しきい値（-1.0〜0.0）
- **no_speech_prob**: 無音判定しきい値（0.0〜1.0）

### 計算設定
- **device**: "cpu" または "cuda"
- **compute_type**: "float32", "float16", "int8" など

## 音声データフォーマット

### 入力形式
- サンプリングレート: 16kHz推奨
- ビット深度: 16bit
- チャンネル: モノラル推奨
- フォーマット: WAV、FLAC等

### 処理フロー
1. 音声キューからデータ取得
2. 音声フォーマット正規化
3. 音声認識エンジン実行
4. 結果の後処理・フィルタリング
5. 最終結果の通知

## パフォーマンス最適化

### メモリ管理
- 音声バッファの適切なサイズ設定
- 不要な音声データの早期解放
- Whisperモデルのメモリ効率化

### 計算最適化
- CUDA使用による高速化
- 適切な計算精度選択
- バッチ処理の活用

### レイテンシ削減
- 音声バッファサイズの最適化
- エンジン切り替えの高速化
- キャッシュ機能の活用

## エラーハンドリング

### ネットワークエラー
- Google API接続失敗の検出
- 自動Whisperエンジン切り替え

### 音声品質エラー
- 低品質音声の検出・フィルタリング
- ノイズレベル監視

### リソースエラー
- VRAM不足の検出
- メモリ不足時の対応

## 依存関係

### 必須依存関係
- `speech_recognition`: Google音声認識
- `faster_whisper`: Whisper音声認識
- `pyaudiowpatch`: 音声入力
- `pydub`: 音声処理

### オプション依存関係
- `torch`: CUDA計算
- `utils`: エラーログ機能

## 注意事項

- Google APIは使用制限あり
- Whisperは初回起動に時間要
- CUDA使用時はVRAM消費に注意
- 音声品質が認識精度に大きく影響
- 多言語認識時は処理負荷増加

## 関連モジュール

- `transcription_recorder.py`: 音声録音
- `transcription_whisper.py`: Whisperモデル管理
- `transcription_languages.py`: 言語コード管理
- `config.py`: 認識設定管理
- `model.py`: 音声認識統合制御