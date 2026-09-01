"""Controller.shutdown() のロック取得に関するテスト (ロードマップ項目 5)。

対象の欠陥:
  shutdown() は model.stopMicTranscript() 等を mic/speaker_lifecycle_lock を
  取らずに直接呼んでいた。他の全ての start/stop 系
  (stopTranscriptionSendMessage, AudioLifecycleWorker 経由の
  restartAccessMicDevices 等) は必ずこのロックを取るため、shutdown() だけが
  それらと並行実行され得た。最悪ケースでは、AudioLifecycleWorker がまだ
  デバイス切替の途中 (ロック保持・PyAudio open 中) に shutdown() の
  停止処理が割り込み、_stop() と _start() が同一 Session に対して交錯し、
  listener スレッドと PyAudio ストリームが宙に浮いたままプロセスが終了する。

  修正: _stopLockedForShutdown() でロックを取得してから停止関数を呼ぶ。
  ロックが (異常に長時間保持されて) 取得できない場合でも shutdown() 自体は
  無期限にハングしないよう、acquire(timeout=...) を使う。
"""

import threading
import time
import unittest
from unittest.mock import patch

import controller as controller_module
from controller import Controller


class StopLockedForShutdownTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        self.controller.mic_lifecycle_lock = threading.Lock()
        self.controller.speaker_lifecycle_lock = threading.Lock()

    def test_calls_stop_fn_while_holding_the_lock(self) -> None:
        lock = self.controller.mic_lifecycle_lock
        observed_locked = []

        def stop_fn() -> None:
            # 呼ばれた時点でロックが取得済み (= 他の保持者がいない) ことを
            # 直接は検証できない (自スレッドが既に持っているため) が、
            # 少なくとも stop_fn 実行中にロックが acquire 可能でない
            # (= 自分が保持中) ことを確認する。
            observed_locked.append(lock.locked())

        self.controller._stopLockedForShutdown(lock, stop_fn, "test")

        self.assertEqual(observed_locked, [True])
        # 呼び出し後はロックが解放されていること (次の停止処理や、
        # 通常経路の start/stop がブロックされないこと)。
        self.assertFalse(lock.locked())

    def test_exception_in_stop_fn_is_caught_and_lock_is_still_released(self) -> None:
        lock = self.controller.mic_lifecycle_lock

        def failing_stop_fn() -> None:
            raise RuntimeError("boom")

        with patch.object(controller_module, "errorLogging") as mock_error_logging:
            try:
                self.controller._stopLockedForShutdown(lock, failing_stop_fn, "test")
            except RuntimeError:
                self.fail("_stopLockedForShutdown が stop_fn の例外を伝播させてはいけない")
            mock_error_logging.assert_called_once()

        self.assertFalse(lock.locked(), "例外発生時もロックは解放されなければならない")

    def test_times_out_and_skips_when_lock_is_held_elsewhere(self) -> None:
        lock = self.controller.mic_lifecycle_lock
        lock.acquire()  # 他スレッド (例: AudioLifecycleWorker) が保持中を模す
        self.addCleanup(lock.release)

        calls = []
        with patch.object(controller_module, "_SHUTDOWN_LIFECYCLE_LOCK_TIMEOUT_SEC", 0.2):
            with patch.object(controller_module, "printLog") as mock_print_log:
                self.controller._stopLockedForShutdown(lock, lambda: calls.append(1), "test")

        # タイムアウトしたので停止関数は呼ばれず、shutdown() 自体もハングしない。
        self.assertEqual(calls, [])
        mock_print_log.assert_called_once()

    def test_does_not_block_other_lock_holders_once_it_returns(self) -> None:
        # 実際のスレッド競合下で、stop_fn 完了後にロックが速やかに他スレッドへ
        # 渡ることを確認する (単体プロセス内での簡易的な結合テスト)。
        lock = self.controller.mic_lifecycle_lock
        order = []

        def slow_stop_fn() -> None:
            order.append("stop_fn:start")
            time.sleep(0.05)
            order.append("stop_fn:end")

        def other_holder() -> None:
            with lock:
                order.append("other:acquired")

        t = threading.Thread(target=other_holder)

        def run_shutdown_stop():
            self.controller._stopLockedForShutdown(lock, slow_stop_fn, "test")
            t.start()

        run_shutdown_stop()
        t.join(timeout=2)

        self.assertEqual(order, ["stop_fn:start", "stop_fn:end", "other:acquired"])


class ShutdownUsesLockedStopHelpersTests(unittest.TestCase):
    """shutdown() 本体が、生の model.* 呼び出しではなく
    _stopLockedForShutdown 経由で 4 つの停止関数を呼んでいることを確認する。"""

    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        self.controller.mic_lifecycle_lock = threading.Lock()
        self.controller.speaker_lifecycle_lock = threading.Lock()
        self.locked_calls = []
        self.controller._stopLockedForShutdown = (
            lambda lock, stop_fn, label: self.locked_calls.append(label)
        )

    @patch("controller.device_manager")
    @patch("controller.model")
    @patch("controller.config")
    def test_shutdown_routes_all_four_stops_through_the_lock_helper(
        self, mock_config, mock_model, mock_device_manager
    ) -> None:
        mock_model.telemetryShutdown.return_value = None
        result = self.controller.shutdown()

        self.assertEqual(
            self.locked_calls,
            ["mic transcript", "speaker transcript", "mic energy", "speaker energy"],
        )
        self.assertEqual(result, {"status": 200, "result": True})


if __name__ == "__main__":
    unittest.main()
