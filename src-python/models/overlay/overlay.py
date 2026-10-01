import os
from functools import lru_cache
import ctypes
import sys
import time
import traceback
from psutil import process_iter
from threading import Lock, Thread, get_ident
from types import SimpleNamespace
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
# SteamVR の起動を待つ間隔と、その間に止められていないかを確かめる間隔
_STEAMVR_POLL_SEC = 10.0
_START_CANCEL_POLL_SEC = 0.5
# オーバーレイの処理がこの秒数進まなかったら、どこで止まっているかをログに出す (実機での切り分け用)
_STALL_REPORT_SEC = 2.0
# 各段階の処理時間の最大をこの秒数ごとに確かめ、遅い段階があればログに出す
_STEP_REPORT_SEC = 10.0
_STEP_SLOW_SEC = 0.05

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
# 掴んでいる間: その手のスティックの上下で手から遠ざける・近づける (XSOverlay と同じ)。
# 速さは今の距離 x この値 (/秒)。スティックは VRChat にも届く (奪えない) ので、倒し量が大きいときだけ動かす
_PUSH_PULL_SPEED = 1.0
_PUSH_PULL_DEADZONE = 0.5
_PUSH_PULL_DISTANCE_RANGE_M = (0.25, 2.5)
# 掴んで動かしている間の手の震えをならす。ゆっくり動かしているときだけ (速いときは遅れないようそのまま)
_GRAB_SMOOTH_TAU_SEC = 0.06
_GRAB_SMOOTH_MAX_SPEED_M = 0.3
# ランチャーを手首を見たときだけ出す (XSOverlay と同じ)。
# 出す: ランチャーの面が顔の方を向き (_LAUNCHER_FACE_DEG 以内)、視線からも近い (_LAUNCHER_GAZE_SHOW_DEG 以内) 状態が続いたら。
# 消す: 面の角度が _LAUNCHER_FACE_DEG + _LAUNCHER_HIDE_MARGIN_DEG を超えるか、視線から大きく外れた状態が続いたら。
# 会話中の身振りで出たり、境目で点滅したりしないよう、出す・消すで角度と待ち時間を変えている。
# 出るまでは短くする (手首を戻してから出るまでが長いと感じた。実機)
_LAUNCHER_FACE_DEG = 45.0
_LAUNCHER_GAZE_SHOW_DEG = 40.0
_LAUNCHER_GAZE_HIDE_DEG = 45.0
_LAUNCHER_HIDE_MARGIN_DEG = 10.0
_LAUNCHER_SHOW_AFTER_SEC = 0.05
_LAUNCHER_HIDE_AFTER_SEC = 0.3
_LAUNCHER_FADE_SEC = 0.1
_LAUNCHER_INPUT_DELAY_SEC = 0.2  # 出始めは押せない (手首を返した勢いで押さないように)
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
# ログウィンドウの下の操作バー (XSOverlay と同じ位置)。settings には入れない (位置はログに付いて動き、保存もしない)
TOOLBAR = "toolbar"
# ログウィンドウの大きさ (論理px)。角を掴んで伸ばせる範囲と既定
PANEL_DEFAULT_SIZE = (900, 700)
PANEL_SIZE_RANGE = ((600, 400), (1400, 1000))
# 大きさを変えたのに VR画面のウィンドウがその大きさにならないとき: この秒数で大きさの変更をやり直し、
# それでも合わなければ最後に表示できていた大きさへ戻す (ログが固まったままにならないように)
_LAYOUT_RETRY_SEC = 1.0
_LAYOUT_GIVE_UP_SEC = 3.0
# 角を掴む当たり判定 (ログの論理px)。角から内側・外側にこの幅。右上は閉じるボタンがあるので外側だけ
_CORNER_INSIDE_PX = 56
_CORNER_OUTSIDE_PX = 32
# 角の取っ手の中心の、ログの端からの距離 (src-ui/views/vr/VrWindow.module.scss の .resize_handle: 端から6px、56px角)
_CORNER_HANDLE_CENTER_PX = 34
# 伸ばしている間に出す枠の色 (RGBA)。最小・最大に達したら注意の色
_GHOST_COLOR = (0xB7, 0xDE, 0xD8, 255)
_GHOST_LIMIT_COLOR = (0xCB, 0x94, 0x4F, 255)
_GHOST_FILL = (0x61, 0xB4, 0xA7, 40)
# 点線の枠はログの面からこの距離だけ手前に出す (同じ面だと、どちらが前に描かれるかが揺れてちらつく)
_GHOST_FRONT_M = 0.004
# 点線の枠のテクスチャの大きさ (最大のログ 1400x1000 の 1/4 が入る)。大きさを変えずに一部だけ使う
_GHOST_TEXTURE_SIZE = (352, 256)


def computeVrLayout(width: int, height: int) -> Dict[str, Any]:
    """撮影するウィンドウ (VR画面) の大きさと各領域 (x, y, w, h)。論理px。

    ログ (左上) の大きさで変わり、ランチャーはログの下、一時ウィンドウと操作バーはログの右に並べる。
    VR画面 (React) はこの結果を受け取って描く。既定の大きさでは src-ui/views/vr/vr_layout.json と一致する
    (test_overlay_grab_move で確認)。
    """
    right_x = max(width, 900) + 8
    return {
        "atlas": (right_x + 720, max(height + 8 + 128, 656 + 96)),
        "regions": {
            PANEL: (0, 0, width, height),
            LAUNCHER: (10, height + 8, 880, 128),
            POPUP: (right_x, 0, 720, 640),
            TOOLBAR: (right_x, 656, 720, 96),
        },
    }


def clampPanelSize(width: float, height: float) -> tuple:
    (min_w, min_h), (max_w, max_h) = PANEL_SIZE_RANGE
    return (round(min(max(width, min_w), max_w)), round(min(max(height, min_h), max_h)))


DEFAULT_LAYOUT = computeVrLayout(*PANEL_DEFAULT_SIZE)
# ログを最大にしたときの並び。VR画面のテクスチャはこれが入る大きさで作る
MAX_LAYOUT = computeVrLayout(*PANEL_SIZE_RANGE[1])
VR_ATLAS_SIZE = DEFAULT_LAYOUT["atlas"]
VR_REGIONS = DEFAULT_LAYOUT["regions"]
# 一時ウィンドウを出す位置: ランチャーの中心から上へ、頭との水平距離をこの範囲に収める
_POPUP_ABOVE_LAUNCHER_M = 0.18
_POPUP_DISTANCE_RANGE_M = (0.45, 0.65)
# ログウィンドウが「見えない」とみなす範囲: 視線から外れた角度、または遠すぎる距離。
# 境界で頭が揺れてもランチャーのボタンが切り替わり続けないよう、戻るときは内側の値で判定する
_RECALL_OUT_OF_VIEW_DEG = (60.0, 50.0)  # (見えなくなる, 見えるようになる)
_RECALL_OUT_OF_VIEW_DISTANCE_M = (3.0, 2.7)
# 呼び戻す位置: 頭の正面 (水平方向) にこの距離、目の高さからこれだけ下
_RECALL_DISTANCE_M = 0.7
_RECALL_BELOW_EYE_M = 0.1
# 呼び戻す向きの上下の範囲 (度、上が正)。手首のランチャーを見下ろしながら呼び戻しても視線の先に出す
_RECALL_PITCH_RANGE_DEG = (-45.0, 20.0)
# 閉じているログを開くのと同時に呼び戻しを頼まれたとき (ランチャーの長押し)、開くのをこの秒数まで待つ
_RECALL_PENDING_SEC = 1.0
# 操作している間の撮影の間隔。ホバーやクリックの反応がこの分だけ遅れて見える
_PANEL_CAPTURE_INTERVAL_SEC = 1 / 20
# 操作していない間 (ポインタがVR UIに無く、画面が変わっていない) は撮影を減らす。
# 画面が変わってからこの秒数は、スクロールやホバーの動きを滑らかにするため元の間隔に戻す
_PANEL_IDLE_CAPTURE_INTERVAL_SEC = 1 / 4
_PANEL_ACTIVE_HOLD_SEC = 1.0
_PANEL_FIND_INTERVAL_SEC = 2.0
# コントローラの先端の向きが分からなかったとき、もう一度調べるまでの秒数 (それまでは本体の向きで指す)
_TIP_RETRY_SEC = 5.0
# レーザーの上下の向きの調整 (度)。コントローラの先端の向き (tipOffset) からこれだけ上に向ける。
# 負の値で下に向く。0 で先端の向きそのまま、Quest のコントローラでは 37.4 で本体の向き (直す前) と同じ
_LASER_PITCH_UP_DEG = 12


def laserTilt(degrees: float) -> np.ndarray:
    """先端の姿勢から、レーザーを上に degrees 度向ける回転 (先端の X 軸まわり)。"""
    angle = np.radians(degrees)
    tilt = np.eye(4)
    tilt[1, 1], tilt[1, 2] = np.cos(angle), -np.sin(angle)
    tilt[2, 1], tilt[2, 2] = np.sin(angle), np.cos(angle)
    return tilt
# VR画面の撮影・転送でこの回数続けて失敗したら、ログを埋めないよう撮影をやめる (1回の失敗ではやめない)
_PANEL_ERROR_LIMIT = 30
# 各領域の角丸の半径 (論理px)。撮影した画像の領域の外と四隅を透明にする
_PANEL_CORNER_RADIUS_PX = 24

# 追従先 "Playspace": SteamVRの空間 (プレイスペース) に固定する。VRChatのスティック移動や
# 回転はワールド側が動くので、空間に固定したオーバーレイはアバターと一緒についてくる
PLAYSPACE = "Playspace"
_PLAYSPACE_INDEX = -1
# ログウィンドウの固定先 (操作バーのボタンと同じ並び)
PANEL_ANCHORS = (PLAYSPACE, "LeftHand", "RightHand", "HMD")
# 操作バーの実際の大きさはログの拡大縮小によらず固定する (ランチャーと同じ。ボタン64pxで約28mm)
_TOOLBAR_M_PER_PX = 0.4 / 900
_TOOLBAR_GAP_M = 0.012
# ログか操作バーをこの秒数指し続けたら出し、外れてからこの秒数で消す
_TOOLBAR_SHOW_AFTER_SEC = 0.3
_TOOLBAR_HIDE_AFTER_SEC = 2.0
# 操作バーを出す・消すときに、この秒数で浮かび上がらせる・薄くして消す
_TOOLBAR_FADE_SEC = 0.25
# 固定先を手・頭に切り替えたとき、遠すぎる (近すぎる) ウィンドウを寄せる距離 (m)
_HAND_ANCHOR_MAX_DISTANCE_M = 0.5
_HMD_ANCHOR_DISTANCE_RANGE_M = (0.4, 1.5)
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


def regionRect(size: str, image_size: tuple, layout: Dict[str, Any] = DEFAULT_LAYOUT) -> tuple:
    """撮影した画像 (DPIで論理pxより大きいことがある) 上での領域 (x0, y0, x1, y1)。"""
    scale = image_size[0] / layout["atlas"][0]
    x, y, w, h = layout["regions"][size]
    return (round(x * scale), round(y * scale), round((x + w) * scale), round((y + h) * scale))


def regionBounds(size: str, layout: Dict[str, Any] = DEFAULT_LAYOUT) -> tuple:
    """setOverlayTextureBounds の (uMin, uMax, vMin, vMax)。

    OpenGLのテクスチャでは、画像の上から y 行目は v = 1 - y/H として扱われる
    (画像全体なら vMin=1, vMax=0 で正しい向きになることを実機で確認済み)。
    vMin が表示の上端、vMax が下端に対応する。
    """
    W, H = layout["atlas"]
    x, y, w, h = layout["regions"][size]
    return (x / W, (x + w) / W, 1 - y / H, 1 - (y + h) / H)


@lru_cache(maxsize=4)
def _atlasMask(image_size: tuple, atlas: tuple, regions: tuple) -> Image.Image:
    """各領域だけを角丸で残し、それ以外を透明にするマスク。"""
    layout = {"atlas": atlas, "regions": dict(regions)}
    scale = image_size[0] / atlas[0]
    mask = Image.new("L", image_size, 0)
    draw = ImageDraw.Draw(mask)
    for size in layout["regions"]:
        x0, y0, x1, y1 = regionRect(size, image_size, layout)
        draw.rounded_rectangle((x0, y0, x1 - 1, y1 - 1), radius=round(_PANEL_CORNER_RADIUS_PX * scale), fill=255)
    return mask


