# transcription_recorder.py - 音声録音インターフェース

## 概要

音声認識システムの入力となる音声データを録音するレコーダークラス群です。マイクとスピーカー出力の両方をサポートし、エネルギーレベル監視機能とともに音声データをキューに送信します。pyaudiowpatchライブラリを使用してWindowsの音声システムと統合します。

## 主要機能

### 音声録音機能
- マイクからの音声録音
- スピーカー出力の録音（ループバック）
- リアルタイム音声データキューイング

### エネルギー監視
- 音声エネルギーレベルの監視
- 動的しきい値調整
- 無音検出

### デバイス対応
- 複数音声デバイスの対応
- デバイス固有設定の管理
- 自動デバイス選択

## クラス構造

### BaseRecorder クラス
```python
class BaseRecorder:
    def __init__(self, source: Any, energy_threshold: int, dynamic_energy_threshold: bool, record_timeout: int)
```

基底レコーダークラス - 共通機能を提供

### SelectedMicRecorder クラス
```python
class SelectedMicRecorder(BaseRecorder):
    def __init__(self, device: dict, energy_threshold: int, dynamic_energy_threshold: bool, record_timeout: int)
```

選択されたマイクデバイスからの録音

### SelectedSpeakerRecorder クラス
```python
class SelectedSpeakerRecorder(BaseRecorder):
    def __init__(self, device: dict, energy_threshold: int, dynamic_energy_threshold: bool, record_timeout: int)
```

選択されたスピーカーデバイスからの録音（ループバック）

### エネルギー監視クラス群

#### BaseEnergyRecorder クラス
```python
class BaseEnergyRecorder:
    def __init__(self, source: Any)
```

エネルギーレベル監視の基底クラス

#### SelectedMicEnergyRecorder クラス
```python
class SelectedMicEnergyRecorder(BaseEnergyRecorder):
    def __init__(self, device: dict)
```

マイクエネルギーレベルの監視

#### SelectedSpeakerEnergyRecorder クラス
```python
class SelectedSpeakerEnergyRecorder(BaseEnergyRecorder):
    def __init__(self, device: dict)
```

スピーカーエネルギーレベルの監視

### 統合録音クラス群

#### BaseEnergyAndAudioRecorder クラス
```python
class BaseEnergyAndAudioRecorder:
    def __init__(self, source: Any, energy_threshold: int, dynamic_energy_threshold: bool, 
                 phrase_time_limit: int, phrase_timeout: int, record_timeout: int)
```

音声録音とエネルギー監視を統合

#### SelectedMicEnergyAndAudioRecorder クラス
```python
class SelectedMicEnergyAndAudioRecorder(BaseEnergyAndAudioRecorder):
    def __init__(self, device: dict, energy_threshold: int, dynamic_energy_threshold: bool,
                 phrase_time_limit: int, phrase_timeout: int = 1, record_timeout: int = 5)
```

マイクの音声録音とエネルギー監視を統合

#### SelectedSpeakerEnergyAndAudioRecorder クラス
```python
class SelectedSpeakerEnergyAndAudioRecorder(BaseEnergyAndAudioRecorder):
    def __init__(self, device: dict, energy_threshold: int, dynamic_energy_threshold: bool,
                 phrase_time_limit: int, phrase_timeout: int = 1, record_timeout: int = 5)
```

スピーカーの音声録音とエネルギー監視を統合

## 主要メソッド

### 録音制御

```python
adjustForNoise() -> None
```
- 環境ノイズに合わせたしきい値調整
- 録音開始前の較正

```python
recordIntoQueue(audio_queue: Queue) -> None
```
- 音声データの継続的キューイング
- バックグラウンドスレッドでの実行

```python
pause() -> None
resume() -> None
stop() -> None
```
- 録音の一時停止・再開・停止制御

### エネルギー監視

```python
recordIntoQueue(energy_queue: Queue) -> None
```
- エネルギーレベルのキューイング
- リアルタイム監視データの提供

## 使用方法

### 基本的なマイク録音

