"""Tests for models.ocr.ocr_languages.

設定値 -> 使用モデルの対応表は純粋な辞書引きなので、OCRエンジン本体が無くても検証できる。

ここで守りたいのは2点。
1. "auto" を含む選択肢が、実際に読めるモデルへ解決されること
2. 未対応の値が黙って別のモデルへフォールバックしないこと
   (EasyOCR時代、未対応言語が黙って英語モデルになり、日本語の吹き出しが
   ローマ字のような文字列で認識される不具合が実機で出た)
"""

import unittest

from models.ocr.ocr_languages import (
    AUTO,
    SELECTABLE_LANGUAGES,
    OcrModelSpec,
    isSupported,
    resolveModelSpec,
)


class TestSelectableLanguages(unittest.TestCase):
    def test_auto_comes_first(self) -> None:
        self.assertEqual(SELECTABLE_LANGUAGES[0], AUTO)

    def test_every_choice_resolves_to_a_model(self) -> None:
        for language in SELECTABLE_LANGUAGES:
            self.assertIsInstance(resolveModelSpec(language), OcrModelSpec, language)
            self.assertTrue(isSupported(language), language)

    def test_only_scripts_needing_their_own_model_are_listed(self) -> None:
        # 日英中+ラテン文字系は auto と同じモデルなので選択肢に出さない。
        for language in ("Japanese", "English", "French", "Chinese Simplified"):
            self.assertNotIn(language, SELECTABLE_LANGUAGES)
        for language in ("Korean", "Russian", "Ukrainian", "Thai", "Arabic", "Hindi"):
            self.assertIn(language, SELECTABLE_LANGUAGES)


class TestResolveModelSpec(unittest.TestCase):
    def test_auto_uses_the_multilingual_model(self) -> None:
        spec = resolveModelSpec(AUTO)
        self.assertEqual((spec.ocr_version, spec.model_type, spec.lang_rec),
                         ("PP-OCRv6", "small", None))

    def test_languages_covered_by_the_multilingual_model_map_to_it(self) -> None:
        # 旧バージョンが保存した言語名の設定を、そのまま使えるようにするため。
        for language in ("Japanese", "English", "Chinese Traditional", "Vietnamese"):
            self.assertEqual(resolveModelSpec(language), resolveModelSpec(AUTO), language)

    def test_scripts_outside_the_multilingual_model_get_their_own(self) -> None:
        cases = {
            "Korean": "korean",
            "Russian": "cyrillic",
            "Ukrainian": "cyrillic",
            "Thai": "th",
            "Arabic": "arabic",
            "Hindi": "devanagari",
        }
        for language, lang_rec in cases.items():
            spec = resolveModelSpec(language)
            self.assertEqual(spec.ocr_version, "PP-OCRv5", language)
            self.assertEqual(spec.lang_rec, lang_rec, language)

    def test_unsupported_values_resolve_to_nothing(self) -> None:
        for value in ("Klingon", "", None, "Japanese (Japan)"):
            self.assertIsNone(resolveModelSpec(value))  # type: ignore[arg-type]
            self.assertFalse(isSupported(value))  # type: ignore[arg-type]

    def test_spec_is_hashable_so_it_can_key_the_engine_cache(self) -> None:
        self.assertEqual(len({resolveModelSpec("Russian"), resolveModelSpec("Ukrainian")}), 1)
        self.assertEqual(len({resolveModelSpec("Korean"), resolveModelSpec("Thai")}), 2)


if __name__ == "__main__":
    unittest.main()
