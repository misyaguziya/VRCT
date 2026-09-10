"""Bug report repro (kiroku.zip logs): repeatedly speaking a language a
translator doesn't support (e.g. Arabic on DeepL_API/Bing) flooded
KeyError in getLanguageCode, which model.getTranslate() treated exactly
like a real backend failure. That made controller.py permanently disable
the translation engine (SELECTABLE_TRANSLATION_ENGINE_STATUS[...] = False)
until app restart, even though nothing was actually wrong with the engine.

getTranslate() must report success_flag=True (engine healthy) when the
translator backend reports None (unsupported language pair), and only
False (engine failure -> caller may disable it) when the backend reports
an actual False failure.
"""
import unittest
from unittest.mock import patch

from model import Model


class TestGetTranslateSuccessFlagSemantics(unittest.TestCase):
    def setUp(self) -> None:
        # object.__new__ bypasses Model's singleton __new__ so this instance
        # doesn't leak into / get clobbered by the shared `model` singleton.
        self.model = object.__new__(Model)
        self.model._inited = True
        self.model.translation_history = []
        self.model.translation_history_max_items = 20
        self.model.translator = None  # replaced per-test below

    def test_unsupported_language_is_not_reported_as_engine_failure(self) -> None:
        # First call (requested engine): unsupported language -> None.
        # CTranslate2 fallback: succeeds with translated text.
        translate_mock = self.model.translator = type(
            "T", (), {"translate": staticmethod(lambda **kwargs: (
                None if kwargs["translator_name"] == "Bing" else "こんにちは"
            ))}
        )()

        translation, success_flag = self.model.getTranslate(
            translator_name="Bing",
            source_language="Arabic",
            target_language="Japanese",
            target_country="Japan",
            message="hello",
        )

        self.assertEqual(translation, "こんにちは")
        self.assertTrue(success_flag, "unsupported language must not be reported as an engine failure")

    def test_real_backend_failure_is_still_reported_as_failure(self) -> None:
        calls = {"n": 0}

        def fake_translate(**kwargs):
            if kwargs["translator_name"] == "Bing":
                return False
            calls["n"] += 1
            return False  # CTranslate2 fallback also down for this test

        self.model.translator = type("T", (), {"translate": staticmethod(fake_translate)})()

        with patch("model.errorLogging"), patch("model.sleep"):
            translation, success_flag = self.model.getTranslate(
                translator_name="Bing",
                source_language="English",
                target_language="Japanese",
                target_country="Japan",
                message="hello",
            )

        self.assertEqual(translation, "hello")  # falls back to original message
        self.assertFalse(success_flag, "a real backend failure must still be reported as a failure")

    def test_unsupported_on_both_engines_is_not_reported_as_engine_failure(self) -> None:
        # Neither the requested engine nor the CTranslate2 fallback support
        # this language pair - expected, not an engine failure.
        self.model.translator = type(
            "T", (), {"translate": staticmethod(lambda **kwargs: None)}
        )()

        with patch("model.errorLogging") as mock_error_logging:
            translation, success_flag = self.model.getTranslate(
                translator_name="Bing",
                source_language="Arabic",
                target_language="Klingon",
                target_country="Qo'noS",
                message="hello",
            )

        self.assertEqual(translation, "hello")  # falls back to the original message
        self.assertTrue(success_flag, "both engines lacking the language pair is not an engine failure")
        mock_error_logging.assert_not_called()

    def test_fallback_failure_after_unsupported_primary_is_still_reported_as_failure(self) -> None:
        # The requested engine reports the language unsupported (None), but
        # the CTranslate2 fallback then hits a genuine backend failure
        # (False) - success_flag must reflect that real failure, not the
        # primary engine's unrelated "unsupported" result.
        self.model.translator = type(
            "T", (), {"translate": staticmethod(lambda **kwargs: (
                None if kwargs["translator_name"] == "Bing" else False
            ))}
        )()

        with patch("model.errorLogging") as mock_error_logging, patch("model.sleep"):
            translation, success_flag = self.model.getTranslate(
                translator_name="Bing",
                source_language="Arabic",
                target_language="Japanese",
                target_country="Japan",
                message="hello",
            )

        self.assertEqual(translation, "hello")
        self.assertFalse(success_flag, "a genuine CTranslate2 fallback failure must not be masked as success")
        mock_error_logging.assert_called_once()


if __name__ == "__main__":
    unittest.main()
