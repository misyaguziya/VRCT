"""`Controller._initVrcMicMuteSync` のテスト (起動時のミュート状態の初期同期)。

VRChat が先に起動していれば、起動時の問い合わせで MuteSelf を読んで同期する。
VRCT が先に起動していると読めず (`None`)、ここでは同期しない。その場合は VRChat が
アバターを読み込んだときの `/avatar/change` で読み直す (test_model_osc_mute_sync.py)。

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
    def test_success_applies_the_status(self, mock_model) -> None:
        mock_model.mic_mute_status = True

        self.controller._initVrcMicMuteSync()

        mock_model.setMuteSelfStatus.assert_called_once()
        mock_model.changeMicTranscriptStatus.assert_called_once()

    @patch("controller.model")
    def test_success_with_false_status_also_applies(self, mock_model) -> None:
        # False は「ミュートされていない」という確定値であり、None (不明) とは区別する。
        mock_model.mic_mute_status = False

        self.controller._initVrcMicMuteSync()

        mock_model.changeMicTranscriptStatus.assert_called_once()

    @patch("controller.model")
    def test_unknown_status_is_left_for_the_avatar_change(self, mock_model) -> None:
        # VRChat がまだ起動していない: None のまま、文字起こしの状態は変えない。
        mock_model.mic_mute_status = None

        self.controller._initVrcMicMuteSync()

        mock_model.setMuteSelfStatus.assert_called_once()
        mock_model.changeMicTranscriptStatus.assert_not_called()


if __name__ == "__main__":
    unittest.main()
