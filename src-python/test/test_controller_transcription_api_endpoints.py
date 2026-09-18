"""Groq/OpenAI/カスタムサーバー文字起こしエンジンの新規エンドポイント
(controller.py の get/set/delete *WhisperAuthKey, *WhisperModel(List),
Custom Whisper の URL) のテスト。

model (SDK呼び出し境界) はモックし、こちら側の責務である「認証成功/失敗の
分岐」「モデル一覧・選択モデルの config への反映」「無効な入力の
エラーレスポンス」のみを検証する。
"""

import unittest
from unittest.mock import patch

from config import config
from controller import Controller

_RUN_MAPPING = {
    "selectable_groq_whisper_model_list": "/run/selectable_groq_whisper_model_list",
    "selected_groq_whisper_model": "/run/selected_groq_whisper_model",
    "selectable_openai_whisper_model_list": "/run/selectable_openai_whisper_model_list",
    "selected_openai_whisper_model": "/run/selected_openai_whisper_model",
    "selectable_custom_whisper_model_list": "/run/selectable_custom_whisper_model_list",
    "selected_custom_whisper_model": "/run/selected_custom_whisper_model",
    "selectable_deepgram_model_list": "/run/selectable_deepgram_model_list",
    "selected_deepgram_model": "/run/selected_deepgram_model",
}


class _ConfigSnapshotMixin:
    """mutable_tracking=True なプロパティは private 属性への直接代入で
    復元すると、既にキャッシュ済みの wrapper が古い内容のまま残り、
    後で wrapper 経由の変更が起きた際にデータが巻き戻りうる
    (config.py の ManagedProperty.__set__ 参照)。public setter 経由で
    復元することでこれを避ける。
    """

    def _snapshot_config(self) -> None:
        self._orig_auth_keys = dict(config._TRANSCRIPTION_AUTH_KEYS)
        self._orig_custom_url = config._TRANSCRIPTION_CUSTOM_URL
        self._orig_status = dict(config._SELECTABLE_TRANSCRIPTION_ENGINE_STATUS)
        self._orig_groq_list = list(config._SELECTABLE_GROQ_WHISPER_MODEL_LIST)
        self._orig_openai_list = list(config._SELECTABLE_OPENAI_WHISPER_MODEL_LIST)
        self._orig_custom_list = list(config._SELECTABLE_CUSTOM_WHISPER_MODEL_LIST)
        self._orig_deepgram_list = list(config._SELECTABLE_DEEPGRAM_MODEL_LIST)
        self._orig_groq_model = config._SELECTED_GROQ_WHISPER_MODEL
        self._orig_openai_model = config._SELECTED_OPENAI_WHISPER_MODEL
        self._orig_custom_model = config._SELECTED_CUSTOM_WHISPER_MODEL
        self._orig_deepgram_model = config._SELECTED_DEEPGRAM_MODEL

    def _restore_config(self) -> None:
        config.TRANSCRIPTION_AUTH_KEYS = self._orig_auth_keys
        config._TRANSCRIPTION_CUSTOM_URL = self._orig_custom_url
        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS = self._orig_status
        config.SELECTABLE_GROQ_WHISPER_MODEL_LIST = self._orig_groq_list
        config.SELECTABLE_OPENAI_WHISPER_MODEL_LIST = self._orig_openai_list
        config.SELECTABLE_CUSTOM_WHISPER_MODEL_LIST = self._orig_custom_list
        config.SELECTABLE_DEEPGRAM_MODEL_LIST = self._orig_deepgram_list
        # allowed=_allowed_in_populated(...) を持つため SELECTABLE_*_LIST の
        # 復元より後に private 属性へ直接書き戻す。
        config._SELECTED_GROQ_WHISPER_MODEL = self._orig_groq_model
        config._SELECTED_OPENAI_WHISPER_MODEL = self._orig_openai_model
        config._SELECTED_CUSTOM_WHISPER_MODEL = self._orig_custom_model
        config._SELECTED_DEEPGRAM_MODEL = self._orig_deepgram_model


