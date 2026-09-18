"""Tests for models.ocr.ocr_languages.

VRCT言語名 <-> EasyOCR言語コードの変換は純粋な辞書引きなので、
実際のEasyOCR/画像処理系の依存が無くても直接検証できる。

EasyOCRのReaderは1つのスクリプトグループしか同時にロードできないため
「autoで全言語」は作れない。ここでは「autoを含む未対応の値が黙って
英語にフォールバックせず、空リストとして扱われる」ことを担保する
(黙ってフォールバックしていた頃、日本語の吹き出しが英語モデルで読まれて
ローマ字のような文字列になる不具合が実機で出た)。
"""

import unittest

from models.ocr.ocr_languages import (
    SUPPORTED_LANGUAGES,
    isSupported,
    resolveEasyocrLangs,
    vrctToEasyocr,
)


class TestVrctToEasyocr(unittest.TestCase):
    def test_known_language_maps_to_its_code(self) -> None:
        self.assertEqual(vrctToEasyocr("Japanese"), "ja")
        self.assertEqual(vrctToEasyocr("Korean"), "ko")
        self.assertEqual(vrctToEasyocr("Chinese Simplified"), "ch_sim")

    def test_unknown_language_has_no_code(self) -> None:
        for value in ("Klingon", "", "auto", None):
            self.assertIsNone(vrctToEasyocr(value))  # type: ignore[arg-type]


class TestSupportedLanguages(unittest.TestCase):
    def test_every_listed_language_resolves(self) -> None:
        self.assertTrue(SUPPORTED_LANGUAGES)
        for language in SUPPORTED_LANGUAGES:
            self.assertTrue(isSupported(language))
            self.assertTrue(resolveEasyocrLangs(language))

    def test_list_is_sorted_and_unique(self) -> None:
        self.assertEqual(list(SUPPORTED_LANGUAGES), sorted(set(SUPPORTED_LANGUAGES)))

    def test_auto_is_not_selectable(self) -> None:
        self.assertNotIn("auto", SUPPORTED_LANGUAGES)
        self.assertFalse(isSupported("auto"))


class TestResolveEasyocrLangs(unittest.TestCase):
    def test_non_english_language_gets_english_as_a_companion(self) -> None:
        # 同じ吹き出しにラテン文字が混ざることがあるため。
        self.assertEqual(resolveEasyocrLangs("Japanese"), ["ja", "en"])
        self.assertEqual(resolveEasyocrLangs("Korean"), ["ko", "en"])

    def test_english_alone_does_not_duplicate_english(self) -> None:
        self.assertEqual(resolveEasyocrLangs("English"), ["en"])

    def test_unsupported_values_return_nothing_instead_of_english(self) -> None:
        for value in ("auto", "Auto", "AUTO", "Klingon", "", None):
            self.assertEqual(resolveEasyocrLangs(value), [])  # type: ignore[arg-type]

    def test_returned_list_is_a_fresh_copy_each_time(self) -> None:
        first = resolveEasyocrLangs("Japanese")
        first.append("ko")
        self.assertEqual(resolveEasyocrLangs("Japanese"), ["ja", "en"])


if __name__ == "__main__":
    unittest.main()
