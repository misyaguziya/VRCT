# チャットボックス検出モデル(YOLOX-Tiny)の学習

`tools/ocr_dataset_collector.py` で集めた画像をアノテーションし、YOLOX-Tinyを
ファインチューニングする手順。検出したChat領域を切り出して文字起こしに渡す。

基盤は Megvii の [YOLOX](https://github.com/Megvii-BaseDetection/YOLOX) (Apache-2.0)。
COCO 事前学習重みも同じ許諾なので、**できあがるモデルの条件は自分で決められる**。
同梱しているものは VRCT 専用の利用許諾にしてある
(理由と経緯は [docs/ocr_model_license.md](ocr_model_license.md)、表記は
[NOTICE.md](../NOTICE.md) と `src-python/models/ocr/onnx/NOTICE.txt`)。
以前は Ultralytics の YOLOv8n を使っていたが、事前学習重みが AGPL-3.0 で
成果物もその派生になるため載せ替えた。検証の記録は
[docs/ocr_yolox_migration_2026-09-22.md](ocr_yolox_migration_2026-09-22.md)。

開発マシン専用。学習環境・データセット・学習結果はいずれもリポジトリにコミットしない
(`.venv-yolox/` `.yolox-src/` `dataset_annotated/` `runs/` は除外済み)。

## 1. 環境構築

VRCT本体の `.venv` とは分ける。torchのCUDAビルドが本体の依存を壊さないようにするため。
検証環境: Windows 11 / CPython 3.11 x64 / RTX 2080 Ti / NVIDIA driver 610.62 (CUDA 12.8 wheel)。

YOLOX は clone をそのまま使う。`pip install yolox` だと `tools/` と `exps/` が手に入らない。
**clone には手を入れない**(由来を説明しやすくするため)。Windows で必要な回避は
`tools/yolox_chatbox_train.py` 側に置いてある。

```powershell
git clone --depth 1 https://github.com/Megvii-BaseDetection/YOLOX.git .yolox-src
py -3.11 -m venv .venv-yolox
.\.venv-yolox\Scripts\python.exe -m pip install --upgrade pip
.\.venv-yolox\Scripts\python.exe -m pip install -r requirements-yolox-train.txt
.\.venv-yolox\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .yolox-src
curl.exe -L -o weights\yolox_tiny.pth https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_tiny.pth
```

`--no-build-isolation` を付けるので `wheel` が先に入っていること
(`requirements-yolox-train.txt` に入れてある)。付けないと setup.py が torch を
見つけられず「pre-compiling ops が無効」で止まる。

GPUを掴んでいるか確認する。`False` ならCPU学習になり実用的な速度が出ない。

```powershell
.\.venv-yolox\Scripts\python.exe -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

## 2. アノテーションの方針

- **Chat吹き出しだけ**を対象にする。ワールド内の文字やVRChatのUI文字は取らない。
- Chatが写っていない画像も**空の .txt のまま**ネガティブサンプルとして残す。消さない。
- 枠は**吹き出し全体を1枠**にする(本体+しっぽ)。行ごとに分けない。
- 「寝た？」「お客様困ります！」のようなワールド由来のTextは対象外。AvatarのChatとは別物。
  判別の目安は、角丸の暗いパネルとしっぽがあるかどうか。
- 画面端で切れている吹き出しも、パネルの形が分かるなら枠を付ける(既存のアノテーションもそうしている)。
- 暗い背景・岩・木目は誤検出しやすい。Chatのない背景だけの画像を意図的に集めて足すと効く。
- **ワールドとウィンドウサイズを変えて集める**。1セッション(100枚/1ワールド)だけで
  学習したモデルは、別のワールド・別の窓サイズで取りこぼしが一気に増えた
  (val 39個中 8個)。2セッション目(別ワールド / 1936x1048)を足したら 1個まで減った。
  精度の支配要因はアーキテクチャではなくデータの幅。

## 3. データセットの配置

アノテーション結果(`images/` と `annotations/` を持つフォルダ)を
`dataset_annotated/<セッション名>/` に置く。セッションは複数並べてよい。

```
dataset_annotated/
  session_20260914_113429/
    images/       元画像 (.png)
    annotations/  アノテーションの .txt(YOLO形式)と .json(メタデータ)
    labels/       ← prepare_yolo_dataset.py が annotations/ の .txt から生成する
  train.txt / val.txt / data.yaml     ← 同じく生成物
  annotations/instances_*_chatbox.json ← prepare_yolox_dataset.py が生成する
```

アノテーションツールの出力フォルダから取り込む場合(差分だけコピーする)。

```powershell
robocopy "C:\Users\<user>\Desktop\VRCT-Gemini-Annotator\<セッション>\result" "dataset_annotated\<セッション>" /E /XO /XD labels /NFL /NDL /NJH /NP
```

`/XD labels` を付けないと生成済みの `labels/` を消しに行く。`/XO` は取り込み先で直したラベルを
古いエクスポートで上書きしないためのもの(アノテーションをやり直せばソースが新しくなるので取り込まれる)。
Git Bashではなく PowerShell で実行する(Git Bashは `/E` をパスと解釈して失敗する)。取り込んだら次を実行する。

```powershell
.\.venv\Scripts\python.exe -X utf8 tools\prepare_yolo_dataset.py    # labels/ と train/val の分割
.\.venv\Scripts\python.exe -X utf8 tools\prepare_yolox_dataset.py   # 同じ分割を COCO JSON へ
```

前者が全セッションを走査して `labels/` を作り、train/val のリストを書き出す。画像は複製しない。
後者はそのリストをそのまま読んで YOLOX が要求する COCO 形式の JSON にする(これも複製しない)。
分割を作り直さないのは、モデルを差し替えても同じ val で比べられるようにするため。

**分割はシーン単位**で行う。2秒周期の連番撮影なので隣接フレームはほぼ同じ絵になり、
1枚単位でランダムに分けると同じ場面がtrainとvalの両方に入って、valのスコアが実力より良く出る。
既定では連続10フレーム(約20秒)を1シーンとみなし、シーンごとtrain/valに振り分ける。
`--scene-size` で粒度、`--val-ratio` で比率、`--seed` で選び方を変えられる。seedが同じなら分割は再現する。
シーン数が足りずvalが空になる場合はエラーで止まる。

**val は `dataset_annotated/val_fixed.txt` に固定する。** 2026-09-25 に4セッション
(4ワールド、Desktop 3 / VR 1)・406枚を基準とし、各セッションから20枚ずつ(計80枚)を
凍結した。以後データを足しても val は変わらず、新しい画像はすべて train に入るので、
モデル同士を同じ物差しで比べられる。作り直すのは基準そのものを変えるときだけ
(`--refreeze`)。作り直すと過去のモデルとの比較は切れる。

アノテーションをやり直したら同じコマンドを再実行する。`labels/` は内容が変わったものだけ書き直す。

アノテーションツールが改行をバックスラッシュとnの2文字で書き出すことがある。
5列でない・数値でない・0〜1の範囲外のラベルは黙って捨てずにエラーで止まる。
学習ログの `Scanning ... N images` が想定枚数と合っているかを毎回確認する。

## 4. 学習

設定は [tools/yolox_chatbox_exp.py](../tools/yolox_chatbox_exp.py) にまとめてある。

```powershell
.\.venv-yolox\Scripts\python.exe -X utf8 tools\yolox_chatbox_train.py -c weights\yolox_tiny.pth
```

- 本家の `tools/train.py` ではなく [tools/yolox_chatbox_train.py](../tools/yolox_chatbox_train.py)
  から起動する。本家は `configure_nccl()` が Linux 専用のシェルコマンドを叩き、Windows では
  cmd の cp932 出力を utf-8 で読んで `UnicodeDecodeError` で落ちる。NCCL は複数GPUの設定なので
  単一GPUでは要らない。同じスクリプトが `fast_cocoeval` の JIT ビルド(MSVCが要る)も回避する。
- `input_size: (1280, 1280)`: 吹き出しが小さい。416や640だと潰れる。FPNのstrideが8/16/32なので
  1280は割り切れる。`multiscale_range = 5` で 1120〜1440 に振る。Desktop(縮小率0.5〜0.66)と
  VR(2988x3260 で縮小率0.39)で吹き出しの見かけの大きさが倍違うため。スケール拡張なしで
  学習したモデルは、VRで推論の入力サイズを変えるだけで取りこぼした。
- `max_epoch: 80`。150 では全ての run が 52〜85 epoch で頭打ちになっていた。
- VRAM は入力 1440 のとき約6GB(batch 8)。**VRChat と同じGPUで学習すると VRAM があふれて
  1iter が 0.8秒→18秒まで落ちる**。学習中は VRChat を閉じる。
- augmentationは控えめ(`mosaic_prob: 0.3`, `mosaic_scale: (0.5, 1.5)`, mixupなし)。
  強いMosaicや過度な縮小は小さい吹き出しを壊す。水平反転とHSVの変動は有効。
- RTX 2080 Ti(11GB)で `batch=8` で 406枚・80 epoch が約50分(VRChat を閉じた状態)。
- 個別に変えたい値は後ろに付けて上書きする: `... tools\yolox_chatbox_train.py max_epoch 200`
- 結果は `runs/chatbox_yolox_tiny/` に出る(`best_ckpt.pth`, `train_log.txt`, tensorboard)。
- YOLOX-Nano を試すときは `-f tools\yolox_chatbox_exp_nano.py -c weights\yolox_nano.pth`。
  速いが小さい吹き出しを落としやすい(実測は移行の記録を参照)。

## 5. 評価

学習中は5 epochごとに pycocotools の COCOeval が走り、`train_log.txt` に mAP が出る。
ただし **val のスコアだけで判断しない**。似た連続画像ばかりなので実力より良く出る。

エクスポート後は配布時と同じ onnxruntime の経路で測る。

```powershell
.\.venv\Scripts\python.exe -X utf8 tools\eval_bubble_onnx.py `
    --model src-python\models\ocr\onnx\chatbox_yolox_tiny.onnx --imgsz 736,1280
```

- **Precisionより Recall を重視する**。文字起こしに渡す前段なので、拾いすぎより見落としの方が痛い。
  `--conf` を 0.15 / 0.25 / 0.5 で振って、取りこぼしがどこから増えるかを見る。
- `--coco-eval` を付けると mAP も出る(pycocotools が要るので `.venv-yolox` から実行する)。
  基盤ごとの val スクリプトを比べると mAP の実装差が混ざるので、比較はこちらで揃える。
- 学習に使っていない別シーンの画像で**必ず目視確認する**。見るのは
  「Chat以外(名前プレート・ワールド文字・UI)を拾っていないか」「小さいChat表示を取りこぼしていないか」。
- 取りこぼす条件(距離・背景・文字量)を控えて次の収集に反映する。

## 6. エクスポートと量子化

推論は onnxruntime だけで動かす。faster-whisper が Silero VAD 用にすでに依存しているので、
配布物に増えるのはモデルファイル1つだけ。YOLOX も torch も推論には要らない。

```powershell
.\.venv-yolox\Scripts\python.exe -X utf8 tools\yolox_chatbox_export.py `
    -c runs\chatbox_yolox_tiny\best_ckpt.pth --size 736,1280 --dynamic `
    -o runs\chatbox_yolox_tiny\chatbox_yolox_tiny.onnx
.\.venv-yolox\Scripts\python.exe -X utf8 tools\yolox_chatbox_quantize.py `
    -i runs\chatbox_yolox_tiny\chatbox_yolox_tiny.onnx `
    -o src-python\models\ocr\onnx\chatbox_yolox_tiny.onnx --size 736,1280
```

- **`--dynamic` は必須**。VRChatのウィンドウはユーザーがリサイズできるので、キャプチャの
  アスペクト比が一定ではない。`BubbleDetector` は長辺を1280に合わせ、短辺を32の倍数に
  切り上げた大きさで入力を作る。正方形に固定すると16:9で4割強を余白の推論に使う。
- `--size` は trace と校正に使う形。可変入力なので実行時はこれに縛られない。
- decode(grid/strideの復元)はグラフに入る。NMS は `BubbleDetector` 側の numpy。
  YOLOv8nのときのように「エクスポート時のconfがNMSへ焼き込まれて実行時に下げられない」
  問題はこの形では起きない。閾値は `BubbleDetector(confidence=...)` 一箇所。
- **量子化は予測conv以降をfp32で残す**。グラフ全体を素直に量子化すると obj/cls のスコアが
  0に潰れて何も検出しなくなる。`yolox_chatbox_quantize.py` がその除外をやる。
  量子化後は conf 0.01 付近の弱い候補が増える(既定の0.7では影響しない)。
- `spec/backend.spec` と `spec/backend_cuda.spec` の datas が
  `src-python/models/ocr/onnx` ディレクトリごと `ocr_onnx/` として同梱する。
  `LICENSE.txt` `LICENSE.en.txt` `NOTICE.txt` はそのまま配布物のライセンス表記になるので消さない。
- `findModelPath()` が凍結時は `_internal/ocr_onnx/`、ソース実行時はパッケージ内を見る。
- リリースに載せるモデルだけをリポジトリに上書きコミットする。実験のたびにコミットしない。

### 学習済みモデルの履歴

| 日付 | 基盤 | データ | val | mAP50 / 50-95 | CPU | 備考 |
|---|---|---|---|---|---|---|
| 2026-09-17 | YOLOv8n (AGPL-3.0) | 100枚 / 1セッション | 20枚 | 0.988 / 0.723 | 165 ms (1280x1280 fp32) | 初版。ライセンスの問題で引退 |
| 2026-09-22 | YOLOX-Tiny (Apache-2.0) | 同上 | 20枚 | 0.985 / 0.661 | 61 ms (736x1280 INT8) | 可変入力 + INT8。5.5MB |
| 2026-09-22 | YOLOX-Tiny (Apache-2.0) | 202枚 / 2セッション | 40枚 | 0.955 / 0.643 | 同上 | 別ワールドでの取りこぼしが 8→1 |
| 2026-09-25 | YOLOX-Tiny (Apache-2.0) | **406枚 / 4セッション (VR含む)** | **固定80枚** | **0.980 / 0.667** | 同上 | 現行。基準モデル。スケール拡張あり・80epoch |

2026-09-25 以降の行は固定 val (`val_fixed.txt`) での値なので、行同士を比べてよい。
それより前の行は val が毎回違うので比べられない。固定 val で測った直前のモデル
(スケール拡張なし)は mAP50 0.933 / 50-95 0.626、conf 0.15 で 66/70・余分17 だった。
スケール拡張と固定分割にしたことで 69/70・余分3 になった。

**mAP は val が変わると比較できない**。3行目は val が 40枚(2セッションから20枚ずつ)に
変わっているので、2行目の 0.985 より低く見えるが実力は上。同じ 40枚で測ると
100枚モデルは mAP50 0.734 / 50-95 0.450 で、202枚モデルの 0.955 / 0.643 に大きく劣る。

mAP は `tools/eval_bubble_onnx.py --coco-eval` で揃えて測った値。CPU は i7-9700K、
1モデルずつ別プロセスで20回の最小値。**絶対値は同時に動いている処理で2〜3倍ぶれる**ので、
比較するときは必ず測り直すこと。

### 実行時の閾値

`BubbleDetector` の既定は `confidence=0.7`。固定val80枚(正解70個)での実測 (2026-09-25 の基準モデル):

| conf | 検出 | 余分な候補 |
|---|---|---|
| 0.15 | 69/70 | 3 |
| 0.5 | 69/70 | 1 |
| **0.7** | **68/70** | **0** |
| 0.85 | 52/70 | 0 |

以前は取りこぼし優先で 0.15 にしていたが、実機で VRChat の config 画面(学習データに
無いUI)を吹き出しと誤検出したため引き上げた。config 画面のネガティブを学習に足した
うえで、誤検出0を取れる一番低い値が 0.7。0.85 まで上げると取りこぼしが一気に増える。

**モデルを学習し直したら、この表を作り直して閾値を決め直す。** 信頼度の分布はモデルごとに
変わる(2026-09-22 のモデルは 0.85 で 83% 残ったが、この基準モデルは 74% しか残らない)。
誤検出が出たら、閾値を上げる前にその画面をネガティブとして足す。

100枚モデルが落としていた横幅1284pxの横長の吹き出し(左右2つに割って検出していた)は、
202枚モデルでは score 0.914 / IoU 0.705 の1枠で取れるようになった。データを足すだけで
直ったので、取りこぼしを見つけたらまずその場面を集めるのが早い。
