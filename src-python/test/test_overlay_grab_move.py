"""VR内の掴み移動 (Overlay.commitPosition / overlay_utils.matrix_to_position) のテスト。

コントローラ入力やSteamVRを使う updateGrab() 本体は実機でしか検証できない。
ここでは「掴んで離した後の行列を設定値へ正しく逆算できるか」だけを確かめる。
"""
import threading
import time
import unittest
from unittest.mock import ANY, MagicMock, patch

import numpy as np
import openvr
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

# 撮影は使い捨てのスレッドで行うが、このファイルのテストでは同じスレッドですぐ終わらせる
# (撮影を別スレッドにしたことのテストは CaptureJobTest で、本物のスレッドで確かめる)
_sync_capture = patch.object(Overlay, "startCaptureJob", lambda self, job: Overlay.runCaptureJob(job))


def setUpModule():
    _sync_capture.start()


def tearDownModule():
    _sync_capture.stop()


def pytest_approx(value):
    import pytest
    return pytest.approx(value)


KEYS = ("x_pos", "y_pos", "z_pos", "x_rotation", "y_rotation", "z_rotation")


def _bgra(size):
    """撮影したクライアント領域の画素 (window_capture.bgraFromCapture の結果) の代わり。"""
    return np.zeros((size[1], size[0], 4), np.uint8)


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
        self.hmd_lost = False  # 頭のトラッキングが切れている

        system = MagicMock()
        system.getTrackedDeviceIndexForControllerRole.side_effect = (
            lambda role: self.LEFT if role == openvr.TrackedControllerRole_LeftHand else self.RIGHT
        )

        def fill_poses(origin, t, poses):
            # 実物の pyopenvr と同じく、渡された配列へ書き込むだけ (戻り値に頼らない)
            self.assertIsNotNone(poses)
            for i in (self.HMD, self.LEFT, self.RIGHT):
                poses[i].bPoseIsValid = not (i == self.HMD and self.hmd_lost)
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

    def test_window_on_the_sphere_stays_put_while_the_head_is_lost(self):
        """頭のトラッキングが一瞬切れても、掴んでいる空間固定のウィンドウは跳ばず、放せばその位置で確定する。"""
        from unittest.mock import patch

        settings = dict(self.overlay.settings["small"], tracker="Playspace", z_pos=1.0, width=900, height=700)
        overlay = Overlay({PANEL: settings})
        overlay.overlay_system, overlay.overlay = self.overlay.overlay_system, self.overlay.overlay
        overlay.handle = {PANEL: 10}
        overlay.pointer_handles = self.overlay.pointer_handles
        overlay.setVrWindows(log=True, popup=False)
        center = overlay.overlayWorldPose(PANEL, lambda index: np.eye(4))[:3, 3]
        overlay.overlay.computeOverlayIntersection.return_value[1].vPoint.v = list(center)
        t = [100.0]
        with patch("models.overlay.overlay.time.monotonic", side_effect=lambda: t[0]),                 patch("models.overlay.overlay.window_capture"):
            overlay.updateGrab()  # 指している
            self.grip = True
            overlay.updateGrab()  # 掴む
            self.assertIsNotNone(overlay.grab_radius)  # 空間固定なので球面上で動かす
            t[0] += 0.05
            overlay.updateGrab()
            before = overlay.grab_last_relative.copy()
            self.hmd_lost = True
            self.right_z = -0.3  # 頭が取れない間に手が動いた
            t[0] += 0.05
            overlay.updateGrab()
            np.testing.assert_allclose(overlay.grab_last_relative, before)  # 動かさない
            self.grip = False
            t[0] += 0.05
            overlay.updateGrab()  # 頭が取れないまま放した
        self.assertIsNone(overlay.grabbing)
        np.testing.assert_allclose(overlay.panelRelative(), before, atol=1e-3)  # 最後に置いた位置で確定

    def test_no_input_while_the_layout_is_switching(self):
        """ログの大きさの切り替え中は、表示と VR画面の並びが合っていないのでクリックを送らない。"""
        from unittest.mock import patch

        settings = dict(self.overlay.settings["small"], width=900, height=700)
        overlay = Overlay({PANEL: settings})
        overlay.overlay_system, overlay.overlay = self.overlay.overlay_system, self.overlay.overlay
        overlay.handle = {PANEL: 10}
        overlay.pointer_handles = self.overlay.pointer_handles
        overlay.panel_hwnd = 123
        overlay.panel_image_size = VR_ATLAS_SIZE
        overlay.layout_applied = overlay.layout
        overlay.setVrWindows(log=True, popup=False)
        # レーザーはログの真ん中に当たっている (見えている範囲の外の当たりは無視されるため)
        center = overlay.overlayWorldPose(PANEL, lambda index: np.eye(4))[:3, 3]
        overlay.overlay.computeOverlayIntersection.return_value[1].vPoint.v = list(center)
        self.trigger = True
        with patch("models.overlay.overlay.window_capture") as wc:
            overlay.updateGrab()
            wc.mouseDown.assert_called_once()  # 切り替え中でなければ押せる
            overlay.panel_input.clear()
            wc.reset_mock()
            overlay.setPanelSize(1200, 800)  # 大きさを変えた (まだ新しい並びで撮れていない)
            overlay.updateGrab()
        wc.mouseMove.assert_not_called()
        wc.mouseDown.assert_not_called()

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
            wc.resizeClient.side_effect = lambda hwnd, w, h: (w, h)
            wc.captureWindowRaw.return_value = (b"frame", None, (0, 0) + VR_ATLAS_SIZE)
            wc.bgraFromCapture.return_value = _bgra((900, 836))
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

