import unittest

from model import model


class TestIsLanguageSupportedByEngine(unittest.TestCase):
    def test_deepl_api_does_not_support_arabic(self) -> None:
        # Matches the kiroku.zip bug report: DeepL_API has no "Arabic" entry.
        self.assertFalse(model.isLanguageSupportedByEngine("DeepL_API", "Arabic"))

    def test_deepl_api_supports_japanese(self) -> None:
        self.assertTrue(model.isLanguageSupportedByEngine("DeepL_API", "Japanese"))

    def test_ctranslate2_uses_configured_weight_type(self) -> None:
        # CTranslate2's supported-language table is nested under the
        # currently selected weight type rather than a flat "source" dict.
        self.assertTrue(model.isLanguageSupportedByEngine("CTranslate2", "Japanese"))


class TestGetListLanguageAndCountryIsNotFilteredByEngine(unittest.TestCase):
    """The language selector must offer every language up front regardless
    of the currently selected engine - filtering it by engine forces users
    to switch to a broadly-compatible engine first, pick the language, then
    switch back. Unsupported picks are instead handled by falling the
    engine/language back automatically (see controller.py)."""

    def test_list_includes_languages_the_current_engine_does_not_support(self) -> None:
        languages = model.getListLanguageAndCountry()
        # DeepL_API has no "Arabic" entry, but it must still be offered.
        self.assertTrue(any(entry["language"] == "Arabic" for entry in languages))


class TestPickDefaultLanguageForEngine(unittest.TestCase):
    def test_prefers_japanese_when_not_avoided(self) -> None:
        default = model.pickDefaultLanguageForEngine("DeepL_API", avoid_languages=set())
        self.assertEqual(default, {"language": "Japanese", "country": "Japan"})

    def test_falls_back_to_english_when_japanese_is_avoided(self) -> None:
        default = model.pickDefaultLanguageForEngine("DeepL_API", avoid_languages={"Japanese"})
        self.assertEqual(default, {"language": "English", "country": "United States"})

    def test_picks_some_other_supported_language_when_both_defaults_avoided(self) -> None:
        default = model.pickDefaultLanguageForEngine("DeepL_API", avoid_languages={"Japanese", "English"})
        self.assertIsNotNone(default)
        self.assertNotIn(default["language"], {"Japanese", "English"})
        self.assertTrue(model.isLanguageSupportedByEngine("DeepL_API", default["language"]))


if __name__ == "__main__":
    unittest.main()
