# 全面 Rust 化 PoC の結果（2026-10-11）

調査（`rust_full_migration_survey_2026-10-11.md`）で「実機でないと判断できない」とした点のうち、推論（PoC 1）と ONNX（PoC 2）を確かめた。比較の基準は、今の Python バックエンドと同じ設定で動かした結果。

## PoC 1: CTranslate2（ct2rs 0.10.1、同梱の CTranslate2 は 4.8.2）

- 場所: `native/poc-ct2`（`reference.py` が Python の基準、`compare.py` が比較、`src/main.rs` が Rust 版）。
- Whisper は faster-whisper 1.1.1 の処理を Rust で再現した。log-mel 特徴量（FeatureExtractor と同じ計算）、エンコーダ 1 回、言語判定、プロンプト `[sot, 言語, transcribe, notimestamps]`、ビーム 5、`avg_logprob = score × len / (len + 1)`。抑止するトークンの一覧は、PoC では Python から書き出したものを読む（本実装では faster-whisper の `get_suppressed_tokens` を移植する）。
- NLLB は `tokenizer.json` を tokenizers クレートで読み、`[src_lang] + トークン + [</s>]` を作って `sys::Translator` に `target_prefix` を渡す（ct2rs #97 の回避）。

| 計算ライブラリ | ビルド | Whisper 文字列・トークン | NLLB（4 文） | 速さ（Python 比） |
|---|---|---|---|---|
| ruy（ct2rs の既定） | 通る | 3/3 一致 | 4/4 一致 | 4〜7 倍遅い（使えない） |
| oneDNN（`dnnl` + `openmp-runtime-comp`） | 通る（約 7.5 分） | 3/3 一致 | 2/4 一致（言い回しの差） | 同等（Whisper 1.3〜1.5 秒、翻訳 0.25〜1.1 秒） |
| Intel MKL（`mkl`） | `nuget.exe` が必要で未実施 | — | — | — |

- メル特徴量の差は最大 1.8e-5。無音は両方とも空の結果（言語判定は確率 0.27 前後で `nn` / `en` / `cy` と揺れる）。
- NLLB の差は「Hello.」→「Hi.」、「번역 주셔서 감사합니다」→「번역 감사합니다」。入力トークンは同一で、int8 の計算ライブラリの違い（Python は MKL）によるビーム探索の分岐。
- Windows で終了時に固まる問題（ct2rs #64）は起きなかった（CPU）。
- ビルドの注意: CTranslate2 は静的 CRT（/MT）なので `+crt-static` が必要（`native/poc-ct2/.cargo/config.toml`）。MSBuild のパス長の上限（260 文字）に当たるので、ビルド先は短いパスにする（`D:\WORKSPACE\poc-target\...`）。
- CUDA: CUDA Toolkit（nvcc）が無いため未実施。Python の `ctranslate2.dll`（4.6.0、/MD）に `system` でつなぐ案は、版と CRT が合わないため見送り。

### NLLB の差の原因の調査（PoC 1 の続き）

ソースから CTranslate2 をビルドする方式では、Python と完全に同じ結果にはできなかった。分かったこと:

| 試したこと | 結果 |
|---|---|
| MKL でビルド（`mkl` + Intel OpenMP。MKL は 2026.1 と、Python の wheel と同じ 2025.3） | 変わらず 2/4。行列計算ライブラリが原因ではない |
| float32 で実行 | Python と点数まで一致。差は int8 の経路だけで出る |
| Python の CTranslate2 を 4.6.3 / 4.8.2 に替える | 訳文は 4.6.0 と同じ。ただし点数は 4.6.0 と 4.8.2 で違う（例: -0.61860 と -0.62412） |
| ct2rs の同梱ソースと本家 v4.8.2 の比較 | 改行を除いて同一 |
| ct2rs のビルド設定 | cmake クレートが `CMAKE_CXX_FLAGS_RELEASE` を上書きして `/O2` と `NDEBUG` が外れていた。`CL=/O2 /Ob2 /DNDEBUG` で付けると 4/4 一致したが、点数は Python 4.8.2 と 1 文で少し違う（コンパイラの違い。CTranslate2 は一部で浮動小数点の並べ替えを許す最適化を使う） |