class PanelRecoveryTest(unittest.TestCase):
    """VR画面の撮影・転送の失敗と、止めるときの後片付け。"""

    def _overlay(self):
        overlay = Overlay({PANEL: {}, LAUNCHER: {}})
        overlay.handle = {PANEL: 10, LAUNCHER: 11}
        overlay.overlay = MagicMock()
        overlay.gl = {"GL": MagicMock(), "glfw": MagicMock(), "window": 5, "texture": 1, "vr_texture": MagicMock(), "size": None}
        return overlay

    def test_textures_are_cleared_before_the_gl_context_is_destroyed(self):
        """テクスチャを渡したまま OpenGL の環境を消すと、SteamVR との接続を閉じるときに落ちる。"""
        overlay = self._overlay()
        order = MagicMock()
        order.attach_mock(overlay.overlay.clearOverlayTexture, "clear")
        order.attach_mock(overlay.gl["glfw"].destroy_window, "destroy")
        overlay.shutdownPanelTexture()
        names = [c[0] for c in order.mock_calls]
        self.assertEqual(names, ["clear", "clear", "destroy"])
        self.assertIsNone(overlay.gl)

    def test_error_left_by_steamvr_is_discarded_before_drawing(self):
        overlay = self._overlay()
        GL = overlay.gl["GL"]
        GL.GL_NO_ERROR = 0
        GL.glGetError.side_effect = [1281, 0]
        with patch("models.overlay.overlay.printLog") as log:
            self.assertIs(overlay.prepareGl(), GL)
        overlay.gl["glfw"].make_context_current.assert_called_once_with(5)
        self.assertEqual(GL.glGetError.call_count, 2)
        log.assert_called_once()

    def test_one_failure_does_not_stop_the_panel(self):
        overlay = self._overlay()
        with patch("models.overlay.overlay.errorLogging") as logged:
            overlay.onPanelError(RuntimeError("GL"))
            self.assertIsNotNone(overlay.gl)
            for _ in range(28):
                overlay.onPanelError(RuntimeError("GL"))
            self.assertIsNotNone(overlay.gl)
            overlay.onPanelError(RuntimeError("GL"))  # 30回続いたら止める
        self.assertTrue(overlay.panel_stopped)
        # OpenGL の環境は残す (消した後に SteamVR との接続を閉じると落ちるため、teardown まで待つ)
        self.assertIsNotNone(overlay.gl)
        overlay.gl["glfw"].destroy_window.assert_not_called()
        self.assertEqual(logged.call_count, 1)  # 同じ失敗は1回だけ記録する

    def test_teardown_closes_steamvr_while_the_gl_context_is_current(self):
        """SteamVR との接続は、OpenGL の環境を今のものにしたまま閉じ、その後で環境を消す。"""
        overlay = self._overlay()
        overlay.overlay = MagicMock(spec=openvr.IVROverlay)
        overlay.system = MagicMock(spec=openvr.IVRSystem)
        order = MagicMock()
        order.attach_mock(overlay.gl["glfw"].make_context_current, "current")
        order.attach_mock(overlay.overlay.destroyOverlay, "destroy_overlay")
        order.attach_mock(overlay.gl["glfw"].destroy_window, "destroy_gl")
        with patch("models.overlay.overlay.openvr_session") as session:
            order.attach_mock(session.release, "release")
            overlay.teardown()
        names = [c[0] for c in order.mock_calls]
        self.assertEqual(names, ["current", "destroy_overlay", "destroy_overlay", "release", "destroy_gl"])
        self.assertIsNone(overlay.overlay)
        self.assertIsNone(overlay.system)

    def test_failed_close_still_allows_turning_on_again(self):
        """接続を閉じるのに失敗しても (実機で access violation)、止まった状態にして次の ON で作り直せるようにする。"""
        overlay = self._overlay()
        overlay.gl = None
        overlay.initialized = True
        overlay.system = MagicMock(spec=openvr.IVRSystem)
        with patch("models.overlay.overlay.openvr_session") as session, patch("models.overlay.overlay.errorLogging"):
            session.release.side_effect = OSError("access violation")
            overlay.shutdownOverlay()
        self.assertFalse(overlay.initialized)
        self.assertIsNone(overlay.system)

    def test_texture_size_is_fixed_and_the_bounds_shrink(self):
        """SteamVR は最初のテクスチャの大きさのまま受け取るので、最大の並びが入る大きさで1回だけ作り、
        撮影画像は左上に書いて、表示範囲をその分だけ縮める。"""

        from models.overlay.overlay import MAX_LAYOUT, computeVrLayout

        overlay = self._overlay()
        overlay.initialized = False  # 位置の更新は見ない
        overlay.panel_hwnd = 123
        overlay.layout_applied = None
        GL = overlay.gl["GL"]
        GL.GL_NO_ERROR = 0
        GL.glGetError.return_value = 0
        with patch("models.overlay.overlay.window_capture") as wc:
            wc.isWindow.return_value = True
            wc.resizeClient.side_effect = lambda hwnd, w, h: (w, h)
            wc.captureWindowRaw.return_value = (b"a", None, (0, 0) + VR_ATLAS_SIZE)
            wc.bgraFromCapture.return_value = _bgra(VR_ATLAS_SIZE)
            overlay.updatePanel()
            self.assertEqual(overlay.gl["size"], MAX_LAYOUT["atlas"])  # 最大の並びの大きさで作った
            self.assertEqual(overlay.gl["texture"], 1)
            bounds = overlay.overlay.setOverlayTextureBounds.call_args_list[0].args[1]
            self.assertAlmostEqual(bounds.uMax, 900 / MAX_LAYOUT["atlas"][0])  # ログの右端 (900px)
            self.assertAlmostEqual(bounds.vMax, 1 - 700 / MAX_LAYOUT["atlas"][1])  # ログの下端 (700px)

            overlay.setPanelSize(790, 668)  # 縮めても、テクスチャは作り直さない
            small = computeVrLayout(790, 668)["atlas"]
            overlay.setLayoutRendered([790, 668])
            wc.captureWindowRaw.return_value = (b"b", None, (0, 0) + small)
            wc.bgraFromCapture.return_value = _bgra(small)
            overlay.overlay.setOverlayTextureBounds.reset_mock()
            overlay.panel_last_capture = 0.0
            overlay.updatePanel()
        GL.glGenTextures.assert_not_called()
        self.assertEqual(overlay.gl["size"], MAX_LAYOUT["atlas"])
        bounds = overlay.overlay.setOverlayTextureBounds.call_args_list[0].args[1]
        self.assertAlmostEqual(bounds.uMax, 790 / MAX_LAYOUT["atlas"][0])
        self.assertAlmostEqual(bounds.vMax, 1 - 668 / MAX_LAYOUT["atlas"][1])

    def test_hit_outside_the_visible_region_is_ignored(self):
        overlay = Overlay({PANEL: {k: 0.0 for k in KEYS} | {"tracker": "Playspace", "ui_scaling": 0.9, "z_pos": 1.0}})
        overlay.overlay_system = MagicMock()
        pose_of = lambda index: np.eye(4)  # noqa: E731
        center = overlay.overlayWorldPose(PANEL, pose_of)
        hit = MagicMock()
        hit.vPoint.v = list((center @ np.array([0.0, -0.30, 0.0, 1.0]))[:3])  # 下端 (0.35m) の内側
        self.assertTrue(overlay.hitInsideRegion(PANEL, hit, pose_of))
        hit.vPoint.v = list((center @ np.array([0.0, -0.40, 0.0, 1.0]))[:3])  # 下の操作バーのあたり
        self.assertFalse(overlay.hitInsideRegion(PANEL, hit, pose_of))

    def test_grab_error_clears_the_highlight(self):
        overlay = self._overlay()
        overlay.setHighlight = MagicMock()
        overlay.showPointer = MagicMock()
        with patch("models.overlay.overlay.errorLogging"):
            overlay.onGrabError(RuntimeError("GL"))
        overlay.setHighlight.assert_called_with(None, ANY)
        overlay.showPointer.assert_called_with(None, ANY)


