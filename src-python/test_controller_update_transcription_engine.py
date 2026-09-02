"""Controller.updateTranscriptionEngine() のテスト。

以前は Whisper/Google 以外の SELECTED_TRANSCRIPTION_ENGINE を無条件に
"Whisper" へ巻き戻していた (Groq/OpenAI/カスタムサーバー導入前の実装の
まま残っていたバグ)。これだと新エンジンを選択した直後にこの関数が
呼ばれるたびに意図せず Whisper へ戻ってしまう。
"""

import unittest

from config import config
from controller import Controller


class UpdateTranscriptionEngineApiEnginesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        self._original_engine = config._SELECTED_TRANSCRIPTION_ENGINE
        self._original_status = dict(config._SELECTABLE_TRANSCRIPTION_ENGINE_STATUS)
        self._original_weight_dict = dict(config._SELECTABLE_WHISPER_WEIGHT_TYPE_DICT)

    def tearDown(self) -> None:
        config._SELECTED_TRANSCRIPTION_ENGINE = self._original_engine
        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS = self._original_status
        config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT = self._original_weight_dict

    def test_keeps_api_engine_selected_while_still_available(self) -> None:
        config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT = {}
        config._SELECTED_TRANSCRIPTION_ENGINE = "Groq_Whisper"
        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS = {
            "Google": True, "Whisper": False, "Groq_Whisper": True,
            "OpenAI_Whisper": False, "Custom_Whisper": False,
        }

        self.controller.updateTranscriptionEngine()

        self.assertEqual(config.SELECTED_TRANSCRIPTION_ENGINE, "Groq_Whisper")

    def test_falls_back_to_whisper_when_api_engine_becomes_unavailable(self) -> None:
        config.SELECTABLE_WHISPER_WEIGHT_TYPE_DICT = {}
        config._SELECTED_TRANSCRIPTION_ENGINE = "Groq_Whisper"
        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS = {
            "Google": True, "Whisper": False, "Groq_Whisper": False,
            "OpenAI_Whisper": False, "Custom_Whisper": False,
        }

        self.controller.updateTranscriptionEngine()

        self.assertEqual(config.SELECTED_TRANSCRIPTION_ENGINE, "Whisper")

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


if __name__ == "__main__":
    unittest.main()
