"""AudioLifecycleWorker のmic/speaker分離・重複投入の集約・停止に関する
テスト (フェーズ3項目21)。

対象の欠陥:
  以前は mic/speaker が model.audio_lifecycle_worker という同一の
  単一スレッド・単一キューを共有しており、片方の重い処理
  (最大 TRANSCRIPT_STOP_JOIN_TIMEOUT + _MIC_OPEN_TIMEOUT_SEC 秒) の間、
  無関係なもう片方の操作まで無駄に足止めされていた
  (mic/speaker_lifecycle_lock を分けた意味が薄れる)。

  また ActiveEndpointTracker (250ms周期) からの reconfigure 要求のように
  常に「現在の状態」を読むだけの冪等な処理が、処理速度を上回るペースで
  積み上がると、既に古くなった内容を無駄に何度も実行し続けていた。

  さらに Controller.shutdown() が worker を止めていなかったため、
  シャットダウン中に古いデバイス通知やミュート同期の再送が届くと
  リソース解放と競合しうる状態だった。
"""

import threading
import time
import unittest

from model import AudioLifecycleWorker


def _wait_until(predicate, timeout=2.0, interval=0.01) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


class BasicExecutionTests(unittest.TestCase):
    def test_enqueued_functions_run_in_fifo_order(self) -> None:
        worker = AudioLifecycleWorker()
        self.addCleanup(worker.stop)
        order = []
        worker.enqueue(lambda: order.append(1))
        worker.enqueue(lambda: order.append(2))
        worker.enqueue(lambda: order.append(3))

        self.assertTrue(_wait_until(lambda: order == [1, 2, 3]))

    def test_exception_in_one_item_does_not_stop_the_worker(self) -> None:
        worker = AudioLifecycleWorker()
        self.addCleanup(worker.stop)
        order = []

        def raising():
            raise RuntimeError("boom")

        worker.enqueue(raising)
        worker.enqueue(lambda: order.append("still runs"))

        self.assertTrue(_wait_until(lambda: order == ["still runs"]))


class CoalescingTests(unittest.TestCase):
    def test_duplicate_pending_key_is_dropped_while_one_is_still_queued(self) -> None:
        """ActiveEndpointTrackerのように、実行が追いつかないペースで
        同じ (冪等な) 処理が積まれても、まだ実行開始していない重複は
        1件にまとめられること。"""
        worker = AudioLifecycleWorker()
        self.addCleanup(worker.stop)
        release = threading.Event()
        run_count = {"n": 0}

        def blocking_first_call():
            run_count["n"] += 1
            release.wait(timeout=2.0)

        # 1件目 (これが即座に実行され、releaseされるまでブロックする)
        worker.enqueue(blocking_first_call, coalesce_key="reconfigure")
        self.assertTrue(_wait_until(lambda: run_count["n"] == 1))

        # 実行中に同じkeyで3回投入しても、キューに並ぶのは高々1件のはず
        # (実行中の1件目はキューから既に外れているため対象外)。
        counter = {"n": 0}
        for _ in range(3):
            worker.enqueue(lambda: counter.__setitem__("n", counter["n"] + 1), coalesce_key="reconfigure")

        release.set()  # 1件目を完了させる

        self.assertTrue(_wait_until(lambda: counter["n"] == 1))
        time.sleep(0.1)  # 余分に実行されていないことを確認するため少し待つ
        self.assertEqual(counter["n"], 1, "重複した保留分は1件にまとめられるはず")

    def test_a_new_request_after_execution_starts_is_queued_again(self) -> None:
        """実行が始まった時点でkeyはキューから外れるため、実行中に来た
        新しい要求は次の1件として改めてキューされること (取りこぼさない)。"""
        worker = AudioLifecycleWorker()
        self.addCleanup(worker.stop)
        started = threading.Event()
        release = threading.Event()
        calls = []

        def first_call():
            calls.append("first")
            started.set()
            release.wait(timeout=2.0)

        worker.enqueue(first_call, coalesce_key="reconfigure")
        self.assertTrue(started.wait(timeout=2.0))

        # 実行開始後に来た新しい要求。
        worker.enqueue(lambda: calls.append("second"), coalesce_key="reconfigure")
        release.set()

        self.assertTrue(_wait_until(lambda: calls == ["first", "second"]))

    def test_different_keys_do_not_interfere(self) -> None:
        worker = AudioLifecycleWorker()
        self.addCleanup(worker.stop)
        order = []
        worker.enqueue(lambda: order.append("mic"), coalesce_key="mic_reconfigure")
        worker.enqueue(lambda: order.append("speaker"), coalesce_key="speaker_reconfigure")

        self.assertTrue(_wait_until(lambda: set(order) == {"mic", "speaker"}))

    def test_items_without_a_key_are_never_coalesced(self) -> None:
        worker = AudioLifecycleWorker()
        self.addCleanup(worker.stop)
        order = []
        for i in range(3):
            worker.enqueue(lambda i=i: order.append(i))

        self.assertTrue(_wait_until(lambda: order == [0, 1, 2]))