class GroqWhisperAuthKeyEndpointTests(_ConfigSnapshotMixin, unittest.TestCase):
    def setUp(self) -> None:
        self._snapshot_config()
        self.controller = Controller.__new__(Controller)
        self.controller.run_mapping = _RUN_MAPPING
        self.controller.run = lambda *a, **k: None
        self.controller.updateTranscriptionEngine = lambda: None

    def tearDown(self) -> None:
        self._restore_config()

    @patch("controller.model")
    def test_set_auth_key_success_populates_model_list_and_status(self, mock_model) -> None:
        mock_model.authenticationTranscriptionApiKey.return_value = True
        mock_model.getTranscriptionApiModelList.return_value = ["whisper-large-v3"]

        response = self.controller.setGroqWhisperAuthKey("sk-groq")

        self.assertEqual(response["status"], 200)
        self.assertEqual(config.TRANSCRIPTION_AUTH_KEYS["Groq_Whisper"], "sk-groq")
        self.assertTrue(config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS["Groq_Whisper"])
        self.assertEqual(config.SELECTABLE_GROQ_WHISPER_MODEL_LIST, ["whisper-large-v3"])
        self.assertEqual(config.SELECTED_GROQ_WHISPER_MODEL, "whisper-large-v3")

    @patch("controller.model")
    def test_set_auth_key_empty_is_rejected_without_calling_model(self, mock_model) -> None:
        response = self.controller.setGroqWhisperAuthKey("   ")

        self.assertEqual(response["status"], 400)
        mock_model.authenticationTranscriptionApiKey.assert_not_called()

    @patch("controller.model")
    def test_set_auth_key_failure_clears_state(self, mock_model) -> None:
        mock_model.authenticationTranscriptionApiKey.return_value = False

        response = self.controller.setGroqWhisperAuthKey("sk-bad")

        self.assertEqual(response["status"], 400)
        self.assertIsNone(config.TRANSCRIPTION_AUTH_KEYS["Groq_Whisper"])
        self.assertFalse(config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS["Groq_Whisper"])
        self.assertEqual(config.SELECTABLE_GROQ_WHISPER_MODEL_LIST, [])

    @patch("controller.model")
    def test_set_auth_key_with_no_models_is_treated_as_failure(self, mock_model) -> None:
        mock_model.authenticationTranscriptionApiKey.return_value = True
        mock_model.getTranscriptionApiModelList.return_value = []

        response = self.controller.setGroqWhisperAuthKey("sk-groq")

        self.assertEqual(response["status"], 400)
        self.assertIsNone(config.TRANSCRIPTION_AUTH_KEYS["Groq_Whisper"])

    @patch("controller.model")
    def test_del_auth_key_clears_everything(self, mock_model) -> None:
        mock_model.authenticationTranscriptionApiKey.return_value = True
        mock_model.getTranscriptionApiModelList.return_value = ["whisper-large-v3"]
        self.controller.setGroqWhisperAuthKey("sk-groq")

        response = self.controller.delGroqWhisperAuthKey()

        self.assertEqual(response["status"], 200)
        self.assertIsNone(config.TRANSCRIPTION_AUTH_KEYS["Groq_Whisper"])
        self.assertFalse(config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS["Groq_Whisper"])
        self.assertEqual(config.SELECTABLE_GROQ_WHISPER_MODEL_LIST, [])
        self.assertIsNone(config.SELECTED_GROQ_WHISPER_MODEL)

    def test_set_model_accepts_a_listed_model(self) -> None:
        config.SELECTABLE_GROQ_WHISPER_MODEL_LIST = ["whisper-large-v3", "distil-whisper-large-v3-en"]

        response = self.controller.setGroqWhisperModel("distil-whisper-large-v3-en")

        self.assertEqual(response["status"], 200)
        self.assertEqual(config.SELECTED_GROQ_WHISPER_MODEL, "distil-whisper-large-v3-en")

    def test_set_model_rejects_an_unlisted_model(self) -> None:
        config.SELECTABLE_GROQ_WHISPER_MODEL_LIST = ["whisper-large-v3"]

        response = self.controller.setGroqWhisperModel("not-a-real-model")

        self.assertEqual(response["status"], 400)

    def test_getters_reflect_current_config(self) -> None:
        config.TRANSCRIPTION_AUTH_KEYS = {"Groq_Whisper": "sk-groq"}
        config.SELECTABLE_GROQ_WHISPER_MODEL_LIST = ["whisper-large-v3"]
        config._SELECTED_GROQ_WHISPER_MODEL = "whisper-large-v3"

        self.assertEqual(self.controller.getGroqWhisperAuthKey()["result"], "sk-groq")
        self.assertEqual(self.controller.getGroqWhisperModelList()["result"], ["whisper-large-v3"])
        self.assertEqual(self.controller.getGroqWhisperModel()["result"], "whisper-large-v3")


