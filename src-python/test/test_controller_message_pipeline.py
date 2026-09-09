"""特性テスト(characterization tests): `micMessage`/`speakerMessage`/`chatMessage`。

バックエンドレビュー(`docs/backend_review_2026-08-27.md`)フェーズ3項目25
「`MessagePipeline`への3メソッド統合」に着手する前に、現状の挙動
(翻訳・transliteration・OSC送信・オーバーレイ更新・クリップボード・
WebSocket送信・ロガー・エラーハンドリング)を固定化するためのテスト。
統合前はこの3メソッドがほぼ無テストだったため、まずここで安全網を作る。

既知のバグ(統合時に修正予定): `chatMessage`だけ`self._is_overlay_available()`
のガードが無い。該当テストは現状の(バグを含む)挙動を明示的に固定化し、
修正後に個別に更新する前提としている。

除外ワード保護機能(`USE_EXCLUDE_WORDS`/`replaceExclamationsWithRandom`等)は
2026-09-07に完全に削除されたため、このテストでは対象外。
"""

import unittest
from unittest.mock import MagicMock

from controller import Controller, config


_CONFIG_KEYS = [
    "ENABLE_TRANSLATION",
    "ENABLE_TRANSCRIPTION_SEND",
    "ENABLE_TRANSCRIPTION_RECEIVE",
    "VRC_MIC_MUTE_SYNC",
    "SEND_MESSAGE_TO_VRC",
    "SEND_RECEIVED_MESSAGE_TO_VRC",
    "SEND_ONLY_TRANSLATED_MESSAGES",
    "OVERLAY_LARGE_LOG",
    "OVERLAY_SMALL_LOG",
    "OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES",
    "ENABLE_CLIPBOARD",
    "CONVERT_MESSAGE_TO_HIRAGANA",
    "CONVERT_MESSAGE_TO_ROMAJI",
    "LOGGER_FEATURE",
    "SELECTED_YOUR_LANGUAGES",
    "SELECTED_TARGET_LANGUAGES",
    "SELECTED_TAB_NO",
    "SEND_MESSAGE_FORMAT_PARTS",
    "RECEIVED_MESSAGE_FORMAT_PARTS",
]

_RUN_MAPPING = {
    "transcription_mic": "/run/transcription_send_mic_message",
    "transcription_speaker": "/run/transcription_receive_speaker_message",
    "error_device": "/run/error_device",
    "error_translation_engine": "/run/error_translation_engine",
    "error_translation_chat_vram_overflow": "/run/error_translation_chat_vram_overflow",
    "error_translation_mic_vram_overflow": "/run/error_translation_mic_vram_overflow",
    "error_translation_speaker_vram_overflow": "/run/error_translation_speaker_vram_overflow",
    "enable_translation": "/run/enable_translation",
    "word_filter": "/run/word_filter",
    "transcription_recognition_error": "/run/transcription_recognition_error",
}


def _enable_multi_target(tab_no: str = "1") -> None:
    """SELECTED_TARGET_LANGUAGESの"1"〜"3"を全て有効化する(既定は"1"のみ)。"""
    targets = config.SELECTED_TARGET_LANGUAGES
    for no in ("1", "2", "3"):
        targets[tab_no][no]["enable"] = True
    config.SELECTED_TARGET_LANGUAGES = targets


def _set_target_language(no: str, language: str, country: str, tab_no: str = "1") -> None:
    """SELECTED_TARGET_LANGUAGES[tab_no][no]のlanguage/countryを設定する。

    `_selected_target_languages_validator`はlanguage/countryの組み合わせが
    `transcription_lang`に存在しないと変更全体を旧値へサイレントにフォール
    バックするため、必ず両方を一致させて渡す必要がある。
    """
    targets = config.SELECTED_TARGET_LANGUAGES
    targets[tab_no][no]["language"] = language
    targets[tab_no][no]["country"] = country
    config.SELECTED_TARGET_LANGUAGES = targets


