"""Tests for models.ocr.ocr_languages.

VRCT言語名 <-> EasyOCR言語コードの変換テーブルは純粋な辞書引きなので、
実際のEasyOCR/画像処理系の依存が無くても直接検証できる。
"""

import unittest

from models.ocr.ocr_languages import resolveEasyocrLangs, vrctToEasyocr


class TestVrctToEasyocr(unittest.TestCase):
    def test_known_language_maps_to_its_code(self) -> None:
        self.assertEqual(vrctToEasyocr("Japanese"), "ja")
        self.assertEqual(vrctToEasyocr("Korean"), "ko")
        self.assertEqual(vrctToEasyocr("Chinese Simplified"), "ch_sim")

    def test_unknown_language_falls_back_to_english(self) -> None:
        self.assertEqual(vrctToEasyocr("Klingon"), "en")
        self.assertEqual(vrctToEasyocr(""), "en")


class TestResolveEasyocrLangs(unittest.TestCase):
    def test_auto_returns_default_ja_en_set(self) -> None:
        self.assertEqual(resolveEasyocrLangs("auto"), ["ja", "en"])

    def test_auto_is_case_insensitive(self) -> None:
        self.assertEqual(resolveEasyocrLangs("Auto"), ["ja", "en"])
        self.assertEqual(resolveEasyocrLangs("AUTO"), ["ja", "en"])

    def test_non_string_falls_back_to_default(self) -> None:
        self.assertEqual(resolveEasyocrLangs(None), ["ja", "en"])  # type: ignore[arg-type]

    def test_known_non_english_language_adds_english_fallback(self) -> None:
        self.assertEqual(resolveEasyocrLangs("Japanese"), ["ja", "en"])
        self.assertEqual(resolveEasyocrLangs("Korean"), ["ko", "en"])

    def test_english_does_not_duplicate_itself(self) -> None:
        self.assertEqual(resolveEasyocrLangs("English"), ["en"])

    def test_unknown_language_falls_back_to_default_set(self) -> None:
        self.assertEqual(resolveEasyocrLangs("Klingon"), ["ja", "en"])

    def test_returned_list_is_a_fresh_copy_each_time(self) -> None:
        # resolveEasyocrLangs 内部の _DEFAULT_LANGS を呼び出し元が誤って
        # mutateしても、モジュールの状態が壊れないことを保証する。
        first = resolveEasyocrLangs("auto")
        first.append("fr")
        second = resolveEasyocrLangs("auto")
        self.assertEqual(second, ["ja", "en"])


if __name__ == "__main__":
    unittest.main()
