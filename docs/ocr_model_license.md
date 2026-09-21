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

AGPL-3.0 はライセンス全文を著作物に添付することを求める。

- 全文は `src-python/models/ocr/onnx/LICENSE.txt` に置いてある。
- `spec/backend.spec` / `spec/backend_cuda.spec` は `src-python/models/ocr/onnx`
  ディレクトリごと `ocr_onnx/` として同梱するので、`LICENSE.txt` と `NOTICE.txt` は
  **自動的に配布物へ入る**。モデルを差し替えるときにこの2ファイルを消さないこと。

## 残っているリスク

1. **MIT 本体との同梱**。AGPL のモデルを MIT のアプリと同じインストーラで配る形になる。
   モデルは onnxruntime が実行時に読み込むデータであってコードとリンクしていないので
   単なる集積（mere aggregation）と解する余地はあるが、Ultralytics 側の解釈はより広い。
   完全に切り離したいなら次項の「載せ替え」しかない。
2. **過去のリリース**。`51e60af`（2026-09）以降、この表記なしで配布していた期間がある。
   表記の修正で将来は直るが、既に取得された分は取り消せない。
3. 上記はいずれも法律の専門家の判断ではない。配布形態を確定させる前に一度相談することを勧める。

## 制限を強めたい場合の選択肢

「他プロジェクトに流用されたくない」を実現する道は3つ。現状の AGPL は1番目にあたる。

| | 実現できること | コスト |
|---|---|---|
| AGPL-3.0 のまま（現状） | 流用側も全ソースを AGPL で公開する義務を負う。クローズドな流用は実質不可 | ゼロ |
| Ultralytics Enterprise License を購入 | 任意の独自ライセンス（VRCT 専用・再配布禁止など）を課せる | 年額課金 |
| 許諾の緩い基盤で再学習 | 権利が完全に自分のものになり、任意の条件を課せる。過去分のリスクも切れる | 再学習の手間。候補は YOLOX / RT-DETR / RF-DETR（いずれも Apache-2.0）。アノテーションは YOLO 形式から変換して再利用できる |
