"""`Controller._initVrcMicMuteSync` / `_retryMuteSelfStatusOnceVrchatFound`
のテスト (起動順序に依存するミュート同期の不具合修正)。

対象の欠陥: VRCTがVRChatより先に起動すると、起動時1回きりの
`model.setMuteSelfStatus()` (OSCQueryへの問い合わせ) が失敗し、
`model.mic_mute_status` が `None` のまま二度と更新されず、ミュート同期が
永久に機能しなかった。`_initVrcMicMuteSync()` は、この一発勝負が失敗した
場合に `model.watchForVrchatOscQueryConnection()` で再試行の仕込みをする。

model (SDK呼び出し境界) はモックし、こちら側の責務である「初回問い合わせが
成功/失敗した場合の分岐」だけを検証する。
"""

import unittest
from unittest.mock import patch

from controller import Controller


class TestInitVrcMicMuteSync(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)

    @patch("controller.model")
    def test_success_applies_the_status_without_watching(self, mock_model) -> None:
        mock_model.mic_mute_status = True

        self.controller._initVrcMicMuteSync()

        mock_model.setMuteSelfStatus.assert_called_once()
        mock_model.changeMicTranscriptStatus.assert_called_once()
        mock_model.watchForVrchatOscQueryConnection.assert_not_called()

    @patch("controller.model")
    def test_success_with_false_status_also_applies_without_watching(self, mock_model) -> None:
        # False は「ミュートされていない」という確定値であり、None (不明) とは区別する。
        mock_model.mic_mute_status = False

        self.controller._initVrcMicMuteSync()

        mock_model.changeMicTranscriptStatus.assert_called_once()
        mock_model.watchForVrchatOscQueryConnection.assert_not_called()

    @patch("controller.model")
    def test_failure_registers_a_watch_instead_of_giving_up(self, mock_model) -> None:
        # VRChatがまだ起動していない: 問い合わせは成功も失敗もせず None のまま。
        mock_model.mic_mute_status = None

        self.controller._initVrcMicMuteSync()

        mock_model.setMuteSelfStatus.assert_called_once()
        mock_model.changeMicTranscriptStatus.assert_not_called()
        mock_model.watchForVrchatOscQueryConnection.assert_called_once_with(
            self.controller._retryMuteSelfStatusOnceVrchatFound
        )


class TestRetryMuteSelfStatusOnceVrchatFound(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)

    @patch("controller.model")
    def test_retries_the_query_and_applies_the_status(self, mock_model) -> None:
        self.controller._retryMuteSelfStatusOnceVrchatFound()

        mock_model.setMuteSelfStatus.assert_called_once()
        mock_model.changeMicTranscriptStatus.assert_called_once()

    @patch("controller.errorLogging")
    @patch("controller.model")
    def test_exception_is_logged_instead_of_propagating(self, mock_model, mock_error_logging) -> None:
        mock_model.setMuteSelfStatus.side_effect = RuntimeError("boom")

        self.controller._retryMuteSelfStatusOnceVrchatFound()  # should not raise

        mock_error_logging.assert_called_once()


if __name__ == "__main__":
    unittest.main()
