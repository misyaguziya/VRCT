"""models/transcription/transcription_providers.py のテスト。

各プロバイダの「1言語候補に対して1回試行する」契約
(text, confidence, is_definitive) を検証する。実際のネットワーク/SDK
内部通信はテスト対象としない (SDKは信頼する)。VRCT側のテストは
「送信までの処理」(正しいファイル形式・モデル名・パラメータでSDKを
呼び出しているか) と「データ取得後の処理」(レスポンスの解釈・
エラーハンドリング) の2点に絞る。
"""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import requests
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)
from speech_recognition import UnknownValueError

from errors import ErrorCode
from models.transcription.transcription_providers import (
    DeepgramProvider,
    GoogleProvider,
    LocalWhisperProvider,
    OpenAICompatibleTranscriptionProvider,
    TranscriptionApiError,
)


def _segment(text: str, avg_logprob: float = -0.1, no_speech_prob: float = 0.1) -> SimpleNamespace:
    return SimpleNamespace(text=text, avg_logprob=avg_logprob, no_speech_prob=no_speech_prob)


class TestGoogleProvider(unittest.TestCase):
    def test_returns_text_and_confidence_on_success(self) -> None:
        recognizer = MagicMock()
        recognizer.recognize_google.return_value = ("hello", 0.9)
        provider = GoogleProvider(recognizer)

        text, confidence, is_definitive = provider.transcribe(
            MagicMock(), "English", "United States",
            avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=True,
        )

        self.assertEqual(text, "hello")
        self.assertEqual(confidence, 0.9)
        # Google に「検出言語」の概念は無いため、常に False (呼び出し元が
        # 全候補を試行する既存の挙動を維持する)。
        self.assertFalse(is_definitive)
        recognizer.recognize_google.assert_called_once()
        _, kwargs = recognizer.recognize_google.call_args
        self.assertEqual(kwargs["language"], "en-US")

    def test_returns_empty_text_on_unknown_value_error(self) -> None:
        recognizer = MagicMock()
        recognizer.recognize_google.side_effect = UnknownValueError()
        provider = GoogleProvider(recognizer)

        text, confidence, is_definitive = provider.transcribe(
            MagicMock(), "Japanese", "Japan",
            avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=True,
        )

        self.assertEqual(text, "")
        self.assertEqual(confidence, 0.0)
        self.assertFalse(is_definitive)


class TestLocalWhisperProvider(unittest.TestCase):
    def _make_audio_data(self) -> MagicMock:
        audio_data = MagicMock()
        audio_data.get_raw_data.return_value = b"\x00\x00" * 8
        return audio_data

    def test_filters_low_confidence_segments(self) -> None:
        whisper_model = MagicMock()
        whisper_model.transcribe.return_value = (
            [
                _segment("good ", avg_logprob=-0.1, no_speech_prob=0.1),
                _segment("bad ", avg_logprob=-5.0, no_speech_prob=0.1),  # avg_logprob 閾値割れ
            ],
            SimpleNamespace(language="ja", language_probability=0.95),
        )
        provider = LocalWhisperProvider(whisper_model)

        text, confidence, is_definitive = provider.transcribe(
            self._make_audio_data(), "Japanese", "Japan",
            avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=True,
        )

        self.assertEqual(text, "good ")
        self.assertEqual(confidence, 0.95)
        self.assertTrue(is_definitive)  # force_language=True なので常に definitive

    def test_forces_language_only_when_single_candidate(self) -> None:
        whisper_model = MagicMock()
        whisper_model.transcribe.return_value = ([], SimpleNamespace(language="en", language_probability=0.5))
        provider = LocalWhisperProvider(whisper_model)

        provider.transcribe(
            self._make_audio_data(), "English", "United States",
            avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=False,
        )

        _, kwargs = whisper_model.transcribe.call_args
        self.assertIsNone(kwargs["language"])

    def test_is_definitive_when_detected_language_matches_candidate(self) -> None:
        whisper_model = MagicMock()
        whisper_model.transcribe.return_value = (
            [_segment("bonjour")],
            SimpleNamespace(language="fr", language_probability=0.8),
        )
        provider = LocalWhisperProvider(whisper_model)

        _, _, is_definitive = provider.transcribe(
            self._make_audio_data(), "French", "France",
            avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=False,
        )

        self.assertTrue(is_definitive)  # transcription_lang["French"]["France"]["Whisper"] == "fr"

    def test_is_not_definitive_when_detected_language_does_not_match(self) -> None:
        whisper_model = MagicMock()
        whisper_model.transcribe.return_value = (
            [_segment("hola")],
            SimpleNamespace(language="es", language_probability=0.8),
        )
        provider = LocalWhisperProvider(whisper_model)

        _, _, is_definitive = provider.transcribe(
            self._make_audio_data(), "French", "France",
            avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=False,
        )

        self.assertFalse(is_definitive)


