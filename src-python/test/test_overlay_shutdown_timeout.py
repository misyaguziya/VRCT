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
