# transcription_whisper.py - Whisperモデル管理

## 概要

OpenAI Whisper（faster-whisper）モデルのダウンロード、検証、読み込みを管理するユーティリティモジュールです。複数のモデルサイズをサポートし、Hugging Face Hubからの自動ダウンロード機能とファイル整合性チェック機能を提供します。

## 主要機能

### モデル管理
- 複数Whisperモデルサイズの対応
- Hugging Face Hubからの自動ダウンロード
- モデルファイルの整合性検証

### ダウンロード機能
- 進捗表示付きダウンロード
- レジューム対応
- エラーハンドリング

### モデル読み込み
- 効率的なモデル初期化
- CUDA対応
- 計算タイプ最適化

## サポートモデル

### 利用可能なモデル
```python
_MODELS = {
    "tiny": "Systran/faster-whisper-tiny",           # ~39MB
    "base": "Systran/faster-whisper-base",           # ~74MB  
    "small": "Systran/faster-whisper-small",         # ~244MB
    "medium": "Systran/faster-whisper-medium",       # ~769MB
    "large-v1": "Systran/faster-whisper-large-v1",  # ~1.5GB
    "large-v2": "Systran/faster-whisper-large-v2",  # ~1.5GB
    "large-v3": "Systran/faster-whisper-large-v3",  # ~1.5GB
    "large-v3-turbo-int8": "Zoont/faster-whisper-large-v3-turbo-int8-ct2",  # ~794MB
    "large-v3-turbo": "deepdml/faster-whisper-large-v3-turbo-ct2"           # ~1.58GB
}
```

### モデル特性比較

#### tiny
- **サイズ**: ~39MB
- **精度**: 低
- **速度**: 最高速
- **用途**: リアルタイム処理、リソース制限環境

#### base  
- **サイズ**: ~74MB
- **精度**: 中程度
- **速度**: 高速
- **用途**: 一般的な用途、バランス重視

#### small
- **サイズ**: ~244MB  
- **精度**: 良好
- **速度**: 中程度
- **用途**: 品質重視、モバイル環境

#### medium
- **サイズ**: ~769MB
- **精度**: 高
- **速度**: やや低速
- **用途**: 高品質認識、デスクトップ環境

#### large系
- **サイズ**: ~1.5GB
- **精度**: 最高
- **速度**: 低速
- **用途**: 最高品質、サーバー環境

## 主要関数

### ファイルダウンロード

```python
downloadFile(url: str, path: str, func: Optional[Callable[[float], None]] = None) -> None
```

ファイルのストリームダウンロード

#### パラメータ
- **url**: ダウンロードURL
- **path**: 保存先パス
- **func**: 進捗コールバック関数

### モデル検証

```python
checkWhisperWeight(root: str, weight_type: str) -> bool
```

Whisperモデルの利用可能性確認

#### パラメータ
- **root**: アプリケーションルートパス
- **weight_type**: モデルタイプ（"tiny", "base"等）

#### 戻り値
- **bool**: モデルが利用可能かどうか

### モデルダウンロード

```python
downloadWhisperWeight(root: str, weight_type: str, 
                     callback: Optional[Callable[[float], None]] = None,
                     end_callback: Optional[Callable[[], None]] = None) -> None
```

Whisperモデルのダウンロード

#### パラメータ
- **root**: アプリケーションルートパス
- **weight_type**: ダウンロードするモデルタイプ
- **callback**: 進捗コールバック
- **end_callback**: 完了コールバック

### モデル読み込み

```python
getWhisperModel(root: str, weight_type: str, device: str = "cpu",
                device_index: int = 0, compute_type: str = "auto") -> WhisperModel
```

Whisperモデルの初期化

#### パラメータ
- **root**: アプリケーションルートパス
- **weight_type**: 使用するモデルタイプ
- **device**: 計算デバイス（"cpu"/"cuda"）
- **device_index**: デバイスインデックス
- **compute_type**: 計算精度タイプ

#### 戻り値
- **WhisperModel**: 初期化されたWhisperモデルインスタンス

## 使用方法

### モデルの確認とダウンロード

```python
from models.transcription.transcription_whisper import checkWhisperWeight, downloadWhisperWeight

root_path = "."
model_type = "base"

# モデルの利用可能性確認
if not checkWhisperWeight(root_path, model_type):
    print(f"{model_type}モデルが見つかりません。ダウンロードします...")
    
    # 進捗コールバック
    def progress_callback(progress):
        print(f"ダウンロード進捗: {progress:.1%}")
    
    # 完了コールバック  
    def completion_callback():
        print("ダウンロード完了!")
    
    # モデルダウンロード
    downloadWhisperWeight(
        root=root_path,
        weight_type=model_type,
        callback=progress_callback,
        end_callback=completion_callback
    )
else:
    print(f"{model_type}モデルは利用可能です")
```

### モデルの読み込みと使用

```python
from models.transcription.transcription_whisper import getWhisperModel

# CPUでのモデル読み込み
model = getWhisperModel(
    root=".",
    weight_type="base", 
    device="cpu"
)

# CUDAでのモデル読み込み（GPU使用）
gpu_model = getWhisperModel(
    root=".",
    weight_type="small",
    device="cuda",
    device_index=0,
    compute_type="float16"  # 半精度で高速化
)

# 音声認識の実行
audio_file = "audio.wav"
segments, info = model.transcribe(audio_file, language="ja")

for segment in segments:
    print(f"{segment.start:.1f}s - {segment.end:.1f}s: {segment.text}")
```

