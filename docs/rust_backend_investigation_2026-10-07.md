# VRCT バックエンドの Rust 移行調査

調査日: 2026年10月7日。目的は、現行機能を維持しながら処理負荷と体感遅延を減らすために、Rustへ移す範囲を選ぶこと。

OCR再学習と起動高速化の統合を見据えた切り出し境界・API案・比較条件は、[Rust部分移行の先行設計](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/docs/rust_backend_migration_plan_2026-10-07.md)に記載した。

**現時点では、Pythonを残して処理単位でRust拡張へ切り出す方針が有力。** Whisper、VAD、OCR推論、画面取得の主要演算は既にネイティブ実装を呼んでいる。高速化の主な候補は、オーバーレイ画像のCPU往復、OCRの繰り返し認識、音声認識と翻訳の直列処理である。Rust化の効果と、推論回数・コピー・待ち時間を減らす効果は分けて測る必要がある。

静的調査であり、下表は実装候補の優先順位であって実測の速度順位ではない。ソースと既存テストを確認したが、アプリ実行、モデル推論、SteamVR実機比較、性能ベンチマークは実施していない。

| 対象 | 先に確認する改善 | Rustへ切り出す候補 | 判断 |
|---|---|---|---|
| VR UIオーバーレイ | 取得・コピー・GPU転送・同期待ちの内訳 | WGC取得からマスク処理、テクスチャ提出まで | コピー削減を伴う移行の第一候補。実装リスクは高い |
| OCR | 同一ROIの再認識回避、候補の公平な処理 | キャプチャと前処理、必要ならOCRワーカー全体 | 推論回数削減が先。言語だけの置換効果は限定的と予想 |
| 音声認識 | キュー待ち、発話確定待ち、翻訳による後続ASR阻害 | PCM正規化、VAD、セグメント生成 | 小さく比較できる候補。推論本体の置換を急がない |
| 設定、API、UI通信、翻訳プロバイダ | 実測で支配的な処理があるか | 当面は現状維持 | 高速化目的だけで全面移行する根拠は薄い |

## 調査対象

