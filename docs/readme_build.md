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
- **Python 3.x**
- **Rust** (Tauri用)
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

### 3. Python環境のセットアップ

以下のコマンドで、CPU版とCUDA版の両方の仮想環境を作成します:

```bash
npm run setup-python
```

このコマンドは以下の処理を実行します:
- `.venv` (CPU版) の作成と依存関係のインストール
- `.venv_cuda` (CUDA版) の作成と依存関係のインストール

> **注意**: CUDA版を使用する場合は、NVIDIAのGPUとCUDA Toolkit 12.8が必要です。

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
4. Pythonバックエンドのビルド (`build-python`)
5. ViteとTauriの開発サーバー起動

### CUDA版の開発ビルド

```bash
npm run dev-cuda
```

CPU版と同様ですが、CUDA対応のPythonバックエンドをビルドします。

### UIのみの開発

バックエンドのビルドをスキップして、UIのみを開発する場合:

```bash
npm run dev-ui
```

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

### どこにバージョンを設定すればReleaseに反映されるか

- **設定箇所**: `package.json` の `version` が唯一のソース・オブ・トゥルース。
- **反映方法**: `npm run update-version`（`build`/`build-cuda`/`release`コマンド内でも自動実行）により、
	- `src-tauri/tauri.conf.json` の `version` に同期（Tauri/NSISインストーラーの表示・メタデータに使用）
	- `src-python/config.py` の `self._VERSION` に同期（ランタイム表示等に使用）
- **成果物への影響**:
	- インストーラー（NSIS）は `tauri.conf.json` の `version` を取り込み、プロダクトバージョンとして反映。
	- ZIPパッケージ名はスクリプト既定では固定（`VRCT.zip`/`VRCT_cuda.zip`）。ファイル名にバージョンを含めたい場合は、`package.json` の `release` スクリプトを調整してください。

### Pythonバックエンドのビルド

#### CPU版

```bash
npm run build-python
```

実行内容:

- `.venv` 環境をアクティベート
- PyInstallerで `spec/backend.spec` を使用してビルド
- 出力先: `src-tauri/bin/`

#### CUDA版

```bash
npm run build-python-cuda
```

実行内容:

- `.venv_cuda` 環境をアクティベート
- PyInstallerで `spec/backend_cuda.spec` を使用してビルド
- 出力先: `src-tauri/bin/`

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

			- name: Setup Python envs (.venv/.venv_cuda)
				run: |
					npm run setup-python

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

### プロセスの強制終了

```bash
npm run task-kill
```

VRCTに関連する実行中のプロセスを終了します。

## ディレクトリ構成

```
VRCT/
├── bat/                    # バッチスクリプト
│   ├── build.bat          # CPU版Pythonビルド
│   ├── build_cuda.bat     # CUDA版Pythonビルド
│   └── install.bat        # Python環境セットアップ
├── spec/                   # PyInstallerスペックファイル
│   ├── backend.spec       # CPU版ビルド設定
│   └── backend_cuda.spec  # CUDA版ビルド設定
├── src-python/            # Pythonバックエンドソースコード
├── src-tauri/             # Tauriアプリケーション設定
│   ├── bin/              # ビルド済みPythonバイナリ（生成）
│   └── target/           # Tauriビルド出力（生成）
├── src-ui/               # Reactフロントエンドソースコード
├── utils/                # ユーティリティスクリプト
│   ├── clean.py         # クリーンアップスクリプト
│   ├── task_kill.py     # プロセス終了スクリプト
│   ├── update_version.py # バージョン更新スクリプト
│   └── zip.py           # ZIPパッケージング
├── package.json          # Node.js設定とバージョン管理
├── requirements.txt      # Python依存関係（CPU版）
└── requirements_cuda.txt # Python依存関係（CUDA版）
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

- CUDA Toolkit 12.8がインストールされているか確認
- NVIDIA GPUドライバーが最新か確認
- `requirements_cuda.txt` の依存関係が正しくインストールされているか確認

### プロセスが残っている

```bash
npm run task-kill
```

を実行して、すべてのVRCTプロセスを終了してください。

## 参考情報

### PyInstallerスペックファイル

- `spec/backend.spec` - CPU版の設定
- `spec/backend_cuda.spec` - CUDA版の設定

これらのファイルでは、以下を設定しています:
- エントリーポイント: `src-python/mainloop.py`
- データファイル（フォント、プロンプト、言語ファイル等）のパス
- 依存ライブラリのパス

### バージョン管理フロー

1. `package.json` のバージョンを更新
2. `npm run update-version` を実行
3. 自動的に `tauri.conf.json` と `config.py` が更新される

### リリースパッケージの内容

ZIPファイルには以下が含まれます:
- `VRCT.exe` - メインアプリケーション
- `VRCT-sidecar.exe` - Pythonバックエンド
- `_internal/` - 必要な依存ファイル

## ライセンス

プロジェクトのライセンスについては、`LICENSE` ファイルを参照してください。