class GrabOnSphereTest(unittest.TestCase):
    """空間・頭に固定したウィンドウは、手の向きでは回さず、目を中心とした球面上で自分の方を向く。"""

    def test_pose_on_sphere_faces_the_head_and_stays_level_in_view(self):
        from models.overlay.overlay import poseOnSphere

        head = np.eye(4)
        head[:3, 3] = (0.0, 1.6, 0.0)
        c, s_ = np.cos(np.radians(20)), np.sin(np.radians(20))
        head[:3, :3] = np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1]])  # 頭を横に20°傾けている
        pose = poseOnSphere(np.array([0.5, 1.2, -1.5]), head, 0.8)
        to_head = head[:3, 3] - pose[:3, 3]
        self.assertAlmostEqual(float(np.linalg.norm(to_head)), 0.8)  # 目からの距離は半径のまま
        self.assertGreater(float(np.dot(pose[:3, 2], to_head / 0.8)), 0.999)  # 表が頭を向く
        self.assertAlmostEqual(float(np.dot(pose[:3, 0], head[:3, 1])), 0.0, places=6)  # 見ている人にとって水平

    def test_moving_the_arm_forward_pushes_the_window_away(self):
        """掴んだまま腕を前後に動かすと、その割合でウィンドウも遠ざかる・近づく (範囲は 0.25〜2.5m)。"""
        from models.overlay.overlay import sphereRadius

        self.assertAlmostEqual(sphereRadius(1.0, 0.4, 0.4), 1.0)  # 動かしていない
        self.assertAlmostEqual(sphereRadius(1.0, 0.4, 0.6), 1.5)  # 腕を伸ばした
        self.assertAlmostEqual(sphereRadius(1.0, 0.4, 0.3), 0.75)  # 手前に引いた
        self.assertEqual(sphereRadius(2.0, 0.3, 0.7), 2.5)  # 遠すぎない
        # 範囲の外 (3m) にあるウィンドウを掴んでも跳ばない。近づける向きにだけ動かせる
        self.assertAlmostEqual(sphereRadius(3.0, 0.4, 0.4), 3.0)
        self.assertAlmostEqual(sphereRadius(3.0, 0.4, 0.6), 3.0)
        self.assertAlmostEqual(sphereRadius(3.0, 0.4, 0.3), 2.25)

    def test_push_pull_changes_the_distance_only(self):
        from models.overlay.overlay import pushPullDistance

        state = MagicMock()
        state.rAxis = [MagicMock(x=0.0, y=1.0)]
        self.assertGreater(pushPullDistance(1.0, state, 0.1), 1.0)
        state.rAxis = [MagicMock(x=0.0, y=0.2)]  # 倒し量が小さい
        self.assertEqual(pushPullDistance(1.0, state, 0.1), 1.0)


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
            wc.resizeClient.side_effect = lambda hwnd, w, h: (w, h)
            wc.captureWindowRaw.return_value = (b"frame", None, (0, 0) + VR_ATLAS_SIZE)
            wc.bgraFromCapture.return_value = _bgra(VR_ATLAS_SIZE)
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
            wc.resizeClient.side_effect = lambda hwnd, w, h: (w, h)
            wc.bgraFromCapture.return_value = _bgra(VR_ATLAS_SIZE)
            for raw in (b"a", b"a", b"b"):
                overlay.panel_last_capture = 0.0  # 撮影間隔の待ちを飛ばす
                wc.captureWindowRaw.return_value = (raw, None, (0, 0) + VR_ATLAS_SIZE)
                overlay.updatePanel()
        self.assertEqual(wc.captureWindowRaw.call_count, 3)
        self.assertEqual(wc.bgraFromCapture.call_count, 2)  # 2回目は前回と同じなので変換しない
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

    def test_capture_keeps_bgra_and_crops_the_client_area(self):
        from models.overlay.window_capture import bgraFromCapture

        # 3x2 のウィンドウ。左端の1列が枠。BGRX で 青, 緑, 赤 の順に並べる
        row = bytes([255, 0, 0, 0, 0, 255, 0, 0, 0, 0, 255, 0])
        pixels = bgraFromCapture((row * 2, (3, 2), (1, 0, 3, 2)))
        self.assertEqual(pixels.shape, (2, 2, 4))
        self.assertEqual(tuple(pixels[0, 0][:3]), (0, 255, 0))  # 緑 (BGR のまま)
        self.assertEqual(tuple(pixels[0, 1][:3]), (0, 0, 255))  # 赤 (BGR のまま)
        pixels[..., 3] = 255  # 書き換えられる (撮影のバッファとは別)