class _MessagePipelineTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {k: getattr(config, k) for k in _CONFIG_KEYS}
        config.ENABLE_TRANSLATION = True
        config.ENABLE_TRANSCRIPTION_SEND = True
        config.ENABLE_TRANSCRIPTION_RECEIVE = True
        config.VRC_MIC_MUTE_SYNC = False
        config.SEND_MESSAGE_TO_VRC = True
        config.SEND_RECEIVED_MESSAGE_TO_VRC = True
        config.SEND_ONLY_TRANSLATED_MESSAGES = False
        config.OVERLAY_LARGE_LOG = False
        config.OVERLAY_SMALL_LOG = False
        config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES = False
        config.ENABLE_CLIPBOARD = False
        config.CONVERT_MESSAGE_TO_HIRAGANA = False
        config.CONVERT_MESSAGE_TO_ROMAJI = False
        config.LOGGER_FEATURE = False

        self.controller = Controller.__new__(Controller)
        self.controller.run_mapping = dict(_RUN_MAPPING)
        self.run_calls: list = []
        self.controller.run = lambda status, endpoint, result: self.run_calls.append((status, endpoint, result))
        self.controller.changeToCTranslate2Process = MagicMock()
        self.controller._is_overlay_available = lambda: False

        import controller as controller_module
        self._model = controller_module.model
        self._model_patches: dict = {}
        for name, value in (
            ("checkKeywords", MagicMock(return_value=False)),
            ("detectRepeatSendMessage", MagicMock(return_value=False)),
            ("detectRepeatReceiveMessage", MagicMock(return_value=False)),
            ("getInputTranslate", MagicMock(return_value=([], [True]))),
            ("getOutputTranslate", MagicMock(return_value=([], [True]))),
            ("detectVRAMError", MagicMock(return_value=(False, ""))),
            ("convertMessageToTransliteration", MagicMock(return_value=["TRANSLITERATED"])),
            ("oscSendMessage", MagicMock()),
            ("createOverlayImageLargeLog", MagicMock(return_value="LARGE_IMG")),
            ("createOverlayImageSmallLog", MagicMock(return_value="SMALL_IMG")),
            ("updateOverlayLargeLog", MagicMock()),
            ("updateOverlaySmallLog", MagicMock()),
            ("setCopyToClipboardAndPasteFromClipboard", MagicMock()),
            ("checkWebSocketServerAlive", MagicMock(return_value=False)),
            ("websocketSendMessage", MagicMock()),
            ("addTranslationHistory", MagicMock()),
            ("logger", MagicMock()),
        ):
            self._model_patches[name] = getattr(self._model, name, None)
            setattr(self._model, name, value)

    def tearDown(self) -> None:
        for k, v in self._saved.items():
            setattr(config, k, v)
        for name, original in self._model_patches.items():
            if original is None:
                delattr(self._model, name)
            else:
                setattr(self._model, name, original)


