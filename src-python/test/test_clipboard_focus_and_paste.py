import unittest
from unittest.mock import MagicMock, patch

from models.clipboard import clipboard


class FocusWindowUsesAttachThreadInputTests(unittest.TestCase):
    """Windows refuses SetForegroundWindow() from a process that was not
    already foreground unless the calling thread's input state is
    AttachThreadInput()-ed to the current foreground window's thread
    first. Regression coverage for that workaround actually being wired
    up (it cannot exercise the real OS-level refusal in a unit test, but
    it does prove the attach/detach sequence around SetForegroundWindow
    is present).
    """

    @patch("models.clipboard.clipboard.user32")
    @patch("models.clipboard.clipboard.kernel32")
    def test_attaches_to_the_foreground_threads_input_before_stealing_focus(
        self, kernel32: MagicMock, user32: MagicMock,
    ) -> None:
        current_thread_id = 111
        fore_hwnd = 999
        fore_thread_id = 222
        target_hwnd = 123

        kernel32.GetCurrentThreadId.return_value = current_thread_id
        user32.GetForegroundWindow.return_value = fore_hwnd
        user32.GetWindowThreadProcessId.return_value = fore_thread_id
        user32.AttachThreadInput.return_value = 1
        user32.SetForegroundWindow.return_value = 1

        result = clipboard.focus_window(target_hwnd)

        self.assertTrue(result)
        user32.AttachThreadInput.assert_any_call(current_thread_id, fore_thread_id, True)
        user32.AttachThreadInput.assert_any_call(current_thread_id, fore_thread_id, False)
        user32.SetForegroundWindow.assert_called_once_with(target_hwnd)
        # detach must happen after the SetForegroundWindow attempt, not before
        attach_call_index = [c[0] for c in user32.AttachThreadInput.call_args_list].index(
            (current_thread_id, fore_thread_id, True)
        )
        detach_call_index = [c[0] for c in user32.AttachThreadInput.call_args_list].index(
            (current_thread_id, fore_thread_id, False)
        )
        self.assertLess(attach_call_index, detach_call_index)

    @patch("models.clipboard.clipboard.user32")
    @patch("models.clipboard.clipboard.kernel32")
    def test_skips_attach_when_target_thread_is_already_the_foreground_thread(
        self, kernel32: MagicMock, user32: MagicMock,
    ) -> None:
        # If VRCT's own thread already owns the foreground window, there is
        # nothing to attach to -- attaching a thread to itself is a no-op
        # Windows itself rejects, so this must be skipped rather than
        # attempted.
        current_thread_id = 111
        kernel32.GetCurrentThreadId.return_value = current_thread_id
        user32.GetForegroundWindow.return_value = 999
        user32.GetWindowThreadProcessId.return_value = current_thread_id
        user32.SetForegroundWindow.return_value = 1

        result = clipboard.focus_window(123)

        self.assertTrue(result)
        user32.AttachThreadInput.assert_not_called()

    @patch("models.clipboard.clipboard.user32")
    @patch("models.clipboard.clipboard.kernel32")
    def test_detaches_even_if_set_foreground_window_raises(
        self, kernel32: MagicMock, user32: MagicMock,
    ) -> None:
        current_thread_id = 111
        fore_thread_id = 222
        kernel32.GetCurrentThreadId.return_value = current_thread_id
        user32.GetForegroundWindow.return_value = 999
        user32.GetWindowThreadProcessId.return_value = fore_thread_id
        user32.AttachThreadInput.return_value = 1
        user32.SetForegroundWindow.side_effect = OSError("boom")

        result = clipboard.focus_window(123)

        self.assertFalse(result)
        user32.AttachThreadInput.assert_any_call(current_thread_id, fore_thread_id, False)


