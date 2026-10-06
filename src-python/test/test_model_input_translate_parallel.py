"""複数ターゲット言語の翻訳を並列化したことのテスト (再評価 2026-09-14 P-5、2回目)。

1回目の並列化 (`73366d0a`) は実機でフリーズを起こして取り消した
(`afa73518`)。原因は translators ライブラリが `requests.Session` を
シングルトンで使い回しておりスレッドセーフでなかったこと。フォーク側で
`Tse.session` を `threading.local()` へ分離して解消した
(misyaguziya/translators `f3697bd`)。

**1回目のテストはここが検出できなかった**: `getTranslate` をスタブに
差し替えていたため、実物のライブラリの内部状態に一切触れていなかった。
今回は「共有インスタンスの属性がスレッドごとに分離されること」を
直接検証するケースを追加する (ネットワークは使わない)。
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

    def __call__(self, translator_name, source_language, target_language, target_country, message):
        with self._lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            time.sleep(self.delay)
            return f"<{target_language}>{message}", True
        finally:
            with self._lock:
                self.active -= 1


_COUNTRY_OF = {
    "English": "United States",
    "Korean": "South Korea",
    "Chinese Simplified": "China",
}


class _InputTranslateTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.model = object.__new__(Model)
        self.model._inited = True
        self.model._init_failed = False
        # 本番と同じ「常設プール」。使い捨てにすると translators 側の
        # スレッドローカルなセッションが毎回作り直され、ウォームアップの
        # コストを毎回払うことになる。
        from concurrent.futures import ThreadPoolExecutor
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.model._translation_executor = self.executor

        self._saved_targets = config.SELECTED_TARGET_LANGUAGES
        self._saved_tab = config.SELECTED_TAB_NO

    def tearDown(self) -> None:
        self.executor.shutdown(wait=False)
        config.SELECTED_TARGET_LANGUAGES = self._saved_targets
        config.SELECTED_TAB_NO = self._saved_tab

    def _enableTargets(self, *languages: str) -> None:
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


class TestInputTranslateRunsTargetsInParallel(_InputTranslateTestBase):
    def test_three_targets_run_concurrently(self) -> None:
        self._enableTargets("English", "Korean", "Chinese Simplified")
        spy = _TranslateSpy()
        self.model.getTranslate = spy

        started = time.perf_counter()
        translations, flags = self.model.getInputTranslate("hello", source_language="Japanese")
        elapsed = time.perf_counter() - started

        self.assertEqual(spy.max_active, 3, "3言語が同時に走っていない")
        self.assertLess(elapsed, spy.delay * 3, "逐次実行と変わらない所要時間になっている")
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

    def test_single_target_does_not_use_the_pool(self) -> None:
        """1言語のときは従来どおり直接呼ぶ (既定構成では常にこちら)。"""
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


class TestTranslatorsSessionIsThreadLocal(unittest.TestCase):
    """translators 本体の `Tse.session` がスレッドごとに分離されていること。

    1回目の並列化が実機でフリーズした原因そのものを、ネットワーク無しで
    固定する。ここが共有に戻ると、複数スレッドが同じ `requests.Session` を
    同時に使い、コネクションプールが壊れて
    `urllib3.exceptions.ProtocolError` やハングが再発する。

    requirements の pin がスレッドローカル化前のコミットへ戻された場合も
    ここで落ちる (pin と実装の不整合の検出)。
    """

    def test_session_attribute_is_isolated_per_thread(self) -> None:
        try:
            from translators.server import Tse
        except Exception as exc:  # pragma: no cover - 依存が無い環境
            self.skipTest(f"translators が import できない: {exc}")

        class _Dummy(Tse):
            def __init__(self):
                super().__init__()
                self.session = None

        shared = _Dummy()
        seen: dict = {}

        def worker(name: int) -> None:
            shared.session = f"session-{name}"
            # 他スレッドが書いた値が見えてはいけない
            seen[name] = shared.session

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        remedy = (
            "Tse.session がスレッド間で共有されている。"
            " インストール済みの translators が requirements.txt の pin より古い可能性が高い"
            " (スレッドローカル化は misyaguziya/translators f3697bd 以降)。"
            " `pip install -r requirements.txt --force-reinstall --no-deps translators` で追従すること。"
        )
        self.assertEqual(seen, {i: f"session-{i}" for i in range(5)}, remedy)
        self.assertIsNone(shared.session, remedy)


if __name__ == "__main__":
    unittest.main()
