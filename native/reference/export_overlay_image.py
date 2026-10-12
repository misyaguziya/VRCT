"""オーバーレイの文字の画像 (overlay_image.OverlayImage) を、今の Python 版で記録する。

    python native/reference/export_overlay_image.py   ->  native/testdata/overlay/images.json
                                                          tmp/overlay-images/python/*.png (見比べ用、リポジトリに置かない)

Rust 版とは画像の大きさ (文字幅による折り返しと行数で決まる) を比べる。画素は比べない
(文字の描画は「機能が動けば十分」、設計書 §6.7)。
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src-python"))

RUBY = [{"orig": "慮", "hira": "おもんぱか", "hepburn": "omonpaka"}, {"orig": "る", "hira": "る", "hepburn": "ru"}]
LONG_JA = "これは非常に長いテキストです。表示幅を超えると折り返しが発生します。" * 2
LONG_TOKENS = [{"orig": p, "hira": p, "hepburn": "aaaaa"} for p in
               ["これは", "非常に", "長い", "テキスト", "です", "表示幅", "を", "超える", "と", "折り返し", "が", "発生", "します"] * 2]

SMALL = [
    ("hello", "Hello, World!", "English", [], [], [], []),
    ("translated", "Hello, World!", "English", ["こんにちは、世界！"], ["Japanese"], [], [[]]),
    ("three", "Hi", "English", ["こんにちは", "안녕하세요", "你好"], ["Japanese", "Korean", "Chinese Simplified"], [], [[], [], []]),
    ("ruby", "慮る", "Japanese", ["慮る", "慮る"], ["Japanese", "Japanese"], RUBY, [RUBY, RUBY]),
    ("ruby_message", "慮る", "Japanese", [], [], RUBY, [[]]),
    ("long", LONG_JA, "Japanese", [], [], [], []),
    ("long_ruby", LONG_JA, "Japanese", [], [], LONG_TOKENS, [[]]),
    ("long_en", "The quick brown fox jumps over the lazy dog. " * 6, "English", [], [], [], []),
    ("empty_translation", "", "English", ["訳"], ["Japanese"], [], [[]]),
]
LARGE = [
    ("send", "send", "Hello, World!", "English", ["こんにちは、世界！"], ["Japanese"], [], [[]]),
    ("receive_ruby", "receive", "こんにちは、世界！", "Japanese", ["Hello, World!"], ["English"], RUBY, [RUBY]),
    ("send_long", "send", LONG_JA, "Japanese", [], [], LONG_TOKENS, [[]]),
    ("receive_three", "receive", "慮る", "Japanese", ["Hello"] * 3, ["English"] * 3, RUBY, [RUBY, [], RUBY]),
    ("send_korean", "send", "안녕하세요 반갑습니다", "Korean", ["はじめまして"], ["Japanese"], [], [[]]),
    ("receive_six", "receive", "6つ目で最初の行が消える", "Japanese", ["sixth"], ["English"], [], [[]]),
]


def main():
    from models.overlay.overlay_image import OverlayImage
    out_png = ROOT / "tmp" / "overlay-images" / "python"
    out_png.mkdir(parents=True, exist_ok=True)
    cases = {"small": [], "large": []}
    overlay = OverlayImage()
    for name, message, lang, translation, targets, tl_message, tl_translation in SMALL:
        img = overlay.createOverlayImageSmallLog(message, lang, translation, targets, tl_message, tl_translation)
        img.save(out_png / f"small_{name}.png")
        cases["small"].append({"name": name, "message": message, "language": lang, "translation": translation,
                               "target_language": targets, "transliteration_message": tl_message,
                               "transliteration_translation": tl_translation, "size": list(img.size)})
    # the large log keeps the last 5 messages: one OverlayImage for the sequence
    overlay = OverlayImage()
    for name, kind, message, lang, translation, targets, tl_message, tl_translation in LARGE:
        img = overlay.createOverlayImageLargeLog(kind, message, lang, translation, targets, tl_message, tl_translation)
        img.save(out_png / f"large_{name}.png")
        cases["large"].append({"name": name, "message_type": kind, "message": message, "language": lang,
                               "translation": translation, "target_language": targets,
                               "transliteration_message": tl_message, "transliteration_translation": tl_translation,
                               "size": list(img.size)})
    out = ROOT / "native" / "testdata" / "overlay" / "images.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cases, ensure_ascii=False, indent=1), encoding="utf-8")
    print(out, [(c["name"], c["size"]) for c in cases["small"] + cases["large"]])


if __name__ == "__main__":
    main()
