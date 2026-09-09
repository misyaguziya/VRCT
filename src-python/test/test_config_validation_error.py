"""`ConfigValidationError` (フェーズ3項目24) のテスト。

対象の欠陥: `ManagedProperty`/`ValidatedProperty` は不正な値をサイレントに
無視していたため、`/set/data/*` エンドポイントは「値が拒否されても200で
成功を返す」という誤った契約になっていた (`controller.py` の
`setUiLanguage` 等)。ディスクリプタ自体が拒否時に `ConfigValidationError`
を送出するようにし、呼び出し元 (`controller.py` の
`_configValidationErrorResponse` デコレータ) がこれを `VRCTError` の
エラーレスポンスへ変換できるようにした。

`ValidatedProperty` は「バリデータが値を**全体として**拒否した場合
(`None` を返した場合) のみ」送出する。多くのバリデータ (`HOTKEYS` や
`SELECTED_TRANSLATION_ENGINES` 等) は「キー単位で不正な項目だけ旧値に
フォールバックする」設計を意図的に持っており (test_config_validated_property.py
で検証済み)、その場合は非 `None` を返して正常終了するため送出されない —
この既存の意図的な挙動を壊していないことも合わせて検証する。
"""

import unittest

from config import ConfigValidationError, ManagedProperty, ValidatedProperty


def _total_reject_validator(val, inst):
    # 全体を拒否する (Noneを返す) パターン。
    return val if isinstance(val, str) and val.startswith("ok") else None


def _partial_fallback_validator(val, inst):
    # キー単位で不正な項目だけ旧値にフォールバックするパターン
    # (HOTKEYS/SELECTED_TRANSLATION_ENGINES と同じ設計)。
    if not isinstance(val, dict):
        return None
    old = inst.PARTIAL_FALLBACK
    return {k: (v if isinstance(v, int) else old.get(k)) for k, v in val.items()}


class _DummyConfig:
    """Config クラスをフルに起動せずディスクリプタだけを検証するための最小スタブ。"""

    STRICT_TYPE = ManagedProperty("STRICT_TYPE", type_=int)
    ALLOWED_ONLY = ManagedProperty("ALLOWED_ONLY", type_=str, allowed=["a", "b", "c"])
    READONLY_VALUE = ManagedProperty("READONLY_VALUE", type_=int, readonly=True)
    TOTAL_REJECT = ValidatedProperty("TOTAL_REJECT", _total_reject_validator)
    PARTIAL_FALLBACK = ValidatedProperty("PARTIAL_FALLBACK", _partial_fallback_validator)

    def saveConfig(self, name, value, immediate_save=False):
        pass


class TestManagedPropertyRaisesOnRejection(unittest.TestCase):
    def setUp(self) -> None:
        self.inst = _DummyConfig()
        self.inst._STRICT_TYPE = 1
        self.inst._ALLOWED_ONLY = "a"
        self.inst._READONLY_VALUE = 42

    def test_type_mismatch_raises_and_keeps_old_value(self) -> None:
        with self.assertRaises(ConfigValidationError):
            self.inst.STRICT_TYPE = "not-an-int"
        self.assertEqual(self.inst.STRICT_TYPE, 1)

    def test_value_outside_allowed_raises_and_keeps_old_value(self) -> None:
        with self.assertRaises(ConfigValidationError):
            self.inst.ALLOWED_ONLY = "z"
        self.assertEqual(self.inst.ALLOWED_ONLY, "a")

    def test_valid_value_is_accepted_without_raising(self) -> None:
        self.inst.STRICT_TYPE = 99
        self.assertEqual(self.inst.STRICT_TYPE, 99)

    def test_readonly_still_raises_attribute_error_not_config_validation_error(self) -> None:
        # readonly は「プログラミングエラー」であり、ユーザー入力の検証とは別種の
        # 問題として区別する (フェーズ3項目24の対象外、既存の挙動を維持)。
        with self.assertRaises(AttributeError):
            self.inst.READONLY_VALUE = 1

    def test_config_validation_error_carries_attr_name_and_value(self) -> None:
        try:
            self.inst.STRICT_TYPE = "bad"
        except ConfigValidationError as e:
            self.assertEqual(e.attr_name, "STRICT_TYPE")
            self.assertEqual(e.value, "bad")
        else:
            self.fail("ConfigValidationError was not raised")


class TestValidatedPropertyRaisesOnlyOnTotalRejection(unittest.TestCase):
    def setUp(self) -> None:
        self.inst = _DummyConfig()
        self.inst._TOTAL_REJECT = "ok-initial"
        self.inst._PARTIAL_FALLBACK = {"a": 1, "b": 2}

    def test_validator_returning_none_raises_and_keeps_old_value(self) -> None:
        with self.assertRaises(ConfigValidationError):
            self.inst.TOTAL_REJECT = "definitely-not-ok"
        self.assertEqual(self.inst.TOTAL_REJECT, "ok-initial")

    def test_validator_returning_a_value_is_accepted_without_raising(self) -> None:
        self.inst.TOTAL_REJECT = "ok-new"
        self.assertEqual(self.inst.TOTAL_REJECT, "ok-new")

    def test_validator_raising_is_converted_to_config_validation_error(self) -> None:
        with self.assertRaises(ConfigValidationError):
            self.inst.TOTAL_REJECT = 12345  # startswith() 呼び出しで例外になる非文字列

    def test_partial_fallback_validator_does_not_raise(self) -> None:
        # HOTKEYS/SELECTED_TRANSLATION_ENGINES と同じ「キー単位フォールバック」
        # 設計は、全体としては拒否されていない (non-None を返す) ため、
        # ConfigValidationError は送出されない。既存の意図的な挙動を壊していない
        # ことの確認。
        self.inst.PARTIAL_FALLBACK = {"a": "not-an-int", "b": 99}
        self.assertEqual(self.inst.PARTIAL_FALLBACK, {"a": 1, "b": 99})  # aだけ旧値維持


if __name__ == "__main__":
    unittest.main()
