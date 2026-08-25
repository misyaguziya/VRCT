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


class TestGetListLanguageAndCountryFilteredByEngine(unittest.TestCase):
    def test_filtering_by_engine_excludes_unsupported_languages(self) -> None:
        all_languages = model.getListLanguageAndCountry()
        deepl_languages = model.getListLanguageAndCountry("DeepL_API")

        self.assertTrue(any(entry["language"] == "Arabic" for entry in all_languages))
        self.assertFalse(any(entry["language"] == "Arabic" for entry in deepl_languages))
        self.assertLessEqual(len(deepl_languages), len(all_languages))

    def test_filtered_list_only_contains_engine_supported_languages(self) -> None:
        deepl_languages = model.getListLanguageAndCountry("DeepL_API")
        for entry in deepl_languages:
            self.assertTrue(model.isLanguageSupportedByEngine("DeepL_API", entry["language"]))


if __name__ == "__main__":
    unittest.main()
