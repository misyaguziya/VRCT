"""字幕オーバーレイの座標ロック (locked) の設定検証。

ロックを足す前に保存した設定 (locked なし) を捨てて位置が初期化されないこと、
不正な値は今の値のままにすることを確認する。
"""

import unittest

from config import ValidatedProperty, _overlay_small_validator, _overlay_large_validator


class _DummyConfig:
    OVERLAY_SMALL_LOG_SETTINGS = ValidatedProperty("OVERLAY_SMALL_LOG_SETTINGS", _overlay_small_validator)
    OVERLAY_LARGE_LOG_SETTINGS = ValidatedProperty("OVERLAY_LARGE_LOG_SETTINGS", _overlay_large_validator)

    def saveConfig(self, name, value, immediate_save=False):
        pass


def _settings(**extra):
    return {
        "x_pos": 0.0, "y_pos": 0.0, "z_pos": 0.0,
        "x_rotation": 0.0, "y_rotation": 0.0, "z_rotation": 0.0,
        "display_duration": 5, "fadeout_duration": 2,
        "opacity": 1.0, "ui_scaling": 1.0, "tracker": "HMD", "locked": False,
        **extra,
    }


class OverlayLockedValidatorTest(unittest.TestCase):
    def setUp(self):
        self.inst = _DummyConfig()
        self.inst._OVERLAY_SMALL_LOG_SETTINGS = _settings()
        self.inst._OVERLAY_LARGE_LOG_SETTINGS = _settings(tracker="LeftHand")

    def test_lock_is_saved(self):
        self.inst.OVERLAY_SMALL_LOG_SETTINGS = _settings(locked=True)
        self.assertIs(self.inst.OVERLAY_SMALL_LOG_SETTINGS["locked"], True)
        self.inst.OVERLAY_LARGE_LOG_SETTINGS = _settings(tracker="LeftHand", locked=True)
        self.assertIs(self.inst.OVERLAY_LARGE_LOG_SETTINGS["locked"], True)

    def test_settings_saved_before_lock_existed_keep_their_position(self):
        old = _settings(x_pos=0.3)
        del old["locked"]
        self.inst.OVERLAY_SMALL_LOG_SETTINGS = old
        self.assertEqual(self.inst.OVERLAY_SMALL_LOG_SETTINGS["x_pos"], 0.3)
        self.assertIs(self.inst.OVERLAY_SMALL_LOG_SETTINGS["locked"], False)

    def test_non_bool_lock_keeps_current_value(self):
        self.inst.OVERLAY_SMALL_LOG_SETTINGS = _settings(locked=True)
        self.inst.OVERLAY_SMALL_LOG_SETTINGS = _settings(locked="yes")
        self.assertIs(self.inst.OVERLAY_SMALL_LOG_SETTINGS["locked"], True)


if __name__ == "__main__":
    unittest.main()
