"""旧字幕を表示したまま VR UI を OFF/ON したときの撮影復旧。"""

import threading
import unittest
from types import SimpleNamespace
from unittest.mock import ANY, MagicMock, patch, sentinel

from controller import Controller
from model import Model
from models.overlay.overlay import LAUNCHER, PANEL, VR_ATLAS_SIZE, Overlay, _PANEL_ERROR_LIMIT


class VrPanelCaptureRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.overlay = Overlay({"small": {}, PANEL: {}, LAUNCHER: {}})
        self.overlay.initialized = True
        self.overlay.loop = True
        self.overlay.thread_overlay = sentinel.overlay_thread
        self.overlay.gl = sentinel.gl
        self.overlay.handle = {"small": 1, PANEL: 2, LAUNCHER: 3}
        self.overlay.panel_hwnd = 123
        self.overlay.transferCapture = MagicMock()
        self.overlay.startCaptureJob = lambda job: Overlay.runCaptureJob(job)

        # 実物の Model メソッドを使い、音声/GPU/OpenVR の初期化は行わない。
        self.model = object.__new__(Model)
        self.model.overlay = self.overlay
        self.model.ensure_initialized = MagicMock()
        self.model.startOverlay = MagicMock(wraps=self.model.startOverlay)
        self.model.shutdownOverlay = MagicMock()
        settings = SimpleNamespace(
            OVERLAY_SMALL_LOG=True, OVERLAY_LARGE_LOG=False, OVERLAY_VR_PANEL=True,
            OVERLAY_VR_PANEL_LOCKED=False, OVERLAY_VR_LAUNCHER_AUTO_HIDE=True,
        )
        self._patch("controller.model", self.model)
        # Config の実ファイルへの保存を避け、Controller の切り替え経路を通す。
        self._patch("controller.config", settings)
        self._patch("models.overlay.overlay.errorLogging")
        self._patch("models.overlay.overlay.printLog")
        self.wc = self._patch("models.overlay.overlay.window_capture")
        self.wc.isWindow.return_value = True
        self.wc.findWindow.return_value = 456
        self.wc.resizeClient.side_effect = lambda hwnd, width, height: (width, height)
        self.stream = self.wc.WindowStream.return_value
        self.stream.hwnd, self.stream.closed, self.stream.stale = 456, False, False
        self.capture = (b"stream", VR_ATLAS_SIZE, (0, 0) + VR_ATLAS_SIZE)
        self.stream.take.return_value = self.capture
        self.printed = (b"printed", VR_ATLAS_SIZE, (0, 0) + VR_ATLAS_SIZE)
        self.wc.captureWindowRaw.return_value = self.printed

    def _patch(self, target, *args):
        patcher = patch(target, *args)
        value = patcher.start()
        self.addCleanup(patcher.stop)
        return value

    def _off_on(self):
        Controller.setDisableOverlayVrPanel()
        Controller.setEnableOverlayVrPanel()
        self.model.shutdownOverlay.assert_not_called()

    def _tick(self, in_thread=False):
        # オーバーレイループを1周だけ実行。描画・追跡・watchdog は実機に触れない。
        errors = []

        def run():
            try:
                self.overlay.mainloop()
            except Exception as error:
                errors.append(error)

        with patch.object(self.overlay, "checkActive", side_effect=[True, False]), \
                patch.object(self.overlay, "update"), \
                patch.object(self.overlay, "updateGrab"), \
                patch.object(self.overlay, "teardown"), \
                patch("models.overlay.overlay.Thread"), \
                patch("models.overlay.overlay.time.sleep"):
            if in_thread:
                thread = threading.Thread(target=run)
                thread.start()
                thread.join(timeout=2)
                self.assertFalse(thread.is_alive())
            else:
                run()
        if errors:
            raise errors[0]

    def test_off_on_recovers_stopped_capture_without_restarting_subtitles(self):
        self.overlay.panel_stream = MagicMock()
        for _ in range(_PANEL_ERROR_LIMIT):
            self.overlay.onPanelError(RuntimeError("capture failed"))
        self.assertTrue(self.overlay.panel_stopped)
        old_job = SimpleNamespace(done=False, result=None)
        self.overlay.capture_job = old_job
        handles = self.overlay.handle

        # 1周より短い OFF/ON でも、復旧処理は所有スレッドへ渡す。
        self._off_on()
        self.assertTrue(self.overlay.panel_stopped)
        self._tick()

        self.assertFalse(self.overlay.panel_stopped)
        self.assertEqual(self.overlay.panel_errors, 0)
        self.assertIsNone(self.overlay.panel_error)
        self.assertEqual(self.overlay.panel_hwnd, 456)
        self.overlay.transferCapture.assert_called_once_with(self.capture, ANY)
        self.assertIs(self.overlay.gl, sentinel.gl)
        self.assertIs(self.overlay.handle, handles)
        self.assertIs(self.overlay.thread_overlay, sentinel.overlay_thread)
        self.assertTrue(self.overlay.loop)

        # 切り替え前の撮影が後から戻っても、その結果を使わない。
        old_job.result, old_job.done = (b"old", None, (0, 0) + VR_ATLAS_SIZE), True
        self.overlay.panel_last_capture = 0
        self._tick()
        self.assertTrue(all(call.args[0] == self.capture for call in self.overlay.transferCapture.call_args_list))

    def test_failed_stream_is_retried_through_controller_off_on(self):
        self.wc.WindowStream.side_effect = [OSError("GraphicsCaptureItem"), self.stream]
        self._tick()
        self.assertTrue(self.overlay.stream_unavailable)
        self.overlay.transferCapture.assert_called_once_with(self.printed, ANY)
        self.overlay.transferCapture.reset_mock()

        self._off_on()
        self._tick()

        self.assertFalse(self.overlay.stream_unavailable)
        self.assertEqual(self.wc.WindowStream.call_count, 2)
        self.overlay.transferCapture.assert_called_once_with(self.capture, ANY)

    def test_repeated_enabled_sync_does_not_clear_a_capture_failure(self):
        self.overlay.panel_stopped = True
        self.overlay.stream_unavailable = True
        Controller.syncOverlayRunning()
        Controller.syncOverlayRunning()
        self._tick()
        self.assertTrue(self.overlay.panel_stopped)
        self.assertTrue(self.overlay.stream_unavailable)
        self.wc.WindowStream.assert_not_called()
        self.overlay.transferCapture.assert_not_called()

    def test_missing_dependency_stays_on_printwindow_after_off_on(self):
        self.overlay.stream_missing = True
        self._off_on()
        self._tick()
        self.assertTrue(self.overlay.stream_missing)
        self.wc.WindowStream.assert_not_called()
        self.wc.captureWindowRaw.assert_called_once_with(456)
        self.overlay.transferCapture.assert_called_once_with(self.printed, ANY)

    def test_stream_cleanup_happens_on_the_overlay_thread(self):
        old_stream = MagicMock()
        self.overlay.panel_stream = old_stream
        closed_on = []
        old_stream.close.side_effect = lambda: closed_on.append(threading.get_ident())
        self._off_on()
        old_stream.close.assert_not_called()
        self._tick(in_thread=True)
        self.assertEqual(len(closed_on), 1)
        self.assertNotEqual(closed_on[0], threading.get_ident())
        self.assertIs(self.overlay.panel_stream, self.stream)

    def test_failed_retry_falls_back_without_retrying_each_frame(self):
        self.wc.WindowStream.side_effect = OSError("GraphicsCaptureItem")
        self._tick()
        self._off_on()
        self._tick()
        self.assertTrue(self.overlay.stream_unavailable)
        self.assertEqual(self.wc.WindowStream.call_count, 2)
        self.overlay.panel_last_capture = 0
        self._tick()
        self.assertEqual(self.wc.WindowStream.call_count, 2)
        self.overlay.transferCapture.assert_called_with(self.printed, ANY)

    def test_last_disabled_request_keeps_capture_off_until_the_next_enable(self):
        self.overlay.panel_stopped = True
        self._off_on()
        Controller.setDisableOverlayVrPanel()
        self._tick()
        self.assertFalse(self.overlay.vr_panel_enabled)
        self.wc.WindowStream.assert_not_called()
        self.overlay.transferCapture.assert_not_called()

        Controller.setEnableOverlayVrPanel()
        self._tick()
        self.assertFalse(self.overlay.panel_stopped)
        self.overlay.transferCapture.assert_called_once_with(self.capture, ANY)
        self.model.shutdownOverlay.assert_not_called()

    def test_pending_layout_wait_restarts_without_losing_displayed_bounds(self):
        applied = dict(self.overlay.layout)
        self.overlay.layout_applied = applied
        self.overlay.panel_image_size = VR_ATLAS_SIZE
        for previous in (1.0, 10000.0):
            with self.subTest(previous=previous):
                self.overlay.layout_requested_at = previous
                self.overlay.layout_retried = True
                self._off_on()
                with patch("models.overlay.overlay.time.monotonic", return_value=100.0):
                    self._tick()
                self.assertEqual(self.overlay.layout_requested_at, max(previous, 100.0))
                self.assertFalse(self.overlay.layout_retried)
                self.assertIs(self.overlay.layout_applied, applied)
                self.assertEqual(self.overlay.panel_image_size, VR_ATLAS_SIZE)


if __name__ == "__main__":
    unittest.main()
