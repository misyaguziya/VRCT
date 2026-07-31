import unittest
from unittest.mock import Mock, patch

from model import Model


class TestModelUpdate(unittest.TestCase):
    @patch("model.errorLogging")
    @patch("model.requests_get")
    def test_does_not_run_updater_when_asset_is_missing(
        self,
        requests_get: Mock,
        error_logging: Mock,
    ) -> None:
        requests_get.return_value.json.return_value = {"assets": []}

        with patch("model.Popen") as popen:
            Model.updateSoftware()
            Model.updateCudaSoftware()

        popen.assert_not_called()
        self.assertEqual(requests_get.call_count, 10)
        self.assertEqual(error_logging.call_count, 10)


if __name__ == "__main__":
    unittest.main()