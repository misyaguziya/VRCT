"""models/transcription/transcription_deepgram.py のテスト。

`requests` (実際のHTTP通信) はモックし、こちら側の責務である
「/v1/models の成否でキーの有効性を判定する」「stt[].batch=True のみに
絞り込む」の2点のみを検証する。
"""

import unittest
from unittest.mock import MagicMock, patch

from models.transcription.transcription_deepgram import (
    checkDeepgramApiKey,
    getAvailableDeepgramModels,
    getAvailableDeepgramModelsDetailed,
    getDeepgramSupportedLanguages,
    isLanguageSupportedByDeepgramModel,
)


def _make_response(status_code=200, payload=None):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload or {}
    if status_code >= 400:
        response.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    else:
        response.raise_for_status.return_value = None
    return response


class TestCheckDeepgramApiKey(unittest.TestCase):
    @patch("models.transcription.transcription_deepgram.requests")
    def test_returns_true_on_200(self, mock_requests) -> None:
        mock_requests.get.return_value = _make_response(200)

        result = checkDeepgramApiKey("dg-test")

        self.assertTrue(result)
        _, kwargs = mock_requests.get.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Token dg-test")

    @patch("models.transcription.transcription_deepgram.requests")
    def test_returns_false_on_401(self, mock_requests) -> None:
        mock_requests.get.return_value = _make_response(401)

        result = checkDeepgramApiKey("dg-bad")

        self.assertFalse(result)

    @patch("models.transcription.transcription_deepgram.requests")
    def test_returns_false_when_request_raises(self, mock_requests) -> None:
        mock_requests.get.side_effect = Exception("connection failed")

        result = checkDeepgramApiKey("dg-test")

        self.assertFalse(result)


class TestGetAvailableDeepgramModels(unittest.TestCase):
    @patch("models.transcription.transcription_deepgram.requests")
    def test_keeps_only_batch_capable_stt_models(self, mock_requests) -> None:
        mock_requests.get.return_value = _make_response(200, {
            "stt": [
                {"name": "nova-3", "batch": True, "streaming": True},
                {"name": "nova-3-streaming-only", "batch": False, "streaming": True},
                {"name": "whisper-cloud", "batch": True, "streaming": False},
            ],
            "tts": [{"name": "aura-asteria-en"}],
        })

        result = getAvailableDeepgramModels("dg-test")

        self.assertEqual(result, ["nova-3", "whisper-cloud"])

    @patch("models.transcription.transcription_deepgram.requests")
    def test_deduplicates_and_sorts(self, mock_requests) -> None:
        mock_requests.get.return_value = _make_response(200, {
            "stt": [
                {"name": "nova-2", "batch": True},
                {"name": "nova-2", "batch": True},
                {"name": "base", "batch": True},
            ],
        })

        result = getAvailableDeepgramModels("dg-test")

        self.assertEqual(result, ["base", "nova-2"])

    @patch("models.transcription.transcription_deepgram.requests")
    def test_returns_empty_list_on_error(self, mock_requests) -> None:
        mock_requests.get.return_value = _make_response(500)

        result = getAvailableDeepgramModels("dg-test")

        self.assertEqual(result, [])


class TestGetAvailableDeepgramModelsDetailed(unittest.TestCase):
    @patch("models.transcription.transcription_deepgram.requests")
    def test_includes_supported_languages_per_model(self, mock_requests) -> None:
        mock_requests.get.return_value = _make_response(200, {
            "stt": [
                {"name": "nova-3", "batch": True, "languages": ["en", "en-us"]},
                {"name": "whisper-cloud", "batch": True, "languages": ["multi"]},
            ],
        })

        result = getAvailableDeepgramModelsDetailed("dg-test")

        self.assertEqual(
            result,
            [
                {"name": "nova-3", "languages": ["en", "en-us"]},
                {"name": "whisper-cloud", "languages": ["multi"]},
            ],
        )

    @patch("models.transcription.transcription_deepgram.requests")
    def test_missing_languages_field_becomes_empty_list(self, mock_requests) -> None:
        mock_requests.get.return_value = _make_response(200, {
            "stt": [{"name": "base", "batch": True}],
        })

        result = getAvailableDeepgramModelsDetailed("dg-test")

        self.assertEqual(result, [{"name": "base", "languages": []}])

    @patch("models.transcription.transcription_deepgram.requests")
    def test_excludes_streaming_only_models(self, mock_requests) -> None:
        mock_requests.get.return_value = _make_response(200, {
            "stt": [
                {"name": "nova-3", "batch": True, "languages": ["en"]},
                {"name": "nova-3-streaming-only", "batch": False, "languages": ["en"]},
            ],
        })

        result = getAvailableDeepgramModelsDetailed("dg-test")

        self.assertEqual(result, [{"name": "nova-3", "languages": ["en"]}])

    @patch("models.transcription.transcription_deepgram.requests")
    def test_returns_empty_list_on_error(self, mock_requests) -> None:
        mock_requests.get.return_value = _make_response(500)

        result = getAvailableDeepgramModelsDetailed("dg-test")

        self.assertEqual(result, [])


class TestIsLanguageSupportedByDeepgramModel(unittest.TestCase):
    def test_matches_exact_base_code(self) -> None:
        self.assertTrue(isLanguageSupportedByDeepgramModel("Japanese", "Japan", ["en", "ja", "ko"]))

    def test_matches_region_suffixed_code(self) -> None:
        # モデルが "en-US" のように地域サフィックス付きで対応言語を
        # 申告していても、ベースコード ("en") が一致すれば対応ありとする。
        self.assertTrue(isLanguageSupportedByDeepgramModel("English", "United States", ["en-US"]))

    def test_unsupported_language_returns_false(self) -> None:
        self.assertFalse(isLanguageSupportedByDeepgramModel("Japanese", "Japan", ["en-US", "es"]))

    def test_multi_marker_means_all_languages_supported(self) -> None:
        self.assertTrue(isLanguageSupportedByDeepgramModel("Japanese", "Japan", ["multi"]))

    def test_unknown_language_country_pair_returns_false(self) -> None:
        self.assertFalse(isLanguageSupportedByDeepgramModel("Klingon", "Qo'noS", ["en"]))


class TestGetDeepgramSupportedLanguages(unittest.TestCase):
    def test_returns_per_country_support_for_every_language(self) -> None:
        result = getDeepgramSupportedLanguages(["en", "ja"])

        self.assertEqual(result["Japanese"], {"Japan": True})
        self.assertEqual(result["Korean"], {"South Korea": False})
        self.assertTrue(result["English"]["United States"])
        self.assertTrue(result["English"]["United Kingdom"])

    def test_multi_marker_supports_every_entry(self) -> None:
        result = getDeepgramSupportedLanguages(["multi"])

        self.assertTrue(all(
            supported
            for countries in result.values()
            for supported in countries.values()
        ))

    def test_empty_model_languages_supports_nothing(self) -> None:
        result = getDeepgramSupportedLanguages([])

        self.assertFalse(any(
            supported
            for countries in result.values()
            for supported in countries.values()
        ))


if __name__ == "__main__":
    unittest.main()
