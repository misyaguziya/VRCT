"""Groq/OpenAI/カスタムサーバー選択時に、model.py の
`_create_transcriber()` が config から正しい api_key/base_url/api_model を
`AudioTranscriber` へ渡していることを確認する。

AudioTranscriber 自体の挙動 (プロバイダディスパッチ等) は
test_transcription_transcriber.py で検証済みのため、ここでは
「config → AudioTranscriber 呼び出し引数」の配線のみを見る。
"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from model import config, MicSession, SpeakerSession


class TestResolveApiTranscriptionKwargs(unittest.TestCase):
    def setUp(self) -> None:
        self._original_engine = config._SELECTED_TRANSCRIPTION_ENGINE
        self._original_auth_keys = dict(config._TRANSCRIPTION_AUTH_KEYS)
        self._original_custom_url = config._TRANSCRIPTION_CUSTOM_URL
        self._original_groq_model = config._SELECTED_GROQ_WHISPER_MODEL
        self._original_openai_model = config._SELECTED_OPENAI_WHISPER_MODEL
        self._original_custom_model = config._SELECTED_CUSTOM_WHISPER_MODEL
        self._original_deepgram_model = config._SELECTED_DEEPGRAM_MODEL
        # allowed= バリデータは SELECTABLE_*_MODEL_LIST に無い値を弾くため、
        # private 属性へ直接書き込んでバリデーションを迂回する。
        self._original_groq_list = list(config._SELECTABLE_GROQ_WHISPER_MODEL_LIST)
        self._original_openai_list = list(config._SELECTABLE_OPENAI_WHISPER_MODEL_LIST)
        self._original_custom_list = list(config._SELECTABLE_CUSTOM_WHISPER_MODEL_LIST)
        self._original_deepgram_list = list(config._SELECTABLE_DEEPGRAM_MODEL_LIST)
        self._original_deepgram_languages = dict(config._DEEPGRAM_MODEL_LANGUAGES)
        config._SELECTABLE_GROQ_WHISPER_MODEL_LIST = ["whisper-large-v3"]
        config._SELECTABLE_OPENAI_WHISPER_MODEL_LIST = ["whisper-1"]
        config._SELECTABLE_CUSTOM_WHISPER_MODEL_LIST = ["whisper"]
        config._SELECTABLE_DEEPGRAM_MODEL_LIST = ["nova-3"]

    def tearDown(self) -> None:
        config._SELECTED_TRANSCRIPTION_ENGINE = self._original_engine
        config._TRANSCRIPTION_AUTH_KEYS = self._original_auth_keys
        config._TRANSCRIPTION_CUSTOM_URL = self._original_custom_url
        config._SELECTED_GROQ_WHISPER_MODEL = self._original_groq_model
        config._SELECTED_OPENAI_WHISPER_MODEL = self._original_openai_model
        config._SELECTED_CUSTOM_WHISPER_MODEL = self._original_custom_model
        config._SELECTED_DEEPGRAM_MODEL = self._original_deepgram_model
        config._SELECTABLE_GROQ_WHISPER_MODEL_LIST = self._original_groq_list
        config._SELECTABLE_OPENAI_WHISPER_MODEL_LIST = self._original_openai_list
        config._SELECTABLE_CUSTOM_WHISPER_MODEL_LIST = self._original_custom_list
        config._SELECTABLE_DEEPGRAM_MODEL_LIST = self._original_deepgram_list
        config.DEEPGRAM_MODEL_LANGUAGES = self._original_deepgram_languages

    def test_google_returns_empty_kwargs(self) -> None:
        config._SELECTED_TRANSCRIPTION_ENGINE = "Google"

        self.assertEqual(MicSession._resolve_api_transcription_kwargs(), {})

    def test_local_whisper_returns_empty_kwargs(self) -> None:
        config._SELECTED_TRANSCRIPTION_ENGINE = "Whisper"

        self.assertEqual(MicSession._resolve_api_transcription_kwargs(), {})

    def test_groq_whisper_resolves_key_url_and_model(self) -> None:
        config._SELECTED_TRANSCRIPTION_ENGINE = "Groq_Whisper"
        config.TRANSCRIPTION_AUTH_KEYS = {"Groq_Whisper": "sk-groq"}
        config._SELECTED_GROQ_WHISPER_MODEL = "whisper-large-v3"

        result = MicSession._resolve_api_transcription_kwargs()

        self.assertEqual(
            result,
            {
                "api_key": "sk-groq",
                "base_url": config.GROQ_WHISPER_BASE_URL,
                "api_model": "whisper-large-v3",
            },
        )

    def test_openai_whisper_resolves_key_url_and_model(self) -> None:
        config._SELECTED_TRANSCRIPTION_ENGINE = "OpenAI_Whisper"
        config.TRANSCRIPTION_AUTH_KEYS = {"OpenAI_Whisper": "sk-openai"}
        config._SELECTED_OPENAI_WHISPER_MODEL = "whisper-1"

        result = MicSession._resolve_api_transcription_kwargs()

        self.assertEqual(
            result,
            {
                "api_key": "sk-openai",
                "base_url": config.OPENAI_WHISPER_BASE_URL,
                "api_model": "whisper-1",
            },
        )

    def test_custom_whisper_resolves_key_custom_url_and_model(self) -> None:
        config._SELECTED_TRANSCRIPTION_ENGINE = "Custom_Whisper"
        config.TRANSCRIPTION_AUTH_KEYS = {"Custom_Whisper": "local-secret"}
        config._TRANSCRIPTION_CUSTOM_URL = "http://localhost:8000/v1"
        config._SELECTED_CUSTOM_WHISPER_MODEL = "whisper"

        result = MicSession._resolve_api_transcription_kwargs()

        self.assertEqual(
            result,
            {
                "api_key": "local-secret",
                "base_url": "http://localhost:8000/v1",
                "api_model": "whisper",
            },
        )

    def test_deepgram_resolves_key_and_model_without_base_url(self) -> None:
        config._SELECTED_TRANSCRIPTION_ENGINE = "Deepgram"
        config.TRANSCRIPTION_AUTH_KEYS = {"Deepgram": "dg-test"}
        config._SELECTED_DEEPGRAM_MODEL = "nova-3"
        config.DEEPGRAM_MODEL_LANGUAGES = {"nova-3": ["en", "ja"]}

        result = MicSession._resolve_api_transcription_kwargs()

        self.assertEqual(
            result,
            {"api_key": "dg-test", "api_model": "nova-3", "api_model_languages": ["en", "ja"]},
        )


class TestCreateTranscriberPassesApiKwargsThrough(unittest.TestCase):
    """`_create_transcriber()` が `_resolve_api_transcription_kwargs()` の
    結果を実際に `AudioTranscriber(...)` へ渡していることを、Mic/Speaker
    両方について確認する。"""

    def setUp(self) -> None:
        self._original_engine = config._SELECTED_TRANSCRIPTION_ENGINE
        self._original_auth_keys = dict(config._TRANSCRIPTION_AUTH_KEYS)
        self._original_groq_model = config._SELECTED_GROQ_WHISPER_MODEL
        self._original_groq_list = list(config._SELECTABLE_GROQ_WHISPER_MODEL_LIST)
        config._SELECTABLE_GROQ_WHISPER_MODEL_LIST = ["whisper-large-v3"]
        config._SELECTED_TRANSCRIPTION_ENGINE = "Groq_Whisper"
        config.TRANSCRIPTION_AUTH_KEYS = {"Groq_Whisper": "sk-groq"}
        config._SELECTED_GROQ_WHISPER_MODEL = "whisper-large-v3"

    def tearDown(self) -> None:
        config._SELECTED_TRANSCRIPTION_ENGINE = self._original_engine
        config._TRANSCRIPTION_AUTH_KEYS = self._original_auth_keys
        config._SELECTED_GROQ_WHISPER_MODEL = self._original_groq_model
        config._SELECTABLE_GROQ_WHISPER_MODEL_LIST = self._original_groq_list

    @patch("model.AudioTranscriber")
    def test_mic_session_passes_api_kwargs(self, transcriber_cls) -> None:
        session = MicSession()
        session._recorder = SimpleNamespace(SAMPLE_RATE=16000, SAMPLE_WIDTH=2, channels=1)

        session._create_transcriber()

        _, kwargs = transcriber_cls.call_args
        self.assertEqual(kwargs["api_key"], "sk-groq")
        self.assertEqual(kwargs["base_url"], config.GROQ_WHISPER_BASE_URL)
        self.assertEqual(kwargs["api_model"], "whisper-large-v3")

    @patch("model.AudioTranscriber")
    def test_speaker_session_passes_api_kwargs(self, transcriber_cls) -> None:
        session = SpeakerSession()
        session._recorder = SimpleNamespace(SAMPLE_RATE=16000, SAMPLE_WIDTH=2, channels=1)

        session._create_transcriber()

        _, kwargs = transcriber_cls.call_args
        self.assertEqual(kwargs["api_key"], "sk-groq")
        self.assertEqual(kwargs["base_url"], config.GROQ_WHISPER_BASE_URL)
        self.assertEqual(kwargs["api_model"], "whisper-large-v3")


class TestCreateTranscriberPassesDeepgramKwargsThrough(unittest.TestCase):
    def setUp(self) -> None:
        self._original_engine = config._SELECTED_TRANSCRIPTION_ENGINE
        self._original_auth_keys = dict(config._TRANSCRIPTION_AUTH_KEYS)
        self._original_deepgram_model = config._SELECTED_DEEPGRAM_MODEL
        self._original_deepgram_list = list(config._SELECTABLE_DEEPGRAM_MODEL_LIST)
        config._SELECTABLE_DEEPGRAM_MODEL_LIST = ["nova-3"]
        config._SELECTED_TRANSCRIPTION_ENGINE = "Deepgram"
        config.TRANSCRIPTION_AUTH_KEYS = {"Deepgram": "dg-test"}
        config._SELECTED_DEEPGRAM_MODEL = "nova-3"

    def tearDown(self) -> None:
        config._SELECTED_TRANSCRIPTION_ENGINE = self._original_engine
        config._TRANSCRIPTION_AUTH_KEYS = self._original_auth_keys
        config._SELECTED_DEEPGRAM_MODEL = self._original_deepgram_model
        config._SELECTABLE_DEEPGRAM_MODEL_LIST = self._original_deepgram_list

    @patch("model.AudioTranscriber")
    def test_mic_session_passes_api_kwargs_without_base_url(self, transcriber_cls) -> None:
        session = MicSession()
        session._recorder = SimpleNamespace(SAMPLE_RATE=16000, SAMPLE_WIDTH=2, channels=1)

        session._create_transcriber()

        _, kwargs = transcriber_cls.call_args
        self.assertEqual(kwargs["api_key"], "dg-test")
        self.assertEqual(kwargs["api_model"], "nova-3")
        self.assertNotIn("base_url", kwargs)


if __name__ == "__main__":
    unittest.main()
