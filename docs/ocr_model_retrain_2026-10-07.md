# 吹き出し検出モデルの再学習: VRCT 自身のオーバーレイを拾わないようにする (2026-10-07)

## 目的

OCR が **VRCT 自身の VR オーバーレイ（翻訳ログの窓）** を吹き出しとして拾っていた。
暗い角丸パネルに白い文字が並ぶ見た目が VRChat の吹き出しとそっくりで、拾うと OCR が
VRCT 自身の翻訳を読み返し、それをまた翻訳するループになる。これが現状いちばんの問題だった。

OCR で読んだ文字列を VRCT の最近の出力と照合して捨てる案も検討したが、切り取り方で
OCR の結果が大きく変わるため照合が当てにならず、採らなかった。検出器そのものに
「オーバーレイは吹き出しではない」と教える。

## 結論

**オーバーレイのネガティブを間引いて 14 枚だけ足したモデルを採用した。**
学習に一度も入れていないオーバーレイの画面 49 枚で、出荷閾値 0.7 の誤検出が 6 → 0 になった。
固定 val の検出は 68/70 → 67/70 で、差は誤差の範囲（下の「中身」を参照）。

| 出荷閾値 0.7 | 09-25 (基準) | 10-07 (89枚全部) | **10-07 (14枚に間引き・採用)** |
|---|---|---|---|
| 固定 val 80 枚の検出 | 68/70 | 63/70 | **67/70** |
| 固定 val の余分な候補 | 0 | 4 | 3 |
| 初見のオーバーレイ 49 枚の誤検出 | 6 枚 | (学習に使用) | **0 枚** |
| mAP50 / 50-95 (pycocotools) | 0.980 / 0.667 | 0.989 / 0.661 | 0.977 / 0.657 |

閾値は 0.7 のまま。0.5 に下げるとオーバーレイの誤検出が 1 件出る。

## 追加したデータ

`session_20261006_223249`: VR (2984x3256) で撮った 90 枚。アノテーションは Ollama の
`qwen3-vl:4b` で下書きした（座標は 0〜1000 正規化の `[x1,y1,x2,y2]` で返る。
thinking モデルなので答えが `thinking` 側に入る点に注意）。正例 1 枚と負例 2 枚は目視で確認した。**89 枚が吹き出しなし**（オーバーレイの窓や
デスクトップの窓が写った画面）、1 枚 (000083) だけがオーバーレイと本物の吹き出し
「疲れた」が同時に写った正例。

## やったこと

### 1. 89 枚をそのまま足した（不採用）

追加分を全部 train に入れて、09-25 と同じ設定（YOLOX-Tiny、入力 1280、スケール拡張あり、
80 epoch、seed 0）で学習した。

閾値 0.15 で見ると 70/70 で良く見えたが、**出荷閾値 0.7 では 63/70 に落ちた**。
外れた分を1件ずつ見ると、枠の位置は合っている (IoU 0.66〜0.92) のにスコアだけが
0.38〜0.68 に下がっていた。

原因は量より中身の偏りと見ている。

- 89 枚は 2 秒周期の連番で、ほぼ同じ部屋・同じオーバーレイの絵だった。
- その絵（暗い角丸パネル + 文字）は、モデルが吹き出しを見分ける手がかりと重なる。
  同じ絵で 89 回「これは違う」と教えたので、本物の吹き出しのスコアも一緒に下がった。
- 89 枚全部を学習に入れたので、初めて見るオーバーレイで効くかは測れなかった。

### 2. 間引いて 14 枚にした（採用）

90 枚を連続 10 フレームごとのシーン 9 つに分け、

- **学習**: 奇数シーン (1,3,5,7) から 3 枚おきに 13 枚 + 正例の 000083 = 14 枚
- **検証**: 偶数シーン (0,2,4,6,8) の 49 枚。学習には一切入れない
- 残り 27 枚（学習シーンの隣のフレーム）はどちらにも使わない

シーンを交互に分けたので、隣のフレームが学習と検証の両方に入ることはない。
train は 340 枚（正例 255 / 負例 85）、val は固定の 80 枚のまま。

### 3. 評価は出荷閾値で行った

途中で閾値 0.15 で比べて「差し替えて良い」と誤った判断をしかけた。`BubbleDetector` の
既定は 0.7 で、モデルごとに信頼度の分布が違うので、**比較は必ず出荷閾値で行う**。

