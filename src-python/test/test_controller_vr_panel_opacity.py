"""VR UIのログウィンドウの不透明度 (/get|set/data/overlay_vr_panel_opacity) のテスト。"""

import unittest
from unittest.mock import patch

from config import config
from controller import Controller


class TestVrPanelOpacity(unittest.TestCase):
    def setUp(self) -> None:
        self.original = config.OVERLAY_VR_PANEL_SETTINGS

    def tearDown(self) -> None:
        config.OVERLAY_VR_PANEL_SETTINGS = self.original

    def test_set_saves_only_opacity_and_applies_it(self) -> None:
        with patch("controller.model") as model:
            response = Controller.setOverlayVrPanelOpacity(0.6)
        self.assertEqual(response, {"status": 200, "result": 0.6})
        self.assertEqual(config.OVERLAY_VR_PANEL_SETTINGS, {**self.original, "opacity": 0.6})
        model.updateOverlayVrPanelOpacity.assert_called_once_with()
        self.assertEqual(Controller.getOverlayVrPanelOpacity(), {"status": 200, "result": 0.6})

    def test_set_rounds_float_noise(self) -> None:
        with patch("controller.model"):
            response = Controller.setOverlayVrPanelOpacity(0.1 + 0.2)
        self.assertEqual(response["result"], 0.3)

    def test_set_rejects_invisible_or_invalid_values(self) -> None:
        for bad in (0.0, 0.19, 1.01, -1, "abc", None, float("nan")):
            with self.subTest(bad=bad), patch("controller.model") as model:
                response = Controller.setOverlayVrPanelOpacity(bad)
                self.assertNotEqual(response["status"], 200)
                self.assertEqual(config.OVERLAY_VR_PANEL_SETTINGS, self.original)
                model.updateOverlayVrPanelOpacity.assert_not_called()


if __name__ == "__main__":
    unittest.main()
