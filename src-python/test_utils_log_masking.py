"""ログ出力のシークレットマスクに関するテスト (P0-1 の回帰防止)。

`.venv` に pytest が入っていなくても `python -m unittest test_utils_log_masking`
で動くよう unittest で書いている。

対象の欠陥:
- `_isSensitiveEndpoint` が "auth_key" のみにマッチしており、
  `printLog("Set OpenRouter Auth Key", data)` のような空白区切りのラベルが
  マスク対象外になっていた (全 7 翻訳エンジンで発生)。
- `printResponse` のマスク判定がエンドポイント名だけを見ていたため、
  `/run/initialization_complete` のように複数の *_auth_key を含む集約
  レスポンスに対してはマスクが原理的に機能しなかった。
"""

import json
import logging
import unittest
from unittest.mock import patch

import utils


class IsSensitiveEndpointTests(unittest.TestCase):
    def test_matches_endpoint_style_strings(self):
        self.assertTrue(utils._isSensitiveEndpoint("/set/data/openrouter_auth_key"))
        self.assertTrue(utils._isSensitiveEndpoint("/get/data/deepl_auth_key"))

    def test_matches_human_readable_labels_with_spaces(self):
        # printLog の第一引数はこの形式で渡される。空白区切りのままだと
        # "auth_key" にマッチせず素通りしていた。
        for label in (
            "Set DeepL Auth Key",
            "Set Plamo Auth Key",
            "Set Gemini Auth Key",
            "Set OpenAI Auth Key",
            "Set Groq Auth Key",
            "Set OpenRouter Auth Key",
            "Set OpenAI Compatible Auth Key",
        ):
            with self.subTest(label=label):
                self.assertTrue(utils._isSensitiveEndpoint(label))

    def test_non_sensitive_endpoint_is_not_flagged(self):
        self.assertFalse(utils._isSensitiveEndpoint("/run/initialization_complete"))
        self.assertFalse(utils._isSensitiveEndpoint("/set/data/ui_language"))

    def test_non_string_input_is_not_flagged(self):
        self.assertFalse(utils._isSensitiveEndpoint(None))
        self.assertFalse(utils._isSensitiveEndpoint(123))


class MaskSensitiveDataTests(unittest.TestCase):
    def test_masks_nested_endpoint_style_keys(self):
        # /run/initialization_complete が送出する集約レスポンスと同じ形。
        payload = {
            "/get/data/openrouter_auth_key": "sk-or-REALSECRET",
            "/get/data/deepl_auth_key": None,
            "/get/data/ui_language": "en",
        }
        masked = utils._maskSensitiveData(payload)
        self.assertEqual(masked["/get/data/openrouter_auth_key"], "***MASKED***")
        self.assertIsNone(masked["/get/data/deepl_auth_key"])  # None/空文字はそのまま
        self.assertEqual(masked["/get/data/ui_language"], "en")

    def test_masks_nested_dict_under_sensitive_key(self):
        payload = {"auth_keys": {"OpenRouter_API": "sk-or-REALSECRET", "DeepL_API": None}}
        masked = utils._maskSensitiveData(payload)
        self.assertEqual(masked["auth_keys"], "***MASKED***")

    def test_recurses_into_lists(self):
        payload = [{"password": "hunter2"}, {"ui_language": "en"}]
        masked = utils._maskSensitiveData(payload)
        self.assertEqual(masked[0]["password"], "***MASKED***")
        self.assertEqual(masked[1]["ui_language"], "en")

    def test_scalar_passthrough(self):
        self.assertEqual(utils._maskSensitiveData("plain value"), "plain value")
        self.assertIsNone(utils._maskSensitiveData(None))


class PrintLogMaskingTests(unittest.TestCase):
    def setUp(self):
        # 各テストでモジュールグローバルの process_logger を張り替える。
        self._original_logger = utils.process_logger
        self.records = []
        logger = logging.getLogger("test_process_logger_masking")
        logger.handlers.clear()
        logger.addHandler(logging.Handler())
        utils.process_logger = logger
        self.addCleanup(setattr, utils, "process_logger", self._original_logger)

    def test_sensitive_label_masks_value_even_without_underscore(self):
        captured = {}

        def fake_info(response):
            captured.update(response)

        utils.process_logger.info = fake_info
        with patch.object(utils, "_writeStdoutLine"):
            utils.printLog("Set OpenRouter Auth Key", "sk-or-REALSECRET")
        self.assertEqual(captured["data"], "***MASKED***")

    def test_non_sensitive_label_is_not_masked(self):
        captured = {}

        def fake_info(response):
            captured.update(response)

        utils.process_logger.info = fake_info
        with patch.object(utils, "_writeStdoutLine"):
            utils.printLog("Whisper file download failed, retrying (1/2)", "https://example.com/x.bin")
        self.assertEqual(captured["data"], "https://example.com/x.bin")

    def test_sensitive_label_masks_stdout_too(self):
        # printLog は (printResponse と異なり) log/stdout の両方に同じ
        # response dict を書き出すため、マスクは stdout 側にも及ぶ必要がある。
        written = {}
        utils.process_logger.info = lambda response: None
        with patch.object(utils, "_writeStdoutLine", lambda line: written.setdefault("line", line)):
            utils.printLog("Set OpenRouter Auth Key", "sk-or-REALSECRET")
        sent = json.loads(written["line"])
        self.assertEqual(sent["data"], "***MASKED***")


class PrintResponseMaskingTests(unittest.TestCase):
    def setUp(self):
        self._original_logger = utils.process_logger
        logger = logging.getLogger("test_process_logger_masking_response")
        logger.handlers.clear()
        logger.addHandler(logging.Handler())
        utils.process_logger = logger
        self.addCleanup(setattr, utils, "process_logger", self._original_logger)

    def test_direct_sensitive_endpoint_masks_whole_result(self):
        captured = {}
        utils.process_logger.info = lambda response: captured.update(response)
        with patch.object(utils, "_writeStdoutLine"):
            utils.printResponse(200, "/get/data/openrouter_auth_key", "sk-or-REALSECRET")
        self.assertEqual(captured["result"], "***MASKED***")

    def test_aggregate_endpoint_masks_nested_auth_keys_only(self):
        # /run/initialization_complete 相当: エンドポイント自体は機微でないが
        # 中身に複数の *_auth_key が含まれる。
        captured = {}
        utils.process_logger.info = lambda response: captured.update(response)
        payload = {
            "/get/data/openrouter_auth_key": "sk-or-REALSECRET",
            "/get/data/deepl_auth_key": None,
            "/get/data/ui_language": "en",
        }
        with patch.object(utils, "_writeStdoutLine"):
            utils.printResponse(200, "/run/initialization_complete", payload)
        self.assertEqual(captured["result"]["/get/data/openrouter_auth_key"], "***MASKED***")
        self.assertEqual(captured["result"]["/get/data/ui_language"], "en")

    def test_stdout_payload_is_never_masked_lossily(self):
        # ログ (process_logger) はマスクするが、UI に返す実レスポンス
        # (stdout 経由) は生の値のまま届く必要がある (UI 動作を壊さないため)。
        written = {}

        def fake_write(line):
            written["line"] = line

        utils.process_logger.info = lambda response: None
        with patch.object(utils, "_writeStdoutLine", fake_write):
            utils.printResponse(200, "/get/data/openrouter_auth_key", "sk-or-REALSECRET")
        sent = json.loads(written["line"])
        self.assertEqual(sent["result"], "sk-or-REALSECRET")


if __name__ == "__main__":
    unittest.main()
