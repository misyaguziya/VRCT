"""Controller.updateTranscriptionEngine() のテスト。

以前は Whisper/Google 以外の SELECTED_TRANSCRIPTION_ENGINE を無条件に
"Whisper" へ巻き戻していた (Groq/OpenAI/カスタムサーバー導入前の実装の
まま残っていたバグ)。これだと新エンジンを選択した直後にこの関数が
呼ばれるたびに意図せず Whisper へ戻ってしまう。

また、エンジンが実際に変化した場合は「文字起こしエンジンが変わるたびに」
選択中の言語を検証し、UIへ最新の言語リストをpushする必要がある
(setSelectedTranslationEngines() -> updateTranslationEngineAndEngineList()
と同じパターン)。呼び出し元ごとに重複させず updateTranscriptionEngine()
一箇所に集約しているため、ここで検証する。
"""

import unittest

from config import config
from controller import Controller


class UpdateTranscriptionEngineApiEnginesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        self.controller.run_mapping = {
            "selectable_language_list": "selectable_language_list",
            "selected_your_languages": "selected_your_languages",
            "selected_target_languages": "selected_target_languages",
        }
        self.calls = []
        self.controller.run = lambda status, endpoint, result: self.calls.append((status, endpoint, result))

        self._original_engine = config._SELECTED_TRANSCRIPTION_ENGINE
        self._original_status = dict(config._SELECTABLE_TRANSCRIPTION_ENGINE_STATUS)
        self._original_weight_dict = dict(config._SELECTABLE_WHISPER_WEIGHT_TYPE_DICT)
        self._original_your_languages = config.SELECTED_YOUR_LANGUAGES
        self._original_target_languages = config.SELECTED_TARGET_LANGUAGES

    def tearDown(self) -> None:
        config._SELECTED_TRANSCRIPTION_ENGINE = self._original_engine
        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS = self._original_status
        config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT = self._original_weight_dict
        config.SELECTED_YOUR_LANGUAGES = self._original_your_languages
        config.SELECTED_TARGET_LANGUAGES = self._original_target_languages

    def test_keeps_api_engine_selected_while_still_available(self) -> None:
        config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT = {}
        config._SELECTED_TRANSCRIPTION_ENGINE = "Groq_Whisper"
        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS = {
            "Google": True, "Whisper": False, "Groq_Whisper": True,
            "OpenAI_Whisper": False, "Custom_Whisper": False,
        }

        self.controller.updateTranscriptionEngine()

        self.assertEqual(config.SELECTED_TRANSCRIPTION_ENGINE, "Groq_Whisper")
        # エンジンは変化していないので、言語リストのpushは起きない
        self.assertEqual(self.calls, [])

    def test_falls_back_to_whisper_when_api_engine_becomes_unavailable(self) -> None:
        config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT = {}
        config._SELECTED_TRANSCRIPTION_ENGINE = "Groq_Whisper"
        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS = {
            "Google": True, "Whisper": False, "Groq_Whisper": False,
            "OpenAI_Whisper": False, "Custom_Whisper": False,
        }

        self.controller.updateTranscriptionEngine()

        self.assertEqual(config.SELECTED_TRANSCRIPTION_ENGINE, "Whisper")
        pushed_endpoints = [endpoint for _, endpoint, _ in self.calls]
        self.assertIn("selectable_language_list", pushed_endpoints)

    def test_google_still_falls_back_to_whisper_when_unavailable(self) -> None:
        # 既存挙動 (Whisper/Google 間のフォールバック) の回帰チェック。
        config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT = {"base": True}
        config._SELECTED_TRANSCRIPTION_ENGINE = "Google"
        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS = {
            "Google": False, "Whisper": True, "Groq_Whisper": False,
            "OpenAI_Whisper": False, "Custom_Whisper": False,
        }

        self.controller.updateTranscriptionEngine()

        self.assertEqual(config.SELECTED_TRANSCRIPTION_ENGINE, "Whisper")

    def test_keeps_deepgram_selected_while_still_available(self) -> None:
        config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT = {}
        config._SELECTED_TRANSCRIPTION_ENGINE = "Deepgram"
        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS = {
            "Google": True, "Whisper": False, "Deepgram": True,
        }

        self.controller.updateTranscriptionEngine()

        self.assertEqual(config.SELECTED_TRANSCRIPTION_ENGINE, "Deepgram")
        self.assertEqual(self.calls, [])

    def test_falls_back_to_whisper_when_deepgram_becomes_unavailable(self) -> None:
        config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT = {}
        config._SELECTED_TRANSCRIPTION_ENGINE = "Deepgram"
        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS = {
            "Google": True, "Whisper": False, "Deepgram": False,
        }

        self.controller.updateTranscriptionEngine()

        self.assertEqual(config.SELECTED_TRANSCRIPTION_ENGINE, "Whisper")
        pushed_endpoints = [endpoint for _, endpoint, _ in self.calls]
        self.assertIn("selectable_language_list", pushed_endpoints)

    def test_requested_engine_is_applied_before_validation(self) -> None:
        """setSelectedTranscriptionEngine() は requested_engine を渡して
        呼び出す (setSelectedTranslationEngines() と同じパターン)。"""
        config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT = {}
        config._SELECTED_TRANSCRIPTION_ENGINE = "Google"
        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS = {
            "Google": True, "Whisper": False, "Deepgram": True,
        }

        self.controller.updateTranscriptionEngine(requested_engine="Deepgram")

        self.assertEqual(config.SELECTED_TRANSCRIPTION_ENGINE, "Deepgram")

    def test_requesting_an_unavailable_engine_falls_back(self) -> None:
        config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT = {}
        config._SELECTED_TRANSCRIPTION_ENGINE = "Google"
        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS = {
            "Google": True, "Whisper": False, "Deepgram": False,
        }

        self.controller.updateTranscriptionEngine(requested_engine="Deepgram")

        self.assertEqual(config.SELECTED_TRANSCRIPTION_ENGINE, "Whisper")

    def test_engine_change_resets_now_unsupported_language_and_pushes_list(self) -> None:
        config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT = {}
        config._SELECTED_TRANSCRIPTION_ENGINE = "Whisper"
        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS = {
            "Google": True, "Whisper": True, "Deepgram": True,
        }
        config.SELECTED_YOUR_LANGUAGES = {
            "1": {"1": {"language": "Korean", "country": "South Korea", "enable": True}},
        }
        # ターゲット側に "Japanese" が有効で入っていると、フォールバック先の
        # 優先候補である日本語が衝突回避のため避けられてしまう
        # (pickDefaultLanguageAndCountryForTranscriptionEngine の衝突回避)。
        # ここでは日本語への復帰だけを検証したいので明示的に避けておく。
        config.SELECTED_TARGET_LANGUAGES = {
            "1": {"1": {"language": "English", "country": "United States", "enable": True}},
        }
        original_deepgram_model = config._SELECTED_DEEPGRAM_MODEL
        original_deepgram_languages = dict(config._DEEPGRAM_MODEL_LANGUAGES)
        config._SELECTED_DEEPGRAM_MODEL = "nova-3"
        config.DEEPGRAM_MODEL_LANGUAGES = {"nova-3": ["en", "ja"]}
        try:
            self.controller.updateTranscriptionEngine(requested_engine="Deepgram")

            self.assertEqual(config.SELECTED_TRANSCRIPTION_ENGINE, "Deepgram")
            self.assertEqual(config.SELECTED_YOUR_LANGUAGES["1"]["1"]["language"], "Japanese")
            pushed_endpoints = [endpoint for _, endpoint, _ in self.calls]
            self.assertIn("selectable_language_list", pushed_endpoints)
            self.assertIn("selected_your_languages", pushed_endpoints)
        finally:
            config._SELECTED_DEEPGRAM_MODEL = original_deepgram_model
            config.DEEPGRAM_MODEL_LANGUAGES = original_deepgram_languages


if __name__ == "__main__":
    unittest.main()
