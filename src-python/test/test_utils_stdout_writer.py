"""stdout専用書き込みスレッド (フェーズ3項目18) のテスト。

対象の欠陥: 以前は printLog/printResponse を呼んだスレッドが直接
sys.stdout.write() を (ロック付きで) 実行していたため、パイプが壊れる/
埋まると書き込みに関わる全スレッドが芋づる式に停止していた
(freeze_trace.log 2026-08-27、35秒フリーズで実際に確認済み)。

書き込みを専用スレッド1本に閉じ込め、呼び出し元はキューに積むだけに
することでこの連鎖を断つ。printResponse (実応答) は取りこぼさず、
printLog (診断ログ) は有界キューであふれたら古いものから捨てる。
連続して書き込みに失敗した場合は「フロントエンド消失」とみなして
コールバックを呼ぶ (既定は os._exit、テストでは差し替える)。
"""

import time
import unittest
from queue import Queue
from unittest.mock import patch

import utils


def _wait_until(predicate, timeout=2.0, interval=0.01) -> bool:
    """`predicate()` が真になるまで短い間隔でポーリングする
    (書き込みスレッドは別スレッドで非同期に動くため)。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


class _StdoutWriterTestCase(unittest.TestCase):
    """各テストの前後で書き込みスレッド・キュー・コールバックを
    まっさらな状態に戻す。グローバルなシングルトン状態を扱うため。"""

    def setUp(self) -> None:
        utils.stopStdoutWriter()
        # 直前のテストが残したスレッドが完全に停止するのを待つ。
        _wait_until(lambda: utils._stdout_writer_thread is None or not utils._stdout_writer_thread.is_alive())
        utils._stdout_response_queue = Queue()
        utils._stdout_log_queue = Queue(maxsize=utils._STDOUT_LOG_QUEUE_MAXSIZE)
        utils._stdout_writer_thread = None
        utils.setFrontendLostCallback(None)

    def tearDown(self) -> None:
        utils.stopStdoutWriter()
        utils.setFrontendLostCallback(None)


class TestEnqueuedLinesAreWrittenAsynchronously(_StdoutWriterTestCase):
    def test_log_line_is_eventually_written(self) -> None:
        written = []
        with patch.object(utils, "_writeStdoutLine", side_effect=lambda line: written.append(line) or True):
            utils._enqueueLogLine("hello-log")
            self.assertTrue(_wait_until(lambda: written == ["hello-log"]))

    def test_response_line_is_eventually_written(self) -> None:
        written = []
        with patch.object(utils, "_writeStdoutLine", side_effect=lambda line: written.append(line) or True):
            utils._enqueueResponseLine("hello-response")
            self.assertTrue(_wait_until(lambda: written == ["hello-response"]))

    def test_response_lines_take_priority_over_log_lines(self) -> None:
        written = []
        with patch.object(utils, "_writeStdoutLine", side_effect=lambda line: written.append(line) or True), \
             patch.object(utils, "_ensureStdoutWriterStarted"):
            # 書き込みスレッドをまだ起動させない状態で両方を積んでおき
            # (でないと先に積んだログを書き込みスレッドが即座に処理して
            # しまい、優先度の検証にならない)、その後まとめて起動する。
            utils._enqueueLogLine("log-1")
            utils._enqueueResponseLine("response-1")

        # ログを先に積んでも、後から積んだ応答が先に書き込まれる
        # (応答キューが優先されるため)。
        with patch.object(utils, "_writeStdoutLine", side_effect=lambda line: written.append(line) or True):
            utils._ensureStdoutWriterStarted()
            self.assertTrue(_wait_until(lambda: len(written) == 2))
        self.assertEqual(written[0], "response-1")
        self.assertEqual(written[1], "log-1")


class TestLogQueueDropsOldestWhenFull(_StdoutWriterTestCase):
    def test_overflow_drops_the_oldest_entry(self) -> None:
        # 書き込みスレッド自体は起動させず (＝キューが誰にも drain されない
        # 状態で)、キューの詰め込み動作だけを検証する。
        maxsize = utils._STDOUT_LOG_QUEUE_MAXSIZE
        with patch.object(utils, "_ensureStdoutWriterStarted"):
            for i in range(maxsize):
                utils._enqueueLogLine(f"log-{i}")
            self.assertEqual(utils._stdout_log_queue.qsize(), maxsize)

            utils._enqueueLogLine("log-overflow")

            self.assertEqual(utils._stdout_log_queue.qsize(), maxsize)
            remaining = list(utils._stdout_log_queue.queue)
            self.assertNotIn("log-0", remaining, "the oldest entry should have been dropped")
            self.assertIn("log-overflow", remaining, "the newest entry should have been kept")


class TestResponseQueueNeverDropsUnderLoad(_StdoutWriterTestCase):
    def test_many_response_lines_are_all_queued(self) -> None:
        with patch.object(utils, "_ensureStdoutWriterStarted"):
            for i in range(1000):
                utils._enqueueResponseLine(f"response-{i}")
            self.assertEqual(utils._stdout_response_queue.qsize(), 1000)


class TestConsecutiveFailuresTriggerFrontendLostCallback(_StdoutWriterTestCase):
    def test_callback_fires_after_the_configured_number_of_failures(self) -> None:
        callback_calls = []
        utils.setFrontendLostCallback(lambda: callback_calls.append(True))

        with patch.object(utils, "_writeStdoutLine", return_value=False):
            for _ in range(utils._MAX_CONSECUTIVE_STDOUT_FAILURES):
                utils._enqueueLogLine("doomed-line")
            self.assertTrue(_wait_until(lambda: len(callback_calls) == 1))

    def test_default_callback_is_os_exit(self) -> None:
        # 既定 (コールバック未登録) では os._exit(1) を呼ぶことを、実際には
        # プロセスを終了させずに確認する。
        with patch.object(utils, "_writeStdoutLine", return_value=False), \
             patch.object(utils.os, "_exit") as mock_exit:
            for _ in range(utils._MAX_CONSECUTIVE_STDOUT_FAILURES):
                utils._enqueueLogLine("doomed-line")
            self.assertTrue(_wait_until(lambda: mock_exit.called))
            mock_exit.assert_called_once_with(1)

    def test_a_successful_write_resets_the_failure_counter(self) -> None:
        callback_calls = []
        utils.setFrontendLostCallback(lambda: callback_calls.append(True))

        results = [False] * (utils._MAX_CONSECUTIVE_STDOUT_FAILURES - 1) + [True] + [False] * (
            utils._MAX_CONSECUTIVE_STDOUT_FAILURES - 1
        )
        with patch.object(utils, "_writeStdoutLine", side_effect=results):
            for _ in range(len(results)):
                utils._enqueueLogLine("line")
            # 全件が書き込みスレッドに処理されるまで待ってから判定する
            # (with ブロックを抜けてパッチが外れる前にキューを空にしておかないと、
            # 残った項目が実際の _writeStdoutLine に渡り、後続テストの
            # stdout をリアルに汚してしまう)。
            self.assertTrue(_wait_until(lambda: utils._stdout_log_queue.empty()))
            # 途中で成功が1回挟まるため、カウンタがリセットされ、
            # まだ閾値には到達しないはず。
            self.assertEqual(callback_calls, [])


class TestWriterStartupIsRaceFree(_StdoutWriterTestCase):
    def test_concurrent_start_calls_result_in_a_single_thread(self) -> None:
        import threading

        barrier = threading.Barrier(8)

        def start_it():
            barrier.wait()
            utils._ensureStdoutWriterStarted()

        threads = [threading.Thread(target=start_it) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 起動した書き込みスレッドは常にただ1本 (StdoutWriter という
        # 名前を持つ living thread が1本だけ) であることを確認する。
        stdout_writer_threads = [
            t for t in threading.enumerate() if t.name == "StdoutWriter" and t.is_alive()
        ]
        self.assertEqual(len(stdout_writer_threads), 1)


class PutDroppingOldestOnFullTests(unittest.TestCase):
    """_enqueueLogLine (項目18) から切り出した共通ヘルパー。項目20で
    audio_queue/energy_queue にも展開したため、両者から独立して
    直接検証する (レビュー指摘: 以前は同じロジックが2箇所に手書きで
    重複していた)。"""

    def test_puts_normally_when_not_full(self) -> None:
        q = Queue(maxsize=2)
        evicted = utils.putDroppingOldestOnFull(q, "a")
        self.assertFalse(evicted)
        self.assertEqual(list(q.queue), ["a"])

    def test_evicts_the_oldest_item_when_full(self) -> None:
        q = Queue(maxsize=2)
        q.put("a")
        q.put("b")
        evicted = utils.putDroppingOldestOnFull(q, "c")
        self.assertTrue(evicted)
        self.assertEqual(list(q.queue), ["b", "c"])

    def test_works_on_an_already_empty_queue_racing_another_consumer(self) -> None:
        # get_nowait() が Empty を送出するタイミング (満杯判定直後に
        # 別スレッドが先に空にした場合) でも例外を出さずに積めること。
        q = Queue(maxsize=1)
        q.put("stale")
        # 満杯にした直後、内部でget_nowaitする前に誰か(このテストの
        # シミュレーションとしてここで先に)空にしてしまうケース。
        q.get_nowait()
        evicted = utils.putDroppingOldestOnFull(q, "fresh")
        self.assertFalse(evicted)
        self.assertEqual(list(q.queue), ["fresh"])


if __name__ == "__main__":
    unittest.main()
