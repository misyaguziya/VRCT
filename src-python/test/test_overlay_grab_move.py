"""VR内の掴み移動 (Overlay.commitPosition / overlay_utils.matrix_to_position) のテスト。

コントローラ入力やSteamVRを使う updateGrab() 本体は実機でしか検証できない。
ここでは「掴んで離した後の行列を設定値へ正しく逆算できるか」だけを確かめる。
"""
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
from models.overlay import overlay_utils as utils
from models.overlay.overlay import (
    LAUNCHER,
    PANEL,
    VR_ATLAS_SIZE,
    VR_REGIONS,
    Overlay,
    getHMDBaseMatrix,
    getLeftHandBaseMatrix,
    getRightHandBaseMatrix,
)

def pytest_approx(value):
    import pytest
    return pytest.approx(value)


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
        settings.update(tracker="HMD", opacity=1.0, fadeout_duration=0, ui_scaling=1.0)
        overlay = Overlay({"small": settings})
        overlay.overlay_system = MagicMock()
        callback = MagicMock()
        overlay.position_changed_callback = callback

        target = (0.1, -0.2, 0.8, 5.0, -10.0, 15.0)
        overlay.commitPosition("small", _relative(getHMDBaseMatrix(), target))

        size, position = callback.call_args.args
        self.assertEqual(size, "small")
        self.assertEqual(set(position), {*KEYS, "ui_scaling", "tracker"})
        np.testing.assert_allclose([position[k] for k in KEYS], target, atol=1e-3)
        np.testing.assert_allclose([overlay.settings["small"][k] for k in KEYS], target, atol=1e-3)


class UpdateGrabFlowTest(unittest.TestCase):
    """SteamVRを偽物に差し替え、長押し→掴み→離す→確定の流れを通す。"""

    HMD, LEFT, RIGHT = 0, 1, 2

    def setUp(self):
        import openvr
        settings = {k: 0.0 for k in KEYS}
        settings.update(tracker="LeftHand", opacity=1.0, fadeout_duration=0, z_pos=0.0, ui_scaling=1.0)
        self.overlay = Overlay({"small": settings})
        self.grip = False
        self.trigger = False
        self.right_z = 0.0  # 右手の位置 (z)。前方は -Z
        self.stick = (0.0, 0.0)  # 右手のスティック (x, y)

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
            poses[self.RIGHT].mDeviceToAbsoluteTracking[2][3] = self.right_z
        system.getDeviceToAbsoluteTrackingPose.side_effect = fill_poses

        def controller_state(index):
            state = MagicMock()
            pressed = 0
            if index == self.RIGHT:
                pressed |= (1 << openvr.k_EButton_Grip) if self.grip else 0
                pressed |= (1 << openvr.k_EButton_SteamVR_Trigger) if self.trigger else 0
            state.ulButtonPressed = pressed
            state.rAxis = [MagicMock(x=self.stick[0], y=self.stick[1]) if index == self.RIGHT else MagicMock(x=0.0, y=0.0)]
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
        self.overlay.pointer_handles = {"dot": 11, "plus": 12, "minus": 13}
        self.callback = MagicMock()
        self.overlay.position_changed_callback = self.callback

    def test_press_grab_release_commits(self):
        from unittest.mock import patch
        t = [100.0]
        with patch("models.overlay.overlay.time.monotonic", side_effect=lambda: t[0]):
            self.overlay.updateGrab()  # 指しているだけ → ポインタ
            self.overlay.overlay.showOverlay.assert_called_with(11)
            self.grip = True
            self.overlay.updateGrab()  # 押した瞬間に掴む
            self.assertIsNotNone(self.overlay.grabbing)
            t[0] += 0.2
            self.overlay.updateGrab()  # 掴み中の追従。ポインタは大きくなる
            self.overlay.overlay.setOverlayWidthInMeters.assert_called_with(11, pytest_approx(0.0075 * 1.8))
            self.grip = False
            self.overlay.updateGrab()  # 離す → 確定
        self.assertIsNone(self.overlay.grabbing)
        self.callback.assert_called_once()

    def test_grip_held_before_pointing_does_not_grab(self):
        """グリップを押したままレーザーを当てても掴まない (VRChatで物を持っている時など)。"""
        hit = self.overlay.overlay.computeOverlayIntersection.return_value
        self.overlay.overlay.computeOverlayIntersection.return_value = (False, hit[1])
        self.grip = True
        self.overlay.updateGrab()  # どこも指さずにグリップ
        self.overlay.overlay.computeOverlayIntersection.return_value = hit
        self.overlay.updateGrab()  # 押したままオーバーレイを指す
        self.assertIsNone(self.overlay.grabbing)

    def _grab(self, t):
        self.grip = True
        self.overlay.updateGrab()
        self.overlay.updateGrab()
        self.assertIsNotNone(self.overlay.grabbing)

    def test_trigger_push_forward_scales_up_and_saves_width(self):
        from unittest.mock import patch
        t = [100.0]
        self.overlay.settings["small"]["ui_scaling"] = 1.0
        with patch("models.overlay.overlay.time.monotonic", side_effect=lambda: t[0]):
            self._grab(t)
            self.trigger = True
            self.overlay.updateGrab()  # 拡大縮小の開始
            self.right_z = -0.15  # 前へ15cm押し出す → 2倍
            self.overlay.updateGrab()
            self.overlay.overlay.showOverlay.assert_called_with(12)  # + アイコン
            self.assertAlmostEqual(self.overlay.settings["small"]["ui_scaling"], 2.0, places=5)
            self.trigger = False
            self.overlay.updateGrab()  # 掴み直し
            self.grip = False
            self.overlay.updateGrab()
        _, saved = self.callback.call_args.args
        self.assertAlmostEqual(saved["ui_scaling"], 2.0, places=5)

    def test_transparent_area_is_not_pointed(self):
        from PIL import Image
        self.overlay.images["small"] = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        hit = self.overlay.overlay.computeOverlayIntersection.return_value[1]
        hit.vUVs.v = [0.5, 0.5]
        self.assertEqual(self.overlay.pointingOverlay(np.eye(4)), (None, None))
        self.overlay.images["small"].putpixel((50, 50), (255, 255, 255, 255))
        self.assertEqual(self.overlay.pointingOverlay(np.eye(4))[0], "small")


