# VRCTビルドガイド

このドキュメントでは、VRCTプロジェクトのビルド方法について説明します。

## 目次

- [必要な環境](#必要な環境)
- [初回セットアップ](#初回セットアップ)
- [ビルドの種類](#ビルドの種類)
- [開発ビルド](#開発ビルド)
- [リリースビルド](#リリースビルド)
- [ビルドプロセスの詳細](#ビルドプロセスの詳細)
- [トラブルシューティング](#トラブルシューティング)

## 必要な環境

### 必須ソフトウェア

- **Node.js** (npm含む)
- **Python 3.x** (バージョン同期・ZIP 作成などの補助スクリプト用。`dev-fast` で Python 版を動かすときは仮想環境も)
- **Rust** (Tauri とバックエンド用。MSVC ツールチェーン)
- **Git**

### 推奨環境

- Windows 10/11
- メモリ: 8GB以上
- ストレージ: 5GB以上の空き容量

## 初回セットアップ

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd VRCT
```

### 2. Node.js依存関係のインストール

```bash
npm install
```

### 3. バックエンドの依存

バックエンドは Rust 製 (`native/vrct-backend`、出力は `VRCT-sidecar.exe`) です。
DLL (CTranslate2・ONNX Runtime・OpenVR など)、Sudachi の辞書、Silero VAD、
RapidOCR のモデルは `native/third_party.toml` に版と SHA-256 が書いてあり、
ビルド時に `cargo xtask fetch-native` が取得・検証して `native/third_party/` に置きます
（`build-sidecar` の中で自動実行。手動の準備は不要）。

> **注意**: CUDA版を使用する場合は、CUDA 12.8対応のNVIDIA GPUドライバーが必要です。
> CUDA Toolkit のインストールは不要です。ctranslate2 が使う cuBLAS / cuDNN は
> `fetch-native --cuda` が `nvidia-*-cu12` wheel から取り出し、ビルド時に同梱されます。

Python 版のバックエンド (`src-python`) を `dev-fast` で動かす場合だけ、
`npm run setup-python` で `.venv` / `.venv_cuda` を作成してください。

## ビルドの種類

VRCTでは、以下の2種類のビルドが可能です:

### CPU版
標準的なCPUで動作するバージョン。GPUは不要。

### CUDA版
NVIDIA GPUを活用した高速処理版。CUDA対応GPUが必要。

## 開発ビルド

開発中にアプリケーションを実行・テストするためのビルドです。

### CPU版の開発ビルド

```bash
npm run dev
```

このコマンドは以下を実行します:
1. 実行中のプロセスを終了 (`task-kill`)
2. ビルドファイルのクリーンアップ (`clean`)
3. バージョン情報の更新 (`update-version`)
4. バックエンドのビルド (`build-sidecar`)
5. ViteとTauriの開発サーバー起動

### CUDA版の開発ビルド

```bash
npm run dev-cuda
```

CPU版と同様ですが、cuBLAS / cuDNN を同梱したバックエンドをビルドします (`build-sidecar-cuda`)。

### UIのみの開発

バックエンドのビルドをスキップして、UIのみを開発する場合:

```bash
npm run dev-ui
```

### 高速開発ビルド（推奨: 日常検証用）

インストーラー用の配置を毎回作らず、dev 用 sidecar ラッパーから
バックエンドを直接起動する高速ループです。

```bash
# Rust 版: native/target/sidecar-stage/VRCT-sidecar.exe を起動
npm run dev-rust-fast
```

`dev-rust-fast` の前に、`native/` で Rust 版をビルドして配置しておきます
（設定ファイル・ログは `native/target/sidecar-stage/` に書かれます）:

```bash
cd native
cargo xtask fetch-native
cargo build -p vrct-backend --bin VRCT-sidecar
cargo xtask stage-sidecar --out target\sidecar-stage
```

Python 版 (`src-python`) を仮想環境の Python で直接起動する場合:

```bash
# 標準環境: .venv/Scripts/python.exe
npm run dev-fast

# CUDA環境: .venv_cuda/Scripts/python.exe
npm run dev-cuda-fast
```

どちらのコマンドも以下を実行します:

1. 実行中のプロセスを終了 (`task-kill`)
2. dev 用 sidecar ラッパー（`utils/dev_sidecar/`, Rust 製の薄いバイナリ）を
   ビルドして `src-tauri/bin/` に配置 (`sidecar-dev`)
3. Vite と Tauri の開発サーバー起動 (`dev-ui`)

前提:

- 選択した仮想環境と依存関係が準備済みであること
  - `dev-fast`: `.venv/Scripts/python.exe`
  - `dev-cuda-fast`: `.venv_cuda/Scripts/python.exe`（`.venv` は不要）
- Rust ツールチェーン (`cargo`) が使えること（既に Tauri で必要）

各コマンドが `VRCT_DEV_VENV` を設定し、Tauri 経由で dev 用 sidecar に
使用する環境を渡します。選択した環境が存在しない場合はエラーで停止し、
別の仮想環境への自動切り替えは行いません。環境の有効化（activate）は不要です。

配布 EXE と同一挙動になる根拠:

- Python コード側は `_internal/...` バンドルパスと開発ツリー相対パスの
  両対応が入っており、venv 直起動でもリソース探索が正しく解決される
  （`src-python/models/overlay/overlay_image.py` ほか）
- Tauri 側の sidecar 起動ロジックは共通のまま（EXE ファイル名は不変）

配布形式そのものを確認したい場合は `npm run dev` / `npm run build` を使ってください。

## リリースビルド

配布用のインストーラーを作成するビルドです。

### CPU版のリリースビルド

```bash
npm run build
```

または、ZIP形式でパッケージング:

```bash
npm run release
```

生成されるファイル:
- インストーラー: `src-tauri/target/release/bundle/nsis/`
- ZIPファイル: `VRCT.zip` (releaseコマンド使用時)

### CUDA版のリリースビルド

```bash
npm run build-cuda
```

または、ZIP形式でパッケージング:

```bash
npm run release-cuda
```

生成されるファイル:
- インストーラー: `src-tauri/target/release/bundle/nsis/`
- ZIPファイル: `VRCT_cuda.zip` (release-cudaコマンド使用時)

### 両バージョンの同時ビルド

CPU版とCUDA版の両方をビルドする場合:

```bash
npm run release-all
```

## ビルドプロセスの詳細

### バージョン管理

バージョンは `package.json` で一元管理され、以下のファイルに自動で同期されます:

```bash
npm run update-version
```

更新されるファイル:
- `src-tauri/tauri.conf.json`
- `src-python/config.py`

Rust のバックエンドはビルド時に `package.json` の `version` を直接読みます (`native/vrct-backend/build.rs`)。

### どこにバージョンを設定すればReleaseに反映されるか

- **設定箇所**: `package.json` の `version` が唯一のソース・オブ・トゥルース。
- **反映方法**: `npm run update-version`（`build`/`build-cuda`/`release`コマンド内でも自動実行）により、
	- `src-tauri/tauri.conf.json` の `version` に同期（Tauri/NSISインストーラーの表示・メタデータに使用）
	- `src-python/config.py` の `self._VERSION` に同期（ランタイム表示等に使用）
- **成果物への影響**:
	- インストーラー（NSIS）は `tauri.conf.json` の `version` を取り込み、プロダクトバージョンとして反映。
	- ZIPパッケージ名はスクリプト既定では固定（`VRCT.zip`/`VRCT_cuda.zip`）。ファイル名にバージョンを含めたい場合は、`package.json` の `release` スクリプトを調整してください。

### バックエンドのビルド

#### CPU版

```bash
npm run build-sidecar
```

実行内容 (`bat/build.bat`、`native/` で):

- `cargo xtask fetch-native` — DLL・辞書・モデル・ライセンスを取得し SHA-256 を検証
- `cargo build --release -p vrct-backend --bin VRCT-sidecar`
- `cargo xtask stage-sidecar --release` — exe と `_internal/` を `src-tauri/bin/` に配置

`_internal/` の中身:

- DLL (ctranslate2・onnxruntime・openvr_api・OpenBLAS など)
- `translation_settings/`, `fonts/`, `sudachi/` (system.dic), `silero/`, `ocr/` (YOLOX と RapidOCR のモデル)
- `licenses/` — 同梱物のライセンス。Rust のクレートの分は `native/vrct-backend/THIRD_PARTY_LICENSES.txt`
  （依存を変えたら `python tools/collect_rust_licenses.py native/vrct-backend` で作り直す）

#### CUDA版

```bash
npm run build-sidecar-cuda
```

CPU版の手順に `--cuda` を付けたもの (`bat/build_cuda.bat`)。cuBLAS / cuDNN の DLL が `_internal/` に加わります。

### フロントエンドのビルド

```bash
npm run vite-build
```

Viteを使用してフロントエンド（React）をビルドし、`dist/` ディレクトリに出力します。

### Tauriアプリケーションのビルド

```bash
npm run tauri build
```

Tauriを使用して最終的なデスクトップアプリケーションをビルドします。

## GitHub ActionsでのRelease自動化

Windows用のReleaseをGitHub Actionsで自動生成・公開する例です。`package.json` のバージョンをタグ・リリース名に使い、TauriのNSISインストーラーとZIPを添付します。

### 推奨トリガー

- タグプッシュ（例: `v*`）または手動実行（`workflow_dispatch`）

### サンプルワークフロー（Windows）

```yaml
name: Release (Windows)

on:
	workflow_dispatch: {}
	push:
		tags:
			- 'v*'

jobs:
	build-release-windows:
		runs-on: windows-latest

		steps:
			- name: Checkout
				uses: actions/checkout@v4

			- name: Setup Node
				uses: actions/setup-node@v4
				with:
					node-version: '20'

			- name: Setup Python
				uses: actions/setup-python@v5
				with:
					python-version: '3.11'

			- name: Setup Rust
				uses: dtolnay/rust-toolchain@stable

			- name: Install dependencies
				run: |
					npm ci

			- name: Sync versions from package.json
				run: |
					npm run update-version

			- name: Build (CPU)
				run: |
					npm run build

			- name: Package ZIP (CPU)
				run: |
					python utils/zip.py --zip_name VRCT.zip

			- name: Read version from package.json
				id: pkg
				shell: pwsh
				run: |
					$version = (Get-Content package.json | ConvertFrom-Json).version
					echo "version=$version" >> $env:GITHUB_OUTPUT

			- name: Upload artifacts
				uses: actions/upload-artifact@v4
				with:
					name: VRCT-windows-${{ steps.pkg.outputs.version }}
					path: |
						src-tauri/target/release/bundle/nsis/**/*
						VRCT.zip

			- name: Create GitHub Release
				uses: softprops/action-gh-release@v2
				with:
					tag_name: v${{ steps.pkg.outputs.version }}
					name: VRCT v${{ steps.pkg.outputs.version }}
					files: |
						src-tauri/target/release/bundle/nsis/**/*
						VRCT.zip
				env:
					GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### ポイント
- ビルド前に必ず `npm run update-version` を実行して、`tauri.conf.json` と `config.py` にバージョンを同期します。
- アーティファクトのパスは既定構成に合わせています：
	- インストーラー: `src-tauri/target/release/bundle/nsis/`
	- ZIP: ルート直下の `VRCT.zip`
- CUDA版も同様にビルドする場合は、`npm run build-cuda` と `python utils/zip.py --zip_name VRCT_cuda.zip` を追加して、別アーティファクト名でアップロード・添付してください。

## ユーティリティコマンド

### クリーンアップ

```bash
npm run clean
```

以下のディレクトリを削除します:
- `build/`
- `dist/`
- `src-tauri/bin/`
- `src-tauri/target/`

Rust のインクリメンタルビルド結果 (`src-tauri/target/`) を残したい場合は
`--soft` 版を使ってください:

```bash
npm run clean-soft
```

こちらは `build/`, `dist/`, `src-tauri/bin/` のみを削除します。

### プロセスの強制終了

```bash
npm run task-kill
```

VRCTに関連する実行中のプロセスを終了します。

## ディレクトリ構成

```
VRCT/
├── bat/                    # バッチスクリプト
│   ├── build.bat          # CPU版バックエンドのビルドと配置
│   ├── build_cuda.bat     # CUDA版バックエンドのビルドと配置
│   ├── install.bat        # Python環境セットアップ (dev-fast の Python 版用)
│   └── sidecar_dev.bat    # dev-fast用sidecarラッパービルド
├── native/                # Rust バックエンド (vrct-backend) とその部品、xtask
│   └── third_party.toml  # 同梱する DLL・辞書・モデルの版と SHA-256
├── src-python/            # Python 版バックエンド (安定版のリリース用に残している)
├── src-tauri/             # Tauriアプリケーション設定
│   ├── bin/              # ビルド済みバックエンドと _internal（生成）
│   └── target/           # Tauriビルド出力（生成）
├── src-ui/               # Reactフロントエンドソースコード
├── utils/                # ユーティリティスクリプト
│   ├── clean.py         # クリーンアップスクリプト
│   ├── dev_sidecar/     # dev-fast用のvenv直起動ラッパー(Rust)
│   ├── task_kill.py     # プロセス終了スクリプト
│   ├── update_version.py # バージョン更新スクリプト
│   └── zip.py           # ZIPパッケージング
├── package.json          # Node.js設定とバージョン管理
├── requirements.txt      # Python依存関係（CPU版）
└── requirements_cuda.txt # Python依存関係（CUDA版。requirements.txt + CUDAライブラリ）
```

## トラブルシューティング

### Python環境のエラー

仮想環境を再作成してください:

```bash
npm run setup-python
```

### ビルドが失敗する

1. クリーンアップを実行:
```bash
npm run clean
```

2. Node.js依存関係を再インストール:
```bash
npm install
```

3. 再度ビルド:
```bash
npm run build
```

### CUDA版が動作しない

- NVIDIA GPUドライバーが最新か確認（CUDA Toolkit のインストールは不要）
- `_internal/` に `cublas64_12.dll` / `cudnn64_9.dll` などの CUDA の DLL があるか確認
  (`build-sidecar-cuda` で入る)。ctranslate2 はGPU実行時にこれらを
  実行時ロードする。無ければGPUは計算デバイス一覧に出ない

### プロセスが残っている

```bash
npm run task-kill
```

を実行して、すべてのVRCTプロセスを終了してください。

## 参考情報

### バージョン管理フロー

1. `package.json` のバージョンを更新
2. `npm run update-version` を実行
3. 自動的に `tauri.conf.json` と `config.py` が更新される（Rust のバックエンドはビルド時に `package.json` を読む）

## β版リリース

実際のリリースは `.github/workflows/release.yml` が `v*` タグのpushで自動実行しますが、
タグ名に `-beta` または `-rc` を含めることで、公開先を本番と分離したβ版として配布できます。

### リリース手順

1. `package.json` の `version` を `3.5.0-beta.1` のようなpre-release識別子付きの値にする
2. `npm run update-version` を実行(通常のビルド/リリースコマンド内で自動実行されるため手動実行は不要)
3. `v3.5.0-beta.1` のようなタグを打ってpush

```bash
git tag v3.5.0-beta.1
git push origin v3.5.0-beta.1
```

### 本番版との違い

| 項目 | 本番版 (`v3.5.0`) | β版 (`v3.5.0-beta.1`) |
|---|---|---|
| GitHub Release | `prerelease: false` | `prerelease: true` |
| Hugging Face公開先 | `ms-software/VRCT` | `ms-software/VRCT-beta` |
| インストーラー(setup.exe)の既定ダウンロード元 | `ms-software/VRCT` | `ms-software/VRCT-beta`(バージョン文字列の `-beta`/`-rc` から自動判定、または `/CHANNEL=` 指定) |

> **事前準備**: β用のHugging Faceリポジトリ `ms-software/VRCT-beta` は
> CIでは自動作成されないため、初回は手動で作成しておく必要があります。

### チャンネル切り替え・旧バージョンへのロールバック

GitHub Releasesで配布されるsetup.exeは、実行時にHugging Faceから本体一式を
ダウンロードするダウンローダー形式です。そのため、通常はGitHub Releasesの
古いバージョンのsetup.exeを取得しても、その時点の最新版がインストールされてしまいます。

チャンネル・バージョンの指定はGUI画面ではなく `/CHANNEL=` `/VERSION=` の
CLI引数でのみ行えます(setup.exe自体はどのバージョン・チャンネルのものでも
構いません)。setup.exeを単体でダブルクリックした場合はこれらの引数が付かない
ため、CPU/GPU選択のみでビルド元チャンネルの最新版がインストールされます
(GUI上に選択肢を増やさないための意図的な設計です)。VRCT本体のUpdaterタブ
からの更新はこれらの引数を自動的に付与して起動します。

```bash
VRCT_setup.exe /CHANNEL=beta
VRCT_setup.exe /VERSION=3.4.2
```

`/VERSION=` を指定した場合は、そのバージョン文字列に `-beta` または `-rc` が
含まれるかどうかで自動的にダウンロード元リポジトリ(`ms-software/VRCT` /
`ms-software/VRCT-beta`)を判定します(`/CHANNEL=` の指定より優先されます)。
`/VERSION=` を指定しない場合は `/CHANNEL=`(省略時はこのsetup.exe自身が
ビルドされたチャンネル)の最新版をダウンロードします。指定したバージョンが
Hugging Face上に存在しない場合はダウンロードに失敗し、インストールが
中断されます。

### リリースパッケージの内容

ZIPファイルには以下が含まれます:
- `VRCT.exe` - メインアプリケーション
- `VRCT-sidecar.exe` - バックエンド (Rust)
- `_internal/` - 必要な依存ファイル

## ライセンス

プロジェクトのライセンスについては、`LICENSE` ファイルを参照してください。
