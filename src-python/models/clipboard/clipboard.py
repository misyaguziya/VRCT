import sys
import time
import os
import threading
from subprocess import Popen, PIPE
from psutil import process_iter
import openvr

try:
    from models import openvr_session
except ImportError:
    import openvr_session

try:
    from utils import printLog
except ImportError:
    def printLog(data, *args, **kwargs):
        print(data, *args, **kwargs)

# Optional deps; None fallback lets clipboard/window helpers no-op when the
# package is unavailable.
try:
    import psutil  # noqa: F401
except Exception:
    psutil = None  # type: ignore

try:
    import pyperclip  # noqa: F401
except Exception:
    pyperclip = None  # type: ignore

try:
    import tkinter as tk  # noqa: F401
except Exception:
    tk = None  # type: ignore

try:
    import pyautogui  # noqa: F401
except Exception:
    pyautogui = None  # type: ignore

def checkSteamvrRunning() -> bool:
    _proc_name = "vrmonitor.exe" if os.name == "nt" else "vrmonitor"
    return _proc_name in (p.name() for p in process_iter())

# Windows-specific imports via ctypes will be used when focusing windows
if sys.platform == 'win32':
    import ctypes
    import ctypes.wintypes as wintypes
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

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
            if psutil is None:
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
            SW_RESTORE = 9
            user32.ShowWindow(hwnd, SW_RESTORE)

            # Windows のフォーカス奪取防止機構により、直前までフォア
            # グラウンドでなかった別プロセス (VRCT) からの素の
            # SetForegroundWindow はしばしば OS に無視され、タスクバーの
            # 点滅だけで終わる。AttachThreadInput で自スレッドの入力状態を
            # 現在のフォアグラウンドウィンドウのスレッドに一時的に結び付ける
            # と、両者が「入力状態を共有するスレッド」とみなされ、この
            # 制限を正規の方法で回避できる (よく知られた Win32 の作法)。
            current_thread_id = kernel32.GetCurrentThreadId()
            fore_hwnd = user32.GetForegroundWindow()
            fore_thread_id = user32.GetWindowThreadProcessId(fore_hwnd, None) if fore_hwnd else 0

            attached = False
            if fore_thread_id and fore_thread_id != current_thread_id:
                attached = bool(user32.AttachThreadInput(current_thread_id, fore_thread_id, True))

            try:
                user32.BringWindowToTop(hwnd)
                res = user32.SetForegroundWindow(hwnd)
            finally:
                if attached:
                    user32.AttachThreadInput(current_thread_id, fore_thread_id, False)

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
    if pyperclip is None:
        return False
    try:
        pyperclip.copy(text)
        return True
    except Exception:
        return False

def copy_to_clipboard_tk(text: str) -> bool:
    if tk is None:
        return False
    try:
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
    if pyautogui is None:
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
        """Setup VR application name from OpenVR.

        Goes through the shared, reference-counted openvr_session instead
        of calling openvr.init()/openvr.shutdown() directly: Overlay uses
        the same OpenVR session, and openvr.shutdown() tears down the
        whole process's VR connection, not just this caller's. Releasing
        in a finally block avoids leaking a reference (which would keep
        the shared session permanently "held" and stop shutdown() from
        ever running) if anything below the acquire fails.
        """
        try:
            openvr_session.acquire(openvr.VRApplication_Background)
        except Exception as e:
            printLog(f"Clipboard: Error setting up VR app name: {e}")
            self.app_name = None
            return

        try:
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
        except Exception as e:
            printLog(f"Clipboard: Error setting up VR app name: {e}")
            self.app_name = None
        finally:
            openvr_session.release()

    def copy_and_paste(self, message: str, window_name: str|None = None, countdown: int = 0) -> bool:
        window_name = window_name if window_name is not None else self.app_name

        # If window_name is available, attempt to focus it (Windows only).
        # Focusing another process's window is an OS-level privilege VRCT
        # is not always granted (see focus_window()); when it fails we
        # still want the text on the clipboard for a manual paste, so
        # copying below is unconditional -- only the automatic paste
        # (which requires the right window to actually be focused, or it
        # would type into whatever else happens to have focus) is gated
        # on focus having actually succeeded.
        focused = False
        if window_name is not None and sys.platform == 'win32':
            printLog(f"paste: attempting to focus window matching '{window_name}'")

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
                printLog(f"copy_and_paste: could not focus a window matching '{window_name}'; copying only")
            else:
                # small delay to allow focus to settle
                time.sleep(0.2)

        copied = copy_to_clipboard(message)
        if not copied:
            printLog("copy_and_paste: failed to copy to clipboard")
            return False

        if not focused:
            return False

        pasted = paste_via_pyautogui(countdown)
        return bool(pasted)

if __name__ == '__main__':
    clipboard = Clipboard()
    clipboard.copy_and_paste("Sample text to copy to clipboard.", window_name=None, countdown=3)