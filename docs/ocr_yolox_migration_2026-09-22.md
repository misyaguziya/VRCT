# 吹き出し検出を YOLOX へ載せ替えられるかの検証 (2026-09-22)

[docs/ocr_model_license.md](ocr_model_license.md) で決めた「許諾の緩い基盤で再学習する」方針
(候補: YOLOX-Tiny, Apache-2.0) について、**精度が落ちないか**と**VRCT に組み込めるか**を
実機で確認した記録。ブランチは `ocr-yolox`。

## 結論

**載せ替えた。** 精度は実用上同等、速度と容量はむしろ改善、組み込みの差分は小さい。

| | YOLOv8n (旧) | YOLOX-Tiny (新) |
|---|---|---|
| ライセンス | AGPL-3.0 (Ultralytics 由来) | VRCT 専用の利用許諾 (基盤は Apache-2.0) |
| mAP50 / mAP50-95 | 0.988 / 0.723 | 0.985 / 0.661 |
| 取りこぼし (conf 0.15) | 0/20 | 1/20 |
| CPU 推論 | 165 ms (1280x1280 fp32) | **61 ms** (16:9 の窓、可変入力 INT8) |
| ONNX | 12.8 MB | **5.5 MB** |

採用したのは **入力サイズ可変 + INT8 量子化** の YOLOX-Tiny。ウィンドウの形に合わせて
余白を削るので、正方形に固定していた旧モデルより速い。`chatbox_yolov8n.onnx` は削除した。

このドキュメントは検証の記録。運用手順は
[docs/ocr_yolo_training.md](ocr_yolo_training.md)、権利関係は
[docs/ocr_model_license.md](ocr_model_license.md) に移してある。

## 精度

学習データ・train/val の分割・入力サイズ (1280)・augmentation はすべて YOLOv8n 側
([tools/yolo_chatbox_train.yaml](../tools/yolo_chatbox_train.yaml)) と揃えた。基盤の差だけを見るため。

比較は [tools/eval_bubble_onnx.py](../tools/eval_bubble_onnx.py) で行う。基盤ごとの val
スクリプト (ultralytics / YOLOX) をそのまま比べると mAP の実装差が混ざるので、
**配布時と同じ onnxruntime 推論を通し、mAP も pycocotools で揃えて**測り直している。
参考までに ultralytics の `detect val` は現行モデルに mAP50 0.986 / mAP50-95 0.710 を出す。

| | YOLOv8n (現行) | YOLOX-Tiny | YOLOX-Nano |
|---|---|---|---|
| params | 3.01 M | 5.05 M | 0.91 M |
| ONNX (fp32) | 12.8 MB | 20.6 MB | 4.1 MB |
| mAP50 | 0.988 | 0.985 | 0.927 |
| mAP75 | 0.778 | **0.859** | **0.874** |
| mAP50-95 | **0.723** | 0.661 | 0.693 |
| 平均 IoU (conf 0.01) | 0.857 | 0.828 | 0.853 |
| CPU 推論 (1280x1280 fp32, 最小) | 165 ms | 240 ms | 115 ms |

運用で効くのは mAP ではなく取りこぼしの方なので、[ocr_yolo_training.md](ocr_yolo_training.md)
の閾値の表と同じ見方も出す (val 20枚、正解 20個)。

| conf | YOLOv8n | YOLOX-Tiny | YOLOX-Nano |
|---|---|---|---|
| 0.15 (既定) | 20/20・余分5 | 19/20・余分4 | 18/20・余分3 |
| 0.25 | 19/20・余分2 | 19/20・余分4 | 18/20・余分3 |
| 0.50 | 18/20・余分0 | **19/20・余分2** | 18/20・余分3 |
| 0.01 | 20/20・余分7 | 20/20・余分11 | 19/20・余分7 |

読み方:

- **YOLOX-Tiny は閾値を上げても落ちにくい**。YOLOv8n は 0.15→0.5 で 20→18 に減るが、
  Tiny は 19 のまま。当たっている吹き出しには高い信頼度が付いている。
- **既定の 0.15 で 1枚落ちる**のは frame `000089`。横幅 1284px の横長の吹き出しで、
  Tiny はこれを左右2つに割って検出する (score 0.416 と 0.354)。**YOLOv8n も同じ割り方をしていて**、
  全体を1枠で拾った候補は score 0.153 しかない (conf 0.25 では YOLOv8n も落とす)。
  アーキテクチャではなく、横長の吹き出しが学習データにほぼ無いことが原因。
