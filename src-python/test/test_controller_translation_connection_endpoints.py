"""LMStudio/Ollama翻訳エンジンのCRUDエンドポイント (controller.py の
check*Connection, get/setXModel) のテスト。

この2エンジンは認証キーを持たず、疎通確認 (URL指定 または ローカル自動検出)
でモデル一覧を取得する「疎通確認型」であるため、認証キー型5エンジンとは
別のレジストリ (CONNECTION_PROVIDER_REGISTRY) + 別の汎用実装
(Controller._checkTranslationEngineConnection) に載せた (フェーズ3・項目17)。

model (SDK呼び出し境界) はモックし、こちら側の責務である「接続成功/失敗の
分岐」「モデル一覧・選択モデルの config への反映」「接続 SDK 例外時の
専用エラーコードと安全なレスポンス」を検証する。
"""

import unittest
from unittest.mock import patch

from config import config
from controller import Controller
from errors import ErrorCode
from models.translation.translation_providers import CONNECTION_PROVIDER_REGISTRY

_RUN_MAPPING = {
    "selectable_lmstudio_model_list": "/run/selectable_lmstudio_model_list",
    "selected_lmstudio_model": "/run/selected_lmstudio_model",
    "selectable_ollama_model_list": "/run/selectable_ollama_model_list",
    "selected_ollama_model": "/run/selected_ollama_model",
}


