# VRCT native audio

Python向けのWindows x64拡張（`.pyd`）。デバイス・ネットワーク・認識モデルは所有せず、mono PCM16LEからのFLAC生成、VAD用downmix、非VAD speakerの多チャンネル変換、エネルギーに基づく発話区間判定を行う。デバイスI/Oとthreadの寿命はPythonが管理する。

## ビルド

Rust 1.83以上、Windows MSVC build tools、Python 3.10以上が必要。VRCTでの検証対象はPython 3.11。リポジトリのルートから実行する。

```powershell
.\.venv\Scripts\python.exe -m pip install --no-deps ./native/vrct-audio
.\.venv\Scripts\python.exe -c "import vrct_audio; print(vrct_audio.__file__)"
```

CPU/CUDAとも`bat/install.bat`と`bat/build*.bat`が拡張をビルド・導入する。maturinとRust依存は固定し、Cargo.lockを必須とする。wheelは`cp310-abi3-win_amd64`で、Pythonの安定ABIを使う。CPU/GPU推論の選択には依存しない。

`dev-fast`はvenv内の拡張を使用するため、初回とRustソース変更後は上記の`pip install`を実行する。Pythonファイルの変更だけならnative拡張の再ビルドは不要。

## 契約

- `encode_flac(pcm: bytes, sample_rate: int) -> bytes`: mono、16bit signed little-endian。8000〜96000Hz、非空、完全sample。外部FLACプロセスを起動しない。
- `downmix_pcm16(pcm: bytes, channels: int) -> bytes`: 1〜256ch、完全frame。平均をties-to-evenで丸める。VAD向けであり、speaker旧経路の2ch合算・飽和とは区別する。
- `normalize_pcm16(pcm: bytes, sample_width: int, channels: int) -> bytes`: signed PCM8/16/24/32LEをPCM16へ変換後、1〜256chをties-to-evenの平均でmonoにする。8bitもsigned。完全sampleが必要で、端数channel frameは破棄する。入力・出力それぞれ64MiB以下、空入力可。mono PCM16は元のimmutable bytesを返し、それ以外は入力bytesを借用し、GILを解放してRust所有の出力bufferへ変換する。整数幅変換にはMITを選択した`dasp_sample =0.11.0`（追加依存なし）を使う。
- VAD normalizerのレート変換と状態/resetは既存`audioop.ratecv`を維持する。非bytes・非標準形式・不完全sample・大入力は従来経路で処理し、幅変換後のinterleaved PCM16に対する旧downmixの64MiB制限も保持する。
- `speaker_downmix_pcm16(pcm: bytes, channels: int) -> bytes`: 非VAD speaker向けPCM16LE、3〜256ch、完全frame、空入力可、入力上限64MiB。pydub 0.25.1と同じく各channelを床除算して順に加算し、途中でもi16範囲を超えればOverflowError。VAD平均・stereo合算とは別の契約。対象外の形式・サイズと拡張未導入時は既存pydubへ戻る。
- `EnergyDetector`: 既存forkの音量閾値・発話開始終了・前後保持・短発話棄却・timeoutを状態機械として処理する。listenerは各read前に`before_read()`、read後に`push()`を呼ぶ。無制限録音時も音声bufferを無制限に拡大しない。forkとの意図的な差は2点: 録音中のwall-clock `record_timeout`は発話を捨てず短発話判定を通して`PHRASE`として返す。`phrase_time_limit`/`record_timeout`で分割した直後（無音が`pause_threshold`以内）に始まる続きの発話は短発話として棄却しない。
- 入力上限64MiBを処理前に検証。これは総メモリ上限ではない。FLAC生成・downmix・正規化中はGILを解放し、参照元を保持したimmutable `PyBytes`のsliceだけを借用する。入力コピーを省き、出力は引き続きRustが所有する。Python API・mutable bufferには触れない。[固定PyO3 0.24.2のbytes契約](https://github.com/PyO3/pyo3/blob/v0.24.2/src/types/bytes.rs)に従い、同期呼出し終了まで入力を保持する。エネルギー判定の短いchunk処理はGILを保持する。
- FLACは単一thread、LPC次数4で可逆圧縮する。次数10の既定値より計算量を抑え、LPCを無効にする案より出力サイズを維持する。圧縮率と時間は入力によって変わる。
- 録音と8000〜96000HzのGoogle FLACにはnative拡張が必須。未導入時は導入案内を含むImportError、壊れたDLLや実行エラーも明示する。SpeechRecognitionパッケージは不要。normalizerと対象外speaker変換の既存fallbackは維持する。
- 96000Hzを超えるFLACは既存依存PyAV 18.1.0でmono PCM16を小分けencodeし、flush/closeする。元レートを維持し、旧encoder同様655350Hz以下かつ10の倍数のみ許容。非空・完全sample・64MiB以下を共通検証する（高rate上限64MiBは追加の安全制約）。旧外部プロセスの10秒timeoutは廃止され、in-process処理となる。
- 録音デバイスはPythonの`AudioCaptureSource`とPyAudioWPatchが所有し、既存ロックでopen/close/stopを直列化する。明示sample rateでのsource生成はPyAudioを初期化しない。listenerは自前PythonとRustの状態機械を使用する。
- provider側の`PcmAudio`は1発話内の言語候補間で16kHz/16bit monoのraw/WAVだけを遅延再利用する。最大2つのimmutable bytesで、引数の検証・変換順序・元PCMを保持する。その他のrate/widthは都度変換する。Whisperには毎回独立したfloat32配列を渡す。これはPythonでの変換重複・コピー削減であり、Google FLACやfloat配列はキャッシュしない。

## 検証

```powershell
cargo test --locked --manifest-path native/vrct-audio/Cargo.toml
cargo clippy --locked --manifest-path native/vrct-audio/Cargo.toml --all-targets -- -D warnings
cargo fmt --manifest-path native/vrct-audio/Cargo.toml -- --check
.\.venv\Scripts\python.exe -m pytest -q src-python/test/test_native_audio.py src-python/test/test_pcm_audio.py src-python/test/test_google_speech.py src-python/test/test_audio_source.py src-python/test/test_audio_listener.py src-python/test/test_transcription_recorder.py src-python/test/test_audio_vad.py
.\.venv\Scripts\python.exe tools/benchmark_audio_native.py --output tmp/audio-benchmark.json
.\.venv\Scripts\python.exe tools/benchmark_audio_native.py --suite speaker --output tmp/speaker-benchmark.json
.\.venv\Scripts\python.exe -m pytest -q src-python/test/test_audio_normalizer.py
.\.venv\Scripts\python.exe -m pytest -q src-python/test/test_native_audio_buffers.py
.\.venv\Scripts\python.exe tools/benchmark_audio_normalizer.py --output tmp/normalizer-benchmark.json
.\.venv\Scripts\python.exe tools/benchmark_audio_preparation.py --output tmp/preparation-benchmark.json
```

nativeテストには拡張の導入が必要。未導入時のskipを成功と扱わない。FLACの正しさはPyAVで復号したsample・rate・channelの一致で確認する。ベンチは固定seedの合成音でPythonとのコピーも含めて測定する。FLAC/energyは現行native単独、normalizer/speakerは代替実装と順序を交互にして比較する。実Google応答や発話終了から画面表示までの速度を測るものではない。

保存済みの旧・新DLLは`tools/benchmark_audio_buffers.py --baseline-pyd <旧.pyd> --candidate-pyd <新.pyd> --output <結果.json>`で比較できる。同じprocessで38条件を交互に測り、返却bytesの一致とDLL hashを記録する。入力借用で省く一時割当は入力長と同じであり、process全体のピークメモリ削減量ではない。FLAC圧縮や通常チャンクを含め、全条件で速度が改善するとは限らない。

次の実機チェックはWindows既定マイクと既定出力のWASAPIループバックを開く。`benchmark`は現行constructorとprobeのopen/closeを測定し、`lifecycle`は短時間録音して同時停止・再開始を確認する。音声は保存・外部送信せず、JSONには設定・件数・時間・ソースhashだけを残す。子processは90秒で打ち切る。別デバイスへのfallbackは失敗とし、物理的な切断・再接続と認識品質は確認しない。

```powershell
.\.venv\Scripts\python.exe tools/check_audio_capture.py benchmark --output tmp/capture-benchmark.json
.\.venv\Scripts\python.exe tools/check_audio_capture.py lifecycle --output tmp/capture-lifecycle.json
```

物理的な切断・再接続は対話式の`hotplug`で確認する。選んだマイク(USBヘッドセット)を本番のRecorderで開き、コンソールの案内に従ってWindows既定デバイスの切替、抜去、再接続を行う。各段階のcallback件数、`device_error_info`のcode/stage、抜去からエラー検知までの時間、`stop()`が15秒(`TRANSCRIPT_STOP_JOIN_TIMEOUT`相当)内に戻ったか、再接続後に名前で再解決したデバイスを開けたかを記録する。音声とデバイス名は保存しない。各案内と待機は`--step-timeout`秒(既定120)で打ち切り、Ctrl+Cでも録音を止めてから途中結果を出す。Recorder層だけの確認で、Auto Mic Selectによる再選択や画面通知は含まない。`--vad`でVAD Recorder、`--speaker`で既定出力のループバックも同時に観測する。

```powershell
$env:PYTHONPATH="$PWD\tmp\native-site;$PWD\src-python"
.\.venv\Scripts\python.exe tools/check_audio_capture.py hotplug --output tmp/capture-hotplug.json
```

録音I/Oは当面PyAudioWPatchを維持する。固定依存0.2.12.6はC/PortAudioで録音し、read/open/初期化等ではGILを解放する。単に呼び出し元をRustへ変えてもOS側の待機や初期化は残る。常駐instanceによる初期化省略はデバイス再検出に影響するため、性能だけで採用しない。根拠と残る条件は`progress.md`のサイクル3Dを参照。

次の手動モードはRust拡張なしで動き、デバイス一覧更新を9回測定する。録音streamのopenは禁止し、デバイス名や音声は保存しない。初回importの列挙は時間に含めず、同じworkerに既存streamがない状態の初期化・終了・その他の所要時間とAPI呼び出し数を記録する。「その他」には計装負荷を含む。デバイス構成の変化や列挙エラーがあれば失敗として終了する。

```powershell
.\.venv\Scripts\python.exe tools/check_audio_capture.py enumeration --output tmp/audio-enumeration.json
```

ライセンスは`LICENSE`、`THIRD_PARTY_LICENSES.txt`、`SPEECH_RECOGNITION_LICENSE.txt`に同梱。エネルギー判定の互換実装とPython listenerはSpeechRecognition forkのBSD-3-Clause通知を保持する。依存更新時にはCargo.lockと第三者ライセンス集を一緒に更新する。

RustのAPI変更後はrelease wheelを再ビルド・再導入する。古いwheelのsymbol欠落やnative実行エラーはfallbackで隠さず報告する。speaker suiteは48kHzの3/15秒・3/6/8chをpydub、NumPy、実際のRust呼び出し経路で比較し、PCM一致・全試行時間・ソースとバイナリのhashを保存する。conversion/energyは現行native単独の計測。旧実装との比較は過去の保存結果であり、現行ツールでは再実行しない。
