## 文字起こしモジュール (models.transcription)

このドキュメントでは `models/transcription` に関する設計・セットアップ・使用例・テスト方針・トラブルシュートをまとめます。

### 概要
- `models/transcription` は音声入力をテキストに変換する機能を提供します。主に:
  - `transcription_recorder.py` — マイクやスピーカからの音声取得ラッパー
  - `transcription_transcriber.py` — 音声バッファを認識エンジンに渡して文字起こしを行うロジック
  - `transcription_whisper.py` — faster-whisper（WhisperModel）周りのダウンロード/ロード補助
  - `transcription_languages.py` — 各言語・国別のエンジン別コードマップ

### 最近の変更点
- 各モジュールに型注釈と docstring を追加しました。これによりメンテナンス性が向上します。
- `transcription_whisper.py` にダウンロード進捗コールバックを明記した実装を追加しました。

### 依存関係
主要な依存:
- `speech_recognition` — オーディオ録音と Google 音声認識のラッパー
- `pyaudiowpatch` — クロスプラットフォームのオーディオ設定
- `pydub` — 音声のチャンネル変換や処理
- `faster_whisper`（オプショナル）— ローカルで Whisper を使う場合
- `huggingface_hub`（オプショナル）— モデルアーティファクトのダウンロード

注意: `pydub` は `ffmpeg` が必要です。環境に ffmpeg が無いとワーニングが出ます。

推奨インストール（任意）:

```powershell
pip install speechrecognition pyaudiowpatch pydub faster-whisper huggingface-hub
```

テストでは多くの外部依存をモックするため、全てをインストールする必要はありません。

### 初回セットアップ
1. 必要に応じて `ffmpeg` をインストールしてください（pydub の動作に必要）。
2. Whisper ローカルモデルを使う場合、`transcription_whisper.downloadWhisperWeight(root, weight_type, callback, end_callback)` を呼んでモデルを取得します。
   - `callback(progress: float)` は 0.0〜1.0 の進捗通知です。
   - 例:

```python
from models.transcription import transcription_whisper as tw
tw.downloadWhisperWeight("./", "tiny", callback=lambda p: print(f"{p*100:.1f}%"), end_callback=lambda: print("done"))
```

### API 使用例
簡単な `AudioTranscriber` の使い方:

```python
from models.transcription.transcription_transcriber import AudioTranscriber

# source はライブラリが提供するオーディオソースオブジェクト
tr = AudioTranscriber(speaker=False, source=source, phrase_timeout=3, max_phrases=10, transcription_engine="Google")
# audio_queue は録音スレッドがプッシュするキュー
tr.transcribeAudioQueue(audio_queue, languages=["English"], countries=["United States"]) 
```

戻り値やエラー処理のルールについては各関数の docstring を参照してください。

### テスト方針
- `AudioTranscriber` と `Whisper` ラッパーはユニットテストでモック化して検証します。
- 推奨: `pytest` と `unittest.mock` を使い、以下のケースをカバーします:
  - 正常系: Google/Whisper の成功パス（モックで期待テキストを返す）
  - エッジ: 無音、低確信、複数言語
  - フォールバック: Whisper が利用不可の場合のフォールバック動作

### トラブルシュート
- ffmpeg が見つからない: `pydub` がワーニングを出します。OS に合わせて ffmpeg をインストールしてください。
- Whisper のロード時に VRAM エラー: `getWhisperModel` は VRAM 不足を検出して `ValueError("VRAM_OUT_OF_MEMORY", message)` を投げます。デバイス設定や compute_type を調整してください。
- ハッシュ不一致やダウンロード失敗: キャッシュや weights ディレクトリを削除して再ダウンロードしてください。

### 変更履歴
- 2025-10-09: 型注釈と docstring を追加、ダウンロード/コールバック仕様を明記。

---
このドキュメントは簡潔な参照用です。さらに詳細な実行手順（ログ収集方法、ffmpeg のインストール手順例など）が必要であれば追記します。
# transcription — 文字起こしモジュール
概要: マイク/スピーカー音声の録音と Whisper/Google などのエンジンを使った文字起こしを提供するモジュール群です。主なクラスは録音用の Recorder と `AudioTranscriber` です。

主要クラス/シグネチャ:
- SelectedMicEnergyAndAudioRecorder(device, energy_threshold, dynamic_energy_threshold, phrase_time_limit)
- SelectedSpeakerEnergyAndAudioRecorder(...)
- SelectedMicEnergyRecorder(device)
- SelectedSpeakerEnergyRecorder(device)
- AudioTranscriber(speaker: bool, source, phrase_timeout: int, max_phrases: int, transcription_engine: str, root: str, whisper_weight_type: str, device: str, device_index: int, compute_type: str)
  - transcribeAudioQueue(queue, languages:list, countries:list, avg_logprob: float, no_speech_prob: float) -> bool
  - getTranscript() -> dict

使用例:

```python
from models.transcription.transcription_recorder import SelectedMicEnergyAndAudioRecorder
from models.transcription.transcription_transcriber import AudioTranscriber

# 録音
rec = SelectedMicEnergyAndAudioRecorder(device, energy_threshold=300, dynamic_energy_threshold=False, phrase_time_limit=3)
queue = Queue()
rec.recordIntoQueue(queue, None)

# 文字起こし
transcriber = AudioTranscriber(speaker=False, source=rec.source, phrase_timeout=3, max_phrases=10, transcription_engine='Google', root='.', whisper_weight_type='base', device='cpu', device_index=0, compute_type='auto')
transcriber.transcribeAudioQueue(queue, ['Japanese'], ['Japan'], -0.8, 0.6)
print(transcriber.getTranscript())
```

注意点:
- Whisper のモデルロードは VRAM を消費します。`Model.detectVRAMError` のような検知と回復策が必要です。
- 録音は OS のデバイス依存のため `device_manager` でのデバイス取得と組み合わせて利用してください。

# models/transcription — 詳細設計

構成ファイル:
- transcription_recorder.py — 各デバイス向け Recorder クラス群（Base, SelectedMic*, SelectedSpeaker*）。speech_recognition をラップし、Audio / Energy をキューへ出す。
- transcription_transcriber.py — AudioTranscriber: Google Speech API または faster-whisper を使った音声→テキスト変換の実行ロジック。複数言語に対する最良候補選択と confidence に基づく選出。
- transcription_whisper.py — Whisper（faster-whisper）重みのダウンロードとモデル生成のユーティリティ。

主要契約:
- Recorder は recordIntoQueue(audio_queue, energy_queue) を提供し、バックグラウンドで音声データをキューに流す。
- AudioTranscriber.transcribeAudioQueue(audio_queue, languages, countries, avg_logprob, no_speech_prob) -> bool
  - audio_queue から音声を取り出し認識を試みる。結果は getTranscript() で取得する。常に True/False を返して呼び出し側がループ継続を制御。

VRAM エラー対策:
- Whisper のモデルロードで GPU メモリ不足が発生すると、ValueError("VRAM_OUT_OF_MEMORY", message) を投げる実装。Controller で捕捉して機能停止/通知する。

外部依存:
- speech_recognition, faster_whisper, pydub, numpy, torch

