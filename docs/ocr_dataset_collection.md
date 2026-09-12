# チャットボックス学習用画像の収集

Python不要の配布用exeは [exe配布手順](dataset_collector_distribution.md) を参照。
exeをダブルクリックすると同じ既定設定で撮影を開始し、exeの隣へ保存する。

リポジトリルートのPowerShellで実行する。画像はローカルに保存され、Geminiへ自動送信されない。

```powershell
.\.venv\Scripts\python.exe -X utf8 tools\ocr_dataset_collector.py
```

既定では、**2秒周期・左眼・10分間**の自動撮影を開始する。セッション名は日時から自動生成。
VRChatがSteamVRのsceneとして動いているときはOpenVR D3D11、Desktopではウィンドウを取得する。
VRの撮影ではVRChatウィンドウを最小化できる。Desktop経路では最小化できない。

## 操作

キー操作はこのツールのコンソールにフォーカスがあるときに有効。Enterは不要。
撮影中にVRChatへ戻っても自動保存を継続する。

| キー | 動作 |
|---|---|
| P | 一時停止・再開 |
| Q / Ctrl+C | 終了 |
| R | 保存枚数・停止状態を表示 |

一時停止・終了は処理中の1枚の完了を待つ場合がある。保存失敗はエラーを表示して停止する。
VRChatの画像が取得できない場合は理由を表示し、次の撮影時刻に再試行する。
古い画像を新しい画像として保存することはない。

例:

```powershell
# 名前を付け、VR用の取得を指定する
.\.venv\Scripts\python.exe -X utf8 tools\ocr_dataset_collector.py night_world --backend openvr

# Desktop専用、5分間
.\.venv\Scripts\python.exe -X utf8 tools\ocr_dataset_collector.py desktop --backend hwnd --duration 300

# 右眼、3秒周期、保存成功100枚または10分で停止
.\.venv\Scripts\python.exe -X utf8 tools\ocr_dataset_collector.py right_eye --eye right --interval 3 --max-frames 100

# 時間制限なし（Q/Ctrl+Cで停止）
.\.venv\Scripts\python.exe -X utf8 tools\ocr_dataset_collector.py --duration 0
```

`--duration`は一時停止時間も含む実時間（秒）。`--max-frames`は今回の実行で保存成功した枚数。
`--interval`は取得開始の目標周期で、保存が間に合わない回は飛ばす。遅れを取り戻す連写はしない。
PNGは圧縮レベル1の可逆圧縮で、3000×3276の検証画像では1枚約6.6 MBだった。
300枚なら約2 GBが目安だが、画像内容や解像度で変わる。

## 保存内容

```text
dataset_collected/
  night_world/
    unlabeled/
      <run_id>_000000.png
      <run_id>_000000.json
      ...
```

JSONには実際の取得開始日時（UTC）、取得方法、眼、解像度、session、run_id、VRChatのPIDと
ウィンドウ状態を保存。OpenVRでは読出し前後のcompositorフレーム番号も記録する。
画像とJSONの両方が保存できた場合だけ件数が増える。同じsession名で再実行してもrun_idで分かれる。
通常の書込失敗時は途中ファイルを片付ける。OSの強制終了や電源断では`.part`等が残る可能性がある。

自動撮影の画像はすべて`unlabeled`（未分類）。**このフォルダをそのままYOLOの背景画像として使わない。**
チャットボックスの有無と枠を確認し、ラベルを作ってから学習に使う。
既存`gemini_bbox_labeler.py`の複数枠対応・未検出結果の確認工程は今回変更していない。

## 手動で分類しながら保存する場合

```powershell
.\.venv\Scripts\python.exe -X utf8 tools\ocr_dataset_collector.py manual_session --manual
```

| キー | 保存先 |
|---|---|
| Enter | `positive/`（チャットボックスあり） |
| N | `negative/`（なし） |
| U | `unlabeled/`（後で確認） |

このモードもP/Q/Rが使える。撮影はキーの要求後に行われるため、キーを押すまで対象が見える状態を保つ。
以前のCLIの「最新キャッシュ画像を保存」という動作は廃止。未知のキーでは保存しない。

## 動作上の制約

- Windowsの独立CLI用。本番VRCTのOpenVR sessionとは別プロセスで初期化・終了する。
- `openvr`、`numpy`、`Pillow`、`psutil`を使用。今回のD3D11経路にPyOpenGL/glfw/cv2は不要。
- 自動選択でVRChatのVR sceneを一度確認した後は、そのプロセスのVR取得失敗を
  Desktop撮影へ黙って切り替えない。VRChatを終了すると自動選択をやり直す。
- 取得元が変わった画像、更新のないOpenVRフレーム、取得に2秒超かかった画像は保存しない。
  遅い環境の上限は`--max-age`で変更できる。
- 選択眼や縮小処理は本番推論に合わせて収集する。左右は別の画像で、同時撮影ではない。
- 現在の単キー操作はグローバルショートカットやVRコントローラー操作ではない。
- ネイティブAPIが返らない場合は安全な解放のため終了を待つ。未終了スレッドを残して完了とは表示しない。

## 検証

```powershell
.\.venv\Scripts\python.exe -m pytest -q src-python\test_ocr_dataset_collector.py
.\.venv\Scripts\python.exe -m ruff check tools\ocr_dataset_collector.py tools\ocr_capture_source.py tools\openvr_d3d11.py tools\probe_openvr_capture.py src-python\test_ocr_dataset_collector.py
```

回帰テストでは保存失敗、古いフレーム、停止時の所有権、pause/resume、期限・枚数停止、
画像とJSONの整合性、RGB/BGRの色順序、誤った取得元の除外を検証する。
実機を使うテストは上記のpytestから実行しない。

2026-09-12の検証結果:

- 新規回帰テスト23件・対象ファイルのruff: PASS。独立testerでも同じ結果。
- 独立レビュー: LGTM。重大指摘なし。
- D3D11による通常表示4枚、最小化中の自動撮影4枚: PASS。
  最小化中に一時停止し、2.5秒間の保存増加なしを確認。再開後、4枚の上限で正常終了。
- 初期化後のVR取得間隔は約2秒。保存したPNGとJSON全件の対応、画像形式・解像度を確認。
- HWND経路でVRChatのデスクトップミラーを2枚保存: PASS。
  この試行はVRモードのウィンドウを使用し、Desktopモードへの起動切替は実施していない。
- 手動モードの入力なし期限終了、共通モジュール抽出後のprobe実機保存: PASS。
- 長時間連続稼働、SteamVR再起動・HMD切断からの復旧、VR/Desktop起動の切替は未検証。

実機検証画像・JSONはGit対象外の`tmp/collector_validation/`以下。
