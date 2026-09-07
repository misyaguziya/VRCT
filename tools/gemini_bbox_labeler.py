"""Gemini APIでVRChatチャット吹き出しのbbox座標を自動アノテーションする
開発用ツール(YOLO学習データセット作成用、VRCTには同梱しない)。

`tools/ocr_dataset_collector.py` で集めた positive/ 配下の画像
(吹き出しが写っていることは目視確認済み)に対してGeminiへ「吹き出しの
bboxを返して」と問い合わせ、YOLO形式のラベルファイル(class x_center
y_center width height、すべて0-1正規化)を書き出す。あわせて確認用に
bboxを描画した画像も保存するので、Geminiの誤り(吹き出し以外を検出した/
検出できなかった)を目視でざっと確認できる。

使い方:
    export GEMINI_API_KEY=xxxxx  (Windows: set GEMINI_API_KEY=xxxxx)
    python tools/gemini_bbox_labeler.py <positive画像が入ったディレクトリ> [--out DIR]

    例:
    python tools/gemini_bbox_labeler.py dataset_collected/factory_world_desktop/positive

出力構成 (--out省略時は <入力ディレクトリ>/../yolo_labels/):
    yolo_labels/images/<元のファイル名>.png   (画像本体のコピー)
    yolo_labels/labels/<元のファイル名>.txt   (YOLO形式、1行 "0 cx cy w h")
    yolo_labels/preview/<元のファイル名>.png  (bbox描画済み、目視確認用)
    yolo_labels/failed.txt                    (Geminiが検出できなかった/
                                                 パース失敗した画像の一覧)

Gemini APIキーは VRCT の config.json とは無関係に、この開発用ツール専用
として環境変数 GEMINI_API_KEY (または --api-key) で渡す。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from typing import Optional

_SRC_PYTHON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src-python")
sys.path.insert(0, _SRC_PYTHON)

import cv2  # noqa: E402
from google import genai  # noqa: E402
from google.genai import types  # noqa: E402

_MODEL = "gemini-2.0-flash"

_PROMPT = """This is a screenshot from the VRChat video game. Find the VRChat chat
bubble (a floating speech-bubble UI element showing text that another
player typed, rendered by VRChat itself above a player's avatar).

The chat bubble has a flat, semi-transparent dark rounded-rectangle
background with white text, usually appearing above an avatar's head.
Do NOT select: nameplates, in-world signs, posters, or any UI panel
that is part of the 3D world/game content rather than VRChat's own
chat UI.

If you find it, respond with ONLY a JSON array like this, with pixel
coordinates normalized to a 0-1000 scale (Gemini's standard convention):
[{"box_2d": [ymin, xmin, ymax, xmax], "label": "chat_bubble"}]

If there is no such VRChat chat bubble in the image, respond with
exactly: []
"""

_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)


def _extract_json_array(text: str) -> Optional[list]:
    text = text.strip()
    # Gemini sometimes wraps the JSON in ```json ... ``` fences.
    if text.startswith("```"):
        text = text.strip("`")
        text = text[4:] if text.lower().startswith("json") else text
    match = _JSON_ARRAY_RE.search(text)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _detect_bubble_box(client: "genai.Client", image_path: str) -> Optional[tuple]:
    """Returns (ymin, xmin, ymax, xmax) in 0-1000 scale, or None."""
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    response = client.models.generate_content(
        model=_MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
            _PROMPT,
        ],
    )
    text = response.text or ""
    parsed = _extract_json_array(text)
    if not parsed:
        return None
    entry = parsed[0]
    box = entry.get("box_2d")
    if not box or len(box) != 4:
        return None
    return tuple(box)  # (ymin, xmin, ymax, xmax), 0-1000 scale


def _to_yolo_line(box_0_1000: tuple, img_w: int, img_h: int, class_id: int = 0) -> str:
    ymin, xmin, ymax, xmax = box_0_1000
    xmin_px, xmax_px = xmin / 1000.0 * img_w, xmax / 1000.0 * img_w
    ymin_px, ymax_px = ymin / 1000.0 * img_h, ymax / 1000.0 * img_h
    cx = (xmin_px + xmax_px) / 2.0 / img_w
    cy = (ymin_px + ymax_px) / 2.0 / img_h
    w = (xmax_px - xmin_px) / img_w
    h = (ymax_px - ymin_px) / img_h
    return f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


def _draw_preview(image_path: str, box_0_1000: tuple, out_path: str) -> None:
    frame = cv2.imread(image_path)
    if frame is None:
        return
    h, w = frame.shape[:2]
    ymin, xmin, ymax, xmax = box_0_1000
    x0, y0 = int(xmin / 1000.0 * w), int(ymin / 1000.0 * h)
    x1, y1 = int(xmax / 1000.0 * w), int(ymax / 1000.0 * h)
    cv2.rectangle(frame, (x0, y0), (x1, y1), (0, 255, 0), 2)
    cv2.imwrite(out_path, frame)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", help="positive/ 画像が入ったディレクトリ (複数セッション分をまとめて渡してもよい)")
    parser.add_argument("--out", default=None)
    parser.add_argument("--api-key", default=None)
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] Gemini APIキーが指定されていません。--api-key か環境変数 GEMINI_API_KEY を設定してください。")
        sys.exit(1)

    out_root = args.out or os.path.join(os.path.dirname(os.path.abspath(args.input_dir)), "yolo_labels")
    images_out = os.path.join(out_root, "images")
    labels_out = os.path.join(out_root, "labels")
    preview_out = os.path.join(out_root, "preview")
    for d in (images_out, labels_out, preview_out):
        os.makedirs(d, exist_ok=True)

    client = genai.Client(api_key=api_key)

    files = sorted(
        f for f in os.listdir(args.input_dir)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    )
    print(f"found {len(files)} images in {args.input_dir}")

    failed: list[str] = []
    ok_count = 0

    for i, fname in enumerate(files):
        src_path = os.path.join(args.input_dir, fname)
        stem = os.path.splitext(fname)[0]
        try:
            box = _detect_bubble_box(client, src_path)
        except Exception as e:  # noqa: BLE001
            print(f"[{i+1}/{len(files)}] {fname}: API error: {e}")
            failed.append(f"{fname}\tapi_error: {e}")
            time.sleep(1.0)
            continue

        if box is None:
            print(f"[{i+1}/{len(files)}] {fname}: no bubble detected / unparsable response")
            failed.append(f"{fname}\tno_detection")
            continue

        frame = cv2.imread(src_path)
        if frame is None:
            failed.append(f"{fname}\tunreadable_image")
            continue
        h, w = frame.shape[:2]

        with open(os.path.join(labels_out, f"{stem}.txt"), "w", encoding="utf-8") as lf:
            lf.write(_to_yolo_line(box, w, h) + "\n")
        shutil.copy2(src_path, os.path.join(images_out, fname))
        _draw_preview(src_path, box, os.path.join(preview_out, fname))
        ok_count += 1
        print(f"[{i+1}/{len(files)}] {fname}: OK box_2d(0-1000)={box}")

        # Free-tier rate limiting headroom; adjust if you have a paid quota.
        time.sleep(0.5)

    if failed:
        with open(os.path.join(out_root, "failed.txt"), "w", encoding="utf-8") as ff:
            ff.write("\n".join(failed) + "\n")

    print()
    print(f"done. labeled={ok_count}/{len(files)}  failed={len(failed)}")
    print(f"labels: {labels_out}")
    print(f"preview (目視確認用、bbox描画済み): {preview_out}")
    if failed:
        print(f"failed list: {os.path.join(out_root, 'failed.txt')}")


if __name__ == "__main__":
    main()
