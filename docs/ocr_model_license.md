# チャットボックス検出モデルのライセンスと出自

`src-python/models/ocr/onnx/chatbox_yolov8n.onnx` の権利関係をまとめる。
リポジトリ全体は MIT だが、**このファイルだけは MIT の対象外**で AGPL-3.0。
正式な表記は [`NOTICE.md`](../NOTICE.md) と
[`src-python/models/ocr/onnx/NOTICE.txt`](../src-python/models/ocr/onnx/NOTICE.txt)。

## なぜ MIT にできないか

学習の起点が `tools/yolo_chatbox_train.yaml` の `model: weights/yolov8n.pt`、
つまり **Ultralytics が AGPL-3.0 で配布している COCO 事前学習重み**で、
学習・エクスポートも `ultralytics==8.3.203`（AGPL-3.0）で行っている。

Ultralytics は「自社ソフトウェアで学習した重みも AGPL-3.0 の派生物であり、
それ以外の条件で使うには Enterprise License が必要」という立場を公表している。
VRCT はそのライセンスを持っていないので、**自分が受け取った条件より広い許諾を
第三者に出すことはできない**。MIT で配るのは、持っていない権利を許諾している状態になる。

「プログラムの出力は派生物ではない」（GNU の GPL FAQ）という一般論による反論はあるが、
今回は出力ではなく AGPL で配布された重みそのものを初期値にした継続学習なので、
その反論が最も効きにくいケースに当たる。

## ライセンスの連鎖

| 要素 | 出所 | ライセンス |
|---|---|---|
| `weights/yolov8n.pt`（学習の初期値） | Ultralytics | AGPL-3.0 |
| `ultralytics==8.3.203`（学習・エクスポート） | Ultralytics | AGPL-3.0 |
| 学習データ（VRChat のスクリーンショット + 人手確定アノテーション） | 自前収集（`tools/ocr_dataset_collector.py`） | 非公開・未配布 |
| **`chatbox_yolov8n.onnx`（成果物）** | 上記の派生 | **AGPL-3.0** |
| RapidOCR / PP-OCR の ONNX（文字認識側） | RapidAI | Apache-2.0 |

`rapidocr==3.9.2` は Apache-2.0 で、`tools/fetch_ocr_models.py` が取得する
PP-OCR の重みも同じく Apache-2.0。こちらは制約にならない。

## 配布時にやること

AGPL 13条（ネットワーク越しの利用者へのソース提供）は、VRCT がローカルで動く
デスクトップアプリでモデルをネットワーク越しに提供していないので発動しない。
義務として残るのは、配布物へのライセンス全文と著作権表示の添付。

- 全文は `src-python/models/ocr/onnx/LICENSE.txt` に置いてある。
- `spec/backend.spec` / `spec/backend_cuda.spec` は `src-python/models/ocr/onnx`
  ディレクトリごと `ocr_onnx/` として同梱するので、`LICENSE.txt` と `NOTICE.txt` は
  **自動的に配布物へ入る**。モデルを差し替えるときにこの2ファイルを消さないこと。

## 残っているリスク

1. **MIT 本体との同梱**。AGPL のモデルを MIT のアプリと同じインストーラで配る形になる。
   モデルは onnxruntime が実行時に読み込むデータであってコードとリンクしていないので
   単なる集積（mere aggregation）と解する余地はあるが、Ultralytics 側の解釈はより広い。
   完全に切り離したいなら、下表の「許諾の緩い基盤で再学習」しかない。
2. **過去のリリース**。`51e60af`（2026-09）以降、この表記なしで配布していた期間がある。
   表記の修正で将来は直るが、既に取得された分は取り消せない。
3. **配布しているのが ONNX だけ**。AGPL は著作物の「改変に適した形式」を求めるが、
   配布しているのはエクスポート後の `.onnx` で、再学習の起点になるのは `runs/chatbox/weights/best.pt`
   の方。厳密に詰めるなら `best.pt` もリリースアセットとして公開しておくと隙がなくなる。
   学習設定 (`tools/yolo_chatbox_train.yaml`)、前処理 (`tools/prepare_yolo_dataset.py`)、
   手順 (`docs/ocr_yolo_training.md`) は既に公開済み。学習データそのものが
   Corresponding Source に当たるかは定説がない。
4. 上記はいずれも法律の専門家の判断ではない。配布形態を確定させる前に一度相談することを勧める。

## 方針: 許諾の緩い基盤へ載せ替える