class PanelInputTest(unittest.TestCase):
    """VRパネルへの入力: トリガーのクリック判定とスクロール。"""

    def test_uv_to_pixel_matches_device_measurement(self):
        from models.overlay.overlay import uvToPixel
        # 実機: 900x700 のパネルで Voice2Chatbox (y≈73) を指したときの UV
        self.assertEqual(uvToPixel(0.1216, 0.8048, 900, 700)[1], 75)
        self.assertEqual(uvToPixel(0.5, 0.5, 900, 700), (450, 350))

    def test_trigger_click_and_scroll(self):
        import openvr
        from unittest.mock import patch

        overlay = Overlay({})
        overlay.panel_hwnd = 123
        overlay.panel_image_size = (900, 836)
        xy = (450, 260)
        state = MagicMock()
        state.rAxis[0].y = 0.0

        with patch("models.overlay.overlay.window_capture") as wc:
            state.ulButtonPressed = 0
            overlay.handlePanelInput(1, xy, state)
            wc.mouseMove.assert_called_with(123, 450, 260, pressed=False)
            state.ulButtonPressed = 1 << openvr.k_EButton_SteamVR_Trigger
            overlay.handlePanelInput(1, xy, state)
            wc.mouseDown.assert_called_once_with(123, 450, 260)
            # 押したままパネルの外へ外れたら、パネルの外で離したことにする (クリックを成立させない)
            overlay.handlePanelInput(1, None, state)
            wc.mouseUp.assert_called_once_with(123, -1, -1)
            state.ulButtonPressed = 0
            state.rAxis[0].y = -1.0
            overlay.handlePanelInput(1, xy, state)
            wc.mouseWheel.assert_called_once_with(123, 450, 260, -60)

class UpdatePanelTest(unittest.TestCase):
    def test_captured_panel_becomes_pointable(self):
        """撮影したパネル画像が当たり判定に使われる (起動時の1x1透明画像のままにしない)。"""
        from unittest.mock import patch

        from PIL import Image

        from models.overlay.overlay import PANEL

        overlay = Overlay({PANEL: {}})
        overlay.handle = {PANEL: 10}
        overlay.overlay = MagicMock()
        overlay.images[PANEL] = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        overlay.gl = {"GL": MagicMock(), "texture": 1, "vr_texture": MagicMock(), "size": None}
        overlay.panel_hwnd = 123
        with patch("models.overlay.overlay.window_capture") as wc:
            wc.isWindow.return_value = True
            wc.captureWindowRaw.return_value = (b"frame", None, None)
            wc.imageFromCapture.return_value = Image.new("RGBA", (900, 836), (40, 40, 40, 255))
            overlay.updatePanel()
        results = MagicMock()
        results.vUVs.v = [0.5, 0.5]
        self.assertTrue(overlay.hasContentAt(PANEL, results))