class TestMicMessage(_MessagePipelineTestBase):
    def test_empty_message_is_a_noop(self) -> None:
        self.controller.micMessage({"text": "", "language": "English"})
        self.assertEqual(self.run_calls, [])
        self._model.getInputTranslate.assert_not_called()

    def test_mute_sync_skips_entirely(self) -> None:
        config.VRC_MIC_MUTE_SYNC = True
        self._model.mic_mute_status = True
        try:
            self.controller.micMessage({"text": "hello", "language": "English"})
        finally:
            del self._model.mic_mute_status
        self.assertEqual(self.run_calls, [])

    def test_device_not_detected(self) -> None:
        self.controller.micMessage({"text": False, "language": None})
        self.assertEqual(len(self.run_calls), 1)
        status, endpoint, result = self.run_calls[0]
        self.assertEqual((status, endpoint), (400, "/run/error_device"))
        self.assertIn("mic", result["message"].lower())

    def test_word_filter_short_circuits(self) -> None:
        self._model.checkKeywords.return_value = True
        self.controller.micMessage({"text": "banned word", "language": "English"})
        self.assertEqual(len(self.run_calls), 1)
        status, endpoint, result = self.run_calls[0]
        self.assertEqual((status, endpoint), (200, "/run/word_filter"))
        self.assertIn("banned word", result["message"])
        self._model.getInputTranslate.assert_not_called()

    def test_repeat_message_short_circuits(self) -> None:
        self._model.detectRepeatSendMessage.return_value = True
        self.controller.micMessage({"text": "again", "language": "English"})
        self.assertEqual(self.run_calls, [])
        self._model.getInputTranslate.assert_not_called()

    def test_translation_disabled_sends_original_only(self) -> None:
        config.ENABLE_TRANSLATION = False
        self.controller.micMessage({"text": "hello", "language": "English"})
        self._model.getInputTranslate.assert_not_called()
        self.assertEqual(len(self.run_calls), 1)
        _, endpoint, result = self.run_calls[0]
        self.assertEqual(endpoint, "/run/transcription_send_mic_message")
        self.assertEqual(result["original"]["message"], "hello")
        self.assertEqual(result["translations"], [])

    def test_translation_success_calls_get_input_translate_and_reports(self) -> None:
        self._model.getInputTranslate.return_value = (["hola"], [True])
        self.controller.micMessage({"text": "hello", "language": "English"})
        self._model.getInputTranslate.assert_called_once_with("hello", source_language="English")
        _, endpoint, result = self.run_calls[-1]
        self.assertEqual(endpoint, "/run/transcription_send_mic_message")
        self.assertEqual(result["translations"], [{"message": "hola", "transliteration": []}])
        self._model.addTranslationHistory.assert_called_once_with("mic", "hello")

    def test_translation_engine_limit_falls_back_and_reports_error(self) -> None:
        self._model.getInputTranslate.return_value = ([], [False])
        self.controller.micMessage({"text": "hello", "language": "English"})
        self.controller.changeToCTranslate2Process.assert_called_once()
        status, endpoint, result = self.run_calls[0]
        self.assertEqual((status, endpoint), (400, "/run/error_translation_engine"))
        self.assertEqual(result.get("error_code"), "TRANSLATION_ENGINE_LIMIT")

    def test_vram_error_disables_translation_and_reports(self) -> None:
        self._model.getInputTranslate.side_effect = RuntimeError("boom")
        self._model.detectVRAMError.return_value = (True, "out of memory")
        self.controller.micMessage({"text": "hello", "language": "English"})
        endpoints = [c[1] for c in self.run_calls]
        self.assertIn("/run/error_translation_mic_vram_overflow", endpoints)
        self.assertIn("/run/enable_translation", endpoints)
        # VRAMエラー時は以降のOSC/オーバーレイ等の処理を行わず即returnする。
        self._model.oscSendMessage.assert_not_called()

    def test_non_vram_exception_propagates(self) -> None:
        self._model.getInputTranslate.side_effect = RuntimeError("boom")
        self._model.detectVRAMError.return_value = (False, "")
        with self.assertRaises(RuntimeError):
            self.controller.micMessage({"text": "hello", "language": "English"})

    def test_transliteration_uses_own_configured_language(self) -> None:
        config.CONVERT_MESSAGE_TO_HIRAGANA = True
        your_langs = config.SELECTED_YOUR_LANGUAGES
        # language/countryの組み合わせが不整合だと_selected_your_languages_validator
        # がサイレントに旧値へフォールバックするため、両方を明示的に設定する
        # (config.jsonに実機検証等で保存された既存の言語設定に依存しないため)。
        your_langs["1"]["1"]["language"] = "Japanese"
        your_langs["1"]["1"]["country"] = "Japan"
        config.SELECTED_YOUR_LANGUAGES = your_langs
        self._model.getInputTranslate.return_value = (["hola"], [True])
        self.controller.micMessage({"text": "hello", "language": "English"})
        self._model.convertMessageToTransliteration.assert_any_call(
            "hello", hiragana=True, romaji=False
        )

    def test_transliteration_skipped_when_own_language_is_not_japanese(self) -> None:
        config.CONVERT_MESSAGE_TO_HIRAGANA = True
        your_langs = config.SELECTED_YOUR_LANGUAGES
        # _selected_your_languages_validator は language/country の組み合わせが
        # transcription_lang に無いと変更全体をサイレントに旧値へフォールバック
        # するため、両方を一致させて変更する必要がある。
        your_langs["1"]["1"]["language"] = "English"
        your_langs["1"]["1"]["country"] = "United States"
        config.SELECTED_YOUR_LANGUAGES = your_langs
        self._model.getInputTranslate.return_value = (["hola"], [True])
        self.controller.micMessage({"text": "hello", "language": "English"})
        calls = [c.args[0] for c in self._model.convertMessageToTransliteration.call_args_list]
        self.assertNotIn("hello", calls)

    def test_multi_target_translation_and_transliteration(self) -> None:
        _enable_multi_target()
        config.CONVERT_MESSAGE_TO_HIRAGANA = True
        _set_target_language("1", "Japanese", "Japan")
        _set_target_language("2", "English", "United States")
        _set_target_language("3", "Japanese", "Japan")
        self._model.getInputTranslate.return_value = (["ja1", "en", "ja3"], [True, True, True])

        self.controller.micMessage({"text": "hello", "language": "English"})

        _, _, result = self.run_calls[-1]
        self.assertEqual(
            [t["message"] for t in result["translations"]], ["ja1", "en", "ja3"]
        )
        # Japaneseターゲット("1"と"3")だけtransliterationされ、"2"(English)は[]。
        self.assertEqual(result["translations"][1]["transliteration"], [])
        self.assertEqual(result["translations"][0]["transliteration"], ["TRANSLITERATED"])
        self.assertEqual(result["translations"][2]["transliteration"], ["TRANSLITERATED"])

    def test_send_disabled_suppresses_all_output(self) -> None:
        config.ENABLE_TRANSCRIPTION_SEND = False
        self._model.getInputTranslate.return_value = (["hola"], [True])
        self.controller.micMessage({"text": "hello", "language": "English"})
        self.assertEqual(self.run_calls, [])
        self._model.oscSendMessage.assert_not_called()
        self._model.websocketSendMessage.assert_not_called()
        # ENABLE_TRANSCRIPTION_SEND に関わらず履歴だけは記録される。
        self._model.addTranslationHistory.assert_called_once_with("mic", "hello")

    def test_osc_send_respects_send_message_to_vrc_flag(self) -> None:
        config.SEND_MESSAGE_TO_VRC = False
        self._model.getInputTranslate.return_value = (["hola"], [True])
        self.controller.micMessage({"text": "hello", "language": "English"})
        self._model.oscSendMessage.assert_not_called()

    def test_osc_send_only_translated_uses_translation_only(self) -> None:
        config.SEND_ONLY_TRANSLATED_MESSAGES = True
        self._model.getInputTranslate.return_value = (["hola"], [True])
        self.controller.micMessage({"text": "hello", "language": "English"})
        self._model.oscSendMessage.assert_called_once_with("hola")

    def test_osc_send_combines_message_and_translation_by_default(self) -> None:
        self._model.getInputTranslate.return_value = (["hola"], [True])
        self.controller.micMessage({"text": "hello", "language": "English"})
        # SEND_MESSAGE_FORMAT_PARTS の既定は translation_first=False なので
        # メッセージが先、翻訳が後になる。
        self._model.oscSendMessage.assert_called_once_with("hello\nhola")

    def test_clipboard_copies_when_enabled(self) -> None:
        config.ENABLE_CLIPBOARD = True
        self._model.getInputTranslate.return_value = (["hola"], [True])
        self.controller.micMessage({"text": "hello", "language": "English"})
        self._model.setCopyToClipboardAndPasteFromClipboard.assert_called_once_with("hello\nhola")

    def test_clipboard_not_copied_when_disabled(self) -> None:
        self._model.getInputTranslate.return_value = (["hola"], [True])
        self.controller.micMessage({"text": "hello", "language": "English"})
        self._model.setCopyToClipboardAndPasteFromClipboard.assert_not_called()

    def test_overlay_skipped_when_unavailable(self) -> None:
        config.OVERLAY_LARGE_LOG = True
        self.controller._is_overlay_available = lambda: False
        self._model.getInputTranslate.return_value = (["hola"], [True])
        self.controller.micMessage({"text": "hello", "language": "English"})
        self._model.updateOverlayLargeLog.assert_not_called()

    def test_overlay_updates_when_available(self) -> None:
        config.OVERLAY_LARGE_LOG = True
        self.controller._is_overlay_available = lambda: True
        self._model.getInputTranslate.return_value = (["hola"], [True])
        self.controller.micMessage({"text": "hello", "language": "English"})
        self._model.createOverlayImageLargeLog.assert_called_once()
        args = self._model.createOverlayImageLargeLog.call_args.args
        self.assertEqual(args[0], "send")
        self.assertEqual(args[1], "hello")
        self._model.updateOverlayLargeLog.assert_called_once_with("LARGE_IMG")

    def test_overlay_show_only_translated_skips_when_no_translation(self) -> None:
        config.OVERLAY_LARGE_LOG = True
        config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES = True
        self.controller._is_overlay_available = lambda: True
        config.ENABLE_TRANSLATION = False
        self.controller.micMessage({"text": "hello", "language": "English"})
        self._model.createOverlayImageLargeLog.assert_not_called()

    def test_websocket_sent_when_server_alive(self) -> None:
        self._model.checkWebSocketServerAlive.return_value = True
        self._model.getInputTranslate.return_value = (["hola"], [True])
        self.controller.micMessage({"text": "hello", "language": "English"})
        self._model.websocketSendMessage.assert_called_once()
        payload = self._model.websocketSendMessage.call_args.args[0]
        self.assertEqual(payload["type"], "SENT")
        self.assertEqual(payload["message"], "hello")
        self.assertEqual(payload["translation"], ["hola"])

    def test_logger_writes_when_enabled(self) -> None:
        config.LOGGER_FEATURE = True
        self._model.getInputTranslate.return_value = (["hola"], [True])
        self.controller.micMessage({"text": "hello", "language": "English"})
        self._model.logger.info.assert_called_once()
        self.assertIn("[SENT]", self._model.logger.info.call_args.args[0])

    def test_recognition_error_emits_notification_but_still_processes(self) -> None:
        self.controller.micMessage({
            "text": "", "language": None, "recognition_error": True,
        })
        self.assertEqual(len(self.run_calls), 1)
        status, endpoint, result = self.run_calls[0]
        self.assertEqual((status, endpoint), (200, "/run/transcription_recognition_error"))
        self.assertIn("Mic", result["message"])


