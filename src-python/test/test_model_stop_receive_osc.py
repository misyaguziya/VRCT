"""model.stopReceiveOSC() のテスト(バックエンドレビュー フェーズ4項目30)。

対象の欠陥: アプリ終了時(Controller.shutdown())にOSC受信サーバ
(UDP + OSCQuery HTTP + zeroconf監視)を明示的に止める経路が無く、
daemon threadとしてのプロセス終了任せになっていた。OSCQueryはzeroconfで
サービス広告を出しているため、close()無しの終了は他アプリ側に無効な
レコードを残す。

NOTE: フェーズ3項目21で一度 `stopReceiveOSC` は「呼び出し元が無い =
未使用」と判断され削除されたが、今回は実際に呼ばれる経路
(Controller.shutdown()) として再設置した別物。
"""

import unittest
from unittest.mock import MagicMock

from model import Model


class StopReceiveOscTests(unittest.TestCase):
    def setUp(self) -> None:
        # Model はプロセス全体で共有されるシングルトン。他のテストが既に
        # init() 済みかもしれないので、実属性を保存してから上書きし、
        # tearDown で必ず元に戻す。
        self.model = Model.__new__(Model)
        self._had_inited = hasattr(self.model, "_inited")
        self._original_inited = getattr(self.model, "_inited", None)
        self._had_osc_handler = hasattr(self.model, "osc_handler")
        self._original_osc_handler = getattr(self.model, "osc_handler", None)

        self.model._inited = True  # ensure_initialized() の実init発火を防ぐ
        self.model.osc_handler = MagicMock()

    def tearDown(self) -> None:
        for attr, had, original in (
            ("_inited", self._had_inited, self._original_inited),
            ("osc_handler", self._had_osc_handler, self._original_osc_handler),
        ):
            if had:
                setattr(self.model, attr, original)
            else:
                try:
                    delattr(self.model, attr)
                except AttributeError:
                    pass

    def test_delegates_to_osc_handler_server_stop(self) -> None:
        self.model.stopReceiveOSC()

        self.model.osc_handler.oscServerStop.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
