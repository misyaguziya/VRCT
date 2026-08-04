import unittest

import yaml

from models.translation.translation_utils import ctranslate2_weights


LANGUAGES_YAML_PATH = "models/translation/translation_settings/languages/languages.yml"


class TestCTranslate2WeightDefinitions(unittest.TestCase):
    def test_nllb_600m_is_registered(self) -> None:
        weight = ctranslate2_weights["nllb-200-distilled-600M-ct2-int8"]
        self.assertEqual(
            weight["hf_repo"], "JustFrederik/nllb-200-distilled-600M-ct2-int8"
        )
        self.assertEqual(weight["tokenizer"], "facebook/nllb-200-distilled-600M")

    def test_every_weight_type_has_language_mapping(self) -> None:
        with open(LANGUAGES_YAML_PATH, encoding="utf-8") as fp:
            languages = yaml.safe_load(fp)
        ctranslate2_languages = languages["CTranslate2"]

        for weight_type in ctranslate2_weights:
            self.assertIn(weight_type, ctranslate2_languages)
            self.assertIn("source", ctranslate2_languages[weight_type])
            self.assertIn("target", ctranslate2_languages[weight_type])

    def test_nllb_600m_shares_flores200_codes_with_other_nllb_models(self) -> None:
        with open(LANGUAGES_YAML_PATH, encoding="utf-8") as fp:
            languages = yaml.safe_load(fp)
        ctranslate2_languages = languages["CTranslate2"]

        nllb_600m = ctranslate2_languages["nllb-200-distilled-600M-ct2-int8"]
        nllb_1_3b = ctranslate2_languages["nllb-200-distilled-1.3B-ct2-int8"]
        self.assertEqual(nllb_600m["source"], nllb_1_3b["source"])
        self.assertEqual(nllb_600m["target"], nllb_1_3b["target"])
        self.assertEqual(nllb_600m["source"]["Japanese"], "jpn_Jpan")


if __name__ == "__main__":
    unittest.main()
