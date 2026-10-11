# native/

Rust バックエンドのワークスペース（設計: `docs/rust_backend_design_2026-10-11.md`）。
`vrct-audio` / `vrct-graphics`（今の Python 版が PyO3 で使うもの）と `poc-*` はワークスペースの外（それぞれ単独でビルドする）。

| 場所 | 中身 |
|---|---|
| `third_party.toml` | 同梱するネイティブ DLL（CTranslate2・onnxruntime・OpenBLAS・CUDA）の版と SHA-256。今の Python 版と同じ wheel から取り出す |
| `xtask/` | `cargo xtask fetch-native [--cuda]`: 上の DLL と CTranslate2 のヘッダーを `third_party/`（git 管理外）に置く |
| `vrct-contract/` | IPC の契約テスト。バックエンドを stdin / stdout だけで動かし、2 つのバックエンドの応答を比べる |
| `vrct-ct2/` | CTranslate2（wheel の `ctranslate2.dll`）の受け口。C の shim と安全な Rust の型 |
| `vrct-whisper/` | faster-whisper 1.1.1 の `transcribe`（VRCT が通る経路）。メル特徴量は numpy と同じ計算 |
| `vrct-ocr/` | 吹き出し検出（YOLOX）と RapidOCR 3.9.2 の移植（OpenCV / numpy の該当処理、Clipper、bidi） |
| `vrct-backend/` | バックエンド本体。今は翻訳（NLLB / M2M100）と音訳（Sudachi + ヘボン式）、HF のキャッシュの読み方 |
| `data/error_codes.json` | `errors.py` のエラーコード表（`reference/export_error_codes.py` で作る。Rust 版はこれを取り込む） |
| `data/sudachi/` | SudachiPy 0.6.10 と同じリソース（sudachi.rs v0.6.10、Apache-2.0）。辞書（`system.dic`）は別 |
| `reference/` | Python から基準データを書き出すスクリプトと、照合用の文（`corpus/`） |
| `testdata/` | 基準データ（Python の出力）と照合用の音声・画像。音声と画像は合成したもの |

## ネイティブ DLL

```powershell
cd native
cargo xtask fetch-native          # CPU 版の分
cargo xtask fetch-native --cuda   # cuBLAS / cuDNN も (約 1.3 GB のダウンロード)
```

版を上げるときは `third_party.toml` の `version` / `wheel` / `sha256`（PyPI の JSON の `digests.sha256`）を書き換え、取り直してビルドし、回帰テストを流す。

## 推論の照合（P1）

Python 版が出した基準（`testdata/`）と、Rust 版の出力が完全に一致するかを見る。重み・辞書・モデルは環境変数で場所を渡す（無ければそのテストは「SKIPPED」と出して飛ばす）。

```powershell
cd native
$env:VRCT_WEIGHTS_ROOTS = "D:\WORKSPACE\WORK\VRChatProject\VRCT\src-python;<M2M100 を置いた weights の親>"
$env:VRCT_SUDACHI_DICT = "<venv>\Lib\site-packages\sudachidict_fullesources\system.dic"
$env:VRCT_RAPIDOCR_MODELS = "<venv>\Lib\site-packagesapidocr\models"
$env:VRCT_OCR_DATASET_REF = "<repo>	mp\ocr-dataset-cpu.json"   # 実際のスクリーンショットの基準 (任意、リポジトリに置かない)
cargo test --release -p vrct-whisper -p vrct-ocr -p vrct-backend -- --nocapture
```

- `VRCT_TEST_CUDA=1` で `*-cuda.json` も比べる。cuBLAS / cuDNN（`fetch-native --cuda`）を PATH に入れておく。
- 基準の作り直し: `reference/export_{nmt,whisper,ocr,translit}.py`（各ファイルの先頭に使い方）。音声は `reference/make_audio_corpus.ps1`、画像は `reference/make_ocr_corpus.py` で作る（声やフォントは PC で違うので、作り直したら基準も作り直す）。
- 数値の一致は AVX2 / FMA を持つ x64 CPU が前提（numpy・OpenBLAS が CPU で計算方法を変えるため）。

## 契約テスト

```powershell
cd native
cargo build -p vrct-contract
$repo = (Resolve-Path ..).Path
# Python 版 (このブランチの vrct_audio / vrct_graphics を使う)
.\target\debug\vrct-contract.exe run --python D:\WORKSPACE\WORK\VRChatProject\VRCT\.venv\Scripts\python.exe `
  --src "$repo\src-python" --pythonpath "$repo\tmp\native-site;$repo\tmp\graphics-site" --name python --out target\contract\python.json
# Rust 版 (P4 以降)
.\target\debug\vrct-contract.exe run --exe <VRCT-sidecar.exe> --weights "$repo\src-python\weights" --name rust --out target\contract\rust.json
.\target\debug\vrct-contract.exe compare target\contract\python.json target\contract\rust.json
```

- バックエンドは `target/contract-run/<name>/` にコピーして動かす（`config.json` やログはそこに書かれ、本物には触れない）。重みはジャンクションで本物を読む。
- 外部ネットワークは存在しないプロキシで止める（毎回同じ「オフライン」の起動になる）。
- テストの組は `vrct-contract/cases/*.toml`（ファイル名の順に、上から順に送る）。`rule` は `exact`（既定）/ `shape`（起動ごとに変わる値）/ `status`。`expect_status` はどのバックエンドでも守るべき status。
- 機器・外部を動かすもの（録音の開始、更新のインストーラ、エクスプローラーを開く、VRChat へのチャット送信など）は入れない。チャットの送信は、先に VRChat への送信を OFF にしてから。
- 同じ PC で Python 版を 2 回動かして比べ、差が 0 になることを確かめてある（起動ごとに変わる値は `websocket_auth_token` と `vr_panel_layout` の 2 つ）。
