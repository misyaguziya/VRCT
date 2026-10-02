"""Overlay.updateImage()の再初期化待ちループ / shutdownOverlay()のスレッド
joinのタイムアウトに関するテスト(バックエンドレビュー フェーズ4項目31)。

対象の欠陥:
  1. updateImage()は setOverlayRaw() が例外を投げると reStartOverlay() で
     再初期化を試みるが、その後の `while self.initialized is False:
     time.sleep(0.1)` にタイムアウトが無かった。SteamVRが落ちたままだと
     self.initialized が永遠に True にならず無限に回り続ける。この
     呼び出し元は mainloop ワーカースレッドなので、詰まるとワーカーを
     1本恒久的に奪う。
  2. shutdownOverlay() の thread_overlay.join() にもタイムアウトが無く、
     mainloop() が OpenVR のブロッキング呼び出し等で詰まっていると
     無期限にハングした。

  修正: 両方に上限(既定5秒)を設ける。Pythonのスレッドは外部から強制
  終了できないため、これらは「詰まったスレッドを殺す」ものではなく
  「待つのを諦める」もの。shutdownOverlay()がタイムアウトした場合は
  self.overlay/self.systemを破棄せず(詰まったスレッドが後で復帰した際に
  Noneへ触れて例外になることを避けるため)、代わりにself.initializedを
  Falseに戻して次のstartOverlay()で復旧できるようにする(OpenVRハンドル
  とセッション参照は1つ分リークするが、機能が再起動必須になることは
  避ける)。
"""

import threading
import time
import sys
import unittest
from threading import Thread
from unittest.mock import MagicMock, patch

import openvr
from PIL import Image

from models.overlay.overlay import Overlay

# Real classes, captured before any test patches openvr.IVRSystem/IVROverlay
# themselves -- MagicMock(spec=...) needs the genuine class, not a mock of it.
_RealIVRSystem = openvr.IVRSystem
_RealIVROverlay = openvr.IVROverlay


def _overlay_settings() -> dict:
    return {
        "small": {
            "x_pos": 0.0, "y_pos": 0.0, "z_pos": 0.0,
            "x_rotation": 0.0, "y_rotation": 0.0, "z_rotation": 0.0,
            "display_duration": 5, "fadeout_duration": 2,
            "opacity": 1.0, "ui_scaling": 1.0, "tracker": "HMD",
        },
    }


class UpdateImageReinitTimeoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.overlay = Overlay(_overlay_settings())
        self.overlay.initialized = True
        self.overlay.overlay = MagicMock()
        self.overlay.overlay.setOverlayRaw.side_effect = RuntimeError("boom")
        self.overlay.handle = {"small": 1}

    def test_gives_up_after_reinit_timeout_without_hanging_the_caller(self) -> None:
        def fake_restart() -> None:
            # 実際の reStartOverlay() が新しいバックグラウンドスレッドを
            # 立てて再初期化を試みるが、SteamVR が落ちたままで
            # self.initialized が二度と True にならない状況を模す。
            self.overlay.initialized = False

        self.overlay.reStartOverlay = MagicMock(side_effect=fake_restart)

        with patch("models.overlay.overlay._REINIT_WAIT_TIMEOUT_SEC", 0.2), \
             patch("models.overlay.overlay._REINIT_WAIT_POLL_INTERVAL_SEC", 0.02), \
             patch("models.overlay.overlay.printLog") as mock_print_log:
            start = time.monotonic()
            self.overlay.updateImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0)), "small")
            elapsed = time.monotonic() - start

        self.assertLess(elapsed, 2.0, "タイムアウトを超えて長時間ブロックしてはいけない")
        mock_print_log.assert_called_once()
        # 再初期化が終わらなかったので、リトライの setOverlayRaw は
        # 呼ばれていないこと (=最初の1回だけ)。
        self.overlay.overlay.setOverlayRaw.assert_called_once()

    def test_retries_and_succeeds_once_reinit_completes_within_timeout(self) -> None:
        def fake_restart() -> None:
            self.overlay.initialized = True  # 再初期化が(すぐに)成功した場合

        self.overlay.reStartOverlay = MagicMock(side_effect=fake_restart)

        with patch("models.overlay.overlay._REINIT_WAIT_TIMEOUT_SEC", 5.0):
            self.overlay.updateImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0)), "small")

        # 最初の失敗分 + リトライ分で2回呼ばれる。
        self.assertEqual(self.overlay.overlay.setOverlayRaw.call_count, 2)


class ShutdownOverlayJoinTimeoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.overlay = Overlay(_overlay_settings())
        self.overlay.initialized = True
        self.overlay.init_process = False
        self.overlay.overlay = MagicMock(spec=_RealIVROverlay)
        self.overlay.system = MagicMock(spec=_RealIVRSystem)
        self.overlay.handle = {"small": 1}

    def test_gives_up_after_join_timeout_and_resets_initialized_without_destroying_handles(
        self,
    ) -> None:
        # mainloop() が (OpenVR呼び出し等で) 詰まって二度と戻ってこないスレッド
        # を模す。
        never_set = threading.Event()
        stuck_thread = Thread(target=never_set.wait, daemon=True)
        stuck_thread.start()
        self.addCleanup(never_set.set)
        self.addCleanup(lambda: stuck_thread.join(timeout=2))
        self.overlay.thread_overlay = stuck_thread

        with patch("models.overlay.overlay._SHUTDOWN_JOIN_TIMEOUT_SEC", 0.2), \
             patch("models.overlay.overlay.printLog") as mock_print_log, \
             patch("models.openvr_session.release") as release_mock:
            start = time.monotonic()
            self.overlay.shutdownOverlay()
            elapsed = time.monotonic() - start

        self.assertLess(elapsed, 2.0, "タイムアウトを超えて長時間ブロックしてはいけない")
        mock_print_log.assert_called_once()

        # 古いスレッドの追跡は諦めるが、再有効化で復旧できるよう
        # initialized は False に戻す。
        self.assertIsNone(self.overlay.thread_overlay)
        self.assertFalse(self.overlay.initialized)

        # 詰まっているかもしれない古いスレッドが後で復帰した際に例外に
        # ならないよう、overlay/systemは破棄しない(=リークを許容)。
        self.overlay.overlay.destroyOverlay.assert_not_called()
        release_mock.assert_not_called()
        self.assertIsNotNone(self.overlay.overlay)
        self.assertIsNotNone(self.overlay.system)

    def test_shutdown_completes_normally_when_thread_exits_promptly(self) -> None:
        # 通常ケース (詰まっていない) の回帰確認: join にタイムアウトを
        # 付けても、素直に終わるスレッドに対する挙動は変わらないこと。
        self.overlay.loop = True

        def quick_loop() -> None:
            while self.overlay.loop is not False:
                time.sleep(0.01)

        quick_thread = Thread(target=quick_loop, daemon=True)
        quick_thread.start()
        self.overlay.thread_overlay = quick_thread
        mock_overlay_api = self.overlay.overlay  # 破棄後もassertできるよう保持

        with patch("models.openvr_session.release") as release_mock:
            self.overlay.shutdownOverlay()

        self.assertIsNone(self.overlay.thread_overlay)
        self.assertFalse(self.overlay.initialized)
        mock_overlay_api.destroyOverlay.assert_called_once_with(1)
        release_mock.assert_called_once()
        self.assertIsNone(self.overlay.overlay)
        self.assertIsNone(self.overlay.system)


if __name__ == "__main__":
    unittest.main()


class StartCancelTest(unittest.TestCase):
    """SteamVR の起動を待っている間に止められたら、SteamVR が起動してもオーバーレイを出さない。"""

    def _overlay(self):
        from models.overlay.overlay import Overlay

        overlay = Overlay({})
        overlay.init = MagicMock()
        return overlay

    def test_shutdown_while_waiting_for_steamvr_cancels_the_start(self):
        overlay = self._overlay()
        with patch("models.overlay.overlay._START_CANCEL_POLL_SEC", 0.01), \
                patch.object(overlay, "checkSteamvrRunning", return_value=False):
            overlay.startOverlay()
            self.assertTrue(overlay.init_process)
            overlay.shutdownOverlay()
            overlay.thread_overlay.join(timeout=2.0)
        self.assertFalse(overlay.thread_overlay.is_alive())
        overlay.init.assert_not_called()  # SteamVR が起動しても作らない
        self.assertFalse(overlay.init_process)
        self.assertFalse(overlay.start_cancelled)

    def test_off_then_on_while_waiting_keeps_waiting(self):
        overlay = self._overlay()
        steamvr = {"running": False}
        with patch("models.overlay.overlay._START_CANCEL_POLL_SEC", 0.01), \
                patch("models.overlay.overlay._STEAMVR_POLL_SEC", 0.02), \
                patch.object(overlay, "checkSteamvrRunning", side_effect=lambda: steamvr["running"]):
            overlay.startOverlay()
            overlay.shutdownOverlay()
            overlay.startOverlay()  # すぐ ON に戻した
            steamvr["running"] = True
            overlay.thread_overlay.join(timeout=2.0)
        overlay.init.assert_called_once_with()  # 待ち続けて、SteamVR が起動したら作る


class SteamvrCheckTest(unittest.TestCase):
    def test_process_that_exits_during_the_check_does_not_raise(self):
        """確かめている途中で終わったプロセス (名前が取れない) があっても、例外にしない。"""
        from models.overlay.overlay import Overlay

        gone = MagicMock(info={"name": None})
        steamvr = MagicMock(info={"name": "vrmonitor.exe"})
        with patch("models.overlay.overlay.process_iter", return_value=[gone, steamvr]) as it, \
                patch("models.overlay.overlay.os.name", "nt"):
            self.assertTrue(Overlay.checkSteamvrRunning())
        it.assert_called_once_with(["name"])
        with patch("models.overlay.overlay.process_iter", return_value=[gone]), \
                patch("models.overlay.overlay.os.name", "nt"):
            self.assertFalse(Overlay.checkSteamvrRunning())

    def test_error_in_the_overlay_thread_allows_starting_again(self):
        """オーバーレイのスレッドが例外で終わっても記録し、次の ON で作り直せるようにする。"""
        from models.overlay.overlay import Overlay

        overlay = Overlay({})
        overlay.init = MagicMock()
        with patch.object(overlay, "checkSteamvrRunning", side_effect=RuntimeError("boom")), \
                patch("models.overlay.overlay.errorLogging") as logged:
            overlay.startOverlay()
            overlay.thread_overlay.join(timeout=2.0)
        logged.assert_called_once()
        self.assertFalse(overlay.init_process)
        with patch.object(overlay, "checkSteamvrRunning", return_value=True):
            overlay.startOverlay()  # 作り直せる
            overlay.thread_overlay.join(timeout=2.0)
        overlay.init.assert_called_once_with()


