"""CTranslate2 の重みが未ロードのとき、翻訳フォールバックが待たないことのテスト。

背景 (バックエンド再評価 2026-09-14 P-3):

`Model.getTranslate()` は選択エンジンが失敗 (False) したとき、CTranslate2 へ
フォールバックして 0.1 秒間隔で最大 20 回リトライする。しかし
`Translator.translateCTranslate2()` は重みが未ロードなら即 False を返すだけ
なので、この 20 回は 1 回も意味のある処理をせずに **2 秒を sleep で捨てる**。

さらに `getInputTranslate()` はターゲット言語ごとに `getTranslate()` を呼ぶ
ため、3 言語有効なら最悪 6 秒。その間、音声パイプラインは単一スレッド構造の
ため文字起こしまで止まる。

重みがロード済みのときのリトライは「一時的な失敗を待つ」という本来の意図が
成立するので残す。
"""

import unittest
from unittest.mock import patch

from model import Model


def _makeTranslator(is_loaded: bool, calls: dict):
    """常に False を返す (= 障害中の) CTranslate2 スタブ。"""

    def fake_translate(**kwargs):
        calls[kwargs["translator_name"]] = calls.get(kwargs["translator_name"], 0) + 1
        return False

    return type("T", (), {
        "translate": staticmethod(fake_translate),
        "isLoadedCTranslate2Model": staticmethod(lambda: is_loaded),
    })()


class TestTranslateFallbackDoesNotSpinWhenWeightsMissing(unittest.TestCase):
    def setUp(self) -> None:
        # object.__new__ でシングルトンを迂回する (既存テストと同じ作法)。
        self.model = object.__new__(Model)
        self.model._inited = True
        self.model.translation_history = []
        self.model.translation_history_max_items = 20

    def _getTranslate(self):
        return self.model.getTranslate(
            translator_name="Bing",
            source_language="English",
            target_language="Japanese",
            target_country="Japan",
            message="hello",
        )

    def test_unloaded_weights_stop_the_retry_loop_immediately(self) -> None:
        calls: dict = {}
        self.model.translator = _makeTranslator(is_loaded=False, calls=calls)

        with patch("model.errorLogging"), patch("model.sleep") as mock_sleep:
            translation, success_flag = self._getTranslate()

        self.assertEqual(calls.get("CTranslate2"), 1, "未ロードなら1回で見切ること")
        mock_sleep.assert_not_called()
        # 挙動そのものは従来どおり: 原文にフォールバックし実障害として報告する。
        self.assertEqual(translation, "hello")
        self.assertFalse(success_flag)

    def test_loaded_weights_still_retry(self) -> None:
        """ロード済みなら従来どおり待つこと (一時障害のためのリトライは残す)。"""
        calls: dict = {}
        self.model.translator = _makeTranslator(is_loaded=True, calls=calls)

        with patch("model.errorLogging"), patch("model.sleep") as mock_sleep:
            self._getTranslate()

        self.assertEqual(calls.get("CTranslate2"), 20)
        self.assertEqual(mock_sleep.call_count, 20)


if __name__ == "__main__":
    unittest.main()
