"""重い計算のスレッドを低い優先度にする。"""
import ctypes
import os
import threading
import unittest
from unittest.mock import patch

from models import background_priority
from models.background_priority import BackgroundThreads, lowerCurrentThread


@unittest.skipUnless(os.name == "nt", "Windows only")
class BackgroundPriorityTest(unittest.TestCase):
    def _priority(self):
        kernel32 = ctypes.windll.kernel32
        kernel32.GetCurrentThread.restype = ctypes.c_void_p
        kernel32.GetThreadPriority.argtypes = [ctypes.c_void_p]
        return kernel32.GetThreadPriority(kernel32.GetCurrentThread())

    def test_current_thread_gets_a_lower_priority(self):
        result = {}

        def run():
            lowerCurrentThread()
            result["priority"] = self._priority()

        thread = threading.Thread(target=run)
        thread.start()
        thread.join()
        self.assertEqual(result["priority"], -1)

    def test_only_new_native_threads_are_lowered(self):
        """作った後に増えたネイティブのスレッドだけを下げる。Python の Thread と元からあるスレッドは下げない。"""
        scope_before = {1, 2}
        with patch.object(background_priority, "_nativeThreadIds", return_value=scope_before):
            scope = BackgroundThreads()
        python_id = threading.get_native_id()
        with patch.object(background_priority, "_nativeThreadIds", return_value={1, 2, 3, 4, python_id}), \
                patch.object(background_priority, "_setPriority", return_value=True) as set_priority:
            self.assertEqual(scope.lower(), 2)
            self.assertEqual(scope.lower(), 0)  # 2回目は何もしない
        self.assertEqual({c.args[0] for c in set_priority.call_args_list}, {3, 4})
        self.assertTrue(all(c.args[1] == -1 for c in set_priority.call_args_list))


if __name__ == "__main__":
    unittest.main()
