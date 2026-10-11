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

## PoC 2: ONNX（ort 2.0.0-rc.13）

- 場所: `native/poc-ort`（`scripts/make_reference.py` が Python の基準、`src/main.rs` が Rust 版で `vad` / `yolox` / `ocr` / `all`）。

| 対象 | 結果 |
|---|---|
| Silero VAD | 合格。最大誤差 1.1e-16、判定の入れ替わり 0（361 フレーム） |
| YOLOX 吹き出し検出 | 合格。16 枚で箱の数・座標・スコアが一致。INT8 モデルなので、縮小処理を OpenCV の SIMD 経路と同じ整数計算に揃える必要があった（揃える前は箱が最大 76px ずれた） |
| PP-OCR（oar-ocr 0.10.0） | 不合格。通しで改行まで一致 10/14。認識モデル単体は 40/41 一致。差は oar-ocr の前後処理（det の正規化、dilation、全体の縮小・余白、向き判定モデル、行画像の縮小、並び順、bidi）を rapidocr と同じにできないため |
| 1 プロセスで 3 つ同時 | 合格（Environment を共有、スレッド数は Session ごと） |
| 配布 | Python の `onnxruntime.dll`（1.30）を動的に読める。ort に取得させる方式（1.28 を静的リンク）も可 |
| DirectML / CUDA | どちらも動いた。ただし onnxruntime-gpu 1.30 は CUDA 13 用で、CTranslate2 の CUDA 12 と別に同梱が必要。今の Python も OCR・VAD は CPU なので、CPU で足りる |

- ort は rc のため `=` で版を固定する。oar-ocr は Rust 1.95 以上が必要で、ort の版にも縛られる。

## ここから決めること

1. NLLB の結果を今と完全に同じにするか（MKL でビルドする。`nuget.exe` と Intel MKL のパッケージのダウンロードが必要）、言い回しの差を許容して oneDNN にするか。
2. CTranslate2 の CUDA 版の確認（CUDA Toolkit 12.x のインストールが必要）。
3. OCR を rapidocr と同じ結果にするか（YOLOX と同じく ort の上に PP-OCR の前後処理を自作する）、oar-ocr の差を許容するか。
4. PoC 3（VRChat の OSCQuery）は実機が必要。
