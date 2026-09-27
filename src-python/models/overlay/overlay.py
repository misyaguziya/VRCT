import os
from functools import lru_cache
import ctypes
import time
from psutil import process_iter
from threading import Thread
from typing import Any, Callable, Dict, Optional, Sequence

import openvr
import numpy as np
from PIL import Image, ImageDraw
try:
    from models import openvr_session
except ImportError:
    import openvr_session
try:
    from utils import errorLogging, printLog
except ImportError:
    def errorLogging():
        import traceback
        print(traceback.format_exc())
    def printLog(log, data=None):
        print(log, data)

# updateImage()の再初期化待ちループ / shutdownOverlay()のスレッドjoinの
# 上限(バックエンドレビュー フェーズ4項目31)。Pythonのスレッドは外部から
# 強制終了できないため、これらのタイムアウトは「詰まったスレッドを殺す」
# ものではなく、「呼び出し元(mainloopワーカースレッド等)を無期限に
# ブロックしないよう待つのを諦める」ためのもの。
_REINIT_WAIT_TIMEOUT_SEC = 5.0
_REINIT_WAIT_POLL_INTERVAL_SEC = 0.1
_SHUTDOWN_JOIN_TIMEOUT_SEC = 5.0

# オーバーレイを指したままグリップを押した瞬間に掴む。グリップはVRChatにも
# 同時に届く(オーバーレイ側で入力を奪えない)ことは既知の制約。
_GRIP_MASK = 1 << openvr.k_EButton_Grip
_POINTER_WIDTH_M = 0.0075
# 掴んだ瞬間にポインタをこの倍率まで大きくして、掴んだことを伝える
_GRAB_POP_SCALE = 1.8
_GRAB_POP_SEC = 0.12
# VRCTの primary カラー (src-ui の --primary_300_color / --primary_100_color)
# 掴んだままトリガーを引いて手を前後に動かすと拡大縮小する (XSOverlayと同様)。
# 前に押し出すと拡大、手前に引くと縮小。この距離動かすと2倍 (1/2倍) になる
_SCALE_DOUBLING_M = 0.15
_SCALE_ICON_THRESHOLD_M = 0.01
_WIDTH_MIN_M = 0.05
_WIDTH_MAX_M = 3.0
# 透明な部分にはポインタを出さない。この半径 (px) 内に描画があれば当たりとみなす
_HIT_MARGIN_PX = 12
_COLOR_NORMAL = (1.0, 1.0, 1.0)
_COLOR_POINTER = (0x61 / 255, 0xB4 / 255, 0xA7 / 255)
_COLOR_GRABBING = (0xB7 / 255, 0xDE / 255, 0xD8 / 255)

try:
    from . import overlay_utils as utils
    from . import window_capture
except ImportError:
    import overlay_utils as utils
    import window_capture

# VR UI: Tauriの "VRCT VR Panel" ウィンドウ1枚に複数のウィンドウ (ログ・ランチャー) を並べて描き、
# 1回だけ撮影して、オーバーレイごとにその一部 (領域) を切り出して表示する。
# settings のキー。PANEL はログウィンドウ (位置は OVERLAY_VR_PANEL_SETTINGS に保存)
PANEL = "panel"
LAUNCHER = "launcher"
# 一時ウィンドウ (言語 / VR設定)。同時に1つだけ開き、開くたびにランチャーの近くに出す。位置は保存しない
POPUP = "popup"
# 撮影するウィンドウの大きさと各領域 (x, y, w, h)。論理px。
# src-ui/views/vr/vr_layout.json と一致させる (test_overlay_grab_move で確認)
VR_ATLAS_SIZE = (1628, 836)
VR_REGIONS = {
    PANEL: (0, 0, 900, 700),
    LAUNCHER: (10, 708, 880, 128),
    POPUP: (908, 0, 720, 640),
}
# 一時ウィンドウを出す位置: ランチャーの中心から上へ、頭との水平距離をこの範囲に収める
_POPUP_ABOVE_LAUNCHER_M = 0.18
_POPUP_DISTANCE_RANGE_M = (0.45, 0.65)
_PANEL_CAPTURE_INTERVAL_SEC = 1 / 15
_PANEL_FIND_INTERVAL_SEC = 2.0
# 各領域の角丸の半径 (論理px)。撮影した画像の領域の外と四隅を透明にする
_PANEL_CORNER_RADIUS_PX = 24

# 追従先 "Playspace": SteamVRの空間 (プレイスペース) に固定する。VRChatのスティック移動や
# 回転はワールド側が動くので、空間に固定したオーバーレイはアバターと一緒についてくる
PLAYSPACE = "Playspace"
_PLAYSPACE_INDEX = -1
# パネル下の追従先切り替えボタン。押すたびにこの順で切り替わる
PANEL_ANCHORS = (PLAYSPACE, "LeftHand", "RightHand", "HMD")
_TOOLBAR_WIDTH_RATIO = 0.3  # パネル幅に対するボタンの幅
_TOOLBAR_GAP_M = 0.012
_TRIGGER_MASK = 1 << openvr.k_EButton_SteamVR_Trigger
# スティックの倒し具合をホイール量へ変換する係数 (1フレームあたり)。WHEEL_DELTA=120
_PANEL_SCROLL_PER_FRAME = 60
_PANEL_SCROLL_DEADZONE = 0.3
# パネルの外 (クライアント領域外) の座標。ここへ移動・離すと、Webのclickは成立せずホバーも外れる
_OUTSIDE_XY = (-1, -1)
# ポインタの位置をVR UIへ知らせる (ホバー表示用)。この距離 (論理px) 未満の動きは送らない
_POINTER_NOTIFY_MIN_MOVE_PX = 4

def uvToPixel(u: float, v: float, width: int, height: int) -> tuple:
    """computeOverlayIntersection のUVをオーバーレイ画像のピクセル座標に変換する。

    UVは左下が原点だが、縦方向も「横幅」を1とした長さで、中心 (0.5) を基準にしている
    (実機で確認。縦横比の分だけ端ほどずれていた)。
    """
    x = u * width
    y = height / 2 - (v - 0.5) * width
    return (min(max(int(x), 0), width - 1), min(max(int(y), 0), height - 1))


def regionRect(size: str, image_size: tuple) -> tuple:
    """撮影した画像 (DPIで論理pxより大きいことがある) 上での領域 (x0, y0, x1, y1)。"""
    scale = image_size[0] / VR_ATLAS_SIZE[0]
    x, y, w, h = VR_REGIONS[size]
    return (round(x * scale), round(y * scale), round((x + w) * scale), round((y + h) * scale))


def regionBounds(size: str) -> tuple:
    """setOverlayTextureBounds の (uMin, uMax, vMin, vMax)。

    OpenGLのテクスチャでは、画像の上から y 行目は v = 1 - y/H として扱われる
    (画像全体なら vMin=1, vMax=0 で正しい向きになることを実機で確認済み)。
    vMin が表示の上端、vMax が下端に対応する。
    """
    W, H = VR_ATLAS_SIZE
    x, y, w, h = VR_REGIONS[size]
    return (x / W, (x + w) / W, 1 - y / H, 1 - (y + h) / H)


@lru_cache(maxsize=4)
def atlasMask(image_size: tuple) -> Image.Image:
    """各領域だけを角丸で残し、それ以外を透明にするマスク。"""
    scale = image_size[0] / VR_ATLAS_SIZE[0]
    mask = Image.new("L", image_size, 0)
    draw = ImageDraw.Draw(mask)
    for size in VR_REGIONS:
        x0, y0, x1, y1 = regionRect(size, image_size)
        draw.rounded_rectangle((x0, y0, x1 - 1, y1 - 1), radius=round(_PANEL_CORNER_RADIUS_PX * scale), fill=255)
    return mask