class SetAnchorTest(unittest.TestCase):
    def test_switch_to_playspace_keeps_world_position(self):
        """追従先を切り替えてもパネルは今見えている場所から動かない。"""
        from models.overlay.overlay import PANEL, PLAYSPACE

        settings = {k: 0.0 for k in KEYS}
        settings.update(tracker="HMD", opacity=1.0, fadeout_duration=0, ui_scaling=0.4, y_pos=0.3)
        overlay = Overlay({PANEL: settings})
        overlay.initialized = True
        overlay.overlay = MagicMock()
        overlay.overlay_system = MagicMock()
        overlay.overlay_system.getTrackedDeviceIndexForControllerRole.return_value = 1
        overlay.handle = {PANEL: 10}
        overlay.position_changed_callback = MagicMock()
        head = np.eye(4)
        head[:3, 3] = (0.2, 1.1, -0.3)

        base = getHMDBaseMatrix()
        before = head @ utils.toHomogeneous(_relative(base, [settings[k] for k in KEYS]))
        overlay.setAnchor(lambda index: np.eye(4) if index == -1 else head, PLAYSPACE)

        self.assertEqual(overlay.settings[PANEL]["tracker"], PLAYSPACE)
        s = overlay.settings[PANEL]
        after = utils.toHomogeneous(_relative(np.hstack([np.eye(3), np.zeros((3, 1))]), [s[k] for k in KEYS]))
        np.testing.assert_allclose(after, before, atol=1e-3)
        _, saved = overlay.position_changed_callback.call_args.args
        self.assertEqual(saved["tracker"], PLAYSPACE)
        overlay.overlay.setOverlayTransformAbsolute.assert_called()

    def _overlay_in_space(self, distance):
        """空間固定で、頭 (原点) の正面 distance m にあるログ。"""
        from models.overlay.overlay import PANEL

        settings = {k: 0.0 for k in KEYS}
        settings.update(tracker="Playspace", opacity=1.0, fadeout_duration=0, ui_scaling=0.4, z_pos=distance)
        overlay = Overlay({PANEL: settings})
        overlay.initialized = True
        overlay.overlay = MagicMock()
        overlay.overlay_system = MagicMock()
        overlay.overlay_system.getTrackedDeviceIndexForControllerRole.return_value = 1
        overlay.handle = {PANEL: 10}
        return overlay

    def test_far_window_is_pulled_in_when_attached_to_a_hand(self):
        """遠くのウィンドウを手に付けると手元 (0.5m以内) に寄せる。手首をひねるたびに大きく振れないように。"""
        from models.overlay.overlay import PANEL

        overlay = self._overlay_in_space(2.0)
        pose_of = lambda index: np.eye(4)  # noqa: E731  空間も手も原点
        overlay.setAnchor(pose_of, "LeftHand")
        world = overlay.overlayWorldPose(PANEL, pose_of)
        self.assertAlmostEqual(float(np.linalg.norm(world[:3, 3])), 0.5, places=3)
        self.assertEqual(overlay.settings[PANEL]["tracker"], "LeftHand")

    def test_near_window_keeps_its_place_on_a_hand(self):
        from models.overlay.overlay import PANEL

        overlay = self._overlay_in_space(0.3)
        pose_of = lambda index: np.eye(4)  # noqa: E731
        before = overlay.overlayWorldPose(PANEL, pose_of)
        overlay.setAnchor(pose_of, "RightHand")
        np.testing.assert_allclose(overlay.overlayWorldPose(PANEL, pose_of), before, atol=1e-3)

    def test_failed_switch_tells_the_current_anchor(self):
        """切り替え先の姿勢が取れないときは動かさず、今の固定先を知らせて UI の表示を戻す。"""
        from models.overlay.overlay import PANEL

        overlay = self._overlay_in_space(0.3)
        overlay.position_changed_callback = MagicMock()
        overlay.setAnchor(lambda index: np.eye(4) if index == -1 else None, "RightHand")
        self.assertEqual(overlay.settings[PANEL]["tracker"], "Playspace")
        _, notified = overlay.position_changed_callback.call_args.args
        self.assertEqual(notified["tracker"], "Playspace")

    def test_request_is_applied_on_the_overlay_thread(self):
        from models.overlay.overlay import PANEL

        overlay = self._overlay_in_space(0.3)
        overlay.requestAnchor("Nowhere")  # 知らない固定先は無視する
        self.assertIsNone(overlay.requested_anchor)
        overlay.requestAnchor("HMD")
        overlay.applyVrWindows(lambda index: np.eye(4))
        self.assertEqual(overlay.settings[PANEL]["tracker"], "HMD")
        self.assertIsNone(overlay.requested_anchor)


class GrabMotionTest(unittest.TestCase):
    """掴んでいる間の押し引き・ならしと、放したときに自分の方へ向け直す動き。"""

    def _state(self, x, y):
        state = MagicMock()
        state.rAxis = [MagicMock(x=x, y=y)]
        return state

    def _hand_to_overlay(self, distance):
        m = np.eye(4)
        m[2, 3] = -distance  # 手の前方 (-Z) distance m
        return m

    def test_stick_up_pushes_away_and_down_pulls_in(self):
        from models.overlay.overlay import pushPull

        far = pushPull(self._hand_to_overlay(1.0), self._state(0.0, 1.0), 0.1)
        near = pushPull(self._hand_to_overlay(1.0), self._state(0.0, -1.0), 0.1)
        self.assertAlmostEqual(-far[2, 3], 1.1)  # 距離 x 1.0/秒 x 0.1秒
        self.assertAlmostEqual(-near[2, 3], 0.9)

    def test_small_or_sideways_stick_does_nothing(self):
        """VRChat の移動・回転に使う倒し方では動かさない。"""
        from models.overlay.overlay import pushPull

        for x, y in ((0.0, 0.4), (0.8, 0.6)):
            with self.subTest(x=x, y=y):
                moved = pushPull(self._hand_to_overlay(1.0), self._state(x, y), 0.1)
                self.assertAlmostEqual(-moved[2, 3], 1.0)

    def test_distance_is_limited(self):
        from models.overlay.overlay import pushPull

        self.assertAlmostEqual(-pushPull(self._hand_to_overlay(2.45), self._state(0.0, 1.0), 0.1)[2, 3], 2.5)
        self.assertAlmostEqual(-pushPull(self._hand_to_overlay(0.26), self._state(0.0, -1.0), 0.1)[2, 3], 0.25)
        # 範囲の外にあっても、急に範囲へ跳ばない (近くで掴んだウィンドウを押し出すと、そこから遠ざかる)
        self.assertAlmostEqual(-pushPull(self._hand_to_overlay(0.1), self._state(0.0, -1.0), 0.1)[2, 3], 0.1)

    def test_slow_motion_is_smoothed_and_fast_motion_follows(self):
        overlay = Overlay({})
        start = np.hstack([np.eye(3), np.zeros((3, 1))])
        overlay.smoothGrab(start, 0.016)
        slow = start.copy()
        slow[0, 3] = 0.002  # 0.125 m/s
        self.assertLess(overlay.smoothGrab(slow, 0.016)[0, 3], 0.002)  # 震え程度の動きはならす
        fast = start.copy()
        fast[0, 3] = 0.05  # 3 m/s
        self.assertAlmostEqual(overlay.smoothGrab(fast, 0.016)[0, 3], 0.05)  # 速い動きには遅れない

    def test_steady_medium_speed_does_not_judder(self):
        """0.1〜0.3 m/s で一定に動かしたとき、遅れがフレームごとに入れ替わらない (ガタつかない)。"""
        for speed in (0.1, 0.2, 0.28):
            with self.subTest(speed=speed):
                overlay = Overlay({})
                dt = 1 / 60
                lags = []
                for i in range(60):
                    target = np.hstack([np.eye(3), np.array([[speed * dt * i], [0.0], [0.0]])])
                    lags.append(target[0, 3] - overlay.smoothGrab(target, dt)[0, 3])
                steady = lags[30:]
                self.assertLess(max(steady) - min(steady), 1e-4)

    def _face(self, tracker, head):
        from models.overlay.overlay import PANEL

        settings = {k: 0.0 for k in KEYS}
        settings.update(tracker=tracker, opacity=1.0, fadeout_duration=0, ui_scaling=0.4)
        overlay = Overlay({PANEL: settings})
        overlay.overlay_system = MagicMock()
        relative = np.hstack([np.eye(3), np.array([[0.5], [1.6], [-1.0]])])  # 右前方、表は +Z (横を向いたまま)
        pose_of = lambda index: head if index == 0 else np.eye(4)  # noqa: E731
        return overlay.faceUserOnRelease(PANEL, relative, np.eye(4), pose_of)

    def test_window_in_space_turns_to_face_the_user_level(self):
        head = np.eye(4)
        head[:3, 3] = (0.0, 1.6, 0.0)
        faced = self._face("Playspace", head)
        to_head = head[:3, 3] - faced[:, 3]
        self.assertGreater(float(np.dot(faced[:, 2], to_head / np.linalg.norm(to_head))), 0.999)  # 表が頭を向く
        self.assertAlmostEqual(float(faced[1, 0]), 0.0, places=6)  # 横軸は水平 (傾けない)
        np.testing.assert_allclose(faced[:, 3], (0.5, 1.6, -1.0))  # 位置は変えない

    def test_lying_down_aligns_with_the_head(self):
        head = np.eye(4)
        head[:3, 3] = (0.0, 1.6, 0.0)
        c, s = np.cos(np.radians(60)), np.sin(np.radians(60))
        head[:3, :3] = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])  # 頭を横に60°傾けている
        faced = self._face("Playspace", head)
        self.assertGreater(abs(float(faced[1, 0])), 0.5)  # 水平ではなく頭の傾きに合わせる

    def test_window_on_a_hand_is_not_turned(self):
        head = np.eye(4)
        head[:3, 3] = (0.0, 1.6, 0.0)
        faced = self._face("LeftHand", head)
        np.testing.assert_allclose(faced[:, :3], np.eye(3))


