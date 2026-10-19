"""オーバーレイの起動・停止: 字幕 (一行 / 複数行) と VR UI のどれかがONなら動かし、全部OFFなら止める。"""

import unittest
from unittest.mock import patch

from config import config
from controller import Controller

_KEYS = ("OVERLAY_SMALL_LOG", "OVERLAY_LARGE_LOG", "OVERLAY_VR_PANEL")


class TestOverlayRunning(unittest.TestCase):
    def setUp(self) -> None:
        self.original = {key: getattr(config, key) for key in _KEYS}
        for key in _KEYS:
            setattr(config, key, False)
        patcher = patch("controller.model")
        self.model = patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self) -> None:
        for key, value in self.original.items():
            setattr(config, key, value)

    def test_vr_panel_alone_starts_the_overlay(self) -> None:
        response = Controller.setEnableOverlayVrPanel()
        self.assertEqual(response, {"status": 200, "result": True})
        self.model.setVrPanelEnabled.assert_called_with(True)
        self.model.startOverlay.assert_called_once_with()
        self.model.shutdownOverlay.assert_not_called()

    def test_last_one_off_stops_the_overlay(self) -> None:
        Controller.setEnableOverlayVrPanel()
        Controller.setDisableOverlayVrPanel()
        self.model.setVrPanelEnabled.assert_called_with(False)
        self.model.shutdownOverlay.assert_called_once_with()

    def test_turning_off_subtitles_keeps_the_vr_panel_running(self) -> None:
        Controller.setEnableOverlaySmallLog()
        Controller.setEnableOverlayVrPanel()
        Controller.setDisableOverlaySmallLog()
        self.model.clearOverlayImageSmallLog.assert_called_once_with()
        self.model.shutdownOverlay.assert_not_called()

    def test_turning_off_the_vr_panel_keeps_subtitles_running(self) -> None:
        Controller.setEnableOverlayLargeLog()
        Controller.setEnableOverlayVrPanel()
        Controller.setDisableOverlayVrPanel()
        self.model.setVrPanelEnabled.assert_called_with(False)
        self.model.shutdownOverlay.assert_not_called()


if __name__ == "__main__":
    unittest.main()
