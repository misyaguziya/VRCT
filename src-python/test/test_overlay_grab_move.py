"""VR内の掴み移動 (Overlay.commitPosition / overlay_utils.matrix_to_position) のテスト。

コントローラ入力やSteamVRを使う updateGrab() 本体は実機でしか検証できない。
ここでは「掴んで離した後の行列を設定値へ正しく逆算できるか」だけを確かめる。
"""
import unittest
from unittest.mock import MagicMock

import numpy as np
from models.overlay import overlay_utils as utils
from models.overlay.overlay import (
    Overlay,
    getHMDBaseMatrix,
    getLeftHandBaseMatrix,
    getRightHandBaseMatrix,
)

KEYS = ("x_pos", "y_pos", "z_pos", "x_rotation", "y_rotation", "z_rotation")


def _relative(base, p):
    return utils.transform_matrix(base, (p[0], p[1], -p[2]), (p[3], p[4], p[5]))


class MatrixToPositionTest(unittest.TestCase):
    def test_roundtrip_all_bases(self):
        rng = np.random.default_rng(0)
        for base in (getHMDBaseMatrix(), getLeftHandBaseMatrix(), getRightHandBaseMatrix()):
            for _ in range(50):
                p = [*rng.uniform(-1, 1, 3), *rng.uniform(-170, 170, 3)]
                p[4] = rng.uniform(-80, 80)  # y回転は±90未満で一意
                got = utils.matrix_to_position(base, _relative(base, p))
                np.testing.assert_allclose(got, p, atol=1e-6)

    def test_gimbal_lock_reproduces_same_matrix(self):
        base = getHMDBaseMatrix()
        m = _relative(base, (0.1, 0.2, 0.3, 30.0, 90.0, 10.0))
        got = utils.matrix_to_position(base, m)
        np.testing.assert_allclose(_relative(base, got), m, atol=1e-6)


class CommitPositionTest(unittest.TestCase):
    def test_commit_updates_settings_and_calls_callback(self):
        settings = {k: 0.0 for k in KEYS}
        settings.update(tracker="HMD", opacity=1.0, fadeout_duration=0)
        overlay = Overlay({"small": settings})
        overlay.overlay_system = MagicMock()
        callback = MagicMock()
        overlay.position_changed_callback = callback

        target = (0.1, -0.2, 0.8, 5.0, -10.0, 15.0)
        overlay.commitPosition("small", _relative(getHMDBaseMatrix(), target))

        size, position = callback.call_args.args
        self.assertEqual(size, "small")
        self.assertEqual(set(position), set(KEYS))
        np.testing.assert_allclose([position[k] for k in KEYS], target, atol=1e-3)
        np.testing.assert_allclose([overlay.settings["small"][k] for k in KEYS], target, atol=1e-3)


class UpdateGrabFlowTest(unittest.TestCase):
    """SteamVRを偽物に差し替え、長押し→掴み→離す→確定の流れを通す。"""

    HMD, LEFT, RIGHT = 0, 1, 2

    def setUp(self):
        import openvr
        settings = {k: 0.0 for k in KEYS}
        settings.update(tracker="LeftHand", opacity=1.0, fadeout_duration=0, z_pos=0.0)
        self.overlay = Overlay({"small": settings})
        self.grip = False

        system = MagicMock()
        system.getTrackedDeviceIndexForControllerRole.side_effect = (
            lambda role: self.LEFT if role == openvr.TrackedControllerRole_LeftHand else self.RIGHT
        )

        def fill_poses(origin, t, poses):
            # 実物の pyopenvr と同じく、渡された配列へ書き込むだけ (戻り値に頼らない)
            self.assertIsNotNone(poses)
            for i in (self.HMD, self.LEFT, self.RIGHT):
                poses[i].bPoseIsValid = True
                for r in range(3):
                    for c in range(4):
                        poses[i].mDeviceToAbsoluteTracking[r][c] = 1.0 if r == c else 0.0
        system.getDeviceToAbsoluteTrackingPose.side_effect = fill_poses

        def controller_state(index):
            state = MagicMock()
            state.ulButtonPressed = (1 << openvr.k_EButton_Grip) if (self.grip and index == self.RIGHT) else 0
            return True, state
        system.getControllerState.side_effect = controller_state

        ovr = MagicMock()
        hit = MagicMock()
        hit.fDistance = 0.5
        hit.vNormal.v = [0.0, 0.0, 1.0]
        hit.vPoint.v = [0.0, 0.0, -0.5]
        ovr.computeOverlayIntersection.return_value = (True, hit)

        self.overlay.overlay_system = system
        self.overlay.overlay = ovr
        self.overlay.handle = {"small": 10}
        self.overlay.pointer_handle = 11
        self.callback = MagicMock()
        self.overlay.position_changed_callback = self.callback

    def test_hold_grab_release_commits(self):
        from unittest.mock import patch
        t = [100.0]
        with patch("models.overlay.overlay.time.monotonic", side_effect=lambda: t[0]):
            self.overlay.updateGrab()  # 指しているだけ → 白ポインタ
            self.overlay.overlay.showOverlay.assert_called_with(11)
            self.grip = True
            self.overlay.updateGrab()  # 長押し開始
            self.assertIsNotNone(self.overlay.grab_candidate)
            t[0] += 0.6
            self.overlay.updateGrab()  # 0.5s経過 → 掴む
            self.assertIsNotNone(self.overlay.grabbing)
            self.overlay.updateGrab()  # 掴み中の追従
            self.grip = False
            self.overlay.updateGrab()  # 離す → 確定
        self.assertIsNone(self.overlay.grabbing)
        self.callback.assert_called_once()


class PanelInputTest(unittest.TestCase):
    """VRパネルへの入力: UV→ピクセル変換とトリガーのクリック判定。"""

    def test_trigger_click_and_scroll(self):
        from unittest.mock import patch

        import openvr

        overlay = Overlay({})
        overlay.panel_hwnd = 123
        overlay.panel_image_size = (900, 700)
        results = MagicMock()
        results.vUVs.v = [0.5, 0.25]  # 左下原点 → y = (1-0.25)*700
        state = MagicMock()
        state.rAxis[0].y = 0.0

        with patch("models.overlay.overlay.window_capture") as wc:
            state.ulButtonPressed = 0
            overlay.handlePanelInput(1, results, state)
            wc.mouseMove.assert_called_with(123, 450, 525, pressed=False)
            state.ulButtonPressed = 1 << openvr.k_EButton_SteamVR_Trigger
            overlay.handlePanelInput(1, results, state)
            wc.mouseDown.assert_called_once_with(123, 450, 525)
            # パネルの外で離しても mouseUp を送る
            overlay.handlePanelInput(1, None, state)
            wc.mouseUp.assert_called_once_with(123, 450, 525)
            state.ulButtonPressed = 0
            state.rAxis[0].y = -1.0
            overlay.handlePanelInput(1, results, state)
            wc.mouseWheel.assert_called_once_with(123, 450, 525, -60)


if __name__ == "__main__":
    unittest.main()
