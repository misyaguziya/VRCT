# 文字起こし品質評価

同じWAVファイルを使い、CER、WER、処理時間、発話終了後遅延、実時間係数を比較します。

1. `test_data/transcription_manifest.example.json`を複製します。
2. `test_data/audio`へWAVを配置し、`audio`と`reference`を設定します。
3. `src-python`ディレクトリで評価を実行します。

```powershell
python evaluate_transcription.py test_data/transcription_manifest.json --model weights/whisper/base --output evaluation.json
```

異なるモデルや設定で同じmanifestを実行し、出力JSONの`summary`と各`results`を比較してください。`real_time_factor`が1未満なら、音声の実時間より短く処理できています。