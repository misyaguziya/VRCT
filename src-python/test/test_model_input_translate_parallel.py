"""複数ターゲット言語の翻訳を並列化したことのテスト (再評価 2026-09-14 P-5)。

実機ログ (M-1 の計装) で、3言語有効時の translate が約3.9秒
(1言語あたり約1.3秒 × 3) かかっていることを確認した。逐次ループだった
ためで、翻訳はクラウドエンジンならネットワークI/O待ちが支配的なので
並列化すれば概ね1言語分の時間で済む。

添字はターゲット言語スロットに対応するため、**順序の保持**が必須。
また例外は呼び出し元 (`Controller._processMessage`) が VRAM 不足エラーを
検出する契約になっているため、**そのまま送出**しなければならない。
"""

import threading
import time
import unittest

from model import Model, config


class _TranslateSpy:
    """getTranslate の代役。呼び出しの同時実行数を記録する。"""

    def __init__(self, delay: float = 0.15) -> None:
        self.delay = delay
        self.active = 0
        self.max_active = 0
        self._lock = threading.Lock()
        self.calls: list = []

    def __call__(self, translator_name, source_language, target_language, target_country, message):
        with self._lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            self.calls.append(target_language)
        try:
            time.sleep(self.delay)
            return f"<{target_language}>{message}", True
        finally:
            with self._lock:
                self.active -= 1


class _InputTranslateTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.model = object.__new__(Model)
        self.model._inited = True
        self.model._init_failed = False

        self._saved_targets = config.SELECTED_TARGET_LANGUAGES
        self._saved_tab = config.SELECTED_TAB_NO

    def tearDown(self) -> None:
        config.SELECTED_TARGET_LANGUAGES = self._saved_targets
        config.SELECTED_TAB_NO = self._saved_tab

    def _enableTargets(self, *languages: str) -> None:
        """"1".."3" のうち先頭 len(languages) 個を有効化する。"""
        targets = config.SELECTED_TARGET_LANGUAGES
        tab = config.SELECTED_TAB_NO
        for i, no in enumerate(("1", "2", "3")):
            if i < len(languages):
                targets[tab][no]["language"] = languages[i]
                targets[tab][no]["country"] = _COUNTRY_OF[languages[i]]
                targets[tab][no]["enable"] = True
            else:
                targets[tab][no]["enable"] = False
        config.SELECTED_TARGET_LANGUAGES = targets


_COUNTRY_OF = {
    "English": "United States",
    "Korean": "South Korea",
    "Chinese Simplified": "China",
}


class TestInputTranslateRunsTargetsInParallel(_InputTranslateTestBase):
    def test_three_targets_run_concurrently(self) -> None:
        self._enableTargets("English", "Korean", "Chinese Simplified")
        spy = _TranslateSpy()
        self.model.getTranslate = spy

        started = time.perf_counter()
        translations, flags = self.model.getInputTranslate("hello", source_language="Japanese")
        elapsed = time.perf_counter() - started

        self.assertEqual(spy.max_active, 3, "3言語が同時に走っていない")
        self.assertLess(
            elapsed, spy.delay * 3,
            "逐次実行と変わらない所要時間になっている",
        )
        self.assertEqual(len(translations), 3)
        self.assertEqual(flags, [True, True, True])

    def test_results_keep_target_slot_order(self) -> None:
        """添字はターゲット言語スロットに対応するので順序が崩れてはいけない。"""
        self._enableTargets("English", "Korean", "Chinese Simplified")

        def slow_first(translator_name, source_language, target_language, target_country, message):
            # 1番目をいちばん遅くする。完了順に詰めていると順序が壊れる。
            time.sleep(0.2 if target_language == "English" else 0.01)
            return f"<{target_language}>", True

        self.model.getTranslate = slow_first

        translations, _ = self.model.getInputTranslate("hello", source_language="Japanese")

        self.assertEqual(translations, ["<English>", "<Korean>", "<Chinese Simplified>"])

    def test_single_target_does_not_spawn_threads(self) -> None:
        """1言語のときは従来どおり直接呼ぶ (スレッド生成の無駄を避ける)。"""
        self._enableTargets("English")
        spy = _TranslateSpy(delay=0.0)
        self.model.getTranslate = spy

        translations, flags = self.model.getInputTranslate("hello", source_language="Japanese")

        self.assertEqual(spy.max_active, 1)
        self.assertEqual(len(translations), 1)
        self.assertEqual(flags, [True])

    def test_exception_is_propagated_to_the_caller(self) -> None:
        """_processMessage が VRAM 不足エラーを検出する契約を壊さないこと。"""
        self._enableTargets("English", "Korean")

        def boom(*_args, **_kwargs):
            raise RuntimeError("CUDA out of memory")

        self.model.getTranslate = boom

        with self.assertRaises(RuntimeError):
            self.model.getInputTranslate("hello", source_language="Japanese")

    def test_no_enabled_target_returns_empty(self) -> None:
        self._enableTargets()
        self.model.getTranslate = _TranslateSpy(delay=0.0)

        self.assertEqual(self.model.getInputTranslate("hello", source_language="Japanese"), ([], []))


if __name__ == "__main__":
    unittest.main()
