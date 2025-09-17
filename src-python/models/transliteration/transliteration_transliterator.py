from sudachipy import tokenizer
from sudachipy import dictionary
try:
    from .transliteration_kana_to_hepburn import katakana_to_hepburn
except ImportError:
    from transliteration_kana_to_hepburn import katakana_to_hepburn

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
        for i, (is_kan, part) in enumerate(blocks):
            if is_kan:
                # 漢字ブロックの処理
                if len(blocks) == 1:
                    # 単一ブロック（全て漢字）の場合
                    kana_for_kan = kana_left
                elif i == len(blocks) - 1:
                    # 最後のブロック（漢字）の場合
                    kana_for_kan = kana_left
                else:
                    # 中間の漢字ブロックの場合
                    # 後続の非漢字ブロックの文字数を計算
                    remaining_non_kanji = sum(len(p) for is_k, p in blocks[i+1:] if not is_k)
                    if remaining_non_kanji > 0 and len(kana_left) > remaining_non_kanji:
                        kana_for_kan = kana_left[:-remaining_non_kanji]
                    else:
                        # 漢字1文字あたり最低1文字の読みを割り当て
                        min_kana = len(part)
                        kana_for_kan = kana_left[:max(min_kana, len(kana_left) - remaining_non_kanji)]
                
                # 空の読みを避ける
                if not kana_for_kan and kana_left:
                    kana_for_kan = kana_left[:1]
                
                result.append(
                    {
                        "orig": part,
                        "kana": kana_for_kan,
                        "hira": Transliterator.kata_to_hira(kana_for_kan),
                        "hepburn": katakana_to_hepburn(kana_for_kan, use_macron=True)
                    }
                )
                kana_left = kana_left[len(kana_for_kan):]
            else:
                # 非漢字部分（送り仮名など）
                kana_for_okuri = kana_left[:len(part)]
                result.append(
                    {
                        "orig": part,
                        "kana": kana_for_okuri,
                        "hira": Transliterator.kata_to_hira(kana_for_okuri),
                        "hepburn": katakana_to_hepburn(kana_for_okuri, use_macron=True)
                    }
                )
                kana_left = kana_left[len(kana_for_okuri):]

        return result

    def analyze(self, text: str, use_macron: bool = True):
        tokens = self.tokenizer_obj.tokenize(text, self.mode)

        results = []
        for t in tokens:
            surface = t.surface()
            reading = t.reading_form()
            
            # 単純に1文字ずつ処理
            if len(surface) == 1:
                # 1文字の場合はそのまま
                results.append({
                    "orig": surface,
                    "kana": reading,
                    "hira": self.kata_to_hira(reading),
                    "hepburn": katakana_to_hepburn(reading, use_macron=use_macron)
                })
            else:
                # 複数文字の場合は文字種別で分割
                i = 0
                reading_pos = 0
                
                while i < len(surface):
                    char = surface[i]
                    
                    if self.is_kanji(char):
                        # 漢字の場合、連続する漢字をまとめて処理
                        kanji_block = ""
                        while i < len(surface) and self.is_kanji(surface[i]):
                            kanji_block += surface[i]
                            i += 1
                        
                        # 漢字ブロックの読みを推定
                        if i < len(surface):
                            # 後に文字がある場合、送り仮名を考慮
                            remaining_chars = len(surface) - i
                            kanji_reading = reading[reading_pos:-remaining_chars] if remaining_chars > 0 else reading[reading_pos:]
                        else:
                            # 最後の漢字ブロックの場合
                            kanji_reading = reading[reading_pos:]
                        
                        results.append({
                            "orig": kanji_block,
                            "kana": kanji_reading,
                            "hira": self.kata_to_hira(kanji_reading),
                            "hepburn": katakana_to_hepburn(kanji_reading, use_macron=use_macron)
                        })
                        reading_pos += len(kanji_reading)
                    else:
                        # 非漢字の場合
                        non_kanji_block = ""
                        while i < len(surface) and not self.is_kanji(surface[i]):
                            non_kanji_block += surface[i]
                            i += 1
                        
                        # 非漢字部分の読み（通常は文字数分）
                        non_kanji_reading = reading[reading_pos:reading_pos + len(non_kanji_block)]
                        
                        results.append({
                            "orig": non_kanji_block,
                            "kana": non_kanji_reading,
                            "hira": self.kata_to_hira(non_kanji_reading),
                            "hepburn": katakana_to_hepburn(non_kanji_reading, use_macron=use_macron)
                        })
                        reading_pos += len(non_kanji_reading)
        
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
        "取り敢えず検索してみる",
        "見知らぬ土地で冒険する",
        "彼は優れたエンジニアです",
    ]

    transliterator = Transliterator()
    for case in test_cases:
        print(transliterator.analyze(case))