class TestSpeakerMessage(_MessagePipelineTestBase):
    def test_empty_message_is_a_noop(self) -> None:
        self.controller.speakerMessage({"text": "", "language": "English"})
        self.assertEqual(self.run_calls, [])
        self._model.getOutputTranslate.assert_not_called()

    def test_device_not_detected(self) -> None:
        self.controller.speakerMessage({"text": False, "language": None})
        status, endpoint, result = self.run_calls[0]
        self.assertEqual((status, endpoint), (400, "/run/error_device"))
        self.assertIn("speaker", result["message"].lower())

    def test_word_filter_short_circuits(self) -> None:
        self._model.checkKeywords.return_value = True
        self.controller.speakerMessage({"text": "banned", "language": "English"})
        status, endpoint, _ = self.run_calls[0]
        self.assertEqual((status, endpoint), (200, "/run/word_filter"))
        self._model.getOutputTranslate.assert_not_called()

    def test_repeat_message_short_circuits(self) -> None:
        self._model.detectRepeatReceiveMessage.return_value = True
        self.controller.speakerMessage({"text": "again", "language": "English"})
        self.assertEqual(self.run_calls, [])

    def test_translation_uses_single_your_language_target(self) -> None:
        self._model.getOutputTranslate.return_value = (["hola"], [True])
        self.controller.speakerMessage({"text": "hello", "language": "English"})
        self._model.getOutputTranslate.assert_called_once_with("hello", source_language="English")
        _, endpoint, result = self.run_calls[-1]
        self.assertEqual(endpoint, "/run/transcription_receive_speaker_message")
        self.assertEqual(result["translations"], [{"message": "hola", "transliteration": []}])
        self._model.addTranslationHistory.assert_called_once_with("speaker", "hello")

    def test_translation_engine_limit_falls_back_and_reports_error(self) -> None:
        self._model.getOutputTranslate.return_value = ([], [False])
        self.controller.speakerMessage({"text": "hello", "language": "English"})
        self.controller.changeToCTranslate2Process.assert_called_once()
        status, endpoint, result = self.run_calls[0]
        self.assertEqual((status, endpoint), (400, "/run/error_translation_engine"))

    def test_vram_error_disables_translation_and_reports(self) -> None:
        self._model.getOutputTranslate.side_effect = RuntimeError("boom")
        self._model.detectVRAMError.return_value = (True, "out of memory")
        self.controller.speakerMessage({"text": "hello", "language": "English"})
        endpoints = [c[1] for c in self.run_calls]
        self.assertIn("/run/error_translation_speaker_vram_overflow", endpoints)
        self.assertIn("/run/enable_translation", endpoints)

    def test_transliteration_uses_detected_message_language_not_own_setting(self) -> None:
        config.CONVERT_MESSAGE_TO_HIRAGANA = True
        your_langs = config.SELECTED_YOUR_LANGUAGES
        your_langs["1"]["1"]["language"] = "English"  # 自分の言語は英語
        config.SELECTED_YOUR_LANGUAGES = your_langs
        self._model.getOutputTranslate.return_value = (["hola"], [True])
        # 受信メッセージ自体は日本語として検出された、という想定。
        self.controller.speakerMessage({"text": "hello", "language": "Japanese"})
        self._model.convertMessageToTransliteration.assert_any_call(
            "hello", hiragana=True, romaji=False
        )

    def test_small_log_overlay_updates_when_available(self) -> None:
        config.OVERLAY_SMALL_LOG = True
        self.controller._is_overlay_available = lambda: True
        self._model.getOutputTranslate.return_value = (["hola"], [True])
        self.controller.speakerMessage({"text": "hello", "language": "English"})
        self._model.createOverlayImageSmallLog.assert_called_once()
        self._model.updateOverlaySmallLog.assert_called_once_with("SMALL_IMG")

    def test_small_log_overlay_skipped_when_unavailable(self) -> None:
        config.OVERLAY_SMALL_LOG = True
        self.controller._is_overlay_available = lambda: False
        self.controller.speakerMessage({"text": "hello", "language": "English"})
        self._model.updateOverlaySmallLog.assert_not_called()

    def test_large_log_overlay_direction_is_receive(self) -> None:
        config.OVERLAY_LARGE_LOG = True
        self.controller._is_overlay_available = lambda: True
        self._model.getOutputTranslate.return_value = (["hola"], [True])
        self.controller.speakerMessage({"text": "hello", "language": "English"})
        args = self._model.createOverlayImageLargeLog.call_args.args
        self.assertEqual(args[0], "receive")

    def test_no_clipboard_step_for_speaker(self) -> None:
        # speakerMessage は clipboard 機能を一切持たない (mic だけの機能)。
        self.assertFalse(hasattr(self._model, "setCopyToClipboardAndPasteFromClipboard_called"))
        self._model.getOutputTranslate.return_value = (["hola"], [True])
        self.controller.speakerMessage({"text": "hello", "language": "English"})
        self._model.setCopyToClipboardAndPasteFromClipboard.assert_not_called()

    def test_osc_received_echo_respects_flag(self) -> None:
        config.SEND_RECEIVED_MESSAGE_TO_VRC = False
        self._model.getOutputTranslate.return_value = (["hola"], [True])
        self.controller.speakerMessage({"text": "hello", "language": "English"})
        self._model.oscSendMessage.assert_not_called()

    def test_websocket_payload_type_is_received(self) -> None:
        self._model.checkWebSocketServerAlive.return_value = True
        self._model.getOutputTranslate.return_value = (["hola"], [True])
        self.controller.speakerMessage({"text": "hello", "language": "English"})
        payload = self._model.websocketSendMessage.call_args.args[0]
        self.assertEqual(payload["type"], "RECEIVED")

    def test_logger_prefix_is_received(self) -> None:
        config.LOGGER_FEATURE = True
        self._model.getOutputTranslate.return_value = (["hola"], [True])
        self.controller.speakerMessage({"text": "hello", "language": "English"})
        self.assertIn("[RECEIVED]", self._model.logger.info.call_args.args[0])

    def test_receive_disabled_suppresses_output(self) -> None:
        config.ENABLE_TRANSCRIPTION_RECEIVE = False
        self._model.getOutputTranslate.return_value = (["hola"], [True])
        self.controller.speakerMessage({"text": "hello", "language": "English"})
        self.assertEqual(self.run_calls, [])
        self._model.addTranslationHistory.assert_called_once_with("speaker", "hello")

    def test_recognition_error_emits_notification(self) -> None:
        self.controller.speakerMessage({
            "text": "", "language": None, "recognition_error": True,
        })
        status, endpoint, result = self.run_calls[0]
        self.assertEqual((status, endpoint), (200, "/run/transcription_recognition_error"))
        self.assertIn("Speaker", result["message"])