## 中身: val の差はほぼ無い

閾値 0.7 での取りこぼし 3 件・余分 3 件の内訳:

- **000089**（`session_20260914_113429`）: 横幅 1284px の横長の吹き出し。基準モデルも落とす。
- **000084**（`session_20260922_144343`）: score 0.67・IoU 0.48 で、両方ともぎりぎり届かない。
- **098 / 099**（`session_20260924_123248`）: 正解ラベルが吹き出しの真下の名前プレートまで
  含んでいる。モデルは方針どおり吹き出しだけを囲むので枠が合わず、取りこぼし扱いになる。
  余分な候補の 3 件もすべてこの 2 枚で、**全部正解枠の内側**にある（同じ吹き出しへの
  重複が混じる）。val 上の本当の誤検出は 0。

098/099 のラベルを吹き出しだけに直せば数字はもっと正確になる。val は固定なので、
直すかどうかは未決（直すなら同じシーンの train 側も揃える）。

## データの置き場所

- 学習に使わなかった 76 枚は `dataset_annotated/` の外へ移した。置いたままだと
  `prepare_yolo_dataset.py` が train に戻してしまうため。
  - `dataset_holdout/overlay_test_20261006/`: 検証用 49 枚（偶数シーン）
  - `dataset_holdout/overlay_unused_20261006/`: 使わない 27 枚（学習シーンの隣接フレーム）
  - どちらも `.git/info/exclude` で git の対象外。
- `dataset_annotated/session_20261006_223249/` は学習に使う 14 枚だけになっている。
  `prepare_yolo_dataset.py` を流すと今回と同じ train 340 / val 80 が再現する。
- 学習結果: 採用モデルは `runs/chatbox_yolox_tiny/`、89 枚版は
  `runs/chatbox_yolox_tiny_overlay89_1007/`、09-25 版は `runs/chatbox_yolox_tiny_base_0925/`。

## 再現手順

```powershell
.\.venv\Scripts\python.exe -X utf8 tools\prepare_yolo_dataset.py
.\.venv\Scripts\python.exe -X utf8 tools\prepare_yolox_dataset.py
.\.venv-yolox\Scripts\python.exe -X utf8 tools\yolox_chatbox_train.py -c weights\yolox_tiny.pth
.\.venv-yolox\Scripts\python.exe -X utf8 tools\yolox_chatbox_export.py `
    -c runs\chatbox_yolox_tiny\best_ckpt.pth --size 736,1280 --dynamic `
    -o runs\chatbox_yolox_tiny\chatbox_yolox_tiny.onnx
.\.venv-yolox\Scripts\python.exe -X utf8 tools\yolox_chatbox_quantize.py `
    -i runs\chatbox_yolox_tiny\chatbox_yolox_tiny.onnx `
    -o src-python\models\ocr\onnx\chatbox_yolox_tiny.onnx --size 736,1280

# 固定 val (出荷閾値)
.\.venv\Scripts\python.exe -X utf8 tools\eval_bubble_onnx.py `
    --model src-python\models\ocr\onnx\chatbox_yolox_tiny.onnx --conf 0.7
# 初見のオーバーレイ (extra candidates が誤検出数)
.\.venv\Scripts\python.exe -X utf8 tools\eval_bubble_onnx.py `
    --model src-python\models\ocr\onnx\chatbox_yolox_tiny.onnx --conf 0.7 `
    --dir dataset_holdout\overlay_test_20261006
```

`eval_bubble_onnx.py` の `--dir` はこの作業で足した。`images/` と `annotations/` を持つ
フォルダの全画像で測るので、学習に入れていない画面での誤検出を再学習のたびに確かめられる。

RTX 2080 Ti で学習は約 46 分（340 枚・80 epoch、VRChat を閉じた状態）。

## 残っていること

- **実機確認**。ここまでは保存した画像での確認で、VRChat + VRCT のオーバーレイを
  動かした状態では見ていない。
- 098/099 のラベル修正（上記）。
- 次に足すなら、**オーバーレイと本物の吹き出しが同じ画面に写った VR 画像**が一番効く。
  「暗いパネルは全部違う」ではなく「これは吹き出し、こっちはオーバーレイ」を同じ画面で
  見分けさせられる。今回は 000083 の 1 枚しかない。
- 連番で撮ったネガティブは間引いて入れる（`docs/ocr_yolo_training.md` の「ネガティブの足し方」）。