def popupPoseFacing(position: np.ndarray, target: np.ndarray) -> np.ndarray:
    """position に置き、表 (+Z) を target に向けた姿勢。傾きは付けない (上はワールドの上)。"""
    z = target - position
    z = z / (np.linalg.norm(z) or 1.0)
    up = np.array([0.0, 1.0, 0.0])
    x = np.cross(up, z)
    if np.linalg.norm(x) < 1e-6:
        x = np.array([1.0, 0.0, 0.0])
    x = x / np.linalg.norm(x)
    y = np.cross(z, x)
    pose = np.eye(4)
    pose[:3, 0], pose[:3, 1], pose[:3, 2], pose[:3, 3] = x, y, z, position
    return pose


def createAnchorButtonImages() -> Dict[str, Image.Image]:
    """パネル下の追従先切り替えボタンの画像 (今の追従先を表示)。"""
    from PIL import ImageFont

    font = ImageFont.truetype(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "NotoSansJP-Regular.ttf"), 34)
    labels = {PLAYSPACE: "Space", "LeftHand": "Left hand", "RightHand": "Right hand", "HMD": "Head"}
    images = {}
    for anchor, label in labels.items():
        img = Image.new("RGBA", (320, 88), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((2, 2, 317, 85), radius=42, fill=(0x2E, 0x2F, 0x32, 255), outline=(0x61, 0xB4, 0xA7, 255), width=3)
        icon = (28, 22, 72, 66)
        white = (0xF2, 0xF2, 0xF2, 255)
        if anchor == PLAYSPACE:  # ピン
            draw.ellipse((36, 18, 64, 46), outline=white, width=5)
            draw.polygon([(38, 40), (62, 40), (50, 66)], fill=white)
            draw.ellipse((46, 28, 54, 36), fill=white)
        elif anchor == "HMD":  # 人の頭と肩
            draw.ellipse((40, 18, 60, 38), outline=white, width=5)
            draw.arc((30, 42, 70, 82), 180, 360, fill=white, width=5)
        else:  # 手の平と指。右手は左右反転
            hand = Image.new("RGBA", (44, 44), (0, 0, 0, 0))
            d = ImageDraw.Draw(hand)
            d.rounded_rectangle((10, 18, 36, 42), radius=6, fill=white)
            for x in (10, 17, 24, 31):
                d.rounded_rectangle((x, 4, x + 5, 22), radius=2, fill=white)
            d.rounded_rectangle((32, 20, 43, 27), radius=3, fill=white)
            if anchor == "RightHand":
                hand = hand.transpose(Image.FLIP_LEFT_RIGHT)
            img.alpha_composite(hand, (icon[0], icon[1]))
        draw.text((90, 44), label, font=font, fill=white, anchor="lm")
        images[anchor] = img
    return images


def createPointerImages() -> Dict[str, Image.Image]:
    """ポインタ画像。白で描いてオーバーレイの色 (VRCTの緑) で着色する。"""
    images = {}
    for kind in ("dot", "plus", "minus"):
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((4, 4, 59, 59), fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=5)
        if kind != "dot":
            draw.line((18, 32, 46, 32), fill=(0, 0, 0, 255), width=7)
        if kind == "plus":
            draw.line((32, 18, 32, 46), fill=(0, 0, 0, 255), width=7)
        images[kind] = img
    return images


def mat34Id(array: Sequence[Sequence[float]]) -> Any:
    """Convert a 3x4 nested sequence into an openvr.HmdMatrix34_t instance.

    Args:
        array: 3x4 numeric sequence

    Returns:
        openvr HmdMatrix34_t compatible object
    """
    arr = openvr.HmdMatrix34_t()
    for i in range(3):
        for j in range(4):
            arr[i][j] = array[i][j]
    return arr

def getBaseMatrix(x_pos: float, y_pos: float, z_pos: float, x_rotation: float, y_rotation: float, z_rotation: float) -> np.ndarray:
    """Create a 3x4 base matrix for an overlay given position and Euler rotations.

    Returns a numpy array of shape (3,4).
    """
    arr = np.zeros((3, 4))
    rot = utils.euler_to_rotation_matrix((x_rotation, y_rotation, z_rotation))

    for i in range(3):
        for j in range(3):
            arr[i][j] = rot[i][j]

    arr[0][3] = x_pos * z_pos
    arr[1][3] = y_pos * z_pos
    arr[2][3] = - z_pos
    return arr

def getHMDBaseMatrix() -> np.ndarray:
    x_pos = 0.0
    y_pos = -0.4
    z_pos = 1.0
    x_rotation = 0.0
    y_rotation = 0.0
    z_rotation = 0.0
    arr = getBaseMatrix(x_pos, y_pos, z_pos, x_rotation, y_rotation, z_rotation)
    return arr

def getLeftHandBaseMatrix() -> np.ndarray:
    x_pos = 0.3
    y_pos = 0.1
    z_pos = -0.31
    x_rotation = -65.0
    y_rotation = 165.0
    z_rotation = 115.0
    arr = getBaseMatrix(x_pos, y_pos, z_pos, x_rotation, y_rotation, z_rotation)
    return arr

def getRightHandBaseMatrix() -> np.ndarray:
    x_pos = -0.3
    y_pos = 0.1
    z_pos = -0.31
    x_rotation = -65.0
    y_rotation = -165.0
    z_rotation = -115.0
    arr = getBaseMatrix(x_pos, y_pos, z_pos, x_rotation, y_rotation, z_rotation)
    return arr

class Overlay:
    """Manage OpenVR overlays for multiple sizes (e.g. 'small'/'large')."""
    def __init__(self, settings_dict: Dict[str, Dict[str, Any]]) -> None:
        self.system: Optional[Any] = None
        self.overlay: Optional[Any] = None
        self.handle: Dict[str, Any] = {}
        self.init_process: bool = False
        self.initialized: bool = False
        self.loop: bool = False
        self.thread_overlay: Optional[Thread] = None

        self.settings: Dict[str, Dict[str, Any]] = {}
        self.lastUpdate: Dict[str, float] = {}
        self.fadeRatio: Dict[str, float] = {}
        for key, value in settings_dict.items():
            self.settings[key] = value
            self.lastUpdate[key] = time.monotonic()
            self.fadeRatio[key] = 1.0

        # 手ごとの前フレームのグリップ状態。押した瞬間 (離→押) だけ掴む。
        # 押したままレーザーがオーバーレイに入っても掴まない (VRChatで物を持っている時など)
        self.grip_prev: Dict[int, bool] = {}
        self.grab_started: float = 0.0
        # パネル下の追従先切り替えボタン。追従先ごとに別オーバーレイにして表示を切り替える
        self.toolbar_handles: Dict[str, int] = {}
        self.trigger_prev: Dict[int, bool] = {}
        # grabbing: (size, 手のindex, 手から見たオーバーレイの4x4行列)
        self.grabbing: Optional[tuple] = None
        self.grab_last_relative: Optional[np.ndarray] = None
        # ポインタは種類ごとに別のオーバーレイにして表示を切り替える
        # (setOverlayRaw は約190回で失敗し続けるため、画像の差し替えはしない)
        self.pointer_handles: Dict[str, int] = {}
        # 掴み中の拡大縮小: (開始時の手の位置, 手の前方向, 開始時の幅, 固定したオーバーレイの姿勢)
        self.grab_scale: Optional[tuple] = None
        # 当たり判定で透明部分を除くため、最後に貼った画像を覚えておく
        self.images: Dict[str, Image.Image] = {}
        self.grab_error: Optional[str] = None
        # 追従先が未接続で位置を設定できていないオーバーレイ
        self.position_pending: set = set()

        # VRパネル。setOverlayRawは約190回で RequestFailed が続くようになり連続更新に
        # 使えないため、OpenGLテクスチャ経由 (setOverlayTexture) で渡す。
        self.gl: Optional[Dict[str, Any]] = None
        self.panel_hwnd: Optional[int] = None
        self.panel_last_find: float = 0.0
        self.panel_last_capture: float = 0.0
        self.panel_image_size: Optional[tuple] = None
        # 手ごとの (トリガーを押しているか, 最後に送った座標)
        self.panel_input: Dict[int, tuple] = {}
        # 掴み終えた時点でトリガーを押したままだった手。一度離すまでトリガーを無視する
        # (掴んだまま拡大縮小し、グリップを先に離したときのクリック誤爆を防ぐ)
        self.trigger_blocked: set = set()
        # VR UIのホバー表示用。WebView2 はOSの本物のカーソル位置でホバーを判定するので、
        # PostMessage のマウス移動ではホバーが付かない。ポインタの位置 (VR画面の論理px、
        # 外れたら None) をこのコールバックで知らせ、画面側でホバーを表示する
        self.pointer_callback: Optional[Callable[[Optional[tuple]], None]] = None
        self.pointer_notified: Optional[tuple] = None
        # VR UIのウィンドウの表示・非表示。VR画面 (React) が /run/vr_panel_windows で決め、
        # オーバーレイのスレッドが updateGrab の最初で反映する (vr_windows_hidden が今の状態)
        self.vr_windows_wanted: Dict[str, bool] = {PANEL: True, POPUP: False}
        self.vr_windows_hidden: set = set()
        # 手ごとの (grip, hit) 。変化したときだけログに出す(実機での切り分け用)
        self.debug_state: Dict[int, tuple] = {}
        # self.settings[size] の位置はオーバーレイスレッド(掴み確定)とUI設定変更の
        # 両方が書く。ロックは無い: 同時に起きても後勝ちになるだけで、壊れる値は無い。
        # 掴み移動で位置が確定したときに (size, 位置の設定値) で呼ばれる。
        # Model/Controllerが設定保存とUI通知に使う。
        self.position_changed_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None

    def init(self) -> None:
        try:
            # Go through the shared, reference-counted OpenVR session
            # instead of calling openvr.init() directly: Clipboard uses
            # the same session, and openvr.shutdown() tears down the
            # whole process's VR connection, not just this caller's.
            self.system = openvr_session.acquire(openvr.VRApplication_Background)
            self.overlay = openvr.IVROverlay()
            self.overlay_system = openvr.IVRSystem()
            self.handle = {}
            self.vr_windows_hidden = set()
            for i, size in enumerate(self.settings.keys()):
                self.handle[size] = self.overlay.createOverlay(f"VRCT{i}", f"VRCT{i}")
                self.overlay.showOverlay(self.handle[size])
            self.initialized = True
            for kind, img in createPointerImages().items():
                handle = self.overlay.createOverlay(f"VRCT_pointer_{kind}", f"VRCT_pointer_{kind}")
                self.overlay.setOverlaySortOrder(handle, 100)
                raw = img.tobytes()
                self.overlay.setOverlayRaw(handle, (ctypes.c_char * len(raw)).from_buffer_copy(raw), img.size[0], img.size[1], 4)
                self.pointer_handles[kind] = handle
            if PANEL in self.settings:
                for anchor, img in createAnchorButtonImages().items():
                    handle = self.overlay.createOverlay(f"VRCT_anchor_{anchor}", f"VRCT_anchor_{anchor}")
                    raw = img.tobytes()
                    self.overlay.setOverlayRaw(handle, (ctypes.c_char * len(raw)).from_buffer_copy(raw), img.size[0], img.size[1], 4)
                    self.toolbar_handles[anchor] = handle
                self.images["toolbar"] = next(iter(createAnchorButtonImages().values()))
            if any(size in self.settings for size in VR_REGIONS):
                try:
                    self.initPanelTexture()
                except Exception:
                    self.gl = None
                    errorLogging()

            for size in self.settings.keys():
                self.updateImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0)), size)
                self.updateColor([1, 1, 1], size)
                self.updateOpacity(self.settings[size]["opacity"], size)
                self.updateUiScaling(self.settings[size]["ui_scaling"], size)
                self.updatePosition(
                    self.settings[size]["x_pos"],
                    self.settings[size]["y_pos"],
                    self.settings[size]["z_pos"],
                    self.settings[size]["x_rotation"],
                    self.settings[size]["y_rotation"],
                    self.settings[size]["z_rotation"],
                    self.settings[size]["tracker"],
                    size
                )
                self.updateDisplayDuration(self.settings[size]["display_duration"], size)
                self.updateFadeoutDuration(self.settings[size]["fadeout_duration"], size)
            self.init_process = False

        except Exception:
            errorLogging()

    def updateImage(self, img: Image.Image, size: str) -> None:
        if self.initialized is True:
            self.images[size] = img
            width, height = img.size
            img = img.tobytes()
            img = (ctypes.c_char * len(img)).from_buffer_copy(img)

            try:
                self.overlay.setOverlayRaw(self.handle[size], img, width, height, 4)
            except Exception:
                self.reStartOverlay()
                deadline = time.monotonic() + _REINIT_WAIT_TIMEOUT_SEC
                while self.initialized is False and time.monotonic() < deadline:
                    time.sleep(_REINIT_WAIT_POLL_INTERVAL_SEC)
                if self.initialized is True:
                    try:
                        self.overlay.setOverlayRaw(self.handle[size], img, width, height, 4)
                    except Exception:
                        errorLogging()
                else:
                    # SteamVR/オーバーレイの再初期化が_REINIT_WAIT_TIMEOUT_SEC秒
                    # 以内に終わらなかった(例: SteamVRが落ちたまま)。呼び出し元
                    # (mainloopワーカースレッド)を無期限にブロックしないよう、
                    # この更新は諦める。
                    printLog(
                        f"overlay: {size}の再初期化が{_REINIT_WAIT_TIMEOUT_SEC}s"
                        "でタイムアウトしたため、この画像更新は諦めます"
                    )

            self.updateOpacity(self.settings[size]["opacity"], size)
            self.lastUpdate[size] = time.monotonic()

    def initPanelTexture(self) -> None:
        """VRパネル用のOpenGLコンテキストとテクスチャを作る (オーバーレイのスレッドで呼ぶこと)。"""
        if os.name != "nt":
            raise RuntimeError("VR panel capture is Windows only")
        import glfw
        from OpenGL import GL

        if not glfw.init():
            raise RuntimeError("glfw.init() failed")
        glfw.window_hint(glfw.VISIBLE, False)
        window = glfw.create_window(16, 16, "VRCT overlay GL", None, None)
        if not window:
            glfw.terminate()
            raise RuntimeError("glfw.create_window() failed")
        glfw.make_context_current(window)
        texture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        vr_texture = openvr.Texture_t()
        vr_texture.handle = int(texture)
        vr_texture.eType = openvr.TextureType_OpenGL
        vr_texture.eColorSpace = openvr.ColorSpace_Auto
        for size in self.vrRegionSizes():
            bounds = openvr.VRTextureBounds_t()
            bounds.uMin, bounds.uMax, bounds.vMin, bounds.vMax = regionBounds(size)
            self.overlay.setOverlayTextureBounds(self.handle[size], bounds)
        self.gl = {"glfw": glfw, "GL": GL, "window": window, "texture": texture, "vr_texture": vr_texture, "size": None}

    def vrRegionSizes(self) -> list:
        return [size for size in VR_REGIONS if size in self.settings]

    def shutdownPanelTexture(self) -> None:
        if self.gl is None:
            return
        try:
            self.gl["glfw"].destroy_window(self.gl["window"])
            self.gl["glfw"].terminate()
        except Exception:
            errorLogging()
        self.gl = None

    def updatePanel(self) -> None:
        """VRパネルのウィンドウを撮影してオーバーレイへ転送する。"""
        now = time.monotonic()
        if self.gl is None or now - self.panel_last_capture < _PANEL_CAPTURE_INTERVAL_SEC:
            return
        self.panel_last_capture = now
        if self.panel_hwnd is None or not window_capture.isWindow(self.panel_hwnd):
            self.panel_hwnd = None
            if now - self.panel_last_find < _PANEL_FIND_INTERVAL_SEC:
                return
            self.panel_last_find = now
            self.panel_hwnd = window_capture.findWindow()
            if self.panel_hwnd is None:
                return
        img = window_capture.captureWindow(self.panel_hwnd)
        if img is None:
            return
        img.putalpha(atlasMask(img.size))
        # 当たり判定 (hasContentAt) 用。updateImage を通らないのでここで記録する
        for size in self.vrRegionSizes():
            self.images[size] = img.crop(regionRect(size, img.size))
        GL = self.gl["GL"]
        raw = img.tobytes()
        # setOverlayTexture の後はバインドが外れるため、毎回バインドし直す
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.gl["texture"])
        if self.gl["size"] != img.size:
            self.gl["size"] = img.size
            GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA8, img.size[0], img.size[1], 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, raw)
        else:
            GL.glTexSubImage2D(GL.GL_TEXTURE_2D, 0, 0, 0, img.size[0], img.size[1], GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, raw)
        GL.glFinish()
        # 1枚のテクスチャを全領域のオーバーレイに渡す。表示される範囲は各オーバーレイの bounds で決まる
        for size in self.vrRegionSizes():
            self.overlay.setOverlayTexture(self.handle[size], self.gl["vr_texture"])
        self.panel_image_size = img.size

    def handlePanelInput(self, hand: int, xy: Optional[tuple], state: Optional[Any]) -> None:
        """レーザーが当たっている位置 (撮影画像上のピクセル、外れていれば None) へマウス入力を送る。

        トリガー=クリック、スティック上下=スクロール。
        """
        last_pressed, last_xy = self.panel_input.get(hand, (False, None))
        if self.panel_hwnd is None or self.panel_image_size is None or state is None:
            return
        pressed = bool(state.ulButtonPressed & _TRIGGER_MASK)
        if hand in self.trigger_blocked:
            if pressed:
                pressed = False
            else:
                self.trigger_blocked.discard(hand)
        if xy is None:
            # レーザーがパネルから外れた。押したまま外れた場合もパネルの外で離したことにして、
            # 押し始めたボタンのクリックを成立させない (マイクの誤ONを防ぐ)。ホバーも外す
            if last_xy is not None:
                window_capture.mouseMove(self.panel_hwnd, *_OUTSIDE_XY, pressed=last_pressed)
                if last_pressed:
                    window_capture.mouseUp(self.panel_hwnd, *_OUTSIDE_XY)
            self.panel_input.pop(hand, None)
            return
        if xy != last_xy:
            window_capture.mouseMove(self.panel_hwnd, *xy, pressed=pressed)
        if pressed and not last_pressed:
            window_capture.mouseDown(self.panel_hwnd, *xy)
        elif last_pressed and not pressed:
            window_capture.mouseUp(self.panel_hwnd, *xy)
        stick_y = state.rAxis[0].y
        if abs(stick_y) > _PANEL_SCROLL_DEADZONE:
            window_capture.mouseWheel(self.panel_hwnd, *xy, int(_PANEL_SCROLL_PER_FRAME * stick_y))
        self.panel_input[hand] = (pressed, xy)

    def clearImage(self, size: str) -> None:
        if self.initialized is True:
            self.updateImage(Image.new("RGBA", (1, 1), (0, 0, 0, 0)), size)

    def updateColor(self, col, size):
        """
        col is a 3-tuple representing (r, g, b)
        """
        if self.initialized is True:
            r, g, b = col
            self.overlay.setOverlayColor(self.handle[size], r, g, b)

    def updateOpacity(self, opacity: float, size: str, with_fade: bool = False) -> None:
        self.settings[size]["opacity"] = opacity

        if self.initialized is True:
            if with_fade is True:
                if self.fadeRatio[size] > 0:
                    self.overlay.setOverlayAlpha(self.handle[size], self.fadeRatio[size] * self.settings[size]["opacity"])
            else:
                self.overlay.setOverlayAlpha(self.handle[size], self.settings[size]["opacity"])

    def updateUiScaling(self, ui_scaling: float, size: str) -> None:
        self.settings[size]["ui_scaling"] = ui_scaling
        if self.initialized is True:
            self.overlay.setOverlayWidthInMeters(self.handle[size], self.settings[size]["ui_scaling"])

    def updatePosition(self, x_pos: float, y_pos: float, z_pos: float, x_rotation: float, y_rotation: float, z_rotation: float, tracker: str, size: str) -> None:
        """
        x_pos, y_pos, z_pos are floats representing the position of overlay
        x_rotation, y_rotation, z_rotation are floats representing the rotation of overlay
        tracker is a string representing the tracker to use ("HMD", "LeftHand", "RightHand")
        """

        self.settings[size]["x_pos"] = x_pos
        self.settings[size]["y_pos"] = y_pos
        self.settings[size]["z_pos"] = z_pos
        self.settings[size]["x_rotation"] = x_rotation
        self.settings[size]["y_rotation"] = y_rotation
        self.settings[size]["z_rotation"] = z_rotation
        self.settings[size]["tracker"] = tracker

        if self.initialized is True:
            base_matrix, trackerIndex = self.getTracker(tracker)
            translation = (self.settings[size]["x_pos"], self.settings[size]["y_pos"], - self.settings[size]["z_pos"])
            rotation = (self.settings[size]["x_rotation"], self.settings[size]["y_rotation"], self.settings[size]["z_rotation"])
            transform = utils.transform_matrix(base_matrix, translation, rotation)

            if trackerIndex == _PLAYSPACE_INDEX or bool(self.overlay_system.isTrackedDeviceConnected(trackerIndex)) is True:
                self.setTransform(size, trackerIndex, transform)
                self.position_pending.discard(size)
            else:
                # 追従先 (コントローラ等) がまだ繋がっていない。mainloop で繋がり次第やり直す
                self.position_pending.add(size)

    def retryPendingPositions(self) -> None:
        for size in list(self.position_pending):
            s = self.settings[size]
            self.updatePosition(s["x_pos"], s["y_pos"], s["z_pos"], s["x_rotation"], s["y_rotation"], s["z_rotation"], s["tracker"], size)

    def setTransform(self, size: str, tracker_index: int, relative: np.ndarray) -> None:
        """オーバーレイを追従先から見た位置 (3x4) に置く。パネルなら下のボタンも一緒に動かす。"""
        if tracker_index == _PLAYSPACE_INDEX:
            self.overlay.setOverlayTransformAbsolute(self.handle[size], openvr.TrackingUniverseStanding, mat34Id(relative))
        else:
            self.overlay.setOverlayTransformTrackedDeviceRelative(self.handle[size], tracker_index, mat34Id(relative))
        if size == PANEL and self.toolbar_handles:
            self.placeToolbar(tracker_index, relative)

    def placeToolbar(self, tracker_index: int, panel_relative: np.ndarray) -> None:
        """追従先切り替えボタンをパネルの下に置き、今の追従先のボタンだけ表示する。"""
        panel_width = self.settings[PANEL]["ui_scaling"]
        _, _, image_width, image_height = VR_REGIONS[PANEL]
        button = self.images["toolbar"]
        width = panel_width * _TOOLBAR_WIDTH_RATIO
        height = width * button.size[1] / button.size[0]
        offset = np.eye(4)
        offset[1][3] = -(panel_width * image_height / image_width / 2 + _TOOLBAR_GAP_M + height / 2)
        relative = (utils.toHomogeneous(panel_relative) @ offset)[:3, :]
        for anchor, handle in self.toolbar_handles.items():
            if anchor != self.settings[PANEL]["tracker"] or PANEL in self.vr_windows_hidden:
                self.overlay.hideOverlay(handle)
                continue
            self.overlay.setOverlayWidthInMeters(handle, width)
            if tracker_index == _PLAYSPACE_INDEX:
                self.overlay.setOverlayTransformAbsolute(handle, openvr.TrackingUniverseStanding, mat34Id(relative))
            else:
                self.overlay.setOverlayTransformTrackedDeviceRelative(handle, tracker_index, mat34Id(relative))
            self.overlay.showOverlay(handle)

    def overlayWorldPose(self, size: str, poseOf: Callable[[int], Optional[np.ndarray]]) -> Optional[np.ndarray]:
        """オーバーレイの今の姿勢 (空間座標の4x4)。追従先の姿勢が取れなければ None。"""
        s = self.settings[size]
        base_matrix, tracker_index = self.getTracker(s["tracker"])
        tracker_pose = poseOf(tracker_index)
        if tracker_pose is None:
            return None
        relative = utils.transform_matrix(base_matrix, (s["x_pos"], s["y_pos"], -s["z_pos"]), (s["x_rotation"], s["y_rotation"], s["z_rotation"]))
        return tracker_pose @ utils.toHomogeneous(relative)

    def regionPixel(self, size: str, results: Any, overlay_pose: np.ndarray) -> tuple:
        """レーザーの当たった点 (空間座標) を、撮影画像上のピクセル座標にする。

        computeOverlayIntersection の UV は、テクスチャの一部を切り出したオーバーレイで基準が
        変わるため使わない。オーバーレイの姿勢と幅から、当たった点の位置を自分で求める。
        オーバーレイの中心が原点で、x が右、y が上。
        """
        point = np.array([results.vPoint.v[0], results.vPoint.v[1], results.vPoint.v[2], 1.0])
        local = np.linalg.inv(overlay_pose) @ point
        _, _, region_w, region_h = VR_REGIONS[size]
        width_m = self.settings[size]["ui_scaling"]
        height_m = width_m * region_h / region_w
        fx = min(max(local[0] / width_m + 0.5, 0.0), 1.0)
        fy = min(max(0.5 - local[1] / height_m, 0.0), 1.0)
        x0, y0, x1, y1 = regionRect(size, self.panel_image_size)
        return (min(x0 + int(fx * (x1 - x0)), x1 - 1), min(y0 + int(fy * (y1 - y0)), y1 - 1))

    def cycleAnchor(self, poseOf: Callable[[int], Optional[np.ndarray]]) -> None:
        """パネルの追従先を次に切り替える。パネルは今見えている場所から動かさない。"""
        s = self.settings[PANEL]
        anchors = PANEL_ANCHORS
        new_anchor = anchors[(anchors.index(s["tracker"]) + 1) % len(anchors)] if s["tracker"] in anchors else anchors[0]
        _, new_index = self.getTracker(new_anchor)
        new_pose = poseOf(new_index)
        world = self.overlayWorldPose(PANEL, poseOf)
        if world is None or new_pose is None:
            return
        s["tracker"] = new_anchor
        new_relative = (np.linalg.inv(new_pose) @ world)[:3, :]
        self.commitPosition(PANEL, new_relative)
        self.updatePosition(s["x_pos"], s["y_pos"], s["z_pos"], s["x_rotation"], s["y_rotation"], s["z_rotation"], new_anchor, PANEL)

    def getTracker(self, tracker: str) -> tuple:
        """Return (base 3x4 matrix, tracked device index) for a tracker name."""
        match tracker:
            case "Playspace":
                return np.hstack([np.eye(3), np.zeros((3, 1))]), _PLAYSPACE_INDEX
            case "LeftHand":
                return getLeftHandBaseMatrix(), self.overlay_system.getTrackedDeviceIndexForControllerRole(openvr.TrackedControllerRole_LeftHand)
            case "RightHand":
                return getRightHandBaseMatrix(), self.overlay_system.getTrackedDeviceIndexForControllerRole(openvr.TrackedControllerRole_RightHand)
            case _:
                return getHMDBaseMatrix(), openvr.k_unTrackedDeviceIndex_Hmd

    def isVisible(self, size: str) -> bool:
        if self.settings[size]["opacity"] <= 0:
            return False
        return self.settings[size]["fadeout_duration"] == 0 or self.fadeRatio[size] > 0

    def intersect(self, pose: np.ndarray, size: str) -> Optional[Any]:
        """コントローラのレーザーとオーバーレイの交点。当たらなければ None。"""
        params = openvr.VROverlayIntersectionParams_t()
        params.eOrigin = openvr.TrackingUniverseStanding
        for i in range(3):
            params.vSource.v[i] = pose[i][3]
            params.vDirection.v[i] = -pose[i][2]  # コントローラの前方は -Z
        hit, results = self.overlay.computeOverlayIntersection(self.handle[size], params)
        return results if hit else None

    def intersectToolbar(self, pose: np.ndarray) -> Optional[Any]:
        handle = self.toolbar_handles.get(self.settings.get(PANEL, {}).get("tracker"))
        if handle is None or PANEL in self.vr_windows_hidden:
            return None
        params = openvr.VROverlayIntersectionParams_t()
        params.eOrigin = openvr.TrackingUniverseStanding
        for i in range(3):
            params.vSource.v[i] = pose[i][3]
            params.vDirection.v[i] = -pose[i][2]
        hit, results = self.overlay.computeOverlayIntersection(handle, params)
        return results if hit else None

    def hasContentAt(self, size: str, results: Any) -> bool:
        """当たった位置の近くに描画がある (透明でない) か。"""
        img = self.images.get(size)
        # VR UIの領域は角丸以外すべて不透明。UVの基準も違うので判定しない (regionPixel 参照)
        if size in VR_REGIONS or img is None or img.mode != "RGBA":
            return True
        x, y = uvToPixel(results.vUVs.v[0], results.vUVs.v[1], img.size[0], img.size[1])
        r = _HIT_MARGIN_PX
        return img.crop((x - r, y - r, x + r + 1, y + r + 1)).getchannel("A").getextrema()[1] > 0

    def pointingOverlay(self, pose: np.ndarray) -> tuple:
        """Return (size, intersection results) of the overlay the controller ray hits, or (None, None).

        フェードアウトした(見えない)オーバーレイも対象にする: グリップで起こして掴めるように。
        画像の透明な部分は対象にしない。
        """
        best = (None, None)
        for size in self.settings.keys():
            if self.settings[size]["opacity"] <= 0 or size in self.vr_windows_hidden:
                continue
            results = self.intersect(pose, size)
            if results is None or not self.hasContentAt(size, results):
                continue
            if best[1] is None or results.fDistance < best[1].fDistance:
                best = (size, results)
        return best

    def wakeOverlay(self, size: str) -> None:
        self.lastUpdate[size] = time.monotonic()
        self.fadeRatio[size] = 1.0
        self.overlay.setOverlayAlpha(self.handle[size], self.settings[size]["opacity"])

    def showPointer(self, results: Optional[Any], color: Sequence[float], scale: float = 1.0, kind: str = "dot") -> None:
        """レーザーの当たった位置にポインタを表示する。results が None なら隠す。

        kind: "dot" / "plus" (拡大中) / "minus" (縮小中)
        """
        for other, handle in self.pointer_handles.items():
            if other != kind or results is None:
                self.overlay.hideOverlay(handle)
        handle = self.pointer_handles.get(kind)
        if handle is None or results is None:
            return
        normal = np.array([results.vNormal.v[i] for i in range(3)])
        point = np.array([results.vPoint.v[i] for i in range(3)]) + normal * 0.002
        up = np.array([0.0, 1.0, 0.0]) if abs(normal[1]) < 0.99 else np.array([1.0, 0.0, 0.0])
        x_axis = np.cross(up, normal)
        x_axis /= np.linalg.norm(x_axis)
        y_axis = np.cross(normal, x_axis)
        m = np.column_stack([x_axis, y_axis, normal, point])
        width = _POINTER_WIDTH_M * (1.0 if kind == "dot" else 2.0) * scale
        self.overlay.setOverlayTransformAbsolute(handle, openvr.TrackingUniverseStanding, mat34Id(m))
        self.overlay.setOverlayColor(handle, *color)
        self.overlay.setOverlayWidthInMeters(handle, width)
        self.overlay.showOverlay(handle)

    def setHighlight(self, size: Optional[str], color: Sequence[float]) -> None:
        """掴み対象のオーバーレイを色付けする。size が None なら全て元の色に戻す。"""
        for s in self.settings.keys():
            self.overlay.setOverlayColor(self.handle[s], *(color if s == size else _COLOR_NORMAL))

    def updateGrab(self) -> None:
        """グリップ長押しでオーバーレイを掴み、離したら位置を確定する。

        ポインタは指している位置に出て、グリップ長押し中は縮んでいき、縮みきったら掴む。
        掴んでいる間はオーバーレイを薄い緑で色付けする。
        """
        # None を渡すと pyopenvr は配列を確保せず None を返すため、自前で確保して渡す
        poses = (openvr.TrackedDevicePose_t * openvr.k_unMaxTrackedDeviceCount)()
        self.overlay_system.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseStanding, 0, poses)

        def poseOf(index: int) -> Optional[np.ndarray]:
            if index == _PLAYSPACE_INDEX:
                return np.eye(4)
            if index == openvr.k_unTrackedDeviceIndexInvalid or not poses[index].bPoseIsValid:
                return None
            m = poses[index].mDeviceToAbsoluteTracking
            return utils.toHomogeneous(np.array([[m[i][j] for j in range(4)] for i in range(3)]))

        def controllerState(index: int) -> Optional[Any]:
            ok, state = self.overlay_system.getControllerState(index)
            return state if ok else None

        def gripPressed(index: int) -> bool:
            state = controllerState(index)
            return state is not None and bool(state.ulButtonPressed & _GRIP_MASK)

        now = time.monotonic()
        self.applyVrWindows(poseOf)

        if self.grabbing is not None:
            size, hand, hand_to_overlay = self.grabbing
            hand_pose = poseOf(hand)
            _, tracker_index = self.getTracker(self.settings[size]["tracker"])
            tracker_pose = poseOf(tracker_index)
            if hand_pose is None or tracker_pose is None:
                # トラッキングロスト(スリープ・電源断等)では離したことも検知できないため、
                # 掴みを解除して最後に表示していた位置で確定する。
                self.grabbing = None
                self.grab_scale = None
                self.setHighlight(None, _COLOR_NORMAL)
                self.showPointer(None, _COLOR_NORMAL)
                if self.grab_last_relative is not None:
                    self.commitPosition(size, self.grab_last_relative)
                return
            self.notifyPointer(None)
            state = controllerState(hand)
            grip = state is not None and bool(state.ulButtonPressed & _GRIP_MASK)
            trigger = state is not None and bool(state.ulButtonPressed & _TRIGGER_MASK)
            self.grip_prev[hand] = grip
            if grip and trigger:
                self.updateGrabScale(size, hand_pose, tracker_pose, tracker_index)
                return
            if self.grab_scale is not None:
                # 拡大縮小を終えたら、止めていた位置を今の手から掴み直す
                hand_to_overlay = np.linalg.inv(hand_pose) @ self.grab_scale[3]
                self.grabbing = (size, hand, hand_to_overlay)
                self.grab_scale = None
                self.showPointer(None, _COLOR_NORMAL)
            relative = np.linalg.inv(tracker_pose) @ hand_pose @ hand_to_overlay
            self.grab_last_relative = relative[:3, :]
            if grip:
                self.setTransform(size, tracker_index, relative[:3, :])
                self.wakeOverlay(size)  # 掴んでいる間はフェードさせない
                pop = min((now - self.grab_started) / _GRAB_POP_SEC, 1.0)
                self.showPointer(self.intersect(hand_pose, size), _COLOR_POINTER, 1.0 + (_GRAB_POP_SCALE - 1.0) * pop)
            else:
                self.grabbing = None
                self.setHighlight(None, _COLOR_NORMAL)
                self.showPointer(None, _COLOR_NORMAL)
                if trigger:
                    self.trigger_blocked.add(hand)
                    self.trigger_prev[hand] = True  # 切り替えボタンも押した扱いにしない
                self.commitPosition(size, relative[:3, :])
            return

        pointer = None  # (results, color[, scale])
        hover_xy = None
        for role in (openvr.TrackedControllerRole_LeftHand, openvr.TrackedControllerRole_RightHand):
            hand = self.overlay_system.getTrackedDeviceIndexForControllerRole(role)
            hand_pose = poseOf(hand)
            grip = hand_pose is not None and gripPressed(hand)
            size, results = (None, None) if hand_pose is None else self.pointingOverlay(hand_pose)
            # 自分の手に付いているオーバーレイはその手では動かせない(手と一緒に動くだけ)
            if size is not None and self.getTracker(self.settings[size]["tracker"])[1] == hand:
                size, results = None, None

            debug_state = (grip, size)
            if self.debug_state.get(hand) != debug_state:
                self.debug_state[hand] = debug_state
                printLog("overlay grab", {"hand": hand, "grip": grip, "hit": size})

            if hand_pose is not None and not grip:
                xy = None
                if size in VR_REGIONS and self.panel_image_size is not None:
                    overlay_pose = self.overlayWorldPose(size, poseOf)
                    if overlay_pose is not None:
                        xy = self.regionPixel(size, results, overlay_pose)
                self.handlePanelInput(hand, xy, controllerState(hand))
                if xy is not None and hover_xy is None:
                    scale = self.panel_image_size[0] / VR_ATLAS_SIZE[0]
                    hover_xy = (round(xy[0] / scale), round(xy[1] / scale))

            # パネル下の追従先切り替えボタン: トリガーを押した瞬間に切り替える
            state = controllerState(hand) if hand_pose is not None else None
            trigger = state is not None and bool(state.ulButtonPressed & _TRIGGER_MASK)
            trigger_pressed_now = trigger and not self.trigger_prev.get(hand, False)
            self.trigger_prev[hand] = trigger
            toolbar = self.intersectToolbar(hand_pose) if hand_pose is not None else None
            if toolbar is not None and (results is None or toolbar.fDistance < results.fDistance):
                if trigger_pressed_now:
                    self.cycleAnchor(poseOf)
                if pointer is None:
                    pointer = (toolbar, _COLOR_POINTER)
                continue

            grip_pressed_now = grip and not self.grip_prev.get(hand, False)
            self.grip_prev[hand] = grip
            if size is None or not grip_pressed_now:
                if size is not None and not grip and self.isVisible(size) and pointer is None:
                    pointer = (results, _COLOR_POINTER)
                continue

            overlay_pose = self.overlayWorldPose(size, poseOf)
            if overlay_pose is None:
                continue
            self.wakeOverlay(size)  # フェード済みでもグリップで起こす
            self.grabbing = (size, hand, np.linalg.inv(hand_pose) @ overlay_pose)
            self.grab_last_relative = None
            self.grab_started = now
            self.showPointer(results, _COLOR_POINTER)
            self.setHighlight(size, _COLOR_GRABBING)
            return

        self.showPointer(*(pointer or (None, _COLOR_NORMAL)))
        self.notifyPointer(hover_xy)

    def setVrWindows(self, log: bool, popup: bool) -> None:
        """VR UIのウィンドウの表示・非表示を指定する (どのスレッドからでもよい)。"""
        self.vr_windows_wanted = {PANEL: log, POPUP: popup}

    def applyVrWindows(self, poseOf: Callable[[int], Optional[np.ndarray]]) -> None:
        """指定された表示・非表示をオーバーレイに反映する (オーバーレイのスレッドで呼ぶ)。"""
        for size, wanted in self.vr_windows_wanted.items():
            if size not in self.handle:
                continue
            hidden = size in self.vr_windows_hidden
            if wanted and hidden:
                if size == POPUP:
                    self.placePopup(poseOf)
                self.vr_windows_hidden.discard(size)
                self.overlay.showOverlay(self.handle[size])
                if size == PANEL:
                    s = self.settings[PANEL]
                    self.updatePosition(s["x_pos"], s["y_pos"], s["z_pos"], s["x_rotation"], s["y_rotation"], s["z_rotation"], s["tracker"], PANEL)
            elif not wanted and not hidden:
                self.vr_windows_hidden.add(size)
                self.overlay.hideOverlay(self.handle[size])
                if size == PANEL:
                    for handle in self.toolbar_handles.values():
                        self.overlay.hideOverlay(handle)
                if self.grabbing is not None and self.grabbing[0] == size:
                    self.grabbing = None
                    self.grab_scale = None
                    self.setHighlight(None, _COLOR_NORMAL)
                    self.showPointer(None, _COLOR_NORMAL)

    def placePopup(self, poseOf: Callable[[int], Optional[np.ndarray]]) -> None:
        """一時ウィンドウをランチャーの上に、頭の方を向けて空間固定で出す。"""
        head = poseOf(openvr.k_unTrackedDeviceIndex_Hmd)
        if head is None:
            return
        head_pos = head[:3, 3]
        launcher = self.overlayWorldPose(LAUNCHER, poseOf) if LAUNCHER in self.settings else None
        if launcher is not None:
            pos = launcher[:3, 3] + np.array([0.0, _POPUP_ABOVE_LAUNCHER_M, 0.0])
        else:
            pos = head_pos + (-head[:3, 2]) * _POPUP_DISTANCE_RANGE_M[0]  # ランチャーが無ければ頭の正面
        horizontal = pos - head_pos
        horizontal[1] = 0.0
        distance = float(np.linalg.norm(horizontal))
        if distance > 1e-6:
            clamped = min(max(distance, _POPUP_DISTANCE_RANGE_M[0]), _POPUP_DISTANCE_RANGE_M[1])
            pos = head_pos + horizontal / distance * clamped + np.array([0.0, pos[1] - head_pos[1], 0.0])
        world = popupPoseFacing(pos, head_pos)
        self.settings[POPUP]["tracker"] = PLAYSPACE
        self.commitPosition(POPUP, world[:3, :])
        s = self.settings[POPUP]
        self.updatePosition(s["x_pos"], s["y_pos"], s["z_pos"], s["x_rotation"], s["y_rotation"], s["z_rotation"], PLAYSPACE, POPUP)

    def notifyPointer(self, xy: Optional[tuple]) -> None:
        """ポインタの位置が変わったときだけ VR UI へ知らせる。"""
        last = self.pointer_notified
        if xy == last or (
            xy is not None and last is not None
            and abs(xy[0] - last[0]) < _POINTER_NOTIFY_MIN_MOVE_PX and abs(xy[1] - last[1]) < _POINTER_NOTIFY_MIN_MOVE_PX
        ):
            return
        self.pointer_notified = xy
        if self.pointer_callback is not None:
            try:
                self.pointer_callback(xy)
            except Exception:
                errorLogging()

    def updateGrabScale(self, size: str, hand_pose: np.ndarray, tracker_pose: np.ndarray, tracker_index: int) -> None:
        """掴んだままトリガーを引いている間: オーバーレイをその場に止め、手の前後の動きで拡大縮小する。"""
        if self.grab_scale is None:
            if self.grab_last_relative is None:
                return
            overlay_pose = tracker_pose @ utils.toHomogeneous(self.grab_last_relative)
            self.grab_scale = (hand_pose[:3, 3].copy(), -hand_pose[:3, 2].copy(), self.settings[size]["ui_scaling"], overlay_pose)
        start_position, forward, start_width, overlay_pose = self.grab_scale
        pushed = float(np.dot(hand_pose[:3, 3] - start_position, forward))
        width = min(max(start_width * 2 ** (pushed / _SCALE_DOUBLING_M), _WIDTH_MIN_M), _WIDTH_MAX_M)
        self.updateUiScaling(width, size)
        relative = np.linalg.inv(tracker_pose) @ overlay_pose
        self.grab_last_relative = relative[:3, :]
        self.setTransform(size, tracker_index, relative[:3, :])
        self.wakeOverlay(size)
        kind = "plus" if pushed > _SCALE_ICON_THRESHOLD_M else "minus" if pushed < -_SCALE_ICON_THRESHOLD_M else "dot"
        self.showPointer(self.intersect(hand_pose, size), _COLOR_POINTER, kind=kind)

    def commitPosition(self, size: str, relative: np.ndarray) -> None:
        """掴んで動かした結果 (位置と幅) を確定し、保存用にコールバックへ渡す。"""
        base_matrix, _ = self.getTracker(self.settings[size]["tracker"])
        keys = ("x_pos", "y_pos", "z_pos", "x_rotation", "y_rotation", "z_rotation")
        for key, value in zip(keys, utils.matrix_to_position(base_matrix, relative)):
            self.settings[size][key] = round(value, 4)
        if self.position_changed_callback is not None:
            try:
                # ui_scaling はオーバーレイの幅(m)。設定値への換算は呼び出し側で行う
                self.position_changed_callback(size, {
                    **{k: self.settings[size][k] for k in keys},
                    "ui_scaling": self.settings[size]["ui_scaling"],
                    "tracker": self.settings[size]["tracker"],
                })
            except Exception:
                errorLogging()

    def updateDisplayDuration(self, display_duration: float, size: str) -> None:
        self.settings[size]["display_duration"] = display_duration

    def updateFadeoutDuration(self, fadeout_duration: float, size: str) -> None:
        self.settings[size]["fadeout_duration"] = fadeout_duration

    def checkActive(self) -> bool:
        try:
            if self.system is not None and self.initialized is True:
                new_event = openvr.VREvent_t()
                while self.system.pollNextEvent(new_event):
                    if new_event.eventType == openvr.VREvent_Quit:
                        return False
            return True
        except Exception:
            errorLogging()
            return False

    def evaluateOpacityFade(self, size: str) -> None:
        currentTime = time.monotonic()
        if (currentTime - self.lastUpdate[size]) > self.settings[size]["display_duration"]:
            timeThroughInterval = currentTime - self.lastUpdate[size] - self.settings[size]["display_duration"]
            self.fadeRatio[size] = 1 - timeThroughInterval / self.settings[size]["fadeout_duration"]
            if self.fadeRatio[size] < 0:
                self.fadeRatio[size] = 0
            self.overlay.setOverlayAlpha(self.handle[size], self.fadeRatio[size] * self.settings[size]["opacity"])

    def update(self, size: str) -> None:
        if self.settings[size]["fadeout_duration"] != 0:
            self.evaluateOpacityFade(size)
        else:
            self.updateOpacity(self.settings[size]["opacity"], size)

    def mainloop(self) -> None:
        self.loop = True
        while self.checkActive() is True and self.loop is True:
            startTime = time.monotonic()
            for size in self.settings.keys():
                self.update(size)
            try:
                self.retryPendingPositions()
            except Exception:
                errorLogging()
            try:
                self.updatePanel()
            except Exception:
                # 失敗し続けてもログを埋めないよう、パネルを止める
                errorLogging()
                self.shutdownPanelTexture()
            try:
                self.updateGrab()
                self.grab_error = None
            except Exception as e:
                self.grabbing = None
                # 毎フレーム呼ばれるため、同じ例外が続く間はログを1回だけにする
                if repr(e) != self.grab_error:
                    self.grab_error = repr(e)
                    errorLogging()
            # 掴んでいる間は追従を滑らかにするため更新頻度を上げる
            interval = (1 / 60) if self.grabbing is not None else (1 / 16)
            sleepTime = interval - (time.monotonic() - startTime)
            if sleepTime > 0:
                time.sleep(sleepTime)
        # GLコンテキストは作ったスレッドでしか破棄できない
        self.shutdownPanelTexture()

    def main(self) -> None:
        while self.checkSteamvrRunning() is False:
            time.sleep(10)
        self.init()
        if self.initialized is True:
            self.mainloop()

    def startOverlay(self) -> None:
        if self.initialized is False and self.init_process is False:
            self.init_process = True
            self.thread_overlay = Thread(target=self.main)
            self.thread_overlay.daemon = True
            self.thread_overlay.start()

    def shutdownOverlay(self) -> None:
        if self.initialized is True and self.init_process is False:
            if isinstance(self.thread_overlay, Thread):
                self.loop = False
                self.thread_overlay.join(timeout=_SHUTDOWN_JOIN_TIMEOUT_SEC)
                if self.thread_overlay.is_alive():
                    # mainloop()がOpenVRのブロッキング呼び出し等で詰まって
                    # いる可能性がある。Pythonのスレッドは外部から強制終了
                    # できないため、これ以上は待たずに諦める。
                    #
                    # self.overlay/self.systemはここで破棄しない: 詰まって
                    # いるスレッドが後で復帰した際に、None化されたオブジェ
                    # クトへ触れて例外になる恐れがあるため。代償として
                    # OpenVRのオーバーレイハンドルとセッション参照が1つ分
                    # リークするが、self.initializedはFalseに戻すことで
                    # 次の startOverlay() が新しいオーバーレイを作り直せる
                    # ようにする(=再起動しなくても機能を復旧できることを
                    # 優先する。バックエンドレビュー フェーズ4項目31)。
                    printLog(
                        f"overlay: shutdownOverlayのスレッドjoinが"
                        f"{_SHUTDOWN_JOIN_TIMEOUT_SEC}sでタイムアウトしました"
                        "(古いスレッドは残存、ハンドルはリークします)"
                    )
                    self.thread_overlay = None
                    self.initialized = False
                    return
                self.thread_overlay = None
            if isinstance(self.overlay, openvr.IVROverlay):
                for size in self.settings.keys():
                    if isinstance(self.handle[size], int):
                        self.overlay.destroyOverlay(self.handle[size])
                for handle in [*self.pointer_handles.values(), *self.toolbar_handles.values()]:
                    self.overlay.destroyOverlay(handle)
                self.pointer_handles = {}
                self.toolbar_handles = {}
                self.overlay = None
            if isinstance(self.system, openvr.IVRSystem):
                # Only releases our reference; the real openvr.shutdown()
                # only runs once every other holder (e.g. Clipboard) has
                # released theirs too.
                openvr_session.release()
                self.system = None
            self.initialized = False

    def reStartOverlay(self) -> None:
        self.shutdownOverlay()
        self.startOverlay()

    @staticmethod
    def checkSteamvrRunning() -> bool:
        _proc_name = "vrmonitor.exe" if os.name == "nt" else "vrmonitor"
        return _proc_name in (p.name() for p in process_iter())

