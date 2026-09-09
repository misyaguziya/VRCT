"""文字起こしエンジンを切り替えた際、既に選択されている言語が新しい
エンジンで対応していないまま放置されないことを確認する。

test_controller_translation_engine_language_fallback.py の文字起こし版。
updateTranscriptionEngine() 自体は言語を見ないため、
fallbackUnsupportedLanguagesForTranscriptionEngine() がその役割を担う
(翻訳側の fallbackUnsupportedLanguagesForEngine() のミラー)。

SELECTED_TRANSCRIPTION_ENGINE は SELECTED_TRANSLATION_ENGINES と違い
タブ横断のグローバル設定なので、全タブについて確認する。
"""

import unittest

from controller import Controller, config


class TestFallbackUnsupportedLanguagesForTranscriptionEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        self.controller.run_mapping = {
            "selected_your_languages": "selected_your_languages",
            "selected_target_languages": "selected_target_languages",
            "selectable_language_list": "selectable_language_list",
        }
        self.calls = []
        self.controller.run = lambda status, endpoint, result: self.calls.append((status, endpoint, result))

        self._original_your_languages = config.SELECTED_YOUR_LANGUAGES
        self._original_target_languages = config.SELECTED_TARGET_LANGUAGES
        self._original_deepgram_model = config._SELECTED_DEEPGRAM_MODEL
        self._original_deepgram_languages = dict(config._DEEPGRAM_MODEL_LANGUAGES)

        # nova-3 は英語/日本語のみ対応、という体で固定する。
        config._SELECTED_DEEPGRAM_MODEL = "nova-3"
        config.DEEPGRAM_MODEL_LANGUAGES = {"nova-3": ["en", "ja"]}

    def tearDown(self) -> None:
        config.SELECTED_YOUR_LANGUAGES = self._original_your_languages
        config.SELECTED_TARGET_LANGUAGES = self._original_target_languages
        config._SELECTED_DEEPGRAM_MODEL = self._original_deepgram_model
        config.DEEPGRAM_MODEL_LANGUAGES = self._original_deepgram_languages

    def test_resets_unsupported_source_language_when_switching_to_deepgram(self) -> None:
        config.SELECTED_YOUR_LANGUAGES = {
            "1": {"1": {"language": "Korean", "country": "South Korea", "enable": True}},
        }
        config.SELECTED_TARGET_LANGUAGES = {
            "1": {
                "1": {"language": "English", "country": "United States", "enable": True},
                "2": {"language": "English", "country": "United States", "enable": False},
                "3": {"language": "English", "country": "United States", "enable": False},
            },
        }

        changed = self.controller.fallbackUnsupportedLanguagesForTranscriptionEngine("Deepgram")

        self.assertTrue(changed)
        self.assertEqual(
            config.SELECTED_YOUR_LANGUAGES["1"]["1"],
            {"language": "Japanese", "country": "Japan", "enable": True},
        )
        self.assertTrue(any(endpoint == "selected_your_languages" for _, endpoint, _ in self.calls))

    def test_avoids_colliding_with_an_already_fine_enabled_target(self) -> None:
        config.SELECTED_YOUR_LANGUAGES = {
            "1": {"1": {"language": "Korean", "country": "South Korea", "enable": True}},
        }
        config.SELECTED_TARGET_LANGUAGES = {
            "1": {
                "1": {"language": "Japanese", "country": "Japan", "enable": True},
                "2": {"language": "English", "country": "United States", "enable": False},
                "3": {"language": "English", "country": "United States", "enable": False},
            },
        }

        changed = self.controller.fallbackUnsupportedLanguagesForTranscriptionEngine("Deepgram")

        self.assertTrue(changed)
        self.assertNotEqual(
            config.SELECTED_YOUR_LANGUAGES["1"]["1"]["language"],
            config.SELECTED_TARGET_LANGUAGES["1"]["1"]["language"],
        )
        self.assertEqual(
            config.SELECTED_YOUR_LANGUAGES["1"]["1"],
            {"language": "English", "country": "United States", "enable": True},
        )

    def test_resets_unsupported_enabled_target_language_only(self) -> None:
        config.SELECTED_YOUR_LANGUAGES = {
            "1": {"1": {"language": "Japanese", "country": "Japan", "enable": True}},
        }
        config.SELECTED_TARGET_LANGUAGES = {
            "1": {
                "1": {"language": "Korean", "country": "South Korea", "enable": True},
                "2": {"language": "Korean", "country": "South Korea", "enable": False},  # disabled: must be left alone
                "3": {"language": "English", "country": "United States", "enable": False},
            },
        }

        changed = self.controller.fallbackUnsupportedLanguagesForTranscriptionEngine("Deepgram")

        self.assertTrue(changed)
        self.assertEqual(
            config.SELECTED_TARGET_LANGUAGES["1"]["1"],
            {"language": "English", "country": "United States", "enable": True},
        )
        # disabled slot は触らない
        self.assertEqual(config.SELECTED_TARGET_LANGUAGES["1"]["2"]["language"], "Korean")

    def test_all_tabs_are_checked_since_engine_is_global(self) -> None:
        config.SELECTED_YOUR_LANGUAGES = {
            "1": {"1": {"language": "Japanese", "country": "Japan", "enable": True}},
            "2": {"1": {"language": "Korean", "country": "South Korea", "enable": True}},
        }
        config.SELECTED_TARGET_LANGUAGES = {
            "1": {"1": {"language": "English", "country": "United States", "enable": True}},
            "2": {"1": {"language": "English", "country": "United States", "enable": True}},
        }

        changed = self.controller.fallbackUnsupportedLanguagesForTranscriptionEngine("Deepgram")

        self.assertTrue(changed)
        self.assertEqual(config.SELECTED_YOUR_LANGUAGES["1"]["1"]["language"], "Japanese")
        self.assertNotEqual(config.SELECTED_YOUR_LANGUAGES["2"]["1"]["language"], "Korean")

    def test_no_change_when_all_languages_already_supported(self) -> None:
        config.SELECTED_YOUR_LANGUAGES = {
            "1": {"1": {"language": "Japanese", "country": "Japan", "enable": True}},
        }
        config.SELECTED_TARGET_LANGUAGES = {
            "1": {"1": {"language": "English", "country": "United States", "enable": True}},
        }

        changed = self.controller.fallbackUnsupportedLanguagesForTranscriptionEngine("Deepgram")

        self.assertFalse(changed)
        self.assertEqual(self.calls, [])

    def test_whisper_supports_everything_so_nothing_is_reset(self) -> None:
        config.SELECTED_YOUR_LANGUAGES = {
            "1": {"1": {"language": "Korean", "country": "South Korea", "enable": True}},
        }
        config.SELECTED_TARGET_LANGUAGES = {
            "1": {"1": {"language": "English", "country": "United States", "enable": True}},
        }

        changed = self.controller.fallbackUnsupportedLanguagesForTranscriptionEngine("Whisper")

        self.assertFalse(changed)


