"""VR UIのログウィンドウの操作バー (固定先・ロック) のエンドポイント。"""

import unittest
from unittest.mock import MagicMock, patch

from config import config
from controller import Controller


class TestVrPanelAnchor(unittest.TestCase):
    def test_valid_anchor_is_requested_on_the_overlay(self) -> None:
        with patch("controller.model") as model:
            response = Controller.setOverlayVrPanelAnchor("RightHand")
        self.assertEqual(response, {"status": 200, "result": "RightHand"})
        model.requestVrPanelAnchor.assert_called_once_with("RightHand")

    def test_unknown_anchor_is_rejected(self) -> None:
        for bad in ("Foot", None, 1):
            with self.subTest(bad=bad), patch("controller.model") as model:
                response = Controller.setOverlayVrPanelAnchor(bad)
                self.assertNotEqual(response["status"], 200)
                model.requestVrPanelAnchor.assert_not_called()

    def test_committed_position_tells_the_ui_the_anchor(self) -> None:
        """掴み・呼び戻し・操作バーのどれで固定先が変わっても、確定したら UI へ知らせる。"""
        original = config.OVERLAY_VR_PANEL_SETTINGS
        controller = Controller.__new__(Controller)
        controller.run = MagicMock()
        controller.run_mapping = {"overlay_vr_panel_anchor": "/run/overlay_vr_panel_anchor"}
        try:
            controller._onOverlayPositionChanged("panel", {"x_pos": 0.1, "ui_scaling": 0.4, "tracker": "Playspace"})
        finally:
            config.OVERLAY_VR_PANEL_SETTINGS = original
        controller.run.assert_called_once_with(200, "/run/overlay_vr_panel_anchor", "Playspace")


class TestVrPanelLock(unittest.TestCase):
    def setUp(self) -> None:
        self.original = config.OVERLAY_VR_PANEL_LOCKED

    def tearDown(self) -> None:
        config.OVERLAY_VR_PANEL_LOCKED = self.original

    def test_lock_and_unlock(self) -> None:
        with patch("controller.model") as model:
            self.assertEqual(Controller.setEnableOverlayVrPanelLocked(), {"status": 200, "result": True})
            model.setVrPanelLocked.assert_called_with(True)
            self.assertEqual(Controller.setDisableOverlayVrPanelLocked(), {"status": 200, "result": False})
            model.setVrPanelLocked.assert_called_with(False)
        self.assertEqual(Controller.getOverlayVrPanelLocked(Controller.__new__(Controller)), {"status": 200, "result": False})


class TestVrPanelFontSize(unittest.TestCase):
    def setUp(self) -> None:
        self.original = config.OVERLAY_VR_PANEL_FONT_SIZE

    def tearDown(self) -> None:
        config.OVERLAY_VR_PANEL_FONT_SIZE = self.original

    def test_valid_size_is_saved(self) -> None:
        self.assertEqual(Controller.setOverlayVrPanelFontSize(20), {"status": 200, "result": 20})
        self.assertEqual(config.OVERLAY_VR_PANEL_FONT_SIZE, 20)

    def test_out_of_range_or_non_integer_is_rejected(self) -> None:
        for bad in (13, 29, 17.5, "20", True, None):
            with self.subTest(bad=bad):
                self.assertNotEqual(Controller.setOverlayVrPanelFontSize(bad)["status"], 200)
                self.assertEqual(config.OVERLAY_VR_PANEL_FONT_SIZE, self.original)


