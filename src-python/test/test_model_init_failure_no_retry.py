"""`Model.init()` が途中で失敗したときに再試行しないことのテスト。

背景 (バックエンド再評価 2026-09-14 P-2):

`Model.init()` は `self._inited = True` を最終行でのみ立てるが、その手前で
`AudioLifecycleWorker` を 2 つ生成する。このコンストラクタは即 daemon
スレッドを start する (`model.py` の `AudioLifecycleWorker.__init__`)。

したがって後半 (`Translator()` / `Overlay()` / `OverlayImage()` /
`Clipboard()` / `Telemetry()` など) で例外が出ると:

1. `_inited` は False のまま
2. `Controller._bootstrapModel()` は例外を握りつぶして続行
3. 以降すべての `ensure_initialized()` が `init()` を先頭から再実行
4. そのたびにワーカースレッドが 2 本増え、前回分は誰からも参照されない
5. `Controller.shutdown()` が止められるのは最新の 1 組だけ

`_init_failed` フラグを「成功が証明されるまで失敗扱い」で先に立てることで、
失敗した初期化を 1 回で打ち切る。
"""

import unittest
from unittest.mock import patch

import model as model_module
from model import Model


class _StubWorker:
    """AudioLifecycleWorker の代役。スレッドは起動せず生成回数だけ数える。"""

    instances: list = []

    def __init__(self) -> None:
        _StubWorker.instances.append(self)


class TestInitFailureIsNotRetried(unittest.TestCase):
    def setUp(self) -> None:
        _StubWorker.instances = []
        # シングルトン (Model.__new__) を汚さないよう、生の新規オブジェクトを作る。
        self.model = object.__new__(Model)
        self.model._inited = False
        self.model._init_failed = False

    def _runFailingInit(self) -> None:
        with patch.object(model_module, "AudioLifecycleWorker", _StubWorker), \
             patch.object(model_module, "Translator", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                self.model.init()

    def test_failure_marks_init_as_failed(self) -> None:
        self._runFailingInit()
        self.assertTrue(self.model._init_failed)
        self.assertFalse(self.model._inited)

    def test_workers_are_created_only_once_across_repeated_init_calls(self) -> None:
        self._runFailingInit()
        self.assertEqual(len(_StubWorker.instances), 2, "1回目で mic/speaker の2本が生成される")

        # 2回目以降は本体を実行せずに即 return すること。
        with patch.object(model_module, "AudioLifecycleWorker", _StubWorker):
            self.model.init()
            self.model.init()

        self.assertEqual(
            len(_StubWorker.instances), 2,
            "失敗後に init() を再実行してワーカーを増やしてはいけない",
        )

    def test_ensure_initialized_does_not_retry_after_failure(self) -> None:
        """public メソッドが呼ばれ続けてもスレッドが増えないこと。

        `ensure_initialized()` は例外を握りつぶして続行する設計なので、
        ここが再試行し続けるとリークが青天井になる。
        """
        self._runFailingInit()

        with patch.object(model_module, "AudioLifecycleWorker", _StubWorker):
            for _ in range(50):
                self.model.ensure_initialized()

        self.assertEqual(len(_StubWorker.instances), 2)


if __name__ == "__main__":
    unittest.main()
