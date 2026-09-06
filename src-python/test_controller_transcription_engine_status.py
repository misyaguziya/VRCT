"""Controller.init() の "Init Transcription Engine Status" フェーズ
(Groq/OpenAI/カスタムサーバーの認証キー検証・モデル一覧反映) のテスト。

test_controller_init_watchdog_and_join_timeout.py と同じ手法: init() を
実際に (メソッド単位で) 走らせつつ、対象フェーズの直後の呼び出しを
センチネル例外で打ち切って結果だけを検証する。
"""

import unittest
from unittest.mock import patch

from config import config
from controller import Controller


class _Sentinel(Exception):
    """対象フェーズの完了後まで init() が進んだことを示す目印。"""


class TranscriptionEngineStatusInitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        self.controller.startWatchdog = lambda *a, **k: None
        self.controller.connectedNetwork = lambda: None
        self.controller.disconnectedNetwork = lambda: None
        self.controller.enableAiModels = lambda: None
        self.controller.disableAiModels = lambda: None
        self.controller.initializationProgress = lambda *a, **k: None
        # Transcription Engine Status フェーズ完了直後 (Set Translation
        # Engine フェーズの先頭) で打ち切る。
        self.controller.updateDownloadedCTranslate2ModelWeight = lambda: (_ for _ in ()).throw(_Sentinel())

        # 元の config 状態を退避 (テスト間で config はプロセス全体の
        # シングルトンなので、他テストへ影響しないよう必ず戻す)。
        self._original_auth_keys = dict(config._TRANSCRIPTION_AUTH_KEYS)
        self._original_custom_url = config._TRANSCRIPTION_CUSTOM_URL
        self._original_groq_model = config._SELECTED_GROQ_WHISPER_MODEL
        self._original_openai_model = config._SELECTED_OPENAI_WHISPER_MODEL
        self._original_custom_model = config._SELECTED_CUSTOM_WHISPER_MODEL
        self._original_groq_list = list(config._SELECTABLE_GROQ_WHISPER_MODEL_LIST)
        self._original_openai_list = list(config._SELECTABLE_OPENAI_WHISPER_MODEL_LIST)
        self._original_custom_list = list(config._SELECTABLE_CUSTOM_WHISPER_MODEL_LIST)
        self._original_deepgram_list = list(config._SELECTABLE_DEEPGRAM_MODEL_LIST)
        self._original_deepgram_model = config._SELECTED_DEEPGRAM_MODEL
        self._original_deepgram_languages = dict(config._DEEPGRAM_MODEL_LANGUAGES)
        self._original_status = dict(config._SELECTABLE_TRANSCRIPTION_ENGINE_STATUS)
        # controller.init() は途中の "Init Translation Engine Status" も
        # 素通りするため、こちらも副作用で書き換わる。他テストに影響しない
        # よう合わせて退避・復元する。
        self._original_translation_status = dict(config._SELECTABLE_TRANSLATION_ENGINE_STATUS)

        config._TRANSCRIPTION_AUTH_KEYS = {
            "Groq_Whisper": "sk-groq",
            "OpenAI_Whisper": None,
            "Custom_Whisper": "bad-key",
            "Deepgram": "dg-test",
        }
        config._TRANSCRIPTION_CUSTOM_URL = "http://localhost:8000/v1"

    def tearDown(self) -> None:
        config._TRANSCRIPTION_AUTH_KEYS = self._original_auth_keys
        config._TRANSCRIPTION_CUSTOM_URL = self._original_custom_url
        # mutable_tracking=True なプロパティは、`config.X = value` (public
        # setter) 経由でないとキャッシュ済み wrapper が新しい値へ追従せず
        # 次に wrapper 経由で変更が起きた際に古い内容へ巻き戻りうる
        # (config.py の ManagedProperty.__set__ 参照)。プライベート属性への
        # 直接代入では復元しない。
        config.SELECTABLE_GROQ_WHISPER_MODEL_LIST = self._original_groq_list
        config.SELECTABLE_OPENAI_WHISPER_MODEL_LIST = self._original_openai_list
        config.SELECTABLE_CUSTOM_WHISPER_MODEL_LIST = self._original_custom_list
        config.SELECTABLE_DEEPGRAM_MODEL_LIST = self._original_deepgram_list
        config.DEEPGRAM_MODEL_LANGUAGES = self._original_deepgram_languages
        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS = self._original_status
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS = self._original_translation_status
        # allowed=_allowed_in_populated(...) を持つため、上の SELECTABLE_*_LIST
        # 復元より後にプライベート属性へ直接書き戻す (public setter だと
        # 元の選択値が「たまたま今リストに無い」場合に弾かれてしまうため)。
        config._SELECTED_GROQ_WHISPER_MODEL = self._original_groq_model
        config._SELECTED_OPENAI_WHISPER_MODEL = self._original_openai_model
        config._SELECTED_CUSTOM_WHISPER_MODEL = self._original_custom_model
        config._SELECTED_DEEPGRAM_MODEL = self._original_deepgram_model

    def _run_init(self, mock_model) -> None:
        # Controller.__init__ をバイパスしているため、init() 冒頭の
        # _bootstrapModel() (フェーズ3項目22) が使う self._model を手動で
        # 用意する (patch("controller.model") はモジュール属性を差し替える
        # だけで、既に __new__ 済みのインスタンス属性までは遡らない)。
        self.controller._model = mock_model
        mock_model.checkTranslatorCTranslate2ModelWeight.return_value = True
        mock_model.checkTranscriptionWhisperModelWeight.return_value = True

        def fake_auth(api_key=None, base_url=None):
            return api_key == "sk-groq"

        def fake_model_list(api_key=None, base_url=None, keyword_filter=None):
            if api_key == "sk-groq":
                return ["whisper-large-v3", "distil-whisper-large-v3-en"]
            return []

        mock_model.authenticationTranscriptionApiKey.side_effect = fake_auth
        mock_model.getTranscriptionApiModelList.side_effect = fake_model_list
        mock_model.authenticationDeepgramApiKey.return_value = True
        mock_model.getDeepgramModelListDetailed.return_value = [
            {"name": "nova-2", "languages": ["en"]},
            {"name": "nova-3", "languages": ["en", "ja"]},
        ]

        with self.assertRaises(_Sentinel):
            self.controller.init()

    @patch("controller.isConnectedNetwork", return_value=True)
    @patch("controller.model")
    def test_engine_with_valid_key_becomes_available_with_models(self, mock_model, _) -> None:
        self._run_init(mock_model)

        self.assertTrue(config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS["Groq_Whisper"])
        self.assertEqual(
            config.SELECTABLE_GROQ_WHISPER_MODEL_LIST,
            ["whisper-large-v3", "distil-whisper-large-v3-en"],
        )
        self.assertEqual(config.SELECTED_GROQ_WHISPER_MODEL, "whisper-large-v3")

    @patch("controller.isConnectedNetwork", return_value=True)
    @patch("controller.model")
    def test_engine_with_no_key_configured_is_unavailable(self, mock_model, _) -> None:
        self._run_init(mock_model)

        self.assertFalse(config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS["OpenAI_Whisper"])
        self.assertEqual(config.SELECTABLE_OPENAI_WHISPER_MODEL_LIST, [])
        self.assertIsNone(config.SELECTED_OPENAI_WHISPER_MODEL)
        # 未設定 (None) はキーの試行自体が起きないため、無効化(auth_key_invalid)扱いにはならない
        mock_model.authenticationTranscriptionApiKey.assert_any_call(
            api_key="sk-groq", base_url=config.GROQ_WHISPER_BASE_URL
        )

    @patch("controller.isConnectedNetwork", return_value=True)
    @patch("controller.model")
    def test_engine_with_invalid_key_is_cleared_from_config(self, mock_model, _) -> None:
        self._run_init(mock_model)

        self.assertFalse(config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS["Custom_Whisper"])
        self.assertEqual(config.SELECTABLE_CUSTOM_WHISPER_MODEL_LIST, [])
        self.assertIsNone(config.SELECTED_CUSTOM_WHISPER_MODEL)
        # 無効なキーは起動時検証でクリアされる (翻訳エンジンの既存挙動と同じ)
        self.assertIsNone(config.TRANSCRIPTION_AUTH_KEYS["Custom_Whisper"])

    @patch("controller.isConnectedNetwork", return_value=True)
    @patch("controller.model")
    def test_deepgram_with_valid_key_becomes_available_with_models(self, mock_model, _) -> None:
        self._run_init(mock_model)

        self.assertTrue(config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS["Deepgram"])
        self.assertEqual(config.SELECTABLE_DEEPGRAM_MODEL_LIST, ["nova-2", "nova-3"])
        self.assertEqual(config.SELECTED_DEEPGRAM_MODEL, "nova-2")
        self.assertEqual(
            dict(config.DEEPGRAM_MODEL_LANGUAGES),
            {"nova-2": ["en"], "nova-3": ["en", "ja"]},
        )
        mock_model.authenticationDeepgramApiKey.assert_called_once_with(api_key="dg-test")


if __name__ == "__main__":
    unittest.main()
