import unittest
from unittest.mock import MagicMock

from models.translation.translation_translator import Translator


class FakeHypothesis:
    def __init__(self, tokens: list[str]) -> None:
        self.hypotheses = [tokens]


class FakeTokenizer:
    def __init__(self) -> None:
        self.src_lang = None
        self.lang_code_to_token = {"en": "__en__"}

    def encode(self, message: str) -> list[str]:
        return list(message)

    def convert_ids_to_tokens(self, ids: list[str]) -> list[str]:
        return ids

    def convert_tokens_to_ids(self, tokens: list[str]) -> list[str]:
        return tokens

    def decode(self, ids: list[str]) -> str:
        return "".join(ids)


class TestTranslateCTranslate2Dispatch(unittest.TestCase):
    def setUp(self) -> None:
        self.translator = Translator()
        self.translator.is_loaded_ctranslate2_model = True
        self.translator.ctranslate2_tokenizer = FakeTokenizer()
        self.translator.ctranslate2_translator = MagicMock()
        self.translator.ctranslate2_translator.translate_batch.return_value = [
            FakeHypothesis(["_prefix_", "h", "i"])
        ]

    def test_m2m100_uses_lang_code_to_token(self) -> None:
        self.translator.translateCTranslate2("hi", "ja", "en", "m2m100_418M-ct2-int8")
        _, kwargs = self.translator.ctranslate2_translator.translate_batch.call_args
        self.assertEqual(kwargs["target_prefix"], [["__en__"]])

    def test_nllb_600m_uses_raw_language_code_as_prefix(self) -> None:
        self.translator.translateCTranslate2(
            "hi", "jpn_Jpan", "eng_Latn", "nllb-200-distilled-600M-ct2-int8"
        )
        _, kwargs = self.translator.ctranslate2_translator.translate_batch.call_args
        self.assertEqual(kwargs["target_prefix"], [["eng_Latn"]])

    def test_unknown_weight_type_returns_false(self) -> None:
        result = self.translator.translateCTranslate2(
            "hi", "ja", "en", "unknown-weight"
        )
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
