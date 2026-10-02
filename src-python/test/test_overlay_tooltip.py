"""Tooltip generation, alpha, and OpenVR ownership without hardware."""
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import openvr
from models.overlay.overlay import (
    LAUNCHER,
    PANEL,
    TOOLBAR,
    TOOLTIP,
    Overlay,
    atlasMaskArray,
)
from models.overlay.overlay_tooltip import (
    marker_matches,
    tooltip_mask,
    validate_tooltip,
)


def payload(epoch=1, revision=1, **changes):
    return {"epoch": epoch, "revision": revision, "visible": True, "region": LAUNCHER,
            "button": [10, 20, 64, 64], "size": [360, 60], "arrow_x": 42, **changes}


def marked_pixels(layout, state, scale=1):
    w, h = layout["atlas"]
    pixels = np.zeros((round(h * scale), round(w * scale), 4), dtype=np.uint8)
    x, y, _, _ = layout["regions"][TOOLTIP]
    bits = (state["epoch"] << 32) | state["revision"]
    for i in range(80):
        color = 255 if bits >> (79 - i) & 1 else 0
        pixels[round(y * scale):round((y + 8) * scale), round((x + i * 4) * scale):round((x + i * 4 + 4) * scale), :3] = color
    return pixels


def overlay_fixture():
    settings = {"tracker": "Playspace", "ui_scaling": 0.88, "x_pos": 0, "y_pos": 0,
                "z_pos": 0, "x_rotation": 0, "y_rotation": 0, "z_rotation": 0}
    overlay = Overlay({LAUNCHER: settings.copy(), PANEL: settings.copy()})
    overlay.overlay = MagicMock(spec=openvr.IVROverlay)
    overlay.overlay_system = MagicMock()
    overlay.tooltip_handle = 90
    overlay.handle = {LAUNCHER: 1, PANEL: 2}
    overlay.gl = {"size": overlay.layout["atlas"], "texture": 10, "vr_texture": object(), "GL": MagicMock()}
    overlay.launcher_interactive = True
    overlay.layout_applied = overlay.layout
    overlay.panel_image_size = overlay.layout["atlas"]
    overlay.window_size = overlay.layout["atlas"]
    overlay.pointer_notified = (30, overlay.layout["regions"][LAUNCHER][1] + 30)
    return overlay


