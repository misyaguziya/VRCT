# 収集ツールのexe配布

`dist/VRCT-Dataset-Collector-windows-x64.zip` が配布用。
展開後に `VRCT-Dataset-Collector.exe` をダブルクリックすると撮影を開始する。
Python、VRCT本体、CUDAのインストールは不要。Windows 10/11 x64向け。
VR取得にはSteamVRと、そこで動作中のVRChatが必要。

既定の保存先はexeと同じフォルダの `dataset_collected/`。
書き込める場所へZIP全体を展開する。`--out` で保存先を変更できる。
操作・取得条件は同梱READMEと [収集手順](ocr_dataset_collection.md) を参照。

## 再ビルド

既存の `.venv` に対象依存がある場合:

```powershell
.\bat\build_dataset_collector.bat
```

別の開発PCで準備する場合は、Windows x64のCPython 3.11で専用環境を作る。
本番VRCTの依存を変更する必要はない。

```powershell
py -3.11 -m venv .venv-collector
.\.venv-collector\Scripts\python.exe -m pip install -r requirements-dataset-collector.txt
$env:VRCT_COLLECTOR_PYTHON = "$PWD\.venv-collector\Scripts\python.exe"
.\bat\build_dataset_collector.bat
```

出力:

- `dist/VRCT-Dataset-Collector/`: 動作確認用の展開済みパッケージ
- `dist/VRCT-Dataset-Collector-windows-x64.zip`: 配布するZIP
- `dist/VRCT-Dataset-Collector-windows-x64.zip.sha256`: ZIPのSHA-256

ビルドは依存バージョンの確認、PyInstaller onefile生成、画像を撮影しないCLI起動検査、
ライセンス・README・環境情報の同梱、ZIP化を行う。
撮影済み画像や設定・APIキーは同梱しない。既存の収集画像は削除しない。
VRCT本体のバージョン更新・プロセス停止・ビルド・リリース・公開は実行しない。
exeは未署名。署名済み配布物の作成と公開は別途対応が必要。

OpenVR DLLは `openvr/libopenvr_api_64.dll` として明示的に同梱する。
HWND取得用Pythonファイルのみをデータとして同梱し、OCRや音声モデルの初期化を避ける。
exe内の一時展開パスはリソース読込にだけ使用し、保存先は `sys.executable` から決める。
ビルド時のDLL探索PATHをPythonとWindowsに限定し、PyInstallerの専用作業領域を再解析する。
開発者のPATHにある無関係なDLLの混入を避けるため。

同梱通知は各パッケージのインストール済みLICENSEとPython本体のLICENSEから取得する。
Pythonの通知にはlibffiとMicrosoft Distributable Codeの条項も含まれる。
OpenVR DLLとOpenSSLの通知は対応する上流版から保存して同梱する。

- [Valve OpenVR v1.26.7 LICENSE](https://github.com/ValveSoftware/openvr/blob/v1.26.7/LICENSE)
- [OpenSSL 3.0.9 LICENSE](https://github.com/openssl/openssl/blob/openssl-3.0.9/LICENSE.txt)

依存やPythonを更新した場合は、実際の同梱DLLと通知の対応も更新する。

## 検証

ソースの回帰テストに加え、ZIPをソースツリー外の作業ディレクトリから起動し、
OpenVRとHWNDによるPNG/JSON保存を実機確認する。
`--help` と `--manual --duration 0.1` は撮影を伴わない起動確認に使える。
Python未導入の別PC、別GPU・HMD、長時間稼働は追加の検証対象。

2026-09-12の配布版検証結果:

- 専用ビルド: PASS。exe約26 MB、READMEとライセンス、環境情報・SHA-256を同梱。
- 回帰テスト28件と対象6ファイルのruff: PASS（独立testerでも確認）。
- ZIPのCRC、exe/ZIPのSHA-256、同梱物一覧: PASS。独立レビューLGTM。
- ZIPをリポジトリ外の日本語・空白を含むフォルダへ展開し、実行時PATHを
  Windows関連のみに限定して、exeの隣へ画像・JSONを保存: PASS。
- HWND経路: 1918×1030を2枚保存。VRモードのデスクトップミラーを使用。
- OpenVR自動選択: VRChatウィンドウ最小化中に3000×3276を3枚保存。
  JSONのbackendと最小化状態、全PNGの形式・解像度・対応JSONを確認。
- 引数なしのコンソール起動: 自動撮影、Pで停止・再開、Rで状態表示、Qで保存終了、
  結果を表示したままEnter待ち、Enterで終了コード0まで確認。
- 新しい展開先からの初回起動で40秒のテスト上限を超過したケースがあった。
  同じexeの再試行は正常に起動・保存・終了（HWND約8秒、VR約10秒）。
  初回遅延の原因は未特定。別担当の初回CLI検査は60秒以内で成功した。
- exeは未署名。Python未導入の別PCでの検証、Desktopモードへの起動切替、
  長時間稼働は実施していない。

実機検証記録はGit対象外の `tmp/collector_validation/exe_validation_report.json`。
使用したexeのSHA-256は `031c35ee23f624edbbc4168fd2cc298cf38c57e7e53d9837bf2d5d22100e13b9`。
