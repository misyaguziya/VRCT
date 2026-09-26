"""OCRのキャプチャ経路選択のテスト。

VRの読み出しで何も取れない (VRChatがSteamVRのシーンでない、読み出し失敗) とき、
以前は何も読めないまま待ち続けていた。デスクトップ画面の取得へ切り替えることを見る。
"""

import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from models.ocr.ocr_capture import OcrCapture
from models.ocr.ocr_capture_openvr import OpenVRMirrorCapture


def _frame() -> np.ndarray:
    return np.random.default_rng(0).integers(0, 255, (8, 8, 3), dtype=np.uint8)


class TestFallbackToDesktopWindow(unittest.TestCase):
    def _make(self, vr_frame):
        capture = OcrCapture()
        capture._openvr = MagicMock()
        capture._openvr.isAvailable.return_value = True
        capture._openvr.capture.return_value = vr_frame
        capture._hwnd = MagicMock()
        capture._hwnd.isAvailable.return_value = True
        capture._hwnd.capture.return_value = _frame()
        return capture

    def test_vr_frame_is_used_when_available(self) -> None:
        vr = _frame()
        capture = self._make(vr)
        with patch("models.ocr.ocr_capture._isSteamvrRunning", return_value=True):
            self.assertIs(capture.get(), vr)
        capture._hwnd.capture.assert_not_called()

    def test_falls_back_to_the_window_when_vr_gives_nothing(self) -> None:
        capture = self._make(None)
        with patch("models.ocr.ocr_capture._isSteamvrRunning", return_value=True):
            frame = capture.get()
            self.assertIsNotNone(frame)
            self.assertEqual(capture.backend, OcrCapture.BACKEND_HWND)
            # 次の再判定までは VR を試し直さない。
            capture.get()
        capture._openvr.capture.assert_called_once()


class TestVrchatSceneCheck(unittest.TestCase):
    """VRChat 以外 (SteamVR Home 等) のシーンは読まない。判定は収集ツールで実機確認済みの方法。"""

    def _make(self, renderer: int, focus: int):
        capture = OpenVRMirrorCapture()
        capture._initialized = True
        capture._session_held = True
        capture._compositor = MagicMock()
        capture._compositor.getLastFrameRenderer.return_value = renderer
        capture._compositor.getCurrentSceneFocusProcess.return_value = focus
        return capture

    def _name(self, name: str):
        process = MagicMock()
        process.return_value.name.return_value = name
        return patch("models.ocr.ocr_capture_openvr.Process", process)

    def test_other_scene_app_is_not_read_and_session_is_kept(self) -> None:
        capture = self._make(renderer=100, focus=100)
        with self._name("vrserver.exe"), \
                patch("models.ocr.ocr_capture_openvr.openvr_session.release") as release:
            self.assertIsNone(capture.capture())
        # 異常ではないので、次に VRChat へ戻ったときのためにセッションは保持する。
        release.assert_not_called()
        self.assertTrue(capture._initialized)

    def test_vrchat_scene_is_detected(self) -> None:
        with self._name("VRChat.exe"):
            self.assertTrue(self._make(renderer=100, focus=100)._isVrchatScene())
            # 描画プロセスとフォーカスが食い違う (切り替え途中) ときは読まない。
            self.assertFalse(self._make(renderer=100, focus=200)._isVrchatScene())
            self.assertFalse(self._make(renderer=0, focus=0)._isVrchatScene())


if __name__ == "__main__":
    unittest.main()
