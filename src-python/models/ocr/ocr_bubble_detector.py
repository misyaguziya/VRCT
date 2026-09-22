"""Detect VRChat chat-bubble regions with a fine-tuned YOLOX-Tiny (ONNX).

色/輪郭のヒューリスティックは実機で反証された(ワールドのUIパネル文字や
岩・木目を吹き出しと誤認する)ため、収集したVRChatのスクリーンショットで
学習した検出モデルに置き換えた。学習手順は docs/ocr_yolo_training.md。

基盤は Megvii の YOLOX (Apache-2.0)。以前は Ultralytics の YOLOv8n を使って
いたが、事前学習重みが AGPL-3.0 で成果物もその派生になるため載せ替えた。
経緯は docs/ocr_model_license.md、表記は onnx/NOTICE.txt。

推論は onnxruntime だけで動く。faster-whisper が Silero VAD 用にすでに
依存しているので、配布物に追加される依存はモデルファイル1つだけ。
デコード(grid/stride の復元)はエクスポート時にグラフへ入れてあるので、
ここでやるのは前処理(letterbox)・閾値・NMS・元画像座標への戻しだけになる。

同梱モデルは入力サイズ可変で、INT8に量子化してある(docs/ocr_yolo_training.md)。
ウィンドウのアスペクト比に合わせて余白を削れるので、正方形fp32より速い。
"""

from __future__ import annotations

from os import path as os_path
import sys
from threading import Lock
from typing import List, Optional, Tuple

import numpy as np

try:
    from utils import errorLogging
except Exception:  # pragma: no cover
    def errorLogging():
        import traceback
        print(traceback.format_exc())

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore
    errorLogging()

try:
    import onnxruntime as ort  # type: ignore
except Exception:  # pragma: no cover
    ort = None  # type: ignore
    errorLogging()


BBox = Tuple[int, int, int, int]  # (x, y, w, h)

MODEL_FILE_NAME = "chatbox_yolox_tiny.onnx"
# 長辺をこのサイズに合わせる。学習時と同じ縮尺。吹き出しは画面の1%程度しか
# ないことがあり、640まで落とすと取りこぼす(実測: val20枚で1280が19/20、640は16/20)。
DEFAULT_IMAGE_SIZE = 1280
DEFAULT_CONFIDENCE = 0.85
DEFAULT_NMS_IOU = 0.65
# YOLOXのletterboxと同じ余白色。学習時の前処理に合わせる。
PAD_COLOR = 114
# FPNのstrideが8/16/32なので、入力の縦横はこの倍数でなければならない。
SIZE_MULTIPLE = 32


def findModelPath() -> Optional[str]:
    """同梱されたONNXモデルのパス。見つからなければ None。"""
    candidates = []
    if getattr(sys, "frozen", False):
        # PyInstallerのdatasは実行ファイルの隣の _internal/ 配下に展開される。
        candidates.append(os_path.join(os_path.dirname(sys.executable), "_internal", "ocr_onnx", MODEL_FILE_NAME))
    candidates.append(os_path.join(os_path.dirname(__file__), "onnx", MODEL_FILE_NAME))
    for candidate in candidates:
        if os_path.isfile(candidate):
            return candidate
    return None


def nonMaxSuppression(boxes: np.ndarray, scores: np.ndarray, threshold: float) -> List[int]:
    """信頼度の高い順に、重なりすぎた箱を落とす。残った添字を強い順で返す。

    YOLOXのNMSはtorchvision.opsを使っていてONNXへ落ちないので、ここに持つ。
    閾値を1箇所(BubbleDetectorの引数)に集められる利点もある。YOLOv8nのときは
    エクスポート時の値がグラフへ焼き込まれて実行時に下げられなかった。
    """
    order = scores.argsort()[::-1]
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    keep: List[int] = []
    while order.size:
        current = order[0]
        keep.append(int(current))
        if order.size == 1:
            break
        rest = order[1:]
        x0 = np.maximum(boxes[current, 0], boxes[rest, 0])
        y0 = np.maximum(boxes[current, 1], boxes[rest, 1])
        x1 = np.minimum(boxes[current, 2], boxes[rest, 2])
        y1 = np.minimum(boxes[current, 3], boxes[rest, 3])
        overlap = np.clip(x1 - x0, 0, None) * np.clip(y1 - y0, 0, None)
        union = areas[current] + areas[rest] - overlap
        order = rest[overlap / np.maximum(union, 1e-6) <= threshold]
    return keep