def atlasMaskArray(image_size: tuple, layout: Dict[str, Any] = DEFAULT_LAYOUT) -> np.ndarray:
    """各領域だけを角丸で残し、それ以外を透明にするマスク (高さ, 幅)。撮影画像のアルファにそのまま入れる。"""
    return _atlasMaskArray(image_size, layout["atlas"], tuple(sorted(layout["regions"].items())))


@lru_cache(maxsize=4)
def _atlasMaskArray(image_size: tuple, atlas: tuple, regions: tuple) -> np.ndarray:
    return np.asarray(_atlasMask(image_size, atlas, regions))


def rayPlaneHit(ray_pose: np.ndarray, plane_pose: np.ndarray) -> Optional[tuple]:
    """コントローラの前方 (-Z) へのレーザーと、オーバーレイの面との交点。

    戻り値: (面の中心から見た x, y (m), 交点 (空間座標), 距離)。当たらなければ None。
    OpenVR の当たり判定と違い、オーバーレイの外側や透明な角でも計算できる (角を掴むため)。
    """
    origin = ray_pose[:3, 3]
    direction = -ray_pose[:3, 2]
    normal = plane_pose[:3, 2]
    denom = float(np.dot(direction, normal))
    if abs(denom) < 1e-6:
        return None
    distance = float(np.dot(plane_pose[:3, 3] - origin, normal)) / denom
    if distance <= 0:
        return None
    point = origin + direction * distance
    local = np.linalg.inv(plane_pose) @ np.append(point, 1.0)
    return float(local[0]), float(local[1]), point, distance


def pointerHit(point: np.ndarray, normal: np.ndarray, distance: float) -> Any:
    """showPointer に渡せる、computeOverlayIntersection の結果と同じ形のもの。"""
    return SimpleNamespace(vPoint=SimpleNamespace(v=list(point)), vNormal=SimpleNamespace(v=list(normal)), fDistance=distance)


def createGhostImage(width: int, height: int, at_limit: bool) -> Image.Image:
    """角を掴んで伸ばしている間の枠 (縦横比は新しい大きさ、1/4 の解像度)。"""
    size = (max(round(width / 4), 8), max(round(height / 4), 8))
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle(
        (1, 1, size[0] - 2, size[1] - 2), radius=6, fill=_GHOST_FILL,
        outline=_GHOST_LIMIT_COLOR if at_limit else _GHOST_COLOR, width=3,
    )
    return img


def captureSize(capture: tuple) -> tuple:
    """撮影したクライアント領域の大きさ (物理px)。"""
    x0, y0, x1, y1 = capture[2]
    return (x1 - x0, y1 - y0)


def popupPoseFacing(position: np.ndarray, target: np.ndarray, up: Optional[np.ndarray] = None) -> np.ndarray:
    """position に置き、表 (+Z) を target に向けた姿勢。上は up (省略時はワールドの上 = 傾けない)。"""
    z = target - position
    z = z / (np.linalg.norm(z) or 1.0)
    up = np.array([0.0, 1.0, 0.0]) if up is None else up
    x = np.cross(up, z)
    if np.linalg.norm(x) < 1e-6:
        x = np.array([1.0, 0.0, 0.0])
    x = x / np.linalg.norm(x)
    y = np.cross(z, x)
    pose = np.eye(4)
    pose[:3, 0], pose[:3, 1], pose[:3, 2], pose[:3, 3] = x, y, z, position
    return pose


def faceHead(position: np.ndarray, head: np.ndarray) -> np.ndarray:
    """position に置き、表を頭へ向けた姿勢。上は頭の上 (見ている人にとって水平・垂直になる)。"""
    return popupPoseFacing(position, head[:3, 3], head[:3, 1])


def poseOnSphere(point: np.ndarray, head: np.ndarray, radius: float) -> np.ndarray:
    """目 (頭の位置) を中心とした半径 radius の球面上の、point の方向に置き、頭の方へ向けた姿勢。

    掴んで動かすウィンドウは手の向きでは回さず、いつもこの球面上で自分の方を向ける (XSOverlay と同じ)。
    """
    head_pos = head[:3, 3]
    direction = point - head_pos
    length = float(np.linalg.norm(direction))
    if length < 1e-6:
        direction, length = -head[:3, 2], 1.0
    return faceHead(head_pos + direction / length * radius, head)


def sphereRadius(base: float, hand_start: float, hand_now: float) -> float:
    """掴んでいる間の、目からウィンドウまでの距離。

    腕を前に伸ばす・手前に引くと、その割合で遠ざける・近づける (目から手までの距離の比)。
    base はスティックの上下で変わる距離 (pushPullDistance)。範囲の外にあるウィンドウは、掴んだ瞬間に
    範囲へ跳ばさず、範囲へ戻る向きにだけ動かせる (歩いて離れた遠くのウィンドウを掴んだときなど)。
    """
    low, high = _PUSH_PULL_DISTANCE_RANGE_M
    return min(max(base * hand_now / max(hand_start, 0.05), min(low, base)), max(high, base))


def isOutOfView(head: np.ndarray, position: np.ndarray, was_out: bool = False) -> bool:
    """position が頭の向き (-Z) から外れている、または遠すぎるか。

    was_out (前回の判定) が True なら、内側のしきい値まで戻ったときに初めて見えると判定する。
    """
    index = 1 if was_out else 0
    direction = position - head[:3, 3]
    distance = float(np.linalg.norm(direction))
    if distance > _RECALL_OUT_OF_VIEW_DISTANCE_M[index]:
        return True
    if distance < 1e-6:
        return False
    cos = float(np.dot(direction / distance, -head[:3, 2]))
    # numpy の bool_ のままだと UI への通知 (JSON) で失敗するので Python の bool にする
    return bool(cos < np.cos(np.radians(_RECALL_OUT_OF_VIEW_DEG[index])))


def recallPose(head: np.ndarray) -> np.ndarray:
    """視線の先 (上下は _RECALL_PITCH_RANGE_DEG の範囲) の少し下に置き、頭の方を向けた姿勢。

    上下の向きを無視して水平の正面に置くと、手首のランチャーを見下ろしながら呼び戻したとき
    視線から外れたままになり、何度押しても「呼び戻す」のままだった (実機)。
    """
    head_pos = head[:3, 3]
    gaze = -head[:3, 2]
    forward = gaze.copy()
    forward[1] = 0.0
    if np.linalg.norm(forward) < 1e-6:  # 真上・真下を向いているときは頭の上方向を正面にする
        forward = head[:3, 1].copy()
        forward[1] = 0.0
    forward = forward / (np.linalg.norm(forward) or 1.0)
    low, high = _RECALL_PITCH_RANGE_DEG
    pitch = np.radians(min(max(np.degrees(np.arcsin(np.clip(gaze[1], -1.0, 1.0))), low), high))
    direction = forward * np.cos(pitch) + np.array([0.0, np.sin(pitch), 0.0])
    position = head_pos + direction * _RECALL_DISTANCE_M - np.array([0.0, _RECALL_BELOW_EYE_M, 0.0])
    return faceHead(position, head)


def pushPullDistance(distance: float, state: Optional[Any], dt: float) -> float:
    """掴んでいる手のスティックの上下で、距離を伸ばす (上)・縮める (下)。

    縦にはっきり倒したときだけ動かす (横移動・回転に使う操作と区別するため)。
    範囲の外にあるときは、範囲へ戻る向きにだけ動かせる。
    """
    if state is None:
        return distance
    x, y = state.rAxis[0].x, state.rAxis[0].y
    if abs(y) < _PUSH_PULL_DEADZONE or abs(y) < 2 * abs(x):
        return distance
    low, high = _PUSH_PULL_DISTANCE_RANGE_M
    moved = distance * (1.0 + y * _PUSH_PULL_SPEED * dt)
    return min(moved, max(high, distance)) if y > 0 else max(moved, min(low, distance))


def pushPull(hand_to_overlay: np.ndarray, state: Optional[Any], dt: float) -> np.ndarray:
    """掴んでいる手のスティックの上下で、ウィンドウを手から遠ざける (上)・近づける (下)。"""
    offset = hand_to_overlay[:3, 3]
    distance = float(np.linalg.norm(offset))
    if distance < 1e-6:
        return hand_to_overlay
    result = hand_to_overlay.copy()
    result[:3, 3] = offset / distance * pushPullDistance(distance, state, dt)
    return result


def mirrorHandPosition(position: Dict[str, Any]) -> Dict[str, Any]:
    """手首に付けたウィンドウの位置を、反対の手用に左右反転する。

    左右の手の基準 (getLeftHandBaseMatrix / getRightHandBaseMatrix) は x を中心に鏡写しなので、
    位置の x と、y・z 軸まわりの回転の向きを反転すれば、反対の手の同じ場所に付く。
    """
    mirrored = dict(position)
    for key in ("x_pos", "y_rotation", "z_rotation"):
        mirrored[key] = -position[key]
    mirrored["tracker"] = "RightHand" if position["tracker"] == "LeftHand" else "LeftHand"
    return mirrored