2026-09 に次の順で検討し、**Apache-2.0 の基盤で再学習して権利を自前に戻す**方針とした。

1. まず独自の制限は課さず、YOLOv8 のライセンス (AGPL-3.0) に準拠することにした。
   VRCT 本体は MIT の OSS なので、善意のフォークが吹き出し検出を使えなくなる形は取らない。
2. 次に、同梱をやめて実行時ダウンロードにすれば VRCT はモデルの頒布者にならない、という
   案を検討した。GPL/AGPL の義務は頒布に付きエンドユーザーのローカル実行には付かないので
   理屈は通るが、`fetch_ocr_models.py` と本 doc に明記してきた「実行時にネットワークへ出る
   経路を作らない」という設計判断とオフライン動作を手放す取引になるため見送った。
   なお、ビルド時取得では出荷物にモデルが入るのでこの効果は得られない。
3. 結論として載せ替えを選んだ。同梱の可否、Corresponding Source、MIT との混在、
   過去リリースの汚染が、まとめて解消するため。

**載せ替えが完了するまでは、現行モデルは AGPL-3.0 準拠のまま運用する。**
`LICENSE` の除外節と `NOTICE.md` はそのまま有効。

選択肢を下に残す。現状は1番目、移行先は3番目。

| | 実現できること | コスト |
|---|---|---|
| AGPL-3.0 のまま（現状） | 流用側も全ソースを AGPL で公開する義務を負う。クローズドな流用は実質不可 | ゼロ |
| Ultralytics Enterprise License を購入 | 任意の独自ライセンス（VRCT 専用・再配布禁止など）を課せる | 年額課金 |
| 許諾の緩い基盤で再学習 | 権利が完全に自分のものになり、任意の条件を課せる。過去分のリスクも切れる | 再学習の手間。候補は YOLOX / RT-DETR / RF-DETR（いずれも Apache-2.0）。アノテーションは YOLO 形式から変換して再利用できる |

## 載せ替えの見通し

候補は **YOLOX-Tiny**（Megvii, Apache-2.0）。リポジトリ全体が Apache-2.0 で、COCO 事前学習
重みも同じリポジトリの Release にある。Ultralytics のような「学習した重みも派生物」という
主張は行われていない。

| | params | ONNX (fp32) |
|---|---|---|
| YOLOv8n（現行） | 3.2M | 12.2 MB（実測） |
| YOLOX-Nano | 0.91M | 約 3.6 MB |
| YOLOX-Tiny | 5.06M | 約 20 MB |
| YOLOX-S | 9.0M | 約 36 MB |

`ocr_bubble_detector.py` の差分は小さい。YOLOX の `preproc()` は letterbox のパディング色が
114 で現行と一致し、違うのは次の4点だけ。

| 現行 | YOLOX |
|---|---|
| `/ 255.0` で正規化 | 正規化なし（生の 0-255） |
| `cv2.cvtColor(BGR2RGB)` | 変換なし（BGR のまま） |
| 中央寄せパディング | 左上寄せ（`dx = dy = 0`） |
| NMS は ONNX グラフへ焼き込み | Python 側で numpy 実装 |

左上寄せになるので座標復元は単純化する。NMS を Python に持つと、エクスポート時 `conf=0.05` と
ランタイム `0.15` の二段階という分かりにくさも消え、閾値が `BubbleDetector(confidence=...)`
一箇所になる。

### 着手前に潰すこと

- **YOLOX と torch 2.7 の互換性**。`requirements.txt` が `torch>=1.7` かつ
  `# TODO: Update with exact module version` のままで、更新が止まっている兆候がある。
  `.venv-yolo` は本体と分離済みなので、詰まったら学習用 venv だけ torch を古く固定すればよい。
- **imgsz=1280 での挙動**。YOLOX-Tiny の既定入力は 416 で、1280 は想定外の使い方になる。
  FPN の stride は 8/16/32 なので動くはずだが、小さい吹き出しの取りこぼしは実測で確認する。

### データセット

現行モデルは 100枚 / 1セッション / 1ワールド。この規模では精度の支配要因はアーキテクチャ
ではなくデータで、YOLOv8n → YOLOX-Tiny の差はデータを増やす効果に埋もれる。載せ替えで
パイプラインを通し直すので、**ワールドと距離のバリエーションを足すのが最も効く**。
精度が落ちたように見えても、原因は基盤ではなくデータ側である可能性を先に疑うこと。
