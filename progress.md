# Rust音声処理への段階移行

## 中間チェックポイント（2026-10-08）

ユーザーの依頼により、サイクル1〜9をローカルコミット`b9be99e7`に保存済み。基準はdevelopの`e1c24d1b`、保存先は`codex/rust-audio-pipeline`。今回、サイクル10〜12の検証結果とインストール修正、およびサイクル13の起動競合修正を追加チェックポイントとして保存する。developへのマージとpushは未実施。過去の「未commit」は作業当時の記録。Claude Codeへの引継ぎは`docs/claude_code_handoff_2026-10-08.md`を最初に読む。

| 対象 | 現在の状態 |
|---|---|
| 音声の計算処理 | PCM幅変換、モノラル化、RMS/発話区間判定、通常レートのFLACをRust拡張`.pyd`へ移行。入力コピーも削減 |
| 音声のI/O・制御 | Google通信を独立Python clientへ分離。録音source/listenerは自前実装。`custom_speech_recognition`依存は除去 |
| 維持する音声基盤 | PyAudioWPatchのデバイスI/O、Whisper/CTranslate2・Sileroの推論、`audioop.ratecv`のレート変換を維持。高レートFLACはPyAV |
| 認識前処理 | 同一発話の候補言語間で16kHz/16bitのraw/WAVを再利用し、Whisper用配列の不要コピーを削減 |
| OCR | D3D画素変換とdetector入力整形のコピーを削減。再学習モデル・認識処理は維持 |
| Overlay | 起動演出の透過処理を既存OpenCVで高速化。描画基盤のRust化・GPU直接提出は未実施 |
| ビルド・配布 | CPU/CUDAのinstall/build経路にRust wheel構築・同梱・ライセンス通知を追加。最新ソースから拡張を再ビルドする必要あり |

### 検証済みの範囲

- 最新の音声実装はCPU/CUDAそれぞれ667件＋3 subtests、Rust13件、clippy/fmt、独立設計・実装レビューを通過。旧SR import禁止、skip 0。
- OCRは最新モデルに対し129画像で前処理・出力・切り出しの一致を確認。Overlayは画素互換テストと合成入力の性能比較を実施。各結果と条件は下のサイクル4/5の記録を参照。
- 最新9のDLLを含むCPU/CUDA全sidecarを10/11で再ビルド。11で余剰OpenCV DLLの収集を解消。11のfrozen起動ではCPUのコールバック登録失敗が判明し、13で修正。13は単体回帰と限定exe smokeまで成功し、修正後のfrozen起動・配布物の最終照合は未完了。
- 実Whisper baseのローカル合成音認識はCPU/CUDA各2回成功。通常GUIとの結合や配布exe内の実モデル推論は未検証。起動競合の関連テストはCPU/CUDA各24件＋2 subtests成功。
- 最新DLLで既定マイクとループバックの開始・停止・再開始をCPU/CUDA各3回確認。隔離設定と通信・録音ガード付きのsource起動では、初期化・version/compute_modeのIPC・終了が両方成功。物理切断やendpoint切替は未実行。
- ベンチマークは処理単位の比較。通常の短い音声やFLACを含め全条件で高速化したわけではなく、発話終了から画面表示までの改善率は未測定。詳細は`docs/benchmarks/`に保存。

### 次に進める順序

1. サイクル13の修正後配布物を照合し、ガード付きfrozen起動を再実行する。その後、通常GUIと配布版ローカルモデル推論の結合を確認する。限定exeテストとsource実推論を全アプリ確認として扱わない。
2. endpoint切替・切断再接続・無データが続く状態の停止、実認識までの時間を実機で確認する。通常のマイク/ループバックの開始・停止・再開始はサイクル10で確認済み。
3. 全体計測で残る重い箇所を選び、次のRust化を判断する。PyAudio置換・OCR認識器の置換・OverlayのGPU直接提出は、それぞれ効果と互換性を確認してから設計する。

コミット対象はソース・テスト・ライセンス・手順・計測JSON。`tmp/`の実行ログ、wheel/DLL、ビルド出力、録音や画像データは含めない。

前回`b9be99e7`のコミット前監査はLGTM。検証時のソース・ベンチ・ログhashを再照合し一致。前回は実装変更がなかったためテストを再実行していない。前回staged diffの空白検査は第三者通知の末尾空行1件のみを例外として保持し、それ以外はPASS。通知を検証済みwheelとbyte単位で一致させるためであり、ライセンス本文の変更はない。

## 基準と完了条件

- 2026-10-07、ユーザーがdevelop更新後の設計レビュー・実装・検証・実装レビューの反復を依頼。
- 開始時の`git fetch origin develop`後の基準: `307dd79615f5529f03a411961b215b3863feecbd`。
- 2026-10-08の継続基準: 再fetch後の`e1c24d1b0434e562a02bd4f00106e8bd3974f789`。最新モデル・版更新等をfast-forwardで取り込み、従来の未commit変更を保全した（サイクル5参照）。
- 作業ブランチ: `codex/rust-audio-pipeline`。2026-10-08のユーザー依頼でローカルcommitを許可。pushは未依頼。
- 最初の単位: 共通PCM型とGoogle認識の独立。続いてWindows向けRust拡張でPCM/FLAC処理を置き換える。
- Whisper/CTranslate2、Silero推論、録音デバイスの既存動作を維持し、互換性試験と実測で採用を判断する。
- 参考設計: `docs/rust_backend_migration_plan_2026-10-07.md`。音声経路を優先し、overlay/OCR移行は別の変更単位とする。

## サイクル1 — PCM境界とGoogle分離

- 設計レビュー: LGTM。mono入力、speaker 2chの合算・飽和と多chのpydub変換、Googleの複数結果結合を維持。
- 実装済: `pcm_audio.py`、`google_speech.py`、provider/transcriberと対応試験。独立実装レビューLGTM。
- 着手前検証: 既存のprovider/transcriber/VAD/recorder試験145件PASS。
- 試験環境: 既存メインcheckoutのCPU venvを読み取り利用。パッケージ変更は作業用ディレクトリに限定。

## サイクル2 — Rust PCM/FLAC

- 実装済: PyO3 0.24.2 / flacenc 0.5.1のWindows x64 abi3拡張。FLAC生成とVADの多ch平均化を移行。独立設計・実装レビューともLGTM。
- Native有効の関連13スイート350件PASS、未導入fallback関連6スイート192件PASS、Rust 6件PASS、clippy/fmt/変更Pythonのruff PASS。
- release wheelとPEP517 wheelビルドPASS。CPU/CUDA両venvでnative import/encode、両環境から作ったPyInstaller最小exeの実行PASS。全sidecarのbuild・実機認識は別条件。
- 合成音9回の交互比較でFLAC生成16kHz/3秒は11.48→1.58ms、48kHz/15秒は34.62→27.47ms。32ms VAD前処理48kHz/2chは0.0563→0.0231ms。
- LPC既定値は長尺で遅く、無効化は出力が増えたため、次数4を採用。実測は端末処理だけであり通信・推論・UIを含まない。
- 計測のJSON: `docs/benchmarks/rust_audio_2026-10-07.json`（CPU、基準commit、ソースhash、3設定の時間・出力サイズを記録）。
- Google通信・推論時間と端末側変換時間を分けて測る。FLACは復号後PCM一致を品質条件とする。

## サイクル3A — エネルギー区間検出とlistener

- 実装済。独立設計レビュー、実装レビュー、性能調整後の追加レビューともLGTM。
- SR MicrophoneとPyAudioWPatchのデバイスI/O・lock・read解除を維持し、custom forkのエネルギー区間処理をRust状態機械へ、自前Python listenerから接続した。
- 音量閾値、前後の保持、短い発話の破棄を維持。音声時間によるphrase上限は出力、実時間のrecord timeoutは破棄という違いも互換テストした。
- VADが一度に返す複数segmentの全件配送、pause中の停止、停止時flushを検証。推論モデルやVAD segmenter自体は変更しない。
- Native有効の関連16スイート412件PASS（skipなし）。最後のRMS最適化では境界6件を追加し、listener/recorder/VADの109件を独立再実行してPASS（skipなし）。未導入fallback 192件PASS。Rust 9件、clippy/fmt/変更Pythonのruff PASS。
- 発話bufferの結合をbulk copyへ変更。RMSは平方和が2^53以下と保証できる入力16MiB以内だけ整数化し、これを超える入力は元のf64計算を維持。境界前後と最大振幅・混在入力でaudioopと一致。
- 合成音3秒phraseの同期処理を9回交互・各300回測定。16kHz mono 0.211→0.067ms、48kHz mono 0.633→0.191ms、48kHz stereo 1.214→0.899ms。PCMとread回数の一致を計測前に確認。録音待ち・thread scheduling・推論・通信・UIは含まない。
- 計測のJSON: `docs/benchmarks/rust_audio_energy_2026-10-07.json`。ソースに加えて実際に読み込んだnative binaryと旧SpeechRecognitionソースのSHA256を記録。CPU/環境はサイクル2と同じ。
- 最終PEP517 wheelビルドとCPU/CUDA両venvでのFLAC/downmix/RMS/EnergyDetector/listener読込PASS。wheel内の本体・依存・SpeechRecognitionライセンス通知も検査済み。
- 最終wheelをCPU/CUDAそれぞれのPyInstallerで最小entrypointに同梱し、両exeで上記API・native listener選択・ライセンス配置を確認してPASS。PYTHONPATHを空にして実行した。PyInstallerの既存依存に関するhidden import警告は残るため、全sidecarの検証とは区別する。
- 最終wheel SHA256: `0ffc4c97bf6b98e7f53fc18486bc06334ed49c9fddb1ffdbd699daf28de1b882`。native binary SHA256: `b6442f6b65ba3437a3a635c6b1f6c3df0963f772d450f676dc7a2ca438709ca8`（ベンチと一致）。

