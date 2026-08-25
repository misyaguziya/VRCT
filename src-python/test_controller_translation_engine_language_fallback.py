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
from model import model


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
                "1": {"language": "English", "country": "United States", "enable": True},
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

    def test_avoids_colliding_with_an_already_fine_enabled_target(self) -> None:
        """Resetting an unsupported source straight to "Japanese" while an
        enabled target is already "Japanese" would make source == target,
        which updateTranslationEngineAndEngineList() treats as a reason to
        force the engine back to CTranslate2 - silently undoing the engine
        selection this fallback exists to preserve."""
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
        self.assertNotEqual(
            config.SELECTED_YOUR_LANGUAGES[self.TAB_NO]["1"]["language"],
            config.SELECTED_TARGET_LANGUAGES[self.TAB_NO]["1"]["language"],
        )
        self.assertEqual(
            config.SELECTED_YOUR_LANGUAGES[self.TAB_NO]["1"],
            {"language": "English", "country": "United States", "enable": True},
        )

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


class TestSetSelectedTranslationEnginesValidatesFinalEngine(unittest.TestCase):
    """setSelectedTranslationEngines() must validate the language against
    whichever engine actually ends up active, not just the one the user
    requested - updateTranslationEngineAndEngineList() can still silently
    downgrade an unavailable engine to CTranslate2 afterward."""

    TAB_NO = "1"
    ENGINES = [
        "DeepL_API", "Google", "Bing", "Papago", "CTranslate2",
        "Plamo_API", "Gemini_API", "OpenAI_API", "LMStudio",
        "OpenAI_Compatible", "Ollama", "Groq_API", "OpenRouter_API",
    ]

    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        self.controller.run_mapping = {
            "selected_translation_engines": "selected_translation_engines",
            "translation_engines": "translation_engines",
            "selected_your_languages": "selected_your_languages",
            "selected_target_languages": "selected_target_languages",
        }
        self.calls = []
        self.controller.run = lambda status, endpoint, result: self.calls.append((status, endpoint, result))

        self._original_tab_no = config.SELECTED_TAB_NO
        self._original_engines = config.SELECTED_TRANSLATION_ENGINES
        self._original_your_languages = config.SELECTED_YOUR_LANGUAGES
        self._original_target_languages = config.SELECTED_TARGET_LANGUAGES
        # SELECTABLE_TRANSLATION_ENGINE_STATUS uses mutable_tracking, so its
        # getter returns a live wrapper object rather than a plain dict -
        # snapshot it as a real dict so tearDown can restore it cleanly.
        self._original_status = dict(config.SELECTABLE_TRANSLATION_ENGINE_STATUS)

        config.SELECTED_TAB_NO = self.TAB_NO

    def tearDown(self) -> None:
        config.SELECTED_TAB_NO = self._original_tab_no
        config.SELECTED_TRANSLATION_ENGINES = self._original_engines
        config.SELECTED_YOUR_LANGUAGES = self._original_your_languages
        config.SELECTED_TARGET_LANGUAGES = self._original_target_languages
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS = self._original_status

    def test_language_falls_back_to_the_engine_actually_active_after_downgrade(self) -> None:
        # Norwegian: supported by DeepL_API, but not by CTranslate2's
        # default weight type - so the two engines disagree on it.
        config.SELECTED_YOUR_LANGUAGES = {
            self.TAB_NO: {"1": {"language": "Norwegian", "country": "Norway", "enable": True}},
        }
        config.SELECTED_TARGET_LANGUAGES = {
            self.TAB_NO: {
                "1": {"language": "English", "country": "United States", "enable": True},
                "2": {"language": "English", "country": "United States", "enable": False},
                "3": {"language": "English", "country": "United States", "enable": False},
            },
        }
        # DeepL_API unavailable (e.g. auth/quota) -> forces a downgrade to
        # CTranslate2 inside updateTranslationEngineAndEngineList().
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS = {engine: False for engine in self.ENGINES}
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS["CTranslate2"] = True

        self.controller.setSelectedTranslationEngines({self.TAB_NO: "DeepL_API"})

        self.assertEqual(config.SELECTED_TRANSLATION_ENGINES[self.TAB_NO], "CTranslate2")
        # Norwegian is unsupported by the engine that actually ended up
        # active (CTranslate2), so it must have been reset - not left
        # dangling because the fallback only checked "DeepL_API".
        self.assertNotEqual(config.SELECTED_YOUR_LANGUAGES[self.TAB_NO]["1"]["language"], "Norwegian")
        self.assertTrue(model.isLanguageSupportedByEngine(
            "CTranslate2", config.SELECTED_YOUR_LANGUAGES[self.TAB_NO]["1"]["language"]
        ))


