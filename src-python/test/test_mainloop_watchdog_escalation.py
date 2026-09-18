"""watchdog タイムアウト時のエスカレーション処理に関するテスト
(フェーズ3項目19)。

対象の欠陥:
  以前は watchdog のコールバックとして `Main.stop()`(→
  `controller.shutdown()`)を直接登録していた。`controller.shutdown()`が
  何らかのロック(例: `pyaudio_op_lock`)を握ったまま永久にブロックすると、
  `Main.stop()`内の`self._stop_event.set()`に一生到達せず、かつ
  watchdogのバックグラウンドスレッド自身もこの呼び出しの中で永久に
  ブロックされる。フリーズを検知したいまさにその状況で、検知の仕組み
  自体が道連れで固まってしまい、プロセスが一切終了しなくなっていた。

  修正: `Main.escalateShutdown()`を新設し、watchdogのコールバックとして
  これを登録する。グレースフルな`self.stop()`は別スレッドで試みつつ、
  他のロックに一切触れない`threading.Timer`で独立したハードデッドライン
  (`_WATCHDOG_GRACE_PERIOD_SEC`)を仕掛け、グレースフル処理が何に
  詰まっていても、デッドラインまでには必ず`os._exit()`でプロセスを
  終了させる。また、feedが来ない限りwatchdogスレッドはコールバックを
  interval(既定20秒)ごとに呼び続けるため、二重に停止処理・タイマーを
  積み上げないよう one-shot 化した。
"""

import threading
import time
import unittest
from unittest.mock import MagicMock, patch

import mainloop as mainloop_module
from mainloop import Main


def _make_main() -> Main:
    return Main(controller_instance=MagicMock(), mapping_data={})


def _wait_until(predicate, timeout=2.0, interval=0.01) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


class WatchdogEscalationOneShotTests(unittest.TestCase):
    def test_second_call_does_not_trigger_another_graceful_stop(self) -> None:
        main = _make_main()
        stop_calls = []
        main.stop = lambda *a, **k: stop_calls.append(1)

        with patch.object(mainloop_module, "_WATCHDOG_GRACE_PERIOD_SEC", 5), \
             patch.object(mainloop_module.os, "_exit"):
            main.escalateShutdown()
            main.escalateShutdown()  # 2回目は何もしないはず (feedが来ない限り毎interval呼ばれる想定)

            self.assertTrue(_wait_until(lambda: len(stop_calls) >= 1))
            # 二重発火が無いことを確認するため少し余分に待つ。
            time.sleep(0.2)

        self.assertEqual(len(stop_calls), 1, "graceful stop は一度しか呼ばれないはず")


class WatchdogEscalationForcesExitTests(unittest.TestCase):
    def test_hard_deadline_forces_exit_when_graceful_stop_hangs(self) -> None:
        main = _make_main()
        never_returns = threading.Event()
        # controller.shutdown() がロック待ちで永久にブロックする状況を模す。
        main.stop = lambda *a, **k: never_returns.wait()

        with patch.object(mainloop_module, "_WATCHDOG_GRACE_PERIOD_SEC", 0.05), \
             patch.object(mainloop_module.os, "_exit") as mock_exit:
            main.escalateShutdown()
            self.assertTrue(_wait_until(lambda: mock_exit.called))

        mock_exit.assert_called_once_with(1)

    def test_graceful_completion_cancels_the_hard_deadline_and_exits_cleanly(self) -> None:
        main = _make_main()
        main.stop = lambda *a, **k: None  # 即座に完了する正常系

        with patch.object(mainloop_module, "_WATCHDOG_GRACE_PERIOD_SEC", 0.05), \
             patch.object(mainloop_module.os, "_exit") as mock_exit:
            main.escalateShutdown()
            self.assertTrue(_wait_until(lambda: mock_exit.called))
            # ハードデッドライン (0.05秒) を過ぎても、キャンセルできていれば
            # 追加の os._exit(1) は呼ばれないはず。
            time.sleep(0.3)

        mock_exit.assert_called_once_with(0)

    def test_stop_exceptions_do_not_prevent_process_exit(self) -> None:
        main = _make_main()

        def _raising_stop(*_a, **_k):
            raise RuntimeError("boom")

        main.stop = _raising_stop

        with patch.object(mainloop_module, "_WATCHDOG_GRACE_PERIOD_SEC", 5), \
             patch.object(mainloop_module.os, "_exit") as mock_exit, \
             patch.object(mainloop_module, "errorLogging") as mock_error_logging:
            main.escalateShutdown()
            self.assertTrue(_wait_until(lambda: mock_exit.called))

        mock_exit.assert_called_once_with(0)
        mock_error_logging.assert_called_once()


if __name__ == "__main__":
    unittest.main()
