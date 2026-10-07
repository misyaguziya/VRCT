"""吹き出し検出の .onnx を val 画像で実測する。基盤を載せ替えるときの比較用。

python tools/eval_bubble_onnx.py --model src-python/models/ocr/onnx/chatbox_yolox_tiny.onnx

主に見るのは mAP ではなく「取りこぼし / 余分な候補 / CPU レイテンシ」。文字起こしの
前段なので、実運用で効くのはこの3つ(docs/ocr_yolo_training.md の閾値の表と同じ観点)。
onnxruntime だけで動かすので、配布時と同じ経路を通る。--coco-eval を付けると mAP も
出す(基盤ごとの val スクリプトを比べると実装差が混ざるので、こちらで揃える)。
pycocotools が要るので、その場合は .venv-yolox から実行する。

--dir dataset_holdout/overlay_test_20261006 のように images/ と annotations/ を持つ
フォルダを渡すと、split の代わりにその中の全画像で測る。学習に入れていない画面
(VRCT 自身のオーバーレイなど)での誤検出を、学習し直すたびに確かめるため。
"""

from __future__ import annotations

import argparse
from pathlib import Path
from time import perf_counter

import cv2
import numpy as np
import onnxruntime as ort

ROOT = Path(__file__).resolve().parents[1] / "dataset_annotated"
PAD_COLOR = 114


def letterbox(frame: np.ndarray, size) -> tuple[np.ndarray, float]:
    """BubbleDetector._letterbox と同じ前処理。BGRのまま、0-255のまま、余白は左上寄せ。"""
    h, w = frame.shape[:2]
    if isinstance(size, int):
        # BubbleDetector と同じく、長辺を size に合わせて縦横を32の倍数へ切り上げる。
        # 固定形状で測ると縦長のVRフレームだけ不当に縮む。
        scale = min(size / w, size / h)
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        size_h, size_w = -(-nh // 32) * 32, -(-nw // 32) * 32
    else:
        size_h, size_w = size
        scale = min(size_w / w, size_h / h)
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    canvas = np.full((size_h, size_w, 3), PAD_COLOR, dtype=np.uint8)
    canvas[:nh, :nw] = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
    return np.ascontiguousarray(canvas.transpose(2, 0, 1)[None], dtype=np.float32), scale


def nms(boxes: np.ndarray, scores: np.ndarray, threshold: float) -> list[int]:
    order = scores.argsort()[::-1]
    keep = []
    while order.size:
        i = order[0]
        keep.append(int(i))
        if order.size == 1:
            break
        rest = order[1:]
        xx0 = np.maximum(boxes[i, 0], boxes[rest, 0])
        yy0 = np.maximum(boxes[i, 1], boxes[rest, 1])
        xx1 = np.minimum(boxes[i, 2], boxes[rest, 2])
        yy1 = np.minimum(boxes[i, 3], boxes[rest, 3])
        inter = np.clip(xx1 - xx0, 0, None) * np.clip(yy1 - yy0, 0, None)
        areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
        order = rest[inter / (areas[i] + areas[rest] - inter) <= threshold]
    return keep


def decode(outputs, conf: float, iou: float) -> tuple[np.ndarray, np.ndarray]:
    """(xyxy(入力テンソル座標), score) を返す。出力は [1, n, 6] = cxcywh, obj, cls。"""
    predictions = np.asarray(outputs[0])[0]
    scores = predictions[:, 4] * predictions[:, 5:].max(axis=1)
    keep = scores >= conf
    predictions, scores = predictions[keep], scores[keep]
    boxes = np.empty((len(predictions), 4), dtype=np.float32)
    boxes[:, 0] = predictions[:, 0] - predictions[:, 2] / 2
    boxes[:, 1] = predictions[:, 1] - predictions[:, 3] / 2
    boxes[:, 2] = predictions[:, 0] + predictions[:, 2] / 2
    boxes[:, 3] = predictions[:, 1] + predictions[:, 3] / 2
    kept = nms(boxes, scores, iou)
    return boxes[kept], scores[kept]


def ground_truth(image_path: Path) -> np.ndarray:
    label = image_path.parents[1] / "labels" / f"{image_path.stem}.txt"
    if not label.is_file():  # --dir のフォルダは labels/ を持たない
        label = image_path.parents[1] / "annotations" / f"{image_path.stem}.txt"
    frame_h, frame_w = cv2.imread(str(image_path)).shape[:2]
    boxes = []
    for row in label.read_text(encoding="utf-8").splitlines():
        fields = row.split()
        if fields:
            cx, cy, bw, bh = (float(v) for v in fields[1:5])
            boxes.append([(cx - bw / 2) * frame_w, (cy - bh / 2) * frame_h,
                          (cx + bw / 2) * frame_w, (cy + bh / 2) * frame_h])
    return np.asarray(boxes, dtype=np.float32).reshape(-1, 4)


def iou_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    if not len(a) or not len(b):
        return np.zeros((len(a), len(b)), dtype=np.float32)
    x0 = np.maximum(a[:, None, 0], b[None, :, 0])
    y0 = np.maximum(a[:, None, 1], b[None, :, 1])
    x1 = np.minimum(a[:, None, 2], b[None, :, 2])
    y1 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x1 - x0, 0, None) * np.clip(y1 - y0, 0, None)
    area_a = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    area_b = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / (area_a[:, None] + area_b[None, :] - inter)


