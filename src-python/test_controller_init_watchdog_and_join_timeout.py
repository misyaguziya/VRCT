"""Controller.init() の startWatchdog() 前倒しと、重み DL スレッドの
join() タイムアウトに関するテスト (ロードマップ項目 9、残り部分)。

対象の欠陥:
  以前は startWatchdog() が init() の最終行にあり、ネットワーク判定や
  モデル重みのダウンロード等 (何らかの理由で無期限にハングしうる処理) が
  init() の前半〜中盤に集中していた。ハングが起きると watchdog 自体が
  まだ起動しておらず、自動復旧が一切効かなかった。

  フロントエンドは Python プロセスを spawn した直後から 20s 間隔で
  /run/feed_watchdog を送り続けており (StartPythonController.jsx)、この
  エンドポイントは初期化中でも処理可能 (mainloop.py の "status": True) で
  init() 自体はメインスレッドで同期実行されるため、init() の先頭で
  watchdog を起動しても安全 (ハンドラワーカーがフィードを処理できる)。

  また th_download_ctranslate2/th_download_whisper の join() は無制限で、
  ダウンロードスレッドが (HTTP タイムアウト+リトライの理論上の worst case
  を超えて) 本当にハングした場合、init() を無期限にブロックしていた。
"""

import unittest
from threading import Thread
from unittest.mock import MagicMock, patch

from controller import Controller


class _Sentinel(Exception):
    """init() の実行をここまで進んだことを示すための目印。"""


class StartWatchdogRunsFirstTests(unittest.TestCase):
    def test_start_watchdog_runs_before_the_network_check(self) -> None:
        controller = Controller.__new__(Controller)
        calls = []
        controller.startWatchdog = lambda *a, **k: calls.append("startWatchdog")

        def fake_is_connected():
            calls.append("isConnectedNetwork")
            raise _Sentinel()

        with patch("controller.isConnectedNetwork", side_effect=fake_is_connected), \
             patch("controller.removeLog"):
            with self.assertRaises(_Sentinel):
                controller.init()

        self.assertEqual(calls, ["startWatchdog", "isConnectedNetwork"])


class _StubDownloadThread:
    """weight download 用 Thread の代わり。is_alive()/join() の呼ばれ方を記録する。"""

    def __init__(self, target=None, args=(), **_kwargs):
        self.target = target
        self.args = args
        self.daemon = False
        self.join_calls = []
        self._alive = False

    def start(self):
        self._alive = False  # このスタブでは実行完了済み扱いにする

    def join(self, timeout=None):
        self.join_calls.append(timeout)

    def is_alive(self):
        return self._alive


class WeightDownloadJoinTimeoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        self.controller.startWatchdog = lambda *a, **k: None
        self.controller.connectedNetwork = lambda: None
        self.controller.disconnectedNetwork = lambda: None
        self.controller.initializationProgress = lambda *a, **k: None
        self.controller.downloadCtranslate2Weight = lambda *a, **k: None
        self.controller.downloadWhisperWeight = lambda *a, **k: None

    def test_join_is_called_with_a_bounded_timeout(self) -> None:
        created_threads = []

        class _TrackingThread(_StubDownloadThread):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                created_threads.append(self)

        def fake_check_ctranslate2(weight_type):
            return False  # 未ダウンロード → スレッドが作られる

        def fake_check_whisper(weight_type):
            return False

        with patch("controller.isConnectedNetwork", return_value=True), \
             patch("controller.removeLog"), \
             patch("controller.Thread", _TrackingThread), \
             patch("controller.model") as mock_model:
            mock_model.backwardCompatibleTranslatorCTranslate2ModelRenameWeightsDir = lambda: None
            mock_model.checkTranslatorCTranslate2ModelWeight.side_effect = fake_check_ctranslate2
            mock_model.checkTranscriptionWhisperModelWeight.side_effect = fake_check_whisper
            # ダウンロードスレッドの join() 直後、後続の
            # ThreadPoolExecutor 検証フェーズに入る前で打ち切る。
            mock_model.checkTranslatorCTranslate2ModelWeight.side_effect = fake_check_ctranslate2

            with patch("controller.ThreadPoolExecutor", side_effect=_Sentinel):
                with self.assertRaises(_Sentinel):
                    self.controller.init()

        self.assertEqual(len(created_threads), 2, "ctranslate2/whisper 用に2本のスレッドが作られるはず")
        for th in created_threads:
            self.assertEqual(len(th.join_calls), 1)
            timeout = th.join_calls[0]
            self.assertIsNotNone(timeout, "join() が無制限 (timeout=None) のまま呼ばれている")
            self.assertGreater(timeout, 0)


if __name__ == "__main__":
    unittest.main()
