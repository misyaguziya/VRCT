# VRChat の最小化中に使う学習画像の取得調査

調査日: 2026-09-12 / branch: `feature/ocr-chat-bubble`

追記: 本書は最初の取得可能性検証の記録。その後、収集CLIをD3D11対応・自動撮影・
pause/resume・安全な保存/終了へ更新した。現在の操作は
[画像収集の手順](ocr_dataset_collection.md)を参照。本番OCRへの組み込みは引き続き未実施。

## 結論

**この実機では、VRChat のデスクトップウィンドウを最小化しても、OpenVR の
`GetMirrorTextureD3D11` から VRChat の片眼画像を継続取得できた。**
Windows 版の画像取得候補として D3D11 mirror を推奨する。
今回追加したのは独立した診断 CLI で、本番 OCR や収集ツールへの組み込みは行っていない。

実機で確認できたのは画像取得と最小化中の更新である。チャットボックスを含む画像の
目視確認、YOLO/Gemini による検出精度、長時間稼働は別の検証項目として扱う。

## 実機結果

- Windows / NVIDIA GeForce RTX 2080 Ti / Meta Quest 3。
- OpenVR の HMD driver 情報: `oculus`、driver version `1.64.0`。
- Python `openvr 1.26.701`、`numpy 1.26.4`、`Pillow 10.0.0`、`psutil 5.9.8`。
- `VRApplication_Background` で接続。VRChat の scene を奪う初期化は行わない。
- 推奨 render target は 2112×2304、実際の mirror は **3000×3276**。
  保存解像度は推奨値から推測せず、取得テクスチャの descriptor を使う。
- resource format: `R8G8B8A8_TYPELESS (27)`、SRV format:
  `R8G8B8A8_UNORM_SRGB (29)`。RowPitch は 12032 byte（3000×4=12000とは異なる）。

| 確認 | 結果 | 証拠 |
|---|---|---|
| SteamVR/HMD 接続 | PASS | HMD情報取得、D3D11デバイス生成 |
| VRChat 通常表示の左眼画像 | PASS | ワールドをPNG保存し目視、renderer PIDがVRChatと一致 |
| VRChat 最小化中の左眼画像 | PASS | 6枚すべて`minimized=true`、`renderer_name=VRChat.exe` |
| VRChat 最小化中の右眼画像 | PASS | 別runの6枚で最小化・VRChat描画元を確認、最終画像を目視 |
| 最小化中のフレーム更新 | PASS | frame index 5629→7591、6枚のSHA-256がすべて異なる |
| 最小化中のチャットボックス | 未確認 | 表示状態を作って追加確認する必要がある |
| 既存GL経路 | BLOCKED | この`.venv`と`.venv_cuda`にPyOpenGL/glfwが未導入 |
| 長時間・接続断・SteamVR再起動 | 未実施 | 今回は短時間の取得可能性検証 |

左眼の最小化検証は19:52:07〜19:52:36 JSTの約28秒。
各画像の画素変化率は前フレーム比61〜62%。ワールド映像を目視確認しており、
SteamVR待機画面だけの取得成功やフレーム番号だけを根拠にはしていない。
右眼も19:53:09〜19:53:35 JSTの6枚でframe index 9854→11706、全SHA-256の相違を確認した。
左右は別runで取得しており、同期したステレオペアを検証したものではない。

画像取得・CPUへのRGB変換は中央値 **65.3 ms**（6サンプル、初回を含む）。
PNG保存や統計計算を除いた診断値であり、アプリ全体の処理速度や60 FPS動作を保証しない。
CLIは画像保存・統計処理の後に`--interval`秒待つため、固定FPSの収集器ではない。

ローカル証拠（画像はGit管理対象外の`tmp/`に保存）:

- [最小化中の測定JSON](../tmp/openvr_probe/vrchat_minimized/20260912T105206_847189Z/report.json)
- [最小化中の左眼画像](../tmp/openvr_probe/vrchat_minimized/20260912T105206_847189Z/left_005.png)
- [最小化中の右眼の測定JSON](../tmp/openvr_probe/vrchat_minimized_right/20260912T105308_712285Z/report.json)
- [最小化中の右眼画像](../tmp/openvr_probe/vrchat_minimized_right/20260912T105308_712285Z/right_005.png)
- [通常表示の測定JSON](../tmp/openvr_probe/vrchat_visible/20260912T105127_555255Z/report.json)
- [通常表示の左眼画像](../tmp/openvr_probe/vrchat_visible/20260912T105127_555255Z/left_002.png)

初期の試行ではSteamVR待機画面を取得し、renderer PIDが0だった。
また旧pyopenvr wrapperによるframe index=0の問題があった。
通常表示runのframe indexはこの修正前なので更新の根拠にしない。
最小化runは修正後である。

## 取得方式の比較

| 方式 | VRChat最小化 | 用途・制約 |
|---|---|---|
| **OpenVR D3D11 mirror** | **今回実証済み** | HMD片眼画像。Windows実装の第一候補 |
| OpenVR GL mirror | HWNDには非依存、実機未検証 | branchの既存実装。GL contextとPyOpenGL/glfwが必要 |
| SteamVR VR View＋ウィンドウキャプチャ | VRChat HWNDとは独立、実機未検証 | 目視比較や手動収集向け。VR View自身の最小化は別問題 |
| VRChat Spout | HWNDを介さないが最小化継続は未検証 | ユーザーカメラ視点。HMD視点と異なり、chatboxの描画も要確認 |
| OpenXR単独 | 本用途の標準取得APIは確認できず | 他アプリの完成画像を読むOpenVR mirrorの代替にはしにくい |