class CaptureJobTest(unittest.TestCase):
    """撮影 (PrintWindow) は VRCT の画面が固まると戻らないので、別スレッドで行い、レーザーの処理を止めない。"""

    def setUp(self):
        _sync_capture.stop()  # このクラスだけ本物のスレッドで撮影する
        self.addCleanup(_sync_capture.start)
        self.overlay = Overlay({PANEL: {}, LAUNCHER: {}})
        self.overlay.handle = {PANEL: 10, LAUNCHER: 11}
        self.overlay.overlay = MagicMock()
        self.overlay.gl = {"GL": MagicMock(), "texture": 1, "vr_texture": MagicMock(), "size": None}
        self.overlay.panel_hwnd = 123
        self.overlay.layout_rendered = self.overlay.layout["regions"][PANEL][2:]
        wc = patch("models.overlay.overlay.window_capture").start()
        self.addCleanup(patch.stopall)
        wc.isWindow.return_value = True
        wc.resizeClient.side_effect = lambda hwnd, w, h: (w, h)
        wc.bgraFromCapture.return_value = _bgra(VR_ATLAS_SIZE)
        self.release = threading.Event()
        self.started = threading.Event()

        def blocked_capture(hwnd):
            self.started.set()
            self.release.wait(5)
            return (b"frame", None, (0, 0) + VR_ATLAS_SIZE)

        wc.captureWindowRaw.side_effect = blocked_capture
        self.wc = wc

    def _wait_done(self):
        job = self.overlay.capture_job
        for _ in range(500):
            if job.done:
                return
            time.sleep(0.01)
        self.fail("撮影のスレッドが終わらない")

    def test_blocked_capture_does_not_block_the_loop(self):
        started = time.monotonic()
        self.overlay.updatePanel()
        self.assertTrue(self.started.wait(2))
        for _ in range(3):  # 撮影が戻らない間も、すぐに戻る (その間レーザーの処理が回る)
            self.overlay.panel_last_capture = 0.0
            self.overlay.updatePanel()
        self.assertLess(time.monotonic() - started, 1.0)
        self.assertEqual(self.wc.captureWindowRaw.call_count, 1)  # 同時に頼むのは1つだけ
        self.overlay.overlay.setOverlayTexture.assert_not_called()
        self.release.set()
        self._wait_done()
        self.overlay.updatePanel()
        self.overlay.overlay.setOverlayTexture.assert_called()  # 戻ったら転送する

    def test_frame_taken_for_an_old_layout_is_dropped(self):
        self.overlay.updatePanel()
        self.assertTrue(self.started.wait(2))
        self.overlay.setPanelSize(790, 668)  # 撮っている間にログの大きさを変えた
        self.release.set()
        self._wait_done()
        self.overlay.updatePanel()
        self.overlay.overlay.setOverlayTexture.assert_not_called()
        self.wc.bgraFromCapture.assert_not_called()

    def test_capture_error_is_raised_on_the_overlay_thread(self):
        def failing_capture(hwnd):
            self.release.wait(5)
            raise OSError("PrintWindow")

        self.wc.captureWindowRaw.side_effect = failing_capture
        self.overlay.updatePanel()  # 撮影のスレッドの例外は、ここでは出ない
        self.release.set()
        self._wait_done()
        with self.assertRaises(OSError):  # mainloop の onPanelError が数える
            self.overlay.updatePanel()

    def test_time_blocked_is_not_counted_as_waiting_for_the_resize(self):
        """固まっていた時間で「大きさが合わないので元に戻す」が動かないようにする。"""
        self.overlay.layout_requested_at = 50.0
        self.overlay.updatePanel()
        self.overlay.capture_job.started -= 3.0  # 3秒待たされた
        with patch("models.overlay.overlay.printLog") as logged:
            self.overlay.updatePanel()  # 戻らないことをログに出す
            self.assertIn("時間がかかっています", logged.call_args.args[0])
        self.overlay.setPanelSize(790, 668)  # 固まっている間に大きさを変えた
        self.release.set()
        self._wait_done()
        returned = time.monotonic()
        self.overlay.updatePanel()
        self.assertGreaterEqual(self.overlay.layout_requested_at, returned)  # 戻ったときから数え直す
        with patch("models.overlay.overlay.printLog") as logged:
            self.overlay.retryOrRevertLayout(returned + 0.1)
        self.assertEqual(self.overlay.layout["regions"][PANEL][2:], (790, 668))  # 元の大きさに戻していない
        self.assertFalse(any("元に戻します" in c.args[0] for c in logged.call_args_list))

    def test_normal_capture_time_is_counted_as_waiting_for_the_resize(self):
        self.overlay.layout_requested_at = 50.0
        self.overlay.updatePanel()
        self.assertTrue(self.started.wait(2))
        self.release.set()
        self._wait_done()
        self.overlay.updatePanel()
        self.assertEqual(self.overlay.layout_requested_at, 50.0)

    def test_next_capture_starts_when_the_result_is_taken(self):
        """結果を受け取る周で次の撮影も頼む (受け取るだけで1周使うと、撮影の頻度が半分になる)。"""
        self.overlay.updatePanel()
        self.assertTrue(self.started.wait(2))
        self.release.set()
        self._wait_done()
        self.overlay.panel_last_capture = 0.0  # 撮影間隔の待ちを飛ばす
        self.overlay.updatePanel()
        self.overlay.overlay.setOverlayTexture.assert_called()
        self.assertIsNotNone(self.overlay.capture_job)  # 次の撮影を頼んである

    def test_repeated_capture_errors_stop_the_panel(self):
        """撮影が失敗し続けたら、撮っている途中の周をはさんでも数え続けて止める。"""
        from models.overlay.overlay import _PANEL_ERROR_LIMIT

        self.wc.captureWindowRaw.side_effect = OSError("PrintWindow")
        with patch("models.overlay.overlay.errorLogging"), patch("models.overlay.overlay.printLog"):
            for _ in range(_PANEL_ERROR_LIMIT * 4):
                if self.overlay.panel_stopped:
                    break
                self.overlay.panel_last_capture = 0.0
                try:
                    self.overlay.updatePanel()
                except OSError as e:
                    self.overlay.onPanelError(e)
                if self.overlay.capture_job is not None:
                    self._wait_done()
        self.assertTrue(self.overlay.panel_stopped)

    def test_turning_off_drops_the_pending_capture(self):
        self.overlay.updatePanel()
        self.assertTrue(self.started.wait(2))
        opengl = MagicMock()
        with patch.dict("sys.modules", {"glfw": MagicMock(), "OpenGL": opengl, "OpenGL.GL": opengl.GL}):
            self.overlay.initPanelTexture()  # OFF→ON で作り直した
        self.assertIsNone(self.overlay.capture_job)
        self.release.set()


