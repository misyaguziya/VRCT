import unittest
from unittest.mock import Mock, patch

from model import Model
from config import config


class TestModelUpdate(unittest.TestCase):
    @patch("model.errorLogging")
    @patch("model.requests_get")
    def test_does_not_run_setup_when_download_keeps_failing(
        self,
        requests_get: Mock,
        error_logging: Mock,
    ) -> None:
        requests_get.side_effect = Exception("network error")

        with patch("model.Popen") as popen:
            Model.updateSoftware()
            Model.updateCudaSoftware()

        popen.assert_not_called()
        self.assertEqual(requests_get.call_count, 10)
        self.assertEqual(error_logging.call_count, 10)

    @patch("model.os_exit")
    @patch("model.psutil_Process")
    @patch("model.Popen")
    @patch("model.requests_get")
    def test_quits_app_after_launching_setup(
        self,
        requests_get: Mock,
        popen: Mock,
        psutil_process: Mock,
        os_exit: Mock,
    ) -> None:
        # _downloadSetup() rejects downloads under 1MB as a likely non-installer
        # payload (e.g. an HTML error page), so the mocked download must clear
        # that threshold for the happy path this test exercises.
        requests_get.return_value.iter_content.return_value = [b"data" * 300_000]

        Model.updateCudaSoftware()

        popen.assert_called_once_with(
            ["VRCT_setup.exe", "/EDITION=gpu"], cwd=config.PATH_LOCAL
        )
        psutil_process.return_value.terminate.assert_called_once()
        os_exit.assert_called_once_with(0)


if __name__ == "__main__":
    unittest.main()