class LauncherHandTest(unittest.TestCase):
    """ランチャーを付ける手の切り替えと、手首を見たときだけ出す動き。"""

    def test_switching_hand_mirrors_the_wrist_position(self):
        """左手で付けていた位置を反転すると、右手の同じ場所 (鏡写し) に付く。"""
        from models.overlay.overlay import mirrorHandPosition

        left = {"x_pos": 0.03, "y_pos": 0.05, "z_pos": -0.02, "x_rotation": 10.0, "y_rotation": 20.0, "z_rotation": -30.0, "tracker": "LeftHand"}
        right = mirrorHandPosition(left)
        self.assertEqual(right["tracker"], "RightHand")
        mirror = np.diag([-1.0, 1.0, 1.0, 1.0])
        on_left = utils.toHomogeneous(_relative(getLeftHandBaseMatrix(), [left[k] for k in KEYS]))
        on_right = utils.toHomogeneous(_relative(getRightHandBaseMatrix(), [right[k] for k in KEYS]))
        np.testing.assert_allclose(on_right, mirror @ on_left @ mirror, atol=1e-6)
        self.assertEqual(mirrorHandPosition(right), left)  # 戻せば元どおり

    def _launcher_overlay(self):
        from models.overlay.overlay import LAUNCHER

        settings = {k: 0.0 for k in KEYS}
        settings.update(tracker="Playspace", opacity=1.0, fadeout_duration=0, ui_scaling=0.28)
        overlay = Overlay({LAUNCHER: settings})
        overlay.initialized = True
        overlay.overlay = MagicMock()
        overlay.overlay_system = MagicMock()
        overlay.handle = {LAUNCHER: 11}
        return overlay

    def _head(self, facing_launcher):
        """ランチャー (原点、表は +Z) の 0.4m 手前に頭。facing_launcher なら頭もランチャーを見ている。"""
        head = np.eye(4)
        head[:3, 3] = (0.0, 0.0, 0.4)
        if not facing_launcher:
            c, s_ = np.cos(np.radians(90)), np.sin(np.radians(90))
            head[:3, :3] = np.array([[c, 0, s_], [0, 1, 0], [-s_, 0, c]])  # 横を向いている
        return head

    def test_launcher_shows_when_looking_at_the_wrist_and_hides_otherwise(self):
        overlay = self._launcher_overlay()
        overlay.launcher_shown, overlay.launcher_alpha = False, 0.0
        looking = lambda index: self._head(True) if index == 0 else np.eye(4)  # noqa: E731
        away = lambda index: self._head(False) if index == 0 else np.eye(4)  # noqa: E731
        overlay.updateLauncherVisibility(looking, 10.0)
        self.assertFalse(overlay.launcher_shown)  # 一瞬見ただけでは出さない
        overlay.updateLauncherVisibility(looking, 10.25)
        self.assertTrue(overlay.launcher_shown)
        self.assertFalse(overlay.launcher_interactive)  # 出始めは押せない
        for t in (10.35, 10.45, 10.55, 10.65):
            overlay.updateLauncherVisibility(looking, t)
        self.assertEqual(overlay.launcher_alpha, 1.0)
        self.assertTrue(overlay.launcher_interactive)
        overlay.updateLauncherVisibility(away, 11.0)
        self.assertTrue(overlay.launcher_shown)  # 目をそらしてすぐは消さない
        overlay.updateLauncherVisibility(away, 11.35)
        self.assertFalse(overlay.launcher_shown)
        self.assertFalse(overlay.launcher_interactive)

    def test_pointed_launcher_stays_and_disabled_auto_hide_always_shows(self):
        overlay = self._launcher_overlay()
        away = lambda index: self._head(False) if index == 0 else np.eye(4)  # noqa: E731
        overlay.launcher_pointed = True
        overlay.updateLauncherVisibility(away, 10.0)
        overlay.updateLauncherVisibility(away, 11.0)
        self.assertTrue(overlay.launcher_shown)  # レーザーを当てている間は消さない
        overlay.launcher_pointed = False
        overlay.launcher_auto_hide = False
        overlay.updateLauncherVisibility(away, 12.0)
        overlay.updateLauncherVisibility(away, 13.0)
        self.assertTrue(overlay.launcher_shown)