class TestOpenAICompatibleTranscriptionProvider(unittest.TestCase):
    def _make_audio_data(self) -> MagicMock:
        audio_data = MagicMock()
        audio_data.get_wav_data.return_value = b"RIFF....WAVEfmt "
        return audio_data

    def _make_provider(self) -> OpenAICompatibleTranscriptionProvider:
        with patch("models.transcription.transcription_providers.OpenAI") as openai_cls:
            provider = OpenAICompatibleTranscriptionProvider(
                api_key="sk-test", base_url="https://api.groq.com/openai/v1",
                model="whisper-large-v3", engine_name="Groq_Whisper",
            )
        provider._client = openai_cls.return_value
        return provider

    def test_calls_sdk_with_wav_bytes_and_model(self) -> None:
        provider = self._make_provider()
        provider._client.audio.transcriptions.create.return_value = SimpleNamespace(
            text="hello", language="en", segments=[_segment("hello")],
        )

        provider.transcribe(
            self._make_audio_data(), "English", "United States",
            avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=True,
        )

        _, kwargs = provider._client.audio.transcriptions.create.call_args
        self.assertEqual(kwargs["model"], "whisper-large-v3")
        self.assertEqual(kwargs["language"], "en")
        filename, data, content_type = kwargs["file"]
        self.assertEqual(filename, "audio.wav")
        self.assertEqual(data, b"RIFF....WAVEfmt ")
        self.assertEqual(content_type, "audio/wav")

    def test_does_not_force_language_with_multiple_candidates(self) -> None:
        provider = self._make_provider()
        provider._client.audio.transcriptions.create.return_value = SimpleNamespace(
            text="hello", language="en", segments=[_segment("hello")],
        )

        provider.transcribe(
            self._make_audio_data(), "English", "United States",
            avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=False,
        )

        _, kwargs = provider._client.audio.transcriptions.create.call_args
        self.assertIsNone(kwargs["language"])

    def test_filters_segments_and_computes_confidence_from_avg_logprob(self) -> None:
        import math

        provider = self._make_provider()
        provider._client.audio.transcriptions.create.return_value = SimpleNamespace(
            text="ignored",
            language="ja",
            segments=[
                _segment("good ", avg_logprob=-0.1),
                _segment("bad ", avg_logprob=-5.0),  # 閾値割れで除外される
            ],
        )

        text, confidence, is_definitive = provider.transcribe(
            self._make_audio_data(), "Japanese", "Japan",
            avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=True,
        )

        self.assertEqual(text, "good ")
        self.assertAlmostEqual(confidence, math.exp(-0.1))
        self.assertTrue(is_definitive)

    def test_falls_back_to_plain_text_when_no_segments_returned(self) -> None:
        # verbose_json 非対応のカスタムサーバー等、segments が無いレスポンス。
        provider = self._make_provider()
        provider._client.audio.transcriptions.create.return_value = SimpleNamespace(
            text="plain text result", language=None, segments=None,
        )

        text, confidence, is_definitive = provider.transcribe(
            self._make_audio_data(), "English", "United States",
            avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=True,
        )

        self.assertEqual(text, "plain text result")
        self.assertEqual(confidence, 0.5)  # segments が無いのでデフォルト値

    def test_no_accepted_text_returns_empty_result(self) -> None:
        provider = self._make_provider()
        provider._client.audio.transcriptions.create.return_value = SimpleNamespace(
            text="", language="en", segments=[],
        )

        text, confidence, is_definitive = provider.transcribe(
            self._make_audio_data(), "English", "United States",
            avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=True,
        )

        self.assertEqual(text, "")
        self.assertEqual(confidence, 0.0)
        self.assertFalse(is_definitive)

    def _request(self) -> httpx.Request:
        return httpx.Request("POST", "https://api.groq.com/openai/v1/audio/transcriptions")

    def test_authentication_error_maps_to_auth_failed_code(self) -> None:
        provider = self._make_provider()
        req = self._request()
        provider._client.audio.transcriptions.create.side_effect = AuthenticationError(
            "invalid key", response=httpx.Response(401, request=req), body=None,
        )

        with patch("models.transcription.transcription_providers.errorLogging"):
            with self.assertRaises(TranscriptionApiError) as ctx:
                provider.transcribe(
                    self._make_audio_data(), "English", "United States",
                    avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=True,
                )
        self.assertEqual(ctx.exception.error_code, ErrorCode.TRANSCRIPTION_API_AUTH_FAILED)

    def test_rate_limit_error_maps_to_rate_limited_code(self) -> None:
        provider = self._make_provider()
        req = self._request()
        provider._client.audio.transcriptions.create.side_effect = RateLimitError(
            "too many requests", response=httpx.Response(429, request=req), body=None,
        )

        with patch("models.transcription.transcription_providers.errorLogging"):
            with self.assertRaises(TranscriptionApiError) as ctx:
                provider.transcribe(
                    self._make_audio_data(), "English", "United States",
                    avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=True,
                )
        self.assertEqual(ctx.exception.error_code, ErrorCode.TRANSCRIPTION_API_RATE_LIMITED)

    def test_timeout_error_maps_to_timeout_code(self) -> None:
        provider = self._make_provider()
        provider._client.audio.transcriptions.create.side_effect = APITimeoutError(request=self._request())

        with patch("models.transcription.transcription_providers.errorLogging"):
            with self.assertRaises(TranscriptionApiError) as ctx:
                provider.transcribe(
                    self._make_audio_data(), "English", "United States",
                    avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=True,
                )
        self.assertEqual(ctx.exception.error_code, ErrorCode.TRANSCRIPTION_API_TIMEOUT)

    def test_server_error_maps_to_server_error_code(self) -> None:
        provider = self._make_provider()
        req = self._request()
        provider._client.audio.transcriptions.create.side_effect = APIStatusError(
            "internal error", response=httpx.Response(500, request=req), body=None,
        )

        with patch("models.transcription.transcription_providers.errorLogging"):
            with self.assertRaises(TranscriptionApiError) as ctx:
                provider.transcribe(
                    self._make_audio_data(), "English", "United States",
                    avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=True,
                )
        self.assertEqual(ctx.exception.error_code, ErrorCode.TRANSCRIPTION_API_SERVER_ERROR)

    def test_connection_error_maps_to_server_error_code(self) -> None:
        provider = self._make_provider()
        provider._client.audio.transcriptions.create.side_effect = APIConnectionError(
            message="connection failed", request=self._request(),
        )

        with patch("models.transcription.transcription_providers.errorLogging"):
            with self.assertRaises(TranscriptionApiError) as ctx:
                provider.transcribe(
                    self._make_audio_data(), "English", "United States",
                    avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=True,
                )
        self.assertEqual(ctx.exception.error_code, ErrorCode.TRANSCRIPTION_API_SERVER_ERROR)


