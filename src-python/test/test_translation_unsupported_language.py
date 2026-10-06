import unittest
from unittest.mock import MagicMock, patch

from models.translation.translation_languages import loadTranslationLanguages
from models.translation.translation_translator import Translator, UnsupportedLanguageError


def setUpModule() -> None:
    # `translation_lang` is filled by config.py at startup, so running this
    # file on its own used to leave it empty and turn every lookup into an
    # UnsupportedLanguageError. Load it here so the file stands alone.
    loadTranslationLanguages(path=".")


class TestGetLanguageCodeUnsupportedLanguage(unittest.TestCase):
    """Bug report: selecting a language a translator doesn't support must not
    look like a translator-engine failure (rate limit / auth / network)."""

    def test_unsupported_source_language_raises_unsupported_language_error(self) -> None:
        # DeepL_API has no "Arabic" entry (see docs/kiroku bug report logs:
        # repeated `KeyError: 'Arabic'` at translation_translator.py:498).
        with self.assertRaises(UnsupportedLanguageError):
            Translator.getLanguageCode(
                translator_name="DeepL_API",
                weight_type="",
                target_country="Japan",
                source_language="Arabic",
                target_language="Japanese",
            )

    def test_supported_language_pair_resolves_normally(self) -> None:
        source, target = Translator.getLanguageCode(
            translator_name="DeepL_API",
            weight_type="",
            target_country="Japan",
            source_language="English",
            target_language="Japanese",
        )
        self.assertIsInstance(source, str)
        self.assertIsInstance(target, str)


class TestTranslateReturnsNoneForUnsupportedLanguage(unittest.TestCase):
    def setUp(self) -> None:
        self.translator = Translator.__new__(Translator)

    def test_translate_returns_none_not_false_for_unsupported_language(self) -> None:
        result = self.translator.translate(
            translator_name="DeepL_API",
            weight_type="",
            source_language="Arabic",
            target_language="Japanese",
            target_country="Japan",
            message="hello",
        )
        self.assertIsNone(result)

    @patch("models.translation.translation_translator.errorLogging")
    def test_translate_returns_false_on_real_backend_failure(self, mock_error_logging: MagicMock) -> None:
        with patch(
            "models.translation.translation_translator.other_web_Translator",
            side_effect=RuntimeError("network down"),
        ), patch("models.translation.translation_translator.ENABLE_TRANSLATORS", True):
            result = self.translator.translate(
                translator_name="Bing",
                weight_type="",
                source_language="English",
                target_language="Japanese",
                target_country="Japan",
                message="hello",
            )
        self.assertFalse(result)
        self.assertIsNotNone(result)  # False, not None: this must still look like an engine failure
        mock_error_logging.assert_called_once()


class TestTranslateNeverReportsAnUnreachableEngineAsSuccess(unittest.TestCase):
    """A branch that never ran must not come back as an empty success.

    `getTranslate` decides success with `isinstance(translation, str)`, so a
    "" leaking out of `translate()` is reported as a successful translation of
    nothing: no CTranslate2 fallback, no error log, and nothing the user sees
    except empty output.
    """

    def setUp(self) -> None:
        self.translator = Translator.__new__(Translator)

    def test_web_engine_returns_false_when_the_backend_is_unavailable(self) -> None:
        # What an offline start used to look like: the import failed, so the
        # Google/Bing/Papago branches are skipped entirely.
        with patch(
            "models.translation.translation_translator.ENABLE_TRANSLATORS", False
        ), patch("models.translation.translation_translator.other_web_Translator", None):
            for engine in ("Google", "Bing", "Papago"):
                with self.subTest(engine=engine):
                    result = self.translator.translate(
                        translator_name=engine,
                        weight_type="",
                        source_language="English",
                        target_language="Japanese",
                        target_country="Japan",
                        message="hello",
                    )
                    self.assertIs(result, False)

    def test_deepl_returns_false_when_translators_are_disabled(self) -> None:
        self.translator.is_enable_translators = False
        result = self.translator.translate(
            translator_name="DeepL_API",
            weight_type="",
            source_language="English",
            target_language="Japanese",
            target_country="Japan",
            message="hello",
        )
        self.assertIs(result, False)

    def test_unknown_translator_name_never_returns_an_empty_string(self) -> None:
        # E.g. a config naming an engine this build dropped. It never reaches
        # the `match`: getLanguageCode runs first and finds no language table
        # for the name, so it surfaces as an unsupported pair (None) and the
        # caller passes the original text through. Either way, not "".
        result = self.translator.translate(
            translator_name="NoSuchEngine",
            weight_type="",
            source_language="English",
            target_language="Japanese",
            target_country="Japan",
            message="hello",
        )
        self.assertIsNone(result)

    def test_same_language_still_returns_the_original_message(self) -> None:
        result = self.translator.translate(
            translator_name="Google",
            weight_type="",
            source_language="Japanese",
            target_language="Japanese",
            target_country="Japan",
            message="こんにちは",
        )
        self.assertEqual(result, "こんにちは")


if __name__ == "__main__":
    unittest.main()