- **YOLOX-Nano はもう1枚 `000085` (123x102px の小さい吹き出し) を落とす**。
  候補自体は出るが score 0.013 で、閾値を下げても実用的には拾えない。
  「Precision より Recall」という方針からは Nano は選びにくい。

データセットは 100枚 / 1セッション / 1ワールドのままなので、この差はいずれも
データを増やせば埋まる範囲にある。載せ替えの可否という問いに対しては
**YOLOX-Tiny で問題なし**。

**追記 (同日)**: 2セッション目を足して 202枚で学習し直したところ、この節の
取りこぼしはすべて解消した。val を 40枚 (2セッションから20枚ずつ) に作り直して測ると、
100枚モデルが 31/39・mAP50 0.734 なのに対し 202枚モデルは 38/39・mAP50 0.955。
**アーキテクチャではなくデータが効く**という読みが実測で裏付けられた形。

## 速度

「YOLOX-Tiny が YOLOv8n より遅い」は、**モデルを替えなくても効く手を2つ当てると逆転する**。
どちらも学習し直さずにエクスポートの設定だけで済む。

| モデル | 入力 | 検出 (conf 0.15) | 余分 | CPU 最小 | 中央値 | ONNX |
|---|---|---|---|---|---|---|
| YOLOv8n (現行) | 1280x1280 | 20/20 | 5 | 165 ms | 179 ms | 12.8 MB |
| YOLOX-Tiny | 1280x1280 | 19/20 | 4 | 240 ms | 248 ms | 20.6 MB |
| YOLOX-Tiny | 736x1280 | 19/20 | 4 | 105 ms | 110 ms | 20.4 MB |
| **YOLOX-Tiny INT8** | **736x1280** | **19/20** | **5** | **61 ms** | **64 ms** | **5.7 MB** |
| YOLOX-Nano | 1280x1280 | 18/20 | 3 | 115 ms | 123 ms | 4.1 MB |
| YOLOX-Nano | 736x1280 | 18/20 | 3 | 49 ms | 52 ms | 3.9 MB |
| YOLOX-Nano INT8 | 736x1280 | 19/20 | 3 | 37 ms | 39 ms | 1.7 MB |

Intel Core i7-9700K (8コア) / onnxruntime 1.30 / CPUExecutionProvider。1モデルずつ別プロセスで
20回計測し、全モデルを1回の計測で揃えた。**絶対値は同時に動いている処理で2〜3倍ぶれる**
(同じモデルが別の日に 61ms と 166ms で出た)。中央値より最小値の方が安定するが、それでも
比較するときは必ず全部を測り直すこと。複数モデルを同時に載せて測ると全部 1.5倍ほど遅く出る。

### 1. 入力から余白を削る (Tiny 240 → 105 ms)

キャプチャは 2575x1455 (16:9) なので、1280x1280 の正方形に letterbox すると
**下半分の 44% はパディングの推論に使っている**。YOLOX は余白が左上寄せなので、
高さを 736 (=723 を 32 の倍数に切り上げ) にするだけで縮尺も座標も変わらない。
val の検出結果は完全に同じだった。

### 2. INT8 静的量子化 (Tiny 105 → 61 ms、サイズ 20.4 → 5.7 MB)

[tools/yolox_chatbox_quantize.py](../tools/yolox_chatbox_quantize.py)。校正は学習画像 20枚。
**開発マシンでやる作業で、配布物に増える依存は無い** (VRCT は今までどおり onnxruntime で読むだけ)。

予測conv以降 (sigmoid と grid/stride のデコード) を fp32 のまま残すのが要点。

| 量子化の仕方 | 検出 (conf 0.15) | 速度 |
|---|---|---|
| グラフ全体 | **0/20** (obj/cls が 0 に潰れる) | 86 ms |
| Conv だけ | 19/20 | 264 ms (conv のたびに fp32 へ戻すので逆に遅い) |
| **全体から head を除外** | **19/20** | **98 ms** |

(この表だけ YOLOX-Nano の単独計測。Tiny でも同じ傾向。)