### エラーハンドリング付きの使用

```python
def safe_model_loading(root, weight_type, device="cpu"):
    """安全なモデル読み込み"""
    try:
        # モデル存在確認
        if not checkWhisperWeight(root, weight_type):
            print(f"モデル {weight_type} をダウンロード中...")
            downloadWhisperWeight(root, weight_type)
        
        # モデル読み込み
        model = getWhisperModel(root, weight_type, device)
        return model
        
    except Exception as e:
        print(f"モデル読み込みエラー: {e}")
        # フォールバック: より小さなモデルを試す
        if weight_type != "tiny":
            return safe_model_loading(root, "tiny", device)
        return None
```

### 進捗表示付きダウンロード

```python
import sys

def download_with_progress(root, weight_type):
    """進捗表示付きダウンロード"""
    def show_progress(progress):
        bar_length = 40
        filled_length = int(bar_length * progress)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        sys.stdout.write(f'\r[{bar}] {progress:.1%}')
        sys.stdout.flush()
    
    def download_complete():
        print("\nダウンロード完了!")
    
    print(f"Whisper {weight_type} モデルをダウンロード中...")
    downloadWhisperWeight(root, weight_type, show_progress, download_complete)
```

## ディレクトリ構造

### モデルファイル配置
```
root/
└── weights/
    └── whisper/
        ├── tiny/
        │   ├── config.json
        │   ├── preprocessor_config.json  
        │   ├── model.bin
        │   ├── tokenizer.json
        │   └── vocabulary.txt
        ├── base/
        └── small/
```

### 必要ファイル
```python
_FILENAMES = [
    "config.json",           # モデル設定
    "preprocessor_config.json",  # 前処理設定
    "model.bin",            # モデルウェイト
    "tokenizer.json",       # トークナイザー
    "vocabulary.txt",       # 語彙ファイル
    "vocabulary.json"       # 語彙ファイル（JSON形式）
]
```

## パフォーマンス考慮事項

### メモリ使用量
- **tiny**: ~100MB RAM
- **base**: ~200MB RAM
- **small**: ~500MB RAM  
- **medium**: ~1.5GB RAM
- **large**: ~3GB RAM

### VRAM使用量（CUDA使用時）
- **tiny**: ~200MB VRAM
- **base**: ~300MB VRAM
- **small**: ~600MB VRAM
- **medium**: ~1.8GB VRAM
- **large**: ~3.5GB VRAM

### 処理速度（目安）
- **tiny**: リアルタイム処理可能
- **base**: 1x-2x リアルタイム
- **small**: 0.5x-1x リアルタイム
- **medium**: 0.2x-0.5x リアルタイム
- **large**: 0.1x-0.3x リアルタイム

## 計算タイプ設定

### 利用可能な計算タイプ
- **float32**: 最高精度、低速
- **float16**: 高精度、中速（CUDA推奨）
- **int8**: 中精度、高速
- **int8_float16**: 混合精度、バランス

### 推奨設定
```python
# CPU使用時
compute_type = "int8"  # 速度重視

# CUDA使用時（RTX以上）
compute_type = "float16"  # 精度と速度のバランス

# CUDA使用時（VRAM制限）
compute_type = "int8_float16"  # メモリ効率重視
```

## エラーハンドリング

### ダウンロードエラー
- ネットワーク接続失敗
- ディスク容量不足
- 権限不足

### モデル読み込みエラー  
- VRAM不足
- 破損したモデルファイル
- 非対応デバイス

### 対応策
```python
def robust_model_loading(root, preferred_type="base"):
    """堅牢なモデル読み込み"""
    model_priority = ["tiny", "base", "small", "medium"]
    
    # 優先モデルを先頭に配置
    if preferred_type in model_priority:
        model_priority.remove(preferred_type)
        model_priority.insert(0, preferred_type)
    
    for model_type in model_priority:
        try:
            if checkWhisperWeight(root, model_type):
                return getWhisperModel(root, model_type)
        except Exception as e:
            print(f"{model_type} モデル読み込み失敗: {e}")
            continue
    
    raise RuntimeError("利用可能なWhisperモデルがありません")
```

## 依存関係

### 必須依存関係
- `faster_whisper`: Whisperエンジン
- `requests`: ファイルダウンロード
- `utils`: ユーティリティ機能

### オプション依存関係
- `torch`: CUDA計算（GPU使用時）

## 注意事項

- 初回モデル読み込み時はダウンロードに時間がかかる
- 大きなモデルほど高精度だが、メモリとVRAMを大量消費
- CUDAを使用する場合は適切なGPUドライバーが必要
- モデルファイルの整合性チェックが重要
- ネットワーク環境によってダウンロード時間が大きく変動

## 関連モジュール

- `transcription_transcriber.py`: Whisper音声認識エンジン
- `config.py`: Whisperモデル設定管理
- `utils.py`: 計算デバイス管理
- `model.py`: Whisper統合制御