class StopTests(unittest.TestCase):
    def test_stop_ignores_further_enqueues(self) -> None:
        worker = AudioLifecycleWorker()
        calls = []
        worker.stop(timeout=2.0)

        accepted = worker.enqueue(lambda: calls.append(1))

        self.assertFalse(accepted, "stop()後のenqueue()はFalseを返すはず")
        time.sleep(0.1)
        self.assertEqual(calls, [], "stop()後のenqueueは無視されるはず")

    def test_stop_lets_the_thread_exit(self) -> None:
        worker = AudioLifecycleWorker()
        thread = worker._thread
        worker.stop(timeout=2.0)

        self.assertFalse(thread.is_alive())

    def test_stop_is_idempotent(self) -> None:
        worker = AudioLifecycleWorker()
        worker.stop(timeout=2.0)
        worker.stop(timeout=2.0)  # 2回呼んでも例外にならないこと

    def test_enqueue_returns_true_when_actually_queued(self) -> None:
        worker = AudioLifecycleWorker()
        self.addCleanup(worker.stop)

        self.assertTrue(worker.enqueue(lambda: None))


class RaceRegressionTests(unittest.TestCase):
    """コードレビュー指摘: enqueue()の`_stopped`チェックとqueue.put()が
    非アトミックだった旧実装では、stop()と競合した際に「enqueue()は
    受理したのに実は誰も処理しない」まま項目が消えるバグがあった。
    enqueue()/stop()を同じロックで保護したことで、結果は「積んで実行
    される」か「stop()済みとして拒否される」のいずれか一方に必ず
    確定するはず。多数回競合させて再発しないことを確認する。"""

    def test_concurrent_enqueue_and_stop_never_silently_drops_an_accepted_item(self) -> None:
        for _ in range(200):
            worker = AudioLifecycleWorker()
            ran = threading.Event()
            accepted: list = []

            def enqueuer() -> None:
                accepted.append(worker.enqueue(ran.set))

            t_enqueue = threading.Thread(target=enqueuer)
            t_stop = threading.Thread(target=worker.stop)
            t_enqueue.start()
            t_stop.start()
            t_enqueue.join(timeout=2.0)
            t_stop.join(timeout=2.0)

            if accepted and accepted[0]:
                self.assertTrue(
                    ran.wait(timeout=2.0),
                    "enqueue()がTrueを返した(受理した)のに実行されなかった(レース再発)",
                )


class MicSpeakerIndependenceTests(unittest.TestCase):
    def test_a_slow_item_on_one_worker_does_not_block_another_worker(self) -> None:
        """mic用workerが重い処理で詰まっていても、別インスタンスの
        speaker用workerは即座に処理できること (フェーズ3項目21の本題)。"""
        mic_worker = AudioLifecycleWorker()
        speaker_worker = AudioLifecycleWorker()
        self.addCleanup(mic_worker.stop)
        self.addCleanup(speaker_worker.stop)

        mic_worker.enqueue(lambda: time.sleep(2.0))

        speaker_done = threading.Event()
        speaker_worker.enqueue(speaker_done.set)

        self.assertTrue(speaker_done.wait(timeout=0.5), "別インスタンスのworkerは無関係な処理に足止めされないはず")


if __name__ == "__main__":
    unittest.main()
