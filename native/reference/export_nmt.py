"""CTranslate2 翻訳 (NLLB / M2M100) の基準データを、今の Python 版のコードで書き出す。

    python native/reference/export_nmt.py <weights の親> <weight_type> [cpu|cuda] [compute_type]
      -> native/testdata/nmt/<weight_type>-<device>.json

Translator.changeCTranslate2Model / translateCTranslate2 をそのまま呼ぶ。トークナイザーの照合
(分割・ID 化・復号) は、同じ tokenizer オブジェクトで translateCTranslate2 と同じ式を使う。
compute_type を省くと Python 版の "auto" と同じく getBestComputeType で選ぶ。
"""

import json
import os
import random
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src-python"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(SRC / "models" / "translation"))

from translation_languages import loadTranslationLanguages, translation_lang  # noqa: E402
from translation_translator import Translator  # noqa: E402
from utils import getBestComputeType  # noqa: E402

# 分割・空白の掃除・特殊トークンの扱いを試す文
EDGE_CASES = [
    "", " ", "   ", "  leading and trailing  ", "multiple   spaces   inside", "line\nbreak", "tab\there",
    "emoji 😀🎉 test", "https://example.com/a?b=c&d=e", "</s> inside", "<s>start", "<unk><pad>", "<mask>",
    " <mask> x", "__ja__ token", "__en__", "jpn_Jpan code", "zero​width", "é combining",
    "full-width ！？ punctuation", "\x1c separator \x1f", "123,456.78", "C'est l'été", "don't won't can't",
    "...", "!!!", "? ! , .", "a . b ? c ! d , e", "♪♪♪", "Ｈｅｌｌｏ　Ｗｏｒｌｄ", "㍻ ㌔ ㈱", "ﬁ ligature",
    "　全角スペース　", "I 'm here", "it 's", "they 've", "we 're", "isn 't", " ' ", "x y",
    "‮rtl override", "ǅ titlecase", "ß straße", "İstanbul", "日本語とEnglishのmix", "ｱｲｳｴｵ",
]


def load_sentences():
    rows = []
    for line in (Path(__file__).parent / "corpus" / "sentences.tsv").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            language, text = line.split("\t", 1)
            rows.append((language, text))
    return rows


def main():
    weights_root, weight_type = sys.argv[1], sys.argv[2]
    device = sys.argv[3] if len(sys.argv) > 3 else "cpu"
    compute_type = sys.argv[4] if len(sys.argv) > 4 else getBestComputeType(device, 0)
    loadTranslationLanguages(str(SRC))
    table = translation_lang["CTranslate2"][weight_type]
    translator = Translator()
    translator.changeCTranslate2Model(weights_root, weight_type, device=device, compute_type=compute_type)
    tokenizer = translator.ctranslate2_tokenizer

    def source_tokens(text, source_language):
        # translateCTranslate2 の前半と同じ式
        tokenizer.src_lang = source_language
        return tokenizer.convert_ids_to_tokens(tokenizer.encode(text))

    def decode(tokens):
        # translateCTranslate2 の後半と同じ式
        return tokenizer.decode(tokenizer.convert_tokens_to_ids(tokens))

    sentences = [(lang, text) for lang, text in load_sentences() if lang in table["source"]]
    skipped = sorted({lang for lang, _ in load_sentences() if lang not in table["source"]})
    codes = sorted(set(table["source"].values()))

    tokenize_cases = []
    for lang, text in sentences:
        tokenize_cases.append({"text": text, "source_language": table["source"][lang]})
    for text in EDGE_CASES:
        for code in codes[:3] + [table["source"]["English"], table["source"]["Japanese"]]:
            tokenize_cases.append({"text": text, "source_language": code})
    # 全コードで 1 文ずつ (言語トークンの ID)
    for i, code in enumerate(codes):
        tokenize_cases.append({"text": sentences[i % len(sentences)][1], "source_language": code})
    for case in tokenize_cases:
        try:
            case["tokens"] = source_tokens(case["text"], case["source_language"])
        except Exception as e:
            # translateCTranslate2 はこれを拾って False を返す (M2M100 の表にある "as" など)
            case["error"] = type(e).__name__

    translate_cases = []
    targets = ["English", "Japanese", "Korean", "Chinese Simplified"]
    for i, (lang, text) in enumerate(sentences):
        for target in [t for t in targets if t != lang][: 2]:
            if target == "Korean" and i % 2:
                target = "French"
            source_code, target_code = table["source"][lang], table["target"][target]
            # translateCTranslate2 の中身を分けて記録 (照合の段階を分けるため)
            src = source_tokens(text, source_code)
            prefix = [tokenizer.lang_code_to_token[target_code]] if weight_type.startswith("m2m100") else [target_code]
            hypothesis = translator.ctranslate2_translator.translate_batch([src], target_prefix=[prefix])[0].hypotheses[0]
            result = translator.translateCTranslate2(text, source_code, target_code, weight_type)
            assert result == decode(hypothesis[1:]), (text, result)
            translate_cases.append({"text": text, "source_language": source_code, "target_language": target_code,
                                    "source_tokens": src, "target_prefix": prefix, "hypothesis": hypothesis,
                                    "result": result})

    # 復号: 訳の出力に加え、語彙からの乱択 (特殊トークン・言語トークン・掃除の対象になる記号を多めに)
    vocab = [t for t, _ in sorted(tokenizer.get_vocab().items(), key=lambda kv: kv[1])]
    specials = list(tokenizer.all_special_tokens)
    punct = [t for t in vocab if t.strip("▁") in {".", "?", "!", ",", "'", "n't", "'m", "'s", "'ve", "'re", "t", "s", "m"}]
    rng = random.Random(20261011)
    decode_cases = []
    for _ in range(400):
        tokens = []
        for _ in range(rng.randint(1, 24)):
            r = rng.random()
            pool = specials if r < 0.1 else punct if r < 0.35 else vocab
            tokens.append(rng.choice(pool))
        if rng.random() < 0.1:
            tokens.append("not-in-vocab")
        decode_cases.append({"tokens": tokens, "text": decode(tokens)})
    for case in translate_cases:
        decode_cases.append({"tokens": case["hypothesis"][1:], "text": case["result"]})

    out = ROOT / "native" / "testdata" / "nmt" / f"{weight_type}-{device}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    report = {"weight_type": weight_type, "device": device, "compute_type": compute_type,
              "skipped_languages": skipped, "tokenize": tokenize_cases, "translate": translate_cases,
              "decode": decode_cases}
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{out}: tokenize {len(tokenize_cases)}, translate {len(translate_cases)}, decode {len(decode_cases)}, "
          f"skipped {skipped}")


if __name__ == "__main__":
    main()