class PanelLockTest(unittest.TestCase):
    """ロック中のログウィンドウはグリップしても掴めない。"""

    HMD, LEFT, RIGHT = UpdateGrabFlowTest.HMD, UpdateGrabFlowTest.LEFT, UpdateGrabFlowTest.RIGHT

    def setUp(self):
        UpdateGrabFlowTest.setUp(self)  # 偽の SteamVR だけ借りる (テストは継がない)
        settings = dict(self.overlay.settings["small"], tracker="Playspace")
        overlay = Overlay({PANEL: settings})
        overlay.overlay_system = self.overlay.overlay_system
        overlay.overlay = self.overlay.overlay
        overlay.handle = {PANEL: 10}
        overlay.pointer_handles = self.overlay.pointer_handles
        overlay.setVrWindows(log=True, popup=False)  # ログウィンドウを開いている
        self.overlay = overlay

    def test_press_grab_release_commits(self):
        """ロックしていなければ、ログも今までどおり掴める。"""
        self.grip = True
        self.overlay.updateGrab()
        self.assertIsNotNone(self.overlay.grabbing)

    def test_locked_panel_is_not_grabbed(self):
        self.overlay.panel_locked = True
        self.grip = True
        self.overlay.updateGrab()
        self.assertIsNone(self.overlay.grabbing)


class ToolbarTest(unittest.TestCase):
    """ログの下の操作バー: 指している間だけ出し、ログに付いて動く。"""

    def _overlay(self):
        from models.overlay.overlay import PANEL

        settings = {k: 0.0 for k in KEYS}
        settings.update(tracker="Playspace", opacity=1.0, fadeout_duration=0, ui_scaling=0.8, z_pos=1.0)
        overlay = Overlay({PANEL: settings})
        overlay.initialized = True
        overlay.overlay = MagicMock()
        overlay.overlay_system = MagicMock()
        overlay.handle = {PANEL: 10}
        overlay.toolbar_handle = 20
        return overlay

    def test_shown_after_pointing_for_a_moment_and_hidden_later(self):
        overlay = self._overlay()
        overlay.updateToolbarVisibility(10.0, True)
        self.assertFalse(overlay.toolbar_visible)  # 横切っただけでは出さない
        overlay.updateToolbarVisibility(10.35, True)
        self.assertTrue(overlay.toolbar_visible)
        overlay.overlay.showOverlay.assert_called_with(20)
        overlay.updateToolbarVisibility(11.0, False)
        self.assertTrue(overlay.toolbar_visible)  # 外れてすぐは消さない (バーへ移る間)
        overlay.updateToolbarVisibility(12.4, False)
        self.assertFalse(overlay.toolbar_visible)
        overlay.overlay.hideOverlay.assert_called_with(20)

    def test_hidden_with_the_log_window(self):
        from models.overlay.overlay import PANEL

        overlay = self._overlay()
        overlay.updateToolbarVisibility(10.0, True)
        overlay.updateToolbarVisibility(10.5, True)
        overlay.vr_windows_hidden.add(PANEL)
        overlay.updateToolbarVisibility(10.6, True)
        self.assertFalse(overlay.toolbar_visible)

    def test_size_is_fixed_and_placed_below_the_log(self):
        """ログを拡大してもバーの大きさは変わらず、ログの下端のすぐ下に付く。"""
        from models.overlay.overlay import TOOLBAR, VR_REGIONS

        overlay = self._overlay()
        self.assertAlmostEqual(overlay.regionWidthM(TOOLBAR), 720 * 0.4 / 900)
        overlay.setToolbarVisible(True)
        pose = overlay.regionWorldPose(TOOLBAR, lambda index: np.eye(4))
        log_bottom = -(0.8 * 700 / 900) / 2
        bar_half = overlay.regionWidthM(TOOLBAR) * VR_REGIONS[TOOLBAR][3] / VR_REGIONS[TOOLBAR][2] / 2
        self.assertAlmostEqual(pose[1, 3], log_bottom - 0.012 - bar_half, places=4)
        self.assertAlmostEqual(pose[2, 3], -1.0, places=4)  # ログと同じ奥行き


class PanelTriggerBlockTest(unittest.TestCase):
    def test_trigger_held_after_grab_is_ignored_until_released(self):
        import openvr
        from unittest.mock import patch

        overlay = Overlay({})
        overlay.panel_hwnd = 123
        overlay.panel_image_size = (900, 836)
        overlay.trigger_blocked.add(1)
        results = MagicMock()
        results.vUVs.v = [0.5, 0.5]
        state = MagicMock()
        state.rAxis[0].y = 0.0
        with patch("models.overlay.overlay.window_capture") as wc:
            state.ulButtonPressed = 1 << openvr.k_EButton_SteamVR_Trigger
            overlay.handlePanelInput(1, (450, 350), state)  # 掴み終えたときから押したまま
            state.ulButtonPressed = 0
            overlay.handlePanelInput(1, (450, 350), state)  # 離す
            wc.mouseDown.assert_not_called()
            wc.mouseUp.assert_not_called()
            state.ulButtonPressed = 1 << openvr.k_EButton_SteamVR_Trigger
            overlay.handlePanelInput(1, (450, 350), state)  # 押し直せば効く
            wc.mouseDown.assert_called_once()