class CustomWhisperURLEndpointTests(_ConfigSnapshotMixin, unittest.TestCase):
    def setUp(self) -> None:
        self._snapshot_config()
        self.controller = Controller.__new__(Controller)
        self.controller.run_mapping = _RUN_MAPPING
        self.controller.run = lambda *a, **k: None
        self.controller.updateTranscriptionEngine = lambda: None

    def tearDown(self) -> None:
        self._restore_config()

    @patch("controller.model")
    def test_set_url_without_auth_key_only_saves_the_url(self, mock_model) -> None:
        config.TRANSCRIPTION_AUTH_KEYS = {"Custom_Whisper": None}

        response = self.controller.setCustomWhisperURL("http://localhost:8000/v1")

        self.assertEqual(response["status"], 200)
        self.assertEqual(config.TRANSCRIPTION_CUSTOM_URL, "http://localhost:8000/v1")
        mock_model.authenticationTranscriptionApiKey.assert_not_called()

    @patch("controller.model")
    def test_set_url_with_auth_key_validates_and_applies(self, mock_model) -> None:
        config.TRANSCRIPTION_AUTH_KEYS = {"Custom_Whisper": "local-secret"}
        mock_model.authenticationTranscriptionApiKey.return_value = True
        mock_model.getTranscriptionApiModelList.return_value = ["whisper"]

        response = self.controller.setCustomWhisperURL("http://localhost:9000/v1")

        self.assertEqual(response["status"], 200)
        self.assertEqual(config.TRANSCRIPTION_CUSTOM_URL, "http://localhost:9000/v1")
        self.assertTrue(config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS["Custom_Whisper"])
        self.assertEqual(config.SELECTABLE_CUSTOM_WHISPER_MODEL_LIST, ["whisper"])
        mock_model.getTranscriptionApiModelList.assert_called_once_with(
            api_key="local-secret", base_url="http://localhost:9000/v1"
        )

    @patch("controller.model")
    def test_set_url_that_fails_auth_keeps_old_url_and_clears_models(self, mock_model) -> None:
        config.TRANSCRIPTION_AUTH_KEYS = {"Custom_Whisper": "local-secret"}
        config.TRANSCRIPTION_CUSTOM_URL = "http://localhost:8000/v1"
        config.SELECTABLE_CUSTOM_WHISPER_MODEL_LIST = ["whisper"]
        mock_model.authenticationTranscriptionApiKey.return_value = False

        response = self.controller.setCustomWhisperURL("http://unreachable:9000/v1")

        self.assertEqual(response["status"], 400)
        self.assertEqual(config.TRANSCRIPTION_CUSTOM_URL, "http://localhost:8000/v1")
        self.assertFalse(config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS["Custom_Whisper"])
        self.assertEqual(config.SELECTABLE_CUSTOM_WHISPER_MODEL_LIST, [])


