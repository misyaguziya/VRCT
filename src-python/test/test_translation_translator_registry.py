"""`Translator` の TRANSLATION_PROVIDER_REGISTRY 駆動メソッド
(authenticationRegistryAuthKey/getRegistryModelList/setRegistryModel/
updateRegistryClient) と、それに委譲するようになった Gemini 固有メソッドの
テスト (フェーズ3・項目17)。

実クライアント (GeminiClient等) は実APIへの通信を伴うため、ここでは
一時的なテスト専用エンジンを TRANSLATION_PROVIDER_REGISTRY に登録して
汎用メカニズム自体を検証する。Gemini固有メソッドの委譲は、
`_provider_clients` に直接テストダブルを差し込んで検証する。
"""

import unittest

from errors import ErrorCode
from models.translation.translation_providers import (
    TRANSLATION_PROVIDER_REGISTRY,
    TranslationEngineSpec,
)
from models.translation.translation_translator import Translator


class _FakeRegistryClient:
    """翻訳クライアントの最小限のインターフェースを持つテストダブル。"""

    should_auth_succeed = True

    def __init__(self, root_path=None):
        self.root_path = root_path
        self.auth_key = None
        self.model = None
        self.updated = False

    def setAuthKey(self, api_key):
        self.auth_key = api_key
        return self.should_auth_succeed

    def getAuthKey(self):
        return self.auth_key

    def getModelList(self):
        return ["fake-model-a", "fake-model-b"]

    def getModel(self):
        return self.model

    def setModel(self, model):
        self.model = model
        return True

    def updateClient(self):
        self.updated = True

    def translate(self, text, input_lang, output_lang):
        return f"[{output_lang}] {text}"


class _FailingAuthClient(_FakeRegistryClient):
    should_auth_succeed = False


class TestRegistryDrivenAuthAndModelManagement(unittest.TestCase):
    ENGINE_KEY = "Test_Registry_Engine"

    def setUp(self) -> None:
        self.translator = Translator()
        self._register_spec(_FakeRegistryClient)

    def tearDown(self) -> None:
        TRANSLATION_PROVIDER_REGISTRY.pop(self.ENGINE_KEY, None)

    def _register_spec(self, client_class) -> None:
        TRANSLATION_PROVIDER_REGISTRY[self.ENGINE_KEY] = TranslationEngineSpec(
            engine_key=self.ENGINE_KEY,
            client_class=client_class,
            auth_validate=lambda data: len(data) >= 5,
            error_auth_invalid=ErrorCode.GENERAL_EXCEPTION,
            error_auth_failed=ErrorCode.GENERAL_EXCEPTION,
            error_model_invalid=ErrorCode.GENERAL_EXCEPTION,
            selectable_model_list_attr="_unused",
            selected_model_attr="_unused",
            run_mapping_selectable_key="_unused",
            run_mapping_selected_key="_unused",
        )

    def test_successful_auth_stores_client_and_returns_true(self) -> None:
        result = self.translator.authenticationRegistryAuthKey(self.ENGINE_KEY, "valid-key")

        self.assertTrue(result)
        self.assertIn(self.ENGINE_KEY, self.translator._provider_clients)

    def test_failed_auth_does_not_store_client_and_returns_false(self) -> None:
        self._register_spec(_FailingAuthClient)

        result = self.translator.authenticationRegistryAuthKey(self.ENGINE_KEY, "valid-key")

        self.assertFalse(result)
        self.assertNotIn(self.ENGINE_KEY, self.translator._provider_clients)

    def test_get_model_list_returns_empty_when_not_authenticated(self) -> None:
        self.assertEqual(self.translator.getRegistryModelList(self.ENGINE_KEY), [])

    def test_get_model_list_delegates_to_client_after_auth(self) -> None:
        self.translator.authenticationRegistryAuthKey(self.ENGINE_KEY, "valid-key")

        self.assertEqual(
            self.translator.getRegistryModelList(self.ENGINE_KEY),
            ["fake-model-a", "fake-model-b"],
        )

    def test_set_model_returns_false_when_not_authenticated(self) -> None:
        self.assertFalse(self.translator.setRegistryModel(self.ENGINE_KEY, "fake-model-a"))

    def test_set_model_delegates_to_client_after_auth(self) -> None:
        self.translator.authenticationRegistryAuthKey(self.ENGINE_KEY, "valid-key")

        self.assertTrue(self.translator.setRegistryModel(self.ENGINE_KEY, "fake-model-a"))

    def test_update_client_is_a_noop_when_not_authenticated(self) -> None:
        self.translator.updateRegistryClient(self.ENGINE_KEY)  # should not raise

    def test_update_client_delegates_to_client_after_auth(self) -> None:
        self.translator.authenticationRegistryAuthKey(self.ENGINE_KEY, "valid-key")

        self.translator.updateRegistryClient(self.ENGINE_KEY)

        client = self.translator._provider_clients[self.ENGINE_KEY]
        self.assertTrue(client.updated)


class TestGeminiMethodsDelegateToRegistry(unittest.TestCase):
    """Gemini固有メソッドが引き続き `_provider_clients` 経由で動作することを確認する。"""

    def test_gemini_methods_operate_through_the_shared_client_dict(self) -> None:
        translator = Translator()
        fake_client = _FakeRegistryClient()
        translator._provider_clients["Gemini_API"] = fake_client

        self.assertEqual(translator.getGeminiModelList(), ["fake-model-a", "fake-model-b"])
        self.assertTrue(translator.setGeminiModel("fake-model-a"))
        translator.updateGeminiClient()
        self.assertTrue(fake_client.updated)

    def test_gemini_model_list_is_empty_before_authentication(self) -> None:
        translator = Translator()

        self.assertEqual(translator.getGeminiModelList(), [])
        self.assertFalse(translator.setGeminiModel("anything"))


if __name__ == "__main__":
    unittest.main()
