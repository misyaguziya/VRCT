"""Changing the translation engine must not silently leave a language
selected that the new engine doesn't support (e.g. picking DeepL_API while
"your language" is still Arabic, which DeepL_API has no entry for in
translation_languages.py). Before this fix nothing validated the language
against the newly selected engine, so the mismatch went unnoticed until a
translation was actually attempted (see kiroku.zip bug report logs).

updateTranslationEngineAndEngineList() already handles the opposite
direction (falls the ENGINE back to CTranslate2 when the LANGUAGE changes
to something unsupported); fallbackUnsupportedLanguagesForEngine() is its
mirror for engine -> language.
"""
import unittest

from controller import Controller, config


class TestFallbackUnsupportedLanguagesForEngine(unittest.TestCase):
    TAB_NO = "1"

    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        self.controller.run_mapping = {
            "selected_your_languages": "selected_your_languages",
            "selected_target_languages": "selected_target_languages",
        }
        self.calls = []
        self.controller.run = lambda status, endpoint, result: self.calls.append((status, endpoint, result))

        self._original_your_languages = config.SELECTED_YOUR_LANGUAGES
        self._original_target_languages = config.SELECTED_TARGET_LANGUAGES

    def tearDown(self) -> None:
        config.SELECTED_YOUR_LANGUAGES = self._original_your_languages
        config.SELECTED_TARGET_LANGUAGES = self._original_target_languages

    def test_resets_unsupported_source_language_to_default(self) -> None:
        config.SELECTED_YOUR_LANGUAGES = {
            self.TAB_NO: {"1": {"language": "Arabic", "country": "Syria", "enable": True}},
        }
        config.SELECTED_TARGET_LANGUAGES = {
            self.TAB_NO: {
                "1": {"language": "Japanese", "country": "Japan", "enable": True},
                "2": {"language": "English", "country": "United States", "enable": False},
                "3": {"language": "English", "country": "United States", "enable": False},
            },
        }

        changed = self.controller.fallbackUnsupportedLanguagesForEngine(self.TAB_NO, "DeepL_API")

        self.assertTrue(changed)
        self.assertEqual(
            config.SELECTED_YOUR_LANGUAGES[self.TAB_NO]["1"],
            {"language": "Japanese", "country": "Japan", "enable": True},
        )
        self.assertTrue(any(endpoint == "selected_your_languages" for _, endpoint, _ in self.calls))

    def test_resets_unsupported_enabled_target_language_only(self) -> None:
        config.SELECTED_YOUR_LANGUAGES = {
            self.TAB_NO: {"1": {"language": "Japanese", "country": "Japan", "enable": True}},
        }
        config.SELECTED_TARGET_LANGUAGES = {
            self.TAB_NO: {
                "1": {"language": "Arabic", "country": "Syria", "enable": True},
                "2": {"language": "Arabic", "country": "Syria", "enable": False},  # disabled: must be left alone
                "3": {"language": "English", "country": "United States", "enable": False},
            },
        }

        changed = self.controller.fallbackUnsupportedLanguagesForEngine(self.TAB_NO, "DeepL_API")

        self.assertTrue(changed)
        self.assertEqual(
            config.SELECTED_TARGET_LANGUAGES[self.TAB_NO]["1"],
            {"language": "English", "country": "United States", "enable": True},
        )
        # A disabled slot isn't actually translated to, so it's left as-is.
        self.assertEqual(config.SELECTED_TARGET_LANGUAGES[self.TAB_NO]["2"]["language"], "Arabic")
        self.assertTrue(any(endpoint == "selected_target_languages" for _, endpoint, _ in self.calls))

    def test_no_change_when_languages_are_supported(self) -> None:
        config.SELECTED_YOUR_LANGUAGES = {
            self.TAB_NO: {"1": {"language": "Japanese", "country": "Japan", "enable": True}},
        }
        config.SELECTED_TARGET_LANGUAGES = {
            self.TAB_NO: {
                "1": {"language": "English", "country": "United States", "enable": True},
                "2": {"language": "English", "country": "United States", "enable": False},
                "3": {"language": "English", "country": "United States", "enable": False},
            },
        }

        changed = self.controller.fallbackUnsupportedLanguagesForEngine(self.TAB_NO, "DeepL_API")

        self.assertFalse(changed)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