class TestSetSelectedTranscriptionEnginePushesLanguageListAndFallback(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        self.controller.run_mapping = {
            "selected_your_languages": "selected_your_languages",
            "selected_target_languages": "selected_target_languages",
            "selectable_language_list": "selectable_language_list",
        }
        self.calls = []
        self.controller.run = lambda status, endpoint, result: self.calls.append((status, endpoint, result))

        self._original_engine = config._SELECTED_TRANSCRIPTION_ENGINE
        self._original_your_languages = config.SELECTED_YOUR_LANGUAGES
        self._original_target_languages = config.SELECTED_TARGET_LANGUAGES
        self._original_deepgram_model = config._SELECTED_DEEPGRAM_MODEL
        self._original_deepgram_languages = dict(config._DEEPGRAM_MODEL_LANGUAGES)
        self._original_status = dict(config._SELECTABLE_TRANSCRIPTION_ENGINE_STATUS)
        config._SELECTED_DEEPGRAM_MODEL = "nova-3"
        config.DEEPGRAM_MODEL_LANGUAGES = {"nova-3": ["en", "ja"]}
        # updateTranscriptionEngine() が可用性チェックで巻き戻さないよう、
        # Whisper/Deepgram の両方を利用可能扱いにしておく。
        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS = {
            "Google": True, "Whisper": True, "Deepgram": True,
        }

    def tearDown(self) -> None:
        config._SELECTED_TRANSCRIPTION_ENGINE = self._original_engine
        config.SELECTED_YOUR_LANGUAGES = self._original_your_languages
        config.SELECTED_TARGET_LANGUAGES = self._original_target_languages
        config._SELECTED_DEEPGRAM_MODEL = self._original_deepgram_model
        config.DEEPGRAM_MODEL_LANGUAGES = self._original_deepgram_languages
        config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS = self._original_status

    def test_switching_to_deepgram_pushes_language_list_and_resets_language(self) -> None:
        config.SELECTED_YOUR_LANGUAGES = {
            "1": {"1": {"language": "Korean", "country": "South Korea", "enable": True}},
        }
        config.SELECTED_TARGET_LANGUAGES = {
            "1": {"1": {"language": "English", "country": "United States", "enable": True}},
        }

        response = self.controller.setSelectedTranscriptionEngine("Deepgram")

        self.assertEqual(response["status"], 200)
        self.assertEqual(config.SELECTED_YOUR_LANGUAGES["1"]["1"]["language"], "Japanese")
        pushed_endpoints = [endpoint for _, endpoint, _ in self.calls]
        self.assertIn("selectable_language_list", pushed_endpoints)
        self.assertIn("selected_your_languages", pushed_endpoints)

    def test_switching_to_whisper_does_not_touch_languages(self) -> None:
        # 実際にエンジンが変化するケースを試すため、起点を明示的に
        # "Whisper" 以外にしておく (でないと変化なし=pushされずテストの
        # 意図が成立しない)。
        config._SELECTED_TRANSCRIPTION_ENGINE = "Google"
        config.SELECTED_YOUR_LANGUAGES = {
            "1": {"1": {"language": "Korean", "country": "South Korea", "enable": True}},
        }

        response = self.controller.setSelectedTranscriptionEngine("Whisper")

        self.assertEqual(response["status"], 200)
        self.assertEqual(config.SELECTED_YOUR_LANGUAGES["1"]["1"]["language"], "Korean")
        pushed_endpoints = [endpoint for _, endpoint, _ in self.calls]
        self.assertIn("selectable_language_list", pushed_endpoints)
        self.assertNotIn("selected_your_languages", pushed_endpoints)


class TestSetDeepgramModelPushesLanguageListOnlyWhenActiveEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        self.controller.run_mapping = {
            "selected_your_languages": "selected_your_languages",
            "selected_target_languages": "selected_target_languages",
            "selectable_language_list": "selectable_language_list",
            "selectable_deepgram_model_list": "selectable_deepgram_model_list",
            "selected_deepgram_model": "selected_deepgram_model",
        }
        self.calls = []
        self.controller.run = lambda status, endpoint, result: self.calls.append((status, endpoint, result))

        self._original_engine = config._SELECTED_TRANSCRIPTION_ENGINE
        self._original_deepgram_model = config._SELECTED_DEEPGRAM_MODEL
        self._original_deepgram_list = list(config._SELECTABLE_DEEPGRAM_MODEL_LIST)
        self._original_deepgram_languages = dict(config._DEEPGRAM_MODEL_LANGUAGES)
        self._original_your_languages = config.SELECTED_YOUR_LANGUAGES
        self._original_target_languages = config.SELECTED_TARGET_LANGUAGES
        config.SELECTABLE_DEEPGRAM_MODEL_LIST = ["nova-2", "nova-3"]
        config.DEEPGRAM_MODEL_LANGUAGES = {"nova-2": ["en"], "nova-3": ["en", "ja"]}
        # ターゲット言語を明示的に無効化しておく (実際の現在値を使うと、
        # 既定で有効な "English" ターゲットとの衝突回避により
        # nova-2 (英語のみ対応) へのフォールバック先候補が無くなってしまう)。
        config.SELECTED_TARGET_LANGUAGES = {
            "1": {"1": {"language": "English", "country": "United States", "enable": False}},
        }

    def tearDown(self) -> None:
        config._SELECTED_TRANSCRIPTION_ENGINE = self._original_engine
        config._SELECTED_DEEPGRAM_MODEL = self._original_deepgram_model
        config.SELECTABLE_DEEPGRAM_MODEL_LIST = self._original_deepgram_list
        config.DEEPGRAM_MODEL_LANGUAGES = self._original_deepgram_languages
        config.SELECTED_YOUR_LANGUAGES = self._original_your_languages
        config.SELECTED_TARGET_LANGUAGES = self._original_target_languages

    def test_pushes_language_list_when_deepgram_is_the_active_engine(self) -> None:
        config._SELECTED_TRANSCRIPTION_ENGINE = "Deepgram"
        config.SELECTED_YOUR_LANGUAGES = {
            "1": {"1": {"language": "Japanese", "country": "Japan", "enable": True}},
        }

        response = self.controller.setDeepgramModel("nova-2")

        self.assertEqual(response["status"], 200)
        pushed_endpoints = [endpoint for _, endpoint, _ in self.calls]
        self.assertIn("selectable_language_list", pushed_endpoints)
        # nova-2 は日本語非対応 -> リセットされる
        self.assertEqual(config.SELECTED_YOUR_LANGUAGES["1"]["1"]["language"], "English")

    def test_does_not_push_when_deepgram_is_not_the_active_engine(self) -> None:
        config._SELECTED_TRANSCRIPTION_ENGINE = "Whisper"
        config.SELECTED_YOUR_LANGUAGES = {
            "1": {"1": {"language": "Japanese", "country": "Japan", "enable": True}},
        }

        response = self.controller.setDeepgramModel("nova-2")

        self.assertEqual(response["status"], 200)
        pushed_endpoints = [endpoint for _, endpoint, _ in self.calls]
        self.assertNotIn("selectable_language_list", pushed_endpoints)
        # 今アクティブなエンジンではないので言語には触らない
        self.assertEqual(config.SELECTED_YOUR_LANGUAGES["1"]["1"]["language"], "Japanese")


if __name__ == "__main__":
    unittest.main()