```python
from queue import Queue
from models.transcription.transcription_recorder import SelectedMicRecorder

# デバイス設定
mic_device = {
    "name": "マイク (USB Audio Device)",
    "index": 0,
    "channels": 1,
    "sample_rate": 16000
}

# 録音設定
energy_threshold = 300
dynamic_threshold = True
record_timeout = 5

# レコーダー初期化
recorder = SelectedMicRecorder(
    device=mic_device,
    energy_threshold=energy_threshold,
    dynamic_energy_threshold=dynamic_threshold,
    record_timeout=record_timeout
)

# 音声キューの作成
audio_queue = Queue()

# 録音開始
recorder.adjustForNoise()  # ノイズ調整
recorder.recordIntoQueue(audio_queue)

# 音声データの取得
while True:
    if not audio_queue.empty():
        audio_data = audio_queue.get()
        print(f"音声データ受信: {len(audio_data)} bytes")
```

### スピーカー録音（ループバック）

```python
from models.transcription.transcription_recorder import SelectedSpeakerRecorder

# スピーカーデバイス設定
speaker_device = {
    "name": "スピーカー (USB Audio Device)",
    "index": 1,
    "channels": 2,
    "sample_rate": 44100
}

# スピーカーレコーダー
recorder = SelectedSpeakerRecorder(
    device=speaker_device,
    energy_threshold=500,
    dynamic_energy_threshold=False,
    record_timeout=3
)

audio_queue = Queue()
recorder.recordIntoQueue(audio_queue)
```

### エネルギー監視

```python
from models.transcription.transcription_recorder import SelectedMicEnergyRecorder

# エネルギー監視のみ
energy_recorder = SelectedMicEnergyRecorder(mic_device)
energy_queue = Queue()

energy_recorder.recordIntoQueue(energy_queue)

# エネルギーレベルの取得
while True:
    if not energy_queue.empty():
        energy_level = energy_queue.get()
        print(f"エネルギーレベル: {energy_level}")
```

### 統合録音（音声+エネルギー）

```python
from models.transcription.transcription_recorder import SelectedMicEnergyAndAudioRecorder

# 統合レコーダー
integrated_recorder = SelectedMicEnergyAndAudioRecorder(
    device=mic_device,
    energy_threshold=300,
    dynamic_energy_threshold=True,
    phrase_time_limit=5,     # フレーズ制限時間
    phrase_timeout=1,        # フレーズタイムアウト
    record_timeout=5         # 録音タイムアウト
)

audio_queue = Queue()
energy_queue = Queue()

# 両方のキューに同時出力
integrated_recorder.recordIntoQueue(audio_queue, energy_queue)
```

## 設定パラメータ

### しきい値設定
- **energy_threshold**: 音声検出のエネルギーしきい値
- **dynamic_energy_threshold**: 動的しきい値調整の有効・無効

### タイムアウト設定
- **record_timeout**: 録音継続時間の上限
- **phrase_timeout**: フレーズ間の無音許容時間
- **phrase_time_limit**: 単一フレーズの最大長

### デバイス設定
- **name**: デバイス名
- **index**: デバイスインデックス  
- **channels**: チャンネル数（1=モノラル、2=ステレオ）
- **sample_rate**: サンプリングレート（Hz）

## デバイス対応

### マイクデバイス
- USB マイク
- 内蔵マイク
- Bluetooth マイク
- 仮想マイクデバイス

### スピーカーデバイス（ループバック）
- USB スピーカー/ヘッドフォン
- 内蔵スピーカー
- Bluetooth スピーカー
- 仮想音声デバイス

## エラーハンドリング

### デバイスエラー
- デバイス接続失敗の検出
- 適切なエラーメッセージの提供

### 音声フォーマットエラー
- 非対応フォーマットの検出
- 自動フォーマット変換

### メモリエラー
- キューオーバーフローの防止
- メモリ使用量の最適化

## パフォーマンス特性

### レイテンシ
- 低レイテンシ録音（～10ms）
- リアルタイム処理最適化

### スループット
- 連続録音対応
- 高サンプリングレート対応

### メモリ使用量
- 効率的なバッファ管理
- キューサイズの最適化

## 依存関係

### 必須依存関係
- `speech_recognition`: 音声認識ライブラリ
- `pyaudiowpatch`: Windows音声システム統合
- `queue`: データキューイング

### オプション依存関係
- `datetime`: タイムスタンプ機能

## 注意事項

- Windows専用（pyaudiowpatchによる制限）
- 適切な音声デバイスドライバーが必要
- 排他制御による同時デバイスアクセス制限
- 高サンプリングレート使用時のCPU使用率上昇

## 関連モジュール

- `transcription_transcriber.py`: 音声認識エンジン
- `device_manager.py`: デバイス管理
- `config.py`: 録音設定管理
- `model.py`: 録音制御統合