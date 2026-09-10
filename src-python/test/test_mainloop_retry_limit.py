"""mainloop.Main.handler() の再キュー上限に関するテスト (ロードマップ項目 11)。

対象の欠陥:
  handler() は (a) 同一ロックが処理中のとき、(b) エンドポイントが初期化
  未完了 (423) のとき、いずれも応答を一切返さないまま無制限に再キューして
  いた。ワーカーは DEFAULT_WORKER_COUNT (3) 本しかないため、詰まった要求が
  積み重なると他の全リクエストが処理できなくなる (特に初期化ハングと重なると
  恒久的な無応答になる)。

  修正: キュー要素を (endpoint, data, attempt) の 3-tuple にし、再キュー
  のたびに attempt をインクリメント。上限に達したら 423 を応答して
  打ち切るようにした。
"""

import threading
import time
import unittest
from unittest.mock import MagicMock, patch

import mainloop as mainloop_module
from mainloop import Main


def _make_main(mapping: dict) -> Main:
    return Main(controller_instance=MagicMock(), mapping_data=mapping)


class LockBusyRetryLimitTests(unittest.TestCase):
    def test_responds_423_after_retry_limit_instead_of_requeueing_forever(self) -> None:
        endpoint = "/set/enable/transcription_send"
        main = _make_main({endpoint: {"status": True, "variable": lambda data: {"status": 200, "result": True}}})
        main._stop_event.clear()

        # 同一ロックキーを他スレッドが保持している状況を模す
        # (lock.acquire(blocking=False) が常に失敗する)。
        lock_key = main._canonical_lock_key(endpoint)
        main._endpoint_locks[lock_key].acquire()
        self.addCleanup(main._endpoint_locks[lock_key].release)

        responses = []
        with patch.object(mainloop_module, "printResponse", side_effect=lambda status, ep, result: responses.append((status, ep, result))), \
             patch.object(mainloop_module, "printLog"):
            # 上限ちょうどの attempt でキューに入れ、1 回の処理で
            # 打ち切られることを確認する (数百回の実リトライを待たない)。
            main.queue.put((endpoint, None, mainloop_module._LOCK_BUSY_MAX_RETRIES))
            t = threading.Thread(target=main.handler, daemon=True)
            t.start()

            deadline = time.time() + 2
            while not responses and time.time() < deadline:
                time.sleep(0.01)
            main._stop_event.set()
            t.join(timeout=2)

        self.assertEqual(len(responses), 1, "上限到達時に応答が1回だけ返るはず")
        status, ep, _result = responses[0]
        self.assertEqual(status, 423)
        self.assertEqual(ep, endpoint)
        self.assertTrue(main.queue.empty(), "上限超過後は再キューされてはいけない")


class EndpointLockedRetryLimitTests(unittest.TestCase):
    def test_responds_423_after_retry_limit_instead_of_requeueing_forever(self) -> None:
        endpoint = "/set/enable/transcription_send"
        # status: False = 初期化未完了でロック中のエンドポイント。
        main = _make_main({endpoint: {"status": False, "variable": lambda data: {"status": 200, "result": True}}})
        main._stop_event.clear()

        responses = []
        with patch.object(mainloop_module, "printResponse", side_effect=lambda status, ep, result: responses.append((status, ep, result))), \
             patch.object(mainloop_module, "printLog"):
            main.queue.put((endpoint, None, mainloop_module._ENDPOINT_LOCKED_MAX_RETRIES))
            t = threading.Thread(target=main.handler, daemon=True)
            t.start()

            deadline = time.time() + 2
            while not responses and time.time() < deadline:
                time.sleep(0.01)
            main._stop_event.set()
            t.join(timeout=2)

        self.assertEqual(len(responses), 1, "上限到達時に応答が1回だけ返るはず")
        status, ep, _result = responses[0]
        self.assertEqual(status, 423)
        self.assertEqual(ep, endpoint)
        self.assertTrue(main.queue.empty(), "上限超過後は再キューされてはいけない")


class FreshRequestsAndHappyPathTests(unittest.TestCase):
    def test_receiver_enqueues_fresh_requests_with_attempt_zero(self) -> None:
        main = _make_main({"/x": {"status": True, "variable": lambda data: {"status": 200, "result": None}}})
        main._stop_event.clear()

        fake_stdin_lines = iter(['{"endpoint": "/x", "data": null}\n', ""])

        def fake_readline():
            try:
                return next(fake_stdin_lines)
            except StopIteration:
                main._stop_event.set()
                return ""

        with patch.object(mainloop_module.sys.stdin, "readline", side_effect=fake_readline), \
             patch.object(mainloop_module, "printLog"):
            t = threading.Thread(target=main.receiver, daemon=True)
            t.start()
            t.join(timeout=2)

        endpoint, data, attempt = main.queue.get(timeout=1)
        self.assertEqual(endpoint, "/x")
        self.assertEqual(attempt, 0)

    def test_normal_request_still_gets_a_response(self) -> None:
        endpoint = "/x"
        main = _make_main({endpoint: {"status": True, "variable": lambda data: {"status": 200, "result": "ok"}}})
        main._stop_event.clear()

        responses = []
        with patch.object(mainloop_module, "printResponse", side_effect=lambda status, ep, result: responses.append((status, ep, result))), \
             patch.object(mainloop_module, "printLog"):
            main.queue.put((endpoint, None, 0))
            t = threading.Thread(target=main.handler, daemon=True)
            t.start()

            deadline = time.time() + 2
            while not responses and time.time() < deadline:
                time.sleep(0.01)
            main._stop_event.set()
            t.join(timeout=2)

        self.assertEqual(responses, [(200, endpoint, "ok")])


if __name__ == "__main__":
    unittest.main()