class PanelLayoutTest(unittest.TestCase):
    """ログの大きさで VR画面の並びが変わる。新しい並びで撮れたフレームから表示を切り替える。"""

    def test_layout_grows_with_the_log(self):
        from models.overlay.overlay import POPUP, TOOLBAR, computeVrLayout

        layout = computeVrLayout(1400, 1000)
        self.assertEqual(layout["regions"][PANEL], (0, 0, 1400, 1000))
        self.assertEqual(layout["regions"][LAUNCHER], (10, 1008, 880, 128))  # ログの下
        self.assertEqual(layout["regions"][POPUP][0], 1408)  # ログの右
        self.assertEqual(layout["regions"][TOOLBAR][0], 1408)
        self.assertEqual(layout["atlas"], (1408 + 720, 1008 + 128))
        # 小さくしても、ランチャー (880px) より左の列は狭くしない
        self.assertEqual(computeVrLayout(600, 400)["regions"][POPUP][0], 908)

    def _overlay(self):
        overlay = Overlay({PANEL: {}, LAUNCHER: {}})
        overlay.handle = {PANEL: 10, LAUNCHER: 11}
        overlay.overlay = MagicMock()
        overlay.gl = {"GL": MagicMock(), "texture": 1, "vr_texture": MagicMock(), "size": None}
        overlay.panel_hwnd = 123
        return overlay

    def test_resize_updates_the_window_and_waits_for_a_matching_frame(self):

        from models.overlay.overlay import computeVrLayout

        overlay = self._overlay()
        layouts = []
        overlay.layout_callback = layouts.append
        with patch("models.overlay.overlay.window_capture") as wc:
            wc.isWindow.return_value = True
            wc.resizeClient.side_effect = lambda hwnd, w, h: (w, h)
            wc.captureWindowRaw.return_value = (b"old", None, (0, 0) + VR_ATLAS_SIZE)
            wc.bgraFromCapture.return_value = _bgra(VR_ATLAS_SIZE)
            overlay.updatePanel()
            self.assertIs(overlay.layout_applied, overlay.layout)
            overlay.overlay.setOverlayTextureBounds.reset_mock()

            overlay.setPanelSize(1200, 800)
            new_atlas = computeVrLayout(1200, 800)["atlas"]
            self.assertEqual(layouts[-1]["atlas"], new_atlas)  # VR画面へ知らせる
            overlay.panel_last_capture = 0.0
            overlay.updatePanel()  # ウィンドウはまだ古い縦横比
            wc.resizeClient.assert_called_with(123, *new_atlas)
            overlay.overlay.setOverlayTextureBounds.assert_not_called()

            wc.captureWindowRaw.return_value = (b"new", None, (0, 0) + new_atlas)
            wc.bgraFromCapture.return_value = _bgra(new_atlas)
            overlay.panel_last_capture = 0.0
            overlay.updatePanel()  # ウィンドウは新しい大きさでも、VR画面がまだ古い並びで描いている
            overlay.overlay.setOverlayTextureBounds.assert_not_called()

            overlay.setLayoutRendered([1200, 800])
            overlay.panel_last_capture = 0.0
            overlay.updatePanel()  # 新しい並びで描かれ、その大きさで撮れた → 表示範囲を切り替える
        self.assertIs(overlay.layout_applied, overlay.layout)
        self.assertEqual(overlay.overlay.setOverlayTextureBounds.call_count, 2)  # ログとランチャー

    def test_smaller_log_with_the_same_window_size_waits_for_the_new_layout(self):
        """ログを縮めても VR画面全体の大きさが変わらないことがある。その場合も描き直しを待ってから切り替える。"""

        overlay = self._overlay()
        with patch("models.overlay.overlay.window_capture") as wc:
            wc.isWindow.return_value = True
            wc.resizeClient.side_effect = lambda hwnd, w, h: (w, h)
            wc.captureWindowRaw.return_value = (b"old", None, (0, 0) + VR_ATLAS_SIZE)
            wc.bgraFromCapture.return_value = _bgra(VR_ATLAS_SIZE)
            overlay.updatePanel()
            overlay.overlay.setOverlayTextureBounds.reset_mock()
            overlay.setPanelSize(700, 700)
            self.assertEqual(overlay.layout["atlas"], VR_ATLAS_SIZE)  # 全体の大きさは同じ
            wc.captureWindowRaw.return_value = (b"new", None, (0, 0) + VR_ATLAS_SIZE)
            overlay.panel_last_capture = 0.0
            overlay.updatePanel()
            overlay.overlay.setOverlayTextureBounds.assert_not_called()  # まだ古い並びで描いている
            overlay.setLayoutRendered([700, 700])
            overlay.panel_last_capture = 0.0
            overlay.updatePanel()
        self.assertIs(overlay.layout_applied, overlay.layout)

    def test_saved_size_is_kept_while_waiting_for_the_first_layout(self):
        """起動時に保存した大きさがあると、VR画面がその並びで描くまで待つ (既定の大きさへ戻さない)。"""

        from models.overlay.overlay import computeVrLayout

        overlay = self._overlay()
        overlay.settings[PANEL]["width"], overlay.settings[PANEL]["height"] = 1200, 800
        overlay.layout = computeVrLayout(1200, 800)
        overlay.layout_applied = None
        overlay.layout_requested_at = 0.0  # 起動したとき (撮影を始める前) のまま
        new_atlas = overlay.layout["atlas"]
        with patch("models.overlay.overlay.window_capture") as wc, patch("models.overlay.overlay.time.monotonic") as clock:
            wc.isWindow.return_value = True
            wc.resizeClient.side_effect = lambda hwnd, w, h: (w, h)
            wc.captureWindowRaw.return_value = (b"new", None, (0, 0) + new_atlas)
            wc.bgraFromCapture.return_value = _bgra(new_atlas)
            for t in (100.0, 110.0):  # 設定が届くまで時間がかかっても
                clock.return_value = t
                overlay.panel_last_capture = 0.0
                overlay.updatePanel()
            self.assertEqual(overlay.layout["regions"][PANEL][2:], (1200, 800))  # 戻さない
            overlay.setLayoutRendered([1200, 800])
            clock.return_value = 110.5
            overlay.panel_last_capture = 0.0
            overlay.updatePanel()
        self.assertIs(overlay.layout_applied, overlay.layout)
        self.assertEqual(overlay.settings[PANEL]["width"], 1200)

    def test_window_resized_while_shown_is_fitted_again(self):
        """表示中にウィンドウの大きさが変わったら (DPIの変更など)、そのフレームは使わずに合わせ直す。"""

        overlay = self._overlay()
        with patch("models.overlay.overlay.window_capture") as wc:
            wc.isWindow.return_value = True
            wc.resizeClient.side_effect = lambda hwnd, w, h: (w, h)
            wc.captureWindowRaw.return_value = (b"old", None, (0, 0) + VR_ATLAS_SIZE)
            wc.bgraFromCapture.return_value = _bgra(VR_ATLAS_SIZE)
            overlay.updatePanel()
            overlay.overlay.setOverlayTexture.reset_mock()
            wc.captureWindowRaw.return_value = (b"odd", None, (0, 0, 1630, 836))  # 縦横比はほぼ同じでも大きさが違う
            overlay.panel_last_capture = 0.0
            overlay.updatePanel()
            overlay.overlay.setOverlayTexture.assert_not_called()
            overlay.panel_last_capture = 0.0
            overlay.updatePanel()
        self.assertEqual(wc.resizeClient.call_count, 2)  # 起動時と、合わせ直し

    def test_size_is_kept_in_range(self):
        overlay = self._overlay()
        overlay.setPanelSize(100, 5000)
        self.assertEqual(overlay.layout["regions"][PANEL][2:], (600, 1000))

    def test_window_that_cannot_be_resized_is_retried_and_then_reverted(self):
        """VR画面のウィンドウが新しい大きさにならないと、1秒後にやり直し、3秒後に元の大きさへ戻す (固まらない)。"""

        overlay = self._overlay()
        with patch("models.overlay.overlay.window_capture") as wc, patch("models.overlay.overlay.time.monotonic") as clock:
            wc.isWindow.return_value = True
            wc.resizeClient.side_effect = lambda hwnd, w, h: (w, h)
            wc.captureWindowRaw.return_value = (b"old", None, (0, 0) + VR_ATLAS_SIZE)  # ずっと古い大きさのまま
            wc.bgraFromCapture.return_value = _bgra(VR_ATLAS_SIZE)
            clock.return_value = 10.0
            overlay.updatePanel()
            overlay.setPanelSize(1200, 800)
            for t in (10.5, 11.2, 11.3, 13.5):
                clock.return_value = t
                overlay.panel_last_capture = 0.0
                overlay.updatePanel()
            self.assertEqual(wc.resizeClient.call_count, 3)  # 起動時、変えたとき、やり直し
            self.assertEqual(overlay.layout["regions"][PANEL][2:], (900, 700))  # 元の大きさへ戻した
            clock.return_value = 13.6
            overlay.panel_last_capture = 0.0
            overlay.updatePanel()
        self.assertIs(overlay.layout_applied, overlay.layout)