class _ConnectionEndpointTestMixin:
    """LMStudio/Ollama共通のテスト本体。`unittest.TestCase` を直接継承しないのは、
    このミックスイン自体が pytest にテストクラスとして収集され
    ENGINE_KEY 等未設定のまま実行されるのを防ぐため。
    """

    ENGINE_KEY: str
    CHECK_METHOD: str
    MODEL_METHOD: str
    MODEL_LIST_ATTR: str
    MODEL_ATTR: str
    AUTHENTICATE_MOCK: str
    GET_MODEL_LIST_MOCK: str
    SET_MODEL_MOCK: str
    UPDATE_CLIENT_MOCK: str
    EXPECTED_CONNECT_KWARGS: dict

    def setUp(self) -> None:
        self._orig_status = dict(config._SELECTABLE_TRANSLATION_ENGINE_STATUS)
        self._orig_model_list = list(getattr(config, f"_{self.MODEL_LIST_ATTR}"))
        self._orig_model = getattr(config, f"_{self.MODEL_ATTR}")
        self.controller = Controller.__new__(Controller)
        self.controller.run_mapping = _RUN_MAPPING
        self.controller.run = lambda *a, **k: None
        self.controller.updateTranslationEngineAndEngineList = lambda: None

    def tearDown(self) -> None:
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS = self._orig_status
        setattr(config, self.MODEL_LIST_ATTR, self._orig_model_list)
        # allowed=_allowed_in_populated(...) を持つため MODEL_LIST_ATTR の
        # 復元より後に private 属性へ直接書き戻す。
        setattr(config, f"_{self.MODEL_ATTR}", self._orig_model)

    def _check_method(self):
        return getattr(self.controller, self.CHECK_METHOD)

    def _model_method(self):
        return getattr(self.controller, self.MODEL_METHOD)

    @patch("controller.model")
    def test_check_connection_success_populates_model_list_and_status(self, mock_model) -> None:
        getattr(mock_model, self.AUTHENTICATE_MOCK).return_value = True
        getattr(mock_model, self.GET_MODEL_LIST_MOCK).return_value = ["fake-model-a"]

        response = self._check_method()()

        self.assertEqual(response, {"status": 200, "result": True})
        self.assertTrue(config.SELECTABLE_TRANSLATION_ENGINE_STATUS[self.ENGINE_KEY])
        self.assertEqual(getattr(config, self.MODEL_LIST_ATTR), ["fake-model-a"])
        self.assertEqual(getattr(config, self.MODEL_ATTR), "fake-model-a")
        getattr(mock_model, self.UPDATE_CLIENT_MOCK).assert_called_once()
        getattr(mock_model, self.AUTHENTICATE_MOCK).assert_called_once_with(**self.EXPECTED_CONNECT_KWARGS)

    @patch("controller.model")
    def test_check_connection_success_but_empty_model_list_resets_everything(self, mock_model) -> None:
        getattr(mock_model, self.AUTHENTICATE_MOCK).return_value = True
        getattr(mock_model, self.GET_MODEL_LIST_MOCK).return_value = []

        response = self._check_method()()

        self.assertEqual(response["status"], 400)
        self.assertEqual(
            response["result"]["error_code"],
            CONNECTION_PROVIDER_REGISTRY[self.ENGINE_KEY].error_connection_failed.value,
        )
        self.assertFalse(config.SELECTABLE_TRANSLATION_ENGINE_STATUS[self.ENGINE_KEY])
        self.assertEqual(getattr(config, self.MODEL_LIST_ATTR), [])
        self.assertIsNone(getattr(config, self.MODEL_ATTR))

    @patch("controller.model")
    def test_check_connection_failure_resets_everything(self, mock_model) -> None:
        getattr(mock_model, self.AUTHENTICATE_MOCK).return_value = False
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS[self.ENGINE_KEY] = True
        setattr(config, self.MODEL_LIST_ATTR, ["stale-model"])
        setattr(config, self.MODEL_ATTR, "stale-model")

        response = self._check_method()()

        self.assertEqual(response["status"], 400)
        self.assertEqual(
            response["result"]["error_code"],
            CONNECTION_PROVIDER_REGISTRY[self.ENGINE_KEY].error_connection_failed.value,
        )
        self.assertFalse(config.SELECTABLE_TRANSLATION_ENGINE_STATUS[self.ENGINE_KEY])
        self.assertEqual(getattr(config, self.MODEL_LIST_ATTR), [])
        self.assertIsNone(getattr(config, self.MODEL_ATTR))
        getattr(mock_model, self.GET_MODEL_LIST_MOCK).assert_not_called()

    @patch("controller.errorLogging")
    @patch("controller.model")
    def test_check_connection_exception_returns_safe_provider_error(
        self, mock_model, mock_error_logging
    ) -> None:
        getattr(mock_model, self.AUTHENTICATE_MOCK).side_effect = RuntimeError(
            "provider response contains a secret"
        )

        response = self._check_method()()

        self.assertEqual(response["status"], 400)
        self.assertEqual(
            response["result"]["error_code"],
            CONNECTION_PROVIDER_REGISTRY[self.ENGINE_KEY].error_connection_failed.value,
        )
        self.assertNotIn("provider response contains a secret", response["result"]["message"])
        mock_error_logging.assert_called_once()
        self.assertFalse(config.SELECTABLE_TRANSLATION_ENGINE_STATUS[self.ENGINE_KEY])

    def test_get_model_returns_config_value(self) -> None:
        setattr(config, self.MODEL_LIST_ATTR, ["fake-model-a"])
        setattr(config, self.MODEL_ATTR, "fake-model-a")

        response = getattr(self.controller, f"get{self.MODEL_METHOD[3:]}")()

        self.assertEqual(response, {"status": 200, "result": "fake-model-a"})

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
        self.assertEqual(
            response["result"]["error_code"],
            CONNECTION_PROVIDER_REGISTRY[self.ENGINE_KEY].error_model_invalid.value,
        )
        self.assertEqual(getattr(config, self.MODEL_ATTR), "fake-model-a")
        getattr(mock_model, self.UPDATE_CLIENT_MOCK).assert_not_called()

    @patch("controller.errorLogging")
    @patch("controller.model")
    def test_set_model_exception_returns_safe_provider_error(self, mock_model, mock_error_logging) -> None:
        setattr(config, self.MODEL_LIST_ATTR, ["fake-model-a"])
        setattr(config, self.MODEL_ATTR, "fake-model-a")
        getattr(mock_model, self.SET_MODEL_MOCK).side_effect = RuntimeError(
            "provider response contains a secret"
        )

        response = self._model_method()("unknown-model")

        self.assertEqual(response["status"], 400)
        self.assertEqual(
            response["result"]["error_code"],
            CONNECTION_PROVIDER_REGISTRY[self.ENGINE_KEY].error_model_invalid.value,
        )
        self.assertNotIn("provider response contains a secret", response["result"]["message"])
        mock_error_logging.assert_called_once()
        self.assertEqual(getattr(config, self.MODEL_ATTR), "fake-model-a")


