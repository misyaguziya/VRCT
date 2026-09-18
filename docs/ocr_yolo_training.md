# チャットボックス検出モデル(YOLOv8n)の学習

`tools/ocr_dataset_collector.py` で集めた画像をアノテーションし、YOLOv8の軽量モデル(yolov8n)を
ファインチューニングする手順。検出したChat領域を切り出して文字起こしに渡す。

開発マシン専用。学習環境・データセット・学習結果はいずれもリポジトリにコミットしない
(`.venv-yolo/` `dataset_annotated/` `runs/` は .gitignore 済み)。

## 1. 環境構築

VRCT本体の `.venv` とは分ける。torchのCUDAビルドが本体の依存を壊さないようにするため。
検証環境: Windows 11 / CPython 3.11 x64 / RTX 2080 Ti / NVIDIA driver 610.62 (CUDA 12.8 wheel)。

```powershell
py -3.11 -m venv .venv-yolo
.\.venv-yolo\Scripts\python.exe -m pip install --upgrade pip
.\.venv-yolo\Scripts\python.exe -m pip install -r requirements-yolo-train.txt
```

GPUを掴んでいるか確認する。`False` ならCPU学習になり実用的な速度が出ない。

```powershell
.\.venv-yolo\Scripts\python.exe -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

ultralyticsは既定で利用統計を送信する。VRCTのデータを扱うので切っておく(設定は一度だけで永続)。

```powershell
.\.venv-yolo\Scripts\yolo.exe settings sync=False
```

## 2. アノテーションの方針

- **Chat吹き出しだけ**を対象にする。ワールド内の文字やVRChatのUI文字は取らない。
- Chatが写っていない画像も**空の .txt のまま**ネガティブサンプルとして残す。消さない。
- 枠は**吹き出し全体を1枠**にする(本体+しっぽ)。行ごとに分けない。
- 「寝た？」「お客様困ります！」のようなワールド由来のTextは対象外。AvatarのChatとは別物。
  判別の目安は、角丸の暗いパネルとしっぽがあるかどうか。
- 画面端で切れている吹き出しも、パネルの形が分かるなら枠を付ける(既存のアノテーションもそうしている)。
- 暗い背景・岩・木目は誤検出しやすい。Chatのない背景だけの画像を意図的に集めて足すと効く。

## 3. データセットの配置

アノテーション結果(`images/` と `annotations/` を持つフォルダ)を
`dataset_annotated/<セッション名>/` に置く。セッションは複数並べてよい。

```
dataset_annotated/
  session_20260914_113429/
    images/       元画像 (.png)
    annotations/  アノテーションの .txt(YOLO形式)と .json(メタデータ)
    labels/       ← 次のスクリプトが annotations/ の .txt から生成する
  train.txt / val.txt / data.yaml  ← 同じく生成物
