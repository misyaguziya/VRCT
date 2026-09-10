"""`Controller._configValidationErrorResponse` デコレータ (フェーズ3項目24)
と、それを適用した12個の単純な設定セッターのテスト。

対象の欠陥: `config.X = data` して結果を返すだけの単純なエンドポイント
(`setUiLanguage` 等) は、不正な値を渡されても config.py のディスクリプタが
サイレントに値を無視し、変化していない旧値を200(成功)で返していた。
デコレータで `ConfigValidationError` を捕まえ `VRCTError` の
エラーレスポンスへ変換することで、この誤った契約を直した
(メソッド本体は一切変更していない)。
"""

import unittest
from unittest.mock import MagicMock

from config import ConfigValidationError, config
from controller import Controller, _configValidationErrorResponse
from errors import ErrorCode


class TestConfigValidationErrorResponseDecoratorInIsolation(unittest.TestCase):
    """実際の config/controller を使わず、デコレータ自体の動作だけを検証する。"""

    def test_successful_call_passes_through_unchanged(self) -> None:
        @_configValidationErrorResponse(ErrorCode.VALIDATION_CONFIG_VALUE_INVALID)
        def fake_setter(data):
            return {"status": 200, "result": data}

        self.assertEqual(fake_setter("ok"), {"status": 200, "result": "ok"})

    def test_config_validation_error_is_converted_to_vrct_error_response(self) -> None:
        @_configValidationErrorResponse(ErrorCode.VALIDATION_CONFIG_VALUE_INVALID)
        def fake_setter(data):
            raise ConfigValidationError("SOME_ATTR", data)

        response = fake_setter("bad-value")

        self.assertEqual(response["status"], 400)
        self.assertEqual(response["result"]["data"], "bad-value")
        self.assertEqual(response["result"]["error_code"], ErrorCode.VALIDATION_CONFIG_VALUE_INVALID.value)

    def test_other_exceptions_are_not_caught(self) -> None:
        @_configValidationErrorResponse(ErrorCode.VALIDATION_CONFIG_VALUE_INVALID)
        def fake_setter(data):
            raise RuntimeError("unrelated bug")

        with self.assertRaises(RuntimeError):
            fake_setter("anything")

    def test_preserves_the_wrapped_function_name(self) -> None:
        @_configValidationErrorResponse(ErrorCode.VALIDATION_CONFIG_VALUE_INVALID)
        def setSomething(data):
            return {"status": 200, "result": data}

        self.assertEqual(setSomething.__name__, "setSomething")


class _SimpleConfigSetterTestMixin:
    """12エンドポイント共通のテスト本体。`unittest.TestCase` を直接継承しないのは、
    このミックスイン自体が pytest にテストクラスとして収集され
    METHOD_NAME 等未設定のまま実行されるのを防ぐため。

    サブクラスは METHOD_NAME/ATTR_NAME に加えて get_valid_value(current)/
    get_invalid_value(current) を実装する (current = 変更前の実際の値)。
    """

    METHOD_NAME: str
    ATTR_NAME: str

    def get_valid_value(self, current):
        raise NotImplementedError

    def get_invalid_value(self, current):
        raise NotImplementedError

    def setUp(self) -> None:
        self._original_value = getattr(config, self.ATTR_NAME)
        self.controller = Controller.__new__(Controller)

    def tearDown(self) -> None:
        setattr(config, self.ATTR_NAME, self._original_value)

    def _call(self, value):
        return getattr(self.controller, self.METHOD_NAME)(value)

    def test_valid_value_is_accepted(self) -> None:
        valid_value = self.get_valid_value(self._original_value)

        response = self._call(valid_value)

        self.assertEqual(response["status"], 200)
        self.assertEqual(getattr(config, self.ATTR_NAME), valid_value)

    def test_invalid_value_is_rejected_and_config_is_unchanged(self) -> None:
        invalid_value = self.get_invalid_value(self._original_value)

        response = self._call(invalid_value)

        self.assertEqual(response["status"], 400)
        # 拒否された場合、値は変化していないこと (以前はここが200で
        # 「成功したが何も変わっていない」という誤った契約になっていた)。
        self.assertEqual(getattr(config, self.ATTR_NAME), self._original_value)


class SetSelectedReleaseChannelTests(_SimpleConfigSetterTestMixin, unittest.TestCase):
    METHOD_NAME = "setSelectedReleaseChannel"
    ATTR_NAME = "SELECTED_RELEASE_CHANNEL"

    def get_valid_value(self, current):
        choices = config.SELECTABLE_RELEASE_CHANNEL_LIST
        return next(c for c in choices if c != current)

    def get_invalid_value(self, current):
        return "definitely-not-a-real-channel"


