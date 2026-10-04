"""プロセスが動いているかの確認 (SteamVR の vrmonitor など)。

psutil.process_iter(["name"]) は、このPC (プロセス約460個) で1回2秒近くかかり、VR UI が動いている間に
OCR・クリップボードが数秒おきに呼ぶと、CPU を使い続けて VR UI のオーバーレイの処理まで遅らせた。
Windows の Toolhelp のスナップショットなら約15ms で済む (約130倍速い)。
"""
import ctypes
import os
from ctypes import wintypes

_TH32CS_SNAPPROCESS = 2
_INVALID_HANDLE = ctypes.c_void_p(-1).value


class _ProcessEntry(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG), ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


def _isRunningWindows(name: str) -> bool:
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.Process32FirstW.argtypes = kernel32.Process32NextW.argtypes = [ctypes.c_void_p, ctypes.POINTER(_ProcessEntry)]
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    snapshot = kernel32.CreateToolhelp32Snapshot(_TH32CS_SNAPPROCESS, 0)
    if snapshot in (None, _INVALID_HANDLE):
        raise OSError("CreateToolhelp32Snapshot failed")
    try:
        entry = _ProcessEntry()
        entry.dwSize = ctypes.sizeof(_ProcessEntry)
        wanted = name.lower()
        found = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while found:
            if entry.szExeFile.lower() == wanted:
                return True
            found = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
        return False
    finally:
        kernel32.CloseHandle(snapshot)


def isProcessRunning(name: str) -> bool:
    """name (例: "vrmonitor.exe") のプロセスが動いているか。確かめられなければ False。"""
    try:
        if os.name == "nt":
            return _isRunningWindows(name)
        from psutil import process_iter

        # 名前はまとめて取る (1つずつ p.name() で取ると、途中で終わったプロセスで NoSuchProcess になる)
        return any(p.info["name"] == name for p in process_iter(["name"]))
    except Exception:
        return False