結論: 同じ結果を保証するには、Python と同じバイナリを使うしかない。

### PoC 1b: Python の wheel の `ctranslate2.dll` を Rust から呼ぶ

- 場所: `native/poc-ct2dll`。`shim/ct2_shim.cpp` が C の関数として公開する薄い受け口（自作）。`build.rs` が DLL の公開関数の一覧からインポートライブラリを作り、受け口を `/MD`、CTranslate2 4.6.0 のヘッダーでコンパイルする（C++ のオブジェクトが DLL の境界をまたぐので、CRT・STL・ヘッダーの版を DLL に合わせる）。呼び方は Python の拡張（`python/cpp/translator.cc`、`whisper.cc`、`replica_pool.h`）と同じ。
- Whisper の特徴量は numpy 1.26 の計算を 1 段ずつ再現した（`native/poc-ct2/src/mel.rs`）。FFT は倍精度で計算して complex64 に落とす。絶対値は numpy の SIMD の式（大きい方 × sqrt(fma(r, r, 1))）。フィルタ・窓・周波数は numpy と同じ順で計算する。フィルタとの行列積は numpy 同梱の OpenBLAS の `cblas_sgemm64_` を呼ぶ（OpenBLAS は CPU ごとに計算の中身が変わり、自前の足し算では 1 ビットずれる。int8 のモデルでは、この 1 ビットで `avg_logprob` が最大 0.02 動いた）。
- 言語判定は、faster-whisper と同じく、最後のフレームを含む最初の 30 秒を別にエンコードして行う。

| デバイス | Whisper（3 音声 + 無音） | NLLB（4 文） |
|---|---|---|
| CPU（int8） | 文字列・トークン・言語判定の確率・`avg_logprob`・`no_speech_prob` がすべて完全一致。メル特徴量も 0 個の差 | 訳文と点数（候補 2 つ）が完全一致 |
| CUDA（int8_float16、RTX 2080 Ti） | 同上、完全一致 | 完全一致 |

- CUDA は wheel の DLL がもともと対応している（`CUDA_DYNAMIC_LOADING`）。cuBLAS 12.8 と cuDNN 9.7（今の `requirements_cuda.txt` と同じ版）の DLL が PATH にあれば動く。終了時に固まることはなかった。CUDA Toolkit のインストールは不要（確認用に NVIDIA の公式の部品別アーカイブを `D:\WORKSPACE\poc-target\cuda-12.8` に展開した。ソースからビルドする場合にだけ要る）。
- 配布物: `ctranslate2.dll`（58 MB、MIT）、`libiomp5md.dll`、`cudnn64_9.dll`、numpy の OpenBLAS（36 MB、BSD-3。GCC のランタイムを含む）。今の Python 版が同梱しているものと同じ。
- 速さ: CPU は Python とほぼ同じ（Whisper 1 回 0.8〜1.5 秒、翻訳 0.26〜0.94 秒）。

## PoC 2: ONNX（ort 2.0.0-rc.13）

- 場所: `native/poc-ort`（`scripts/make_reference.py` が Python の基準、`src/main.rs` が Rust 版で `vad` / `yolox` / `ocr` / `all`）。

