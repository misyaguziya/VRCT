import os
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

# グリップ長押しで掴む。グリップはVRChatにも同時に届き(オーバーレイ側で
# 入力を奪えない)、短押しはアバターの掴み操作と区別できないため。
_GRAB_HOLD_SEC = 0.5
_GRIP_MASK = 1 << openvr.k_EButton_Grip
_POINTER_WIDTH_M = 0.015
_COLOR_NORMAL = (1.0, 1.0, 1.0)
_COLOR_POINTER = (1.0, 1.0, 1.0)
_COLOR_HOLDING = (1.0, 0.85, 0.3)
_COLOR_GRABBING = (0.4, 1.0, 0.5)

try:
    from . import overlay_utils as utils
except ImportError:
    import overlay_utils as utils

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

        # 掴み移動の状態。grab_candidate: (size, 手のindex, 押し始め時刻)
        self.grab_candidate: Optional[tuple] = None
        # grabbing: (size, 手のindex, 手から見たオーバーレイの4x4行列)
        self.grabbing: Optional[tuple] = None
        self.grab_last_relative: Optional[np.ndarray] = None
        self.pointer_handle: Optional[int] = None
        self.grab_error: Optional[str] = None
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
            for i, size in enumerate(self.settings.keys()):
                self.handle[size] = self.overlay.createOverlay(f"VRCT{i}", f"VRCT{i}")
                self.overlay.showOverlay(self.handle[size])
            self.pointer_handle = self.overlay.createOverlay("VRCT_pointer", "VRCT_pointer")
            self.overlay.setOverlayWidthInMeters(self.pointer_handle, _POINTER_WIDTH_M)
            self.overlay.setOverlaySortOrder(self.pointer_handle, 100)
            self.initialized = True
            dot = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
            ImageDraw.Draw(dot).ellipse((2, 2, 29, 29), fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=3)
            self.updatePointerImage(dot)

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

    def updatePointerImage(self, img: Image.Image) -> None:
        raw = img.tobytes()
        buf = (ctypes.c_char * len(raw)).from_buffer_copy(raw)
        self.overlay.setOverlayRaw(self.pointer_handle, buf, img.size[0], img.size[1], 4)

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
            transform = mat34Id(transform)

            if bool(self.overlay_system.isTrackedDeviceConnected(trackerIndex)) is True:
                self.overlay.setOverlayTransformTrackedDeviceRelative(
                    self.handle[size],
                    trackerIndex,
                    transform
                )

    def getTracker(self, tracker: str) -> tuple:
        """Return (base 3x4 matrix, tracked device index) for a tracker name."""
        match tracker:
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

    def pointingOverlay(self, pose: np.ndarray) -> tuple:
        """Return (size, intersection results) of the overlay the controller ray hits, or (None, None).

        フェードアウトした(見えない)オーバーレイも対象にする: グリップで起こして掴めるように。
        """
        params = openvr.VROverlayIntersectionParams_t()
        params.eOrigin = openvr.TrackingUniverseStanding
        for i in range(3):
            params.vSource.v[i] = pose[i][3]
            params.vDirection.v[i] = -pose[i][2]  # コントローラの前方は -Z
        best = (None, None)
        for size in self.settings.keys():
            if self.settings[size]["opacity"] <= 0:
                continue
            hit, results = self.overlay.computeOverlayIntersection(self.handle[size], params)
            if hit and (best[1] is None or results.fDistance < best[1].fDistance):
                best = (size, results)
        return best

    def wakeOverlay(self, size: str) -> None:
        self.lastUpdate[size] = time.monotonic()
        self.fadeRatio[size] = 1.0
        self.overlay.setOverlayAlpha(self.handle[size], self.settings[size]["opacity"])

    def showPointer(self, results: Optional[Any], color: Sequence[float]) -> None:
        """レーザーの当たった位置に小さな点を表示する。results が None なら隠す。"""
        if self.pointer_handle is None:
            return
        if results is None:
            self.overlay.hideOverlay(self.pointer_handle)
            return
        normal = np.array([results.vNormal.v[i] for i in range(3)])
        point = np.array([results.vPoint.v[i] for i in range(3)]) + normal * 0.002
        up = np.array([0.0, 1.0, 0.0]) if abs(normal[1]) < 0.99 else np.array([1.0, 0.0, 0.0])
        x_axis = np.cross(up, normal)
        x_axis /= np.linalg.norm(x_axis)
        y_axis = np.cross(normal, x_axis)
        m = np.column_stack([x_axis, y_axis, normal, point])
        self.overlay.setOverlayTransformAbsolute(self.pointer_handle, openvr.TrackingUniverseStanding, mat34Id(m))
        self.overlay.setOverlayColor(self.pointer_handle, *color)
        self.overlay.showOverlay(self.pointer_handle)

    def setHighlight(self, size: Optional[str], color: Sequence[float]) -> None:
        """掴み対象のオーバーレイを色付けする。size が None なら全て元の色に戻す。"""
        for s in self.settings.keys():
            self.overlay.setOverlayColor(self.handle[s], *(color if s == size else _COLOR_NORMAL))

    def updateGrab(self) -> None:
        """グリップ長押しでオーバーレイを掴み、離したら位置を確定する。

        ポインタの色: 白=指している / 黄=グリップ長押し中 / 緑=掴んでいる。
        """
        # None を渡すと pyopenvr は配列を確保せず None を返すため、自前で確保して渡す
        poses = (openvr.TrackedDevicePose_t * openvr.k_unMaxTrackedDeviceCount)()
        self.overlay_system.getDeviceToAbsoluteTrackingPose(openvr.TrackingUniverseStanding, 0, poses)

        def poseOf(index: int) -> Optional[np.ndarray]:
            if index == openvr.k_unTrackedDeviceIndexInvalid or not poses[index].bPoseIsValid:
                return None
            m = poses[index].mDeviceToAbsoluteTracking
            return utils.toHomogeneous(np.array([[m[i][j] for j in range(4)] for i in range(3)]))

        def gripPressed(index: int) -> bool:
            ok, state = self.overlay_system.getControllerState(index)
            return bool(ok) and bool(state.ulButtonPressed & _GRIP_MASK)

        now = time.monotonic()

        if self.grabbing is not None:
            size, hand, hand_to_overlay = self.grabbing
            hand_pose = poseOf(hand)
            _, tracker_index = self.getTracker(self.settings[size]["tracker"])
            tracker_pose = poseOf(tracker_index)
            if hand_pose is None or tracker_pose is None:
                # トラッキングロスト(スリープ・電源断等)では離したことも検知できないため、
                # 掴みを解除して最後に表示していた位置で確定する。
                self.grabbing = None
                self.setHighlight(None, _COLOR_NORMAL)
                if self.grab_last_relative is not None:
                    self.commitPosition(size, self.grab_last_relative)
                return
            relative = np.linalg.inv(tracker_pose) @ hand_pose @ hand_to_overlay
            self.grab_last_relative = relative[:3, :]
            if gripPressed(hand):
                self.overlay.setOverlayTransformTrackedDeviceRelative(self.handle[size], tracker_index, mat34Id(relative[:3, :]))
                self.wakeOverlay(size)  # 掴んでいる間はフェードさせない
            else:
                self.grabbing = None
                self.setHighlight(None, _COLOR_NORMAL)
                self.commitPosition(size, relative[:3, :])
            return

        pointer = None  # (results, color)
        highlight = None  # (size, color)
        for role in (openvr.TrackedControllerRole_LeftHand, openvr.TrackedControllerRole_RightHand):
            hand = self.overlay_system.getTrackedDeviceIndexForControllerRole(role)
            hand_pose = poseOf(hand)
            grip = hand_pose is not None and gripPressed(hand)
            size, results = (None, None) if hand_pose is None else self.pointingOverlay(hand_pose)
            # 自分の手に付いているオーバーレイはその手では動かせない(手と一緒に動くだけ)
            if size is not None and self.getTracker(self.settings[size]["tracker"])[1] == hand:
                size, results = None, None

            state = (grip, size)
            if self.debug_state.get(hand) != state:
                self.debug_state[hand] = state
                printLog("overlay grab", {"hand": hand, "grip": grip, "hit": size})

            if size is None or not grip:
                if self.grab_candidate is not None and self.grab_candidate[1] == hand:
                    self.grab_candidate = None
                if size is not None and self.isVisible(size) and pointer is None:
                    pointer = (results, _COLOR_POINTER)
                continue

            self.wakeOverlay(size)  # フェード済みでもグリップで起こす
            if self.grab_candidate is None or self.grab_candidate[:2] != (size, hand):
                self.grab_candidate = (size, hand, now)
            pointer = (results, _COLOR_HOLDING)
            highlight = (size, _COLOR_HOLDING)
            if now - self.grab_candidate[2] >= _GRAB_HOLD_SEC:
                base_matrix, tracker_index = self.getTracker(self.settings[size]["tracker"])
                tracker_pose = poseOf(tracker_index)
                if tracker_pose is None:
                    continue
                s = self.settings[size]
                relative = utils.transform_matrix(
                    base_matrix,
                    (s["x_pos"], s["y_pos"], -s["z_pos"]),
                    (s["x_rotation"], s["y_rotation"], s["z_rotation"]),
                )
                overlay_pose = tracker_pose @ utils.toHomogeneous(relative)
                self.grabbing = (size, hand, np.linalg.inv(hand_pose) @ overlay_pose)
                self.grab_last_relative = None
                self.grab_candidate = None
                self.showPointer(None, _COLOR_NORMAL)
                self.setHighlight(size, _COLOR_GRABBING)
                return

        self.showPointer(*(pointer or (None, _COLOR_NORMAL)))
        self.setHighlight(*(highlight or (None, _COLOR_NORMAL)))

    def commitPosition(self, size: str, relative: np.ndarray) -> None:
        base_matrix, _ = self.getTracker(self.settings[size]["tracker"])
        keys = ("x_pos", "y_pos", "z_pos", "x_rotation", "y_rotation", "z_rotation")
        for key, value in zip(keys, utils.matrix_to_position(base_matrix, relative)):
            self.settings[size][key] = round(value, 4)
        if self.position_changed_callback is not None:
            try:
                self.position_changed_callback(size, {k: self.settings[size][k] for k in keys})
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
                self.updateGrab()
                self.grab_error = None
            except Exception as e:
                self.grabbing = None
                self.grab_candidate = None
                # 毎フレーム呼ばれるため、同じ例外が続く間はログを1回だけにする
                if repr(e) != self.grab_error:
                    self.grab_error = repr(e)
                    errorLogging()
            # 掴んでいる間は追従を滑らかにするため更新頻度を上げる
            interval = (1 / 60) if self.grabbing is not None else (1 / 16)
            sleepTime = interval - (time.monotonic() - startTime)
            if sleepTime > 0:
                time.sleep(sleepTime)

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
                if isinstance(self.pointer_handle, int):
                    self.overlay.destroyOverlay(self.pointer_handle)
                self.pointer_handle = None
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