class VrLayoutTest(unittest.TestCase):
    def test_python_regions_match_react_layout(self):
        """撮影側 (Python) と描画側 (React) で領域の定義がずれていない。"""
        import json
        import os

        path = os.path.join(os.path.dirname(__file__), "..", "..", "src-ui", "views", "vr", "vr_layout.json")
        with open(path, encoding="utf-8") as f:
            layout = json.load(f)
        self.assertEqual(tuple(layout["atlas"]), VR_ATLAS_SIZE)
        self.assertEqual({k: tuple(v) for k, v in layout["regions"].items()}, VR_REGIONS)

    def test_region_bounds_and_input_offset(self):
        from models.overlay.overlay import regionBounds

        u0, _u1, v0, v1 = regionBounds(LAUNCHER)
        self.assertAlmostEqual(u0, 10 / 1628)
        self.assertAlmostEqual(v0, 1 - 708 / 836)  # 表示の上端 = 画像の708行目
        self.assertAlmostEqual(v1, 0.0)  # 表示の下端 = 画像の最下行
        self.assertEqual(regionBounds(PANEL)[2:], (1.0, 1 - 700 / 836))  # ログは画像の上側
        # レーザーの当たった点 (空間座標) → 撮影画像上のピクセル。空間固定・原点に置いたランチャー
        overlay = Overlay({LAUNCHER: {k: 0.0 for k in KEYS} | {"tracker": "Playspace", "ui_scaling": 0.28}})
        overlay.panel_image_size = (2442, 1254)  # DPI 150%
        pose = overlay.overlayWorldPose(LAUNCHER, lambda index: np.eye(4))
        results = MagicMock()
        results.vPoint.v = [0.0, 0.0, 0.0]  # 中央
        x, y = overlay.regionPixel(LAUNCHER, results, pose)
        self.assertAlmostEqual(x, (10 + 440) * 1.5, delta=2)
        self.assertAlmostEqual(y, (708 + 64) * 1.5, delta=2)
        results.vPoint.v = [-0.14 + 0.001, 0.28 * 128 / 880 / 2 - 0.001, 0.0]  # 左上の角
        x, y = overlay.regionPixel(LAUNCHER, results, pose)
        self.assertAlmostEqual(x, 10 * 1.5, delta=8)
        self.assertAlmostEqual(y, 708 * 1.5, delta=8)

class UpdatePanelRegionsTest(unittest.TestCase):
    def test_one_capture_is_split_into_log_and_launcher(self):
        """1回の撮影から、ログとランチャーそれぞれの領域が別々に切り出される。"""
        from unittest.mock import patch

        from PIL import Image, ImageDraw

        overlay = Overlay({PANEL: {}, LAUNCHER: {}})
        overlay.handle = {PANEL: 10, LAUNCHER: 11}
        overlay.overlay = MagicMock()
        overlay.gl = {"GL": MagicMock(), "texture": 1, "vr_texture": MagicMock(), "size": None}
        overlay.panel_hwnd = 123
        atlas = Image.new("RGBA", VR_ATLAS_SIZE, (255, 0, 0, 255))  # ログ領域 = 赤
        ImageDraw.Draw(atlas).rectangle((0, 700, 900, 836), fill=(0, 0, 255, 255))  # ランチャー側 = 青
        with patch("models.overlay.overlay.window_capture") as wc:
            wc.isWindow.return_value = True
            wc.captureWindowRaw.return_value = (b"frame", None, None)
            wc.imageFromCapture.return_value = atlas
            overlay.updatePanel()
        # 領域ごとの切り出しは各オーバーレイのテクスチャ範囲 (bounds) で行う (VrLayoutTest 参照)
        self.assertEqual(overlay.panel_image_size, VR_ATLAS_SIZE)
        # 1枚のテクスチャを両方のオーバーレイへ渡す
        handles = [c.args[0] for c in overlay.overlay.setOverlayTexture.call_args_list]
        self.assertEqual(sorted(handles), [10, 11])

