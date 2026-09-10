"""Plamo/OpenAI/Groq/OpenRouter翻訳エンジンのCRUDエンドポイント
(controller.py の get/set/delXAuthKey, getXModelList, get/setXModel) のテスト。

Geminiパイロット (test_controller_translation_gemini_endpoint.py) で実証した
TRANSLATION_PROVIDER_REGISTRY駆動の共通実装 (Controller._getTranslationEngineAuthKey
等) に、この4エンジンを一括で載せた (フェーズ3・項目17)。

model (SDK呼び出し境界) はモックし、こちら側の責務である「認証成功/失敗の
分岐」「モデル一覧・選択モデルの config への反映」「無効な入力の
エラーレスポンス」のみを検証する。
"""

import unittest
from unittest.mock import patch

from config import config
from controller import Controller

_RUN_MAPPING = {
    "selectable_plamo_model_list": "/run/selectable_plamo_model_list",
    "selected_plamo_model": "/run/selected_plamo_model",
    "selectable_openai_model_list": "/run/selectable_openai_model_list",
    "selected_openai_model": "/run/selected_openai_model",
    "selectable_groq_model_list": "/run/selectable_groq_model_list",
    "selected_groq_model": "/run/selected_groq_model",
    "selectable_openrouter_model_list": "/run/selectable_openrouter_model_list",
    "selected_openrouter_model": "/run/selected_openrouter_model",
}


class _RegistryEndpointTestMixin:
    """4エンジン共通のテスト本体。サブクラスで `unittest.TestCase` と多重継承し
    ENGINE_* を上書きして使う (`unittest.TestCase` を直接継承しないのは、
    このミックスイン自体が pytest にテストクラスとして収集され
    ENGINE_KEY 等未設定のまま実行されるのを防ぐため)。

    mutable_tracking=True なプロパティは private 属性への直接代入で復元すると、
    既にキャッシュ済みの wrapper が古い内容のまま残る (config.py の
    ManagedProperty.__set__ 参照) ため、public setter 経由で復元する。
    """

    ENGINE_KEY: str
    AUTH_METHOD: str  # controller.<AUTH_METHOD>
    MODEL_METHOD: str  # controller.<MODEL_METHOD>
    MODEL_LIST_ATTR: str  # config.SELECTABLE_*_MODEL_LIST
    MODEL_ATTR: str  # config.SELECTED_*_MODEL
    VALID_KEY: str  # auth_validate を満たすサンプルキー
    INVALID_KEY: str  # auth_validate を満たさないサンプルキー
    AUTHENTICATE_MOCK: str  # model.<...AuthKey> のメソッド名
    GET_MODEL_LIST_MOCK: str  # model.getTranslator...ModelList のメソッド名
    SET_MODEL_MOCK: str  # model.setTranslator...Model のメソッド名
    UPDATE_CLIENT_MOCK: str  # model.updateTranslator...Client のメソッド名

    def setUp(self) -> None:
        self._orig_auth_keys = dict(config.AUTH_KEYS)
        self._orig_status = dict(config._SELECTABLE_TRANSLATION_ENGINE_STATUS)
        self._orig_model_list = list(getattr(config, f"_{self.MODEL_LIST_ATTR}"))
        self._orig_model = getattr(config, f"_{self.MODEL_ATTR}")
        self.controller = Controller.__new__(Controller)
        self.controller.run_mapping = _RUN_MAPPING
        self.controller.run = lambda *a, **k: None
        self.controller.updateTranslationEngineAndEngineList = lambda: None

    def tearDown(self) -> None:
        config.AUTH_KEYS = self._orig_auth_keys
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS = self._orig_status
        setattr(config, self.MODEL_LIST_ATTR, self._orig_model_list)
        # allowed=_allowed_in_populated(...) を持つため MODEL_LIST_ATTR の
        # 復元より後に private 属性へ直接書き戻す。
        setattr(config, f"_{self.MODEL_ATTR}", self._orig_model)

    def _auth_method(self):
        return getattr(self.controller, self.AUTH_METHOD)

    def _model_method(self):
        return getattr(self.controller, self.MODEL_METHOD)

    @patch("controller.model")
    def test_set_auth_key_success_populates_model_list_and_status(self, mock_model) -> None:
        getattr(mock_model, self.AUTHENTICATE_MOCK).return_value = True
        getattr(mock_model, self.GET_MODEL_LIST_MOCK).return_value = ["fake-model-a"]

        response = self._auth_method()(self.VALID_KEY)

        self.assertEqual(response["status"], 200)
        self.assertEqual(config.AUTH_KEYS[self.ENGINE_KEY], self.VALID_KEY)
        self.assertTrue(config.SELECTABLE_TRANSLATION_ENGINE_STATUS[self.ENGINE_KEY])
        self.assertEqual(getattr(config, self.MODEL_LIST_ATTR), ["fake-model-a"])
        self.assertEqual(getattr(config, self.MODEL_ATTR), "fake-model-a")
        getattr(mock_model, self.UPDATE_CLIENT_MOCK).assert_called_once()

    @patch("controller.model")
    def test_set_auth_key_format_invalid_is_rejected_without_calling_model(self, mock_model) -> None:
        response = self._auth_method()(self.INVALID_KEY)

        self.assertEqual(response["status"], 400)
        getattr(mock_model, self.AUTHENTICATE_MOCK).assert_not_called()
        self.assertIsNone(config.AUTH_KEYS[self.ENGINE_KEY])

    @patch("controller.model")
    def test_set_auth_key_auth_failure_clears_key_via_del(self, mock_model) -> None:
        getattr(mock_model, self.AUTHENTICATE_MOCK).return_value = False

        response = self._auth_method()(self.VALID_KEY)

        self.assertEqual(response["status"], 400)
        self.assertIsNone(config.AUTH_KEYS[self.ENGINE_KEY])
        self.assertFalse(config.SELECTABLE_TRANSLATION_ENGINE_STATUS[self.ENGINE_KEY])

    @patch("controller.model")
    def test_set_model_success_updates_config_and_calls_update_client(self, mock_model) -> None:
        setattr(config, self.MODEL_LIST_ATTR, ["fake-model-a", "fake-model-b"])
        getattr(mock_model, self.SET_MODEL_MOCK).return_value = True

        response = self._model_method()("fake-model-b")

        self.assertEqual(response, {"status": 200, "result": "fake-model-b"})
        self.assertEqual(getattr(config, self.MODEL_ATTR), "fake-model-b")
        getattr(mock_model, self.UPDATE_CLIENT_MOCK).assert_called_once()

    @patch("controller.model")
    def test_set_model_failure_returns_error_response_without_changing_config(self, mock_model) -> None:
        setattr(config, self.MODEL_LIST_ATTR, ["fake-model-a"])
        setattr(config, self.MODEL_ATTR, "fake-model-a")
        getattr(mock_model, self.SET_MODEL_MOCK).return_value = False

        response = self._model_method()("unknown-model")

        self.assertEqual(response["status"], 400)
        self.assertEqual(getattr(config, self.MODEL_ATTR), "fake-model-a")
        getattr(mock_model, self.UPDATE_CLIENT_MOCK).assert_not_called()


