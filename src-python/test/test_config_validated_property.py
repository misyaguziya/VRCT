"""ValidatedProperty の生参照バグに関するテスト (P0-3 の回帰防止)。

`.venv` に pytest が入っていなくても
`python -m unittest test_config_validated_property` で動くよう unittest で書いている。

対象の欠陥:
  ValidatedProperty.__get__ が内部ストレージの生参照をそのまま返していたため、
  コードベース全体で使われる次のイディオムが config の内部状態を
  __set__ (=バリデータ) が走る前に直接書き換えてしまっていた。

      d = config.X       # 生参照
      d[k] = bad_value    # ← この時点で既に config._X が書き換わっている
      config.X = d        # バリデータへ渡す

  多くのバリデータは「不正な値は inst.X (=old_value) にフォールバックする」
  設計だが、__get__ が生参照を返すために old_value と val が同一オブジェクトに
  なり、フォールバック先が「新しい不正値」自身になっていた。

  実際の本番コードでは実プロダクションの config.py の
  _selected_translation_engines_validator を対象に検証する。
"""

import unittest

import config as config_module
from config import ValidatedProperty, _selected_translation_engines_validator, _mic_word_filter_validator


class _DummyConfig:
    """Config クラスをフルに起動 (ファイル I/O・デバイス列挙・ネットワーク疎通) せずに
    ValidatedProperty ディスクリプタと実際の本番バリデータだけを検証するための
    最小スタブ。"""

    SELECTABLE_TRANSLATION_ENGINE_LIST = ["Google", "Bing", "DeepL"]
    SELECTED_TRANSLATION_ENGINES = ValidatedProperty(
        "SELECTED_TRANSLATION_ENGINES", _selected_translation_engines_validator
    )
    MIC_WORD_FILTER = ValidatedProperty("MIC_WORD_FILTER", _mic_word_filter_validator)

    def saveConfig(self, name, value, immediate_save=False):
        # ディスクへの書き込みはテスト対象外なので no-op。
        pass


class ValidatedPropertyGetReturnsCopyTests(unittest.TestCase):
    def setUp(self):
        self.inst = _DummyConfig()
        # __set__ を経由すると初回はバリデータが inst.SELECTED_TRANSLATION_ENGINES
        # を読もうとして未初期化の private storage に触れるため、初期状態は
        # private attribute へ直接シードする (Config.init_config が実際に行う
        # のと同じやり方)。
        self.inst._SELECTED_TRANSLATION_ENGINES = {"tab1": "Google"}
        self.inst._MIC_WORD_FILTER = ["ng_word"]

    def test_get_returns_a_copy_not_the_internal_object(self):
        got = self.inst.SELECTED_TRANSLATION_ENGINES
        got["tab1"] = "Mutated"
        # 取得したオブジェクトを書き換えても内部状態は変わらない。
        self.assertEqual(self.inst.SELECTED_TRANSLATION_ENGINES, {"tab1": "Google"})

    def test_get_returns_a_copy_for_lists_too(self):
        got = self.inst.MIC_WORD_FILTER
        got.append("mutated")
        self.assertEqual(self.inst.MIC_WORD_FILTER, ["ng_word"])

    def test_read_modify_write_idiom_no_longer_corrupts_internal_state_before_set(self):
        # コードベース全体で使われる `d = config.X; d[k] = v; config.X = d`
        # イディオムを再現する。
        engines = self.inst.SELECTED_TRANSLATION_ENGINES
        engines["tab1"] = "NotARealEngine"  # 不正な値
        # __set__ が呼ばれる前の時点で、内部状態がまだ汚染されていないことを確認。
        self.assertEqual(self.inst._SELECTED_TRANSLATION_ENGINES, {"tab1": "Google"})


class ValidatorFallbackTests(unittest.TestCase):
    """実際のバリデータ (_selected_translation_engines_validator) が
    「不正値は旧値にフォールバックする」設計どおりに機能することを確認する。"""

    def setUp(self):
        self.inst = _DummyConfig()
        self.inst._SELECTED_TRANSLATION_ENGINES = {"tab1": "Google", "tab2": "Bing"}

    def test_invalid_entry_falls_back_to_the_true_previous_value(self):
        # コードベース全体で使われる read-modify-write イディオムをそのまま再現する。
        engines = self.inst.SELECTED_TRANSLATION_ENGINES
        engines["tab1"] = "NotARealEngine"  # 不正な値
        self.inst.SELECTED_TRANSLATION_ENGINES = engines

        # 修正前はここで {"tab1": "NotARealEngine", ...} になっていた
        # (old_value が val と同一オブジェクトになり、フォールバック先が
        #  「新しい不正値」自身になっていたため)。
        self.assertEqual(self.inst.SELECTED_TRANSLATION_ENGINES["tab1"], "Google")
        self.assertEqual(self.inst.SELECTED_TRANSLATION_ENGINES["tab2"], "Bing")

    def test_valid_entry_is_accepted(self):
        engines = self.inst.SELECTED_TRANSLATION_ENGINES
        engines["tab1"] = "DeepL"
        self.inst.SELECTED_TRANSLATION_ENGINES = engines
        self.assertEqual(self.inst.SELECTED_TRANSLATION_ENGINES["tab1"], "DeepL")


class ValidatedPropertySetStoresCopyTests(unittest.TestCase):
    """__set__ 側も、渡された/バリデータが返したオブジェクトをそのまま
    格納せず deepcopy することを確認する (呼び出し元がその後そのオブジェクトを
    書き換えても内部状態が汚染されないようにするため)。"""

    def setUp(self):
        self.inst = _DummyConfig()
        self.inst._SELECTED_TRANSLATION_ENGINES = {"tab1": "Google"}

    def test_mutating_the_object_passed_to_set_does_not_affect_stored_state(self):
        payload = {"tab1": "Bing"}
        self.inst.SELECTED_TRANSLATION_ENGINES = payload
        payload["tab1"] = "Evil"  # 呼び出し元がまだ参照を持っている場合を想定
        self.assertEqual(self.inst.SELECTED_TRANSLATION_ENGINES["tab1"], "Bing")


class RealConfigDescriptorWiringTests(unittest.TestCase):
    """本番の config.py 上で ValidatedProperty が実際にこの deepcopy 版に
    差し替わっていることを確認する (退行防止のための配線チェック)。"""

    def test_auth_keys_descriptor_get_is_the_deepcopy_version(self):
        descriptor = config_module.Config.__dict__["AUTH_KEYS"]
        self.assertIsInstance(descriptor, ValidatedProperty)
        # 型チェックだけでは不十分 (差し替え忘れでも同じ型になる) なので、
        # __get__ の実装がリストコピーを行うことを直接確認する。
        stored = {"OpenRouter_API": "sk-or-x"}

        class _Holder:
            pass

        holder = _Holder()
        holder._AUTH_KEYS = stored
        returned = ValidatedProperty.__get__(descriptor, holder, _Holder)
        self.assertIsNot(returned, stored)
        self.assertEqual(returned, stored)


if __name__ == "__main__":
    unittest.main()
