"""model.py の isLanguageSupportedByTranscriptionEngine /
getTranscriptionLanguagesForEngine / pickDefaultLanguageAndCountryForTranscriptionEngine
/ getListLanguageAndCountry の文字起こしエンジンによる言語フィルタリングの
テスト。

Google/Whisper/Groq_Whisper/OpenAI_Whisper/Custom_Whisper は
transcription_lang の全エントリを網羅している前提 (常に対応) で、
Deepgram だけが実際に選択中のモデルの対応言語と動的に突き合わされる。
"""

import unittest

from config import config
from model import model


class TestIsLanguageSupportedByTranscriptionEngine(unittest.TestCase):
    def setUp(self) -> None:
        self._original_deepgram_model = config._SELECTED_DEEPGRAM_MODEL
        self._original_deepgram_languages = dict(config._DEEPGRAM_MODEL_LANGUAGES)
        config._SELECTED_DEEPGRAM_MODEL = "nova-3"
        config.DEEPGRAM_MODEL_LANGUAGES = {"nova-3": ["en", "ja"]}

    def tearDown(self) -> None:
        config._SELECTED_DEEPGRAM_MODEL = self._original_deepgram_model
        config.DEEPGRAM_MODEL_LANGUAGES = self._original_deepgram_languages

    def test_google_supports_every_entry_in_the_table(self) -> None:
        self.assertTrue(model.isLanguageSupportedByTranscriptionEngine("Google", "Korean", "South Korea"))

    def test_whisper_api_engines_support_every_entry_too(self) -> None:
        for engine in ("Whisper", "Groq_Whisper", "OpenAI_Whisper", "Custom_Whisper"):
            with self.subTest(engine=engine):
                self.assertTrue(model.isLanguageSupportedByTranscriptionEngine(engine, "Korean", "South Korea"))

    def test_deepgram_matches_currently_selected_models_languages(self) -> None:
        self.assertTrue(model.isLanguageSupportedByTranscriptionEngine("Deepgram", "Japanese", "Japan"))
        self.assertFalse(model.isLanguageSupportedByTranscriptionEngine("Deepgram", "Korean", "South Korea"))

    def test_unknown_language_country_pair_is_never_supported(self) -> None:
        self.assertFalse(model.isLanguageSupportedByTranscriptionEngine("Google", "Klingon", "Qo'noS"))


class TestGetTranscriptionLanguagesForEngine(unittest.TestCase):
    def setUp(self) -> None:
        self._original_deepgram_model = config._SELECTED_DEEPGRAM_MODEL
        self._original_deepgram_languages = dict(config._DEEPGRAM_MODEL_LANGUAGES)
        config._SELECTED_DEEPGRAM_MODEL = "nova-3"
        config.DEEPGRAM_MODEL_LANGUAGES = {"nova-3": ["en", "ja"]}

    def tearDown(self) -> None:
        config._SELECTED_DEEPGRAM_MODEL = self._original_deepgram_model
        config.DEEPGRAM_MODEL_LANGUAGES = self._original_deepgram_languages

    def test_deepgram_list_is_restricted(self) -> None:
        result = model.getTranscriptionLanguagesForEngine("Deepgram")
        languages = {entry["language"] for entry in result}
        self.assertEqual(languages, {"English", "Japanese"})

    def test_whisper_list_covers_far_more_languages(self) -> None:
        deepgram_count = len(model.getTranscriptionLanguagesForEngine("Deepgram"))
        whisper_count = len(model.getTranscriptionLanguagesForEngine("Whisper"))
        self.assertGreater(whisper_count, deepgram_count)


class TestPickDefaultLanguageAndCountryForTranscriptionEngine(unittest.TestCase):
    def setUp(self) -> None:
        self._original_deepgram_model = config._SELECTED_DEEPGRAM_MODEL
        self._original_deepgram_languages = dict(config._DEEPGRAM_MODEL_LANGUAGES)
        config._SELECTED_DEEPGRAM_MODEL = "nova-3"
        config.DEEPGRAM_MODEL_LANGUAGES = {"nova-3": ["en", "ja"]}

    def tearDown(self) -> None:
        config._SELECTED_DEEPGRAM_MODEL = self._original_deepgram_model
        config.DEEPGRAM_MODEL_LANGUAGES = self._original_deepgram_languages

    def test_prefers_japanese_when_available_and_not_avoided(self) -> None:
        result = model.pickDefaultLanguageAndCountryForTranscriptionEngine("Deepgram", avoid_languages=set())
        self.assertEqual(result, {"language": "Japanese", "country": "Japan"})

    def test_falls_back_to_english_when_japanese_is_avoided(self) -> None:
        result = model.pickDefaultLanguageAndCountryForTranscriptionEngine("Deepgram", avoid_languages={"Japanese"})
        self.assertEqual(result, {"language": "English", "country": "United States"})

    def test_returns_none_when_every_supported_language_is_taken(self) -> None:
        result = model.pickDefaultLanguageAndCountryForTranscriptionEngine(
            "Deepgram", avoid_languages={"Japanese", "English"}
        )
        self.assertIsNone(result)


class TestGetListLanguageAndCountryFiltersByTranscriptionEngine(unittest.TestCase):
    def setUp(self) -> None:
        self._original_engine = config._SELECTED_TRANSCRIPTION_ENGINE
        self._original_deepgram_model = config._SELECTED_DEEPGRAM_MODEL
        self._original_deepgram_languages = dict(config._DEEPGRAM_MODEL_LANGUAGES)

    def tearDown(self) -> None:
        config._SELECTED_TRANSCRIPTION_ENGINE = self._original_engine
        config._SELECTED_DEEPGRAM_MODEL = self._original_deepgram_model
        config.DEEPGRAM_MODEL_LANGUAGES = self._original_deepgram_languages

    def test_google_returns_the_full_list(self) -> None:
        config._SELECTED_TRANSCRIPTION_ENGINE = "Google"
        result = model.getListLanguageAndCountry()
        self.assertTrue(any(e["language"] == "Korean" for e in result))

    def test_deepgram_restricts_the_list_to_the_selected_models_languages(self) -> None:
        config._SELECTED_TRANSCRIPTION_ENGINE = "Deepgram"
        config._SELECTED_DEEPGRAM_MODEL = "nova-3"
        config.DEEPGRAM_MODEL_LANGUAGES = {"nova-3": ["en", "ja"]}

        result = model.getListLanguageAndCountry()

        languages = {e["language"] for e in result}
        self.assertIn("Japanese", languages)
        self.assertIn("English", languages)
        self.assertNotIn("Korean", languages)


if __name__ == "__main__":
    unittest.main()
