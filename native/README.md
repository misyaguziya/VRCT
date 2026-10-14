# native/

Rust バックエンドのワークスペース（設計: `docs/rust_backend_design_2026-10-11.md`）。
`poc-oscquery` はワークスペースの外（単独でビルドする）。

Python 版のコードは削除した。基準データ（`testdata/`）は、削除の前に Python 版から書き出したもの。書き出したスクリプトは git の履歴にある（Python のコードが残っている最後のコミットは `6c68cfd6`。ただし配布用のデータは `c71c465d` で `native/data/` へ移したので、Python 版を動かすならその前の `051aed5d`）。契約テストの基準（`vrct-contract/baseline.json`）は Rust 版の確認済みの応答。

### 基準データの扱い（Python 版を消した後）

- 今の仕様は Rust 版。`testdata/` は「Python 版と同じに作った」証拠として残し、書き出し直さない（書き出し直すと、Rust で意図して変えた仕様が Python の仕様へ戻る）。
- Rust 側で挙動を意図して変えたときは、その分だけ `testdata/` の値を手で直し、コミットメッセージに理由を書く（例: 9c78ee27 の `config/checks.json`、VR UI の初期値）。
- Python 版の挙動を確かめたいときは、上のコミットのコードを読む（動かすなら別の worktree で）。
- 画面からの操作の回帰は契約テスト（下）で見る。

| 場所 | 中身 |
|---|---|
| `third_party.toml` | 同梱するネイティブ DLL（CTranslate2・onnxruntime・OpenBLAS・CUDA）と辞書・モデルの版と SHA-256。Python 版が使っていたのと同じ wheel から取り出す |
| `xtask/` | `cargo xtask fetch-native [--cuda]`: 上の DLL と CTranslate2 のヘッダーを `third_party/`（git 管理外）に置く |
| `vrct-contract/` | IPC の契約テスト。バックエンドを stdin / stdout だけで動かし、確認済みの応答 (`baseline.json`) と比べる |
| `vrct-ct2/` | CTranslate2（wheel の `ctranslate2.dll`）の受け口。C の shim と安全な Rust の型 |
| `vrct-whisper/` | faster-whisper 1.1.1 の `transcribe`（VRCT が通る経路）。メル特徴量は numpy と同じ計算 |
| `vrct-ocr/` | 吹き出し検出（YOLOX）と RapidOCR 3.9.2 の移植（OpenCV / numpy の該当処理、Clipper、bidi） |
| `vrct-backend/` | バックエンド本体。今は翻訳（NLLB / M2M100・LLM・DeepL・Web 翻訳の入口）、音訳（Sudachi + ヘボン式）、文字起こしの API、重みとトークナイザーの取得、ソフトの更新、テレメトリー、WebSocket・OBS のサーバー |
| `vrct-webtranslate/` | Web 翻訳（Google / Bing / Papago）。`translator_engines` のソースを取り込み、PyO3 の入口を外したもの |
| `data/` | 配布に入れるデータ（翻訳設定・フォント・OCR のモデル・Sudachi のリソース）と、Python 版から書き出した表（エラーコード・設定のスキーマ・文字起こしの言語） |
| `reference/` | 照合用の文（`corpus/`）と、照合用の音声を作るスクリプト |
| `testdata/` | 基準データ（Python 版の出力）と照合用の音声・画像。音声と画像は合成したもの |

## ネイティブ DLL

```powershell
cd native
cargo xtask fetch-native          # CPU 版の分
cargo xtask fetch-native --cuda   # cuBLAS / cuDNN も (約 1.3 GB のダウンロード)
```

版を上げるときは `third_party.toml` の `version` / `wheel` / `sha256`（PyPI の JSON の `digests.sha256`）を書き換え、取り直してビルドし、回帰テストを流す。

## 推論の照合（P1）

Python 版が出した基準（`testdata/`）と、Rust 版の出力が完全に一致するかを見る（Python は使わない）。重み・辞書・モデルは環境変数で場所を渡す（無ければそのテストは「SKIPPED」と出して飛ばす）。

```powershell
cd native
$env:VRCT_WEIGHTS_ROOTS = "<weights を置いたフォルダの親>;<M2M100 を置いた weights の親>"
$env:VRCT_SUDACHI_DICT = "<venv>\Lib\site-packages\sudachidict_full\resources\system.dic"
$env:VRCT_RAPIDOCR_MODELS = "<venv>\Lib\site-packages\rapidocr\models"
$env:VRCT_OCR_DATASET_REF = "<repo>\tmp\ocr-dataset-cpu.json"   # 実際のスクリーンショットの基準 (任意、リポジトリに置かない)
cargo test --release -p vrct-whisper -p vrct-ocr -p vrct-backend -- --nocapture
```

