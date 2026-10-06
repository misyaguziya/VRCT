"""プロセスが動いているかの確認 (psutil.process_iter より桁違いに速い Toolhelp)。"""
import os
import time
import unittest
from unittest.mock import MagicMock, patch

from models.process_check import isProcessRunning


class ProcessCheckTest(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows only")
    def test_finds_this_process_and_misses_an_unknown_one(self):
        self.assertTrue(isProcessRunning(os.path.basename(__import__("sys").executable)))
        self.assertTrue(isProcessRunning(os.path.basename(__import__("sys").executable).upper()))  # 大文字小文字は区別しない
        self.assertFalse(isProcessRunning("definitely-not-running-vrct.exe"))

    @unittest.skipUnless(os.name == "nt", "Windows only")
    def test_is_fast(self):
        started = time.perf_counter()
        for _ in range(5):
            isProcessRunning("vrmonitor.exe")
        self.assertLess((time.perf_counter() - started) / 5, 0.5)  # process_iter は約2秒かかっていた

    def test_failure_means_not_running(self):
        with patch("models.process_check._isRunningWindows", side_effect=OSError("snapshot")), patch("models.process_check.os.name", "nt"):
            self.assertFalse(isProcessRunning("vrmonitor.exe"))

    def test_other_platforms_use_psutil_names(self):
        gone = MagicMock(info={"name": None})
        steamvr = MagicMock(info={"name": "vrmonitor"})
        with patch("models.process_check.os.name", "posix"), patch("psutil.process_iter", return_value=[gone, steamvr]):
            self.assertTrue(isProcessRunning("vrmonitor"))


if __name__ == "__main__":
    unittest.main()
