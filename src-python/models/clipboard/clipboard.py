import sys
import time
import os
import threading
from subprocess import Popen, PIPE
from psutil import process_iter
import openvr

try:
    from utils import printLog
except ImportError:
    def printLog(data, *args, **kwargs):
        print(data, *args, **kwargs)

def checkSteamvrRunning() -> bool:
    _proc_name = "vrmonitor.exe" if os.name == "nt" else "vrmonitor"
    return _proc_name in (p.name() for p in process_iter())

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

    for i in range(countdown, 0, -1):
        print(i, end=' ', flush=True)
        time.sleep(1)

    try:
        # pyautogui.hotkey is a safe cross-platform way to send keys
        pyautogui.hotkey('ctrl', 'v')
        return True
    except Exception as e:
        printLog(f'pyautogui failed to send hotkey: {e}')
        return False


class Clipboard:
    def __init__(self):
        self.is_enabled = True
        self._vr_monitor_thread = None
        self._stop_monitoring = False
        self.app_name = None
        
        self._initialize()

    def _initialize(self):
        """Initialize clipboard by starting VR monitor thread."""
        self._stop_monitoring = False
        self._vr_monitor_thread = threading.Thread(target=self._monitor_steamvr, daemon=True)
        self._vr_monitor_thread.start()
        self.app_name = None
        printLog("Clipboard initialized. Waiting for SteamVR.")

    def _monitor_steamvr(self):
        """Monitor SteamVR startup in background thread."""
        printLog("Clipboard: VR monitor thread started.")
        while not self._stop_monitoring:
            if checkSteamvrRunning():
                printLog("Clipboard: SteamVR detected. Setting up app info.")
                self._setup_vr_app_name()
                break
            time.sleep(10)
        printLog("Clipboard: VR monitor thread ended.")

    def _setup_vr_app_name(self):
        """Setup VR application name from OpenVR."""
        try:
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
        except Exception as e:
            printLog(f"Clipboard: Error setting up VR app name: {e}")
            self.app_name = None

    def enable(self):
        """Enable clipboard functionality. Reinitialize the class."""
        printLog("Clipboard: Enabling clipboard functionality.")
        self.is_enabled = True
        self._initialize()

    def disable(self):
        """Disable clipboard functionality. Stop VR monitoring."""
        printLog("Clipboard: Disabling clipboard functionality.")
        self.is_enabled = False
        self._stop_monitoring = True
        if self._vr_monitor_thread is not None and self._vr_monitor_thread.is_alive():
            self._vr_monitor_thread.join(timeout=1)
            self._vr_monitor_thread = None

    def copy(self, message: str) -> bool:
        """Copy `message` to clipboard.

        Args:
            message: Text to copy.

        Returns:
            True if copy succeeded, False otherwise.
        """
        if not self.is_enabled:
            return False
        return copy_to_clipboard(message)

    def paste(self, window_name: str|None = None, countdown: int = 0) -> bool:
        """Focus a window identified by `window_name`, then paste via Ctrl+V.

        Args:
            window_name: Window title substring or process name to find and focus (Windows only). Required.
            countdown: Seconds to wait before sending paste key.

        Returns:
            True if paste command was sent, False otherwise.
        """
        if not self.is_enabled:
            return False

        window_name = window_name if window_name is not None else self.app_name

        # If window_name is provided, attempt to focus it (Windows only).
        # If window_name is None, skip focusing and paste into the currently focused window.
        if window_name is not None and sys.platform == 'win32':
            printLog(f"paste: attempting to focus window matching '{window_name}'")
            focused = False

            # try title substring match first
            wins = find_windows_by_title_substring(window_name)
            printLog(f"paste: found {wins} windows matching title substring '{window_name}'")
            for hwnd in wins:
                if focus_window(hwnd):
                    focused = True
                    break

            # if not found by title, try treating window_name as process name
            if not focused:
                wins = find_windows_by_process_name(window_name)
                printLog(f"paste: found {wins} windows matching process name '{window_name}'")
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
    clipboard.paste(window_name=None, countdown=3)