OpenVR mirror は片眼ごとのレンズ用歪みを加える前の合成画像である。
遠近投影によるチャットボックスの傾きは残る。実画像には周辺の黒いマスク領域もある。
本番推論と学習収集で同じ眼・crop・縮小方式を使う必要がある。
これはVRChatのウィンドウキャプチャではなく、SteamVR compositorからの取得であるため、
別のVRアプリや待機画面も取得できてしまう。収集時には画像の出所を検証する。
[Valve公式ヘッダ](https://raw.githubusercontent.com/ValveSoftware/openvr/master/headers/openvr.h)

VR View の Both Eyes モードは左右のブレンドを含むため、文字検出にはまず片眼を使う。
[ValveのVR View更新説明](https://store.steampowered.com/news/posts/?appids=250820&enddate=1568845125)

Spout はVRChatが公式に提供するカメラ出力。2024.4.1で720p〜4K（既定1080p）が提供されている。
カメラUIを閉じてもstreamを維持する機能はあるが、HMD画像と同一ではない。
[VRChat 2024.3.3](https://docs.vrchat.com/docs/vrchat-202433)、
[VRChat 2024.4.1](https://docs.vrchat.com/docs/vrchat-202441)

OpenXRの標準swapchainは自分のアプリが描画して提出するための画像である。
今回は他プロセスのHMD画像を取り出す標準経路を確認できなかった。
SteamVRを通さないQuest単体や別runtimeまで、今回のOpenVR検証結果は一般化できない。
[Khronos公式描画仕様](https://github.com/KhronosGroup/OpenXR-Docs/blob/main/specification/sources/chapters/rendering.adoc)

## 診断CLIの再実行

リポジトリルートで、SteamVR/HMDとVRChatを起動してから実行する。
OpenVRの所有権を分けるため、**必ず別プロセスのCLIとして使う**。

```powershell
.\.venv\Scripts\python.exe -X utf8 tools\probe_openvr_capture.py --frames 6 --out tmp\openvr_probe\visible
# VRChatを最小化して、HMDで視点やチャットボックスの表示を変える
.\.venv\Scripts\python.exe -X utf8 tools\probe_openvr_capture.py --frames 6 --out tmp\openvr_probe\minimized
.\.venv\Scripts\python.exe -X utf8 tools\probe_openvr_capture.py --frames 6 --eye right --out tmp\openvr_probe\right
```

出力先にUTC時刻のサブフォルダが作られ、PNGと`report.json`が保存される。
`CAPTURED`は画像読出し成功だけを意味し、VRChatやチャットボックスの検証成功とは区別する。
`renderer_name`、`vrchat_windows[].minimized`、`compositor_frame_index`、`sha256`と実画像を確認する。
最小化runでは対象ウィンドウが1つ以上記録されていることも確認する。
CLI自身はウィンドウを最小化したり、チャットを送ったりしない。

実装上の注意:

- `GetDXGIOutputInfo()`が返すadapterでD3D11デバイスを生成。
- mirrorを一度取得し、各回で`CopyResource`→staging textureの`Map`→RowPitchを考慮したコピー→`Unmap`。
- typeless resourceのSRV formatを使ってCPU読出し用テクスチャを作る。D3D経路は上下反転しない。
- SRVはOpenVRの`ReleaseMirrorTextureD3D11`で解放。自分で取得したCOM参照も解放する。
- `openvr 1.26.701`のD3D11 wrapperは入力`void*`へ余分な`byref`を付けるため、
  正しい型定義を持つ`function_table`を利用。`getFrameTiming`も`m_nSize`を明示する。

GPUコピーとCPUマッピングの契約:
[Microsoft CopyResource](https://learn.microsoft.com/en-us/windows/win32/api/d3d11/nf-d3d11-id3d11devicecontext-copyresource)、
[Microsoft Map](https://learn.microsoft.com/en-us/windows/win32/api/d3d11/nf-d3d11-id3d11devicecontext-map)

## 現branchで収集開始前に対処する点

1. `src-python/models/ocr/ocr_capture_openvr.py` は既存GL実装で、今回のD3D11 CLIとは別。
   必要ライブラリはrequirementsに記載済みだが、現在のvenvにはPyOpenGL/glfwがない。
2. 同モジュールは`openvr.init()`を直呼びし、既存`models/openvr_session.py`の参照カウントへ参加していない。
   本番組み込みではOverlay/Clipboardとセッション所有権を揃える必要がある。
3. `ocr_capture.py`はvrmonitorの存在で経路を選び、実際のsceneがVRChatか確認しない。
   依存import成功後にOpenVR取得だけ失敗する場合もHWNDへ戻らない。
4. `tools/ocr_dataset_collector.py`は取得失敗後も古い成功画像を保持する。
   新鮮な画像かの検証と撮影時刻・backend・眼情報の記録が収集前の修正候補。
5. `tools/gemini_bbox_labeler.py`は画像あたり単一bboxを扱う構造。
   複数人のchatboxを収集する場合は複数bboxに対応させる。

YOLO導入時は`OcrPipeline`のdetectorを交換し、既存の
`detect(frame) -> [((x, y, w, h), BGR crop), ...]`を維持すれば後段のOCR等へ接続できる。
今回、データセットへの収集、Geminiへの画像送信、YOLO学習は実施していない。

## 検証と残課題

- `python -m ruff check tools/probe_openvr_capture.py`: PASS。
- 独立レビューでCOM ABI/所有権/RowPitch/画像方向を確認。
  `m_nSize`不足の指摘を修正し、実機でフレーム番号の進行を確認した。
- 修正後の独立レビュー: **LGTM**。左眼最小化runの6枚について、保存PNGからの
  画素ハッシュ再計算・JSONとの一致・相違、最終画像のワールド映像を確認済み。
- 本番ファイル・UI・Rustは変更していないため、アプリ全体のpytest/buildは実施していない。
- 本番採用前にはchatbox表示、HMD待機/切断、SteamVR再起動、Overlay同時使用、
  長時間のメモリ使用量を確認する。低頻度の学習収集と高速な推論用キャプチャは性能要件を分ける。