class TooltipValidationTest(unittest.TestCase):
    def test_valid_and_detached(self):
        original = payload()
        validated = validate_tooltip(original)
        original["button"][0] = 123
        self.assertEqual(validated["button"][0], 10)
        self.assertEqual(validated["mode"], "hover")
        self.assertEqual(validate_tooltip({"epoch": 1, "revision": 1, "visible": False})["visible"], False)

    def test_invalid_values(self):
        changes = [{"epoch": True}, {"epoch": 0}, {"epoch": 1 << 48}, {"revision": 1 << 32},
                   {"revision": 1.0}, {"visible": 1}, {"region": PANEL}, {"mode": "other"},
                   {"button": [float("nan"), 0, 1, 1]}, {"button": [0, True, 1, 1]},
                   {"button": [0, 0, -1, 1]}, {"button": [879, 0, 2, 1]}, {"button": [10**1000, 0, 1, 1]},
                   {"size": [359, 20]}, {"size": [360, 105]}, {"size": [360, float("inf")]},
                   {"arrow_x": True}, {"arrow_x": 349}, {"unknown": 1}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_tooltip(payload(**change))
        for malformed in (None, [], {}, {"epoch": 1, "revision": 1, "visible": False, "size": [360, 10]}):
            with self.subTest(malformed=malformed), self.assertRaises(ValueError):
                validate_tooltip(malformed)


class TooltipCaptureTest(unittest.TestCase):
    def test_marker_epoch_revision_and_dpi(self):
        overlay = overlay_fixture()
        state = payload(overlay.tooltip_epoch, 567)
        for scale in (1, 1.25, 1.5, 2):
            pixels = marked_pixels(overlay.layout, state, scale)
            self.assertTrue(marker_matches(pixels, overlay.layout, state))
            self.assertFalse(marker_matches(pixels, overlay.layout, {**state, "revision": 568}))
            self.assertFalse(marker_matches(pixels, overlay.layout, {**state, "epoch": state["epoch"] + 1}))

    def test_mask_body_arrow_and_transparent_marker(self):
        overlay = overlay_fixture()
        w, h = overlay.layout["atlas"]
        static = atlasMaskArray((w, h), overlay.layout)
        before = static.copy()
        state = payload()
        mask = tooltip_mask((w, h), overlay.layout, state, static)
        x, y, _, _ = overlay.layout["regions"][TOOLTIP]
        self.assertFalse(mask[y:y + 8, x:x + 360].any())
        self.assertEqual(mask[y + 8, x], 0)
        self.assertEqual(mask[y + 30, x + 30], 255)
        self.assertEqual(mask[y + 70, x + 42], 255)
        self.assertEqual(mask[y + 70, x + 100], 0)
        np.testing.assert_array_equal(static, before)

    def test_shared_upload_and_matching_capture_only(self):
        overlay = overlay_fixture()
        state = payload(overlay.tooltip_epoch, 1)
        overlay.setTooltip(state)
        overlay.applyTooltipRequests()
        overlay.updateTooltip()
        capture = (b"same", None, (0, 0) + overlay.window_size)
        GL = overlay.gl["GL"]
        with patch.object(overlay, "prepareGl", return_value=GL), patch("models.overlay.overlay.window_capture.bgraFromCapture", return_value=marked_pixels(overlay.layout, state)):
            overlay.transferCapture(capture, 1)
        self.assertTrue(overlay.tooltip_ready)
        GL.glTexSubImage2D.assert_called_once()
        self.assertEqual(overlay.overlay.setOverlayTexture.call_count, 3)
        overlay.overlay.showOverlay.assert_called_with(90)
        # Same raw frame must be re-evaluated when a new ready generation arrives.
        new_state = payload(overlay.tooltip_epoch, 2)
        overlay.setTooltip(new_state)
        overlay.applyTooltipRequests()
        with patch.object(overlay, "prepareGl", return_value=GL), patch("models.overlay.overlay.window_capture.bgraFromCapture", return_value=marked_pixels(overlay.layout, state)):
            overlay.transferCapture(capture, 2)
        self.assertFalse(overlay.tooltip_ready)
        self.assertEqual(GL.glTexSubImage2D.call_count, 2)
        overlay.overlay.hideOverlay.assert_called_with(90)


class TooltipLifecycleTest(unittest.TestCase):
    def test_queue_rejects_delayed_epochs_and_revisions(self):
        overlay = overlay_fixture()
        epoch = overlay.tooltip_epoch
        overlay.overlay.reset_mock()
        overlay.setTooltip(payload(epoch, 3))
        overlay.setTooltip(payload(epoch, 2))
        overlay.setTooltip(payload(epoch - 1, 4))
        # Sender cannot call OpenVR.
        overlay.overlay.assert_not_called()
        self.assertEqual(overlay.overlay.mock_calls, [])
        overlay.applyTooltipRequests()
        self.assertEqual(overlay.tooltip_state["revision"], 3)
        overlay.setTooltip({"epoch": epoch, "revision": 4, "visible": False})
        overlay.setTooltip(payload(epoch, 3))
        overlay.applyTooltipRequests()
        self.assertIsNone(overlay.tooltip_state)
        overlay.resetTooltipEpoch()
        self.assertGreater(overlay.tooltip_epoch, epoch)
        overlay.setTooltip(payload(epoch, 100))
        overlay.applyTooltipRequests()
        self.assertIsNone(overlay.tooltip_state)

    def test_parent_hide_grab_resize_off_and_focus(self):
        for attribute, value in (("launcher_interactive", False), ("vr_panel_enabled", False),
                                 ("grabbing", {}), ("resizing", {}), ("panel_stopped", True)):
            with self.subTest(attribute=attribute):
                overlay = overlay_fixture()
                epoch = overlay.tooltip_epoch
                overlay.setTooltip(payload(epoch, 1, mode="focus"))
                overlay.applyTooltipRequests()
                setattr(overlay, attribute, value)
                overlay.updateTooltip()
                self.assertIsNone(overlay.tooltip_state)
                self.assertEqual(overlay.tooltip_revision, 1)

    def test_pointer_leave_before_notification_threshold(self):
        overlay = overlay_fixture()
        overlay.setTooltip(payload(overlay.tooltip_epoch, 1))
        overlay.applyTooltipRequests()
        x, y, _, _ = overlay.layout["regions"][LAUNCHER]
        overlay.pointer_notified = (x + 73, y + 30)
        overlay.notifyPointer((x + 74, y + 30))  # 通知の不感帯の中: UI のホバーも残っているので、説明も残す
        self.assertIsNotNone(overlay.tooltip_state)
        overlay.notifyPointer((x + 80, y + 30))  # 十分に外れて通知した
        self.assertIsNone(overlay.tooltip_state)

    def test_pose_width_and_input_exclusion(self):
        overlay = overlay_fixture()
        overlay.setTooltip(payload(overlay.tooltip_epoch, 1))
        overlay.applyTooltipRequests()
        overlay.tooltip_ready = True
        overlay.updateTooltip()
        overlay.overlay.setOverlayWidthInMeters.assert_called_with(90, 0.36)
        call = overlay.overlay.setOverlayTransformAbsolute.call_args.args
        pose = call[2]
        self.assertAlmostEqual(pose[0][3], -0.248)
        self.assertAlmostEqual(pose[1][3], 0.089)
        self.assertAlmostEqual(pose[2][3], 0.004)
        self.assertNotIn(TOOLTIP, overlay.vrRegionSizes())
        self.assertNotIn(TOOLTIP, overlay.settings)
        self.assertEqual(overlay.vrRegionHandles()[TOOLTIP], 90)

    def test_toolbar_tracker_and_cleanup(self):
        overlay = overlay_fixture()
        overlay.toolbar_handle = 80
        overlay.toolbar_visible = True
        overlay.toolbar_relative = np.eye(4)[:3, :]
        overlay.toolbar_tracker_index = 2
        overlay.setTooltip(payload(overlay.tooltip_epoch, 1, region=TOOLBAR, mode="focus"))
        overlay.applyTooltipRequests()
        overlay.tooltip_ready = True
        overlay.updateTooltip()
        self.assertEqual(overlay.overlay.setOverlayTransformTrackedDeviceRelative.call_args.args[:2], (90, 2))
        steam = overlay.overlay
        overlay.destroyOverlays()
        steam.destroyOverlay.assert_any_call(90)
        self.assertIsNone(overlay.tooltip_handle)

    def test_short_off_on_changes_epoch_and_clears_ready(self):
        overlay = overlay_fixture()
        epoch = overlay.tooltip_epoch
        overlay.setTooltip(payload(epoch, 1))
        overlay.applyTooltipRequests()
        overlay.tooltip_ready = True
        overlay.setVrPanelEnabled(False)
        overlay.setVrPanelEnabled(True)
        overlay.applyVrPanelEnabled()
        self.assertEqual(overlay.tooltip_epoch, epoch + 2)
        self.assertIsNone(overlay.tooltip_state)
        self.assertFalse(overlay.tooltip_ready)

    def test_parent_closes_before_ready_arrives(self):
        overlay = overlay_fixture()
        overlay.toolbar_handle = 80
        overlay.toolbar_visible = True
        epoch = overlay.tooltip_epoch
        overlay.setToolbarVisible(False)
        overlay.toolbar_visible = True
        overlay.setTooltip(payload(epoch, 1, region=TOOLBAR, mode="focus"))
        overlay.applyTooltipRequests()
        self.assertIsNone(overlay.tooltip_state)


class TooltipBridgeTest(unittest.TestCase):
    def test_controller_validates_and_layout_preserves_epoch(self):
        from controller import Controller, vrLayoutToJson
        overlay = overlay_fixture()
        with patch("controller.model") as model:
            self.assertNotEqual(Controller.setVrPanelTooltip(payload(epoch=True))["status"], 200)
            model.setVrPanelTooltip.assert_not_called()
            self.assertEqual(Controller.setVrPanelTooltip(payload())["status"], 200)
            model.setVrPanelTooltip.assert_called_once()
            model.overlay = overlay
            result = Controller.getVrPanelLayout()["result"]
            self.assertEqual(result["tooltip_epoch"], overlay.tooltip_epoch)
        self.assertNotIn("tooltip_epoch", vrLayoutToJson(overlay.layout))

    def test_model_does_not_initialize_for_tooltip(self):
        from model import Model
        model = object.__new__(Model)
        model.ensure_initialized = MagicMock(side_effect=AssertionError("must not initialize"))
        model.setVrPanelTooltip(payload())
        model.overlay = MagicMock()
        model.setVrPanelTooltip(payload())
        model.overlay.setTooltip.assert_called_once()
        model.ensure_initialized.assert_not_called()


class TooltipReviewFixesTest(unittest.TestCase):
    def test_pointer_near_the_edge_does_not_repeat_epoch_resets(self):
        """通知済みの位置が縁の内側で、現在位置が縁のすぐ外 (不感帯の中) でも、epoch を繰り返し進めない。"""
        overlay = overlay_fixture()
        ry = overlay.layout["regions"][LAUNCHER][1]
        overlay.pointer_notified = (10 + 62, ry + 30)  # ボタン (x 10..74) の内側
        overlay.tooltip_state = validate_tooltip(payload(overlay.tooltip_epoch, 1))
        epoch = overlay.tooltip_epoch
        for _ in range(5):
            overlay.notifyPointer((10 + 65, ry + 30))  # 3px 外 (不感帯: 通知しない)
        self.assertEqual(overlay.tooltip_epoch, epoch)
        overlay.notifyPointer((10 + 90, ry + 30))  # 十分に外れた
        self.assertEqual(overlay.tooltip_epoch, epoch + 1)

    def test_tooltip_error_is_not_counted_as_a_capture_failure(self):
        overlay = overlay_fixture()
        overlay.tooltip_state = validate_tooltip(payload(overlay.tooltip_epoch, 1))
        overlay.tooltip_ready = True
        overlay.overlay.setOverlayTransformAbsolute.side_effect = RuntimeError("OpenVR")
        with patch("models.overlay.overlay.errorLogging") as logged:
            overlay.safeUpdateTooltip()  # 例外は出さない
        logged.assert_called_once()
        self.assertIsNone(overlay.tooltip_state)

    def test_failing_hide_does_not_break_the_epoch_reset(self):
        overlay = overlay_fixture()
        overlay.tooltip_shown = True
        overlay.overlay.hideOverlay.side_effect = RuntimeError("OpenVR")
        callback = MagicMock()
        overlay.layout_callback = callback
        with patch("models.overlay.overlay.errorLogging"):
            overlay.resetTooltipEpoch()
        callback.assert_called_once()  # UI へは通知される

    def test_hidden_tooltip_is_not_hidden_again(self):
        overlay = overlay_fixture()
        overlay.overlay.reset_mock()
        overlay.hideTooltip()
        overlay.hideTooltip()
        overlay.overlay.hideOverlay.assert_not_called()
        overlay.tooltip_shown = True
        overlay.hideTooltip()
        overlay.overlay.hideOverlay.assert_called_once_with(90)

    def test_apply_layout_does_not_set_tooltip_bounds(self):
        from models.overlay.overlay import TOOLTIP as TIP

        overlay = overlay_fixture()
        overlay.handle = {LAUNCHER: 1, PANEL: 2}
        overlay.applyLayout()
        handles = [c.args[0] for c in overlay.overlay.setOverlayTextureBounds.call_args_list]
        self.assertNotIn(overlay.tooltip_handle, handles)
        self.assertIn(TIP, overlay.layout["regions"])
