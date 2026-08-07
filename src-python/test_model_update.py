import unittest
from unittest.mock import Mock, patch

from model import Model


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


if __name__ == "__main__":
    unittest.main()
