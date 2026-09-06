"""`Controller.__init__` のデフォルト引数注入 (フェーズ3項目22) のテスト。

このクラスの残り大部分は引き続き裸のモジュールレベル `config`/`model` を
直接参照している (項目23の対象)。ここでは `self._config`/`self._model` が
正しく解決されること、および `@patch("controller.model")` のような
モジュール属性差し替えにも追従することだけを検証する。
"""

import unittest
from unittest.mock import patch

import controller as controller_module
from config import config
from controller import Controller
from model import model


class TestControllerConstructorDefaults(unittest.TestCase):
    def test_no_args_resolves_to_the_real_singletons(self) -> None:
        c = Controller()

        self.assertIs(c._config, config)
        self.assertIs(c._model, model)


class TestControllerConstructorInjection(unittest.TestCase):
    def test_explicit_model_override_is_used(self) -> None:
        fake_model = object()

        c = Controller(model_override=fake_model)

        self.assertIs(c._model, fake_model)
        self.assertIs(c._config, config)

    def test_explicit_config_override_is_used(self) -> None:
        fake_config = object()

        c = Controller(config_override=fake_config)

        self.assertIs(c._config, fake_config)
        self.assertIs(c._model, model)


class TestControllerConstructorTracksModulePatching(unittest.TestCase):
    """回帰テスト: `def __init__(self, model=model)` のように引数名を
    モジュールレベル名と揃えてデフォルト値にすると、デフォルト値は
    関数定義時 (import時) に1回だけ評価されるため、後から
    `@patch("controller.model")` しても反映されない。この形では
    そうならないことを確認する。
    """

    def test_patched_module_attribute_is_picked_up_without_explicit_override(self) -> None:
        with patch("controller.model") as mock_model:
            c = Controller()

            self.assertIs(c._model, mock_model)

        # patch 終了後は実シングルトンに戻る。
        c_after = Controller()
        self.assertIs(c_after._model, controller_module.model)


if __name__ == "__main__":
    unittest.main()