class StallReportTest(unittest.TestCase):
    """オーバーレイの処理が止まった・遅いときに、どこかをログに出す (実機での切り分け用)。"""

    def test_slow_step_is_reported(self):
        from models.overlay.overlay import Overlay

        overlay = Overlay({})
        with patch("models.overlay.overlay.time.monotonic", side_effect=[100.0, 100.2, 100.3, 111.0]), \
                patch("models.overlay.overlay.printLog") as log:
            overlay.step_reported_at = 100.0
            overlay.loop_step = ("idle", 100.0)
            overlay.markStep("panel:upload")    # 100.0
            overlay.markStep("panel:set_texture")  # 100.2 → upload に 0.2秒
            overlay.markStep("sleep")  # 100.3
            overlay.reportSlowSteps()  # 111.0 → 10秒たった
        log.assert_called_once()
        self.assertEqual(log.call_args.args[1], {"panel:upload": 200, "panel:set_texture": 100})

    def test_stalled_step_is_reported_with_its_stack(self):
        import threading

        from models.overlay.overlay import Overlay

        overlay = Overlay({})
        overlay.loop = True
        overlay.loop_step = ("panel:set_texture", 0.0)  # ずっと前から進んでいない
        frames = {threading.get_ident(): sys._getframe()}
        with patch("models.overlay.overlay._STALL_REPORT_SEC", 0.1), \
                patch("models.overlay.overlay.time.sleep", side_effect=lambda _: setattr(overlay, "loop", overlay.loop and log.call_count == 0)), \
                patch("models.overlay.overlay.printLog") as log:
            overlay.watchStall(lambda: frames, threading.get_ident())
        log.assert_called_once()
        self.assertEqual(log.call_args.args[1]["step"], "panel:set_texture")
        self.assertIn("test_stalled_step_is_reported_with_its_stack", log.call_args.args[1]["stack"])


class StepBreakdownTest(unittest.TestCase):
    def test_breakdown_is_logged_per_second_only_when_busy(self):
        from unittest.mock import patch

        from models.overlay.overlay import Overlay

        overlay = Overlay({})
        overlay.step_reported_at = 0.0
        overlay.step_total = {"panel:upload": 5.0, "grab": 1.0, "panel:convert": 0.001}
        overlay.step_loops = 100
        with patch("models.overlay.overlay.time.monotonic", return_value=10.0), patch("models.overlay.overlay.printLog") as logged:
            overlay.reportSlowSteps()
        data = logged.call_args.args[1]
        self.assertEqual(data["panel:upload"], 500)  # 5 秒 / 10 秒 = 500 ms/秒
        self.assertEqual(data["grab"], 100)
        self.assertEqual(data["loops_per_sec"], 10.0)
        self.assertNotIn("panel:convert", data)  # 2 ms/秒に満たない段階は出さない
        overlay.step_reported_at = 0.0
        overlay.step_total = {"grab": 0.01}
        with patch("models.overlay.overlay.time.monotonic", return_value=10.0), patch("models.overlay.overlay.printLog") as logged:
            overlay.reportSlowSteps()
        logged.assert_not_called()  # 暇なときは出さない


class ThreadPriorityTest(unittest.TestCase):
    def test_mainloop_raises_the_thread_priority(self):
        from unittest.mock import patch

        from models.overlay.overlay import Overlay

        overlay = Overlay({})
        overlay.loop = False
        with patch("models.overlay.overlay.raiseThreadPriority") as raised, patch.object(Overlay, "checkActive", return_value=False),                 patch.object(Overlay, "teardown"), patch.object(Overlay, "notifyPanelOutOfView"), patch("models.overlay.overlay.Thread"):
            overlay.mainloop()
        raised.assert_called_once_with()

    @unittest.skipUnless(__import__("os").name == "nt", "Windows only")
    def test_priority_is_really_raised_and_restored(self):
        import ctypes
        import threading

        from models.overlay.overlay import raiseThreadPriority

        result = {}

        def run():
            kernel32 = ctypes.windll.kernel32
            kernel32.GetCurrentThread.restype = ctypes.c_void_p
            raiseThreadPriority()
            result["priority"] = kernel32.GetThreadPriority(ctypes.c_void_p(kernel32.GetCurrentThread()))

        thread = threading.Thread(target=run)
        thread.start()
        thread.join()
        self.assertEqual(result["priority"], 1)
