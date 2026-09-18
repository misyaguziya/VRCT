"""changeToCTranslate2Process() の回帰テスト (P0-3 の副作用チェック)。

ValidatedProperty.__get__ を生参照から deepcopy に修正した際、コードベース内で
唯一 `config.SELECTED_TRANSLATION_ENGINES[tab] = "CTranslate2"` という
再代入なしの直接添字代入に依存していた箇所が動かなくなることが分かった
(controller.py:changeToCTranslate2Process)。以前はこの行が ValidatedProperty の
生参照バグを利用して (バリデータを一切通さずに) 内部状態を直接書き換えており、
deepcopy 化するとその場限りのコピーを変更するだけになり効果が消える。

read → 変更 → 再代入する正しいパターンに直したので、その配線が壊れていない
ことを確認する。
"""

import unittest

from controller import Controller, config


class ChangeToCTranslate2ProcessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        self.controller.run_mapping = {
            "selected_translation_engines": "selected_translation_engines",
            "translation_engines": "translation_engines",
        }
        self.calls = []
        self.controller.run = lambda status, endpoint, result: self.calls.append((status, endpoint, result))
        self.controller.getTranslationEngines = lambda: {"result": {"dummy": "engines"}}

        self.TAB_NO = "1"
        self._original_engines = config.SELECTED_TRANSLATION_ENGINES
        self._original_status = dict(config.SELECTABLE_TRANSLATION_ENGINE_STATUS)
        config.SELECTED_TRANSLATION_ENGINES = {self.TAB_NO: "OpenAI_API"}

    def tearDown(self) -> None:
        config.SELECTED_TRANSLATION_ENGINES = self._original_engines
        for key, value in self._original_status.items():
            config.SELECTABLE_TRANSLATION_ENGINE_STATUS[key] = value

    def test_switches_the_selected_tab_to_ctranslate2(self):
        self.controller.changeToCTranslate2Process()

        # 内部状態が実際に "CTranslate2" へ切り替わっていること
        # (以前はここが no-op になり、元のエンジンが選択されたまま残っていた)。
        self.assertEqual(config.SELECTED_TRANSLATION_ENGINES[self.TAB_NO], "CTranslate2")

    def test_other_tabs_are_left_untouched(self):
        config.SELECTED_TRANSLATION_ENGINES = {self.TAB_NO: "OpenAI_API", "2": "Google"}
        self.controller.changeToCTranslate2Process()
        self.assertEqual(config.SELECTED_TRANSLATION_ENGINES[self.TAB_NO], "CTranslate2")
        self.assertEqual(config.SELECTED_TRANSLATION_ENGINES["2"], "Google")

    def test_disables_the_previously_selected_engine(self):
        self.controller.changeToCTranslate2Process()
        self.assertFalse(config.SELECTABLE_TRANSLATION_ENGINE_STATUS["OpenAI_API"])

    def test_pushes_the_updated_engines_to_the_ui(self):
        self.controller.changeToCTranslate2Process()
        pushed = {endpoint: result for _status, endpoint, result in self.calls}
        self.assertEqual(pushed["selected_translation_engines"][self.TAB_NO], "CTranslate2")


if __name__ == "__main__":
    unittest.main()