### 3. 入力サイズを可変にする (採用した形)

`ocr_capture_hwnd.py` は VRChat のウィンドウ矩形をそのまま使うので、ユーザーが
リサイズすればアスペクト比は 16:9 とは限らない。そこで 736x1280 に固定せず、
**長辺を 1280 に合わせて短辺を 32 の倍数へ切り上げる**形にした
(`BubbleDetector._letterbox`)。縮尺は長辺で決まるので、窓の形が変わっても
吹き出しの見かけの大きさは変わらない。

同梱モデルは `--dynamic` でエクスポートしてある。量子化後も可変のまま動く。

| ウィンドウ | 入力 | CPU 最小 | 検出 |
|---|---|---|---|
| 2575x1455 (収集時) | 1280x736 | 61 ms | 19/20 |
| 1920x1080 | 1280x736 | 61 ms | 19/20 |
| 1280x720 | 1280x736 | 61 ms | 19/20 |
| 960x540 | 1280x736 | 61 ms | 19/20 |
| 3440x1440 (ウルトラワイド) | 1280x544 | — | 19/20 |
| 1000x1400 (縦長) | 928x1280 | 79 ms | — |
| 1024x1024 (正方形、最悪ケース) | 1280x1280 | 112 ms | — |

`BubbleDetector` を通した実測。**どの窓の大きさでも 19/20 で変わらない**。
最悪ケースの正方形の窓でも 112 ms で、旧 YOLOv8n の 165 ms より速い。

### 注意
- **INT8 はモデルを学習し直すたびにやり直す**。量子化後は conf 0.01 付近の弱い候補が
  増える (Tiny で 11 → 56)。実行時の既定 0.15 では影響しないが、閾値を下げて使うときは効く。
- **固定形状のモデルに差し替えないこと**。`_letterbox` が窓に合わせた形で入力を作るので、
  固定入力の ONNX を置くと onnxruntime が形の不一致で落ち、`detect()` が例外を握りつぶして
  「OCR は動くが何も出ない」状態になる。`TestRealModelSmoke` が 4 種類の窓で検出を回して守っている。
- 速度はどれも **val 画像 20枚と乱数入力での計測**で、VRChat を動かしての確認はしていない。
- **ウィンドウの形が変わると onnxruntime が入力形状ごとに最適化をやり直す**。
  リサイズ直後の 1 tick だけ遅くなるはずだが、実機で測っていない。

### 他の基盤も見たか

Apache-2.0 / MIT / BSD で、COCO 事前学習重みも同じ許諾のものを調べた結果:

| 候補 | 判断 | 理由 |
|---|---|---|
| NanoDet-Plus-m | 次点 | Apache-2.0、1.17M params、ONNX 公式サポート。ただし**最終更新が 2023-01**で 3年止まっている |
| PP-PicoDet | 見送り | Apache-2.0 で設計もモバイルCPU向きだが、学習と ONNX 変換に PaddlePaddle が要る |
| RTMDet-tiny | 見送り | Apache-2.0 だが mmcv のプリビルドが torch 2.4 までで、Windows のソースビルドが重い。ONNX も mmdeploy 前提 |
| DAMO-YOLO | 見送り | Apache-2.0 だが最終 push 2024-05 でメンテ終了 |
| RT-DETR / D-FINE / RF-DETR | 見送り | ライセンスは可。ただし **DETR 系は CPU 推論が構造的に不利**。RT-DETR-L は Intel CPU の 960px 入力で 285ms、RF-DETR-Nano は 320px でも約 180ms |
| torchvision SSDLite / FCOS | 見送り | BSD-3-Clause で最も安全だが、SSDLite は 320 入力前提で小物体に弱く、FCOS は backbone が ResNet50 で桁が違う |

**いずれも YOLOX-Tiny INT8 の 166ms を明確に上回る根拠が無いので、基盤の変更は不要**と判断した。
どうしても足りないときの次の一手は、NanoDet-Plus-m を試すか、入力の長辺を 1280 から
1024 あたりへ下げる (取りこぼしの実測が要る)。

## 組み込み

差分は小さい。前処理と後処理が変わるだけで、インタフェース (`BubbleDetector.detect()` が
信頼度の降順で `[(bbox, 切り出しBGR), ...]` を返す) は同じ。