class PanelResizeTest(unittest.TestCase):
    """ログの角を掴んで大きさを変える。空間固定で正面1mに、1px = 1mm (900x700px = 0.9x0.7m) で置いたログ。"""

    def _overlay(self):
        settings = {k: 0.0 for k in KEYS}
        settings.update(tracker="Playspace", opacity=1.0, fadeout_duration=0, ui_scaling=0.9, z_pos=1.0, width=900, height=700)
        overlay = Overlay({PANEL: settings})
        overlay.initialized = True
        overlay.overlay = MagicMock()
        overlay.overlay_system = MagicMock()
        overlay.handle = {PANEL: 10}
        overlay.layout_applied = overlay.layout
        overlay.position_changed_callback = MagicMock()
        return overlay

    def _hand(self, x, y):
        """原点から (x, y) だけずらした位置で、正面 (-Z) を指している手。"""
        pose = np.eye(4)
        pose[0, 3], pose[1, 3] = x, y
        return pose

    def test_corner_zone_includes_outside_and_skips_the_close_button(self):
        overlay = self._overlay()
        pose_of = lambda index: np.eye(4)  # noqa: E731

        def corner(x, y):
            found = overlay.panelCornerAt(1, self._hand(x, y), pose_of)
            return found and found[:2]

        self.assertEqual(corner(0.44, -0.34), (1, -1))  # 右下の内側
        self.assertEqual(corner(0.47, -0.36), (1, -1))  # 右下の外側 (透明な角・枠の外でも掴める)
        self.assertEqual(corner(-0.44, 0.34), (-1, 1))  # 左上
        self.assertIsNone(corner(0.44, 0.34))  # 右上の内側は閉じるボタン
        self.assertEqual(corner(0.47, 0.36), (1, 1))  # 右上は外側だけ
        self.assertIsNone(corner(0.0, 0.0))
        self.assertIsNone(corner(0.60, -0.50))  # 離れすぎ
        overlay.panel_locked = True
        self.assertIsNone(corner(0.44, -0.34))  # ロック中は伸ばせない

    def _drag(self, overlay, corner, to_xy):
        hand = 1
        pose_of = lambda index: self._hand(*to_xy) if index == hand else np.eye(4)  # noqa: E731
        overlay.startResize(hand, corner, lambda index: np.eye(4))
        gripping = MagicMock(ulButtonPressed=1 << __import__("openvr").k_EButton_Grip)
        overlay.updateResize(pose_of, lambda index: gripping, 0.0)
        return pose_of

    def test_opposite_corner_stays_and_size_is_saved_on_release(self):
        overlay = self._overlay()
        pose_of = self._drag(overlay, (1, -1), (0.55, -0.45))  # 右下の角を右下へ 0.1m ずつ
        self.assertEqual(overlay.resizing["size"], (1000, 800))
        np.testing.assert_allclose(overlay.resizing["center"], (0.05, -0.05))  # 左上の角 (-0.45, 0.35) は動かない
        released = MagicMock(ulButtonPressed=0)
        overlay.updateResize(pose_of, lambda index: released, 0.1)
        self.assertIsNone(overlay.resizing)
        s = overlay.settings[PANEL]
        self.assertEqual((s["width"], s["height"]), (1000, 800))
        self.assertAlmostEqual(s["ui_scaling"], 1.0)  # 1px の長さは変えない (文字の大きさはそのまま)
        self.assertEqual(overlay.layout["regions"][PANEL][2:], (1000, 800))
        _, saved = overlay.position_changed_callback.call_args.args
        self.assertEqual((saved["width"], saved["height"]), (1000, 800))
        self.assertAlmostEqual(saved["x_pos"], 0.05, places=4)
        self.assertAlmostEqual(saved["y_pos"], -0.05, places=4)

    def test_invisible_log_cannot_be_resized(self):
        overlay = self._overlay()
        overlay.settings[PANEL]["opacity"] = 0.0
        self.assertIsNone(overlay.panelCornerAt(1, self._hand(0.44, -0.34), lambda index: np.eye(4)))

    def test_hiding_the_log_cancels_resizing(self):
        overlay = self._overlay()
        self._drag(overlay, (1, -1), (0.55, -0.45))
        overlay.setVrWindows(log=False, popup=False)
        overlay.applyVrWindows(lambda index: np.eye(4))
        self.assertIsNone(overlay.resizing)
        self.assertEqual(overlay.settings[PANEL]["width"], 900)  # 保存しない

    def test_log_on_a_hand_follows_the_hand_while_resizing(self):
        """手に付けたログは、伸ばしている間に手が動いても、放した位置で跳ばない。"""
        overlay = self._overlay()
        overlay.settings[PANEL]["tracker"] = "LeftHand"
        overlay.settings[PANEL]["z_pos"] = 0.0
        left, right = 1, 2
        overlay.overlay_system.getTrackedDeviceIndexForControllerRole.return_value = left
        before = overlay.panelRelative()
        hand_at = {"x": 0.0}

        def pose_of(index):
            pose = np.eye(4)
            if index == left:
                pose[0, 3] = hand_at["x"]  # 左手 (ログの固定先) が横へ動く
            return pose

        overlay.startResize(right, (1, -1), pose_of)
        hand_at["x"] = 0.3
        released = MagicMock(ulButtonPressed=0)
        overlay.updateResize(pose_of, lambda index: released, 0.1)
        np.testing.assert_allclose(overlay.panelRelative()[:, 3], before[:, 3], atol=1e-4)  # 手から見た位置は変わらない

    def test_revert_also_restores_the_position(self):
        """新しい大きさにできず元に戻すときは、伸ばす前の位置と幅にも戻す (跳ばない)。"""
        overlay = self._overlay()
        pose_of = self._drag(overlay, (1, -1), (0.55, -0.45))
        overlay.updateResize(pose_of, lambda index: MagicMock(ulButtonPressed=0), 0.1)
        self.assertAlmostEqual(overlay.settings[PANEL]["x_pos"], 0.05, places=4)
        overlay.retryOrRevertLayout(overlay.layout_requested_at + 5.0)
        s = overlay.settings[PANEL]
        self.assertEqual((s["width"], s["height"]), (900, 700))
        self.assertEqual((s["x_pos"], s["y_pos"], s["ui_scaling"]), (0.0, 0.0, 0.9))
        _, saved = overlay.position_changed_callback.call_args.args
        self.assertEqual((saved["x_pos"], saved["width"]), (0.0, 900))

    def test_ghost_is_hidden_when_the_vr_ui_is_turned_off_after_release(self):
        overlay = self._overlay()
        overlay.ghost_handle = 20
        pose_of = self._drag(overlay, (1, -1), (0.55, -0.45))
        overlay.updateResize(pose_of, lambda index: MagicMock(ulButtonPressed=0), 0.1)  # 放して、切り替え待ち
        overlay.overlay.hideOverlay.reset_mock()
        overlay.vr_panel_enabled = False
        overlay.applyVrWindows(lambda index: np.eye(4))
        overlay.overlay.hideOverlay.assert_any_call(20)

    def test_moving_after_release_is_kept_when_the_size_is_reverted(self):
        """伸ばして放した後に動かした位置は、大きさを元に戻しても残す。"""
        overlay = self._overlay()
        pose_of = self._drag(overlay, (1, -1), (0.55, -0.45))
        overlay.updateResize(pose_of, lambda index: MagicMock(ulButtonPressed=0), 0.1)
        moved = overlay.panelRelative()
        moved[0, 3] += 0.2
        overlay.commitPosition(PANEL, moved)  # 切り替え待ちの間に掴んで動かした
        x_after_move = overlay.settings[PANEL]["x_pos"]
        overlay.retryOrRevertLayout(overlay.layout_requested_at + 5.0)
        self.assertEqual(overlay.settings[PANEL]["width"], 900)
        self.assertEqual(overlay.settings[PANEL]["x_pos"], x_after_move)

    def test_error_while_resizing_stops_resizing(self):
        """伸ばしている処理で例外が出たら伸ばすのをやめる (毎フレーム同じ例外で操作できなくならない)。"""
        overlay = self._overlay()
        overlay.ghost_handle = 20
        self._drag(overlay, (1, -1), (0.55, -0.45))
        with patch("models.overlay.overlay.errorLogging"):
            overlay.onGrabError(RuntimeError("GL"))
        self.assertIsNone(overlay.resizing)
        overlay.overlay.hideOverlay.assert_any_call(20)

    def test_corner_handle_position(self):
        overlay = self._overlay()
        self.assertEqual(overlay.cornerHandleXY((-1, 1)), (34, 34))  # 左上
        self.assertEqual(overlay.cornerHandleXY((1, -1)), (866, 666))  # 右下
        self.assertIsNone(overlay.cornerHandleXY((1, 1)))  # 右上は閉じるボタン

    def test_size_stops_at_the_limits(self):
        overlay = self._overlay()
        self._drag(overlay, (1, -1), (2.0, 0.2))  # 右へ大きく、上へ (高さはほぼ0)
        self.assertEqual(overlay.resizing["size"], (1400, 400))


