"""Gemini翻訳エンジンのCRUDエンドポイント (controller.py の
get/set/delGeminiAuthKey, getGeminiModelList, get/setGeminiModel) のテスト。

これらはフェーズ3・項目17 (TranslationProviderレジストリ) のパイロットとして
Controller._getTranslationEngineAuthKey 等の共通実装への1行委譲に置き換えた。
このテストは「委譲後も既存の挙動 (config反映・run()によるpush・
エラーレスポンス) が変わっていないこと」と「_ENGINE_MODEL_BINDINGS が
`controller.model` パッチ経由でも正しくモックに届くこと」を検証する。

model (SDK呼び出し境界) はモックし、こちら側の責務である「認証成功/失敗の
分岐」「モデル一覧・選択モデルの config への反映」「無効な入力の
エラーレスポンス」のみを検証する (test_controller_transcription_api_endpoints.py
と同じ方針)。
"""

import unittest
from unittest.mock import patch

from config import config
from controller import Controller

_RUN_MAPPING = {
    "selectable_gemini_model_list": "/run/selectable_gemini_model_list",
    "selected_gemini_model": "/run/selected_gemini_model",
}


class _ConfigSnapshotMixin:
    """mutable_tracking=True なプロパティは private 属性への直接代入で
    復元すると、既にキャッシュ済みの wrapper が古い内容のまま残り、
    後で wrapper 経由の変更が起きた際にデータが巻き戻りうる
    (config.py の ManagedProperty.__set__ 参照)。public setter 経由で
    復元することでこれを避ける。
    """

    def _snapshot_config(self) -> None:
        self._orig_auth_keys = dict(config.AUTH_KEYS)
        self._orig_status = dict(config._SELECTABLE_TRANSLATION_ENGINE_STATUS)
        self._orig_model_list = list(config._SELECTABLE_GEMINI_MODEL_LIST)
        self._orig_model = config._SELECTED_GEMINI_MODEL

    def _restore_config(self) -> None:
        config.AUTH_KEYS = self._orig_auth_keys
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS = self._orig_status
        config.SELECTABLE_GEMINI_MODEL_LIST = self._orig_model_list
        # allowed=_allowed_in_populated(...) を持つため SELECTABLE_*_LIST の
        # 復元より後に private 属性へ直接書き戻す。
        config._SELECTED_GEMINI_MODEL = self._orig_model


