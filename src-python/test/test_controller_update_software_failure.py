"""更新の失敗が UI へ届くこと (UI は更新中の表示のまま待っているので、
知らせないと固着する)。"""

import unittest
from unittest.mock import Mock, patch

from controller import Controller
from model import SETUP_DOWNLOAD_FAILED, SETUP_LAUNCHED, SETUP_VERIFY_FAILED

_RUN_MAPPING = {
    "update_software": "/run/update_software",
    "update_cuda_software": "/run/update_cuda_software",
}


class RunSoftwareUpdateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = Controller.__new__(Controller)
        self.controller.run_mapping = _RUN_MAPPING
        self.controller.run = Mock()

    def test_failure_is_reported_to_ui(self) -> None:
        self.controller._runSoftwareUpdate(Mock(return_value=SETUP_DOWNLOAD_FAILED), "/run/update_software", "3.5.1-beta.1")

        status, endpoint, result = self.controller.run.call_args.args
        self.assertEqual(status, 400)
        self.assertEqual(endpoint, "/run/update_software")
        self.assertEqual(result["error_code"], "UPDATE_SOFTWARE_DOWNLOAD")

    def test_verification_failure_gets_its_own_error_code(self) -> None:
        self.controller._runSoftwareUpdate(Mock(return_value=SETUP_VERIFY_FAILED), "/run/update_software", "3.5.1-beta.1")

        result = self.controller.run.call_args.args[2]
        self.assertEqual(result["error_code"], "UPDATE_SOFTWARE_VERIFY")

    def test_anything_but_launched_is_reported_as_failure(self) -> None:
        # None などを成功とみなすと、失敗のとき UI が更新中の表示のまま固着する
        self.controller._runSoftwareUpdate(Mock(return_value=None), "/run/update_software", None)

        result = self.controller.run.call_args.args[2]
        self.assertEqual(result["error_code"], "UPDATE_SOFTWARE_DOWNLOAD")

    @patch("controller.errorLogging")
    def test_exception_is_reported_to_ui(self, _error_logging: Mock) -> None:
        self.controller._runSoftwareUpdate(Mock(side_effect=RuntimeError("boom")), "/run/update_cuda_software", None)

        status, endpoint, result = self.controller.run.call_args.args
        self.assertEqual((status, endpoint), (400, "/run/update_cuda_software"))
        self.assertEqual(result["error_code"], "UPDATE_SOFTWARE_DOWNLOAD")

    def test_nothing_reported_when_installer_was_launched(self) -> None:
        # 起動に成功するとアプリが終了するので、戻ってくるのはテストのモックだけ
        self.controller._runSoftwareUpdate(Mock(return_value=SETUP_LAUNCHED), "/run/update_software", None)

        self.controller.run.assert_not_called()

    def test_endpoints_pass_their_own_run_mapping_key(self) -> None:
        with patch("controller.Thread") as thread, patch("controller.model") as model:
            self.controller.updateSoftware("3.5.0")
            self.controller.updateCudaSoftware("3.5.0")

        calls = [c.kwargs["args"] for c in thread.call_args_list]
        self.assertEqual(calls[0], (model.updateSoftware, "/run/update_software", "3.5.0"))
        self.assertEqual(calls[1], (model.updateCudaSoftware, "/run/update_cuda_software", "3.5.0"))