class PanelInputReentryTest(unittest.TestCase):
    def test_leaving_while_pressed_does_not_press_again_on_return(self):
        """トリガーを押したまま外れて戻ってきても、押し直したことにしない (離すまで無視する)。"""
        overlay = Overlay({})
        overlay.panel_hwnd = 123
        overlay.panel_image_size = (900, 836)
        state = MagicMock()
        state.rAxis[0].y = 0.0
        state.ulButtonPressed = 1 << openvr.k_EButton_SteamVR_Trigger
        with patch("models.overlay.overlay.window_capture") as wc:
            overlay.handlePanelInput(1, (450, 350), state)
            overlay.handlePanelInput(1, None, state)  # 押したまま外れた
            overlay.handlePanelInput(1, (450, 350), state)  # 押したまま戻ってきた
            self.assertEqual(wc.mouseDown.call_count, 1)
            state.ulButtonPressed = 0
            overlay.handlePanelInput(1, (450, 350), state)  # 離した
            state.ulButtonPressed = 1 << openvr.k_EButton_SteamVR_Trigger
            overlay.handlePanelInput(1, (450, 350), state)  # 押し直した
        self.assertEqual(wc.mouseDown.call_count, 2)


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

    def test_recall_while_looking_down_ends_up_in_view(self):
        """手首のランチャーを見下ろしながら呼び戻しても、呼び戻したログは視線から外れない。"""
        from models.overlay.overlay import isOutOfView, recallPose

        c, s_ = np.cos(np.radians(-60)), np.sin(np.radians(-60))
        self.head[:3, :3] = np.array([[1, 0, 0], [0, c, -s_], [0, s_, c]])  # 60°見下ろしている
        pose = recallPose(self.head)
        self.assertFalse(isOutOfView(self.head, pose[:3, 3], was_out=True))

    def test_recall_waits_for_the_log_to_open(self):
        """ランチャーの長押し: 閉じているログを開くのと同時に頼まれたら、開いてから呼び戻す。"""
        self.overlay.settings[PANEL]["tracker"] = "LeftHand"  # 手に付けていても呼び戻せる
        self.overlay.setVrWindows(log=False, popup=False)
        self.overlay.applyVrWindows(self.pose_of)
        self.overlay.requestRecallPanel()
        self.overlay.applyVrWindows(self.pose_of)  # まだ開いていない
        self.assertEqual(self.saved, [])
        self.overlay.setVrWindows(log=True, popup=False)
        self.overlay.applyVrWindows(self.pose_of)
        self.assertInFront()

    def test_recall_is_dropped_if_the_log_does_not_open(self):
        self.overlay.setVrWindows(log=False, popup=False)
        self.overlay.applyVrWindows(self.pose_of)
        with patch("models.overlay.overlay.time.monotonic", return_value=100.0):
            self.overlay.requestRecallPanel()
        with patch("models.overlay.overlay.time.monotonic", return_value=102.0):
            self.overlay.applyVrWindows(self.pose_of)
        self.assertIsNone(self.overlay.vr_recall_requested)

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