def launcherLooksVisible(launcher: np.ndarray, head: np.ndarray, face_deg: float, gaze_deg: float) -> bool:
    """ランチャーの面 (+Z) が頭の方を向いていて (face_deg 以内)、視線からも gaze_deg 以内か。

    コントローラーの軸は機種で違うので、手ではなくランチャー自身の向きで判定する。
    """
    to_head = head[:3, 3] - launcher[:3, 3]
    distance = float(np.linalg.norm(to_head))
    if distance < 1e-6:
        return False
    to_head = to_head / distance
    face_cos = float(np.dot(launcher[:3, 2], to_head))
    gaze_cos = float(np.dot(-head[:3, 2], -to_head))
    return face_cos >= np.cos(np.radians(face_deg)) and gaze_cos >= np.cos(np.radians(gaze_deg))


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
        # SteamVR の起動を待っている間 (または作っている間) に止められた。起動しない
        # (以前は待っている間に OFF にしても、SteamVR が起動するとオーバーレイが出てきた)。
        # start_cancelled と init_process の読み書きは start_lock で直列にする
        self.start_cancelled = False
        self.start_lock = Lock()

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
        # 操作バー (VR画面の TOOLBAR 領域を表示するオーバーレイ)。指している間だけ出す
        self.toolbar_handle: Optional[int] = None
        self.toolbar_visible = False
        # 操作バーの今の濃さ (0〜1) と、最後に濃さを変えた時刻 (updateToolbarFade)
        self.toolbar_alpha = 0.0
        self.toolbar_faded_at: Optional[float] = None
        self.toolbar_pointed_since: Optional[float] = None
        self.toolbar_last_pointed = 0.0
        # 操作バーの置き場所 (追従先から見た 3x4) と追従先。当たった位置の計算に使う
        self.toolbar_relative: Optional[np.ndarray] = None
        self.toolbar_tracker_index: Optional[int] = None
        # 固定先の切り替えの要求 (操作バーから、どのスレッドからでもよい)。オーバーレイのスレッドで反映する
        self.requested_anchor: Optional[str] = None
        # ログウィンドウのロック (掴めない。スクロールと操作バーは使える)
        self.panel_locked = False
        # ランチャーを手首を見たときだけ出す (updateLauncherVisibility)。設定は Model が入れる
        self.launcher_auto_hide = True
        self.launcher_shown = True
        self.launcher_alpha = 1.0
        self.launcher_interactive = True
        self.launcher_change_since: Optional[float] = None
        self.launcher_shown_at = 0.0
        self.launcher_pointed = False
        self.launcher_prev_time: Optional[float] = None
        # grabbing: (size, 手のindex, 手から見たオーバーレイの4x4行列)
        self.grabbing: Optional[tuple] = None
        self.grab_last_relative: Optional[np.ndarray] = None
        # ポインタは種類ごとに別のオーバーレイにして表示を切り替える
        # (setOverlayRaw は約190回で失敗し続けるため、画像の差し替えはしない)
        self.pointer_handles: Dict[str, int] = {}
        # 掴み中の拡大縮小: (開始時の手の位置, 手の前方向, 開始時の幅, 固定したオーバーレイの姿勢)
        self.grab_scale: Optional[tuple] = None
        # 掴んでいる間: 前のフレームの時刻 (押し引き・ならしの経過時間) と、ならした後の位置 (追従先から見た 3x4)
        self.grab_prev_time: float = 0.0
        self.grab_smoothed: Optional[np.ndarray] = None
        self.grab_prev_target: Optional[np.ndarray] = None
        # 空間・頭に固定したウィンドウを掴んでいる間の、目からの距離 (球面の半径)。手に付けたものは None
        self.grab_radius: Optional[float] = None
        # 掴み始め (掴み直し) のときの、目から手までの距離。腕の前後で奥行きを変える基準
        self.grab_hand_distance = 1.0
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
        # コントローラごとの先端 (render model の "tip") の、本体の姿勢から見た姿勢と、調べ直す時刻 (tipOffset)
        self.tip_offsets: Dict[int, tuple] = {}
        # 撮影を頼んだ使い捨てのスレッドの結果 (startCaptureJob)。同時に頼むのは1つだけ
        self.capture_job: Optional[SimpleNamespace] = None
        # VR画面を撮り続ける画面キャプチャ (window_capture.WindowStream)。使えなければ PrintWindow で撮る
        self.panel_stream: Optional[Any] = None
        # stream_missing は windows-capture が無い (起動し直すまで戻らない)。stream_unavailable は始められない・
        # 止まった (撮り直しを繰り返さないよう、次に VR UI を ON にするまで PrintWindow で撮る)
        self.stream_missing = False
        self.stream_unavailable = False
        # 前回転送した撮影の生データと、画面が最後に変わった時刻。変わっていなければ転送しない
        self.panel_last_raw: Optional[bytes] = None
        self.panel_last_change: float = 0.0
        self.panel_image_size: Optional[tuple] = None
        # 撮影・転送の失敗が続いている回数と、最後に記録した失敗 (同じ失敗はログに1回だけ出す)
        self.panel_errors = 0
        self.panel_error: Optional[str] = None
        # SteamVR が OpenGL に残したエラーを見つけたことをログに出したか (1回だけ出す)
        self.gl_error_logged = False
        # 今の処理の段階とその開始時刻、段階ごとの処理時間の最大 (markStep。止まった・遅い段階をログに出す)
        self.loop_step: tuple = ("idle", time.monotonic())
        self.step_max: Dict[str, float] = {}
        self.step_reported_at = time.monotonic()
        # 撮影が続けて失敗したので撮影をやめた (OpenGL の環境は、接続を閉じるまで残す)
        self.panel_stopped = False
        # VR画面の並び (ログの大きさで変わる)。layout_applied は今のテクスチャと表示範囲 (bounds) が合っている並び。
        # 大きさを変えたら、VR画面のウィンドウを合わせ、新しい並びで撮れた最初のフレームで表示範囲を切り替える
        self.layout: Dict[str, Any] = computeVrLayout(*self.panelSize())
        self.layout_applied: Optional[Dict[str, Any]] = None
        self.window_fitted_layout: Optional[Dict[str, Any]] = None
        # 並びが変わったときに VR画面へ知らせる (並びを描くのは React)
        self.layout_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        # VR画面が描き終えた並びのログの大きさ (VR画面から届く)。これと撮影の縦横比が合ってから表示を切り替える。
        # 並びはログの大きさだけで決まる (全体の大きさは同じでもログの大きさが違うことがあるので、ログの大きさで見る)
        self.layout_rendered: Optional[tuple] = PANEL_DEFAULT_SIZE  # VR画面は起動時に既定の並びで描く
        self.layout_requested_at = 0.0
        self.layout_retried = False
        # VR画面のウィンドウを合わせた大きさ (物理px。resizeClient の結果)。撮影がこの大きさになってから表示を切り替える
        self.window_size: Optional[tuple] = None
        # 大きさの切り替えの各段階を、並びごとに1回だけログに出す (実機での切り分け用)
        self.layout_logged: set = set()
        # 伸ばして放したときの、伸ばす前の位置と幅。新しい大きさにできず元に戻すときに使う
        self.resize_undo: Optional[Dict[str, Any]] = None
        # 角を掴んで大きさを変えている間の状態 (startResize)。手ごとに前のフレームで指していた角
        self.resizing: Optional[Dict[str, Any]] = None
        self.corner_prev: Dict[int, Optional[tuple]] = {}
        # 伸ばしている間に出す枠のオーバーレイと、今の枠の画像の (幅/4, 高さ/4, 限界か)
        self.ghost_handle: Optional[int] = None
        self.ghost_key: Optional[tuple] = None
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
        # 起動時はランチャーだけ (VR画面の初期状態と同じ。VR画面から届くまでログを出さない)
        self.vr_windows_wanted: Dict[str, bool] = {PANEL: False, POPUP: False}
        self.vr_windows_hidden: set = set()
        # VR UI 全体のON/OFF (設定 OVERLAY_VR_PANEL)。OFFの間はランチャーも含めて隠し、撮影しない。
        # 字幕のオーバーレイだけが動いているときに False になる
        self.vr_panel_enabled = True
        # ログウィンドウを見失ったとき用。VR画面が呼び戻しを頼む (どのスレッドからでもよい) と、
        # オーバーレイのスレッドが頭の正面へ置き直す。見えなくなった・見えるようになったときに
        # panel_out_of_view_callback(bool) で知らせ、ランチャーのボタンを「呼び戻す」に変える
        # 呼び戻しを頼まれた時刻 (頼まれていなければ None)
        self.vr_recall_requested: Optional[float] = None
        self.panel_out_of_view = False
        self.panel_out_of_view_callback: Optional[Callable[[bool], None]] = None
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
            self.tip_offsets = {}
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
                self.toolbar_handle = self.overlay.createOverlay("VRCT_toolbar", "VRCT_toolbar")
                self.overlay.setOverlayWidthInMeters(self.toolbar_handle, self.regionWidthM(TOOLBAR))
                self.overlay.hideOverlay(self.toolbar_handle)
                self.toolbar_visible = False
                self.toolbar_alpha, self.toolbar_faded_at = 0.0, None
                self.ghost_handle = self.overlay.createOverlay("VRCT_resize_ghost", "VRCT_resize_ghost")
                self.overlay.setOverlaySortOrder(self.ghost_handle, 50)
                self.overlay.hideOverlay(self.ghost_handle)
                self.ghost_key = None
            if any(size in self.settings for size in VR_REGIONS):
                try:
                    self.initPanelTexture()
                except Exception:
                    self.shutdownPanelTexture()
                    errorLogging()

            # 手首を見たときだけ出すなら、見るまでは出さない (起動直後に一度出てから消えないように)
            self.launcher_shown = not self.launcher_auto_hide
            self.launcher_alpha = 1.0 if self.launcher_shown else 0.0
            self.launcher_interactive = self.launcher_shown
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
            printLog("overlay: 起動しました", {"vr_panel": self.gl is not None})
        except Exception:
            errorLogging()
        finally:
            # 途中で失敗しても「作っている途中」のままにしない (以後 OFF/ON できなくなる)
            self.init_process = False

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
        ghost_texture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, ghost_texture)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA8, *_GHOST_TEXTURE_SIZE, 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, None)
        ghost_vr_texture = openvr.Texture_t()
        ghost_vr_texture.handle = int(ghost_texture)
        ghost_vr_texture.eType = openvr.TextureType_OpenGL
        ghost_vr_texture.eColorSpace = openvr.ColorSpace_Auto
        self.gl = {
            "glfw": glfw, "GL": GL, "window": window, "texture": texture, "vr_texture": vr_texture, "size": None,
            "ghost_texture": ghost_texture, "ghost_vr_texture": ghost_vr_texture,
            # 大きさが変わって使わなくなったテクスチャ。SteamVR が覚えているかもしれないので、接続を閉じた後に消す
            "old_textures": [],
        }
        self.panel_last_raw = None  # 作り直したテクスチャには必ず転送する
        self.panel_stopped = False
        self.layout_applied = None  # 最初に撮れたフレームで表示範囲を設定する
        self.window_fitted_layout = None
        # 大きさを合わせるのを待つ時間は、撮影を始めたときから測る (起動直後に元の大きさへ戻さないように)
        self.layout_requested_at = time.monotonic()
        self.layout_retried = False
        self.layout_logged = set()  # 作り直したら、大きさを合わせる各段階をもう一度ログに出す
        self.capture_job = None  # 止める前に頼んだ撮影の結果は使わない
        self.closePanelStream()
        self.stream_unavailable = False

    def panelSize(self) -> tuple:
        """ログウィンドウの大きさ (論理px)。"""
        s = self.settings.get(PANEL, {})
        return clampPanelSize(s.get("width", PANEL_DEFAULT_SIZE[0]), s.get("height", PANEL_DEFAULT_SIZE[1]))

    def setLayoutRendered(self, panel_size: Sequence[int]) -> None:
        """VR画面が描き終えた並びのログの大きさ [幅, 高さ] を受け取る (どのスレッドからでもよい)。"""
        self.layout_rendered = tuple(panel_size)

    def setPanelSize(self, width: float, height: float) -> None:
        """ログウィンドウの大きさを変える。VR画面の並びを変え、新しい並びで撮れたら表示を切り替える。"""
        width, height = clampPanelSize(width, height)
        if PANEL in self.settings:
            self.settings[PANEL]["width"], self.settings[PANEL]["height"] = width, height
        layout = computeVrLayout(width, height)
        if layout == self.layout:
            return
        self.layout = layout
        self.panel_last_raw = None
        self.layout_requested_at = time.monotonic()
        self.layout_retried = False
        self.layout_logged = set()
        if self.layout_callback is not None:
            try:
                self.layout_callback(layout)
            except Exception:
                errorLogging()

    def logLayout(self, event: str, data: Dict[str, Any]) -> None:
        """大きさの切り替えの段階を、今の並びにつき1回だけログに出す (実機での切り分け用)。"""
        if event in self.layout_logged:
            return
        self.layout_logged.add(event)
        printLog(f"overlay layout: {event}", {"atlas": self.layout["atlas"], **data})

    def retryOrRevertLayout(self, now: float) -> None:
        """新しい並びで撮れないまま時間が経ったら、大きさの変更をやり直し、それでもだめなら元に戻す。"""
        if self.layout_applied is self.layout:
            return
        waited = now - self.layout_requested_at
        if waited >= _LAYOUT_GIVE_UP_SEC:
            fallback = self.layout_applied["regions"][PANEL][2:] if self.layout_applied is not None else PANEL_DEFAULT_SIZE
            printLog("overlay: VR画面が新しい大きさにならないので元に戻します", {"wanted": self.layout["atlas"], "back_to": fallback})
            if self.resize_undo is not None:
                # 伸ばす前の位置と幅に戻す (伸ばした後の位置のままだと、元の大きさで跳んで見える)
                self.settings[PANEL].update(self.resize_undo)
                self.resize_undo = None
            elif PANEL in self.settings and "ui_scaling" in self.settings[PANEL]:
                # 1px の長さは変えない
                self.settings[PANEL]["ui_scaling"] *= fallback[0] / self.layout["regions"][PANEL][2]
            self.setPanelSize(*fallback)
            self.layout_requested_at = now + 3600  # 戻した大きさでも合わなければ、もう繰り返さない
            if PANEL in self.settings and "x_pos" in self.settings[PANEL]:
                self.notifyPosition(PANEL)
        elif waited >= _LAYOUT_RETRY_SEC and not self.layout_retried:
            self.layout_retried = True
            self.window_fitted_layout = None

    def applyLayout(self) -> None:
        """今の並びに合わせて、各領域の表示範囲 (bounds) とログの大きさ・位置をオーバーレイに反映する。"""
        # 撮影画像はテクスチャの左上の一部 (newPanelTexture)。その割合で表示範囲を縮める
        fu, fv = 1.0, 1.0
        if self.gl is not None and self.gl.get("size") and self.panel_image_size is not None:
            fu = self.panel_image_size[0] / self.gl["size"][0]
            fv = self.panel_image_size[1] / self.gl["size"][1]
        for size, handle in self.vrRegionHandles().items():
            u_min, u_max, v_min, v_max = regionBounds(size, self.layout)
            bounds = openvr.VRTextureBounds_t()
            bounds.uMin, bounds.uMax = u_min * fu, u_max * fu
            bounds.vMin, bounds.vMax = 1 - (1 - v_min) * fv, 1 - (1 - v_max) * fv
            self.overlay.setOverlayTextureBounds(handle, bounds)
        if self.initialized is True and PANEL in self.settings:
            s = self.settings[PANEL]
            self.updateUiScaling(s["ui_scaling"], PANEL)
            self.updatePosition(s["x_pos"], s["y_pos"], s["z_pos"], s["x_rotation"], s["y_rotation"], s["z_rotation"], s["tracker"], PANEL)
        self.layout_applied = self.layout
        self.resize_undo = None
        self.logLayout("applied", {
            "image": self.panel_image_size,
            "texture": None if self.gl is None else self.gl.get("texture"),
            "ui_scaling": self.settings.get(PANEL, {}).get("ui_scaling"),
        })
        if self.resizing is None:
            self.hideResizeGhost()

    def vrRegionSizes(self) -> list:
        return [size for size in VR_REGIONS if size in self.settings]

    def vrRegionHandles(self) -> Dict[str, int]:
        """VR画面の領域ごとのオーバーレイ (操作バーを含む)。"""
        handles = {size: self.handle[size] for size in self.vrRegionSizes()}
        if self.toolbar_handle is not None:
            handles[TOOLBAR] = self.toolbar_handle
        return handles

    def prepareGl(self) -> Any:
        """OpenGL を使う前に、このスレッドのコンテキストを確かにし、前から残っているエラーを捨てる。

        SteamVR にテクスチャを渡す処理 (setOverlayTexture) はこちらのコンテキストで OpenGL を使うが、
        そのエラーは確かめないので、残ったエラーが次の自分の処理のエラーとして見つかってしまう
        (実機で、テクスチャを選ぶだけの glBindTexture が GL_INVALID_VALUE になった)。
        """
        GL = self.gl["GL"]
        glfw = self.gl.get("glfw")
        if glfw is not None:
            glfw.make_context_current(self.gl["window"])
        left = []
        for _ in range(8):
            error = GL.glGetError()
            if error == GL.GL_NO_ERROR:
                break
            left.append(error)
        if left and not self.gl_error_logged:
            self.gl_error_logged = True
            printLog("overlay: OpenGL に前の処理のエラーが残っていたので捨てました", {"errors": [str(e) for e in left]})
        return GL

    def shutdownPanelTexture(self) -> None:
        if self.gl is None:
            return
        # SteamVR にテクスチャを渡したまま OpenGL の環境を消すと、後で SteamVR との接続を閉じるときに
        # 落ちる (実機で access violation)。先にオーバーレイからテクスチャを外す
        if self.overlay is not None:
            try:
                handles = [*self.vrRegionHandles().values(), *([self.ghost_handle] if self.ghost_handle is not None else [])]
                for handle in handles:
                    self.overlay.clearOverlayTexture(handle)
            except Exception:
                errorLogging()
        try:
            if self.gl.get("old_textures"):
                self.gl["GL"].glDeleteTextures(self.gl["old_textures"])
            self.gl["glfw"].destroy_window(self.gl["window"])
            self.gl["glfw"].terminate()
        except Exception:
            errorLogging()
        self.gl = None

    def updatePanel(self) -> None:
        """VRパネルのウィンドウを撮影してオーバーレイへ転送する。"""
        now = time.monotonic()
        if not self.vr_panel_enabled or self.gl is None or self.panel_stopped:
            return
        self.markStep("panel:capture")
        capture = self.collectCapture(now)
        if capture is None:
            return
        self.transferCapture(capture, now)
        # 撮れた結果を最後まで処理できた (撮影を別スレッドにしたので、撮っている途中の周では数え直さない)
        self.panel_errors = 0

    def transferCapture(self, capture: tuple, now: float) -> None:
        """撮影した結果を確かめ、変わっていればテクスチャに書いてオーバーレイへ渡す。"""
        # 大きさを変えている途中 (ウィンドウがまだ新しい大きさでない、または VR画面がまだ古い並びで描いている)
        # のフレームは使わない。やり直し・元に戻すのはウィンドウの大きさが合わないときだけ
        # (VR画面の描き終わりは必ず届くので待つ。起動直後は設定が届くまで既定の並びで描いている)
        window_fits = captureSize(capture) == self.window_size
        if not window_fits:
            self.logLayout("window size differs", {"capture": captureSize(capture), "target": self.window_size})
        elif self.layout_rendered != self.layout["regions"][PANEL][2:]:
            self.logLayout("waiting for render", {"rendered": self.layout_rendered})
        if not window_fits or self.layout_rendered != self.layout["regions"][PANEL][2:]:
            if not window_fits and self.layout_applied is self.layout:
                self.window_fitted_layout = None  # 表示中に大きさが変わった (DPIの変更など): 合わせ直す
            elif not window_fits:
                self.retryOrRevertLayout(now)
            return
        # 前回と同じなら、変換・転送をすべて省く (オーバーレイは前回のテクスチャを表示し続ける)
        if capture[0] == self.panel_last_raw:
            return
        self.panel_last_raw = capture[0]
        self.panel_last_change = now
        self.markStep("panel:convert")
        pixels = window_capture.bgraFromCapture(capture)
        size = (pixels.shape[1], pixels.shape[0])
        # 各領域だけを角丸で残し、それ以外は透明にする (PrintWindow のアルファは不定)
        pixels[..., 3] = atlasMaskArray(size, self.layout)
        GL = self.prepareGl()
        texture_size = self.gl["size"]
        if texture_size is None or size[0] > texture_size[0] or size[1] > texture_size[1]:
            # 最大の並びが入る大きさで作る (撮影は論理px x DPI倍率の大きさ)。以後は大きさを変えない
            scale = size[0] / self.layout["atlas"][0]
            max_w, max_h = MAX_LAYOUT["atlas"]
            self.newPanelTexture(GL, (max(round(max_w * scale), size[0]), max(round(max_h * scale), size[1])))
        # setOverlayTexture の後はバインドが外れるため、毎回バインドし直す。撮影画像はテクスチャの左上に BGRA のまま書く
        self.markStep("panel:upload")
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.gl["texture"])
        GL.glTexSubImage2D(GL.GL_TEXTURE_2D, 0, 0, 0, size[0], size[1], GL.GL_BGRA, GL.GL_UNSIGNED_BYTE, pixels)
        GL.glFinish()
        self.markStep("panel:set_texture")
        # 1枚のテクスチャを全領域のオーバーレイに渡す。表示される範囲は各オーバーレイの bounds で決まる
        for handle in self.vrRegionHandles().values():
            self.overlay.setOverlayTexture(handle, self.gl["vr_texture"])
        image_size_changed = size != self.panel_image_size
        self.panel_image_size = size
        # 表示範囲はテクスチャの中の撮影画像の大きさで決まるので、並びか撮影の大きさが変わったら当て直す
        if self.layout_applied is not self.layout or image_size_changed:
            self.applyLayout()

    def collectCapture(self, now: float) -> Optional[tuple]:
        """撮影を使い捨てのスレッドに頼み、撮れていればその結果 (captureWindowRaw) を返す。まだなら None。

        PrintWindow は VRCT の画面 (Tauri の UI スレッド) が描き終えるまで戻らず、画面が固まると
        数秒待たされる (実機で 7.5 秒)。ここで待つとレーザーや掴んだウィンドウも止まるので、撮影だけを
        別のスレッドで行う。状態を書き換えるのはこのスレッドだけで、撮影のスレッドは結果を job に入れるだけ。
        """
        job = self.capture_job
        started_now = job is None
        if started_now:
            self.startCapture(now)
            job = self.capture_job
            if job is None or not job.done:
                return None
        elif not job.done:
            if not job.reported and now - job.started >= _STALL_REPORT_SEC:
                job.reported = True
                printLog("overlay: VR画面の撮影に時間がかかっています (VRCT の画面が応答していない可能性)", {"sec": round(now - job.started, 1)})
            return None
        self.capture_job = None
        if job.reported:
            returned = time.monotonic()
            printLog("overlay: VR画面の撮影が戻りました", {"sec": round(returned - job.started, 1)})
            # 大きさを合わせる待ち時間は、戻ったときから数え直す (固まっている間に大きさを変えても、
            # 戻った直後に元の大きさへ戻さないように)。もう繰り返さない印 (now + 3600) は残す
            self.layout_requested_at = max(self.layout_requested_at, returned)
        if job.error is not None:
            raise job.error
        if not started_now:
            self.startCapture(now)  # 次の撮影をすぐ頼む (結果を受け取るだけで1周使わない)
        if job.layout is not self.layout:
            return None  # 撮っている間に並びが変わった。次の撮影を待つ
        if job.result is None:
            self.logLayout("no capture", {})
        return job.result

    def startCapture(self, now: float) -> None:
        """撮影の間隔が過ぎていれば、ウィンドウを探して大きさを合わせ、撮影を頼む。"""
        if now - self.panel_last_capture < self.panelCaptureInterval(now):
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
            self.window_fitted_layout = None  # 見つけ直したウィンドウは既定の大きさで作られている
        # VR画面のウィンドウの大きさを並びに合わせる (ログの大きさを変えたとき・起動したとき)
        if self.window_fitted_layout is not self.layout:
            self.window_size = window_capture.resizeClient(self.panel_hwnd, *self.layout["atlas"])
            self.window_fitted_layout = self.layout
            self.logLayout("resize", {"target": self.window_size})
        stream = self.panelStream()
        if stream is not None:
            # 画面キャプチャは撮り続けているので、届いている最新の画像を受け取るだけ (待たない)
            result = stream.take()
            if result is not None:
                self.capture_job = SimpleNamespace(hwnd=self.panel_hwnd, layout=self.layout, started=now,
                                                   done=True, result=result, error=None, reported=False)
                return
            if not stream.stale:
                return  # まだ1枚も届いていない
            # 大きさを変えた後の画像がまだ届かない: 届くまでは PrintWindow で撮る
        self.capture_job = SimpleNamespace(hwnd=self.panel_hwnd, layout=self.layout, started=now,
                                           done=False, result=None, error=None, reported=False)
        self.startCaptureJob(self.capture_job)

    def panelStream(self) -> Optional[Any]:
        """VR画面のウィンドウを撮り続ける画面キャプチャ。使えなければ None (PrintWindow で撮る)。"""
        if self.stream_missing or self.stream_unavailable:
            return None
        stream = self.panel_stream
        if stream is not None and stream.hwnd == self.panel_hwnd and not stream.closed:
            return stream
        if stream is not None and stream.hwnd == self.panel_hwnd:
            # 同じウィンドウなのに止まった: 撮り直しを繰り返さず PrintWindow に切り替える
            printLog("overlay: 画面キャプチャが止まったので PrintWindow で撮ります")
            self.stream_unavailable = True
            self.closePanelStream()
            return None
        self.closePanelStream()  # ウィンドウが作り直された
        try:
            self.panel_stream = window_capture.WindowStream(self.panel_hwnd)
        except ImportError:
            printLog("overlay: windows-capture が無いので PrintWindow で撮ります")
            self.stream_missing = True
            return None
        except Exception:
            errorLogging()
            printLog("overlay: 画面キャプチャを始められないので PrintWindow で撮ります")
            self.stream_unavailable = True
            return None
        return self.panel_stream

    def closePanelStream(self) -> None:
        stream, self.panel_stream = self.panel_stream, None
        if stream is not None:
            try:
                stream.close()
            except Exception:
                errorLogging()

    def startCaptureJob(self, job: SimpleNamespace) -> None:
        # ponytail: 1回ごとにスレッドを作る (撮影は最大20回/秒)。固まったまま OFF/ON すると1つずつ残るが、戻れば終わる
        Thread(target=self.runCaptureJob, args=(job,), daemon=True).start()

    @staticmethod
    def runCaptureJob(job: SimpleNamespace) -> None:
        """撮影のスレッド。Overlay の状態には触れず、結果を job に入れるだけ。"""
        try:
            job.result = window_capture.captureWindowRaw(job.hwnd)
        except Exception as e:
            job.error = e
        job.done = True

    def newPanelTexture(self, GL: Any, size: tuple) -> None:
        """VR画面のテクスチャの大きさを決める (中身は後で左上に書く)。

        SteamVR は最初に渡されたテクスチャの大きさのまま受け取り続け、大きさの違うテクスチャを渡すと
        OpenGL のエラーを残して前の画像を映し続けた (実機で、ログを縮めると前の大きな画像の一部が
        新しい表示範囲で切り出され、見切れた。同じ名前で大きさを変えても、別の名前にしても同じ)。
        そのため最大の並びが入る大きさで1回だけ作り、表示範囲 (bounds) で使う部分を決める。
        最初の1回は initPanelTexture で作ったものをそのまま使う。DPI が上がって入らなくなったときだけ作り直すが、
        上の制約のため SteamVR は新しい大きさを受け取れず、表示が見切れることがある (VR UI を OFF/ON するか、
        アプリを起動し直すと直る)。DPI の変更はまれなので、それ以上の対応はしない。
        """
        if self.gl["size"] is not None:
            printLog("overlay: VR画面のテクスチャを大きくします (表示が見切れたら VR UI を OFF/ON してください)", {"from": self.gl["size"], "to": size})
            # 古いテクスチャは SteamVR が持っているかもしれないので、接続を閉じた後に消す
            self.gl.setdefault("old_textures", []).append(self.gl["texture"])
            texture = GL.glGenTextures(1)
            GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
            self.gl["texture"] = texture
            self.gl["vr_texture"].handle = int(texture)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.gl["texture"])
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA8, size[0], size[1], 0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, None)
        self.gl["size"] = size

    def panelCaptureInterval(self, now: float) -> float:
        """撮影の間隔。ポインタがVR UIにあるか、画面が変わった直後は短く、それ以外は長くする。"""
        is_active = (
            self.pointer_notified is not None
            or self.grabbing is not None
            or self.resizing is not None
            or now - self.panel_last_change < _PANEL_ACTIVE_HOLD_SEC
        )
        return _PANEL_CAPTURE_INTERVAL_SEC if is_active else _PANEL_IDLE_CAPTURE_INTERVAL_SEC

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
                    # 押したまま戻ってきても押し直したことにしない (長押しが何度も起きないように)
                    self.trigger_blocked.add(hand)
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
        if size == PANEL and self.toolbar_handle is not None:
            self.placeToolbar(tracker_index, relative)

    def placeToolbar(self, tracker_index: int, panel_relative: np.ndarray) -> None:
        """操作バーをログの下に置く。出すのは指している間だけ (updateToolbarVisibility)。"""
        _, _, panel_w, panel_h = self.layout["regions"][PANEL]
        _, _, bar_w, bar_h = self.layout["regions"][TOOLBAR]
        panel_height_m = self.settings[PANEL]["ui_scaling"] * panel_h / panel_w
        bar_height_m = self.regionWidthM(TOOLBAR) * bar_h / bar_w
        offset = np.eye(4)
        offset[1][3] = -(panel_height_m / 2 + _TOOLBAR_GAP_M + bar_height_m / 2)
        self.toolbar_relative = (utils.toHomogeneous(panel_relative) @ offset)[:3, :]
        self.toolbar_tracker_index = tracker_index
        if not self.toolbar_visible:
            return
        if tracker_index == _PLAYSPACE_INDEX:
            self.overlay.setOverlayTransformAbsolute(self.toolbar_handle, openvr.TrackingUniverseStanding, mat34Id(self.toolbar_relative))
        else:
            self.overlay.setOverlayTransformTrackedDeviceRelative(self.toolbar_handle, tracker_index, mat34Id(self.toolbar_relative))

    def panelRelative(self) -> np.ndarray:
        """今のログの位置 (追従先から見た 3x4)。"""
        s = self.settings[PANEL]
        base_matrix, _ = self.getTracker(s["tracker"])
        return utils.transform_matrix(base_matrix, (s["x_pos"], s["y_pos"], -s["z_pos"]), (s["x_rotation"], s["y_rotation"], s["z_rotation"]))

    def setToolbarVisible(self, visible: bool) -> None:
        if self.toolbar_handle is None or visible == self.toolbar_visible:
            return
        if visible and PANEL in self.position_pending:
            return
        self.toolbar_visible = visible
        if visible:
            self.placeToolbar(self.getTracker(self.settings[PANEL]["tracker"])[1], self.panelRelative())
            self.overlay.setOverlayAlpha(self.toolbar_handle, self.toolbar_alpha)  # 今の濃さから浮かび上がらせる
            self.overlay.showOverlay(self.toolbar_handle)
        # 消すときは updateToolbarFade で薄くしてから隠す (突然消えないように)

    def updateToolbarFade(self, now: float) -> None:
        """操作バーの濃さを、出す・消すに合わせて _TOOLBAR_FADE_SEC かけて変える。薄くなりきったら隠す。"""
        if self.toolbar_handle is None:
            return
        dt = 0.0 if self.toolbar_faded_at is None else now - self.toolbar_faded_at
        self.toolbar_faded_at = now
        target = 1.0 if self.toolbar_visible else 0.0
        if self.toolbar_alpha == target:
            return
        step = dt / _TOOLBAR_FADE_SEC
        self.toolbar_alpha = min(self.toolbar_alpha + step, target) if target > self.toolbar_alpha else max(self.toolbar_alpha - step, target)
        self.overlay.setOverlayAlpha(self.toolbar_handle, self.toolbar_alpha)
        if self.toolbar_alpha == 0.0 and target == 0.0:
            self.overlay.hideOverlay(self.toolbar_handle)

    def hideToolbarNow(self) -> None:
        """ログと一緒に消すときは薄くせずにすぐ隠す。"""
        self.setToolbarVisible(False)
        if self.toolbar_handle is not None and self.toolbar_alpha > 0.0:
            self.toolbar_alpha = 0.0
            self.overlay.hideOverlay(self.toolbar_handle)

    def updateToolbarVisibility(self, now: float, pointing_log: bool) -> None:
        """ログか操作バーを少し指し続けたら操作バーを出し、外れてしばらくしたら消す。"""
        if PANEL in self.vr_windows_hidden or not self.vr_panel_enabled:
            self.toolbar_pointed_since = None
            self.hideToolbarNow()
            return
        if pointing_log:
            if self.toolbar_pointed_since is None:
                self.toolbar_pointed_since = now
            self.toolbar_last_pointed = now
            if now - self.toolbar_pointed_since >= _TOOLBAR_SHOW_AFTER_SEC:
                self.setToolbarVisible(True)
        else:
            self.toolbar_pointed_since = None
            if now - self.toolbar_last_pointed >= _TOOLBAR_HIDE_AFTER_SEC:
                self.setToolbarVisible(False)

    def regionWidthM(self, size: str) -> float:
        """VR画面の領域のオーバーレイの横幅 (m)。操作バーはログの大きさによらず固定。"""
        if size == TOOLBAR:
            return VR_REGIONS[TOOLBAR][2] * _TOOLBAR_M_PER_PX
        return self.settings[size]["ui_scaling"]

    def regionWorldPose(self, size: str, poseOf: Callable[[int], Optional[np.ndarray]]) -> Optional[np.ndarray]:
        """VR画面の領域のオーバーレイの今の姿勢。操作バーはログに付いて動く。"""
        if size != TOOLBAR:
            return self.overlayWorldPose(size, poseOf)
        if self.toolbar_relative is None:
            return None
        tracker_pose = poseOf(self.toolbar_tracker_index)
        return None if tracker_pose is None else tracker_pose @ utils.toHomogeneous(self.toolbar_relative)

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
        _, _, region_w, region_h = self.layout["regions"][size]
        width_m = self.regionWidthM(size)
        height_m = width_m * region_h / region_w
        fx = min(max(local[0] / width_m + 0.5, 0.0), 1.0)
        fy = min(max(0.5 - local[1] / height_m, 0.0), 1.0)
        x0, y0, x1, y1 = regionRect(size, self.panel_image_size, self.layout)
        return (min(x0 + int(fx * (x1 - x0)), x1 - 1), min(y0 + int(fy * (y1 - y0)), y1 - 1))

    def requestAnchor(self, anchor: str) -> None:
        """ログの固定先の切り替えを頼む (どのスレッドからでもよい)。"""
        if anchor in PANEL_ANCHORS:
            self.requested_anchor = anchor

    def setAnchor(self, poseOf: Callable[[int], Optional[np.ndarray]], anchor: str) -> None:
        """ログの固定先を切り替える。見えている場所からは動かさない。

        手に付けるときに手から遠すぎれば手元へ、頭に付けるときは近すぎ・遠すぎを適度な距離へ寄せる
        (遠くのウィンドウを手に付けると、手首を少しひねるだけで大きく振れるため)。
        """
        s = self.settings[PANEL]
        _, new_index = self.getTracker(anchor)
        new_pose = poseOf(new_index)
        world = self.overlayWorldPose(PANEL, poseOf)
        if world is None or new_pose is None:
            # 追従先が見つからない (コントローラが未接続など)。UI は切り替わった表示になっているので戻す
            self.notifyPosition(PANEL)
            return
        new_relative = np.linalg.inv(new_pose) @ world
        offset = new_relative[:3, 3].copy()
        distance = float(np.linalg.norm(offset))
        if anchor in ("LeftHand", "RightHand"):
            low, high = 0.0, _HAND_ANCHOR_MAX_DISTANCE_M
        elif anchor == "HMD":
            low, high = _HMD_ANCHOR_DISTANCE_RANGE_M
        else:
            low, high = 0.0, float("inf")
        if distance > 1e-6 and not low <= distance <= high:
            new_relative[:3, 3] = offset / distance * min(max(distance, low), high)
        s["tracker"] = anchor
        self.commitPosition(PANEL, new_relative[:3, :])
        self.updatePosition(s["x_pos"], s["y_pos"], s["z_pos"], s["x_rotation"], s["y_rotation"], s["z_rotation"], anchor, PANEL)

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
        if self.toolbar_handle is None or not self.toolbar_visible:
            return None
        params = openvr.VROverlayIntersectionParams_t()
        params.eOrigin = openvr.TrackingUniverseStanding
        for i in range(3):
            params.vSource.v[i] = pose[i][3]
            params.vDirection.v[i] = -pose[i][2]
        hit, results = self.overlay.computeOverlayIntersection(self.toolbar_handle, params)
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

    def hitInsideRegion(self, size: str, results: Any, poseOf: Callable[[int], Optional[np.ndarray]]) -> bool:
        """VR UI の領域に当たった点が、その領域の見えている範囲の中か。

        切り出したオーバーレイの SteamVR の当たり判定は、見えている範囲からはみ出すことがある
        (実機で、ログの下の操作バーを指しているのに、ログにも当たったと返り、どちらになるかが揺れた)。
        """
        if size not in (PANEL, LAUNCHER, POPUP, TOOLBAR):
            return True
        pose = self.regionWorldPose(size, poseOf)
        if pose is None:
            return True
        local = np.linalg.inv(pose) @ np.array([results.vPoint.v[0], results.vPoint.v[1], results.vPoint.v[2], 1.0])
        _, _, region_w, region_h = self.layout["regions"][size]
        width_m = self.regionWidthM(size)
        height_m = width_m * region_h / region_w
        margin = 0.001
        return abs(local[0]) <= width_m / 2 + margin and abs(local[1]) <= height_m / 2 + margin

    def pointingOverlay(self, pose: np.ndarray, poseOf: Optional[Callable[[int], Optional[np.ndarray]]] = None) -> tuple:
        """Return (size, intersection results) of the overlay the controller ray hits, or (None, None).

        フェードアウトした(見えない)オーバーレイも対象にする: グリップで起こして掴めるように。
        画像の透明な部分と、VR UI の領域の見えている範囲の外 (poseOf があるとき) は対象にしない。
        """
        best = (None, None)
        for size in self.settings.keys():
            if self.settings[size]["opacity"] <= 0 or size in self.vr_windows_hidden:
                continue
            if size == LAUNCHER and not self.launcher_interactive:
                continue
            results = self.intersect(pose, size)
            if results is None or not self.hasContentAt(size, results):
                continue
            if poseOf is not None and not self.hitInsideRegion(size, results, poseOf):
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

    def tipOffset(self, index: int, now: float) -> np.ndarray:
        """コントローラの先端 (render model の "tip") の、本体の姿勢から見た姿勢。

        指す向きは本体の姿勢の -Z ではなく先端の -Z。Quest のコントローラでは先端が本体より 37° 下を
        向いていて、本体の -Z で指すとレーザーが上にずれて見えた (実機)。分からなければ本体の姿勢のまま指し、
        _TIP_RETRY_SEC 後にもう一度調べる (電源を入れた直後などは分からないことがある)。
        """
        cached = self.tip_offsets.get(index)
        if cached is not None and (cached[1] is None or now < cached[1]):
            return cached[0]
        offset, retry_at = np.eye(4), now + _TIP_RETRY_SEC
        try:
            name = self.overlay_system.getStringTrackedDeviceProperty(index, openvr.Prop_RenderModelName_String)
            ok, state = self.overlay_system.getControllerState(index)
            if name and ok:
                found, component = openvr.VRRenderModels().getComponentState(name, "tip", state, openvr.RenderModel_ControllerMode_State_t())
                if found:
                    m = component.mTrackingToComponentLocal
                    offset = utils.toHomogeneous(np.array([[m[i][j] for j in range(4)] for i in range(3)]))
                    retry_at = None
        except Exception:
            pass  # 先端が無いコントローラ・まだ繋がっていない: 本体の姿勢で指す
        if cached is None and retry_at is not None:
            printLog("overlay: コントローラの先端の向きが分からないので、本体の向きで指します", {"device": index})
        self.tip_offsets[index] = (offset, retry_at)
        return offset

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

        def rayOf(hand: int) -> Optional[np.ndarray]:
            """レーザーを出す姿勢 (コントローラの先端)。掴んだウィンドウもこの姿勢に付いて動く。"""
            pose = poseOf(hand)
            return None if pose is None else pose @ self.tipOffset(hand, now) @ laserTilt(_LASER_PITCH_UP_DEG)

        self.applyVrWindows(poseOf)
        self.updateLauncherVisibility(poseOf, now)
        self.updateToolbarFade(now)

        if self.resizing is not None:
            self.updateResize(poseOf, rayOf, controllerState, now)
            return

        if self.grabbing is not None:
            size, hand, hand_to_overlay = self.grabbing
            hand_pose = rayOf(hand)
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
                self.grab_prev_time = now
                self.grab_smoothed = None
                self.grab_prev_target = None
                return
            if self.grab_scale is not None:
                # 拡大縮小を終えたら、止めていた位置を今の手から掴み直す
                hand_to_overlay = np.linalg.inv(hand_pose) @ self.grab_scale[3]
                self.grabbing = (size, hand, hand_to_overlay)
                head = poseOf(openvr.k_unTrackedDeviceIndex_Hmd)
                if self.grab_radius is not None and head is not None:
                    self.grab_radius = float(np.linalg.norm(self.grab_scale[3][:3, 3] - head[:3, 3]))
                    self.grab_hand_distance = float(np.linalg.norm(hand_pose[:3, 3] - head[:3, 3]))
                self.grab_scale = None
                self.showPointer(None, _COLOR_NORMAL)
            dt = min(max(now - self.grab_prev_time, 0.0), 0.1)  # 撮影で止まったフレームでも跳ばないよう上限を付ける
            self.grab_prev_time = now
            # 空間・頭に固定したウィンドウは、手の向きでは回さず、目を中心とした球面上で自分の方を向ける。
            # 距離はスティックの上下で変える (手に付けたウィンドウは手から見た距離を変える)
            head = poseOf(openvr.k_unTrackedDeviceIndex_Hmd)
            on_sphere = self.grab_radius is not None and head is not None
            # 頭の位置が取れない (一瞬のトラッキングロスト): 球面上に置けないので、最後に置いた位置のままにする
            # (手の向きに合わせた姿勢で置くと、向きが一瞬跳ぶ。放したときもその位置で確定する)
            lost_head = self.grab_radius is not None and head is None and self.grab_last_relative is not None
            if grip and on_sphere:
                self.grab_radius = pushPullDistance(self.grab_radius, state, dt)
            elif grip and not lost_head:
                hand_to_overlay = pushPull(hand_to_overlay, state, dt)
                self.grabbing = (size, hand, hand_to_overlay)
            if lost_head:
                relative = self.grab_last_relative
            else:
                world = hand_pose @ hand_to_overlay
                if on_sphere:
                    hand_distance = float(np.linalg.norm(hand_pose[:3, 3] - head[:3, 3]))
                    world = poseOnSphere(world[:3, 3], head, sphereRadius(self.grab_radius, self.grab_hand_distance, hand_distance))
                relative = self.smoothGrab((np.linalg.inv(tracker_pose) @ world)[:3, :], dt)
                if on_sphere:
                    # ならして少し遅れた位置でも、頭の方を向ける
                    smoothed = (tracker_pose @ utils.toHomogeneous(relative))[:3, 3]
                    relative = (np.linalg.inv(tracker_pose) @ faceHead(smoothed, head))[:3, :]
            self.grab_last_relative = relative
            if grip:
                self.setTransform(size, tracker_index, relative)
                self.wakeOverlay(size)  # 掴んでいる間はフェードさせない
                pop = min((now - self.grab_started) / _GRAB_POP_SEC, 1.0)
                self.showPointer(self.intersect(hand_pose, size), _COLOR_POINTER, 1.0 + (_GRAB_POP_SCALE - 1.0) * pop)
            else:
                self.grabbing = None
                self.setHighlight(None, _COLOR_NORMAL)
                self.showPointer(None, _COLOR_NORMAL)
                if trigger:
                    self.trigger_blocked.add(hand)
                # 放した位置は、ならした後の位置 (放した瞬間に跳ねないように)
                self.setTransform(size, tracker_index, relative)
                self.commitPosition(size, relative)
            return

        pointer = None  # (results, color[, scale])
        hover_xy = None
        pointing_log = False
        pointing_launcher = False
        for role in (openvr.TrackedControllerRole_LeftHand, openvr.TrackedControllerRole_RightHand):
            hand = self.overlay_system.getTrackedDeviceIndexForControllerRole(role)
            hand_pose = rayOf(hand)
            grip = hand_pose is not None and gripPressed(hand)
            size, results = (None, None) if hand_pose is None else self.pointingOverlay(hand_pose, poseOf)
            toolbar = self.intersectToolbar(hand_pose) if hand_pose is not None else None
            if toolbar is not None and not self.hitInsideRegion(TOOLBAR, toolbar, poseOf):
                toolbar = None
            if toolbar is not None and (results is None or toolbar.fDistance < results.fDistance):
                size, results = TOOLBAR, toolbar
            # 自分の手に付いているオーバーレイはその手では動かせない(手と一緒に動くだけ)。操作バーはログと同じ
            tracker = self.settings[PANEL if size == TOOLBAR else size]["tracker"] if size is not None else None
            if tracker is not None and self.getTracker(tracker)[1] == hand:
                size, results = None, None
            pointing_log = pointing_log or size in (PANEL, TOOLBAR)
            corner = self.panelCornerAt(hand, hand_pose, poseOf) if hand_pose is not None else None
            if corner is not None and size not in (None, PANEL):
                # ログ以外のウィンドウ (操作バーなど) を指しているときは、そちらを優先する。
                # 角の当たり判定はログの外側まで広げてあり、同じ面にある操作バーの端と重なるため
                corner = None
            corner_before = self.corner_prev.get(hand)
            self.corner_prev[hand] = corner[:2] if corner is not None else None
            if corner is not None:
                pointing_log = True
            # 握った瞬間のレーザーのぶれで外れないよう、前のフレームで指していた角を優先する
            grip_corner = corner_before if corner_before is not None else (corner[:2] if corner is not None else None)
            if grip and not self.grip_prev.get(hand, False) and grip_corner is not None:
                self.grip_prev[hand] = True
                self.startResize(hand, grip_corner, poseOf)
                return
            pointing_launcher = pointing_launcher or size == LAUNCHER

            debug_state = (grip, size)
            if self.debug_state.get(hand) != debug_state:
                self.debug_state[hand] = debug_state
                printLog("overlay grab", {"hand": hand, "grip": grip, "hit": size})

            if hand_pose is not None and not grip:
                xy = None
                # 大きさの切り替え中は、表示 (古い並び) と VR画面 (新しい並び) が合っていないので入力を送らない
                # (押した位置が別のボタンに当たることがある)
                if size in VR_REGIONS and self.panel_image_size is not None and self.layout_applied is self.layout:
                    overlay_pose = self.regionWorldPose(size, poseOf)
                    if overlay_pose is not None:
                        xy = self.regionPixel(size, results, overlay_pose)
                # 角 (取っ手) ではクリック・スクロールを送らない。ホバー (取っ手を明るくする) だけ
                self.handlePanelInput(hand, None if corner is not None else xy, controllerState(hand))
                handle_xy = self.cornerHandleXY(corner[:2]) if corner is not None else None
                if hover_xy is None and handle_xy is not None:
                    hover_xy = handle_xy  # 角の取っ手を明るくする (ウィンドウの外側を指しているときも)
                elif hover_xy is None and xy is not None:
                    scale = self.panel_image_size[0] / self.layout["atlas"][0]
                    hover_xy = (round(xy[0] / scale), round(xy[1] / scale))

            # 角を指している (ウィンドウの外側を含む): ポインタを出し、グリップで大きさを変える (上で処理)
            if corner is not None and size != TOOLBAR:
                self.grip_prev[hand] = grip
                if pointer is None:
                    pointer = (corner[2], _COLOR_POINTER)
                continue

            # 操作バーは掴めない (ログに付いて動くだけ)。ボタンは VR画面へのクリックで押す
            if size == TOOLBAR:
                self.grip_prev[hand] = grip
                if pointer is None:
                    pointer = (results, _COLOR_POINTER)
                continue

            grip_pressed_now = grip and not self.grip_prev.get(hand, False)
            self.grip_prev[hand] = grip
            if size is None or not grip_pressed_now:
                if size is not None and not grip and self.isVisible(size) and pointer is None:
                    pointer = (results, _COLOR_POINTER)
                continue

            if size == PANEL and self.panel_locked:
                continue
            overlay_pose = self.overlayWorldPose(size, poseOf)
            if overlay_pose is None:
                continue
            self.wakeOverlay(size)  # フェード済みでもグリップで起こす
            self.grabbing = (size, hand, np.linalg.inv(hand_pose) @ overlay_pose)
            head = poseOf(openvr.k_unTrackedDeviceIndex_Hmd)
            on_sphere = self.settings[size]["tracker"] in (PLAYSPACE, "HMD") and head is not None
            self.grab_radius = float(np.linalg.norm(overlay_pose[:3, 3] - head[:3, 3])) if on_sphere else None
            if on_sphere:
                self.grab_hand_distance = float(np.linalg.norm(hand_pose[:3, 3] - head[:3, 3]))
            self.grab_last_relative = None
            self.grab_started = now
            self.grab_prev_time = now
            self.grab_smoothed = None
            self.grab_prev_target = None
            self.showPointer(results, _COLOR_POINTER)
            self.setHighlight(size, _COLOR_GRABBING)
            return

        self.showPointer(*(pointer or (None, _COLOR_NORMAL)))
        self.notifyPointer(hover_xy)
        self.updateToolbarVisibility(now, pointing_log)
        self.launcher_pointed = pointing_launcher

    def updateLauncherVisibility(self, poseOf: Callable[[int], Optional[np.ndarray]], now: float) -> None:
        """手首を見たときだけランチャーを出す。レーザーを当てている間は消さない。"""
        dt = 0.0 if self.launcher_prev_time is None else min(now - self.launcher_prev_time, 0.1)
        self.launcher_prev_time = now
        if LAUNCHER not in self.handle:
            return
        if not self.launcher_auto_hide:
            want = True
        elif self.launcher_pointed or (self.grabbing is not None and self.grabbing[0] == LAUNCHER):
            want = self.launcher_shown
        else:
            head = poseOf(openvr.k_unTrackedDeviceIndex_Hmd)
            launcher = self.overlayWorldPose(LAUNCHER, poseOf)
            if head is None or launcher is None:
                want = self.launcher_shown
            elif self.launcher_shown:
                want = launcherLooksVisible(launcher, head, _LAUNCHER_FACE_DEG + _LAUNCHER_HIDE_MARGIN_DEG, _LAUNCHER_GAZE_HIDE_DEG)
            else:
                want = launcherLooksVisible(launcher, head, _LAUNCHER_FACE_DEG, _LAUNCHER_GAZE_SHOW_DEG)
        # 出す・消すは、その状態が少し続いてから (設定で OFF にしたときはすぐ出す)
        if want == self.launcher_shown:
            self.launcher_change_since = None
        elif not self.launcher_auto_hide:
            self.launcher_shown, self.launcher_shown_at, self.launcher_change_since = True, now, None
        else:
            if self.launcher_change_since is None:
                self.launcher_change_since = now
            wait = _LAUNCHER_SHOW_AFTER_SEC if want else _LAUNCHER_HIDE_AFTER_SEC
            if now - self.launcher_change_since >= wait:
                self.launcher_shown, self.launcher_change_since = want, None
                if want:
                    self.launcher_shown_at = now
        target = 1.0 if self.launcher_shown else 0.0
        step = dt / _LAUNCHER_FADE_SEC
        self.launcher_alpha = min(self.launcher_alpha + step, target) if target > self.launcher_alpha else max(self.launcher_alpha - step, target)
        self.launcher_interactive = self.launcher_alpha >= 1.0 and (not self.launcher_auto_hide or now - self.launcher_shown_at >= _LAUNCHER_INPUT_DELAY_SEC)

    def setVrWindows(self, log: bool, popup: bool) -> None:
        """VR UIのウィンドウの表示・非表示を指定する (どのスレッドからでもよい)。"""
        self.vr_windows_wanted = {PANEL: log, POPUP: popup}

    def applyVrWindows(self, poseOf: Callable[[int], Optional[np.ndarray]]) -> None:
        """指定された表示・非表示をオーバーレイに反映する (オーバーレイのスレッドで呼ぶ)。"""
        wanted_windows = {**self.vr_windows_wanted, LAUNCHER: True}
        for size, wanted in wanted_windows.items():
            if size not in self.handle:
                continue
            wanted = wanted and self.vr_panel_enabled
            hidden = size in self.vr_windows_hidden
            if wanted and hidden:
                if size == POPUP:
                    self.placePopup(poseOf)
                self.vr_windows_hidden.discard(size)
                self.overlay.showOverlay(self.handle[size])
                self.panel_last_raw = None  # 念のため、表示し直したウィンドウには画面を送り直す
                if size == PANEL:
                    s = self.settings[PANEL]
                    self.updatePosition(s["x_pos"], s["y_pos"], s["z_pos"], s["x_rotation"], s["y_rotation"], s["z_rotation"], s["tracker"], PANEL)
                    # 前回置いた場所が見えないところなら、開いたときに目の前へ出す
                    if self.isPanelOutOfView(poseOf):
                        self.recallPanel(poseOf)
            elif not wanted and not hidden:
                self.vr_windows_hidden.add(size)
                self.overlay.hideOverlay(self.handle[size])
                if size == PANEL:
                    self.setToolbarVisible(False)
                    self.hideResizeGhost()  # 放した後、新しい大きさへの切り替えを待っている枠も消す
                    if self.resizing is not None:
                        self.resizing = None
                        self.setHighlight(None, _COLOR_NORMAL)
                        self.showPointer(None, _COLOR_NORMAL)
                if self.grabbing is not None and self.grabbing[0] == size:
                    self.grabbing = None
                    self.grab_scale = None
                    self.setHighlight(None, _COLOR_NORMAL)
                    self.showPointer(None, _COLOR_NORMAL)
        # 掴んでいる間は動かさない (掴み処理が同じフレームで位置を上書きする)。呼び戻しは離してから行う
        if self.grabbing is not None or self.resizing is not None:
            return
        if self.requested_anchor is not None:
            anchor, self.requested_anchor = self.requested_anchor, None
            if PANEL in self.handle:
                self.setAnchor(poseOf, anchor)
        if self.vr_recall_requested is not None:
            if PANEL in self.handle and PANEL not in self.vr_windows_hidden:
                self.vr_recall_requested = None
                self.recallPanel(poseOf)
            elif time.monotonic() - self.vr_recall_requested > _RECALL_PENDING_SEC:
                self.vr_recall_requested = None  # ログが開かれなかった
        self.notifyPanelOutOfView(PANEL in self.handle and self.isPanelOutOfView(poseOf))

    def requestRecallPanel(self) -> None:
        """ログウィンドウを目の前へ呼び戻すよう頼む (どのスレッドからでもよい)。

        固定先によらず、頭の正面に空間固定で置き直す。閉じていれば、開かれるのを少し待つ。
        """
        self.vr_recall_requested = time.monotonic()

    def isPanelOutOfView(self, poseOf: Callable[[int], Optional[np.ndarray]]) -> bool:
        """ログウィンドウが開いていて、視線から外れているか。

        手に付けているときは手を上げれば見えるので対象にしない (空間固定と頭に付けたときだけ)。
        """
        if PANEL in self.vr_windows_hidden or self.settings[PANEL]["tracker"] not in (PLAYSPACE, "HMD"):
            return False
        head = poseOf(openvr.k_unTrackedDeviceIndex_Hmd)
        world = self.overlayWorldPose(PANEL, poseOf)
        if head is None or world is None:
            return False
        return isOutOfView(head, world[:3, 3], was_out=self.panel_out_of_view)

    def recallPanel(self, poseOf: Callable[[int], Optional[np.ndarray]]) -> None:
        """ログウィンドウを頭の正面に空間固定で置き直し、その位置を保存する。"""
        head = poseOf(openvr.k_unTrackedDeviceIndex_Hmd)
        if head is None:
            return
        self.settings[PANEL]["tracker"] = PLAYSPACE
        self.commitPosition(PANEL, recallPose(head)[:3, :])
        s = self.settings[PANEL]
        self.updatePosition(s["x_pos"], s["y_pos"], s["z_pos"], s["x_rotation"], s["y_rotation"], s["z_rotation"], PLAYSPACE, PANEL)

    def notifyPanelOutOfView(self, out_of_view: bool) -> None:
        """ログウィンドウが見えなくなった・見えるようになったときだけ知らせる。"""
        if out_of_view == self.panel_out_of_view:
            return
        self.panel_out_of_view = out_of_view
        if self.panel_out_of_view_callback is not None:
            try:
                self.panel_out_of_view_callback(out_of_view)
            except Exception:
                errorLogging()

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
        world = faceHead(pos, head)
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

    def panelCornerAt(self, hand: int, hand_pose: np.ndarray, poseOf: Callable[[int], Optional[np.ndarray]]) -> Optional[tuple]:
        """レーザーがログの角 (伸ばすための取っ手) を指しているか。指していれば (x向き, y向き, 当たり)。

        x向き・y向きは +1 が右・上。ロック中・隠れているとき・大きさの切り替え中は判定しない。
        """
        if PANEL not in self.handle or PANEL in self.vr_windows_hidden or not self.vr_panel_enabled:
            return None
        if self.panel_locked or self.layout_applied is not self.layout or not self.isVisible(PANEL):
            return None
        if self.getTracker(self.settings[PANEL]["tracker"])[1] == hand:
            return None  # 自分の手に付けたログは、その手では伸ばせない
        pose = self.overlayWorldPose(PANEL, poseOf)
        if pose is None:
            return None
        hit = rayPlaneHit(hand_pose, pose)
        if hit is None:
            return None
        x, y, point, distance = hit
        _, _, width_px, height_px = self.layout["regions"][PANEL]
        m_per_px = self.settings[PANEL]["ui_scaling"] / width_px
        half_w, half_h = width_px * m_per_px / 2, height_px * m_per_px / 2
        inside, outside = _CORNER_INSIDE_PX * m_per_px, _CORNER_OUTSIDE_PX * m_per_px
        for sx in (1, -1):
            for sy in (1, -1):
                dx, dy = sx * x - half_w, sy * y - half_h  # 正なら枠の外
                if not (-inside <= dx <= outside and -inside <= dy <= outside):
                    continue
                if (sx, sy) == (1, 1) and dx <= 0 and dy <= 0:
                    continue  # 右上の内側は閉じるボタン
                return sx, sy, pointerHit(point, pose[:3, 2], distance)
        return None

    def cornerHandleXY(self, corner: tuple) -> Optional[tuple]:
        """角の取っ手の中心 (VR画面の論理px)。右上は閉じるボタンなので取っ手がない (None)。"""
        if corner == (1, 1):
            return None
        _, _, width_px, height_px = self.layout["regions"][PANEL]
        sx, sy = corner
        return (
            _CORNER_HANDLE_CENTER_PX if sx < 0 else width_px - _CORNER_HANDLE_CENTER_PX,
            _CORNER_HANDLE_CENTER_PX if sy > 0 else height_px - _CORNER_HANDLE_CENTER_PX,
        )

    def startResize(self, hand: int, corner: tuple, poseOf: Callable[[int], Optional[np.ndarray]]) -> None:
        """角を掴む。反対の角を動かさず、掴んだ角だけを動かして大きさを変える。"""
        tracker_index = self.getTracker(self.settings[PANEL]["tracker"])[1]
        tracker_pose = poseOf(tracker_index)
        pose = self.overlayWorldPose(PANEL, poseOf)
        if pose is None or tracker_pose is None:
            return
        _, _, width_px, height_px = self.layout["regions"][PANEL]
        m_per_px = self.settings[PANEL]["ui_scaling"] / width_px
        sx, sy = corner
        self.resizing = {
            "hand": hand, "corner": corner, "m_per_px": m_per_px,
            "tracker_index": tracker_index, "relative": np.linalg.inv(tracker_pose) @ pose, "pose": pose,
            "fixed": (-sx * width_px * m_per_px / 2, -sy * height_px * m_per_px / 2),
            "size": (width_px, height_px), "center": (0.0, 0.0),
        }
        self.setToolbarVisible(False)
        self.notifyPointer(None)
        self.setHighlight(PANEL, _COLOR_GRABBING)

    def updateResize(self, poseOf: Callable[[int], Optional[np.ndarray]], rayOf: Callable[[int], Optional[np.ndarray]],
                     controllerState: Callable[[int], Optional[Any]], now: float) -> None:
        """掴んだ角をレーザーの先に合わせる。中身は描き直さず、新しい大きさの枠だけを動かす。"""
        r = self.resizing
        hand_pose = rayOf(r["hand"])
        state = controllerState(r["hand"])
        if hand_pose is None or state is None or not (state.ulButtonPressed & _GRIP_MASK):
            self.finishResize(poseOf)
            return
        tracker_pose = poseOf(r["tracker_index"])
        if tracker_pose is not None:
            r["pose"] = tracker_pose @ r["relative"]
        hit = rayPlaneHit(hand_pose, r["pose"])
        if hit is None:
            return
        x, y, point, distance = hit
        sx, sy = r["corner"]
        fixed_x, fixed_y = r["fixed"]
        m_per_px = r["m_per_px"]
        wanted = (sx * (x - fixed_x) / m_per_px, sy * (y - fixed_y) / m_per_px)
        width_px, height_px = clampPanelSize(*wanted)
        at_limit = abs(width_px - wanted[0]) > 1 or abs(height_px - wanted[1]) > 1
        r["size"] = (width_px, height_px)
        r["center"] = (fixed_x + sx * width_px * m_per_px / 2, fixed_y + sy * height_px * m_per_px / 2)
        self.showPointer(pointerHit(point, r["pose"][:3, 2], distance), _COLOR_POINTER)
        self.markStep("grab:ghost")  # 実機で角を掴んで伸ばしている間に1.2秒止まった。どこで止まるかを分ける
        self.showResizeGhost(at_limit)
        self.markStep("grab")

    def finishResize(self, poseOf: Callable[[int], Optional[np.ndarray]]) -> None:
        """放したら大きさと位置を確定して保存する。表示は新しい大きさで撮れてから切り替わる (applyLayout)。"""
        r, self.resizing = self.resizing, None
        self.markStep("grab:finish_resize")
        self.setHighlight(None, _COLOR_NORMAL)
        self.showPointer(None, _COLOR_NORMAL)
        s = self.settings[PANEL]
        width_px, height_px = r["size"]
        center = np.eye(4)
        center[0, 3], center[1, 3] = r["center"]
        undo = {k: s[k] for k in ("x_pos", "y_pos", "z_pos", "x_rotation", "y_rotation", "z_rotation", "ui_scaling", "tracker")}
        # 1px の実際の長さは変えない (横に伸ばすと1行の文字数が増え、文字の大きさは変わらない)
        s["ui_scaling"] = r["m_per_px"] * width_px
        self.setPanelSize(width_px, height_px)
        self.commitPosition(PANEL, (r["relative"] @ center)[:3, :])
        self.resize_undo = undo if self.layout_applied is not self.layout else None
        if self.layout_applied is self.layout:
            self.hideResizeGhost()  # 大きさが変わらなかった

    def showResizeGhost(self, at_limit: bool) -> None:
        if self.ghost_handle is None or self.gl is None:
            return
        r = self.resizing
        width_px, height_px = r["size"]
        key = (width_px // 4, height_px // 4, at_limit)
        if key != self.ghost_key:
            self.ghost_key = key
            img = createGhostImage(width_px, height_px, at_limit)
            GL = self.prepareGl()
            GL.glBindTexture(GL.GL_TEXTURE_2D, self.gl["ghost_texture"])
            # テクスチャの大きさは変えない (newPanelTexture と同じ理由)。左上の一部だけを使う
            GL.glTexSubImage2D(GL.GL_TEXTURE_2D, 0, 0, 0, img.size[0], img.size[1], GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, img.tobytes())
            GL.glFinish()
            tex_w, tex_h = _GHOST_TEXTURE_SIZE
            bounds = openvr.VRTextureBounds_t()
            bounds.uMin, bounds.uMax, bounds.vMin, bounds.vMax = 0.0, img.size[0] / tex_w, 1.0, 1.0 - img.size[1] / tex_h
            self.overlay.setOverlayTextureBounds(self.ghost_handle, bounds)
            self.overlay.setOverlayTexture(self.ghost_handle, self.gl["ghost_vr_texture"])
        center = np.eye(4)
        center[0, 3], center[1, 3] = r["center"]
        center[2, 3] = _GHOST_FRONT_M  # ログの表 (+Z) 側
        self.overlay.setOverlayTransformAbsolute(self.ghost_handle, openvr.TrackingUniverseStanding, mat34Id((r["pose"] @ center)[:3, :]))
        self.overlay.setOverlayWidthInMeters(self.ghost_handle, width_px * r["m_per_px"])
        self.overlay.showOverlay(self.ghost_handle)

    def hideResizeGhost(self) -> None:
        if self.ghost_handle is not None and self.overlay is not None:
            self.overlay.hideOverlay(self.ghost_handle)

    def smoothGrab(self, target: np.ndarray, dt: float) -> np.ndarray:
        """掴んで動かしている位置をならす (追従先から見た空間で。手に付けたウィンドウでも遅れて揺れないように)。

        ゆっくり動かしているときだけ手の震えを抑え、速く動かしているときはそのまま付いていく。
        """
        previous, previous_target = self.grab_smoothed, self.grab_prev_target
        self.grab_prev_target = target.copy()
        if previous is None or previous_target is None or dt <= 0:
            self.grab_smoothed = target.copy()
            return self.grab_smoothed
        # 速さは手の動きそのもの (ならす前の位置) で測る。ならした位置は遅れを含むので使わない
        speed = float(np.linalg.norm(target[:, 3] - previous_target[:, 3])) / dt
        alpha = 1.0 if speed >= _GRAB_SMOOTH_MAX_SPEED_M else 1.0 - float(np.exp(-dt / _GRAB_SMOOTH_TAU_SEC))
        smoothed = target.copy()
        smoothed[:, 3] = previous[:, 3] + (target[:, 3] - previous[:, 3]) * alpha
        self.grab_smoothed = smoothed
        return smoothed

    def commitPosition(self, size: str, relative: np.ndarray) -> None:
        """掴んで動かした結果 (位置と幅) を確定し、保存用にコールバックへ渡す。"""
        base_matrix, _ = self.getTracker(self.settings[size]["tracker"])
        keys = ("x_pos", "y_pos", "z_pos", "x_rotation", "y_rotation", "z_rotation")
        for key, value in zip(keys, utils.matrix_to_position(base_matrix, relative)):
            self.settings[size][key] = round(value, 4)
        if size == PANEL:
            # 伸ばした後に動かした・固定先を変えた・呼び戻した位置を、大きさを元に戻すときに消さない
            # (伸ばして放したときは finishResize がこの後で記録し直す)
            self.resize_undo = None
        self.notifyPosition(size)

    def notifyPosition(self, size: str) -> None:
        """今の位置と幅・固定先を、保存と UI への通知のためにコールバックへ渡す。"""
        if self.position_changed_callback is None:
            return
        keys = ("x_pos", "y_pos", "z_pos", "x_rotation", "y_rotation", "z_rotation")
        try:
            # ui_scaling はオーバーレイの幅(m)。設定値への換算は呼び出し側で行う
            self.position_changed_callback(size, {
                **{k: self.settings[size][k] for k in keys},
                "ui_scaling": self.settings[size]["ui_scaling"],
                "tracker": self.settings[size]["tracker"],
                # ログウィンドウの大きさ (論理px)。角を掴んで伸ばしたとき
                **({k: self.settings[size][k] for k in ("width", "height") if k in self.settings[size]}),
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
        elif size == LAUNCHER and self.launcher_alpha < 1.0:
            # 手首を見ていないので薄く (消して) いる。設定の不透明度は書き換えない
            if self.initialized is True:
                self.overlay.setOverlayAlpha(self.handle[size], self.settings[size]["opacity"] * self.launcher_alpha)
        else:
            self.updateOpacity(self.settings[size]["opacity"], size)

    def mainloop(self) -> None:
        self.loop = True
        Thread(target=self.watchStall, args=(sys._current_frames, get_ident()), daemon=True).start()
        while self.checkActive() is True and self.loop is True and not self.start_cancelled:
            startTime = time.monotonic()
            self.markStep("update")
            for size in self.settings.keys():
                self.update(size)
            try:
                self.retryPendingPositions()
            except Exception:
                errorLogging()
            # 先にレーザー (ポインタ・ホバー) を処理してから撮影する (レーザーの反応を撮影の分だけ待たせない)
            self.markStep("grab")
            try:
                self.updateGrab()
                self.grab_error = None
            except Exception as e:
                self.onGrabError(e)
            self.markStep("panel")
            try:
                self.updatePanel()
            except Exception as e:
                self.onPanelError(e)
            # 掴んでいる間・伸ばしている間は滑らかにするため、VR UI を指している間は反応を早くするため更新頻度を上げる
            if self.grabbing is not None or self.resizing is not None:
                interval = 1 / 60
            elif self.pointer_notified is not None:
                interval = 1 / 30
            else:
                interval = 1 / 16
            self.markStep("sleep")
            self.reportSlowSteps()
            sleepTime = interval - (time.monotonic() - startTime)
            if sleepTime > 0:
                time.sleep(sleepTime)
        self.markStep("teardown")
        self.teardown()
        self.markStep("idle")
        # 止まったあとは「見失っている」表示を残さない
        self.notifyPanelOutOfView(False)

    def markStep(self, name: str) -> None:
        """処理の段階が変わった。前の段階にかかった時間の最大を覚える (reportSlowSteps / watchStall)。"""
        now = time.monotonic()
        previous, started = self.loop_step
        took = now - started
        if previous != "sleep" and took > self.step_max.get(previous, 0.0):
            self.step_max[previous] = took
        self.loop_step = (name, now)

    def reportSlowSteps(self) -> None:
        """_STEP_REPORT_SEC ごとに、遅い段階があれば (_STEP_SLOW_SEC 超え) その最大時間をログに出す。"""
        now = time.monotonic()
        if now - self.step_reported_at < _STEP_REPORT_SEC:
            return
        slow = {name: round(took * 1000) for name, took in self.step_max.items() if took > _STEP_SLOW_SEC}
        if slow:
            printLog("overlay: 処理に時間がかかっています (ms、10秒間の最大)", slow)
        self.step_max = {}
        self.step_reported_at = now

    def watchStall(self, current_frames: Callable[[], Dict[int, Any]], thread_id: int) -> None:
        """オーバーレイのスレッドが同じ段階で _STALL_REPORT_SEC 以上止まったら、どこで止まっているかをログに出す。"""
        reported = None
        while self.loop and not self.start_cancelled:
            time.sleep(0.5)
            step = self.loop_step
            if step[0] in ("sleep", "idle") or step is reported or time.monotonic() - step[1] < _STALL_REPORT_SEC:
                continue
            reported = step
            frame = current_frames().get(thread_id)
            stack = "".join(traceback.format_stack(frame)[-4:]) if frame is not None else ""
            printLog("overlay: 処理が止まっています", {"step": step[0], "sec": round(time.monotonic() - step[1], 1), "stack": stack})

    def teardown(self) -> None:
        """オーバーレイを消して SteamVR との接続を閉じ、最後に OpenGL の環境を消す (オーバーレイのスレッドで呼ぶ)。

        OpenGL のテクスチャを渡したあと、ON/OFF を処理するスレッド (OpenGL の環境が無い) から
        接続を閉じると、SteamVR の中で落ちた (実機で access violation。テクスチャを外してからでも同じ)。
        OpenGL の環境を作ったこのスレッドで、環境を今のものにしたまま閉じる。
        GL コンテキストは作ったスレッドでしか破棄できないので、それも最後にここで行う。
        """
        if self.gl is not None:
            try:
                self.gl["glfw"].make_context_current(self.gl["window"])
            except Exception:
                errorLogging()
        self.closePanelStream()
        self.destroyOverlays()
        self.releaseSession()
        self.shutdownPanelTexture()
        printLog("overlay: 止めました")

    def destroyOverlays(self) -> None:
        """作ったオーバーレイをすべて消す。消した後は何もしない。"""
        if not isinstance(self.overlay, openvr.IVROverlay):
            return
        try:
            for size in self.settings.keys():
                if isinstance(self.handle.get(size), int):
                    self.overlay.destroyOverlay(self.handle[size])
            for handle in [*self.pointer_handles.values(), *[h for h in (self.toolbar_handle, self.ghost_handle) if h is not None]]:
                self.overlay.destroyOverlay(handle)
        except Exception:
            errorLogging()
        self.pointer_handles = {}
        self.toolbar_handle = None
        self.toolbar_visible = False
        self.toolbar_alpha, self.toolbar_faded_at = 0.0, None
        self.ghost_handle = None
        self.resizing = None
        self.overlay = None

    def releaseSession(self) -> None:
        """SteamVR との接続の参照を返す。閉じるのに失敗しても、次に ON にしたとき作り直せるようにする。"""
        if not isinstance(self.system, openvr.IVRSystem):
            return
        try:
            # Only releases our reference; the real openvr.shutdown()
            # only runs once every other holder (e.g. Clipboard) has
            # released theirs too.
            openvr_session.release()
        except Exception:
            errorLogging()
        finally:
            self.system = None

    def onPanelError(self, e: Exception) -> None:
        """撮影・転送で例外が出た。1回ではやめず次のフレームでやり直し、続くときだけ撮影をやめる。"""
        self.panel_errors += 1
        # 毎フレーム呼ばれるため、同じ例外が続く間はログを1回だけにする
        if repr(e) != self.panel_error:
            self.panel_error = repr(e)
            errorLogging()
        if self.panel_errors >= _PANEL_ERROR_LIMIT and not self.panel_stopped:
            printLog("overlay: VR画面の撮影が続けて失敗したので止めます", {"errors": self.panel_errors})
            # OpenGL の環境はここでは消さない。消した後に SteamVR との接続を閉じると落ちる (teardown 参照)
            self.panel_stopped = True
            self.closePanelStream()

    def onGrabError(self, e: Exception) -> None:
        """掴み・伸ばす処理で例外が出たら、その操作をやめる (同じ例外で毎フレーム止まり続けないように)。"""
        self.grabbing = None
        if self.resizing is not None:
            self.resizing = None
            try:
                self.hideResizeGhost()
            except Exception:
                errorLogging()
        # 掴んでいる印 (色とポインタ) を残さない
        try:
            self.setHighlight(None, _COLOR_NORMAL)
            self.showPointer(None, _COLOR_NORMAL)
        except Exception:
            errorLogging()
        # 毎フレーム呼ばれるため、同じ例外が続く間はログを1回だけにする
        if repr(e) != self.grab_error:
            self.grab_error = repr(e)
            errorLogging()

    def main(self) -> None:
        printLog("overlay: SteamVR の起動を確かめています")
        try:
            while self.checkSteamvrRunning() is False:
                if self.waitUnlessCancelled(_STEAMVR_POLL_SEC):
                    return
            if self.waitUnlessCancelled(0.0):
                return
            self.init()
            if self.initialized is True:
                self.mainloop()
                with self.start_lock:
                    if self.start_cancelled:
                        # 作っている間に止められた (mainloop はすぐ終わり、後片付けも済んでいる)
                        # ponytail: この直後に ON にされる1秒未満の間は取りこぼす。起こるようなら状態を1つにまとめる
                        self.start_cancelled = False
                        self.initialized = False
        except Exception:
            # スレッドの例外はどこにも残らず、「作っている途中」のままだと以後 ON にしても作り直せない
            errorLogging()
            with self.start_lock:
                self.init_process = False

    def waitUnlessCancelled(self, seconds: float) -> bool:
        """seconds 秒待つ。その間に止められたら (shutdownOverlay)、起動をやめて True を返す。"""
        deadline = time.monotonic() + seconds
        while True:
            with self.start_lock:
                if self.start_cancelled:
                    self.start_cancelled = False
                    self.init_process = False
                    return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            time.sleep(min(remaining, _START_CANCEL_POLL_SEC))

    def startOverlay(self) -> None:
        with self.start_lock:
            # 待っている間に OFF→ON された: 取りやめをなくして、そのまま待ち続ける
            self.start_cancelled = False
            if self.initialized is False and self.init_process is False:
                self.init_process = True
                self.thread_overlay = Thread(target=self.main)
                self.thread_overlay.daemon = True
                self.thread_overlay.start()

    def shutdownOverlay(self) -> None:
        self.requested_anchor = None
        with self.start_lock:
            if self.init_process is True:
                # SteamVR の起動を待っている (または作っている) 間に止められた: 起動しないようにする
                self.start_cancelled = True
                return
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
            # ふつうはオーバーレイのスレッドが終わるときに済ませている (teardown)。残っていれば片付ける
            try:
                self.destroyOverlays()
                self.releaseSession()
            finally:
                self.initialized = False

    def reStartOverlay(self) -> None:
        self.shutdownOverlay()
        self.startOverlay()

    @staticmethod
    def checkSteamvrRunning() -> bool:
        _proc_name = "vrmonitor.exe" if os.name == "nt" else "vrmonitor"
        # 名前はまとめて取る。1つずつ p.name() で取ると、途中で終わったプロセスで NoSuchProcess になり、
        # オーバーレイのスレッドが記録も残さずに止まった (VR UI の OFF→ON で VR画面の WebView が入れ替わるとき)
        return any(p.info["name"] == _proc_name for p in process_iter(["name"]))

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