class PanelCaptureLoadTest(unittest.TestCase):
    """撮影の負荷を下げる: 画面が変わっていなければ転送しない、操作していなければ撮影を減らす。"""

    def _overlay(self):
        from PIL import Image

        overlay = Overlay({PANEL: {}, LAUNCHER: {}})
        overlay.handle = {PANEL: 10, LAUNCHER: 11}
        overlay.overlay = MagicMock()
        overlay.gl = {"GL": MagicMock(), "texture": 1, "vr_texture": MagicMock(), "size": None}
        overlay.panel_hwnd = 123
        return overlay, Image.new("RGBA", VR_ATLAS_SIZE, (40, 40, 40, 255))

    def test_unchanged_frame_is_not_uploaded(self):
        overlay, atlas = self._overlay()
        with patch("models.overlay.overlay.window_capture") as wc:
            wc.isWindow.return_value = True
            wc.imageFromCapture.return_value = atlas
            for raw in (b"a", b"a", b"b"):
                overlay.panel_last_capture = 0.0  # 撮影間隔の待ちを飛ばす
                wc.captureWindowRaw.return_value = (raw, None, None)
                overlay.updatePanel()
        self.assertEqual(wc.captureWindowRaw.call_count, 3)
        self.assertEqual(wc.imageFromCapture.call_count, 2)  # 2回目は前回と同じなので変換しない
        self.assertEqual(overlay.overlay.setOverlayTexture.call_count, 2 * 2)  # 転送は2回 x オーバーレイ2つ

    def test_capture_slows_down_while_idle(self):
        from models.overlay.overlay import _PANEL_CAPTURE_INTERVAL_SEC, _PANEL_IDLE_CAPTURE_INTERVAL_SEC

        overlay, _ = self._overlay()
        now = 100.0
        overlay.panel_last_change = now - 0.5  # 変わった直後
        self.assertEqual(overlay.panelCaptureInterval(now), _PANEL_CAPTURE_INTERVAL_SEC)
        overlay.panel_last_change = now - 5.0  # しばらく変わっていない
        self.assertEqual(overlay.panelCaptureInterval(now), _PANEL_IDLE_CAPTURE_INTERVAL_SEC)
        overlay.pointer_notified = (10, 10)  # ポインタがVR UIにある
        self.assertEqual(overlay.panelCaptureInterval(now), _PANEL_CAPTURE_INTERVAL_SEC)

    def test_image_from_capture_keeps_colors_and_crops_the_client_area(self):
        from models.overlay.window_capture import imageFromCapture

        # 3x2 のウィンドウ。左端の1列が枠。BGRX で 青, 緑, 赤 の順に並べる
        row = bytes([255, 0, 0, 0, 0, 255, 0, 0, 0, 0, 255, 0])
        img = imageFromCapture((row * 2, (3, 2), (1, 0, 3, 2)))
        self.assertEqual(img.size, (2, 2))
        self.assertEqual(img.getpixel((0, 0)), (0, 255, 0, 255))  # 緑
        self.assertEqual(img.getpixel((1, 0)), (255, 0, 0, 255))  # 赤


class NotifyPointerTest(unittest.TestCase):
    def test_only_meaningful_moves_are_sent(self):
        """ホバー表示用のポインタ位置は、動いたとき・外れたときだけ送る。"""
        overlay = Overlay({})
        sent = []
        overlay.pointer_callback = sent.append
        overlay.notifyPointer((100, 100))
        overlay.notifyPointer((102, 101))  # 4px未満の揺れは送らない
        overlay.notifyPointer((110, 100))
        overlay.notifyPointer(None)
        overlay.notifyPointer(None)
        self.assertEqual(sent, [(100, 100), (110, 100), None])

class VrWindowsTest(unittest.TestCase):
    def _overlay(self):
        from models.overlay.overlay import POPUP

        base = {k: 0.0 for k in KEYS} | {"opacity": 1.0, "fadeout_duration": 0, "display_duration": 5}
        overlay = Overlay({
            PANEL: base | {"tracker": "Playspace", "ui_scaling": 0.5},
            LAUNCHER: base | {"tracker": "Playspace", "ui_scaling": 0.28, "y_pos": 1.0, "z_pos": 0.4},
            POPUP: base | {"tracker": "Playspace", "ui_scaling": 0.36},
        })
        overlay.initialized = True
        overlay.overlay = MagicMock()
        overlay.overlay_system = MagicMock()
        overlay.handle = {PANEL: 10, LAUNCHER: 11, POPUP: 12}
        return overlay, POPUP

    def test_hide_and_show_follow_the_requested_state(self):
        overlay, POPUP = self._overlay()
        head = np.eye(4)
        head[:3, 3] = (0.0, 1.6, 0.0)
        pose_of = lambda index: head if index == 0 else np.eye(4)  # noqa: E731
        overlay.applyVrWindows(pose_of)  # 既定: ランチャーだけ表示 (ログと一時ウィンドウは非表示)
        overlay.overlay.hideOverlay.assert_any_call(12)
        self.assertEqual(overlay.vr_windows_hidden, {PANEL, POPUP})
        overlay.setVrWindows(log=True, popup=False)
        overlay.applyVrWindows(pose_of)
        self.assertEqual(overlay.vr_windows_hidden, {POPUP})
        overlay.setVrWindows(log=False, popup=True)
        overlay.applyVrWindows(pose_of)
        self.assertEqual(overlay.vr_windows_hidden, {PANEL})
        overlay.overlay.showOverlay.assert_any_call(12)
        # 隠れているウィンドウにはレーザーが当たらない
        overlay.overlay.computeOverlayIntersection.return_value = (True, MagicMock(fDistance=0.5))
        self.assertEqual(overlay.pointingOverlay(np.eye(4))[0], LAUNCHER)

    def test_popup_is_placed_above_launcher_facing_the_head(self):
        overlay, POPUP = self._overlay()
        head = np.eye(4)
        head[:3, 3] = (0.0, 1.6, 0.0)
        pose_of = lambda index: head if index == 0 else np.eye(4)  # noqa: E731
        overlay.placePopup(pose_of)
        world = overlay.overlayWorldPose(POPUP, pose_of)
        launcher = overlay.overlayWorldPose(LAUNCHER, pose_of)
        self.assertGreater(world[1, 3], launcher[1, 3])  # ランチャーより上
        to_head = head[:3, 3] - world[:3, 3]
        self.assertGreater(float(np.dot(world[:3, 2], to_head)), 0)  # 表が頭を向く
        horizontal = np.linalg.norm([to_head[0], to_head[2]])
        self.assertTrue(0.45 - 1e-3 <= horizontal <= 0.65 + 1e-3)


