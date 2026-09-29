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


if __name__ == "__main__":
    unittest.main()