## サイクル3B — 録音ソースの独立と準備処理の短縮

- 自前`AudioCaptureSource`へ接続し、録音のnative経路からSR Microphone/AudioSource依存を除去。PyAudioWPatch、デバイス選択、既存lock、read解除、probe timeoutを維持。Rustの区間判定へPCMを渡す境界を独立させた。
- 明示rateのsource生成時はPyAudioを作らず、probeの同一instanceでindex上限確認とopenを行う。正常なconstructor＋probeのPyAudio生成は2回から1回へ削減。rate未指定時は従来同様にdefault INPUTのrateを取得する。
- legacy listenerは必要時だけSRをimportし、自前sourceを互換adapterへ渡す。adapterのwithはselfを返し、ambient calibrationは二重openしない。pause中stopで待ち続ける既存forkの挙動はresume→stopで解消。
- 設計レビューLGTM。実装レビューでconstructor/exitの二重失敗時に元例外を失う指摘を修正し再レビューLGTM。cleanupは必ず試行し、本体→close→terminateの順で元例外を保持する。
- native関連10スイート390件PASS、未導入関連7スイート181件PASS/57件native限定skip。最終修正後はsource/listener/recorder128件PASS、fallback source/recorder71件PASS/4件native限定skip。skipは成功と区別する。
- 独立検証: 修正前の関連6スイート167件PASS/skipなし、最終修正後のsource43＋recorder32＝75件PASS/skipなし。ruff・差分検査PASS。Rust本体は3Aから変更していない。
- 実機: 既定mic（MME/44.1kHz/mono）と既定出力のWASAPI loopback（48kHz/stereo）で、同時開始・停止・再開始を3回確認。pause要求を含む。選択index/rate/channel一致を検査し、別デバイスへのfallbackは成功扱いしない。両方のmeter入力、停止後stream/audio=None、device errorなしを確認。音声の保存・外部送信・文字起こしは行わない。
- `tools/check_audio_capture.py`に90秒の子process watchdog付き再現手順を保存。実機検証結果は`docs/benchmarks/audio_capture_lifecycle_2026-10-07.json`（ソース/native binary hash付き）。実機check自体も独立レビューLGTM。
- 最終実機比較: constructor＋probeの中央値はmic 173.80→90.17ms、loopback 157.88→82.43ms。7回交互測定の全試行でPyAudio生成2→1を確認。`docs/benchmarks/audio_capture_startup_2026-10-07.json`に各試行値・ソースhashを保存。CPU sidecarビルド並行中の1台での参考値で、録音中の認識やアプリ全体の起動時間の短縮率ではない。
- 全sidecarのCPU/CUDA配布buildと凍結exe検査が両方PASS（build/smokeともexit 0）。CPUは約645秒・1,231,881,956 bytes/3,186 files、CUDAは約963秒・3,081,456,486 bytes/3,197 files。両版のRust binary SHA256は最終wheelの`b6442f6b65ba3437a3a635c6b1f6c3df0963f772d450f676dc7a2ca438709ca8`と一致。CUDA版はcuBLAS/cuDNN DLL 11本の同梱も確認。
- 配布検証では共有venvを変更せず、task内の隔離spec/出力/cacheを使った。専用runtime hookでnative 4 API、NativeAudioListener選択、PyAudio生成禁止mock下の明示rate AudioCaptureSource構築、同梱資産を確認して終了。controller初期化・外部engine check・GPU推論は実行しない。修正前CPUビルドは途中で中止し、確定版をfresh workpathで再構築済み。成果物は`tmp/sidecar-3b/dist-final-{cpu,cuda}`、ログは`tmp/sidecar-3b/build-final-{cpu,cuda}.log`と`tmp/sidecar-3b/smoke-final-{cpu,cuda}.log`。
- 配布検証の既存制約: 元specの`models.transcription.audio_pipeline` hidden importは存在しないためPyInstallerに非致命ERRORが出るが、現行ソースからの参照はない。任意の公式CI用`telemetry_keys`もローカルに存在しない。tzdata/pycparser生成テーブル等のmissing警告あり。glfw3.dllの探索警告はあるがdatas経由の同梱実在を確認した。公式CIや全アプリ起動の成功とは区別する。
- release workflowは`npm run setup-python`と`release-all`経由で既存batを呼ぶため、今回追加したnative拡張のビルド・導入経路を通ることをコードで確認。CIの実行・公開は行っていない。

## サイクル3C — 非VAD speakerの多チャンネル変換

