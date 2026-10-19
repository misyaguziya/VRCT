"""GitHub API 呼び出し / setup.exe ダウンロードの HTTP タイムアウトに
関するテスト (ロードマップ項目 9、残り部分)。

対象の欠陥:
  Model._fetchGithubReleases()/checkSoftwareUpdated()/_downloadSetup() は
  timeout を指定せずに requests_get() を呼んでいた。GitHub 側が「接続は
  するが応答しない」状態になると無期限にブロックし、これらは
  Controller.init() (checkSoftwareUpdated 経由) や updateSoftware から
  呼ばれるため、初期化やアップデート処理そのものが固まりうる。

  translation_utils.py/transcription_whisper.py の重み DL 関数は
  dc2ea952 で既にタイムアウト+リトライが入っているが、GitHub releases
  取得と setup.exe ダウンロードは対象外のまま残っていた。
"""

import unittest
from unittest.mock import MagicMock, patch

import model as model_module
from model import Model, _HTTP_TIMEOUT


class FetchGithubReleasesTimeoutTests(unittest.TestCase):
    @patch.object(model_module, "requests_get")
    def test_passes_the_shared_http_timeout(self, mock_get) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        Model._fetchGithubReleases()

        mock_get.assert_called_once()
        self.assertEqual(mock_get.call_args.kwargs.get("timeout"), _HTTP_TIMEOUT)


class CheckSoftwareUpdatedTimeoutTests(unittest.TestCase):
    def setUp(self) -> None:
        import config as config_module
        self._original_channel = config_module.config.SELECTED_RELEASE_CHANNEL
        config_module.config.SELECTED_RELEASE_CHANNEL = "stable"

    def tearDown(self) -> None:
        import config as config_module
        config_module.config.SELECTED_RELEASE_CHANNEL = self._original_channel

    @patch.object(model_module, "requests_get")
    def test_passes_the_shared_http_timeout_for_stable_channel(self, mock_get) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"name": "0.0.1"}
        mock_get.return_value = mock_response

        Model.checkSoftwareUpdated()

        mock_get.assert_called_once()
        self.assertEqual(mock_get.call_args.kwargs.get("timeout"), _HTTP_TIMEOUT)


class DownloadSetupTimeoutTests(unittest.TestCase):
    @patch("model.os_path.exists", return_value=False)
    @patch.object(model_module, "requests_get")
    def test_passes_the_shared_http_timeout(self, mock_get, _mock_exists) -> None:
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"0" * (2 * 1024 * 1024)]
        mock_get.return_value = mock_response

        with patch("builtins.open", MagicMock()):
            Model._downloadSetup()

        mock_get.assert_called_once()
        self.assertEqual(mock_get.call_args.kwargs.get("timeout"), _HTTP_TIMEOUT)
        self.assertTrue(mock_get.call_args.kwargs.get("stream"))


if __name__ == "__main__":
    unittest.main()