class DeepgramAuthKeyEndpointTests(_ConfigSnapshotMixin, unittest.TestCase):
    """Deepgramは他3エンジンと違いURLを持たず、認証も `api_key` のみを
    取る (`model.authenticationDeepgramApiKey`/`getDeepgramModelListDetailed`)。
    また対応言語 (`DEEPGRAM_MODEL_LANGUAGES`) もモデル一覧と同時に反映する。"""

    def setUp(self) -> None:
        self._snapshot_config()
        self._orig_languages = dict(config._DEEPGRAM_MODEL_LANGUAGES)
        self.controller = Controller.__new__(Controller)
        self.controller.run_mapping = _RUN_MAPPING
        self.controller.run = lambda *a, **k: None
        self.controller.updateTranscriptionEngine = lambda: None

    def tearDown(self) -> None:
        self._restore_config()
        config.DEEPGRAM_MODEL_LANGUAGES = self._orig_languages

    @patch("controller.model")
    def test_set_auth_key_success_populates_model_list_and_status(self, mock_model) -> None:
        mock_model.authenticationDeepgramApiKey.return_value = True
        mock_model.getDeepgramModelListDetailed.return_value = [
            {"name": "nova-2", "languages": ["en"]},
            {"name": "nova-3", "languages": ["en", "ja"]},
        ]

        response = self.controller.setDeepgramAuthKey("dg-test")

        self.assertEqual(response["status"], 200)
        self.assertEqual(config.TRANSCRIPTION_AUTH_KEYS["Deepgram"], "dg-test")
        self.assertTrue(config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS["Deepgram"])
        self.assertEqual(config.SELECTABLE_DEEPGRAM_MODEL_LIST, ["nova-2", "nova-3"])
        self.assertEqual(config.SELECTED_DEEPGRAM_MODEL, "nova-2")
        self.assertEqual(
            dict(config.DEEPGRAM_MODEL_LANGUAGES),
            {"nova-2": ["en"], "nova-3": ["en", "ja"]},
        )
        mock_model.authenticationDeepgramApiKey.assert_called_once_with(api_key="dg-test")

    @patch("controller.model")
    def test_set_auth_key_empty_is_rejected_without_calling_model(self, mock_model) -> None:
        response = self.controller.setDeepgramAuthKey("   ")

        self.assertEqual(response["status"], 400)
        mock_model.authenticationDeepgramApiKey.assert_not_called()

    @patch("controller.model")
    def test_set_auth_key_failure_clears_state(self, mock_model) -> None:
        mock_model.authenticationDeepgramApiKey.return_value = False

        response = self.controller.setDeepgramAuthKey("dg-bad")

        self.assertEqual(response["status"], 400)
        self.assertIsNone(config.TRANSCRIPTION_AUTH_KEYS["Deepgram"])
        self.assertFalse(config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS["Deepgram"])
        self.assertEqual(config.SELECTABLE_DEEPGRAM_MODEL_LIST, [])

    @patch("controller.model")
    def test_del_auth_key_clears_everything(self, mock_model) -> None:
        mock_model.authenticationDeepgramApiKey.return_value = True
        mock_model.getDeepgramModelListDetailed.return_value = [{"name": "nova-3", "languages": ["en"]}]
        self.controller.setDeepgramAuthKey("dg-test")

        response = self.controller.delDeepgramAuthKey()

        self.assertEqual(response["status"], 200)
        self.assertIsNone(config.TRANSCRIPTION_AUTH_KEYS["Deepgram"])
        self.assertFalse(config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS["Deepgram"])
        self.assertEqual(config.SELECTABLE_DEEPGRAM_MODEL_LIST, [])
        self.assertEqual(dict(config.DEEPGRAM_MODEL_LANGUAGES), {})
        self.assertIsNone(config.SELECTED_DEEPGRAM_MODEL)

    def test_set_model_accepts_a_listed_model(self) -> None:
        config.SELECTABLE_DEEPGRAM_MODEL_LIST = ["nova-2", "nova-3"]

        response = self.controller.setDeepgramModel("nova-3")

        self.assertEqual(response["status"], 200)
        self.assertEqual(config.SELECTED_DEEPGRAM_MODEL, "nova-3")

    def test_set_model_rejects_an_unlisted_model(self) -> None:
        config.SELECTABLE_DEEPGRAM_MODEL_LIST = ["nova-2"]

        response = self.controller.setDeepgramModel("not-a-real-model")

        self.assertEqual(response["status"], 400)

if __name__ == "__main__":
    unittest.main()
