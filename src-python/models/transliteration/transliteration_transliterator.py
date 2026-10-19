from sudachipy import tokenizer
from sudachipy import dictionary
from typing import List, Dict, Any
import threading
try:
    from .transliteration_kana_to_hepburn import katakana_to_hepburn
except ImportError:
    from transliteration_kana_to_hepburn import katakana_to_hepburn
try:
    from .transliteration_context_rules import apply_context_rules
except ImportError:
    from transliteration_context_rules import apply_context_rules

class Transliterator:
    def __init__(self) -> None:
        self.tokenizer_obj = dictionary.Dictionary(dict_type="full").create()
        self.mode = tokenizer.Tokenizer.SplitMode.C
        # Lock to prevent concurrent access to sudachipy tokenizer which may
        # internally use Rust/PyO3 borrow semantics and raise "Already borrowed".
        self._tokenizer_lock = threading.Lock()

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
    def split_kanji_okurigana(surface: str, reading_kana: str, use_macron: bool = True) -> List[Dict[str, str]]:
        """Split a single surface word and its kana reading into parts.

        Inputs:
        - surface: the surface form (may contain kanji + kana)
        - reading_kana: the katakana reading for the whole surface

        Output:
        - a list of dicts: [{"orig": str, "kana": str, "hira": str, "hepburn": str}, ...]

        Notes:
        - The function allocates portions of ``reading_kana`` to each contiguous
          kanji/non-kanji block in ``surface``. Allocation is heuristic: an
          initial allocation based on block length is used and any remainder is
          distributed left-to-right preferring kanji blocks.
        - This function is pure (no external side effects) and returns the
          constructed list.
        """

        result: List[Dict[str, str]] = []

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
        # We'll allocate kana to each block by initial guess = len(part) (characters)
        # and distribute any remaining kana left-to-right preferring kanji blocks.
        kana_len = len(kana_left)

        # initial allocation per block
        allocs = [len(part) for _, part in blocks]
        allocated = sum(allocs)
        remaining = kana_len - allocated

        # distribute extra kana to kanji blocks first (left-to-right)
        if remaining > 0:
            for idx, (is_kan, _) in enumerate(blocks):
                if remaining <= 0:
                    break
                if is_kan:
                    allocs[idx] += 1
                    remaining -= 1
            # if still remaining, distribute to all blocks left-to-right
            idx = 0
            while remaining > 0 and len(blocks) > 0:
                allocs[idx] += 1
                remaining -= 1
                idx = (idx + 1) % len(blocks)

        # if remaining < 0 (reading shorter than base), shrink allocations from right
        if remaining < 0:
            # remove from rightmost blocks as needed
            need = -remaining
            idx = len(blocks) - 1
            while need > 0 and idx >= 0:
                take = min(allocs[idx] - 1, need) if allocs[idx] > 1 else 0
                allocs[idx] -= take
                need -= take
                idx -= 1

        # now slice kana_left according to allocs
        pos = 0
        for (is_kan, part), cnt in zip(blocks, allocs):
            kana_for_part = kana_left[pos:pos+cnt]
            pos += cnt
            result.append({
                "orig": part,
                "kana": kana_for_part,
                "hira": Transliterator.kata_to_hira(kana_for_part),
                "hepburn": katakana_to_hepburn(kana_for_part, use_macron=use_macron)
            })

        return result

    def analyze(self, text: str, use_macron: bool = False) -> List[Dict[str, Any]]:
        """Tokenize ``text`` and produce per-subunit reading information.

        Returns a list of dicts for each token/sub-part with keys:
        - orig: original surface string (one or more characters)
        - kana: katakana reading for this part (may be adapted by context rules)
        - hira: hiragana reading (derived from kana)
        - hepburn: Latin transcription (derived from kana)

        Side-effects / notes:
        - The function calls ``apply_context_rules(results, use_macron=...)``
          which both mutates ``results`` in-place and returns it. This method
          safely accepts the returned list and then recalculates ``hira`` and
          ``hepburn`` for entries whose ``kana`` was changed.
        - If rule application fails, analysis still returns the best-effort
          results.
        """

        # Tokenizer may raise RuntimeError: Already borrowed when called
        # concurrently. Protect the call with a lock to serialize access.
        with self._tokenizer_lock:
            tokens = self.tokenizer_obj.tokenize(text, self.mode)

        results: List[Dict[str, Any]] = []
        for t in tokens:
            surface = t.surface()
            reading = t.reading_form()
            pos = t.part_of_speech()

            if pos and pos[0] in ["記号", "補助記号", "空白"]:
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
                # 複数文字の場合は既存のユーティリティで分割
                parts = self.split_kanji_okurigana(surface, reading, use_macron=use_macron)
                results.extend(parts)

        # 文脈ルールを適用（別ファイル）
        try:
            results = apply_context_rules(results, use_macron=use_macron) or results
        except Exception:
            # ルール適用で失敗しても解析結果は返す
            pass

        # apply_context_rules が kana を書き換えた場合、hira と hepburn を再計算
        for entry in results:
            kana = entry.get("kana", "")
            if kana:
                entry["hira"] = self.kata_to_hira(kana)
                entry["hepburn"] = katakana_to_hepburn(kana, use_macron=use_macron)

        return results

# --- テスト ---
if __name__ == "__main__":
    import pprint
    test_cases = [
        "向こうへ行く",
        "行事を行う",
        "上がる",
        "上る",
        "入り込む",
        "何",
        "何が好き？",
        "何色が好き？",
        "何色ありますか？",
        "何語ですか？",
        "テーブルに色鉛筆は何色ありますか？"
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
        " ".join(list("[]<>!@#$%^&*()_+-={}|\\;:'\",.<>/?`~")),
        " ".join(list("「」＜＞！＠＃＄％＾＆＊（）＿＋－＝｛｝｜＼；：＇＂，．／？｀～")),
        " ".join(list("♪♫♬♭♮♯°℃℉№Å®©™✓✔✕✖★☆○●◎◇◆□■△▲▽▼※→←↑↓↔︎↕︎⇄⇅∞∴∵∷≪≫≦≧±×÷≠≈≡⊂⊃⊆⊇⊄⊅∪∩∈∋∅∀∃∠⊥⌒∂∇√∫∬∮∑∏∧∨¬⇒⇔∀∃∠⊥⌒∂∇√∫∬∮∑∏")),
        " ".join(list("😀😃😄😁😆😅😂🤣😊😇🙂"))
    ]

    transliterator = Transliterator()
    for case in test_cases:
        pprint.pprint(transliterator.analyze(case), sort_dicts=False)