class VrPanelDisabledTest(unittest.TestCase):
    """VR UI がOFF (字幕のオーバーレイだけが動いている) の間は、ランチャーも含めて隠し、撮影しない。"""

    def test_all_vr_windows_are_hidden_and_shown_again(self):
        overlay, POPUP = VrWindowsTest._overlay(self)
        pose_of = lambda index: np.eye(4)  # noqa: E731
        overlay.vr_panel_enabled = False
        overlay.applyVrWindows(pose_of)
        self.assertEqual(overlay.vr_windows_hidden, {PANEL, LAUNCHER, POPUP})
        overlay.overlay.computeOverlayIntersection.return_value = (True, MagicMock(fDistance=0.5))
        self.assertEqual(overlay.pointingOverlay(np.eye(4))[0], None)
        overlay.vr_panel_enabled = True
        overlay.applyVrWindows(pose_of)
        self.assertEqual(overlay.vr_windows_hidden, {PANEL, POPUP})  # ログと一時ウィンドウは開いていないので隠れたまま

    def test_panel_is_not_captured(self):
        overlay, _ = VrWindowsTest._overlay(self)
        overlay.gl = MagicMock()
        overlay.vr_panel_enabled = False
        with patch("models.overlay.overlay.window_capture") as capture:
            overlay.updatePanel()
        capture.findWindow.assert_not_called()
        capture.captureWindowRaw.assert_not_called()


class RecallPanelTest(unittest.TestCase):
    """見失ったログウィンドウを目の前へ呼び戻す。頭は (0, 1.6, 0) で -Z を向く。"""

    def setUp(self):
        self.overlay, _ = VrWindowsTest._overlay(self)
        self.overlay.setVrWindows(log=True, popup=False)  # ログウィンドウを開いている
        self.head = np.eye(4)
        self.head[:3, 3] = (0.0, 1.6, 0.0)
        self.pose_of = lambda index: self.head if index == 0 else np.eye(4)  # noqa: E731
        self.notified = []
        self.overlay.panel_out_of_view_callback = self.notified.append
        self.saved = []
        self.overlay.position_changed_callback = lambda size, position: self.saved.append((size, position))

    def assertInFront(self):
        world = self.overlay.overlayWorldPose(PANEL, self.pose_of)
        np.testing.assert_allclose(world[:3, 3], (0.0, 1.5, -0.7), atol=1e-3)
        self.assertGreater(float(world[2, 2]), 0.98)  # 表が頭 (+Z 側、少し上) を向く
        self.assertEqual(self.overlay.settings[PANEL]["tracker"], "Playspace")

    def test_out_of_view_by_angle_and_distance(self):
        from models.overlay.overlay import isOutOfView

        def at(deg, distance):
            rad = np.radians(deg)
            return self.head[:3, 3] + distance * np.array([np.sin(rad), 0.0, -np.cos(rad)])

        self.assertFalse(isOutOfView(self.head, at(0, 1.0)))
        self.assertFalse(isOutOfView(self.head, at(50, 1.0)))
        self.assertTrue(isOutOfView(self.head, at(70, 1.0)))
        self.assertTrue(isOutOfView(self.head, at(180, 1.0)))
        self.assertTrue(isOutOfView(self.head, at(0, 4.0)))  # 正面でも遠すぎる
        # 一度外れたら、内側 (50°, 2.7m) まで戻るまでは外れたまま (境界での切り替わり続けを防ぐ)
        self.assertTrue(isOutOfView(self.head, at(55, 1.0), was_out=True))
        self.assertFalse(isOutOfView(self.head, at(45, 1.0), was_out=True))
        self.assertTrue(isOutOfView(self.head, at(0, 2.8), was_out=True))
        self.assertFalse(isOutOfView(self.head, at(0, 2.8), was_out=False))

    def test_recall_waits_until_the_grab_ends(self):
        self.overlay.requestRecallPanel()
        self.overlay.grabbing = (PANEL, 1, np.eye(4))
        self.overlay.applyVrWindows(self.pose_of)
        self.assertEqual(self.saved, [])
        self.overlay.grabbing = None
        self.overlay.applyVrWindows(self.pose_of)
        self.assertInFront()

    def test_recall_request_moves_the_panel_in_front_and_saves_it(self):
        # 最初はパネルが足元 (空間の原点) にあり、視線から外れている
        self.overlay.applyVrWindows(self.pose_of)
        self.assertEqual(self.notified, [True])
        self.overlay.requestRecallPanel()
        self.overlay.applyVrWindows(self.pose_of)
        self.assertInFront()
        self.assertEqual(self.saved[-1][0], PANEL)
        self.assertEqual(self.saved[-1][1]["tracker"], "Playspace")
        self.assertEqual(self.notified, [True, False])  # 変わったときだけ知らせる
        # UI へは JSON で送るので、numpy の bool_ ではなく Python の bool で知らせる
        self.assertTrue(all(type(value) is bool for value in self.notified))

    def test_opening_a_lost_panel_brings_it_in_front(self):
        self.overlay.setVrWindows(log=False, popup=False)
        self.overlay.applyVrWindows(self.pose_of)
        self.assertEqual(self.saved, [])
        self.overlay.setVrWindows(log=True, popup=False)
        self.overlay.applyVrWindows(self.pose_of)
        self.assertInFront()

    def test_panel_on_a_hand_is_left_alone(self):
        self.overlay.settings[PANEL]["tracker"] = "LeftHand"
        self.overlay.setVrWindows(log=False, popup=False)
        self.overlay.applyVrWindows(self.pose_of)
        self.overlay.setVrWindows(log=True, popup=False)
        self.overlay.applyVrWindows(self.pose_of)
        self.assertEqual(self.saved, [])
        self.assertEqual(self.notified, [])


if __name__ == "__main__":
    unittest.main()
