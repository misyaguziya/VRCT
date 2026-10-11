"""音訳 (Sudachi + かな→ヘボン式) の基準データを、今の Python 版のコードで書き出す。

    python native/reference/export_translit.py   ->  native/testdata/translit/translit.json

Transliterator.analyze をそのまま呼ぶ (use_macron は False / True の両方)。Sudachi の形態素
(表層・読み・品詞) も段階を分けるために記録する。katakana_to_hepburn は乱択したカタカナ列でも比べる。
"""

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src-python" / "models" / "transliteration"))

from transliteration_kana_to_hepburn import katakana_to_hepburn  # noqa: E402
from transliteration_transliterator import Transliterator  # noqa: E402

# Sudachi のプラグイン (数字の結合・カタカナ未知語の結合・長音・読み仮名の括弧・正規化) と文脈ルールを通る文
TEXTS = [
    "向こうへ行く", "行事を行う", "上がる", "上る", "入り込む", "何", "何が好き？", "何色が好き？", "何色ありますか？",
    "何語ですか？", "テーブルに色鉛筆は何色ありますか？", "何と言いましたか", "何の話？", "何で来たの？", "何何？",
    "美しい花を見る", "東京に行く", "漢字とカタカナの混在", "パーティーに行く", "コンピューターを使う",
    "シェアハウスに住む", "ヴァイオリンを弾く", "ギュウニュウを飲む", "ニューヨークに行く", "ラーメンを食べる",
    "チョコレートが好き", "SessionIDを取得する", "取り敢えず検索してみる", "見知らぬ土地で冒険する",
    "彼は優れたエンジニアです", "1,234円です", "３００ｍ先を右へ", "二〇二六年十月十一日", "約1.5倍になった",
    "電話番号は03-1234-5678です", "すごーい〜", "ええ〰ほんとう⁓", "漢字(かんじ)の読み", "東京（とうきょう）",
    "ﾊﾝｶｸｶﾀｶﾅ", "ＡＢＣとabc", "😀😃😄 絵文字", "https://example.com/a?b=c", "改行\nあり", "タブ\tあり",
    "", " ", "　", "ーあいう", "ッカ", "んば", "ウィキペディアとフィルムとティーカップ", "チェックとジェット",
    "ドゥとトゥ", "ヴュー", "キェとギェ", "ツァツィツェツォ", "スィとズィ", "ヮヵヶ", "ゔぁいおりん",
    "ゐゑ", "ヰヱ", "「こんにちは」と言った", "これはペンです。あれは何ですか。", "明日は雨が降るでしょう",
    "お疲れ様でした！また明日〜", "ワールドの移動中です", "マイクがミュートになってるよ",
    " ".join(list("[]<>!@#$%^&*()_+-={}|\\;:'\",.<>/?`~")),
    " ".join(list("「」＜＞！＠＃＄％＾＆＊（）＿＋－＝｛｝｜＼；：＇＂，．／？｀～")),
    " ".join(list("♪♫♬♭♮♯°℃℉№Å®©™✓✔✕✖★☆○●◎◇◆□■△▲▽▼※→←↑↓∞∴∵≪≫≦≧±×÷≠≈≡")),
    "ΣΑΣ ΟΔΟΣ", "Straße İstanbul",
]


def main():
    sentences = [line.split("\t", 1)[1] for line in
                 (Path(__file__).parent / "corpus" / "sentences.tsv").read_text(encoding="utf-8").splitlines()
                 if line.startswith("Japanese\t")]
    t = Transliterator()
    cases = []
    for text in TEXTS + sentences:
        tokens = [[m.surface(), m.reading_form(), list(m.part_of_speech())] for m in t.tokenizer_obj.tokenize(text, t.mode)]
        cases.append({"text": text, "tokens": tokens, "analyze": t.analyze(text, use_macron=False),
                      "analyze_macron": t.analyze(text, use_macron=True)})
    rng = random.Random(20261011)
    pool = [chr(c) for c in range(ord("ァ"), ord("ヶ") + 1)] + ["ー"] * 8 + ["ッ"] * 6 + ["ャ", "ュ", "ョ"] * 4 + list("abn -")
    hepburn = []
    for _ in range(500):
        kata = "".join(rng.choice(pool) for _ in range(rng.randint(1, 10)))
        hepburn.append({"kata": kata, "plain": katakana_to_hepburn(kata, use_macron=False),
                        "macron": katakana_to_hepburn(kata, use_macron=True)})
    out = ROOT / "native" / "testdata" / "translit" / "translit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"cases": cases, "hepburn": hepburn}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{out}: {len(cases)} texts, {len(hepburn)} katakana strings")


if __name__ == "__main__":
    main()
