"""VRパネル用: Tauriの "VRCT VR Panel" ウィンドウを撮影し、マウス入力を送る (Windows専用)。

ウィンドウは画面外に置かれ、隠れていても PrintWindow(PW_RENDERFULLCONTENT) で撮影できる
(最小化中は不可)。入力はOSのカーソルを動かさないよう PostMessage で送る。
描画側のChromiumが隠れたウィンドウの描画を止めないよう、Tauri側で起動引数を指定している
(src-tauri/src/lib.rs の BROWSER_ARGS)。
"""
import ctypes
from ctypes import wintypes
from typing import Optional

import numpy as np

VR_PANEL_TITLE = "VRCT VR Panel"

_PW_RENDERFULLCONTENT = 2
_WM_MOUSEMOVE = 0x0200
_WM_LBUTTONDOWN = 0x0201
_WM_LBUTTONUP = 0x0202
_WM_MOUSEWHEEL = 0x020A
_MK_LBUTTON = 0x0001
_SWP_NOMOVE = 0x0002
_SWP_NOZORDER = 0x0004
_SWP_NOACTIVATE = 0x0010
# 相手 (VRCT の画面) の応答を待たずに戻る。画面が固まっていると、待つ間オーバーレイの処理が止まる
_SWP_ASYNCWINDOWPOS = 0x4000

_user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None
_gdi32 = ctypes.windll.gdi32 if hasattr(ctypes, "windll") else None


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD),
    ]


def findWindow(title: str = VR_PANEL_TITLE) -> Optional[int]:
    hwnd = _user32.FindWindowW(None, title)
    return hwnd or None


def isWindow(hwnd: int) -> bool:
    return bool(_user32.IsWindow(hwnd))


def captureWindowRaw(hwnd: int) -> Optional[tuple]:
    """撮影した生データ (BGRX のバイト列, (幅, 高さ), クライアント領域の切り出し範囲) を返す。

    PrintWindow は相手の画面が描き終えるまで戻らない (画面が固まると数秒)。オーバーレイは別スレッドで呼ぶ。

    画像への変換は重い (数ms) ので、前回と同じか (バイト列の比較) を先に確かめられるようにしている。
    最小化中などで撮れなければ None。
    """
    if _user32.IsIconic(hwnd):
        return None
    rect = wintypes.RECT()
    _user32.GetWindowRect(hwnd, ctypes.byref(rect))
    width, height = rect.right - rect.left, rect.bottom - rect.top
    if width <= 0 or height <= 0:
        return None
    hdc = _user32.GetWindowDC(hwnd)
    mdc = _gdi32.CreateCompatibleDC(hdc)
    bmp = _gdi32.CreateCompatibleBitmap(hdc, width, height)
    try:
        _gdi32.SelectObject(mdc, bmp)
        if not _user32.PrintWindow(hwnd, mdc, _PW_RENDERFULLCONTENT):
            return None
        info = _BITMAPINFOHEADER(ctypes.sizeof(_BITMAPINFOHEADER), width, -height, 1, 32, 0, 0, 0, 0, 0, 0)
        buf = ctypes.create_string_buffer(width * height * 4)
        _gdi32.GetDIBits(mdc, bmp, 0, height, buf, ctypes.byref(info), 0)
    finally:
        _gdi32.DeleteObject(bmp)
        _gdi32.DeleteDC(mdc)
        _user32.ReleaseDC(hwnd, hdc)
    # ウィンドウ枠 (装飾なしでも数px残る) を除き、入力座標と一致するクライアント領域だけにする
    client = wintypes.RECT()
    _user32.GetClientRect(hwnd, ctypes.byref(client))
    origin = wintypes.POINT(0, 0)
    _user32.ClientToScreen(hwnd, ctypes.byref(origin))
    left, top = origin.x - rect.left, origin.y - rect.top
    return buf.raw, (width, height), (left, top, left + client.right, top + client.bottom)


def resizeClient(hwnd: int, width: int, height: int) -> tuple:
    """クライアント領域が論理px (width x height) になるよう、ウィンドウの大きさを変える (位置は変えない)。

    戻り値: 目標のクライアント領域の大きさ (物理px)。撮影がこの大きさになれば変わり終えている。
    """
    scale = (_user32.GetDpiForWindow(hwnd) or 96) / 96
    rect, client = wintypes.RECT(), wintypes.RECT()
    _user32.GetWindowRect(hwnd, ctypes.byref(rect))
    _user32.GetClientRect(hwnd, ctypes.byref(client))
    target_w, target_h = round(width * scale), round(height * scale)
    if (client.right, client.bottom) == (target_w, target_h):
        return (target_w, target_h)
    frame_w = (rect.right - rect.left) - client.right
    frame_h = (rect.bottom - rect.top) - client.bottom
    _user32.SetWindowPos(hwnd, 0, 0, 0, target_w + frame_w, target_h + frame_h, _SWP_NOMOVE | _SWP_NOZORDER | _SWP_NOACTIVATE | _SWP_ASYNCWINDOWPOS)
    return (target_w, target_h)


def bgraFromCapture(capture: tuple) -> np.ndarray:
    """captureWindowRaw の結果から、クライアント領域の画素 (高さ, 幅, BGRA) を切り出す (書き換えてよい複製)。

    色の並べ替えはせず、OpenGL へは BGRA のまま渡す (PIL で RGBA に変換すると1枚30〜40msかかっていた)。
    アルファは不定なので、呼び出し側で決める。
    """
    raw, (width, height), (x0, y0, x1, y1) = capture
    return np.frombuffer(raw, np.uint8).reshape(height, width, 4)[y0:y1, x0:x1].copy()


def _lparam(x: int, y: int) -> int:
    return ((y & 0xFFFF) << 16) | (x & 0xFFFF)


_ENUM_PROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


_target_cache: dict = {}


def _target(hwnd: int) -> int:
    """WebView2では、子孫の描画用ウィンドウ (Chrome_RenderWidgetHostHWND) が入力を受け取る。"""
    cached = _target_cache.get(hwnd)
    if cached is not None and _user32.IsWindow(cached):
        return cached
    found = []

    def callback(child, _):
        name = ctypes.create_unicode_buffer(64)
        _user32.GetClassNameW(child, name, 64)
        if name.value == "Chrome_RenderWidgetHostHWND":
            found.append(child)
            return False
        return True

    _user32.EnumChildWindows(hwnd, _ENUM_PROC(callback), 0)
    if not found:
        return hwnd
    _target_cache[hwnd] = found[0]
    return found[0]


def mouseMove(hwnd: int, x: int, y: int, pressed: bool = False) -> None:
    _user32.PostMessageW(_target(hwnd), _WM_MOUSEMOVE, _MK_LBUTTON if pressed else 0, _lparam(x, y))


def mouseDown(hwnd: int, x: int, y: int) -> None:
    _user32.PostMessageW(_target(hwnd), _WM_LBUTTONDOWN, _MK_LBUTTON, _lparam(x, y))


def mouseUp(hwnd: int, x: int, y: int) -> None:
    _user32.PostMessageW(_target(hwnd), _WM_LBUTTONUP, 0, _lparam(x, y))


def mouseWheel(hwnd: int, x: int, y: int, delta: int) -> None:
    # WM_MOUSEWHEEL の座標はスクリーン座標
    target = _target(hwnd)
    point = wintypes.POINT(x, y)
    _user32.ClientToScreen(target, ctypes.byref(point))
    _user32.PostMessageW(target, _WM_MOUSEWHEEL, (delta & 0xFFFF) << 16, _lparam(point.x, point.y))
