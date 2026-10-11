"""RapidOCR (VRCT の設定) の各段階の途中結果を書き出す。Rust 移植と段階ごとに比べるため。

使い方 (PowerShell, リポジトリ直下):
  $env:PYTHONPATH = "src-python"
  .venv\\Scripts\\python.exe -X utf8 native\\vrct-ocr\\scripts\\rapidocr_stages.py tmp\\poc-ort <dataset_annotated> [auto|Korean]

<out>/crops_all/ に検証用画像 (val_fixed.txt の全画像) から YOLOX で切り出した吹き出しを書き、
<out>/stages_<language>.json に次を書く:
  pre    … resize_image_within_bounds 後の大きさと比率、縦の余白
  det    … 検出の入力の大きさ、箱 (並べ替え後、元画像へ戻す前) とスコア
  lines  … 行画像の大きさ (get_rotate_crop_image 後)、向き判定のラベルとスコア
  rec    … 行ごとの文字列とスコア
  final  … RapidOCR の戻り値 (txts / scores / boxes)
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

OUT = Path(sys.argv[1])
DATASET = Path(sys.argv[2])
LANGUAGE = sys.argv[3] if len(sys.argv) > 3 else "auto"


def crops() -> list:
    crops_dir = OUT / "crops_all"
    if crops_dir.exists():
        return sorted(str(p) for p in crops_dir.glob("*.png"))
    from models.ocr.ocr_bubble_detector import BubbleDetector

    crops_dir.mkdir()
    detector = BubbleDetector()
    detector.loadModel()
    paths = []
    for i, line in enumerate((DATASET / "val_fixed.txt").read_text().split()):
        frame = cv2.imread(str(DATASET / line), cv2.IMREAD_COLOR)
        for j, (_, crop) in enumerate(detector.detect(frame)):
            path = crops_dir / f"{i:03d}_{j}.png"
            cv2.imwrite(str(path), crop)
            paths.append(str(path))
    return paths


def main() -> None:
    from models.ocr import ocr_engine_rapidocr as engine
    from models.ocr.ocr_languages import resolveModelSpec
    from rapidocr.ch_ppocr_rec import TextRecInput
    from rapidocr.utils.process_img import apply_vertical_padding

    reader = engine.getReader(resolveModelSpec(LANGUAGE))
    out = []
    for path in crops():
        crop = cv2.imread(path, cv2.IMREAD_COLOR)
        item = {"path": path}
        img, op_record = reader.preprocess_img(crop)
        padded, op_record = apply_vertical_padding(img, dict(op_record), reader.width_height_ratio,
                                                   reader.min_height)
        item["pre"] = {"shape": list(img.shape[:2]), "ratio_h": op_record["preprocess"]["ratio_h"],
                       "ratio_w": op_record["preprocess"]["ratio_w"], "pad_top": op_record["padding_1"]["top"]}
        det_pre = reader.text_det.get_preprocess(max(padded.shape[:2]))(padded)
        det = reader.text_det(padded)
        item["det"] = {"input": list(det_pre.shape), "boxes": [] if det.boxes is None else det.boxes.tolist(),
                       "scores": [float(s) for s in (det.scores or [])]}
        if det.boxes is not None:
            line_imgs = reader.crop_text_regions(padded, det.boxes)
            cls = reader.text_cls(line_imgs)
            rec = reader.text_rec(TextRecInput(img=cls.img_list))
            item["lines"] = [{"shape": list(li.shape[:2]), "cls": [c[0], float(c[1])]}
                             for li, c in zip(line_imgs, cls.cls_res)]
            item["rec"] = [[t, float(s)] for t, s in zip(rec.txts, rec.scores)]
        result = reader(crop)
        item["final"] = {"txts": list(result.txts or []), "scores": [float(s) for s in (result.scores or [])],
                         "boxes": [] if result.boxes is None else np.asarray(result.boxes).tolist()}
        out.append(item)
    name = OUT / f"stages_{LANGUAGE}.json"
    json.dump(out, open(name, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(out)} crops -> {name}")


if __name__ == "__main__":
    main()