| 対象 | 結果 |
|---|---|
| Silero VAD | 合格。最大誤差 1.1e-16、判定の入れ替わり 0（361 フレーム） |
| YOLOX 吹き出し検出 | 合格。16 枚で箱の数・座標・スコアが一致。INT8 モデルなので、縮小処理を OpenCV の SIMD 経路と同じ整数計算に揃える必要があった（揃える前は箱が最大 76px ずれた） |
| PP-OCR（oar-ocr 0.10.0、使わない） | 不合格。通しで改行まで一致 10/14。認識モデル単体は 40/41 一致。差は oar-ocr の前後処理（det の正規化、dilation、全体の縮小・余白、向き判定モデル、行画像の縮小、並び順、bidi）を rapidocr と同じにできないため |
| PP-OCR（RapidOCR 3.9.2 の前後処理を自前で移植、後述） | 合格。吹き出し 70 枚 × 2 言語（自動 = PP-OCRv6 small、韓国語 = PP-OCRv5 mobile）で、前処理・検出の箱・行画像の大きさ・向き判定・認識の文字列と点数・最終結果が全段階で完全一致 |
| 1 プロセスで 3 つ同時 | 合格（Environment を共有、スレッド数は Session ごと） |
| 配布 | Python の `onnxruntime.dll`（1.30）を動的に読める。ort に取得させる方式（1.28 を静的リンク）も可 |
| DirectML / CUDA | どちらも動いた。ただし onnxruntime-gpu 1.30 は CUDA 13 用で、CTranslate2 の CUDA 12 と別に同梱が必要。今の Python も OCR・VAD は CPU なので、CPU で足りる |

- ort は rc のため `=` で版を固定する。

### OCR の移植（oar-ocr をやめて自前で移植）

- `native/poc-ort/src/rapidocr.rs`: RapidOCR 3.9.2 の流れ（画像の大きさの調整・縦の余白、DB 検出の後処理、行の切り出し、向き判定、CTC の復号、最終結果の座標の戻し）。Apache-2.0（RapidOCR / PaddleOCR）の表示あり。
- `native/poc-ort/src/cv.rs`: RapidOCR が使う OpenCV 4.11 の処理。`resize`（INTER_LINEAR の固定小数点、ちょうど半分のときの面積平均）、`dilate`、`findContours`（4.11 の新実装、RETR_LIST）、`convexHull`、`minAreaRect`、`boxPoints`、`fillPoly`、`mean`（マスク付き）、`getPerspectiveTransform`（LU）、`warpPerspective`（INTER_CUBIC、BORDER_REPLICATE）。opencv-python の Windows 版のビルド条件（MSVC 19.0、`/fp:precise`、SSE3、LAPACK なし、該当関数は IPP を使わない）に合わせて、丸めと float / double の混ぜ方まで同じにした。Apache-2.0（OpenCV）の表示あり。
- `native/poc-ort/src/npy.rs`: numpy 1.26 の `argsort`（introsort。Windows では SIMD 版に切り替わらない）、`mean`（ペアワイズ和）、`round`。BSD-3（numpy）の表示あり。
- 多角形の膨張（unclip）は pyclipper と同じ Clipper 6.4.2 のソースを同梱（`third_party/clipper`、Boost）。shapely の面積・周長は GEOS 3.13 と同じ計算順。
- 比較: `scripts/rapidocr_stages.py` が Python の各段階を書き出し、`poc-ort ocr` が段階ごとに比べて、最初に食い違った段階を数える。
- 速さ（70 枚、CPU 4 スレッド）: Rust 15.7 秒 / Python 19.7 秒（自動）、22.2 秒 / 25.7 秒（韓国語）。
- 未対応: アラビア語の表示順の並べ替え（python-bidi 0.6.11。中身は Rust の unicode-bidi クレートなので、同じ版を使えば揃えられる）。

## ここから決めること

1. ~~NLLB を完全に同じにするか~~ → 完全一致が必要と決定。PoC 1b（wheel の DLL を呼ぶ）で CPU / CUDA とも完全一致。ct2rs（ソースからのビルド）は使わない。
2. ~~CUDA 版の確認~~ → PoC 1b で確認済み。
3. ~~OCR~~ → rapidocr と同じ結果にすると決定。前後処理を自前で移植し、2 言語 × 70 枚で全段階が完全一致（PoC 2 の「OCR の移植」）。
4. PoC 3（VRChat の OSCQuery）: `native/poc-oscquery`（`vrchat_osc` 2.2.0、MIT/Apache-2.0。mDNS の VRChat 固有の癖への対処込み）。VRChat なしで起動・終了できることは確認済み。VRChat との組み合わせは実機で確認が要る。