| 対象 | 固定したコミット |
|---|---|
| 現行VRCTの作業ツリー | `39b490bfd0ceaf398ae8e5b652c81bc4191c412d` |
| [LogicCuteGuy VRCT-0](https://github.com/LogicCuteGuy/VRCT-0/tree/8de53b5c44d3c2876178d0093d4e48053b252ee2) | `8de53b5c44d3c2876178d0093d4e48053b252ee2` |

現行側は調査開始時に未コミット変更なし。参考実装は一時ディレクトリに取得し、ビルドや実行はしていない。以下の現行コードへのリンクはこの作業ツリーを指す。

## 現行の処理境界

```text
React と Tauri
  └─ JSON行によるPython sidecarとの通信
       └─ mainloop → controller → model
            ├─ 音声取得 → 正規化とVAD → 有界キュー → ASR
            │                                      └─ 同期コールバック → 翻訳と出力
            ├─ HWNDまたはOpenVR取得 → YOLOX → ROIごとにRapidOCR
            │                                      └─ 重複排除 → 翻訳と出力
            └─ オーバーレイ
                 ├─ 字幕画像生成 → SetOverlayRaw
                 └─ VR UIのWGCまたはPrintWindow取得
                       → CPU画像とマスク → OpenGL転送 → SetOverlayTexture
```

sidecar起動は [StartPythonController.jsx](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-ui/views/app/_app_controllers/StartPythonController.jsx:64)、要求送信は [useStdoutToPython.js](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-ui/logics/common/useStdoutToPython.js:28)。音声や画像を毎フレームJSONでUIへ送る構造ではないため、sidecar廃止だけで画像転送負荷が消えるわけではない。

翻訳の既存DLLは [translator_engines.pyd](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/translator_engines.pyd)。WindowsのPython拡張DLLとして `translate_text` をimportしている。[呼び出し元](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/translation/translation_translator.py:17)にはRust製と記載されている。このcheckoutには当該Rustソースがなく、PyO3採用やGIL解放などの内部契約までは確定できない。

## 音声認識

### 既にネイティブで動いている部分

Whisperは `faster-whisper==1.1.1` と `ctranslate2==4.6.0`、VADはONNXのencoderとdecoderを使用する。録音もPyAudioWPatch経由のPortAudioである。Pythonは入力整形、状態機械、バッファ、呼び出しと配送を管理している。

[Whisper生成](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/transcription/transcription_whisper.py:180)は `cpu_threads=4`、`num_workers=1`。CPUとGPUを設定から選び、[Whisper provider](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/transcription/transcription_providers.py:129)はbeam size 5などの条件を指定する。[CTranslate2公式資料](https://opennmt.net/CTranslate2/parallel.html)でも計算メソッドのGIL解放を明示している。Python上で呼んでいることと、推論がPythonインタプリタで実行されることは区別する必要がある。

### 遅延と負荷の候補

1. **翻訳完了待ちが次の認識を遅らせ得る。** [model.py](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/model.py:631)の同じワーカー内で `_transcribe()` の後に `transcript_fnc()` を同期実行する。コールバックは [controller.py](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/controller.py:952)の翻訳・出力へ続く。モデル推論が速くても、翻訳API待ちや出力処理が長ければ次のASR開始が遅れる。寄与率は未測定。分離する場合はメッセージ順序、履歴、設定変更、停止、キュー上限を保つ必要がある。
2. **発話確定の待ち時間。** [audio_vad.py](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/transcription/audio_vad.py:167)の既定hangoverは24フレーム、約768ms。これは演算時間ではなく発話を切る判断の時間。Rust化では消えず、短縮には語尾欠落などの品質評価が必要。
3. **同一音声の処理回数。** [transcription_transcriber.py](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/transcription/transcription_transcriber.py:537)は候補言語ごとにproviderを呼ぶ。停止条件はproviderごとに異なる。Googleの中間結果は成長した音声バッファの再送を伴う。言語数とAPI回数を揃えずにPython対Rustを比較すると効果を取り違える。
4. **小さな変換と割り当ての積み重ね。** [正規化](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/transcription/audio_vad.py:74)、[32msフレーム処理](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/transcription/audio_vad.py:206)、bytes連結、speaker側の[WAV往復](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/transcription/transcription_transcriber.py:630)は比較候補。ただし音声帯域は画像より小さく、CPU負荷全体への寄与は測定が必要。

VAD側は約7秒で強制分割するが、ASR側は継続発話を再結合し15秒以上で安全弁を判定する。厳密な15秒周期ではない。前300ms・後500msの無音付加も実装されており、sleepではないが推論する音声長に含まれる。[分割とpadding](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/transcription/transcription_transcriber.py:66)。

### Rust拡張の候補境界

最初は **PCM正規化からVAD、セグメント生成まで** を状態付きオブジェクトとして切り出せる。入力はPCMと元形式、出力は16kHz・16bit・monoの確定音声と終了理由。ONNXモデルを常駐させ、`process`、`flush`、`reset`、`close` の責務を明確にする。毎32msのONNX呼び出しだけを別DLLへ置き換えるより、バッファと状態を一緒に所有させる方が境界往復を減らせる。

録音デバイスまで移すのは次段階。現行の有界キュー20件・energy最新1件、最古破棄、pause/resume時のdrain、openタイムアウト後の遅延cleanup、停止時のread解除を維持する。[セッション](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/model.py:319)、[録音](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/transcription/transcription_recorder.py:550)、[デバイス管理](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/device_manager.py:46)。

固定依存の [custom_speech_recognition](https://github.com/misyaguziya/custom_speech_recognition/blob/afae7ff78cd5da36e864122f16972d2b0044e03f/speech_recognition/__init__.py#L883) では、ブロッキングreadと `segmenter.process()` が同じ録音スレッドで動く。さらにprocessの返却列から最初のセグメントだけを返すため、DLL側で大きくbatch化して複数セグメントを返すと後続が配送されない。既存設定での実害は未検証だが、境界設計では残りの保持または全件配送が必要。pauseは即時resetではなく、stop時にflushする契約も確認した。

## OCR

### 実際の処理

[OcrPipeline](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/ocr/ocr_pipeline.py:316)は、取得、YOLOX検出、ROIごとのRapidOCR、重複排除、結果コールバックを専用ワーカーで直列実行する。**本番OCRの取得はWGCではなく、OpenVRのD3D11ミラーまたはHWNDのPrintWindow。** WGCを使うVR UI表示とは別経路である。[取得方式の選択](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/ocr/ocr_capture.py:57)。

[YOLOX](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/ocr/ocr_bubble_detector.py:132)はONNX RuntimeのCPU provider。[RapidOCR](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/ocr/ocr_engine_rapidocr.py:52)もONNX Runtimeを使い、モデル別にreaderをキャッシュする。OpenCVとNumPyも使っており、画像処理全体が純Pythonという状態ではない。

既にINT8のYOLOX、長辺1280と可変矩形入力、RapidOCRの短辺拡大抑制、ONNXスレッド上限4、低いワーカー優先度を導入している。[前処理](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/ocr/ocr_bubble_detector.py:151)、[OCR設定](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/ocr/ocr_engine_rapidocr.py:38)、[スレッド設定](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/ocr/ocr_languages.py:21)。Rust側でコアを使い切る設定へ変えると、OCR単体の時間が改善してもVRChatのフレーム時間が悪化し得る。

### 最初に減らしたい処理

**認識後の重複排除だけでは、同じ吹き出しを認識する費用は減らない。** [現在のループ](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/ocr/ocr_pipeline.py:380)は毎回RapidOCRを呼び、その後に文字列を比較する。bbox追跡と正規化ROIの差分を使い、文字が変わらない場合の再認識を省く実験が第一候補。これはPythonのままでも効果を切り分けられる。

キャッシュは画面全体のハッシュだけでは不十分。VRでは視点、位置、大きさ、背景が変わる一方、同じ位置に別発言が現れる。文字追加を見落とさない差分判定、再試行、定期再確認が必要。既存の「見えている間は抑制し、消えて一定時間後は同文を再配送する」契約も保つ。

既定750ms周期、最大6候補、80%のOCR予算があるが、予算判定は認識開始前だけ。1回の認識が予算を超えても途中で止まらない。毎回上位候補から処理するため、下位候補が待ち続ける可能性もある。[予算と候補処理](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/ocr/ocr_pipeline.py:390)。

[既存OCR文書](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/docs/details/ocr.md:27)には、VR取得約100ms、YOLOX約60〜110ms、PP-OCRv6 small約790ms/吹き出しの記録がある。測定条件・時期が揃わないため合算や今回の速度予測には使えないが、認識回数を測る理由にはなる。

### コピー削減とDLL境界

D3D11経路は [CopyResource、Map、CPUコピー](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/ocr/ocr_capture_d3d11.py:127)の後にRGB化し、[OpenVR側](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/ocr/ocr_capture_openvr.py:162)でBGRの連続配列へ戻す。まず同じ形式で処理を通す余地がある。MapのGPU同期待ちはRust化だけで除去できない。

段階導入なら、キャプチャと色変換・リサイズをRust側でまとめ、バッファを再利用する。全画面を毎回新規確保してPythonへ返すだけでは効果が小さい。さらに進めるなら、縮小した検出用画像をGPU側で作り、OCRに必要な高解像度ROIだけを読む構成を試す。CPU推論を残す以上、必要画像のreadback自体は残る。

YOLOXとRapidOCRまでRustへ移す場合は、画像をPythonへ戻さず文字・位置・confidenceを返すワーカー境界が自然。ただしBGR順、padding=114、CHW float32、32の倍数の動的形状、bbox座標復元、NMS、文字辞書、角度分類、行順、多言語モデル選択を固定して比較する。autoのPP-OCRv6と、韓国語・キリル・タイ・アラビア・デーヴァナーガリー等のv5モデルは同一ではない。[言語とモデル](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/ocr/ocr_languages.py:44)。

依存する [RapidOCR v3.9.2](https://github.com/RapidAI/RapidOCR/blob/v3.9.2/python/rapidocr/main.py#L116) も確認した。文字検出・方向分類・認識は全て有効で、方向分類は既定PP-OCRv4 mobileの0/180度判定。認識と分類は既に行画像を6件ずつbatch化しているため、「バッチ化を初導入すれば速くなる」とは言えない。未実施なのは吹き出しをまたぐbatch化である。[recognizer](https://github.com/RapidAI/RapidOCR/blob/v3.9.2/python/rapidocr/ch_ppocr_rec/main.py#L89)。

Rust側の前後処理には、透視変換、DB検出後処理、モデル内metadataまたは外部ファイルの文字辞書、CTCのblank/space/token順、Arabicのbidi処理を引き継ぐ必要がある。RapidOCRの最終confidence閾値0.5もVRCT側の閾値より先に適用される。det/cls/recの `elapse_list` が既に返るので、まずそれを計測に利用できる。[出力と計測](https://github.com/RapidAI/RapidOCR/blob/v3.9.2/python/rapidocr/main.py#L203)。

## オーバーレイ

### 字幕とVR UIを分けて評価する

字幕のsmall/large表示はPillowとFreeTypeで画像を作り、[updateImage](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/overlay/overlay.py:967)で `SetOverlayRaw` へ渡す。主にメッセージ更新時の処理であり、VR UIの連続キャプチャとは頻度が異なる。フォントキャッシュも既にある。[画像生成](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/overlay/overlay_image.py:76)。

VR UIはTauriの画面外WebViewをWGCで取得し、失敗時にPrintWindowへ戻る。現在の経路には次のCPU往復がある。

```text
WebViewの描画 → WGCのフレーム
  → Python bytesへ複製
  → クライアント領域をNumPy配列へ複製
  → alphaマスク等を変更
  → glTexSubImage2DでGPUへ転送
  → glFinishで完了待ち
  → 複数領域へ同じテクスチャを提出
```

根拠は [WindowStream](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/overlay/window_capture.py:117)、[領域コピー](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/overlay/window_capture.py:188)、[転送](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/overlay/overlay.py:1373)。既に同一画像の転送省略、BGRAのままのupload、マスクの再利用がある。取得周期はactiveで上限20Hz、idleで4Hz、操作ループは16/30/60Hzで切り替える。WGC自体も[Rust/Pythonライブラリ](https://github.com/NiiightmareXD/windows-capture)なので、取得APIをRustから呼び直すだけでは新しい高速化にならない。

### Rust化で試す価値がある構成

**WGCのD3D11テクスチャをRust側で保持し、マスク処理をGPU上で行ってOpenVRへ提出する構成**が、CPU往復を減らす候補。まずPython画像化とOpenGLへの再uploadを省けるかを実証する。[OpenVR公式ヘッダ](https://raw.githubusercontent.com/ValveSoftware/openvr/master/headers/openvr.h)はD3D11テクスチャとoverlay向けDXGI共有ハンドルを定義しているが、現在のWebView、GPU adapter、同期方式での実機成立は未検証。

これは「ゼロコピー保証」ではない。GPU内コピー、alpha加工、adapter間の移送、SteamVR側の同期は残り得る。フォールバック、透過、色空間、入力座標、DPI、リサイズ、tooltipの世代管理まで保つ必要がある。Rustコードへ `glFinish` 相当の待ちをそのまま移しても、その待ち時間は短縮しない。

同じアトラスを複数overlayで共有する現行設計は維持できる。ポインタ・掴み・追従の処理もRustへまとめる案はあるが、最初から約3,200行のoverlay全体を移すより、画像経路の効果を先に測る方が比較しやすい。PrintWindow fallbackは呼出先の描画応答を待つため、Rust化してもハング対策は必要。

### OpenVRの所有権

Overlay、OCR、Clipboardは同一プロセスのOpenVRセッションを共有する。[openvr_session.py](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/openvr_session.py:29)は参照カウントでshutdownを管理している。新DLLだけが独自に初期化・終了すると既存ユーザーのハンドルを無効化し得る。

移行時もinit/shutdownの責任者を一つにする。Rustへ所有権を移す段階では既存Python利用者も同じ管理層へ接続し、COM/GPUリソースの作成・使用・解放スレッドを固定する。停止は撮影停止、利用者停止、overlayからテクスチャ解除、リソース解放、最終セッション終了の依存関係を守る。[現行の終了処理](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/overlay/overlay.py:1289)にはテクスチャを保持したまま終了すると落ちた経緯が記載されている。

## 有志版の実装状況と参考にする範囲

対象のVRCT-0には、音声認識・OCR・オーバーレイの実処理がある。READMEだけの構想段階ではない。一方、現行版の全機能との同等性や高速化が証明された状態とも判断できない。確認できた制約を次のように分ける。

| 領域 | 実装で確認できたこと | 現行へ取り込む際の制約 |
|---|---|---|
| 構成 | Tauriから `vrct-core` を直接呼ぶ。runtime、provider、推論、描画を分離 | coreはPython用DLLとしてexportしていない |
| Whisper | CTranslate2を `ct2rs::sys::Whisper` で呼び、特徴量・tokenizer・decode制御をRust化 | CPU以外を明示拒否。CUDA版の代替にはならない |
| ローカル翻訳 | CTranslate2モデルの実推論 | こちらもCPU限定 |
| OCR | YOLOX、PP-OCR検出、方向分類、文字認識、CTC decodeをORTで実行 | 吹き出し検出モデルを非同梱。必要ファイルなしでは無効化 |
| 字幕overlay | Rustの文字整形・CPU描画からRGBAをOpenVRへ渡す | GPU上で完結する画像経路ではない |
| 操作可能なVR UI | small/large字幕overlayとは別の機能 | 現行のWebView capture、ランチャー、操作パネル、tooltip、掴み・リサイズ・入力配送は対象forkのRust backendに未実装 |
| OpenVR | セッションをleaseで共有 | Pythonと併用するなら双方で一つの所有権管理に統一 |

### 推論のRust化とCPU限定を混同しない

Whisperは別エンジンへ変更したものではなく、CTranslate2を維持している。[モデル実装](https://github.com/LogicCuteGuy/VRCT-0/blob/8de53b5c44d3c2876178d0093d4e48053b252ee2/src-tauri/crates/vrct-core/src/transcription/whisper/model.rs#L74)はCPU以外を拒否し、[core依存](https://github.com/LogicCuteGuy/VRCT-0/blob/8de53b5c44d3c2876178d0093d4e48053b252ee2/src-tauri/crates/vrct-core/Cargo.toml)はct2rsをruy構成でビルドする。[ローカル翻訳](https://github.com/LogicCuteGuy/VRCT-0/blob/8de53b5c44d3c2876178d0093d4e48053b252ee2/src-tauri/crates/vrct-core/src/translation/ct2/mod.rs#L224)にも同じ制限がある。

特徴量生成は [features.rs](https://github.com/LogicCuteGuy/VRCT-0/blob/8de53b5c44d3c2876178d0093d4e48053b252ee2/src-tauri/crates/vrct-core/src/transcription/whisper/features.rs#L94) でFFTを含めて再実装している。NumPy等で既にネイティブだった処理を置き換える箇所もあり、Rustで書いたという理由だけで速度向上や数値一致を期待しない。CUDA対応、数学backend、量子化、前処理の一致を揃えた比較が必要である。

### OCRで動かない理由を実装欠落と分ける

[engine.rs](https://github.com/LogicCuteGuy/VRCT-0/blob/8de53b5c44d3c2876178d0093d4e48053b252ee2/src-tauri/crates/vrct-core/src/ocr/engine.rs#L70) は必要モデルがないと `OCR_DISABLED_MODEL_MISSING` を返す。吹き出し検出モデルは配布から意図的に除外され、設定された外部ファイルを要求する。これはOCR処理が未実装という意味ではない。

[実処理](https://github.com/LogicCuteGuy/VRCT-0/blob/8de53b5c44d3c2876178d0093d4e48053b252ee2/src-tauri/crates/vrct-core/src/ocr/engine.rs#L549) は現行同様に最大6候補と周期の80%の予算を使う。ただしforkの予算はYOLOX検出を含み、現行は検出後から計時するため、文字認識に使える時間も異なる。ORTはintra/interとも1 threadであり、現行の最大4 threadと条件が異なる。単に1周期が短いかではなく、読めた候補数、待たされた候補、精度を比較する。

### 参考になる実装

- [Tauriとcoreの接続](https://github.com/LogicCuteGuy/VRCT-0/blob/8de53b5c44d3c2876178d0093d4e48053b252ee2/src-tauri/src/backend/pipeline.rs#L47)は、アプリ管理層と処理ライブラリを分ける例になる。ただしTauri側の `cdylib` 宣言は、そのままPythonから音声・OCR機能を呼べる公開ABIを意味しない。
- [overlay worker](https://github.com/LogicCuteGuy/VRCT-0/blob/8de53b5c44d3c2876178d0093d4e48053b252ee2/src-tauri/crates/vrct-core/src/overlay/mod.rs#L256)は有界channelと最新画像への集約、変更時だけの画像提出を行う。配送と再接続の設計は参考にできる。
- [OpenVRの共有管理](https://github.com/LogicCuteGuy/VRCT-0/blob/8de53b5c44d3c2876178d0093d4e48053b252ee2/src-tauri/crates/vrct-core/src/openvr.rs#L11)は、overlay、OCR、clipboardの寿命を揃える例になる。

字幕は [render.rs](https://github.com/LogicCuteGuy/VRCT-0/blob/8de53b5c44d3c2876178d0093d4e48053b252ee2/src-tauri/crates/vrct-core/src/overlay/render.rs#L94) で描き、[SetOverlayRaw](https://github.com/LogicCuteGuy/VRCT-0/blob/8de53b5c44d3c2876178d0093d4e48053b252ee2/src-tauri/crates/vrct-core/src/overlay/native.rs#L126) にCPUのRGBAを渡す。今回提案したWGCからD3D11 texture提出までの経路の実証例としては使えない。PillowとRustの文字整形・描画結果についても別途比較が必要。

**現行の操作可能なVR UIは機能差として残る。** forkのoverlayはsmall/largeの2種類で、ネイティブ側も2個のハンドルを扱う。現在のランチャー、WebViewから撮影するパネル、tooltip、掴み・リサイズ、マウス入力配送に相当する実装は対象forkの `src-tauri/src` と `vrct-core/src` に存在しない。large字幕に履歴が表示されることを、操作可能なログパネルへの対応と混同しない。現行VR UIを維持したい場合、この部分は自前の移行設計が必要になる。

### 停止と実モデル試験の注意点

forkにはWindowsのruy thread-local poolに関連するスレッド終了hangの注記があり、[Whisper実モデルテスト](https://github.com/LogicCuteGuy/VRCT-0/blob/8de53b5c44d3c2876178d0093d4e48053b252ee2/src-tauri/crates/vrct-core/tests/whisper_model.rs#L126) は `process::exit` を使う。[本番モデルの注記](https://github.com/LogicCuteGuy/VRCT-0/blob/8de53b5c44d3c2876178d0093d4e48053b252ee2/src-tauri/crates/vrct-core/src/transcription/whisper/model.rs#L47) と [通常終了するsession worker](https://github.com/LogicCuteGuy/VRCT-0/blob/8de53b5c44d3c2876178d0093d4e48053b252ee2/src-tauri/crates/vrct-core/src/transcription/session.rs#L452) の整合性は要検証。ここでは実機再現済みの不具合とは断定しないが、ON/OFF、デバイス切替、DLL解放の検証なしに取り込むべきではない。

Whisper実モデルテストは入力資源がない場合にスキップされ、[OCR実モデル試験](https://github.com/LogicCuteGuy/VRCT-0/blob/8de53b5c44d3c2876178d0093d4e48053b252ee2/src-tauri/crates/vrct-core/tests/ocr.rs#L251) は既定でignoreされる。テストコードの存在や通常のunit test成功を、モデル精度・実機互換性・速度の証明として扱わない。

## DLL形式の選択

| 形式 | 適した用途 | 必要な契約 |
|---|---|---|
| PyO3による `.pyd` | 現行Pythonから段階導入。最初の候補 | Python/C ABIの対応範囲、GIL解放、バッファ所有権、例外変換、wheelとPyInstaller同梱 |
| C ABIの `.dll` とctypes | Python以外の利用者にも公開する必要がある場合 | 不透明handle、固定幅型、構造体サイズとABI version、長さ付きbuffer、同じDLLでの解放、panicを境界外へ出さない |
| Tauri内のRust module | Python sidecar全体を段階的に撤去すると決めた場合 | UIイベント、設定、プロバイダ、停止、障害隔離まで移行 |

最初はPythonに設定・UI連携・翻訳などを残し、一つの処理領域を `.pyd` 化する案が扱いやすい。Rust内部はPythonに依存しない処理として書き、必要な場合にだけ別の公開形式を追加する。初回から複数のbindingを作る必要はない。[PyO3公式資料](https://pyo3.rs/main/building-and-distribution)。

重い処理や停止待ちでGILを保持しない。Pythonコールバックは結果配送に限定し、録音やGPUスレッドから頻繁にPythonへ戻らない。バッファを借りる場合は利用中の変更・解放を防ぎ、非同期処理には所有権を移すか必要なコピーを行う。[PyO3の並列実行](https://pyo3.rs/main/parallelism)。

DLLはプロセス内にあるため、ネイティブクラッシュの隔離にはならない。初期段階ではPython sidecar内に読み込むことで現在のUIとのプロセス境界を維持できる。Tauriへの統合は高速化実験とは別の判断として扱う。

## 測定と段階移行

最初に比較対象を固定する。同じ音声・映像、モデルhash、辞書、言語、beam size、量子化、CPUスレッド、GPU、画面解像度、OCR周期で比較し、モデルロードを含むcoldと常駐後のwarmを分ける。VRChatと同時実行してCPU使用率だけでなくフレーム時間への影響も確認する。

| 系統 | 測る区間 | 速度以外の判定 |
|---|---|---|
| 音声 | 発話終了、VAD確定、enqueue/dequeue、正規化、VAD推論、ASR、翻訳、配送 | WER/CER、語尾欠落、誤認識、結果順序、破棄件数、デバイス復帰 |
| OCR | 取得、Map待ち、コピー、検出前後処理、検出推論、文字検出・分類・認識、dedup、callback | bbox recall、CER、更新見逃し、重複、候補ごとの待ち時間 |
| Overlay | キャプチャ到着、CPUコピー、加工、upload、GPU同期、提出、操作ループ | 画面鮮度、VRフレーム時間、透過、DPI、入力ずれ、復帰、長時間のメモリ |

既存の音声 `[latency]` はASR・翻訳・出力を測るが、録音取得やVAD確定待ち、キュー待ちは含まない。総体感遅延として解釈しない。[ログの計算](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/controller.py:1208)。overlayには [区間計装](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/models/overlay/overlay.py:2886)があるため拡張できる。経過時間にはmonotonic clockを使い、p50/p95、コピー量、キュー長を記録する。

推奨する順序は次の通り。

1. 既存計装を使い、同時利用時の支配的な区間を特定する。
2. OCR再認識回避と音声の翻訳待ちを個別に試し、Rust化しなくても得られる改善を把握する。
3. VR UIのGPU経路、またはPCMとVADの小さいRust拡張を一つだけ試作する。効果の見込みを優先するなら前者、移行手順を小さく検証するなら後者。
4. 現行と同じ入力で比較し、品質と復帰動作が一致した範囲だけ置き換える。
5. OCR全体やASR制御の移行は測定結果から判断する。全面Rust化は配布サイズや起動時間、保守方針も含めた別の目的として評価する。

## 回帰検証の対象

| 領域 | 維持する既存テスト |
|---|---|
| 音声 | `test_audio_vad.py`、`test_transcription_recorder.py`、`test_transcription_transcriber.py`、`test_model_audio_queue_bounded.py`、`test_model_session_resume_drain.py`、`test_model_transcript_stop.py`、`test_audio_pipeline_failure.py`、`test_device_manager.py` |
| OCR | `test_ocr_capture.py`、`test_ocr_bubble_detector.py`、`test_ocr_pipeline.py`、`test_ocr_languages.py`、`test_ocr_onnx_threads.py`、`test_model_stop_ocr_capture.py` |
| Overlay | `test_openvr_session.py`、`test_overlay_shutdown_timeout.py`、`test_overlay_grab_move.py`、`test_vr_panel_capture_recovery.py`、`test_overlay_tooltip.py` |

テストは [src-python/test](C:/Users/misyaguzi/.codex/worktrees/4508/VRCT/src-python/test) にある。Pythonのmockに依存するテストはRust内部の正しさまで保証しないため、移行時には同じfixtureを新旧実装へ入力する比較試験が必要。GPUドライバ、SteamVR、録音デバイスの復帰は実機検証とする。