class TestChatMessage(_MessagePipelineTestBase):
    def test_empty_message_returns_shape_without_crashing(self) -> None:
        """MessagePipeline統合(2026-09-07)で修正: 以前は空メッセージだと
        `UnboundLocalError`でクラッシュしていたが、今は正しい空の結果
        shapeを返す。
        """
        result = self.controller.chatMessage({"id": "1", "message": ""})
        self.assertEqual(result["status"], 200)
        self.assertEqual(result["result"]["id"], "1")
        self.assertEqual(result["result"]["original"], {"message": "", "transliteration": []})
        self.assertEqual(result["result"]["translations"], [])
        self._model.getInputTranslate.assert_not_called()
        self._model.addTranslationHistory.assert_called_once_with("chat", "")

    def test_no_word_filter_for_typed_chat(self) -> None:
        # chatMessage はタイプ入力なのでワードフィルタを一切適用しない(意図的な仕様)。
        self._model.checkKeywords.return_value = True
        self._model.getInputTranslate.return_value = (["hola"], [True])
        result = self.controller.chatMessage({"id": "1", "message": "hello"})
        self._model.checkKeywords.assert_not_called()
        self.assertEqual(result["result"]["translations"][0]["message"], "hola")

    def test_translation_success_returns_shape(self) -> None:
        self._model.getInputTranslate.return_value = (["hola"], [True])
        result = self.controller.chatMessage({"id": "42", "message": "hello"})
        # MessagePipeline統合により、以前は省略していた source_language を
        # 明示的に None として渡すようになった(model.getInputTranslate側の
        # 既定値と同じなので、渡し方が変わっただけで挙動は同じ)。
        self._model.getInputTranslate.assert_called_once_with("hello", source_language=None)
        self.assertEqual(result["status"], 200)
        self.assertEqual(result["result"]["id"], "42")
        self.assertEqual(result["result"]["original"]["message"], "hello")
        self.assertEqual(result["result"]["translations"], [{"message": "hola", "transliteration": []}])
        self._model.addTranslationHistory.assert_called_once_with("chat", "hello")

    def test_translation_engine_limit_falls_back_and_reports_error(self) -> None:
        self._model.getInputTranslate.return_value = ([], [False])
        self.controller.chatMessage({"id": "1", "message": "hello"})
        self.controller.changeToCTranslate2Process.assert_called_once()
        status, endpoint, result = self.run_calls[0]
        self.assertEqual((status, endpoint), (400, "/run/error_translation_engine"))

    def test_vram_error_returns_empty_translations_without_raising(self) -> None:
        self._model.getInputTranslate.side_effect = RuntimeError("boom")
        self._model.detectVRAMError.return_value = (True, "out of memory")
        result = self.controller.chatMessage({"id": "1", "message": "hello"})
        endpoints = [c[1] for c in self.run_calls]
        self.assertIn("/run/error_translation_chat_vram_overflow", endpoints)
        self.assertIn("/run/enable_translation", endpoints)
        self.assertEqual(result["result"]["translations"][0]["message"], "")

    def test_multi_target_transliteration_matches_mic_semantics(self) -> None:
        _enable_multi_target()
        config.CONVERT_MESSAGE_TO_HIRAGANA = True
        _set_target_language("1", "Japanese", "Japan")
        _set_target_language("2", "English", "United States")
        _set_target_language("3", "Japanese", "Japan")
        self._model.getInputTranslate.return_value = (["ja1", "en", "ja3"], [True, True, True])

        result = self.controller.chatMessage({"id": "1", "message": "hello"})

        translations = result["result"]["translations"]
        self.assertEqual(translations[1]["transliteration"], [])
        self.assertEqual(translations[0]["transliteration"], ["TRANSLITERATED"])
        self.assertEqual(translations[2]["transliteration"], ["TRANSLITERATED"])

    def test_osc_send_only_translated_uses_translation_only(self) -> None:
        config.SEND_ONLY_TRANSLATED_MESSAGES = True
        self._model.getInputTranslate.return_value = (["hola"], [True])
        self.controller.chatMessage({"id": "1", "message": "hello"})
        self._model.oscSendMessage.assert_called_once_with("hola")

    def test_osc_send_respects_send_message_to_vrc_flag(self) -> None:
        # 訂正: chatMessage も mic と同じ SEND_MESSAGE_TO_VRC ゲートを持つ
        # (当初「無い」と誤って想定していたが、実装を再確認して訂正)。
        config.SEND_MESSAGE_TO_VRC = False
        self._model.getInputTranslate.return_value = (["hola"], [True])
        self.controller.chatMessage({"id": "1", "message": "hello"})
        self._model.oscSendMessage.assert_not_called()

    def test_overlay_skipped_when_unavailable(self) -> None:
        """MessagePipeline統合(2026-09-07)で修正: 以前はchatMessageだけ
        `_is_overlay_available()`のガードが無く、利用不可能な状態でも
        オーバーレイ更新を試みていた。今はmic/speakerと同じガードを通る。
        """
        config.OVERLAY_LARGE_LOG = True
        self.controller._is_overlay_available = lambda: False
        self._model.getInputTranslate.return_value = (["hola"], [True])
        self.controller.chatMessage({"id": "1", "message": "hello"})
        self._model.updateOverlayLargeLog.assert_not_called()

    def test_overlay_updates_when_available(self) -> None:
        config.OVERLAY_LARGE_LOG = True
        self.controller._is_overlay_available = lambda: True
        self._model.getInputTranslate.return_value = (["hola"], [True])
        self.controller.chatMessage({"id": "1", "message": "hello"})
        self._model.updateOverlayLargeLog.assert_called_once()

    def test_websocket_payload_type_is_chat(self) -> None:
        self._model.checkWebSocketServerAlive.return_value = True
        self._model.getInputTranslate.return_value = (["hola"], [True])
        self.controller.chatMessage({"id": "1", "message": "hello"})
        payload = self._model.websocketSendMessage.call_args.args[0]
        self.assertEqual(payload["type"], "CHAT")

    def test_logger_prefix_is_chat(self) -> None:
        config.LOGGER_FEATURE = True
        self._model.getInputTranslate.return_value = (["hola"], [True])
        self.controller.chatMessage({"id": "1", "message": "hello"})
        self.assertIn("[CHAT]", self._model.logger.info.call_args.args[0])

    def test_return_value_delivery_not_push(self) -> None:
        # chatMessage は self.run() を介さず、戻り値で結果を返す
        # (同期リクエスト/レスポンス型エンドポイントのため)。
        self._model.getInputTranslate.return_value = (["hola"], [True])
        result = self.controller.chatMessage({"id": "1", "message": "hello"})
        self.assertEqual(self.run_calls, [])
        self.assertIn("result", result)


if __name__ == "__main__":
    unittest.main()