```

アノテーションツールの出力フォルダから取り込む場合(差分だけコピーする)。

```powershell
robocopy "C:\Users\<user>\Desktop\VRCT-Gemini-Annotator\<セッション>\result" "dataset_annotated\<セッション>" /E /XO /XD labels /NFL /NDL /NJH /NP
```

`/XD labels` を付けないと生成済みの `labels/` を消しに行く。`/XO` は取り込み先で直したラベルを
古いエクスポートで上書きしないためのもの(アノテーションをやり直せばソースが新しくなるので取り込まれる)。
Git Bashではなく PowerShell で実行する(Git Bashは `/E` をパスと解釈して失敗する)。取り込んだら次を実行する。

```powershell
.\.venv-yolo\Scripts\python.exe -X utf8 tools\prepare_yolo_dataset.py
```

全セッションを走査して `labels/` を作り、`data.yaml` と train/val のリストを書き出す。画像は複製しない。

**分割はシーン単位**で行う。2秒周期の連番撮影なので隣接フレームはほぼ同じ絵になり、
1枚単位でランダムに分けると同じ場面がtrainとvalの両方に入って、valのスコアが実力より良く出る。
既定では連続10フレーム(約20秒)を1シーンとみなし、シーンごとtrain/valに振り分ける。
`--scene-size` で粒度、`--val-ratio` で比率、`--seed` で選び方を変えられる。seedが同じなら分割は再現する。
シーン数が足りずvalが空になる場合はエラーで止まる。

アノテーションをやり直したら同じコマンドを再実行する。`labels/` は内容が変わったものだけ書き直す。

アノテーションツールが改行をバックスラッシュとnの2文字で書き出すことがある。この形のラベルは
ultralyticsがファイルごとcorrupt扱いで黙って捨てる(初回は80枚中57枚が学習から抜けていた)ため、
このスクリプトが正規化する。5列でない・数値でない・0〜1の範囲外のラベルは黙って捨てずにエラーで止まる。
学習ログの `Scanning ... N images, M backgrounds, 0 corrupt` が想定枚数と合っているかを毎回確認する。

## 4. 学習

設定は [tools/yolo_chatbox_train.yaml](../tools/yolo_chatbox_train.yaml) にまとめてある。

```powershell
.\.venv-yolo\Scripts\yolo.exe cfg=tools/yolo_chatbox_train.yaml
```

- `imgsz: 1280`: 吹き出しが小さいので640では潰れる。アスペクト比はletterboxで維持される。
- augmentationは控えめ(`mosaic: 0.3`, `scale: 0.2`)。強いMosaicや過度な縮小は小さい吹き出しを壊す。
  水平反転(`fliplr`)と明るさ・彩度の変動(`hsv_v`, `hsv_s`)は有効にしてある。
- RTX 2080 Ti(11GB)で `imgsz=1280 batch=8` のVRAM使用は約4GB。上げる余地はある。
  足りない場合は `batch=4` に下げるか `batch=-1` で自動調整。
- 個別に変えたい値は後ろに付けて上書きする: `.\.venv-yolo\Scripts\yolo.exe cfg=tools/yolo_chatbox_train.yaml epochs=200 batch=16`
- 結果は `runs/chatbox/` に出る(`weights/best.pt`, `results.png`, 混同行列など)。

## 5. 評価

```powershell
.\.venv-yolo\Scripts\yolo.exe detect val model=runs\chatbox\weights\best.pt data=dataset_annotated\data.yaml imgsz=1280
.\.venv-yolo\Scripts\yolo.exe detect predict model=runs\chatbox\weights\best.pt source=<未学習の別シーンのフォルダ> imgsz=1280 conf=0.25 save=True
```

- **Precisionより Recall を重視する**。文字起こしに渡す前段なので、拾いすぎより見落としの方が痛い。
  Recallが低いときは `imgsz` を上げるか、`conf` を下げて(0.1〜0.15)どこまで拾えているかを確認する。
- 似た連続画像ばかりなので、valのスコアだけで判断しない。**学習に使っていない別シーンの画像**で
  必ず目視確認する。見るのは「Chat以外(名前プレート・ワールド文字・UI)を拾っていないか」
  「小さいChat表示を取りこぼしていないか」の2点。
- 取りこぼす条件(距離・背景・文字量)を控えて次の収集に反映する。
  暗い背景や岩・木目で誤検出が出たら、その場面のネガティブ画像を足して学習し直す。

## 6. VRCTへの組み込みと配布

推論は onnxruntime だけで動かす。faster-whisper が Silero VAD 用にすでに依存しているので、
配布物に増えるのはモデルファイル1つだけ。ultralytics も torch も推論には要らない。

```powershell
.\.venv-yolo\Scripts\yolo.exe export model=runs\chatbox\weightsest.pt format=onnx imgsz=1280 nms=True simplify=True opset=17 conf=0.05 iou=0.7
```

`conf=0.05` は必ず付ける。エクスポート時の値がNMSに焼き込まれるので、既定(0.25)のままだと
実行時に閾値を下げても候補が増えない。実行時の閾値は `BubbleDetector(confidence=...)` で決める。

出力を `src-python/models/ocr/onnx/chatbox_yolov8n.onnx` に置き換える。
`spec/backend.spec` と `spec/backend_cuda.spec` の datas が `ocr_onnx/` として同梱し、
`findModelPath()` が凍結時は `_internal/ocr_onnx/`、ソース実行時はパッケージ内を見る。
モデルは12MB程度。Whisperの重みのような実行時ダウンロードにはしない(容量が理由の仕組みなので)。

リリースに載せるモデルだけをリポジトリに上書きコミットする。実験のたびにコミットしない。

### 学習済みモデルの履歴

| 日付 | データ | val成績 (mAP50 / mAP50-95) | 実測 (CPU, imgsz=1280) | 備考 |
|---|---|---|---|---|
| 2026-09-17 | 100枚 / 1セッション / 1ワールド | 0.986 / 0.719 | 約300 ms/枚 | 初版。ラベル修正(空ラベル6枚追加・枠ズレ5枚修正)後 |

### 実行時の閾値

`BubbleDetector` の既定は `confidence=0.15`。val20枚での実測:

| conf | 検出 | 余分な候補 |
|---|---|---|
| 0.15 | 20/20 | 5 |
| 0.25 | 19/20 | 2 |
| 0.5 | 18/20 | 0 |

取りこぼしは翻訳されない文が出ることを意味するのに対し、余分な候補はOCR側の
`OCR_MIN_CONFIDENCE` で文字が読めずに落ちるだけなので、取りこぼしを優先して0.15にしている。
ただし候補が増えるとtickのOCR予算を食うので、実機で遅いと感じたら上げる。
