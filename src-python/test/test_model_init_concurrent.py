"""別スレッドが init() の最中でも、2つ目の init() は完了を待ち、feed は待たずに通ること。

2つ目の init() が即 return すると、呼び出し側 (Controller._bootstrapModel のコールバック登録) が
overlay の無いまま走って AttributeError になり、掴んだ位置の保存と UI への通知が起動中ずっと効かなかった。
"""

import threading
import unittest
from unittest.mock import patch

import model as model_module


class _Sentinel(Exception):
    pass


class ConcurrentInitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.m = model_module.Model.__new__(model_module.Model)
        self.m._inited = False
        self.m._init_failed = False
        self.entered = threading.Event()
        self.release = threading.Event()

    def _stall_in_init(self):
        # 1つ目の init() が重い初期化の途中にいる状態
        self.entered.set()
        self.release.wait(5)
        raise _Sentinel()

    def _start_first_init(self) -> threading.Thread:
        def run():
            with self.assertRaises(_Sentinel):
                self.m.init()

        t = threading.Thread(target=run, daemon=True)
        t.start()
        self.assertTrue(self.entered.wait(5))
        return t

    def test_second_init_waits_for_the_first_to_finish(self) -> None:
        with patch.object(model_module, "MicSession", side_effect=self._stall_in_init):
            first = self._start_first_init()
            second = threading.Thread(target=self.m.init, daemon=True)
            second.start()
            second.join(0.3)
            self.assertTrue(second.is_alive(), "1つ目の初期化が終わるまで待つ")
            self.release.set()
            first.join(5)
            second.join(5)
            self.assertFalse(second.is_alive())

    def test_feed_watchdog_is_not_blocked_by_init_in_another_thread(self) -> None:
        with patch.object(model_module, "MicSession", side_effect=self._stall_in_init):
            first = self._start_first_init()
            feed = threading.Thread(target=self.m.feedWatchdog, daemon=True)
            feed.start()
            feed.join(2)
            self.assertFalse(feed.is_alive(), "初期化中でも feed は通る")
            self.release.set()
            first.join(5)


if __name__ == "__main__":
    unittest.main()