class LMStudioConnectionEndpointTests(_ConnectionEndpointTestMixin, unittest.TestCase):
    ENGINE_KEY = "LMStudio"
    CHECK_METHOD = "checkTranslatorLMStudioConnection"
    MODEL_METHOD = "setTranslatorLMStudioModel"
    MODEL_LIST_ATTR = "SELECTABLE_LMSTUDIO_MODEL_LIST"
    MODEL_ATTR = "SELECTED_LMSTUDIO_MODEL"
    AUTHENTICATE_MOCK = "authenticationTranslatorLMStudio"
    GET_MODEL_LIST_MOCK = "getTranslatorLMStudioModelList"
    SET_MODEL_MOCK = "setTranslatorLMStudioModel"
    UPDATE_CLIENT_MOCK = "updateTranslatorLMStudioClient"

    def setUp(self) -> None:
        super().setUp()
        self._orig_url = config.LMSTUDIO_URL
        config.LMSTUDIO_URL = "http://localhost:1234/v1"
        self.EXPECTED_CONNECT_KWARGS = {"base_url": config.LMSTUDIO_URL}

    def tearDown(self) -> None:
        config.LMSTUDIO_URL = self._orig_url
        super().tearDown()


class LMStudioUrlEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_url = config.LMSTUDIO_URL
        self._orig_status = dict(config._SELECTABLE_TRANSLATION_ENGINE_STATUS)
        self._orig_model_list = list(config._SELECTABLE_LMSTUDIO_MODEL_LIST)
        self._orig_model = config._SELECTED_LMSTUDIO_MODEL
        self.controller = Controller.__new__(Controller)
        self.controller.run_mapping = _RUN_MAPPING
        self.controller.run = lambda *a, **k: None
        self.controller.updateTranslationEngineAndEngineList = lambda: None

    def tearDown(self) -> None:
        config.LMSTUDIO_URL = self._orig_url
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS = self._orig_status
        config.SELECTABLE_LMSTUDIO_MODEL_LIST = self._orig_model_list
        config._SELECTED_LMSTUDIO_MODEL = self._orig_model

    @patch("controller.model")
    def test_invalid_url_returns_dedicated_error_code(self, mock_model) -> None:
        mock_model.authenticationTranslatorLMStudio.return_value = False

        response = self.controller.setTranslatorLMStudioURL("http://invalid")

        self.assertEqual(response["status"], 400)
        self.assertEqual(
            response["result"]["error_code"],
            ErrorCode.CONNECTION_LMSTUDIO_URL_INVALID.value,
        )

    @patch("controller.errorLogging")
    @patch("controller.model")
    def test_url_exception_returns_safe_dedicated_error_code(
        self, mock_model, mock_error_logging
    ) -> None:
        mock_model.authenticationTranslatorLMStudio.side_effect = RuntimeError(
            "provider response contains a secret"
        )

        response = self.controller.setTranslatorLMStudioURL("http://invalid")

        self.assertEqual(response["status"], 400)
        self.assertEqual(
            response["result"]["error_code"],
            ErrorCode.CONNECTION_LMSTUDIO_URL_INVALID.value,
        )
        self.assertNotIn("provider response contains a secret", response["result"]["message"])
        mock_error_logging.assert_called_once()


class OllamaConnectionEndpointTests(_ConnectionEndpointTestMixin, unittest.TestCase):
    ENGINE_KEY = "Ollama"
    CHECK_METHOD = "checkTranslatorOllamaConnection"
    MODEL_METHOD = "setTranslatorOllamaModel"
    MODEL_LIST_ATTR = "SELECTABLE_OLLAMA_MODEL_LIST"
    MODEL_ATTR = "SELECTED_OLLAMA_MODEL"
    AUTHENTICATE_MOCK = "authenticationTranslatorOllama"
    GET_MODEL_LIST_MOCK = "getTranslatorOllamaModelList"
    SET_MODEL_MOCK = "setTranslatorOllamaModel"
    UPDATE_CLIENT_MOCK = "updateTranslatorOllamaClient"
    EXPECTED_CONNECT_KWARGS = {}


if __name__ == "__main__":
    unittest.main()
