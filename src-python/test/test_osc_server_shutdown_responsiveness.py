"""OSCサーバのpoll_intervalに関するテスト(バックエンドレビュー フェーズ4項目30)。

対象の欠陥: `OSCHandler.oscServerServe()` が `serve_forever(10)` で
ポーリングしていたため、`oscServerStop()` が呼ぶ `BaseServer.shutdown()` が
最大10秒ブロックしていた(OSCのIP/ポート変更、アプリ終了時の
`Controller.shutdown()` いずれの経路でも)。`serve_forever(poll_interval)` は
内部で `selector.select(timeout=poll_interval)` を使うだけなので、間隔を
縮めてもCPU使用率はほぼ変わらない。0.5秒に短縮した。
"""

import unittest
from unittest.mock import MagicMock

from models.osc.osc import OSCHandler


class OscServerServePollIntervalTests(unittest.TestCase):
    def test_serve_forever_uses_a_short_poll_interval(self) -> None:
        handler = OSCHandler.__new__(OSCHandler)
        handler.osc_server = MagicMock()

        handler.oscServerServe()

        handler.osc_server.serve_forever.assert_called_once_with(0.5)

    def test_no_op_when_server_is_none(self) -> None:
        handler = OSCHandler.__new__(OSCHandler)
        handler.osc_server = None

        # 例外を投げずに何もしないこと。
        handler.oscServerServe()


if __name__ == "__main__":
    unittest.main()
