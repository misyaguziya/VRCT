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

    @patch("models.clipboard.clipboard.paste_via_pyautogui")
    @patch("models.clipboard.clipboard.copy_to_clipboard")
    @patch("models.clipboard.clipboard.find_windows_by_process_name", return_value=[])
    @patch("models.clipboard.clipboard.find_windows_by_title_substring", return_value=[])
    def test_copies_even_when_no_window_can_be_focused(
        self,
        find_by_title: MagicMock,
        find_by_process: MagicMock,
        copy_to_clipboard: MagicMock,
        paste_via_pyautogui: MagicMock,
    ) -> None:
        copy_to_clipboard.return_value = True
        instance = self._make_clipboard()

        result = instance.copy_and_paste("hello world", window_name="VRChat")

        copy_to_clipboard.assert_called_once_with("hello world")
        paste_via_pyautogui.assert_not_called()
        self.assertFalse(result)

    @patch("models.clipboard.clipboard.paste_via_pyautogui")
    @patch("models.clipboard.clipboard.copy_to_clipboard")
    @patch("models.clipboard.clipboard.focus_window")
    @patch("models.clipboard.clipboard.find_windows_by_title_substring")
    def test_copies_and_pastes_when_focus_succeeds(
        self,
        find_by_title: MagicMock,
        focus_window: MagicMock,
        copy_to_clipboard: MagicMock,
        paste_via_pyautogui: MagicMock,
    ) -> None:
        find_by_title.return_value = [123]
        focus_window.return_value = True
        copy_to_clipboard.return_value = True
        paste_via_pyautogui.return_value = True
        instance = self._make_clipboard()

        result = instance.copy_and_paste("hello world", window_name="VRChat")

        copy_to_clipboard.assert_called_once_with("hello world")
        paste_via_pyautogui.assert_called_once()
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
