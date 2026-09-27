"""YOLO形式のラベルをYOLOX学習用のCOCO JSONへ変換する。

python tools/prepare_yolox_dataset.py

tools/prepare_yolo_dataset.py が作った dataset_annotated/train.txt と val.txt を
そのまま読み、dataset_annotated/annotations/ に COCO 形式の JSON を書き出す。
画像は複製しない(COCODataset の data_dir を dataset_annotated、name を "" にして
file_name にセッション込みの相対パスを入れる)。

分割を作り直さないのは、YOLOv8n との比較を同じ train/val で行うため。
先に prepare_yolo_dataset.py を実行しておくこと。
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1] / "dataset_annotated"
CATEGORIES = [{"id": 1, "name": "chat", "supercategory": "chat"}]


def build(split: str) -> dict:
    listing = ROOT / f"{split}.txt"
    if not listing.is_file():
        raise SystemExit(f"not found: {listing} (run tools/prepare_yolo_dataset.py first)")

    images, annotations = [], []
    for image_id, line in enumerate(listing.read_text(encoding="utf-8").splitlines(), start=1):
        entry = line.strip()
        if not entry:
            continue
        relative = entry[2:] if entry.startswith("./") else entry
        image_path = ROOT / relative
        frame = cv2.imread(str(image_path))
        if frame is None:
            raise SystemExit(f"unreadable image: {image_path}")
        height, width = frame.shape[:2]
        images.append({
            "id": image_id,
            "file_name": relative,
            "width": width,
            "height": height,
        })

        label_path = image_path.parents[1] / "labels" / f"{image_path.stem}.txt"
        if not label_path.is_file():
            raise SystemExit(f"missing label: {label_path}")
        for row in label_path.read_text(encoding="utf-8").splitlines():
            fields = row.split()
            if not fields:
                continue
            class_id, cx, cy, bw, bh = int(fields[0]), *(float(v) for v in fields[1:5])
            x = (cx - bw / 2) * width
            y = (cy - bh / 2) * height
            w, h = bw * width, bh * height
            annotations.append({
                "id": len(annotations) + 1,
                "image_id": image_id,
                "category_id": class_id + 1,  # COCOのidは1始まり
                "bbox": [x, y, w, h],
                "area": w * h,
                "iscrowd": 0,
            })

    return {"images": images, "annotations": annotations, "categories": CATEGORIES}


def main() -> None:
    output_dir = ROOT / "annotations"
    output_dir.mkdir(exist_ok=True)
    for split in ("train", "val"):
        dataset = build(split)
        target = output_dir / f"instances_{split}_chatbox.json"
        target.write_text(json.dumps(dataset), encoding="utf-8")
        positives = len({a["image_id"] for a in dataset["annotations"]})
        print(f"{target.name}: {len(dataset['images'])} images "
              f"({positives} positive), {len(dataset['annotations'])} boxes")


if __name__ == "__main__":
    main()
