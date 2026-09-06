"""`Model.watchForVrchatOscQueryConnection` が `osc_handler` へ正しく
委譲することのテスト。
"""

import unittest
from unittest.mock import MagicMock

from model import Model


class TestWatchForVrchatOscQueryConnection(unittest.TestCase):
    def test_delegates_to_osc_handler(self) -> None:
        model = Model.__new__(Model)
        model._inited = True  # ensure_initialized() が実処理を走らせないようにする
        model.osc_handler = MagicMock()
        on_found = MagicMock()

        model.watchForVrchatOscQueryConnection(on_found)

        model.osc_handler.waitForVrchatOscQueryConnectionAsync.assert_called_once_with(on_found)


if __name__ == "__main__":
    unittest.main()
