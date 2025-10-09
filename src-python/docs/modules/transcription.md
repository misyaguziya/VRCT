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

