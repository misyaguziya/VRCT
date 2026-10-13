# VRCT native audio

Rust のバックエンド (`vrct-backend`) が使う音声処理のライブラリ。mono PCM16LE からの FLAC 生成、
VAD 用の downmix、非 VAD の speaker の多チャンネル変換、PCM の正規化、エネルギーに基づく発話区間
判定、`audioop` の互換処理、Silero VAD の区切りを持つ。`devices` 機能で録音デバイス (cpal の WASAPI、
既定デバイスの追跡) も持つ。

## 契約

- `encode_flac(pcm, sample_rate)`: mono、16bit signed little-endian。8000〜96000Hz、非空、完全 sample。外部 FLAC プロセスを起動しない。単一 thread、LPC 次数 4 で可逆圧縮する。
- `downmix_pcm16(pcm, channels)`: 1〜256ch、完全 frame。平均を ties-to-even で丸める。VAD 向け。
- `normalize_pcm16(pcm, sample_width, channels)`: signed PCM8/16/24/32LE を PCM16 へ変換後、1〜256ch を ties-to-even の平均で mono にする。完全 sample が必要で、端数 channel frame は捨てる。
- `speaker_downmix_pcm16(pcm, channels)`: 非 VAD speaker 向け PCM16LE、3〜256ch、完全 frame。pydub 0.25.1 と同じく各 channel を床除算して順に加算し、途中で i16 の範囲を超えればエラー。
- `EnergyDetector`: SpeechRecognition fork の音量閾値・発話開始終了・前後保持・短発話棄却・timeout の状態機械。fork との意図的な差は 2 点: 録音中の `record_timeout` は発話を捨てず短発話判定を通して `PHRASE` として返す。`phrase_time_limit` / `record_timeout` で分割した直後 (無音が `pause_threshold` 以内) に始まる続きの発話は短発話として棄却しない。
- 入力の上限は 64MiB (処理の前に検証する。総メモリの上限ではない)。

## 検証

```powershell
cd native
cargo test -p vrct-audio --all-features
cargo clippy -p vrct-audio --all-targets --all-features -- -D warnings
```

ライセンスは `LICENSE` と `SPEECH_RECOGNITION_LICENSE.txt`。エネルギー判定の互換実装は SpeechRecognition fork の BSD-3-Clause 通知を保持する。依存しているクレートの表記は `native/vrct-backend/THIRD_PARTY_LICENSES.txt` に入る。
