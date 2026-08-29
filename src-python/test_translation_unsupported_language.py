import unittest
from unittest.mock import MagicMock, patch

from models.translation.translation_translator import Translator, UnsupportedLanguageError


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


if __name__ == "__main__":
    unittest.main()
