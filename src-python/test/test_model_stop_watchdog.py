"""`Model.stopWatchdog()` がフリーズダンプのタイマーを確実に解除することのテスト。

背景 (再評価 2026-09-14 P-4 のフォローアップ、実機ログで発覚):

P-4 で shutdown() から stopWatchdog() を呼ぶようにしたが、実機では

    shutdown: watchdog の停止が 5.0s でタイムアウトしました

となり、目的だった「正常終了時に freeze_trace.log へ偽のダンプが出るのを
防ぐ」が達成できていなかった。原因:

- `Watchdog.start()` は末尾で `time.sleep(self.interval)` する (既定20秒)
- `threadFnc.stop()` は loop フラグを降ろすだけでこの sleep を中断できない
- よって `join()` は最大 interval 秒ブロックする
- `faulthandler.cancel_dump_traceback_later()` はその join の *後ろ* にあった
- shutdown() 側の `_stopServiceForShutdown` は5秒で諦めるため、解除は
  一度も実行されなかった

解除を join より前に移し、join に上限を付ける。
"""

import unittest
from unittest.mock import patch

import model as model_module
from model import Model, threadFnc


class _NeverStoppingWatchdogThread(threadFnc):
    """join() が必ずタイムアウトする threadFnc の代役。

    実機の `Watchdog.start()` が `time.sleep(20)` の途中で止まれない状況を、
    スレッドを起動せずに再現する。
    """

    def __init__(self) -> None:
        # Thread.__init__ は通すが start() はしない (join は即タイムアウトする)。
        super().__init__(fnc=lambda: None)
        self.stop_called = False
        self.join_timeouts: list = []

    def stop(self) -> None:
        self.stop_called = True

    def join(self, timeout=None) -> None:  # type: ignore[override]
        self.join_timeouts.append(timeout)


class TestStopWatchdogCancelsDumpBeforeJoining(unittest.TestCase):
    def setUp(self) -> None:
        self.model = object.__new__(Model)
        self.model._inited = True
        self.model._init_failed = False
        self.thread = _NeverStoppingWatchdogThread()
        self.model.th_watchdog = self.thread

    def test_dump_timer_is_cancelled_even_though_join_would_block(self) -> None:
        with patch.object(model_module.faulthandler, "cancel_dump_traceback_later") as mock_cancel:
            self.model.stopWatchdog()

        mock_cancel.assert_called_once()
        self.assertTrue(self.thread.stop_called)

    def test_join_is_bounded(self) -> None:
        """join を無期限にすると shutdown が最大 interval 秒待たされる。"""
        with patch.object(model_module.faulthandler, "cancel_dump_traceback_later"):
            self.model.stopWatchdog()

        self.assertEqual(len(self.thread.join_timeouts), 1)
        timeout = self.thread.join_timeouts[0]
        self.assertIsNotNone(timeout, "join() は無期限にしてはいけない")
        self.assertLessEqual(timeout, 5.0, "shutdown 側の停止上限(5秒)を超えてはいけない")

    def test_cancel_happens_before_join(self) -> None:
        """順序が入れ替わると実機で観測された不具合がそのまま再発する。"""
        order: list = []

        def record_cancel() -> None:
            order.append("cancel")

        self.thread.join = lambda timeout=None: order.append("join")  # type: ignore[assignment]

        with patch.object(model_module.faulthandler, "cancel_dump_traceback_later", record_cancel):
            self.model.stopWatchdog()

        self.assertEqual(order, ["cancel", "join"])

    def test_no_watchdog_thread_still_cancels_the_dump_timer(self) -> None:
        """startWatchdog() より前に shutdown() が走る経路でも解除すること。"""
        self.model.th_watchdog = None

        with patch.object(model_module.faulthandler, "cancel_dump_traceback_later") as mock_cancel:
            self.model.stopWatchdog()

        mock_cancel.assert_called_once()


if __name__ == "__main__":
    unittest.main()
