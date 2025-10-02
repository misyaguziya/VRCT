import spacy

try:
    from .transliteration_kana_to_hepburn import katakana_to_hepburn
except ImportError:
    from transliteration_kana_to_hepburn import katakana_to_hepburn

class Transliterator:
    def __init__(self):
        self.ja_ginza_nlp = spacy.load('ja_ginza')

    @staticmethod
    def is_kanji(ch: str) -> bool:
        return '\u4e00' <= ch <= '\u9fff'

    @staticmethod
    def kata_to_hira(text: str) -> str:
        if text is None:
            return ""
        # token.morph.get などから list/tuple が来る場合があるので正規化する
        if isinstance(text, (list, tuple)):
            text = text[0] if text else ""
        # 安全のため文字列化
        text = str(text)
        out_chars = []
        for c in text:
            # ord() は長さ1の文字列を期待するので長さ1のときのみ処理する
            if len(c) == 1 and 'ァ' <= c <= 'ン':
                out_chars.append(chr(ord(c) - 0x60))
            else:
                out_chars.append(c)
        return "".join(out_chars)

    @staticmethod
    def split_kanji_okurigana(surface: str, reading_kana: str, use_macron: bool = False):
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
                        "hepburn": katakana_to_hepburn(kana_for_kan, use_macron=use_macron)
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
                        "hepburn": katakana_to_hepburn(kana_for_okuri, use_macron=use_macron)
                    }
                )
                kana_left = kana_left[len(kana_for_okuri):]

        return result

    def analyze(self, text: str, use_macron: bool = False):
        doc = self.ja_ginza_nlp(text)

        results = []
        for sent in doc.sents:
            for token in sent:
                surface = token.text
                # token.morph.get("Reading") は list/tuple/None を返す場合があるため正規化
                reading_raw = token.morph.get("Reading")
                if isinstance(reading_raw, (list, tuple)):
                    reading = reading_raw[0] if reading_raw else None
                else:
                    reading = reading_raw
                # 読みが得られない場合は表層形を fallback にする
                if reading is None:
                    reading = surface
                # 以後の処理のために文字列化しておく
                reading = str(reading)

                # 記号・補助記号は読みを表層形に合わせる
                tag = token.tag_
                if tag and "記号" in tag:
                    reading = surface

                if surface == reading:
                    results.append({
                        "orig": surface,
                        "kana": reading,
                        "hira": surface,
                        "hepburn": surface,
                    })
                    continue

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
                    # 複数文字の場合はユーティリティ関数に任せる（漢字/送り仮名の分割）
                    parts = self.split_kanji_okurigana(surface, reading, use_macron=use_macron)
                    # split_kanji_okurigana はすでに辞書リスト（orig/kana/hira/hepburn）を返すのでそのまま追加
                    results.extend(parts)

        return results

# --- テスト ---
if __name__ == "__main__":
    test_cases = [
        "何",
        "何でしょうか",
        "何が好き？",
        "何色が好き？",
        "何色ありますか？",
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
        " ".join(list("[]<>!@#$%^&*()_+-={}|\;:'\",.<>/?`~")),
        " ".join(list("「」＜＞！＠＃＄％＾＆＊（）＿＋－＝｛｝｜＼；：＇＂，．／？｀～")),
        " ".join(list("♪♫♬♭♮♯°℃℉№Å®©™✓✔✕✖★☆○●◎◇◆□■△▲▽▼※→←↑↓↔︎↕︎⇄⇅∞∴∵∷≪≫≦≧±×÷≠≈≡⊂⊃⊆⊇⊄⊅∪∩∈∋∅∀∃∠⊥⌒∂∇√∫∬∮∑∏∧∨¬⇒⇔∀∃∠⊥⌒∂∇√∫∬∮∑∏")),
        " ".join(list("😀😃😄😁😆😅😂🤣😊😇🙂"))
    ]

    transliterator = Transliterator()
    for case in test_cases:
        print(transliterator.analyze(case))

    # nlp = spacy.load('ja_ginza')
    # for case in test_cases:
    #     doc = nlp(case)
    #     for sent in doc.sents:
    #         for token in sent:
    #             print(
    #                 token.orth_,
    #                 token.lemma_,
    #                 token.norm_,
    #                 token.morph.get("Reading"),
    #                 token.pos_,
    #                 token.morph.get("Inflection"),
    #                 token.tag_,
    #                 token.dep_,
    #                 token.head.i,
    #             )