class PlamoEndpointTests(_RegistryEndpointTestMixin, unittest.TestCase):
    ENGINE_KEY = "Plamo_API"
    AUTH_METHOD = "setPlamoAuthKey"
    MODEL_METHOD = "setPlamoModel"
    MODEL_LIST_ATTR = "SELECTABLE_PLAMO_MODEL_LIST"
    MODEL_ATTR = "SELECTED_PLAMO_MODEL"
    VALID_KEY = "a" * 72
    INVALID_KEY = "a" * 71
    AUTHENTICATE_MOCK = "authenticationTranslatorPlamoAuthKey"
    GET_MODEL_LIST_MOCK = "getTranslatorPlamoModelList"
    SET_MODEL_MOCK = "setTranslatorPlamoModel"
    UPDATE_CLIENT_MOCK = "updateTranslatorPlamoClient"


class OpenAIEndpointTests(_RegistryEndpointTestMixin, unittest.TestCase):
    ENGINE_KEY = "OpenAI_API"
    AUTH_METHOD = "setOpenAIAuthKey"
    MODEL_METHOD = "setOpenAIModel"
    MODEL_LIST_ATTR = "SELECTABLE_OPENAI_MODEL_LIST"
    MODEL_ATTR = "SELECTED_OPENAI_MODEL"
    VALID_KEY = "sk-" + "a" * 161
    INVALID_KEY = "sk-" + "a" * 160
    AUTHENTICATE_MOCK = "authenticationTranslatorOpenAIAuthKey"
    GET_MODEL_LIST_MOCK = "getTranslatorOpenAIModelList"
    SET_MODEL_MOCK = "setTranslatorOpenAIModel"
    UPDATE_CLIENT_MOCK = "updateTranslatorOpenAIClient"


class GroqEndpointTests(_RegistryEndpointTestMixin, unittest.TestCase):
    ENGINE_KEY = "Groq_API"
    AUTH_METHOD = "setGroqAuthKey"
    MODEL_METHOD = "setGroqModel"
    MODEL_LIST_ATTR = "SELECTABLE_GROQ_MODEL_LIST"
    MODEL_ATTR = "SELECTED_GROQ_MODEL"
    VALID_KEY = "gsk" + "a" * 37
    INVALID_KEY = "gsk" + "a" * 36
    AUTHENTICATE_MOCK = "authenticationTranslatorGroqAuthKey"
    GET_MODEL_LIST_MOCK = "getTranslatorGroqModelList"
    SET_MODEL_MOCK = "setTranslatorGroqModel"
    UPDATE_CLIENT_MOCK = "updateTranslatorGroqClient"


class OpenRouterEndpointTests(_RegistryEndpointTestMixin, unittest.TestCase):
    ENGINE_KEY = "OpenRouter_API"
    AUTH_METHOD = "setOpenRouterAuthKey"
    MODEL_METHOD = "setOpenRouterModel"
    MODEL_LIST_ATTR = "SELECTABLE_OPENROUTER_MODEL_LIST"
    MODEL_ATTR = "SELECTED_OPENROUTER_MODEL"
    VALID_KEY = "a" * 20
    INVALID_KEY = "a" * 19
    AUTHENTICATE_MOCK = "authenticationTranslatorOpenRouterAuthKey"
    GET_MODEL_LIST_MOCK = "getTranslatorOpenRouterModelList"
    SET_MODEL_MOCK = "setTranslatorOpenRouterModel"
    UPDATE_CLIENT_MOCK = "updateTranslatorOpenRouterClient"


if __name__ == "__main__":
    unittest.main()