if __name__ == "__main__":
    from overlay_image import OverlayImage
    import logging

    logging.basicConfig(level=logging.DEBUG)

    small_settings = {
        "x_pos": 0.0,
        "y_pos": 0.0,
        "z_pos": 0.0,
        "x_rotation": 0.0,
        "y_rotation": 0.0,
        "z_rotation": 0.0,
        "display_duration": 5,
        "fadeout_duration": 2,
        "opacity": 1.0,
        "ui_scaling": 1.0,
        "tracker": "HMD",
    }

    large_settings = {
        "x_pos": 0.0,
        "y_pos": 0.0,
        "z_pos": 0.0,
        "x_rotation": 0.0,
        "y_rotation": 0.0,
        "z_rotation": 0.0,
        "display_duration": 5,
        "fadeout_duration": 2,
        "opacity": 1.0,
        "ui_scaling": 0.25,
        "tracker": "LeftHand",
    }

    settings_dict = {
        "small": small_settings,
        "large": large_settings
    }

    # オーバーレイの初期化設定を確認
    logging.debug(f"Settings Dict: {settings_dict}")

    overlay_image = OverlayImage()
    overlay = Overlay(settings_dict)
    overlay.startOverlay()

    while overlay.initialized is False:
        time.sleep(1)

    # Example usage
    for i in range(1000):
        try:
            print(i)
            img = overlay_image.createOverlayImageLargeLog("send", f"こんにちは、世界！さようなら {i}", "Japanese", "Hello,World!Goodbye", "Japanese")
            logging.debug(f"Generated Image: {img}")
            overlay.updateImage(img, "large")
            img = overlay_image.createOverlayImageSmallLog(f"こんにちは、世界！さようなら_{i}", "Japanese", "Hello,World!Goodbye", "Japanese")
            overlay.updateImage(img, "small")
            time.sleep(1)
        except openvr.error_code.OverlayError_InvalidParameter as e:
            errorLogging()
            logging.error(f"OverlayError_InvalidParameter: {e}")
            break
        except Exception as e:
            errorLogging()
            logging.error(f"Unexpected error: {e}")
            break

    # for i in range(100):
    #     print(i)
    #     # Example usage
    #     img = overlay_image.createOverlayImageSmallLog(f"こんにちは、世界！さようなら_{i}", "Japanese", "Hello,World!Goodbye", "Japanese")
    #     overlay.updateImage(img, "small")
    #     time.sleep(5)

    #     if i%2 == 0:
    #         overlay.updatePosition(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "HMD", "small")
    #     else:
    #         overlay.updatePosition(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "RightHand", "small")

    overlay.shutdownOverlay()