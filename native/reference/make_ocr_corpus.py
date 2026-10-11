"""OCR の照合用の合成画像を作る (実際のスクリーンショットは他の人の発言が写るのでリポジトリに置かない)。

    python native/reference/make_ocr_corpus.py   ->  native/testdata/ocr/images/*.png

crop_<言語>_<n>.png  … 吹き出しの切り出しに見立てた画像 (VRCT の OCR 言語ごと、文は corpus/sentences.tsv)
frame_<n>.png        … 画面全体に見立てた画像 (1280x720 / 1920x1080 / 2560x1440 に吹き出しを置く)
フォントは Windows のもの。描画は PC によって違いうるので、作り直したら export_ocr.py で基準も作り直す。
"""

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "native" / "testdata" / "ocr" / "images"
FONTS = "C:/Windows/Fonts/"
# OCR の言語設定 -> (文の言語, フォント)
LANGUAGES = {
    "auto": [("Japanese", "YuGothM.ttc"), ("English", "arial.ttf"), ("Chinese Simplified", "msyh.ttc"),
             ("French", "arial.ttf"), ("German", "arial.ttf"), ("Spanish", "arial.ttf"), ("Vietnamese", "arial.ttf")],
    "Korean": [("Korean", "malgun.ttf")],
    "Russian": [("Russian", "arial.ttf"), ("Ukrainian", "arial.ttf")],
    "Thai": [("Thai", "LeelawUI.ttf")],
    "Arabic": [("Arabic", "arial.ttf")],
    "Hindi": [("Hindi", "Nirmala.ttc")],
}
STYLES = [((40, 40, 40), (255, 255, 255)), ((250, 250, 250), (20, 20, 20)), ((30, 60, 110), (240, 240, 240))]


def sentences():
    rows = {}
    for line in (Path(__file__).parent / "corpus" / "sentences.tsv").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            language, text = line.split("\t", 1)
            rows.setdefault(language, []).append(text)
    return rows


def bubble(text, font_file, size, style, rng):
    font = ImageFont.truetype(FONTS + font_file, size)
    # 長い文は2行に折る (吹き出しの折り返しに見立てる)
    lines = [text]
    if len(text) > 18 and rng.random() < 0.6:
        cut = len(text) // 2
        lines = [text[:cut], text[cut:]]
    widths = [font.getbbox(line)[2] for line in lines]
    pad_x, pad_y = rng.randint(8, 24), rng.randint(6, 16)
    line_h = int(size * 1.35)
    image = Image.new("RGB", (max(widths) + 2 * pad_x, line_h * len(lines) + 2 * pad_y), style[0])
    draw = ImageDraw.Draw(image)
    for i, line in enumerate(lines):
        draw.text((pad_x, pad_y + i * line_h), line, font=font, fill=style[1])
    return image


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(20261011)
    rows = sentences()
    crops = []
    for setting, sources in LANGUAGES.items():
        n = 0
        for language, font in sources:
            for text in rows[language][:6 if setting == "auto" else 5]:
                image = bubble(text, font, rng.choice([18, 22, 28, 36]), rng.choice(STYLES), rng)
                image.save(OUT / f"crop_{setting}_{n:02d}.png")
                crops.append(image)
                n += 1
    for i, (w, h) in enumerate([(1280, 720), (1920, 1080), (2560, 1440)]):
        frame = Image.new("RGB", (w, h))
        draw = ImageDraw.Draw(frame)
        for y in range(h):  # 縦のグラデーション (圧縮が効くように雑音は入れない)
            draw.line([(0, y), (w, y)], fill=(40 + 60 * y // h, 70, 90 + 40 * y // h))
        for _ in range(4):
            x0, y0 = rng.randint(0, w - 200), rng.randint(0, h - 200)
            draw.rectangle([x0, y0, rng.randint(x0, w), rng.randint(y0, h)],
                           fill=(rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)))
        for crop in rng.sample(crops, 5):
            scale = rng.choice([1.0, 1.5, 2.0]) * w / 1920
            crop = crop.resize((max(1, int(crop.width * scale)), max(1, int(crop.height * scale))))
            frame.paste(crop, (rng.randint(0, max(0, w - crop.width)), rng.randint(0, max(0, h - crop.height))))
        frame.save(OUT / f"frame_{i}.png")
    print(f"{len(crops)} crops, 3 frames in {OUT}")


if __name__ == "__main__":
    main()
