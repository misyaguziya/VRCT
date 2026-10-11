"""OCR (吹き出し検出 + RapidOCR) の基準データを、今の Python 版のコードで書き出す。

    python native/reference/export_ocr.py
      -> native/testdata/ocr/ocr-cpu.json (合成画像 testdata/ocr/images/)
    python native/reference/export_ocr.py <dataset_annotated>
      -> tmp/ocr-dataset-cpu.json (実際のスクリーンショット。val_fixed.txt の画像。リポジトリには置かない)

BubbleDetector.detect / ocr_engine_rapidocr.getReader / readtext_bgr をそのまま呼ぶ。画像は cv2.imread
(BGR)。readtext_bgr は min_confidence=0 で全行を記録する (Rust 側で同じ閾値を当てて比べる)。
画面の画像は検出した吹き出しをすべて "auto" で読む。切り出しの画像はその言語のモデルと "auto" で読む。
"""

import json
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src-python"
sys.path.insert(0, str(SRC))

from models.ocr import ocr_engine_rapidocr as engine  # noqa: E402
from models.ocr.ocr_bubble_detector import BubbleDetector  # noqa: E402
from models.ocr.ocr_languages import resolveModelSpec  # noqa: E402

readers = {}


def read(language, crop):
    if language not in readers:
        readers[language] = engine.getReader(resolveModelSpec(language))
    return engine.readtext_bgr(readers[language], crop, min_confidence=0.0)


def frame_case(detector, path, name):
    frame = cv2.imread(str(path), cv2.IMREAD_COLOR)
    found = detector.detect(frame)
    return {"image": name, "boxes": [list(b) for b, _ in found], "lines": [read("auto", crop) for _, crop in found]}


def main():
    detector = BubbleDetector()
    if len(sys.argv) > 1:
        dataset = Path(sys.argv[1])
        paths = [dataset / line.strip() for line in (dataset / "val_fixed.txt").read_text().splitlines() if line.strip()]
        frames = [frame_case(detector, p, str(p)) for p in paths]
        out = ROOT / "tmp" / "ocr-dataset-cpu.json"
        out.write_text(json.dumps({"frames": frames, "crops": []}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{out}: {len(frames)} frames, {sum(len(f['boxes']) for f in frames)} bubbles")
        return
    images = ROOT / "native" / "testdata" / "ocr" / "images"
    frames = [frame_case(detector, p, p.stem) for p in sorted(images.glob("frame_*.png"))]
    crops = []
    for p in sorted(images.glob("crop_*.png")):
        language = p.stem.split("_")[1]
        crop = cv2.imread(str(p), cv2.IMREAD_COLOR)
        crops.append({"image": p.stem, "language": language, "lines": read(language, crop),
                      "auto_lines": read("auto", crop)})
    out = ROOT / "native" / "testdata" / "ocr" / "ocr-cpu.json"
    out.write_text(json.dumps({"frames": frames, "crops": crops}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{out}: {len(frames)} frames ({sum(len(f['boxes']) for f in frames)} bubbles), {len(crops)} crops")


if __name__ == "__main__":
    main()
