# native/

Rust バックエンドのワークスペース（設計: `docs/rust_backend_design_2026-10-11.md`）。
`vrct-audio` / `vrct-graphics`（今の Python 版が PyO3 で使うもの）と `poc-*` はワークスペースの外（それぞれ単独でビルドする）。

| 場所 | 中身 |
|---|---|
| `third_party.toml` | 同梱するネイティブ DLL（CTranslate2・onnxruntime・OpenBLAS・CUDA）の版と SHA-256。今の Python 版と同じ wheel から取り出す |
| `xtask/` | `cargo xtask fetch-native [--cuda]`: 上の DLL と CTranslate2 のヘッダーを `third_party/`（git 管理外）に置く |
| `vrct-contract/` | IPC の契約テスト。バックエンドを stdin / stdout だけで動かし、2 つのバックエンドの応答を比べる |
| `data/error_codes.json` | `errors.py` のエラーコード表（`reference/export_error_codes.py` で作る。Rust 版はこれを取り込む） |
| `reference/` | Python から基準データを書き出すスクリプト |

## ネイティブ DLL

```powershell
cd native
cargo xtask fetch-native          # CPU 版の分
cargo xtask fetch-native --cuda   # cuBLAS / cuDNN も (約 1.3 GB のダウンロード)
```

版を上げるときは `third_party.toml` の `version` / `wheel` / `sha256`（PyPI の JSON の `digests.sha256`）を書き換え、取り直してビルドし、回帰テストを流す。

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