class CopyAndPasteAlwaysCopiesTests(unittest.TestCase):
    """Regression coverage: copy_and_paste() must put the text on the
    clipboard even when the target window could not be focused (e.g. the
    OS refused the focus steal), so a manual paste is still possible
    instead of the whole call being a silent no-op. Auto-paste (sending
    Ctrl+V) must stay gated on focus actually having succeeded, since
    sending it blind would type into whatever window happens to have
    focus instead.
    """

    def _make_clipboard(self) -> clipboard.Clipboard:
        instance = clipboard.Clipboard.__new__(clipboard.Clipboard)
        instance.app_name = None
        return instance

    @patch("models.clipboard.clipboard.paste_via_ctrl_v")
    @patch("models.clipboard.clipboard.copy_to_clipboard")
    @patch("models.clipboard.clipboard.find_windows_by_process_name", return_value=[])
    @patch("models.clipboard.clipboard.find_windows_by_title_substring", return_value=[])
    def test_copies_even_when_no_window_can_be_focused(
        self,
        find_by_title: MagicMock,
        find_by_process: MagicMock,
        copy_to_clipboard: MagicMock,
        paste_via_ctrl_v: MagicMock,
    ) -> None:
        copy_to_clipboard.return_value = True
        instance = self._make_clipboard()

        result = instance.copy_and_paste("hello world", window_name="VRChat")

        copy_to_clipboard.assert_called_once_with("hello world")
        paste_via_ctrl_v.assert_not_called()
        self.assertFalse(result)

    @patch("models.clipboard.clipboard.paste_via_ctrl_v")
    @patch("models.clipboard.clipboard.copy_to_clipboard")
    @patch("models.clipboard.clipboard.focus_window")
    @patch("models.clipboard.clipboard.find_windows_by_title_substring")
    def test_copies_and_pastes_when_focus_succeeds(
        self,
        find_by_title: MagicMock,
        focus_window: MagicMock,
        copy_to_clipboard: MagicMock,
        paste_via_ctrl_v: MagicMock,
    ) -> None:
        find_by_title.return_value = [123]
        focus_window.return_value = True
        copy_to_clipboard.return_value = True
        paste_via_ctrl_v.return_value = True
        instance = self._make_clipboard()

        result = instance.copy_and_paste("hello world", window_name="VRChat")

        copy_to_clipboard.assert_called_once_with("hello world")
        paste_via_ctrl_v.assert_called_once()
        self.assertTrue(result)

class PasteViaCtrlVTests(unittest.TestCase):
    """PyAutoGUI (GPLv3+ の MouseInfo を引き込む) を ctypes 直呼びに
    置き換えた際の回帰テスト。PyAutoGUI が内部で呼んでいたのと同じ
    user32.keybd_event を、同じ順序で叩いていることを見る。"""

    VK_CONTROL = 0x11
    VK_V = 0x56
    KEYEVENTF_KEYUP = 0x0002

    @patch("models.clipboard.clipboard.sys.platform", "win32")
    @patch("models.clipboard.clipboard.user32")
    def test_sends_ctrl_v_and_releases_both_keys(self, user32: MagicMock) -> None:
        self.assertTrue(clipboard.paste_via_ctrl_v())

        self.assertEqual(
            user32.keybd_event.call_args_list,
            [
                unittest.mock.call(self.VK_CONTROL, 0, 0, 0),
                unittest.mock.call(self.VK_V, 0, 0, 0),
                unittest.mock.call(self.VK_V, 0, self.KEYEVENTF_KEYUP, 0),
                unittest.mock.call(self.VK_CONTROL, 0, self.KEYEVENTF_KEYUP, 0),
            ],
        )

    @patch("models.clipboard.clipboard.sys.platform", "win32")
    @patch("models.clipboard.clipboard.user32")
    def test_ctrl_is_released_even_if_sending_v_fails(self, user32: MagicMock) -> None:
        """Ctrl を押しっぱなしのまま抜けると、以後ユーザーの操作が全て
        Ctrl 付きになり VRChat の操作不能を招く。"""
        def _fail_on_v(vk, *_args):
            if vk == self.VK_V:
                raise OSError("boom")

        user32.keybd_event.side_effect = _fail_on_v

        self.assertFalse(clipboard.paste_via_ctrl_v())
        self.assertIn(
            unittest.mock.call(self.VK_CONTROL, 0, self.KEYEVENTF_KEYUP, 0),
            user32.keybd_event.call_args_list,
        )


if __name__ == "__main__":
    unittest.main()
