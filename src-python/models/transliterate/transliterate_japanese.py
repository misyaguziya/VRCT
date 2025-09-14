from sudachipy import tokenizer
from sudachipy import dictionary
try:
    from .transliterate_kana_to_hepburn import katakana_to_hepburn
except ImportError:
    from transliterate_kana_to_hepburn import katakana_to_hepburn

class Transliterator:
    def __init__(self):
        self.tokenizer_obj = dictionary.Dictionary().create()
        self.mode = tokenizer.Tokenizer.SplitMode.A

    @staticmethod
    def is_kanji(ch: str) -> bool:
        return '\u4e00' <= ch <= '\u9fff'

    @staticmethod
    def kata_to_hira(text: str) -> str:
        return "".join(
            chr(ord(c) - 0x60) if 'ァ' <= c <= 'ン' else c
            for c in text
        )

    @staticmethod
    def split_kanji_okurigana(surface: str, reading_kana: str):
        """
        1語の表層形(surface)と読み(reading_kana)を
        [ {"orig":..., "kana":..., "hira":..., "hepburn":...}, ... ] に分割
        """
        result = []

        # 表層を「漢字ブロック」と「非漢字ブロック」に分割
        buf = ""
        prev_is_kanji = None
        blocks = []
        for ch in surface:
            now_is_kanji = Transliterator.is_kanji(ch)
            if prev_is_kanji is None or now_is_kanji == prev_is_kanji:
                buf += ch
            else:
                blocks.append((prev_is_kanji, buf))
                buf = ch
            prev_is_kanji = now_is_kanji
        if buf:
            blocks.append((prev_is_kanji, buf))

        # 読みを分配
        kana_left = reading_kana
        for is_kan, part in blocks:
            if is_kan:
                # 仮ルール：残りの読みのうち、送り仮名分を除いた前半を充てる
                # ex. "美しい"(うつくしい): 漢字=美, 残り送り仮名=しい
                okuri_len = len(blocks[-1][1]) if not blocks[-1][0] else 0
                kana_for_kan = kana_left[:-okuri_len] if okuri_len else kana_left
                result.append(
                    {
                        "orig": part,
                        "kana": kana_for_kan,
                    }
                )
                kana_left = kana_left[len(kana_for_kan):]
            else:
                # 送り仮名部分 → そのまま残りを割り当てる
                kana_for_okuri = kana_left
                result.append(
                    {
                        "orig": part,
                        "kana": kana_for_okuri,
                    }
                )
                kana_left = ""

        return result

    def analyze(self, text: str, use_macron: bool = True):
        tokens = self.tokenizer_obj.tokenize(text, self.mode)

        results = []
        for t in tokens:
            surface = t.surface()
            parts = self.split_kanji_okurigana(surface, t.reading_form())
            for p in parts:
                results.append({
                    "orig": p["orig"],
                    "kana": p["kana"],
                    "hira": self.kata_to_hira(p["kana"]),
                    "hepburn": katakana_to_hepburn(p["kana"], use_macron=use_macron)
                })
        return results

# --- テスト ---
if __name__ == "__main__":
    test_cases = [
        "美しい花を見る",
        "東京に行く",
        "漢字とカタカナの混在",
        "パーティーに行く",
        "コンピューターを使う",
        "シェアハウスに住む",
        "ヴァイオリンを弾く",
        "ギュウニュウを飲む",
        "ニューヨークに行く",
        "ラーメンを食べる",
        "チョコレートが好き",
        "SessionIDを取得する",
    ]

    transliterator = Transliterator()
    for case in test_cases:
        print(transliterator.analyze(case))