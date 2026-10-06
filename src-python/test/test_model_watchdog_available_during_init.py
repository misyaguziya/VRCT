"""init() の途中で /run/feed_watchdog が届いても watchdog が存在すること。

フロントエンドは spawn 直後から feed_watchdog を送り、ハンドラワーカーは
init() 実行中でも処理する。watchdog の生成が init() の後半にあると、
初期化の遅い環境で AttributeError になっていた。
"""

import unittest
from unittest.mock import patch

import model as model_module


class _Sentinel(Exception):
    pass


class WatchdogAvailableDuringInitTests(unittest.TestCase):
    def test_feed_watchdog_works_while_init_is_still_running(self) -> None:
        m = model_module.Model.__new__(model_module.Model)
        m._inited = False
        m._init_failed = False
        seen = {}

        def stall_in_init():
            # init() が重い初期化 (音声セッション等) に入った時点で feed が届く状況
            seen["feed"] = m.feedWatchdog()
            raise _Sentinel()

        with patch.object(model_module, "MicSession", side_effect=stall_in_init):
            with self.assertRaises(_Sentinel):
                m.init()

        self.assertIn("feed", seen)  # AttributeError にならず通る


if __name__ == "__main__":
    unittest.main()
