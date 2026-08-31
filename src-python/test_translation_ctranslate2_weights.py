import os
import unittest

import yaml

from models.translation.translation_utils import ctranslate2_weights


LANGUAGES_YAML_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "models", "translation", "translation_settings", "languages", "languages.yml",
)


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

    def test_nllb_uses_plain_language_names_shared_with_other_engines(self) -> None:
        """FLORES-200 (nllb's language table) names dialects/scripts more
        granularly than the rest of this file's engines do (e.g. "Standard
        Arabic" vs. everyone else's plain "Arabic"). Where nllb's standard
        variant is what every other engine means by the plain name, the key
        must match - otherwise CTranslate2 looks like it doesn't support a
        language it actually does, and the engine gets treated as
        unavailable for it (see kiroku.zip bug report follow-up)."""
        with open(LANGUAGES_YAML_PATH, encoding="utf-8") as fp:
            languages = yaml.safe_load(fp)
        nllb_source = languages["CTranslate2"]["nllb-200-distilled-600M-ct2-int8"]["source"]

        # Reference set: every other engine's plain language names, plus
        # CTranslate2's own m2m100 weight types (which - unlike nllb's
        # FLORES-200 table - already use the same plain naming as the rest
        # of the app).
        reference_names = set()
        for engine, cfg in languages.items():
            if engine == "CTranslate2":
                reference_names.update(cfg["m2m100_418M-ct2-int8"]["source"].keys())
                continue
            reference_names.update(cfg["source"].keys())
            reference_names.update(cfg.get("target", {}).keys())

        for language in ["Arabic", "Persian", "Norwegian", "Uzbek", "Latvian", "Malay",
                          "Tibetan", "Azerbaijani", "Pashto", "Yiddish", "Mongolian",
                          "Malagasy", "Albanian", "Oromo", "Kurdish"]:
            self.assertIn(
                language, reference_names,
                f"test setup error: {language!r} is expected to also appear in another engine",
            )
            self.assertIn(
                language, nllb_source,
                f"nllb-200 has no plain {language!r} entry - it's likely hiding under a "
                "dialect/script-qualified key (e.g. 'Standard Arabic') that other engines "
                "don't use, making CTranslate2 look unsupported for a language it does support",
            )


if __name__ == "__main__":
    unittest.main()