class SetMessageBoxRatioTests(_SimpleConfigSetterTestMixin, unittest.TestCase):
    METHOD_NAME = "setMessageBoxRatio"
    ATTR_NAME = "MESSAGE_BOX_RATIO"

    def get_valid_value(self, current):
        return 42

    def get_invalid_value(self, current):
        return "not-a-number"


class SetSendMessageButtonTypeTests(_SimpleConfigSetterTestMixin, unittest.TestCase):
    METHOD_NAME = "setSendMessageButtonType"
    ATTR_NAME = "SEND_MESSAGE_BUTTON_TYPE"

    def get_valid_value(self, current):
        choices = config.SEND_MESSAGE_BUTTON_TYPE_LIST
        return next(c for c in choices if c != current)

    def get_invalid_value(self, current):
        return "definitely-not-a-real-button-type"


class SetFontFamilyTests(_SimpleConfigSetterTestMixin, unittest.TestCase):
    METHOD_NAME = "setFontFamily"
    ATTR_NAME = "FONT_FAMILY"

    def get_valid_value(self, current):
        return "Comic Sans MS"

    def get_invalid_value(self, current):
        return 12345  # type_=str なので数値は拒否される


class SetUiLanguageTests(_SimpleConfigSetterTestMixin, unittest.TestCase):
    METHOD_NAME = "setUiLanguage"
    ATTR_NAME = "UI_LANGUAGE"

    def get_valid_value(self, current):
        choices = config.SELECTABLE_UI_LANGUAGE_LIST
        return next(c for c in choices if c != current)

    def get_invalid_value(self, current):
        return "xx-not-a-real-language"


class SetWhisperWeightTypeTests(_SimpleConfigSetterTestMixin, unittest.TestCase):
    METHOD_NAME = "setWhisperWeightType"
    ATTR_NAME = "WHISPER_WEIGHT_TYPE"

    def get_valid_value(self, current):
        choices = list(config.SELECTABLE_WHISPER_WEIGHT_TYPE_LIST)
        return next((c for c in choices if c != current), current)

    def get_invalid_value(self, current):
        return "definitely-not-a-real-weight-type"


class SetSelectedTranscriptionComputeTypeTests(_SimpleConfigSetterTestMixin, unittest.TestCase):
    METHOD_NAME = "setSelectedTranscriptionComputeType"
    ATTR_NAME = "SELECTED_TRANSCRIPTION_COMPUTE_TYPE"

    def get_valid_value(self, current):
        choices = config.SELECTED_TRANSCRIPTION_COMPUTE_DEVICE.get("compute_types", [])
        return next((c for c in choices if c != current), current)

    def get_invalid_value(self, current):
        return "definitely-not-a-real-compute-type"


class SetMainWindowGeometryTests(_SimpleConfigSetterTestMixin, unittest.TestCase):
    METHOD_NAME = "setMainWindowGeometry"
    ATTR_NAME = "MAIN_WINDOW_GEOMETRY"

    def get_valid_value(self, current):
        new_value = dict(current)
        for key in new_value:
            new_value[key] = new_value[key] + 1
        return new_value

    def get_invalid_value(self, current):
        return {"not_a_real_key": 1}  # キー集合が一致しない -> バリデータ全体拒否


class SetHotkeysTests(_SimpleConfigSetterTestMixin, unittest.TestCase):
    METHOD_NAME = "setHotkeys"
    ATTR_NAME = "HOTKEYS"

    def get_valid_value(self, current):
        new_value = dict(current)
        for key in new_value:
            new_value[key] = None
        return new_value

    def get_invalid_value(self, current):
        return "not-a-dict"  # キー集合の比較以前に dict ですらない -> 全体拒否


class SetPluginsStatusTests(_SimpleConfigSetterTestMixin, unittest.TestCase):
    METHOD_NAME = "setPluginsStatus"
    ATTR_NAME = "PLUGINS_STATUS"

    def get_valid_value(self, current):
        return [{"name": "example", "enabled": True}]

    def get_invalid_value(self, current):
        return "not-a-list"


class SetSendMessageFormatPartsTests(_SimpleConfigSetterTestMixin, unittest.TestCase):
    METHOD_NAME = "setSendMessageFormatParts"
    ATTR_NAME = "SEND_MESSAGE_FORMAT_PARTS"

    def get_valid_value(self, current):
        new_value = dict(current)
        new_value["separator"] = " / "
        return new_value

    def get_invalid_value(self, current):
        return {}  # 必須キーが欠けている -> 構造チェックで全体拒否


class SetReceivedMessageFormatPartsTests(_SimpleConfigSetterTestMixin, unittest.TestCase):
    METHOD_NAME = "setReceivedMessageFormatParts"
    ATTR_NAME = "RECEIVED_MESSAGE_FORMAT_PARTS"

    def get_valid_value(self, current):
        new_value = dict(current)
        new_value["separator"] = " / "
        return new_value

    def get_invalid_value(self, current):
        return {}


if __name__ == "__main__":
    unittest.main()