class TestUpdateTranslationEngineAndEngineListResetsLanguageWhenCTranslate2AlsoUnsupported(unittest.TestCase):
    """CTranslate2 is the engine everything falls back to, but its default
    nllb-200 weight tables don't cover every language either (e.g. Arabic).
    If the user changes the LANGUAGE while CTranslate2 is already selected
    and the new language isn't in CTranslate2's table, there's no further
    engine to fall back to - the language itself must be reset, or
    CTranslate2 ends up simultaneously "selected" and excluded from the
    selectable-engines list (shown as greyed out) in the UI."""

    TAB_NO = "1"
    ENGINES = [
        "DeepL_API", "Google", "Bing", "Papago", "CTranslate2",
        "Plamo_API", "Gemini_API", "OpenAI_API", "LMStudio",
        "OpenAI_Compatible", "Ollama", "Groq_API", "OpenRouter_API",
    ]

    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        self.controller.run_mapping = {
            "selected_translation_engines": "selected_translation_engines",
            "translation_engines": "translation_engines",
            "selected_your_languages": "selected_your_languages",
            "selected_target_languages": "selected_target_languages",
        }
        self.calls = []
        self.controller.run = lambda status, endpoint, result: self.calls.append((status, endpoint, result))

        self._original_tab_no = config.SELECTED_TAB_NO
        self._original_engines = config.SELECTED_TRANSLATION_ENGINES
        self._original_your_languages = config.SELECTED_YOUR_LANGUAGES
        self._original_target_languages = config.SELECTED_TARGET_LANGUAGES
        self._original_status = dict(config.SELECTABLE_TRANSLATION_ENGINE_STATUS)

        config.SELECTED_TAB_NO = self.TAB_NO
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS = {engine: True for engine in self.ENGINES}

    def tearDown(self) -> None:
        config.SELECTED_TAB_NO = self._original_tab_no
        config.SELECTED_TRANSLATION_ENGINES = self._original_engines
        config.SELECTED_YOUR_LANGUAGES = self._original_your_languages
        config.SELECTED_TARGET_LANGUAGES = self._original_target_languages
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS = self._original_status

    def test_source_language_reset_when_ctranslate2_does_not_support_it_either(self) -> None:
        config.SELECTED_TRANSLATION_ENGINES = {self.TAB_NO: "CTranslate2"}
        # Arabic isn't in CTranslate2's default nllb-200 weight tables.
        config.SELECTED_YOUR_LANGUAGES = {
            self.TAB_NO: {"1": {"language": "Arabic", "country": "Syria", "enable": True}},
        }
        config.SELECTED_TARGET_LANGUAGES = {
            self.TAB_NO: {
                "1": {"language": "English", "country": "United States", "enable": True},
                "2": {"language": "English", "country": "United States", "enable": False},
                "3": {"language": "English", "country": "United States", "enable": False},
            },
        }

        self.controller.updateTranslationEngineAndEngineList()

        # CTranslate2 stays selected (nothing else to fall back to)...
        self.assertEqual(config.SELECTED_TRANSLATION_ENGINES[self.TAB_NO], "CTranslate2")
        # ...but the language must have been reset to something it
        # actually supports, so CTranslate2 isn't left selected-but-greyed-out.
        self.assertNotEqual(config.SELECTED_YOUR_LANGUAGES[self.TAB_NO]["1"]["language"], "Arabic")
        self.assertTrue(model.isLanguageSupportedByEngine(
            "CTranslate2", config.SELECTED_YOUR_LANGUAGES[self.TAB_NO]["1"]["language"]
        ))
        self.assertIn("CTranslate2", [call[2] for call in self.calls if call[1] == "translation_engines"][-1])


if __name__ == "__main__":
    unittest.main()
