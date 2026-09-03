"""`TRANSLATION_PROVIDER_REGISTRY` (フェーズ3・項目17 の設計段階) の自己整合性テスト。

このレジストリはまだ controller.py / model.py / translation_translator.py の
どこからも参照されていない (設計のみ、挙動変化なし)。ここでは登録内容が
実際の config 属性・mainloop ルーティング・クライアントクラスの形状と
食い違っていないことだけを検証する — 将来レジストリにエンジンを足す際、
タイプミスをここで検出できるようにするための安全網。
"""

import unittest

import mainloop
from config import config
from errors import ErrorCode
from models.translation.translation_providers import (
    REQUIRED_CLIENT_METHODS,
    TRANSLATION_PROVIDER_REGISTRY,
)


class TestRegistryMatchesConfigAttributes(unittest.TestCase):
    def test_every_selectable_model_list_attr_exists_on_config(self) -> None:
        for engine_key, spec in TRANSLATION_PROVIDER_REGISTRY.items():
            with self.subTest(engine=engine_key):
                self.assertTrue(hasattr(config, spec.selectable_model_list_attr))

    def test_every_selected_model_attr_exists_on_config(self) -> None:
        for engine_key, spec in TRANSLATION_PROVIDER_REGISTRY.items():
            with self.subTest(engine=engine_key):
                self.assertTrue(hasattr(config, spec.selected_model_attr))

    def test_every_engine_key_exists_in_default_auth_keys(self) -> None:
        for engine_key in TRANSLATION_PROVIDER_REGISTRY:
            with self.subTest(engine=engine_key):
                self.assertIn(engine_key, config.AUTH_KEYS)


class TestRegistryMatchesMainloopRouting(unittest.TestCase):
    def test_every_run_mapping_key_is_registered_in_mainloop(self) -> None:
        for engine_key, spec in TRANSLATION_PROVIDER_REGISTRY.items():
            with self.subTest(engine=engine_key):
                self.assertIn(spec.run_mapping_selectable_key, mainloop.run_mapping)
                self.assertIn(spec.run_mapping_selected_key, mainloop.run_mapping)


class TestRegistryClientShape(unittest.TestCase):
    def test_every_client_class_exposes_the_required_methods(self) -> None:
        for engine_key, spec in TRANSLATION_PROVIDER_REGISTRY.items():
            with self.subTest(engine=engine_key):
                for method_name in REQUIRED_CLIENT_METHODS:
                    self.assertTrue(
                        hasattr(spec.client_class, method_name),
                        f"{spec.client_class.__name__} is missing {method_name}()",
                    )

    def test_every_error_code_field_is_an_error_code(self) -> None:
        for engine_key, spec in TRANSLATION_PROVIDER_REGISTRY.items():
            with self.subTest(engine=engine_key):
                self.assertIsInstance(spec.error_auth_invalid, ErrorCode)
                self.assertIsInstance(spec.error_auth_failed, ErrorCode)
                self.assertIsInstance(spec.error_model_invalid, ErrorCode)


class TestAuthValidatePredicates(unittest.TestCase):
    """既存 controller.py の一次検証ロジックと同じ結果になることを確認する。"""

    def test_plamo_requires_at_least_72_chars(self) -> None:
        spec = TRANSLATION_PROVIDER_REGISTRY["Plamo_API"]
        self.assertFalse(spec.auth_validate("a" * 71))
        self.assertTrue(spec.auth_validate("a" * 72))

    def test_gemini_requires_at_least_39_chars(self) -> None:
        spec = TRANSLATION_PROVIDER_REGISTRY["Gemini_API"]
        self.assertFalse(spec.auth_validate("a" * 38))
        self.assertTrue(spec.auth_validate("a" * 39))

    def test_openai_requires_sk_prefix_and_164_chars(self) -> None:
        spec = TRANSLATION_PROVIDER_REGISTRY["OpenAI_API"]
        self.assertFalse(spec.auth_validate("x" * 164))  # 長さは足りるがprefix不一致
        self.assertFalse(spec.auth_validate("sk-" + "a" * 160))  # 164文字未満
        self.assertTrue(spec.auth_validate("sk-" + "a" * 161))  # 164文字ちょうど

    def test_groq_requires_gsk_prefix_and_40_chars(self) -> None:
        spec = TRANSLATION_PROVIDER_REGISTRY["Groq_API"]
        self.assertFalse(spec.auth_validate("x" * 40))
        self.assertFalse(spec.auth_validate("gsk" + "a" * 36))  # 40文字未満
        self.assertTrue(spec.auth_validate("gsk" + "a" * 37))  # 40文字ちょうど

    def test_openrouter_requires_at_least_20_chars(self) -> None:
        spec = TRANSLATION_PROVIDER_REGISTRY["OpenRouter_API"]
        self.assertFalse(spec.auth_validate("a" * 19))
        self.assertTrue(spec.auth_validate("a" * 20))


if __name__ == "__main__":
    unittest.main()