| | YOLOv8n | YOLOX |
|---|---|---|
| 正規化 | `/ 255.0` | なし (生の 0-255) |
| 色順 | `cvtColor(BGR2RGB)` | BGR のまま |
| letterbox の余白 | 中央寄せ | 左上寄せ (座標の戻しが `/ scale` だけになる) |
| ONNX の出力 | `[n, 6]` NMS 済み xyxy | `[1, 33600, 6]` NMS 前 cxcywh + obj + cls |
| NMS | グラフに焼き込み | Python 側 (numpy) |

NMS が Python 側に来るのは、むしろ現行の分かりにくさを1つ消す。YOLOv8n は
エクスポート時の `conf=0.05` が NMS へ焼き込まれていて、実行時に閾値を下げても
候補が増えなかった。YOLOX では閾値が `BubbleDetector(confidence=...)` 一箇所になる。
grid/stride のデコードはエクスポート時にグラフへ入れた (`decode_in_inference=True`) ので、
VRCT 側に持つのは letterbox・閾値・NMS・座標の戻しだけ。

実施済み (すべてこのブランチにある):

- [src-python/models/ocr/ocr_bubble_detector.py](../src-python/models/ocr/ocr_bubble_detector.py) — 上記の差し替え、`nonMaxSuppression()` を追加
- [src-python/test/test_ocr_bubble_detector.py](../src-python/test/test_ocr_bubble_detector.py) — 前処理・NMS のテストを追加、座標テストを左上寄せへ
- `src-python/models/ocr/onnx/chatbox_yolox_tiny.onnx` を配置、`chatbox_yolov8n.onnx` を削除
- ライセンス表記: `LICENSE` の除外節、`NOTICE.md`、`onnx/LICENSE.txt` / `LICENSE.en.txt` /
  `NOTICE.txt`、`docs/readmes/README.*.md` (4言語)
- ドキュメント: [ocr_yolo_training.md](ocr_yolo_training.md) を YOLOX 版に書き直し、
  [ocr_model_license.md](ocr_model_license.md) と
  [src-python/docs/details/ocr.md](../src-python/docs/details/ocr.md) を更新
- `requirements-yolo-train.txt` と `tools/yolo_chatbox_train.yaml` を削除 (YOLOv8 の学習経路は廃止)
- 学習・エクスポート・量子化一式 (下記) と [requirements-yolox-train.txt](../requirements-yolox-train.txt)

Python テストは全件通る (943 passed)。`spec/backend.spec` / `spec/backend_cuda.spec` は
`onnx` ディレクトリごと同梱するので **変更不要**。

残っている作業 (いずれも「載せ替える」と決めてからでよい):

- **実機確認**。ここまでは全部 val 画像での机上検証で、VRChat を動かしていない。
- ~~**データの追加**~~。2026-09-22 に2セッション目 (102枚 / 別ワールド / 1936x1048) を
  足して再学習した。落としていた横長の吹き出しは1枠で取れるようになり、別ワールドでの
  取りこぼしも 8→1 に減った。結果は `ocr_yolo_training.md` の履歴表。
- **弁護士の確認**。`LICENSE.txt` の条文は法律の専門家が書いたものではない。

## 学習環境

本体の `.venv` とも YOLOv8 用の `.venv-yolo` とも分ける。YOLOX は clone をそのまま使う
(`pip install` だけだと `tools/` と `exps/` が手に入らない)。clone には手を入れていない。

```powershell
git clone --depth 1 https://github.com/Megvii-BaseDetection/YOLOX.git .yolox-src
py -3.11 -m venv .venv-yolox
.\.venv-yolox\Scripts\python.exe -m pip install -r requirements-yolox-train.txt
.\.venv-yolox\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .yolox-src
curl.exe -L -o weights\yolox_tiny.pth https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_tiny.pth
```

```powershell
.\.venv\Scripts\python.exe -X utf8 tools\prepare_yolo_dataset.py    # labels/ と train/val の分割 (既存)
.\.venv\Scripts\python.exe -X utf8 tools\prepare_yolox_dataset.py   # 同じ分割を COCO JSON へ
.\.venv-yolox\Scripts\python.exe -X utf8 tools\yolox_chatbox_train.py -c weights\yolox_tiny.pth
.\.venv-yolox\Scripts\python.exe -X utf8 tools\yolox_chatbox_export.py `
    -c runs\chatbox_yolox_tiny\best_ckpt.pth -o src-python\models\ocr\onnx\chatbox_yolox_tiny.onnx