class BubbleDetector:
    def __init__(
        self,
        model_path: Optional[str] = None,
        image_size: int = DEFAULT_IMAGE_SIZE,
        confidence: float = DEFAULT_CONFIDENCE,
        crop_padding: int = 4,
        nms_iou: float = DEFAULT_NMS_IOU,
    ) -> None:
        self.model_path = model_path or findModelPath()
        self.image_size = int(image_size)
        # 実機のワールドや距離によって当たり方が変わるので調整できるようにしておく。
        # 既定0.15は取りこぼしを優先した値(val20枚の実測は
        # docs/ocr_yolo_training.md の閾値の表)。余分な候補はOCR側の
        # min_confidenceで文字が読めずに落ちるだけだが、下げすぎるとtickの
        # OCR予算を無駄な切り出しに使う。
        self.confidence = float(confidence)
        self.crop_padding = max(0, int(crop_padding))
        self.nms_iou = float(nms_iou)
        self._session = None
        self._input_name = ""
        self._lock = Lock()

    def isAvailable(self) -> bool:
        # パスの有無だけでなく実体も見る。同梱漏れ(spec の datas 忘れ)に、最初の
        # detect() まで気づけないと「OCRは動いているのに何も出ない」状態になる。
        return (cv2 is not None and ort is not None
                and bool(self.model_path) and os_path.isfile(self.model_path))

    def _ensureSession(self):
        """最初のdetect()でだけモデルを読む。OCRを使わない起動では読み込まない。"""
        if self._session is not None:
            return self._session
        with self._lock:
            if self._session is None:
                options = ort.SessionOptions()
                options.log_severity_level = 3
                session = ort.InferenceSession(
                    self.model_path, options, providers=["CPUExecutionProvider"])
                self._input_name = session.get_inputs()[0].name
                self._session = session
        return self._session

    def _letterbox(self, frame: np.ndarray) -> Tuple[np.ndarray, float]:
        """YOLOXの前処理(yolox.data.data_augment.preproc)と同じ形にする。

        BGRのまま、0-255のまま、余白は左上寄せ。YOLOv8のときと違って正規化も
        RGB変換もしない。左上寄せなので座標の戻しは scale で割るだけになる。

        キャンバスは正方形ではなく、縮小後のフレームを32の倍数に切り上げた大きさに
        する。VRChatのウィンドウはユーザーがリサイズできるのでアスペクト比が
        一定ではなく、正方形に合わせると使わない余白まで推論することになる
        (16:9なら4割強)。縮尺(scale)は長辺で決まるので、キャンバスの形が変わっても
        吹き出しの大きさは変わらない。同梱モデルは入力が可変でエクスポートしてある。
        """
        h, w = frame.shape[:2]
        scale = min(self.image_size / w, self.image_size / h)
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
        canvas_w = -(-nw // SIZE_MULTIPLE) * SIZE_MULTIPLE
        canvas_h = -(-nh // SIZE_MULTIPLE) * SIZE_MULTIPLE
        canvas = np.full((canvas_h, canvas_w, 3), PAD_COLOR, dtype=np.uint8)
        canvas[:nh, :nw] = resized
        tensor = np.ascontiguousarray(canvas.transpose(2, 0, 1)[None], dtype=np.float32)
        return tensor, scale

    def detect(self, frame: np.ndarray) -> List[Tuple[BBox, np.ndarray]]:
        """信頼度の高い順に [(bbox(x,y,w,h), 切り出したBGR画像), ...] を返す。"""
        if not self.isAvailable() or frame is None or frame.size == 0:
            return []
        h, w = frame.shape[:2]
        if h <= 0 or w <= 0:
            return []
        try:
            session = self._ensureSession()
            tensor, scale = self._letterbox(frame)
            outputs = session.run(None, {self._input_name: tensor})[0]
        except Exception:
            errorLogging()
            return []

        # (1, アンカー数, 6) = cx, cy, w, h, 物体らしさ, クラス(吹き出しの1種類だけ)。
        predictions = np.asarray(outputs).reshape(-1, 6)
        scores = predictions[:, 4] * predictions[:, 5]
        predictions = predictions[scores >= self.confidence]
        scores = scores[scores >= self.confidence]
        if not len(predictions):
            return []

        half_w, half_h = predictions[:, 2] / 2, predictions[:, 3] / 2
        boxes = np.stack([predictions[:, 0] - half_w, predictions[:, 1] - half_h,
                          predictions[:, 0] + half_w, predictions[:, 1] + half_h], axis=1)

        results: List[Tuple[BBox, np.ndarray]] = []
        pad = self.crop_padding
        # NMSは強い順に残すので、この時点で信頼度の降順になっている。
        for index in nonMaxSuppression(boxes, scores, self.nms_iou):
            x0 = int(round(boxes[index, 0] / scale)) - pad
            y0 = int(round(boxes[index, 1] / scale)) - pad
            x1 = int(round(boxes[index, 2] / scale)) + pad
            y1 = int(round(boxes[index, 3] / scale)) + pad
            x0, y0 = max(0, x0), max(0, y0)
            x1, y1 = min(w, x1), min(h, y1)
            if x1 - x0 < 2 or y1 - y0 < 2:
                continue
            crop = frame[y0:y1, x0:x1]
            if crop.size == 0:
                continue
            results.append(((x0, y0, x1 - x0, y1 - y0), crop))
        return results