class GeminiAuthKeyEndpointTests(_ConfigSnapshotMixin, unittest.TestCase):
    def setUp(self) -> None:
        self._snapshot_config()
        self.controller = Controller.__new__(Controller)
        self.controller.run_mapping = _RUN_MAPPING
        self.controller.run = lambda *a, **k: None
        self.controller.updateTranslationEngineAndEngineList = lambda: None

    def tearDown(self) -> None:
        self._restore_config()

    @patch("controller.model")
    def test_set_auth_key_success_populates_model_list_and_status(self, mock_model) -> None:
        mock_model.authenticationTranslatorGeminiAuthKey.return_value = True
        mock_model.getTranslatorGeminiModelList.return_value = ["gemini-2.5-flash"]

        response = self.controller.setGeminiAuthKey("a" * 39)

        self.assertEqual(response["status"], 200)
        self.assertEqual(config.AUTH_KEYS["Gemini_API"], "a" * 39)
        self.assertTrue(config.SELECTABLE_TRANSLATION_ENGINE_STATUS["Gemini_API"])
        self.assertEqual(config.SELECTABLE_GEMINI_MODEL_LIST, ["gemini-2.5-flash"])
        self.assertEqual(config.SELECTED_GEMINI_MODEL, "gemini-2.5-flash")
        mock_model.updateTranslatorGeminiClient.assert_called_once()

    @patch("controller.model")
    def test_set_auth_key_too_short_is_rejected_without_calling_model(self, mock_model) -> None:
        response = self.controller.setGeminiAuthKey("a" * 38)

        self.assertEqual(response["status"], 400)
        mock_model.authenticationTranslatorGeminiAuthKey.assert_not_called()
        self.assertIsNone(config.AUTH_KEYS["Gemini_API"])

    @patch("controller.model")
    def test_set_auth_key_auth_failure_clears_key_via_del(self, mock_model) -> None:
        mock_model.authenticationTranslatorGeminiAuthKey.return_value = False

        response = self.controller.setGeminiAuthKey("a" * 39)

        self.assertEqual(response["status"], 400)
        self.assertIsNone(config.AUTH_KEYS["Gemini_API"])
        self.assertFalse(config.SELECTABLE_TRANSLATION_ENGINE_STATUS["Gemini_API"])

    @patch("controller.model")
    def test_get_auth_key_returns_current_value(self, mock_model) -> None:
        config.AUTH_KEYS = {**config.AUTH_KEYS, "Gemini_API": "existing-key"}

        response = self.controller.getGeminiAuthKey()

        self.assertEqual(response, {"status": 200, "result": "existing-key"})

    @patch("controller.model")
    def test_del_auth_key_resets_everything(self, mock_model) -> None:
        config.AUTH_KEYS = {**config.AUTH_KEYS, "Gemini_API": "existing-key"}
        config.SELECTABLE_GEMINI_MODEL_LIST = ["gemini-2.5-flash"]
        config.SELECTED_GEMINI_MODEL = "gemini-2.5-flash"
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS["Gemini_API"] = True

        response = self.controller.delGeminiAuthKey()

        self.assertEqual(response, {"status": 200, "result": None})
        self.assertIsNone(config.AUTH_KEYS["Gemini_API"])
        self.assertEqual(config.SELECTABLE_GEMINI_MODEL_LIST, [])
        self.assertIsNone(config.SELECTED_GEMINI_MODEL)
        self.assertFalse(config.SELECTABLE_TRANSLATION_ENGINE_STATUS["Gemini_API"])


class GeminiModelEndpointTests(_ConfigSnapshotMixin, unittest.TestCase):
    def setUp(self) -> None:
        self._snapshot_config()
        self.controller = Controller.__new__(Controller)
        self.controller.run_mapping = _RUN_MAPPING
        self.controller.run = lambda *a, **k: None
        config.SELECTABLE_GEMINI_MODEL_LIST = ["gemini-2.5-flash", "gemini-2.5-pro"]

    def tearDown(self) -> None:
        self._restore_config()

    def test_get_model_list_returns_config_value(self) -> None:
        response = self.controller.getGeminiModelList()

        self.assertEqual(response, {"status": 200, "result": ["gemini-2.5-flash", "gemini-2.5-pro"]})

    def test_get_model_returns_config_value(self) -> None:
        config.SELECTED_GEMINI_MODEL = "gemini-2.5-pro"

        response = self.controller.getGeminiModel()

        self.assertEqual(response, {"status": 200, "result": "gemini-2.5-pro"})

    @patch("controller.model")
    def test_set_model_success_updates_config_and_calls_update_client(self, mock_model) -> None:
        mock_model.setTranslatorGeminiModel.return_value = True

        response = self.controller.setGeminiModel("gemini-2.5-pro")

        self.assertEqual(response, {"status": 200, "result": "gemini-2.5-pro"})
        self.assertEqual(config.SELECTED_GEMINI_MODEL, "gemini-2.5-pro")
        mock_model.updateTranslatorGeminiClient.assert_called_once()

    @patch("controller.model")
    def test_set_model_failure_returns_error_response_without_changing_config(self, mock_model) -> None:
        mock_model.setTranslatorGeminiModel.return_value = False
        config.SELECTED_GEMINI_MODEL = "gemini-2.5-flash"

        response = self.controller.setGeminiModel("unknown-model")

        self.assertEqual(response["status"], 400)
        self.assertEqual(config.SELECTED_GEMINI_MODEL, "gemini-2.5-flash")
        mock_model.updateTranslatorGeminiClient.assert_not_called()


if __name__ == "__main__":
    unittest.main()