.\.venv\Scripts\python.exe -X utf8 tools\eval_bubble_onnx.py `
    --model src-python\models\ocr\onnx\chatbox_yolox_tiny.onnx --coco-eval
```

RTX 2080 Ti で `imgsz=1280 batch=8` の VRAM は約 6.2GB、150 epoch が Tiny で約 38分、Nano で約 28分。
`tools/prepare_yolox_dataset.py` は画像を複製しない (COCODataset の `data_dir` を
`dataset_annotated`、`name` を空にして `file_name` にセッション込みの相対パスを入れている)。

### Windows で詰まった所

YOLOX 0.3.0 は 2022年で更新が止まっていて、Linux + 旧 torch を前提にしている。
本家 clone を書き換えずに回避できたので、再 clone しても同じ手順で通る。

| 症状 | 原因 | 回避 |
|---|---|---|
| `tools/train.py` が起動直後に `UnicodeDecodeError` | `configure_nccl()` が Linux 専用のシェルコマンドを叩き、cmd の cp932 出力を utf-8 で読む | 単一GPU分だけを写した [tools/yolox_chatbox_train.py](../tools/yolox_chatbox_train.py) から起動する。NCCL は複数GPUの設定なので単一GPUでは不要 |
| 最初の eval で学習ごと停止 | `COCOEvaluator` が C++ 拡張 `fast_cocoeval` を JIT ビルドし、MSVC 不在で `CalledProcessError`。本家の fallback は `ImportError` しか拾わない | 空の `yolox.layers` を `sys.modules` に先に差して pycocotools の `COCOeval` に落とす (同モジュールを import するのは `coco_evaluator` だけ) |
| エクスポートで `torch.load` が失敗 | torch 2.6 以降の `weights_only=True`。YOLOX の checkpoint が `best_ap` を numpy スカラーで持つ | numpy スカラーだけ `add_safe_globals` で許可。`weights_only=True` のまま読む ([tools/yolox_chatbox_export.py](../tools/yolox_chatbox_export.py)) |

想定していた numpy 2.x 由来の非互換 (`np.float` 等) は出なかった。Megvii 配布の
`yolox_tiny.pth` / `yolox_nano.pth` は `weights_only=True` のまま読める。
`pycocotools` は cp311 の Windows wheel があり、MSVC は要らない。

検証環境: Windows 11 / CPython 3.11.5 x64 / torch 2.7.0+cu128 / numpy 2.4.6 /
opencv-python 5.0.0.93 / onnxruntime 1.30.0 / RTX 2080 Ti。

### 学習設定

[tools/yolox_chatbox_exp.py](../tools/yolox_chatbox_exp.py) (Tiny) と
[tools/yolox_chatbox_exp_nano.py](../tools/yolox_chatbox_exp_nano.py) (Nano)。
YOLOv8n 側の yaml と対応させてある。

| yolo_chatbox_train.yaml | yolox_chatbox_exp.py |
|---|---|
| `imgsz: 1280` | `input_size = test_size = (1280, 1280)`, `multiscale_range = 0` |
| `epochs: 150` | `max_epoch = 150` |
| `close_mosaic: 20` | `no_aug_epochs = 20` |
| `mosaic: 0.3` | `mosaic_prob = 0.3` |
| `scale: 0.2` | `mosaic_scale = (0.8, 1.2)` |
| `translate: 0.05` | `translate = 0.05` |
| `degrees / shear: 0.0` | `degrees = shear = 0.0` |
| `fliplr: 0.5` | `flip_prob = 0.5` |
| `hsv_s / hsv_v: 0.4` | `hsv_prob = 1.0` (YOLOX は色相も僅かに振る。唯一揃っていない所) |
| `seed: 0` | `seed = 0` |

YOLOX-Tiny の既定入力は 416 で 1280 は想定外の使い方になるが、FPN の stride が
8/16/32 なので割り切れ、出力は `[1, 33600, 6]` (=160²+80²+40²) になる。
小さい吹き出しの取りこぼしは上の表のとおり YOLOv8n と同程度だった。