def _make_deepgram_response(status_code=200, payload=None):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload or {}
    return response


class TestDeepgramProvider(unittest.TestCase):
    def _make_audio_data(self) -> MagicMock:
        audio_data = MagicMock()
        audio_data.get_wav_data.return_value = b"RIFF....WAVEfmt "
        return audio_data

    def test_calls_rest_api_with_key_model_and_wav_body(self) -> None:
        provider = DeepgramProvider(api_key="dg-test", model="nova-2")
        response = _make_deepgram_response(200, {
            "results": {"channels": [{"alternatives": [{"transcript": "hello", "confidence": 0.95}]}]},
        })

        with patch("models.transcription.transcription_providers.requests") as mock_requests:
            mock_requests.post.return_value = response
            mock_requests.exceptions = requests.exceptions
            text, confidence, is_definitive = provider.transcribe(
                self._make_audio_data(), "English", "United States",
                avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=True,
            )

        self.assertEqual(text, "hello")
        self.assertEqual(confidence, 0.95)
        self.assertTrue(is_definitive)

        _, kwargs = mock_requests.post.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Token dg-test")
        self.assertEqual(kwargs["headers"]["Content-Type"], "audio/wav")
        self.assertEqual(kwargs["params"]["model"], "nova-2")
        self.assertEqual(kwargs["params"]["detect_language"], "true")
        self.assertEqual(kwargs["data"], b"RIFF....WAVEfmt ")
        # model_languages を渡していない (コンストラクタのデフォルト) ため、
        # 具体的なコードを解決できず自動検出にフォールバックする。
        self.assertNotIn("language", kwargs["params"])

    def test_always_reports_definitive_even_with_multiple_candidates(self) -> None:
        # detect_language=true で1回の呼び出しで済むため、force_language=False
        # (複数候補言語) でも is_definitive=True を返し、呼び出し元に
        # 他候補を試させない。
        provider = DeepgramProvider(api_key="dg-test", model="nova-2")
        response = _make_deepgram_response(200, {
            "results": {"channels": [{"alternatives": [{"transcript": "hello", "confidence": 0.5}]}]},
        })

        with patch("models.transcription.transcription_providers.requests") as mock_requests:
            mock_requests.post.return_value = response
            mock_requests.exceptions = requests.exceptions
            _, _, is_definitive = provider.transcribe(
                self._make_audio_data(), "Japanese", "Japan",
                avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=False,
            )

        self.assertTrue(is_definitive)

    def test_passes_resolved_language_code_when_force_language_and_model_matches(self) -> None:
        # 候補言語が1つに確定していて (force_language=True)、モデルが
        # 対応言語として "en-AU" を申告している場合、detect_language では
        # なく具体的なコードを渡す。
        provider = DeepgramProvider(
            api_key="dg-test", model="nova-2",
            model_languages=["en", "en-AU", "en-GB", "en-US"],
        )
        response = _make_deepgram_response(200, {
            "results": {"channels": [{"alternatives": [{"transcript": "hello", "confidence": 0.95}]}]},
        })

        with patch("models.transcription.transcription_providers.requests") as mock_requests:
            mock_requests.post.return_value = response
            mock_requests.exceptions = requests.exceptions
            provider.transcribe(
                self._make_audio_data(), "English", "Australia",
                avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=True,
            )

        _, kwargs = mock_requests.post.call_args
        self.assertEqual(kwargs["params"]["language"], "en-AU")
        self.assertNotIn("detect_language", kwargs["params"])

    def test_falls_back_to_detect_language_when_model_has_no_matching_code(self) -> None:
        provider = DeepgramProvider(
            api_key="dg-test", model="nova-2",
            model_languages=["ja", "ko"],
        )
        response = _make_deepgram_response(200, {
            "results": {"channels": [{"alternatives": [{"transcript": "hello", "confidence": 0.95}]}]},
        })

        with patch("models.transcription.transcription_providers.requests") as mock_requests:
            mock_requests.post.return_value = response
            mock_requests.exceptions = requests.exceptions
            provider.transcribe(
                self._make_audio_data(), "English", "United States",
                avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=True,
            )

        _, kwargs = mock_requests.post.call_args
        self.assertEqual(kwargs["params"]["detect_language"], "true")
        self.assertNotIn("language", kwargs["params"])

    def test_uses_detect_language_when_multiple_candidates_even_if_model_matches(self) -> None:
        # force_language=False (複数候補言語) の場合、1つの言語に絞れない
        # ため、モデルが対応していても明示コードは渡さず自動検出に任せる。
        provider = DeepgramProvider(
            api_key="dg-test", model="nova-2",
            model_languages=["en", "ja"],
        )
        response = _make_deepgram_response(200, {
            "results": {"channels": [{"alternatives": [{"transcript": "hello", "confidence": 0.95}]}]},
        })

        with patch("models.transcription.transcription_providers.requests") as mock_requests:
            mock_requests.post.return_value = response
            mock_requests.exceptions = requests.exceptions
            provider.transcribe(
                self._make_audio_data(), "Japanese", "Japan",
                avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=False,
            )

        _, kwargs = mock_requests.post.call_args
        self.assertEqual(kwargs["params"]["detect_language"], "true")
        self.assertNotIn("language", kwargs["params"])

    def test_empty_transcript_returns_empty_result(self) -> None:
        provider = DeepgramProvider(api_key="dg-test", model="nova-2")
        response = _make_deepgram_response(200, {
            "results": {"channels": [{"alternatives": [{"transcript": "", "confidence": 0.0}]}]},
        })

        with patch("models.transcription.transcription_providers.requests") as mock_requests:
            mock_requests.post.return_value = response
            mock_requests.exceptions = requests.exceptions
            text, confidence, is_definitive = provider.transcribe(
                self._make_audio_data(), "English", "United States",
                avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=True,
            )

        self.assertEqual(text, "")
        self.assertEqual(confidence, 0.0)
        self.assertFalse(is_definitive)

    def test_malformed_response_shape_returns_empty_result(self) -> None:
        provider = DeepgramProvider(api_key="dg-test", model="nova-2")
        response = _make_deepgram_response(200, {"results": {"channels": []}})

        with patch("models.transcription.transcription_providers.requests") as mock_requests:
            mock_requests.post.return_value = response
            mock_requests.exceptions = requests.exceptions
            text, confidence, is_definitive = provider.transcribe(
                self._make_audio_data(), "English", "United States",
                avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=True,
            )

        self.assertEqual(text, "")
        self.assertEqual(confidence, 0.0)
        self.assertFalse(is_definitive)

    def test_401_maps_to_auth_failed(self) -> None:
        provider = DeepgramProvider(api_key="dg-bad", model="nova-2")
        response = _make_deepgram_response(401, {"err_msg": "invalid key"})

        with patch("models.transcription.transcription_providers.requests") as mock_requests, \
             patch("models.transcription.transcription_providers.errorLogging"):
            mock_requests.post.return_value = response
            mock_requests.exceptions = requests.exceptions
            with self.assertRaises(TranscriptionApiError) as ctx:
                provider.transcribe(
                    self._make_audio_data(), "English", "United States",
                    avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=True,
                )
        self.assertEqual(ctx.exception.error_code, ErrorCode.TRANSCRIPTION_API_AUTH_FAILED)

    def test_429_maps_to_rate_limited(self) -> None:
        provider = DeepgramProvider(api_key="dg-test", model="nova-2")
        response = _make_deepgram_response(429, {"err_msg": "too many requests"})

        with patch("models.transcription.transcription_providers.requests") as mock_requests, \
             patch("models.transcription.transcription_providers.errorLogging"):
            mock_requests.post.return_value = response
            mock_requests.exceptions = requests.exceptions
            with self.assertRaises(TranscriptionApiError) as ctx:
                provider.transcribe(
                    self._make_audio_data(), "English", "United States",
                    avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=True,
                )
        self.assertEqual(ctx.exception.error_code, ErrorCode.TRANSCRIPTION_API_RATE_LIMITED)

    def test_500_maps_to_server_error(self) -> None:
        provider = DeepgramProvider(api_key="dg-test", model="nova-2")
        response = _make_deepgram_response(500, {"err_msg": "internal error"})

        with patch("models.transcription.transcription_providers.requests") as mock_requests, \
             patch("models.transcription.transcription_providers.errorLogging"):
            mock_requests.post.return_value = response
            mock_requests.exceptions = requests.exceptions
            with self.assertRaises(TranscriptionApiError) as ctx:
                provider.transcribe(
                    self._make_audio_data(), "English", "United States",
                    avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=True,
                )
        self.assertEqual(ctx.exception.error_code, ErrorCode.TRANSCRIPTION_API_SERVER_ERROR)

    def test_timeout_maps_to_timeout_code(self) -> None:
        provider = DeepgramProvider(api_key="dg-test", model="nova-2")

        with patch("models.transcription.transcription_providers.requests") as mock_requests, \
             patch("models.transcription.transcription_providers.errorLogging"):
            mock_requests.exceptions = requests.exceptions
            mock_requests.post.side_effect = requests.exceptions.Timeout("timed out")
            with self.assertRaises(TranscriptionApiError) as ctx:
                provider.transcribe(
                    self._make_audio_data(), "English", "United States",
                    avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=True,
                )
        self.assertEqual(ctx.exception.error_code, ErrorCode.TRANSCRIPTION_API_TIMEOUT)

    def test_connection_error_maps_to_server_error(self) -> None:
        provider = DeepgramProvider(api_key="dg-test", model="nova-2")

        with patch("models.transcription.transcription_providers.requests") as mock_requests, \
             patch("models.transcription.transcription_providers.errorLogging"):
            mock_requests.exceptions = requests.exceptions
            mock_requests.post.side_effect = requests.exceptions.ConnectionError("connection failed")
            with self.assertRaises(TranscriptionApiError) as ctx:
                provider.transcribe(
                    self._make_audio_data(), "English", "United States",
                    avg_logprob=-0.8, no_speech_prob=0.6, no_repeat_ngram_size=0, force_language=True,
                )
        self.assertEqual(ctx.exception.error_code, ErrorCode.TRANSCRIPTION_API_SERVER_ERROR)


if __name__ == "__main__":
    unittest.main()