- 実装済み、独立設計・実装レビューLGTM。録音I/O置換より先に、サンプル数×チャンネル数のPythonループが残るpydub変換を対象にした。PyAudioWPatchの置換はhost列挙・保存済みデバイス選択・停止契約まで変わるため、今回の範囲に含めない。
- `speaker_downmix_pcm16`を既存拡張へ追加。PCM16LE・3〜256ch・完全frame・64MiB以内だけnativeへ渡し、空入力も受け付ける。対象外の形式・サイズとnative未導入時は既存処理を維持。mono、stereoの合算・飽和、VAD用平均化は変更しない。
- [pydub 0.25.1の実装](https://github.com/jiaaro/pydub/blob/v0.25.1/pydub/audio_segment.py)に合わせ、各チャンネルを床除算してからchannel順に加算。各段でi16範囲を検査し、途中で範囲外になれば旧処理と同じOverflowError。単純な平均や最終結果のclipへ変更しない。コピー前に入力を検証し、GIL解放中はRust所有bufferだけを処理する。
- pydubを独立oracleに、負数の端数・極値・ランダム入力・空入力・不完全frame・各境界を比較。254chの途中overflow後に最終和が範囲内へ戻る入力も検証。native失敗や旧wheelの新symbol欠落はfallbackで隠さない。Rust変更後はwheelの再ビルド・再導入が必要。
- 実装者検証: native/PCM関連180件PASS、Rust 10件PASS、clippy/fmt/変更Python4ファイルruff PASS。独立検証はnative/PCM/transcriber/providers/Google/integrationの6スイート295件PASS、native未導入のPCM/transcriber/providers/Googleの4スイート146件PASS（両方skipなし・exit 0）。
- 固定seed合成PCM16・48kHzを9回交互測定し、全6条件で出力PCM完全一致。3秒の3/6/8chは旧75.48/152.65/203.20ms→Rust 1.68/2.83/4.09ms、15秒は旧376.69/767.68/1180.08ms→Rust 8.93/15.71/22.85ms。既存NumPyでの代替も比較し、15秒の3/6/8chは38.68/69.51/102.80msだった。
- 新経路の時間には本番`processSpeakerData`のdispatch、入力コピー、戻り値生成を含む。ビルド・テストを止めて最終測定。`docs/benchmarks/rust_audio_speaker_2026-10-07.json`に各試行・環境・ソース/pydub/native binary hashを保存し、現行hash一致を確認。非VAD・多chの変換だけの結果で、通常のステレオや認識/通信/UI全体の改善率ではない。
- pydub MIT通知を`THIRD_PARTY_LICENSES.txt`へ追加し、wheel内の同梱を独立レビューで確認。依存追加や配布specの変更はない。
- 新wheelは`tmp/cycle3c-wheels/vrct_audio-0.1.0-cp310-abi3-win_amd64.whl`（SHA256 `91f8826b1dcffd8a3251413d1739000577457549bf1ce61f533f1d6c66673cb3`）、native binaryは`tmp/cycle3c-native-site/vrct_audio/vrct_audio.pyd`（SHA256 `2d38d52f4172aa420e562b8e14abdf302d1c197452e712df1d1abe44d6e248b7`）。3Bの配布物と旧wheelは上書きしていない。
- CPU/CUDA両venvの直接smokeで新APIの床丸め/OverflowError、既存4 API、実transcriberからのnative呼び出しを確認。両環境で作成した最小PyInstaller exeもbuild/実行exit 0、PYTHONPATH除去後にPASS。両exeのnative binary hashが新版wheelと一致し、pydub MIT通知同梱も確認。検証用specの相対dataパスで初回freezeは失敗し、絶対パスへ修正して成功した。アプリソース・共有venvへの変更なし。
- 検証ログは`tmp/cycle3c-validation-{native,fallback}.log`、`tmp/cycle3c-build-{cpu,cuda}.log`、smoke再現scriptは`tmp/cycle3c-direct.py`と`tmp/cycle3c-smoke.py`。依存・配布spec・録音I/Oを変えていないため、3Cでは限定exeで新DLLを確認し、全sidecar再ビルドと実機録音は繰り返していない。3Bの全sidecar成功を新版binaryの結果として扱わない。GPU推論・外部認識APIも未実行。

## サイクル3D — PyAudio境界の固定版調査と実測

- 2026-10-08、ユーザーの「pyaudio周りはそのままでいいんですか？」を受け、固定依存と実機の初期化/列挙時間を確認。本番のPyAudioWPatch・DeviceManager・Rust音声処理は維持する設計に独立レビューLGTM。今回の成果は判断根拠と手動計測手段であり、新しい高速化を達成したサイクルではない。
- PyAudioWPatch 0.2.12.6の公式tagはcommit `7f0ff6ccc76b55ba1eb22a5c76ef97d8b7f48fee`。[固定版Cソース](https://github.com/s0d3s/PyAudioWPatch/blob/7f0ff6ccc76b55ba1eb22a5c76ef97d8b7f48fee/src/_portaudiomodule.c#L2180)で、read/open/start/stop/close/initialize/terminateのPortAudio呼び出し中にGILを解放することを確認。blocking readは返却用PyBytesを先に確保し、その領域へ直接書き込む。毎readのbytes確保とPortAudio内部の転送は残るが、一時C bufferから返却bytesへ追加copyする構成ではない。
- [公式PyPI release metadata](https://pypi.org/pypi/PyAudioWPatch/0.2.12.6/json)のcp311-win_amd64 wheel SHA256は`ff9642f32d6cc9fb183c88f36a9a34d8a7f0434dd96022ec7d235732c07c2188`。インストール済みCPUvenvのC拡張と公式wheel内拡張のSHA256は`6df6fafc7e446c6b663710829ec80c30bfe253f8d5a820b542ce35710a4f385d`で一致。Python wrapperはwheelとbyte一致、tagとの差は改行のみ。tagからの再現ビルド・binary逆解析は行っていないため、Cの挙動は対応する固定tagでの確認として扱う。
- [固定版PortAudio lifecycle](https://github.com/s0d3s/PyAudioWPatch/blob/7f0ff6ccc76b55ba1eb22a5c76ef97d8b7f48fee/portaudio_v19/src/common/pa_front.c#L352)はglobal参照数が0→1のときにhostを初期化する。既存instanceがある間の追加PyAudio()は参照数を増やすだけなので、「PyAudio()ごとにOS全デバイスを再列挙」とは言えない。instance常駐化は初期化費用を省けてもデバイス再検出の契約に影響し、現行のhotplug/録音停止と切り離して変更しない。
- `tools/check_audio_capture.py enumeration --output <path>`を追加。既存90秒子process watchdogを利用し、録音openを禁止。import時の初回列挙後、同workerに録音streamがない条件でupdateを9回計測。API呼出し数、初期化・終了・各試行の残余時間、固定版C拡張とソースhashを保存する。snapshotはhashのみで構成変化を検出し、デバイス名や音声を保存しない。
- generator反復中/通常メソッドの失敗や内部で握り潰されたopen、errorLoggingを計測失敗として検出し、patchを必ず復元。新規offlineテスト6件＋既存DeviceManager 9件を独立実行して15件PASS（skipなし）。独立実装レビューLGTM、既存検証用ruff 0.14.4の2ファイルcheckと差分検査PASS。追加で試したglobal ruff 0.16.4は有効ルール群が異なり、既存行と同期closure/意図的例外模擬を含む16件の指摘を返した。ソースを変えず指定版で再確認し、別設定の結果は`tmp/cycle3d/ruff.log`へ保持。
- CPUvenvの最終9回中央値はupdate 80.8562ms、initialize 79.7433ms、terminate 0.0984ms、その他0.6339ms。CUDAvenvは83.2188/82.5869/0.0846/0.5934ms。各試行でtotal-init-terminateを計算してから残余の中央値を求めており、各成分の中央値を足してtotal中央値になるとは限らない。計装負荷を含むので残余を純粋なPython実行時間とは呼ばない。GPU推論は使わない。
- 全試行で初期化/終了各1回。device info 305回・loopback generator 12回などの重複はあるが、この端末での残余時間は小さい。先読みlist化は列挙途中失敗時の部分結果や既定speakerの再試行を変えるため、現段階では本番変更しない。予備測定約94msとの差を高速化成果とは扱わない。
- CPU/CUDA両CLI実行PASS、native拡張なしでも動作。全trialの計算/中央値・source/C拡張hash・snapshot安定を独立確認。最終結果を`docs/benchmarks/pyaudio_enumeration_2026-10-08.json`に保存。録音中の列挙、物理的な抜き差し、停止上限の保証は今回測っていない。RustによるI/O置換を再検討するなら、録音からPCM処理までをまとめて境界往復を減らす案と、MME/DirectSound/WASAPI・loopback・デバイス変更/停止契約を一緒に検証する。

## サイクル4A — OCRの画素変換とコピー削減

- 2026-10-08、既存OpenCVのnative処理でD3D mirrorからBGRを直接生成し、OCR入力のRGB→BGR往復コピーを除去。Rust DLLを追加せず、実測で目的を満たす小変更を採用。モデル・推論・閾値・COM資源の寿命は維持。
- `D3D11Mirror.read(*, color_order="RGB")`の既定RGBはstandaloneツール互換のため維持し、OCR呼び出しだけBGRを指定。typed DXGI 28/29/87/91、行padding、上下順、alpha除去を検証。sRGB値のgamma変換は加えない。
- `ct.string_at`の所有コピーを残し、null pointer・寸法・pitchの検証を参照前に実施。Map成功後は検証/変換失敗でもUnmap。cv2自体の未導入時だけNumPyへ戻り、破損import/変換エラーは既存再接続経路へ渡す。singleton画像も独立・書込可能・C連続配列を保証。
- 独立設計レビュー/実装レビューLGTM。実装者87件PASS、独立検証はcapture/pixels/bubble detector/pipeline/languages/ONNX threads/OpenVR sessionの7スイート168件PASS（skipなし）。変更5ファイルのruff 0.14.4、diff check PASS。CPU/CUDA両Pythonでstandalone path loadと4形式×RGB/BGRのsynthetic smoke PASS。共有venvは変更しない。
- 固定seed合成画像の9回交互比較で全画素一致。RGBA/BGRAの順に、1080pは旧23.91/40.69→6.90/6.25ms、2575×1455・paddingありは44.60/58.27→11.65/10.59ms、4Kは90.42/111.32→21.68/21.73ms。直接NumPyコピー案も比較し、全6条件でOpenCVが高速だった。
- `docs/benchmarks/ocr_pixel_conversion_2026-10-08.json`に全試行、Python/NumPy/OpenCV版・OpenCV thread数8・ソースhashを保存。独立検証でhash/全中央値を再確認。`tools/benchmark_ocr_pixels.py`から再現できる。
- 測定対象は所有コピーとCPU色変換のみ。GPU Map待ち、実画面取得、OCR推論、アプリ全体の時間は未測定。CPU/CUDA specのcv2同梱を確認。4Bとまとめた限定frozen検証は後述し、全sidecar再ビルド・実機表示確認とは区別する。cv2を除外するcollectorはNumPy fallbackを利用する。
- 既存venvのOpenCV実体は4.11.0、requirements固定はopencv-python-headless 4.10.0.84だった。共有venvを変えず`tmp/cv2-pinned`へ固定版を隔離導入し、CPU/CUDA双方でcv2のpath/4.10.0をassertしてcapture/pixels87件ずつPASS。CUDAにはpytestが無かったため、テストrunnerを`tmp/cycle4a-pytest`へ隔離導入して再実行。pytest依存のpackaging 26.3は既存langchainとの警告があるため、当該パスを全アプリ用環境として扱わない。4Aベンチは実測した4.11.0の記録を維持する。

## サイクル4B — Overlay起動演出の透過処理

- `introKeyAlpha`のuint8 BGRA経路を既存OpenCVへ移し、画像全体のint32展開・複数のNumPy配列演算を削減。通常frameのcrop/alpha mask、WGC、GL upload、OpenVR提出、session/threadの寿命は変更しない。効果は起動演出中の変化frameに限られる。
- RGB/BGRの入替えはせず、BGR各channelの絶対差最大値から256要素のreadonly LUTで透過率を生成。旧式の整数床除算、既存alphaとのmin、alpha=0のBGR消去、key/透明率を維持。固定LUT生成時はint32とし白文字のoverflowを回避。OpenCVの[固定版copyTo仕様](https://docs.opencv.org/4.10.0/d2/de8/group__core__array.html)のmasked新規出力がゼロ初期化される契約を利用。
- OpenCVの演算・結果作成・透明率計算が成功してから、最後にNumPyで元ROIへ代入。変換失敗では入力を部分更新しない。負stride/転置/列間引きviewも入力として処理し、ROI外を維持。cv2自体の未導入、uint8 BGRA以外は旧NumPy処理。壊れたimport/実行失敗は隠さない。
- 独立設計/実装レビューLGTM。実装者検証は固定cv2 4.10でoverlay関連4スイート218件＋33 subtests PASS、既存4.11でもpixels/tooltip68件＋28 subtests PASS。独立検証は固定4.10のCPU7スイート238件＋35 subtests、CUDA4スイート93件＋28 subtests PASS（skipなし）。readonly入力の新旧ValueErrorと入力不変を別途確認。新規2ファイルのruff 0.14.4とoverlayの重大エラー規則、diff check PASS。hash・全16条件×9試行の中央値も独立一致。
- 固定OpenCV 4.10.0・8threads、4 DPI×背景優勢/random×単体/CPU準備の全16条件を9回交互測定し、全画素と戻り値が一致。背景優勢DPI1は演算9.87→1.33ms、crop＋mask＋演算14.38→4.38ms。DPI2は40.17→5.17ms、62.32→25.31ms。randomのDPI2は31.23→5.85ms、47.66→21.59ms。
- 再現ツール`tools/benchmark_overlay_pixels.py`と全試行・ソースhash付き`docs/benchmarks/overlay_intro_2026-10-08.json`を保存。capture待ち・GPU upload・OpenVR・推論・アプリ起動は含まない。
- 初回importは別に計測。新Python processのcv2＋NumPy等の依存importは7回中央値201.42ms、NumPy読込後からのcv2 importは40.50ms。OS cacheは消去していない。`docs/benchmarks/opencv_import_2026-10-08.json`へ記録。通常appは`model.py`→`models.ocr`→bubble detectorでcv2を既にimportする静的経路があるため、これを今回追加するアプリ起動時間とは扱わない。standalone初回呼出しはwarmベンチとは区別する。
- 不採用のRust PoCも実測。PyO3 0.24.2でimmutable bytesを読み、非公開の新規bytearrayへGIL解放中にcrop/alpha/introを処理した。通常crop＋maskのDPI2は既定atlasで旧14.71→Rust18.47ms、最大atlasで24.90→27.45ms。既定DPI1は3.81→3.70msだが、全条件に安定した改善を確認できず採用しない。intro単体のDPI2・背景優勢は旧38.52ms、OpenCV試作5.15ms、Rust試作10.86ms（ROI入出力コピー込み）。安全な境界・コピー方式を変えれば結果も変わるため、Rust全般の限界という主張ではない。
- `docs/benchmarks/overlay_cpu_prototypes_2026-10-08.json`に不採用PoCの実測・ソースsnapshot・Cargo.lock・binary hashを保存。cropは9試行、intro試作は19試行の中央値のみ保持した探索結果。採用実装の根拠は別の確定版16条件ベンチを使う。PoCのDLLは本番や配布へ追加していない。
- CPU/CUDAそれぞれのvenvから限定PyInstaller exeを構築し、PYTHONPATHを除去して両方build/実行exit 0。4Aの8形式/色順と4Bの3合成画像について元式との全画素・戻り値一致を確認。両exeのcv2.pyd SHA256は隔離した固定4.10と一致（`4705689bc8cbe47b57e95560c648cbabdba43de1615d62a85ff21437285ee1b7`）、同梱readerも本番ソースとbyte一致。
- 限定exeはloggerをstub化し、capture/GL/推論等を除外。全sidecar起動や実GPU描画の成功ではない。初回は動的path loadしたreaderの`uuid`を検証用specが収集せず失敗し、hidden importを追加して両方成功。本番specの変更は不要。既存pycparser生成テーブルの警告は残る。結果は`tmp/cycle4b/{build,smoke}-final-{cpu,cuda}.log`、配布物は`tmp/cycle4b/dist-final-{cpu,cuda}`。起動待ちを調べるため段階ログと30秒watchdogを追加した限定exeも両方PASS、元の実行も自然終了exit 0でありprocessの強制終了は行われていない。

## サイクル5 — 最新develop統合とOCR入力整形

- ユーザーの最新develop取得・継続依頼を受け、`git fetch origin develop`後に`codex/rust-audio-pipeline`を`307dd796`→`e1c24d1b`へfast-forward。6コミットの内容はOCR再学習、評価ツール`--dir`、collector試験安定化、3.6.0-beta.1への版更新。既存の未commit変更とのファイル重複なし。統合前に59ファイル・binary patch・hash一覧を`tmp/cycle5-sync/a546c343-2288-4a07-b486-0d03e02599db`へ保存し、統合直後に全59ファイルのbyte一致を確認。stashや新規commitは作成していない。
- 新モデルは5,527,282 bytes、SHA256 `ac3767540dd46f5587a799d611139a18b213293cd1bcabba4491aed7235b8007`。入力`images [1,3,H,W] float32`、出力`output [1,N,6] float32`は同じ。BGR/0〜255/長辺1280/32倍数/左上配置PAD114/confidence0.7/NMS0.65を維持。既存4A/4Bとの契約衝突なし。独立調査で確認した。
- 統合直後のOCR/capture/collector/model/controller関連10スイートは199件PASS・実モデルsmoke1件を後段の直接検証に集約して除外。固定cv2 4.10、終了コード0。共有venv・学習データを変更しない。
- 設計・実装レビューともLGTM。`BubbleDetector._letterbox`のuint8 HWC3経路だけ、中間uint8 canvasを省き、最終float32 NCHWへ画像/下余白/右余白を直接書く。resizeとscaleを変更せず全出力画素を初期化。他dtype/channelは従来のuint8 cast挙動を保持。新規依存やRust DLL、推論・閾値・NMSの変更はない。
- 独立旧式oracleで全uint8値/BGR原色、動的形状、32非倍数のimage_size、両辺と右下cornerのpadding、singleton/細長い/負stride/転置/readonly、所有権/入力不変、uint16/float/他channelを比較。実装者56件PASS、独立検証はCPUの前処理/detector/pipeline/threads/languages107件PASS・1件除外、CUDA環境の前処理/detector55件PASS・1件除外。両方の除外は親の実モデル直接比較に集約。pinned ruff 0.14.4の変更3ファイル、diff check PASS。
- 固定OpenCV 4.10/8threads、19回交互の全8合成形状でtensorとscale完全一致、全条件の中央値が改善。2575×1455は6.52→5.90ms、1080pは6.02→5.19ms、1000×1400は7.98→6.49ms、1024正方形は10.06→8.33ms、2984×3256は10.55→9.62ms。resize込みの前処理のみで、推論やアプリ全体の高速化率ではない。既存cv2.dnn.blobFromImageとfloat mixChannelsの予備案は同条件で遅く、採用しない。
- 1080p入力で2826240 bytes、正方形入力で4915200 bytesの中間canvas割当を除去。これは配列サイズで、process peak memoryの実測値ではない。`tools/benchmark_ocr_preprocessing.py`で再現でき、`docs/benchmarks/ocr_preprocessing_2026-10-08.json`に全試行・source/model/base hash・環境を保存。独立検証でhash/全中央値/削減byte数を検算した。
- 実画像はメインcheckoutの既存val80枚＋学習外overlay49枚を読み取り利用。同じ新モデル/同じCPUExecutionProvider session（intra4/inter1）で旧新テンソルを直接`session.run()`し、全129枚でtensor、推論出力、productionのbbox・切出し画素が一致。`detect()`が例外を空検出へ変換する問題を避け、直接推論とreplay呼出し数も検査した。画像・認識文字列の保存/外部送信、実画面取得は行わない。
- 上記実画像検証は`docs/benchmarks/ocr_preprocessing_model_equivalence_2026-10-08.json`にhash/結果と再現scriptを保存。valでは検出70件を維持、holdout49枚の検出0を維持。これは旧新前処理の同値確認であり、モデル再学習や独立した精度改善の主張ではない。文字認識CER/WERや実VR体感速度は対象外。
- NMS前候補数はval中央値7・最大12、holdout全0だった。このfixtureではNMSループの候補は少なく、次のRust化を優先する根拠としては不足。推論後処理や上位6件への打切りで検出契約を変えない。次の大きな候補は、実機でcapture待ち・GPU同期・OpenVR提出を分けて測定してから判断する。
- 5では依存・配布spec・Rustソースを変えていない。CPU/CUDA環境の前処理と新モデル直接推論を確認し、全sidecar/frozen再ビルドは繰り返さない。4Bの限定exe成功は旧基準での結果として保持する。全変更は未commit・未push。

## サイクル6 — custom_speech_recognition依存の完全除去

- ユーザーの明示指示により、残っていたlistener互換adapterとFLAC subprocessを削除。`requirements.txt`の固定fork依存を除き、CPU/CUDA両specで`speech_recognition`を明示除外。Google通信・応答解析、PyAudioWPatchのデバイスI/O、録音stop/pause/queueの契約は維持する。由来コードのBSD通知は依存と区別して保持。
- `require_native_audio()`を追加し、録音と8000〜96000HzのFLACを既存Rust拡張へ一本化。未導入なら機能開始時に導入案内付きImportErrorとなり、app import時には読み込まない。壊れたDLL・native失敗は隠さない。normalizerと対象外speaker変換の既存NumPy/pydub fallbackは残す。
- flacenc 0.5.1自身の96kHz上限は変更しない。それを超える入力は既存PyAV/FFmpegでmono PCM16を分割encodeし、flush/close後に出力を取得。元rateを維持し、旧encoderで確認した655350Hz以下・10の倍数の受理範囲を維持する。PyAVを直接利用するため、CPU/CUDA既存環境と同じ`av==18.1.0`を明記。
- 非空・完全PCM16・64MiB上限をencoder呼び出し前に共通検証。高rateにも64MiB上限を加え、外部processの10秒強制timeoutは廃止する。空認識の早期return、HTTP timeout・失敗処理は維持。PyAVのencode/flush/close/FFmpegErrorとchunk境界を検査する。
- 旧forkの固定commit/source hashから一度だけ合成入力の結果を採取し、energy 27条件、PCM 12条件、speaker 5条件、calibrationを`src-python/test/fixtures/legacy_audio_contracts.json`へ保存。新実装をoracleにせず、旧packageなしでPCM/hash/energy/readcount/thresholdを回帰検証。ベンチと実機診断ツールも旧packageをimportしない構成に変更。FLAC/energyは今後単独測定、normalizer/speakerは既存比較を維持し、過去の比較JSONは書き換えない。
- 独立設計・実装レビューLGTM。実装者の関連496件PASS後、FFmpegErrorの追加3条件を含むSR import禁止345件PASS。独立検証はCPU 26スイート647件＋環境修正後の対象1件＝648件（4 subtests）、CUDA 9スイート432件＋対象1件＝433件、いずれもskipなし。初回各1件は子process用PYTHONPATHの`src-python`不足による失敗で、起動環境を修正した当該再試験は両方exit 0。source修正による解消ではない。
- 独立検証でav 18.1.0、cv2 4.10.0、3C native binaryを事前assert。pinned ruff 0.14.4の音声関連22ファイル・diff check PASS。レビューで残ったrecorder docstring 2箇所とREADME説明を修正し、指摘解消確認済。docstring除外AST・行数は修正前と一致。実装者のenergy/conversion CLI smokeもPASS。実音声・外部通信は使用しない。
- Rustソース・wheelは変更せず3C binary（SHA256 `2d38d52f4172aa420e562b8e14abdf302d1c197452e712df1d1abe44d6e248b7`）を使用。共有venvを変更せず、`tmp/cycle6`で最新CPU/CUDA全sidecarを再構築し、両方build exit 0。CPUは1,197,652,497 bytes/3,181 files、CUDAは3,047,227,027 bytes/3,192 files。両版のPYZとファイル一覧で旧SR module・dist-info・付属FLAC exeが0であることを確認した。
- ソースPYTHONPATHを除去し、隔離cwdから両exeの限定runtime hookを実行してexit 0。native listener選択、5 native API、8/44.1/96/192kHzのFLAC復号PCM・rate一致、mock Google request、明示rate sourceのdevice初期化なし、モデル・license・配布資産を確認。実controller起動、実デバイス、外部HTTP、GPU推論は行わない。
- 両PYZから取り出した音声関連9モジュールのcode objectを現行ソースからのcompile結果と照合し、docstring修正も含め一致。nativeと固定cv2 4.10のbinary hash一致、最新OCRモデルhash一致、glfw3.dll実在、CUDA数学DLL11本を確認。両環境のsource-freeze 25ファイルも一致。210 PythonファイルのAST走査でも旧SR importが0だった。
- 配布検証の初回hash検査は、検証scriptがUTF-8 JSONを既定encodingで読み日本語ファイル名を誤解釈して失敗。明示UTF-8へ修正し最終検査exit 0。アプリ変更・配布再ビルドは不要だった。既存の非致命hidden import `models.transcription.audio_pipeline`、pycparser/tzdata、glfw探索の警告は残る。glfwはdatas同梱を実在確認しており、警告を未確認のまま成功扱いしていない。
- ログと再現scriptは`tmp/cycle6`に保存。`independent-retest-summary.json`は子process検証の再実行結果をagentが記録したものでrawlogではない。`build-verification.json`、`smoke-{cpu,cuda}.json`に凍結ソース・binary・資産の根拠を保持。全変更は未commit・未push。

## サイクル7 — MIT crateを使ったVAD正規化の統合

- ユーザーのMIT crate利用許可・追加2サイクル依頼の1つ目。`dasp_sample =0.11.0`（MIT OR Apache-2.0からMITを選択、通常依存0件）を採用し、signed PCM8/16/24/32の幅変換とVAD用モノラル化を`normalize_pcm16`へ統合。既存のC実装`audioop.ratecv`とストリーム状態/resetは維持する。
- 各sampleをi16へ変換してからties-to-even平均する。サンプル未満のbyteはエラー、チャンネル未満の末尾sampleは切捨て。mono16は入力bytesを再利用し、他形式は所有bufferでGILを解放する。VADのsigned8とPcmAudioのunsigned8を混同しない。
- Python dispatchは型・形式・チャンネル数・元入力64MiB・旧幅変換後interleaved PCM16の64MiB上限を確認し、対象外は従来経路を維持。古いwheelの新API欠落やnative処理失敗は隠さない。rubato等へのresampler変更は数値・遅延・状態を変えるため採用しない。
- 独立設計・実装レビューLGTM。実装者CPU284件に加え、独立CPU/CUDAの音声関連13スイート各589件PASS、skipなし。Rust13件、clippy/fmt、ruff 0.14.4 PASS。旧SR import禁止下で実行。レビュー担当は幅1〜4×全256chの1024条件を独立比較しPCM一致。既存依存の非推奨警告5件は残る。
- 20条件を9回交互測定してPCM・resampler状態が一致し、全条件の中央値が改善。1024frame/PCM16/48kHzはmono11.336→10.632µs、stereo16.926→15.220µs、6ch18.620→16.709µs。通常チャンクでの絶対効果は数µsであり、ASR全体の改善率ではない。15秒6chは16.67→14.01msだが通常チャンクとは分けて扱う。
- 再現ツール`tools/benchmark_audio_normalizer.py`、結果`docs/benchmarks/rust_audio_normalizer_2026-10-08.json`を保存。親検査で全中央値・現行ソースとbinary hash・保存したcycle6 processとoracleのAST同値（型注釈/16k定数の展開を除く）を確認。探索時の値と最終結果を区別する。
- crate公開元commit `97c3bb9b2363c0b46ac1633858bf1054fd02a980`のMIT全文を第三者通知へ同梱。正規化したMIT本文SHA256 `b1d6df41ed3aa96806e74c729444d7c121d90e6660a6aed01d298e03fde475a0`。公開crateのソース一致とwheel内通知・pyd一致も確認。新wheelは`tmp/cycle7-wheels`、SHA256 `4107b409379ae55ce61520fcc3b972f9ac1da52b141bb52f3e1221eb394bcb33`、pyd SHA256 `497de5454e8faf87c5d581a31bfb883eb7598c363b831340596bad1608576537`。
- 共有venvは変更せず`tmp/cycle7-native-site`へ隔離導入。独立テストログ・親検査は`tmp/cycles7-8/cycle7-*`。最新凍結モジュールのCPU/CUDA検証はサイクル8後にまとめて行う。全sidecar/実機/外部ASRはこの段階では再実行していない。

## サイクル8 — 同じ発話の認識前処理を再利用

- 追加2サイクルの2つ目。同期的な候補言語ループで同じ`PcmAudio`を使う既存構造に合わせ、16kHz/16bitのrawとWAVだけをインスタンス内で遅延保存する。汎用dict/global cache/別発話への持越しは追加しない。Google FLACのキャッシュも対象外。
- 入力検証とNoneによる形式解決をcache hitより先に行い、成功したimmutable bytesだけを保存する。空bytesは有効な結果、失敗は再試行可能。非canonical形式の変換順序、unsigned8bit、dataclassの等価性/hash/reprは維持。WAV作成が失敗しても成功済みrawは再利用する。
- LocalWhisperProviderの`flatten()`と除算結果の別配列を省き、新規float32配列にin-place除算する。float配列自体は候補言語ごとに作り直し、モデルが入力を書き換えても次候補へ影響しない。実際のOpenAI互換providerからSDKへ同一WAV bytesが渡ることもfake clientで検証。
- 独立設計・実装レビューLGTM。独立CPU/CUDAの9スイート各243件＋3 subtests PASS、skipなし。旧SR import禁止、ruff 0.14.4の変更5ファイルPASS。レビュー担当が旧baselineとの2160条件でraw/WAV完全一致を追加確認。Rustは7から変更していないためRustの再試験は重複実行しない。
- raw/WAV/Whisper準備を、16k/44.1k/48kHz・3/15秒・1/3/5候補の54条件で9回交互測定。毎回新規clipから開始し入力一致を確認。48kHz/15秒/3候補はWAV25.7455→8.0738ms、Whisper25.1496→8.6257ms。5候補はWAV41.8878→8.0411ms、Whisper37.5518→8.1237ms。推論・通信時間は含まない。
- 全54条件のうち中央値改善は42条件。単候補のrawは6.8451→7.0616ms、Whisper8.7490→9.1593msとなり、単候補の改善は主張しない。16kHz/3秒/単候補rawは1.308→1.553µsで小さい追加負荷がある。対象は複数候補での重複変換と配列コピーの削減であり、全面的なRust移植や全条件での速度改善ではない。
- 再現ツール`tools/benchmark_audio_preparation.py`、全試行`docs/benchmarks/audio_preparation_reuse_2026-10-08.json`を保存。親が現行ソースと保存baselineのhash、raw/WAV/Whisper oracleのAST同値（型注釈と変数名を除く）、全中央値を検査。実装者テスト・独立検証・親確認のログ/JSONは`tmp/cycles7-8`に保存。
- 7の新pydと8の確定Pythonを、CPU/CUDA各venvから限定PyInstaller exeに同梱。両build/実行exit 0。ソースPYTHONPATH除去・隔離cwdで、native6 API、24形式のPCM/状態一致、raw/WAV再利用、warm cacheでの検証、Whisper入力の変更隔離を確認。SDK/logger/model推論はstub、旧SRはimport禁止。4モジュールのPYZ code objectを現行ソースと照合し一致、新pydとMIT通知の同梱一致も確認した。
- 上記は最新変更モジュールの限定配布検証であり、6の全sidecar buildを最新DLLでやり直したものではない。CPU/CUDAの配布spec・Python依存・デバイスI/Oは7/8で変更なし。実機録音、外部ASR、GPU推論、全アプリ起動は未実行。共有venvは変更せず、全変更は未commit・未push。

## サイクル7/8後の全sidecar配布確認

- ユーザーの次タスクへの移行依頼を受け、最新DLLとPython変更を含むCPU/CUDAの全sidecarビルドを開始。アプリの実装・共有venvは変更せず、`tmp/audio-release-validation`へspec・workpath・cache・配布出力を隔離。旧6/7/8の配布結果は保持。
- 本番specからの変更はパスの絶対化、隔離した新native/固定cv2/sourceの探索パス、検証runtime hookのみ。依存SDKは実体を収集。Google HTTPとWhisperモデルをmockにし、デバイス初期化・controller起動前に検証を終える。独立担当がspec差分とhookを確認し、モデル呼出し3回の明示assertを追加した。
- ビルド入力198ファイルのhashを固定。src-python/toolsの213 PythonファイルのAST走査で旧SR import 0を確認。新6 API、24形式の正常化とresampler状態、raw/WAV再利用、Whisper入力の変更隔離、9音声モジュールの凍結code object、新pyd/notice/model/cv2とCUDA数学DLLの同梱を確認する。
- CPU/CUDAの全sidecar buildは両方exit 0。CPU約1249秒・1,197,663,678 bytes/3,181 files、CUDA約1109秒・3,047,238,208 bytes/3,192 files。PyInstaller 6.10.0、Python 3.11.5、NumPy 1.26.4、PyAV 18.1.0、隔離OpenCV 4.10.0を使用した。ソースPYTHONPATH除去・隔離cwdから両exeの検証hookを実行してexit 0。
- 新6 native API、24形式の正常化とresampler状態、16kHz/16bit raw/WAV再利用、cache後の入力検証、Whisperモデル呼出し3回と配列の変更隔離、8/44.1/96/192kHz FLACの復号PCM/rate一致を確認。SDK/loggerは本物を収集し、Google通信とモデル推論のみmock。実controller起動・実デバイス・外部HTTP・GPU推論は実行していない。
- 親検査と独立検査で両PYZの音声9モジュールが現行ソースのcode objectと完全一致（ファイル名のみ正規化）。ビルド入力198ファイルに変更なし。旧SR module・dist-info・付属FLAC exeは0。新pyd SHA256 `497de5454e8faf87c5d581a31bfb883eb7598c363b831340596bad1608576537`、MIT通知全文、固定cv2、最新OCRモデルのhashが期待値と一致。
- 両版でglfw3.dllの実在、CUDA版でcuBLAS/cuDNN DLL11本を確認。以前と同じ非致命hidden import `models.transcription.audio_pipeline`、pycparser生成テーブル/tzdata、glfw探索警告は残る。旧audio_pipelineはspec以外の現行ソースから参照されておらず、glfwはdatas同梱を実在確認した。全アプリ起動成功とは区別する。
- build/runtime/asset検証のログと再現scriptは`tmp/audio-release-validation`、永続結果は`docs/benchmarks/audio_full_sidecar_2026-10-08.json`。アプリ実装・共有venvの変更、commit/push、外部公開は行っていない。
- 最終独立監査もPASS（exit 0）。実配布物のhash・全文notice・filecount/bytesと各レポートが一致。6の配布物との相対ファイル名集合はCPU/CUDAとも追加0・削除0で、意図しない依存ファイル増加なし。`independent-final-audit.log`に確認結果を保存した。

## サイクル9 — Rust呼出し時の入力コピー削減

- 継続依頼を受け、移動後の`D:/codex/home/worktrees/4508/VRCT`で既存1〜8の成果を保全。基準commitは`e1c24d1b0434e562a02bd4f00106e8bd3974f789`。前回全sidecarの198入力ファイルと照合し、今回の変更はそのうちRustの`lib.rs`/`normalize.rs`だけ。Python本番処理・依存・デバイス境界は変更していない。
- `encode_flac`、`downmix_pcm16`、`speaker_downmix_pcm16`、`normalize_pcm16`の入力`to_vec()`を除去。immutable `PyBytes`の所有者を同期呼出し終了まで保持してsliceを借用し、GILを解放する。固定PyO3 0.24.2のbytes/allow_threads契約を確認し、独立設計・実装レビューともLGTM。unsafe・追加依存なし。入力検証、64MiB制約、丸め、途中overflow、出力所有権と型は維持する。mono downmixのidentity化は行わない。
- 入力長と同じ一時Vec割当とコピーを各呼出しで1回省く。48kHz/15秒/PCM16/6chなら8,640,000 bytes。これはprocessピークメモリの実測値ではない。FLACのi32変換・圧縮bufferと出力bytesコピーは残る。
- `test_native_audio_buffers.py`に20件を追加し、mutable/buffer入力拒否、bytes subclass、同一入力の並列処理、GIL解放中に別threadが外部参照を破棄しても入力が存続することを確認。独立CPU/CUDAは各15スイート667件＋3 subtests PASS、skip 0、旧SR import禁止。CPUは14スイート664件＋統合3件を分けて実行。Rust13件、clippy/fmt、追加Python2ファイルのruff 0.14.4もPASS。既存依存の非推奨警告5件が残る。
- 旧7のDLLと新9のDLLを同じprocessで交互に9回測定。38条件すべて返却bytes一致、FLACはPyAVで復号sample/rate/channelも一致。中央値改善は30/38条件。48kHz/15秒/6chのspeaker変換15.4020→12.0741ms、PCM16正規化9.1880→4.9721ms、PCM24正規化9.9141→4.9987ms。入力・出力のPython API費用を含む前回Rust版との比較であり、旧Python版との比較ではない。
- 通常1024frameではspeakerの3/6/8chと一部幅の正規化が微増。FLACも4条件中3条件で微増（48kHz/15秒34.3174→35.1569ms）。全条件の高速化や実ASR全体の改善率は主張しない。大きな入力の変換時間と一時割当削減を理由に採用する。再現ツール`tools/benchmark_audio_buffers.py`、全試行・ソース/DLL/wheel hash・検証結果は`docs/benchmarks/rust_audio_buffers_2026-10-08.json`に保存。
- 親検査でbaseline Rust2ファイルが前回全sidecarのhashと一致、Cargo.lock/energy.rs不変、両DLLとbenchmarkソースのhash、全中央値、wheel内pydと3ライセンス全文が一致。新wheelは`tmp/cycle9/wheels/vrct_audio-0.1.0-cp310-abi3-win_amd64.whl`、SHA256 `8177dd444745ddac81dc7f76c03551081eb208b5ce1b5903a9e31376801acdbc`。pyd SHA256 `8286bd9ca1f1221d1b14e7f4ccd7040d1d586a6b6fc469e5e15ffa148ca8fc53`。
- 新DLLを`tmp/cycle9/native-site`へ隔離導入し、CPU/CUDAの限定PyInstaller build/runともexit 0。ソースPYTHONPATHなしの隔離cwdで6 API/24正規化形式/resampler状態/発話内raw-WAV再利用/Whisper入力変更隔離を確認。4 PythonモジュールのPYZ code object、新pyd、notice全文も照合一致。SDK/logger/モデルはstub。配布spec・依存を変えていないため全sidecarは再構築せず、全sidecarの最終確認は7/8時点として区別する。
- 実機録音・外部HTTP・GPU推論は未実行。共有venv、ユーザーの既存変更、commit/pushに変更なし。ログと再現spec/scriptは`tmp/cycle9`。初回`python -m maturin`は隔離targetのexeを見つけられなかったため、既存maturin 1.8.3のexeを直接起動してビルド成功。環境検査のtorch metadata欠如は「未導入」と記録する方式に修正し成功し、アプリの修正では解消していない。

## チェックポイント後の検証（サイクル10、2026-10-08）

- `b9be99e7f27ff97abbad2c6f3abd1d218263404b`を基準に再開。製品ソース・共有venvは変更せず、最新9のpydを使ってCPU/CUDA全sidecarを`tmp/cycle10-sidecar`へ並行構築し、両方exit 0。CPU約1646秒・1,225,617,338 bytes/3,182 files、CUDA約1574秒・3,075,191,868 bytes/3,193 files。旧7/8の配布物は保持。本番specとの差はパス・探索先・限定runtime hookのみで、289入力ファイルをhash固定し構築後も一致。独立harness/specレビューLGTM。
- ソースPYTHONPATHなし・隔離cwdから両exeの限定テストがexit 0。native 6 API、24形式の正規化とresampler状態、raw/WAV再利用、Whisper入力の変更隔離、8/44.1/96/192kHz FLAC復号一致を確認。Google HTTPとWhisperモデルをmockにし、通常controller起動前に終了する。両PYZの音声9モジュールを現行code objectと照合し一致。最新pyd・ライセンス全文・OCRモデル・固定cv2のhash、glfw同梱、CUDA数学DLL11本を確認。旧SR module・dist-info・付属FLAC exeは0。既存spec由来の存在しない`audio_pipeline` hidden import等の非致命診断は残る。
- 配布検証の永続結果・入力hash・再現scriptは`docs/benchmarks/audio_full_sidecar_cycle10_2026-10-08.json`に保存。親も結果JSONと入力freeze・実exe/native hash・配布file数/bytesを再照合し一致。
- 最終独立監査LGTM。実exe内の12モジュール・mainloop・検証hookを現行ソースと照合し一致。前回7/8の配布物から削除0、既存cv2/model/license/glfw/font/translation資産のhash変更0。両版で共有venv由来の`opencv_videoio_ffmpeg4110_64.dll`が1本（27,954,688 bytes）余分に収集されていた。固定4.10の資産と動作は維持され、今回のnative検証はPASS。配布最小化時の収集元統一をlow課題として残す。289入力のfreezeは共有venv全体の固定ではない。
- 最新DLLで既定マイク（44.1kHz/mono）とWASAPIループバック（48kHz/stereo）をCPU/CUDA各3回起動し、音量取得、pause要求、同時stop、再開始、繰返しstop、解放を確認。全回両方でmeter受信、device errorなし。stopはCPU31.288/10.940/22.342ms、CUDA26.404/19.591/44.665ms。音声は破棄し保存・送信しない。物理抜き差し、Windows既定endpointの切替、実認識・無音長時間停止はこの試験に含めない。
- 各環境用にtrackedの`src-python`250ファイルを専用tmpへcopyし、copy/現行/source manifestのhash一致を確認。専用configでtelemetry・auto device選択・転写・OCR・VR UI・OBS/WebSocketをOFFにし、ユーザー設定を利用しない。Python socketのconnect/sendto/bindとDNS、requestsを拒否しHF offlineを設定。起動中の録音openは禁止、ClipboardのSteamVR検出のみFalseへ差し替える。OSレベルの通信隔離ではない。
- 本番Main/Controller/Modelとprocess loggerを使ったsource起動をCPU/CUDA両方で確認。初期化完了、version（3.6.0-beta.1）、compute_mode（cpu/cuda）、shutdownは全て200。Main.stop後にMainのthread停止・子process exit 0。stderr空、error.log各1件は意図したHTTPガードによる更新確認失敗のみ。正常なGUI/frozen mainloop起動・モデル推論・全daemon停止の証明とは区別する。独立成果監査LGTM。
- source起動の初回CPU試行は、検証用ready printとアプリstdout writerが混ざって不正JSONとなり、検証側が100秒timeout。Controllerは初期化完了していた。検証コードのみready.json方式へ修正し、fresh directoryで再試行して成功した。初回証跡は保持し、製品の修正・失敗と混同しない。
- 起動時間の観測値はCPU14.27秒/CUDA16.63秒（import込み）。モデル未配置・ガード付き・全buildと同時実行のため性能比較には使わない。結果と検証scriptは`docs/benchmarks/audio_runtime_checkpoint_2026-10-08.json`、詳細ログは`tmp/cycle10-runtime`へ保存。実装変更がないため667件の音声回帰を再実行することはせず、今回追加した実行条件を検証した。

## サイクル11 — 配布の収集元統一とfrozen起動確認（PARTIAL・競合発見）

- サイクル10で余分なOpenCV 4.11用DLLが収集された原因を独立調査。PyInstaller 6.10.0の`pathex`は解析グラフでは先頭、実行プロセスでは末尾に追加され、cv2 hookとisolated子プロセスが共有venvのcv2を参照していた。起動前の`PYTHONPATH`をnative/cv2/sourceの隔離先に揃えたCPU/CUDA事前検査では、全て固定4.10を参照し、4100 DLLのみが収集対象になることを確認。
- 製品specや共有venvを変更せず、`tmp/cycle11-sidecar`で全再解析・ビルド・限定smokeがCPU/CUDAとも成功。CPU 3,181 files / 1,197,668,203 bytes、CUDA 3,192 files / 3,047,242,733 bytes。10との相対ファイル差は余剰4110 DLLの除去のみ。293入力の照合を16:45:27 JSTに閉じた後、12/13の本番変更を開始した。このfreezeは現在のソースではなく変更前の履歴。
- 本物のbootloader `__main__`を捕捉するガード付きfrozen起動は両版exit 0・IPC 200だったが、独立監査でCPUの`Model.overlay`未生成によるコールバック登録失敗を発見。runnerの初期PASSを訂正し、健全なCPU起動はFAIL、サイクル全体をPARTIALと記録。CUDAの当該試行は成功。失敗ログを保持し、再試行だけで解決扱いにしない。永続証跡は`docs/benchmarks/audio_full_sidecar_cycle11_2026-10-08.json`。
- ビルドと並行して既存のWhisper baseモデル4ファイルを専用tmpへcopyし、ローカルSAPIで合成した定型英文をCPU/CUDA各2回実推論してPASS。実deviceはcpu/cuda、compute_typeはint8_float32/int8_float16。Rustで48kHz/stereo→mono変換後、既存providerの16kHz raw再利用と独立float配列を経由し、本物Whisperがsegmentsを生成。全4回の文が合成元と一致し、配列値・入力不変・重み原本/copy hashを確認。単一合成文のsmokeであり精度評価ではない。モデルや音声をダウンロード・外部送信せず、ユーザー録音を使わない。並行処理中の実行時間は性能比較に利用しない。`docs/benchmarks/audio_local_whisper_cycle11_2026-10-08.json`に結果・検証sourceを保存。
- 独立調査で別の既存インストール課題も確認。`bat/install.bat`の最初の通常依存解決はrapidocr/windows-capture経由で`opencv-python`を導入し得る。後段の`--no-deps`再導入は既に入ったpackageを除去しないため、両共有venvにopencv-python 4.11/headless 4.10が併存している。検証用探索先の統一とは別に、後続12でインストール手順を是正した。

## サイクル12 — OpenCVインストール衝突の修復（完了）

- `bat/install.bat`の最初のrequirements導入で通常版とheadless版が同居し、後段のrapidocr/windows-capture再導入では修復できないことを確認。両opencv packageのRECORDにはcv2.pydを含む92個の共有パスがあるため、通常版のuninstall後にheadlessを必ずforce-reinstallする必要がある。
- CPU/CUDA共通で通常版の除去→既存固定版headless 4.10.0.84の再導入→cv2実version/metadata確認を実装。requirements導入と修復の各コマンドに失敗時の即終了を追加。依存指定は変えず説明コメントを更新。11の入力照合を閉じた後、レビュー・試験済みドラフトを本番2ファイルへ反映し、独立最終レビューもLGTM。toolchain encodingテスト3件PASS。
- 使い捨てvenvと取得済みwheelのみで実cmd/pipを実行。headless 4.10→通常版4.11で衝突再現、修復、修復の再実行、空wheelhouseで復元失敗と後続処理禁止、その後の再試行で復旧を確認。11段階のうち失敗注入だけ期待exit 1、他はexit 0。cv2 4.10、通常版metadataなし、FFmpeg 4100のみ、画像変換成功を検査。CPU/CUDA両ドラフトのblockは実試験用blockと一致。独立成果監査もLGTM。
- 証跡と再現scriptは`docs/benchmarks/opencv_install_repair_cycle12_2026-10-08.json`。共有venvを変更する全installerは実行しない。`pip install -r requirements.txt`単体では衝突が残り得ること、headless代替のためpip checkがopencv-python metadata欠落を報告し得ることは制約として残る。

## サイクル13 — 先行heartbeatによる初期化競合の修正（実装済み・配布最終検証は未完）

- 11のCPU失敗は、先行`/run/feed_watchdog`がhandler threadから重いModel初期化を開始し、main thread側の初期化・callback登録と競合したもの。`feedWatchdog()`は生成済みwatchdogだけを更新し、未生成なら戻る最小修正にした。watchdog生成後は重い初期化の途中でもfeed可能。一般の全IPC初期化競合を解決する変更ではない。
- 独立設計・実装レビューLGTM。新規6テストで未初期化/初期化失敗時、初期化中feed、7 callback保持、例外伝播を確認。関連テストはCPU/CUDA各24件＋2 subtests PASS（既存警告4件）。CPUは最終のテスト内lint修正前、CUDAは修正後。製品ソースは両実行間で不変。ruff 0.14.4 PASS。旧checkpointのメソッドを子processで差し戻すと新規試験が3 failures / 2 errorsになり、不具合検出を確認。
- 11のAnalysis TOCと依存資産を再利用してPYZ/EXE/COLLECTを再構築。両ログにCOLLECT完了があり、配布exeの限定smokeも両版PASS。全依存の再解析ではなく、build process終了コードの直接回収と新旧全PYZ/資産hash最終照合は未完。初回specのnamespace `'-'`に対する誤assertは検証specのみ修正し、初回ログも保持。
- 強化した起動harnessは、先行heartbeatで資源が生成されないこと、初期化後のOverlay 5個＋mute＋watchdogのcallback実体、stdout JSON・stderr空・期待したHTTPガード例外のみを検査する。独立harnessレビューLGTM。
- 引継ぎ依頼でCPU/CUDA起動runnerとその専用exeを停止。copy後の起動途中で停止し、`result.json`は未生成。PASSとは扱わず、fresh suffix付きで再実行する。`tmp/cycle13-startup`の途中ログ・コピーは保持。永続checkpointは`docs/benchmarks/audio_startup_heartbeat_cycle13_2026-10-08.json`。
- 引継ぎcheckpointの独立対象監査LGTM。12ファイルのstageに一時配布物・録音・重みなし。JSON 6件の構文と11/13のPARTIAL維持、staged diffの空白検査PASS。修正後frozen起動・配布物照合の完了を意味しない。

## 残る条件と次のサイクル

- サイクル3Bの実装・独立レビュー・対象テスト・限定実機確認・CPU/CUDA配布検証、および3Cの多チャンネル変換・独立レビュー・互換/性能比較・CPU/CUDA最小exe検証は完了。
- `custom_speech_recognition`の実行時・テスト・ツール依存はサイクル6で除去。録音と通常FLACにはRust拡張の導入が必要。旧パッケージ名は由来・ライセンス・過去記録・除外/禁止検査にだけ残す。
- 追加依頼の2サイクル（7/8）と継続9は完了。MIT条件の`dasp_sample`によるVAD正規化統合、発話内の認識前処理再利用、Rust入力コピー削減を採用。配布には9の最新wheelを再ビルド/導入する。3C/6の旧pydには`normalize_pcm16`がない。既存install/build batのnative wheel構築経路を使う。
- PyAudioWPatchは3Dの固定版調査・実測に基づき当面維持。Rustへの全面移行を完了条件にせず、録音とPCM処理を一体化する効果を実証できた場合に再検討する。MME/DirectSound/WASAPIと現在のデバイス識別契約の維持が前提。
- 実機の物理的な切断・再接続、endpoint切替、無データが続く状態の停止、実認識、発話終了から画面表示までの性能は未検証。停止競合とread失敗はfake deviceで別途検証済み。
- 既存の8秒timeoutはprobe呼び出し元を復帰させるもので、ハングしたPyAudio呼出しや保持lockを強制解放する保証はない。本番openのtimeout化も今回の変更に含めない。
- 実音声の外部送信やクラウド認証の導入は行っていない。Googleは従来の経路を独立clientへ移し、別のクラウドサービスへは変更していない。
- OCRは4AのCPU画素変換と5の入力整形、Overlayは4Bの起動演出透過処理を実装。最新developの再学習モデルで129画像の旧新同値を確認。GPU直接提出、モデル/認識ロジックの変更、通常overlay描画全体の性能は別条件。
- cv2の収集元統一は11で確認済み、installerの衝突修復は12で反映済み。13の配布物最終照合とfrozen起動を最初に完了し、その後GUIと配布版実モデル推論の結合を確認する。
- 1〜9はローカルcommit `b9be99e7`、10〜13は今回の引継ぎcheckpointへ保存。13の未完条件は上記のとおり。pushとdevelopへのマージは未実施。

## サイクル14 — 検証の完了（2026-10-08、Claudeへ引継ぎ後・単独でRust化を継続する方針）

- 本worktree（`claude/backend-rust-migration-8f45d6`、HEAD `7877fec9`）で`maturin 1.8.3`によりwheelを再ビルド（隔離`CARGO_TARGET_DIR`、`tmp/`配下。共有venvは未変更）。pyd SHA256は`35294a2a…`で、配布検証済みの`8286bd9c…`とはビルドパス差で一致しない。同一ソースの別ビルドであり、検証済みpydそのものではない。
- Rust: `cargo test --locked`・clippy `-D warnings`・fmt成功。Python: `src-python/test`全体を`vrct_audio`導入下で実行し1857件＋136 subtests成功・skip 0を4連続確認。初回のみ2件失敗したが原因未特定で再現しない（不安定なテストの存在を否定しない）。最初のBash経由の実行はPYTHONPATHが`/d/...`形式になり拡張が読めず、native系306件がskipされた。PowerShellで再実行した結果が上記。
- サイクル13のfrozen起動: ソース（model.py・追加テスト）のhashがcheckpointと一致、install.bat/requirements.txtはCodex作業コピーのCRLF差のみ。新suffix`claude1`でCPU/CUDA各1回実行しPASS。Overlay 5＋mute＋watchdogのcallback実体、先行heartbeatの無初期化、JSON stdout、空stderr、期待したHTTPガード例外のみ、IPC200、shutdown200、exit 0。11のCPU失敗（callback登録のAttributeError）の解消を確認。永続結果は`docs/benchmarks/audio_startup_cycle14_2026-10-08.json`。
- 未実施: 配布物と現行ソースの全PYZ/資産hash照合、通常GUIとの結合、配布版での実モデル推論、物理hotplug/endpoint切替、無データ停止、発話終了から表示までの時間。developへは当面合流せず、このブランチで単独にRust化を進める。

## サイクル15 — 音声のE2E検証・実機抜き差し・エネルギー検出の音声消失修正（2026-10-08）

- 実デバイスなしのE2Eハーネス`tools/check_audio_e2e.py`を追加。SAPI日本語合成音声を実時間でpacingし、本番`MicSession`/`SpeakerSession`→recorder→listener/VAD→`AudioTranscriber`→providerを通す。差替えは`AudioCaptureSource`のみ（時計連動の`get_read_available`、`stop_stream`でreadを解除）。Whisperは実推論、Googleは偽`urlopen`でFLACを復号検証、OpenAI互換はローカルサーバでWAVを検証。`--listener fork`でdevelopの旧fork listenerとA/B可能。独立レビューの指摘（停止経路未通過、availability常時あり、損失カウンタの誤分類、`import model`による`src-python/config.json`書換えの未記載等）を反映済み。
- 発見: エネルギー方式に旧forkと同一の音声消失欠陥が2件（Rust移植は忠実に再現していた）。D1: 壁時計`record_timeout`(3s)が音声時間`phrase_time_limit`(3s)に競り勝つと録音中の最大3秒が破棄。D2: 時間上限で分割した直後の短い残りが短発話として棄却され語尾が消える。A/Bでspeakerのqueueサイズはfork/nativeで完全一致。
- 修正（ユーザー承認済み）: `native/vrct-audio/src/energy.rs`のみ。record_timeout時は通常の採用判定を通してPHRASEで返す。分割直後`pause_threshold`以内に始まる続きは短発話棄却しない。forkとの意図的な差は「分割直後0.8s以内の短い音も発話として出る」点。Python側変更なし。Rust 16件、clippy/fmt成功。
- CPU負荷下の前後比較（google/energy、各6回）: 修正前はmicで2/6回3発話目が消失、speakerで6/6回語尾0.8sが消失 → 修正後は全12回消失0。修正後の全マトリクス（mic/speaker×energy/VAD×Whisper/Google/API、`--fail-on-loss`）CPU12ケース・CUDA Whisper4ケースとも全PASS。CERは合成1話者のsmokeで精度評価ではない。
- 遅延（発話終了→文字、共有開発機での観測値で性能主張ではない）: VADはCPU約1.0〜1.2s・CUDA約0.3〜0.4s、エネルギー方式はCPU約3.4〜4.2s・CUDA約2.6〜3.5s。エネルギー方式の大半は`phrase_timeout=3`の確定待ちとASR推論で、Rust化した前処理は数msで支配要因ではない。
- 既存テストの不安定さを修正: `test_native_audio_buffers.py`のGIL解放中参照破棄テストがOSスケジューリング次第で失敗していた（セッション冒頭の原因不明の単発失敗）。観測スレッドが呼出し中に走らなかった試行は判定不能として最大5回やり直す形にし、負荷下10回連続成功。pytest全体1862件成功×3回、skip 0。
- 配布物照合（引継ぎ手順2）: cycle13とcycle11のPYZ module集合一致、code object差分は`model`のみで現行`model.py`と一致、exe内hookの差分は`startup_hook`のみ、`_internal` 3180/3191ファイルのSHA256差分0（CPU/CUDA）。co_filenameの差（176 module）はTOC再利用ビルドでpathexが効かなかったためで動作影響なし。
- 実機抜き差し（`tools/check_audio_capture.py hotplug`を追加、ユーザー実施・修正前wheel）: 既定デバイス切替中も選択デバイスで受信継続、抜去で`AUDIO_READ_ERROR`/OSError検知、無データ状態のstopは即時でstream close、再接続後はindex 4→1に変わっても名前で再解決してopen成功。抜去→検知時間はツールの計測漏れで未測定（watcherスレッドで修正済み）。
- 修正後wheel（pyd SHA256 `a6e96861…`）で同じ実機抜き差しを再実施し全段階PASS。最後のデータ→`AUDIO_READ_ERROR`検知485ms、無データstop即時、再接続後open 110ms・stop 46ms。
- 結果JSON: `docs/benchmarks/audio_e2e_cycle15_2026-10-08.json`。Auto Mic Selectによる再選択・画面通知、ループバックの無音中フレーム停止、読取り遅延時のoverflowはE2E/ツールの対象外。