- `VRCT_TEST_CUDA=1` で `*-cuda.json` も比べる。cuBLAS / cuDNN（`fetch-native --cuda`）を PATH に入れておく。
- 基準を足す・作り直すときは、Python 版が残っているコミット（上）を別の worktree に出し、そこの `reference/export_*.py` を使う。音声は `reference/make_audio_corpus.ps1` で作る（声は PC で違うので、作り直したら基準も作り直す）。
- 数値の一致は AVX2 / FMA を持つ x64 CPU が前提（numpy・OpenBLAS が CPU で計算方法を変えるため）。

## 外部 API・ファイルの照合（P2）

Python 版が送った HTTP の要求を、送る直前（httpx / requests / urllib）で横取りして記録したもの（`testdata/{llm,deepl,transcription,update,weights,telemetry,obs}/`）と、Rust 版がローカルの模擬サーバーへ送った要求を比べる。外部へは何も送らない。

```powershell
cd native
cargo test -p vrct-backend -p vrct-webtranslate
```

- 基準の作り直しは P1 と同じく、Python 版が残っているコミットの `reference/export_*.py` で（記録の仕組みは `reference/http_capture.py`）。記録に秘密を残さない: `export_weights.py` は `HF_HUB_DISABLE_IMPLICIT_TOKEN=1` で動かし、鍵は偽物を使う。

## 契約テスト

Rust 版をいつもの UI と同じく stdin / stdout だけで動かし、確認済みの応答 `vrct-contract/baseline.json` と比べる
（画面からの操作の回帰テスト）。最初の 216 件は Python 版の応答と一致を確かめたもの、残りは Rust 版の応答を読んで
確かめたもの。

```powershell
cd native
cargo build --release -p vrct-contract
# 配布と同じ形 (exe の隣の _internal に DLL・データ・モデル・ライセンス) に並べる
# DLL・Sudachi の辞書・Silero・RapidOCR のモデルは third_party.toml から (fetch-native が SHA-256 を確かめて取る)
cargo xtask fetch-native
cargo xtask stage-sidecar --out target\sidecar-stage --release
.\target\release\vrct-contract.exe run --exe target\sidecar-stage\VRCT-sidecar.exe --weights <weights のフォルダ> --name rust --out target\contract\rust.json --against vrct-contract\baseline.json
```

- 差が無ければ終了コード 0。差があれば `DIFF` に、ケース名と基準・今回の応答が出る。
- 重みは CPU 版の `nllb-200-distilled-600M-ct2-int8` が要る（チャットの翻訳の結果を完全一致で比べる。CUDA 版では訳が変わりうる）。
- 挙動を意図して変えたときは、差が意図どおりか読んでから、基準を取り直す: `.\target\release\vrct-contract.exe accept target\contract\rust.json`（問題のある記録は受け付けない）。
- 基準には規則で比べるものだけが残る（`shape` の値は形を保って空にし、`status` の結果は捨てる）。デバイス名・GPU・トークンは入らないのでコミットしてよい。
- バックエンドは `target/contract-run/<name>/` にコピーして動かす（`config.json` やログはそこに書かれ、本物には触れない）。重みはジャンクションで本物を読む。
- 外部ネットワークは存在しないプロキシで止める（毎回同じ「オフライン」の起動になる）。API キーのケースは、通信できないときの判定を見る。
- テストの組は `vrct-contract/cases/*.toml`（ファイル名の順に、上から順に送る。状態は前のケースから続く）。
  - `rule` は `exact`（既定）/ `shape`（起動ごと・PC ごとに変わる値。空の一覧はどの一覧とも一致）/ `status`。
  - `expect_status` は毎回確かめる status。500 は「問題」として扱うが、`expect_status = 500` のケース（検証の例外を捕まえない handler。Python 版と同じ）は除く。
  - `pushes = true` のケースは、応答の前に届いた push（endpoint・status・結果）も完全一致で比べる。
- 機器・外部を動かすもの（録音の開始、更新のインストーラ、エクスプローラーを開く、VRChat へのチャット送信など）は入れない。チャットの送信は、先に VRChat への送信を OFF にしてから。
- 録音デバイス・計算デバイス・重みの有無・版は PC や時期で変わるので `shape` で比べる（どの PC でも同じ基準で回せる）。