class TestVrLauncher(unittest.TestCase):
    def setUp(self) -> None:
        self.original = (config.OVERLAY_VR_LAUNCHER_SETTINGS, config.OVERLAY_VR_LAUNCHER_AUTO_HIDE)

    def tearDown(self) -> None:
        config.OVERLAY_VR_LAUNCHER_SETTINGS, config.OVERLAY_VR_LAUNCHER_AUTO_HIDE = self.original

    def test_switching_hand_mirrors_the_saved_position(self) -> None:
        config.OVERLAY_VR_LAUNCHER_SETTINGS = {**config.OVERLAY_VR_LAUNCHER_SETTINGS, "tracker": "LeftHand", "x_pos": 0.02, "y_rotation": 10.0}
        with patch("controller.model") as model:
            response = Controller.setOverlayVrLauncherHand("RightHand")
        self.assertEqual(response, {"status": 200, "result": "RightHand"})
        self.assertEqual(config.OVERLAY_VR_LAUNCHER_SETTINGS["x_pos"], -0.02)
        self.assertEqual(config.OVERLAY_VR_LAUNCHER_SETTINGS["y_rotation"], -10.0)
        model.updateVrLauncherPosition.assert_called_once_with()

    def test_reset_returns_the_launcher_to_the_default_left_hand(self) -> None:
        from config import DEFAULT_OVERLAY_VR_LAUNCHER_SETTINGS

        config.OVERLAY_VR_LAUNCHER_SETTINGS = {**config.OVERLAY_VR_LAUNCHER_SETTINGS, "tracker": "RightHand", "x_pos": 5.0, "ui_scaling": 0.01}
        controller = Controller()
        controller.run_mapping = {"overlay_vr_launcher_hand": "/run/overlay_vr_launcher_hand"}
        with patch("controller.model") as model, patch.object(controller, "run") as run:
            response = controller.resetVrLauncher()
        self.assertEqual(response, {"status": 200, "result": True})
        self.assertEqual(config.OVERLAY_VR_LAUNCHER_SETTINGS, DEFAULT_OVERLAY_VR_LAUNCHER_SETTINGS)  # 左手・初期の位置と大きさ
        model.resetVrLauncher.assert_called_once_with()  # VR につながっていれば、手首へ吸い寄せて戻る
        run.assert_called_once_with(200, controller.run_mapping["overlay_vr_launcher_hand"], "LeftHand")  # UI の手の表示も戻す
        config.OVERLAY_VR_LAUNCHER_SETTINGS["x_pos"] = 1.0  # 初期値の元の dict を書き換えない
        self.assertEqual(DEFAULT_OVERLAY_VR_LAUNCHER_SETTINGS["x_pos"], 0.0)

    def test_a_changed_launcher_position_is_saved_and_the_hand_is_pushed_to_the_ui(self) -> None:
        controller = Controller()
        controller.run_mapping = {"overlay_vr_launcher_hand": "/run/overlay_vr_launcher_hand"}
        position = {**{k: 0.0 for k in ("x_pos", "y_pos", "z_pos", "x_rotation", "y_rotation", "z_rotation")}, "ui_scaling": 0.303, "tracker": "LeftHand"}
        with patch.object(controller, "run") as run:
            controller._onOverlayPositionChanged("launcher", position)
        self.assertEqual(config.OVERLAY_VR_LAUNCHER_SETTINGS["tracker"], "LeftHand")
        run.assert_called_once_with(200, "/run/overlay_vr_launcher_hand", "LeftHand")

    def test_same_hand_or_unknown_value_does_not_move(self) -> None:
        config.OVERLAY_VR_LAUNCHER_SETTINGS = {**config.OVERLAY_VR_LAUNCHER_SETTINGS, "tracker": "LeftHand"}
        with patch("controller.model") as model:
            self.assertEqual(Controller.setOverlayVrLauncherHand("LeftHand")["result"], "LeftHand")
            self.assertNotEqual(Controller.setOverlayVrLauncherHand("HMD")["status"], 200)
            model.updateVrLauncherPosition.assert_not_called()

    def test_auto_hide(self) -> None:
        with patch("controller.model") as model:
            Controller.setDisableOverlayVrLauncherAutoHide()
            model.setVrLauncherAutoHide.assert_called_with(False)
            Controller.setEnableOverlayVrLauncherAutoHide()
            model.setVrLauncherAutoHide.assert_called_with(True)


if __name__ == "__main__":
    unittest.main()


class TestVrTooltipSetting(unittest.TestCase):
    def setUp(self) -> None:
        self.original = config.OVERLAY_VR_TOOLTIP

    def tearDown(self) -> None:
        config.OVERLAY_VR_TOOLTIP = self.original

    def test_default_is_on_and_toggles(self) -> None:
        self.assertIs(Controller.getOverlayVrTooltip()["result"], self.original)
        self.assertEqual(Controller.setDisableOverlayVrTooltip(), {"status": 200, "result": False})
        self.assertIs(config.OVERLAY_VR_TOOLTIP, False)
        self.assertEqual(Controller.setEnableOverlayVrTooltip(), {"status": 200, "result": True})