def cocoEval(split: str, detections: list[dict]) -> None:
    """prepare_yolox_dataset.py が書いた COCO JSON を正解にして mAP を出す。

    conf の影響を受けるので、--conf は低め(0.01)にして呼ぶこと。
    """
    import json
    from contextlib import redirect_stdout
    from io import StringIO
    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval

    annotation = ROOT / "annotations" / f"instances_{split}_chatbox.json"
    with redirect_stdout(StringIO()):
        truth = COCO(str(annotation))
        if not detections:
            print("no detections")
            return
        predicted = truth.loadRes(json.loads(json.dumps(detections)))
        evaluator = COCOeval(truth, predicted, "bbox")
        evaluator.evaluate()
        evaluator.accumulate()
        evaluator.summarize()
    print(f"mAP      : 50-95 {evaluator.stats[0]:.3f}  50 {evaluator.stats[1]:.3f} "
          f" 75 {evaluator.stats[2]:.3f}  (pycocotools, {annotation.name})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--split", default="val")
    parser.add_argument("--dir", type=Path, default=None,
                        help="images/ と annotations/ を持つフォルダ。指定すると --split の代わりに使う")
    parser.add_argument("--imgsz", default="1280", help="長辺のサイズ(既定1280、実機と同じ可変形状)。H,W を渡すと固定形状")
    parser.add_argument("--conf", type=float, default=0.15)
    parser.add_argument("--iou", type=float, default=0.65, help="NMSの閾値")
    parser.add_argument("--match-iou", type=float, default=0.5)
    parser.add_argument("--coco-eval", action="store_true",
                        help="同じ実装(pycocotools)で mAP も出す。基盤ごとの val スクリプトを"
                             "そのまま比べると実装差が混ざるため")
    args = parser.parse_args()

    imgsz = ([int(v) for v in args.imgsz.split(",")] if "," in args.imgsz
             else int(args.imgsz))
    options = ort.SessionOptions()
    options.log_severity_level = 3
    session = ort.InferenceSession(args.model, options, providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name

    if args.dir and args.coco_eval:
        raise SystemExit("--coco-eval は --split の COCO JSON を使うので --dir とは併用できない")
    if args.dir:
        images = sorted((args.dir / "images").glob("*.png"))
    else:
        images = [ROOT / (line.strip()[2:] if line.strip().startswith("./") else line.strip())
                  for line in (ROOT / f"{args.split}.txt").read_text(encoding="utf-8").splitlines()
                  if line.strip()]
    matched = missed = extra = 0
    ious: list[float] = []
    latencies: list[float] = []
    worst: list[tuple[float, str]] = []
    detections: list[dict] = []
    per_session: dict[str, list[int]] = {}  # session -> [matched, total, extra]

    for image_id, image_path in enumerate(images, start=1):
        frame = cv2.imread(str(image_path))
        tensor, scale = letterbox(frame, imgsz)
        started = perf_counter()
        outputs = session.run(None, {input_name: tensor})
        latencies.append((perf_counter() - started) * 1000)

        boxes, scores = decode(outputs, args.conf, args.iou)
        boxes = boxes / scale
        truth = ground_truth(image_path)
        for box, score in zip(boxes, scores):
            detections.append({
                "image_id": image_id, "category_id": 1, "score": float(score),
                "bbox": [float(box[0]), float(box[1]),
                         float(box[2] - box[0]), float(box[3] - box[1])]})

        overlaps = iou_matrix(truth, boxes)
        used: set[int] = set()
        for row in range(len(truth)):
            candidates = [(overlaps[row, col], col) for col in range(len(boxes))
                          if col not in used and overlaps[row, col] >= args.match_iou]
            if candidates:
                best, col = max(candidates)
                used.add(col)
                matched += 1
                ious.append(float(best))
                worst.append((float(best), image_path.name))
            else:
                missed += 1
                worst.append((0.0, image_path.name))
        extra += len(boxes) - len(used)
        stats = per_session.setdefault(image_path.parents[1].name, [0, 0, 0])
        stats[0] += len(used)
        stats[1] += len(truth)
        stats[2] += len(boxes) - len(used)

    total = matched + missed
    print(f"model    : {args.model}")
    print(f"conf {args.conf} / imgsz {imgsz}  ({len(images)} images, {total} boxes)")
    print(f"detected : {matched}/{total}   missed: {missed}   extra candidates: {extra}")
    if ious:
        print(f"IoU      : mean {np.mean(ious):.3f}  min {np.min(ious):.3f}")
    print(f"CPU      : mean {np.mean(latencies):.1f} ms  median {np.median(latencies):.1f} ms")
    for name, (hit, count, more) in sorted(per_session.items()):
        print(f"  {name}: {hit}/{count}  extra {more}")
    for value, name in sorted(worst)[:3]:
        print(f"  worst  : IoU {value:.3f}  {name}")
    if args.coco_eval:
        cocoEval(args.split, detections)


if __name__ == "__main__":
    main()
