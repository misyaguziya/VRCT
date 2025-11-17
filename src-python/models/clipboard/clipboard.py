import sys
import time
from subprocess import Popen, PIPE
import openvr

try:
    from utils import printLog
except ImportError:
    def printLog(data, *args, **kwargs):
        print(data, *args, **kwargs)

# Windows-specific imports via ctypes will be used when focusing windows
if sys.platform == 'win32':
    import ctypes
    import ctypes.wintypes as wintypes
    user32 = ctypes.WinDLL('user32', use_last_error=True)

    def find_windows_by_title_substring(substring: str):
        HWND = wintypes.HWND
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, HWND, wintypes.LPARAM)
        found = []

        def _cb(hwnd, lParam):
            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return True
            buf = ctypes.create_unicode_buffer(length + 1)
            # fill buffer with window title
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value
            if substring.lower() in title.lower():
                found.append(hwnd)
            return True

        user32.EnumWindows(callback_type(_cb), 0)
        return found

    def find_windows_by_process_name(proc_name: str):
        # iterate windows and match process id to name
        HWND = wintypes.HWND
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, HWND, wintypes.LPARAM)
        found = []

        def _cb(hwnd, lParam):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            try:
                import psutil
            except Exception:
                return True
            try:
                p = psutil.Process(pid.value)
                if p.name().lower() == proc_name.lower():
                    found.append(hwnd)
            except Exception:
                pass
            return True

        user32.EnumWindows(callback_type(_cb), 0)
        return found

    def focus_window(hwnd) -> bool:
        try:
            # Restore and set foreground
            SW_RESTORE = 9
            user32.ShowWindow(hwnd, SW_RESTORE)
            res = user32.SetForegroundWindow(hwnd)
            return bool(res)
        except Exception:
            return False

def copy_to_clipboard_windows(text: str) -> bool:
    try:
        p = Popen(['clip'], stdin=PIPE, shell=False)
        # Write as UTF-16LE with BOM so Windows clipboard receives correct Unicode
        bom_utf16le = b"\xff\xfe"
        p.communicate(bom_utf16le + text.encode('utf-16le'))
        return True
    except Exception:
        return False

def copy_to_clipboard_pyperclip(text: str) -> bool:
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        return False

def copy_to_clipboard_tk(text: str) -> bool:
    try:
        import tkinter as tk
        r = tk.Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(text)
        r.update()
        r.destroy()
        return True
    except Exception:
        return False

def copy_to_clipboard(text: str) -> bool:
    if sys.platform == 'win32':
        if copy_to_clipboard_windows(text):
            return True
    if copy_to_clipboard_pyperclip(text):
        return True
    if copy_to_clipboard_tk(text):
        return True
    return False

def paste_via_pyautogui(countdown: int = 0) -> bool:
    try:
        import pyautogui
    except Exception:
        printLog('pyautogui not installed. Install with: pip install pyautogui')
        return False

    printLog(f'Give focus to the target input. Pasting in {countdown} seconds...')
    for i in range(countdown, 0, -1):
        print(i, end=' ', flush=True)
        time.sleep(1)
    printLog('\nSending Ctrl+V...')
    try:
        # pyautogui.hotkey is a safe cross-platform way to send keys
        pyautogui.hotkey('ctrl', 'v')
        return True
    except Exception as e:
        printLog(f'pyautogui failed to send hotkey: {e}')
        return False


class Clipboard:
    def __init__(self, vr_mode: bool = True):
        if not vr_mode:
            self.app_name = None
        else:
            openvr.init(openvr.VRApplication_Background)
            apps = openvr.VRApplications()

            app_count = apps.getApplicationCount()
            running_apps = []

            for i in range(app_count):
                key = apps.getApplicationKeyByIndex(i)
                name = apps.getApplicationPropertyString(
                    key,
                    openvr.VRApplicationProperty_Name_String
                )
                running_apps.append((key, name))

            self.app_name = None
            for key, name in running_apps:
                if key.startswith("steam.app"):
                    self.app_name = name
                    break
            openvr.shutdown()

    def copy(self, message: str) -> bool:
        """Copy `message` to clipboard.

        Args:
            message: Text to copy.

        Returns:
            True if copy succeeded, False otherwise.
        """
        return copy_to_clipboard(message)

    def paste(self, window_name: str|None = None, countdown: int = 0) -> bool:
        """Focus a window identified by `window_name`, then paste via Ctrl+V.

        Args:
            window_name: Window title substring or process name to find and focus (Windows only). Required.
            countdown: Seconds to wait before sending paste key.

        Returns:
            True if paste command was sent, False otherwise.
        """

        if window_name is None:
            window_name = self.app_name

        # focus target window (Windows only) — window_name is required
        focused = False
        if sys.platform == 'win32':
            if not window_name:
                printLog('paste: window_name is required on Windows')
                return False

            # try title substring match first
            wins = find_windows_by_title_substring(window_name)
            for hwnd in wins:
                if focus_window(hwnd):
                    focused = True
                    break

            # if not found by title, try treating window_name as process name
            if not focused:
                wins = find_windows_by_process_name(window_name)
                for hwnd in wins:
                    if focus_window(hwnd):
                        focused = True
                        break

            if not focused:
                printLog(f"copy_and_paste: no window found matching '{window_name}'")
                return False

            # small delay to allow focus to settle
            time.sleep(0.2)

        # paste
        pasted = paste_via_pyautogui(countdown)
        return bool(pasted)

if __name__ == '__main__':
    clipboard = Clipboard()
    clipboard.copy("Sample text to copy to clipboard.")
    clipboard.paste(window_name=None, countdown=0)