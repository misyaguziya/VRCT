"""`_SIMPLE_CONFIG_GETTERS` によるgetterの動的生成 (フェーズ3項目23) のテスト。

対象: `config.X` をそのまま返すだけの単純なgetterエンドポイント94個。
以前はcontroller.pyに個別の`def`として並んでいたが、1個のジェネレータ+
テーブルへ集約した。生成したメソッドは通常の`def`と同じ名前で`Controller`
クラスへ登録するため、`mainloop.py`のルーティングや既存テストからの
直接呼び出しへの影響が無いことも合わせて検証する。
"""

import unittest

from config import config
from controller import Controller, _SIMPLE_CONFIG_GETTERS


class TestSimpleConfigGettersAreRegisteredOnController(unittest.TestCase):
    def test_every_table_entry_is_a_callable_attribute_on_controller(self) -> None:
        for method_name in _SIMPLE_CONFIG_GETTERS:
            self.assertTrue(
                hasattr(Controller, method_name),
                f"Controller.{method_name} was not registered",
            )
            self.assertTrue(callable(getattr(Controller, method_name)))

    def test_every_generated_getter_returns_the_live_config_value(self) -> None:
        controller = Controller.__new__(Controller)
        for method_name, attr_name in _SIMPLE_CONFIG_GETTERS.items():
            response = getattr(controller, method_name)()
            self.assertEqual(response["status"], 200)
            self.assertEqual(response["result"], getattr(config, attr_name))

    def test_generated_getter_preserves_a_debuggable_name(self) -> None:
        self.assertEqual(Controller.getUiLanguage.__name__, "getUiLanguage")
        self.assertEqual(Controller.getUiLanguage.__qualname__, "Controller.getUiLanguage")

    def test_generated_getter_reflects_config_changes_live(self) -> None:
        controller = Controller.__new__(Controller)
        original = config.FONT_FAMILY
        try:
            config.FONT_FAMILY = "Comic Sans MS"
            self.assertEqual(controller.getFontFamily(), {"status": 200, "result": "Comic Sans MS"})
        finally:
            config.FONT_FAMILY = original

    def test_generated_getter_ignores_call_arguments_like_the_original_did(self) -> None:
        # mainloop._call_handler は get系ハンドラにも位置引数でdataを渡すため、
        # 元の "def getX(*args, **kwargs)" と同じく引数を無視できる必要がある。
        controller = Controller.__new__(Controller)
        response = controller.getUiLanguage({"receive_data": None})
        self.assertEqual(response["status"], 200)
        self.assertEqual(response["result"], config.UI_LANGUAGE)


if __name__ == "__main__":
    unittest.main()
