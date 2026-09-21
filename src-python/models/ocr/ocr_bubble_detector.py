"""Detect VRChat chat-bubble regions with a fine-tuned YOLOv8n (ONNX).

色/輪郭のヒューリスティックは実機で反証された(ワールドのUIパネル文字や
岩・木目を吹き出しと誤認する)ため、収集したVRChatのスクリーンショットで
学習した検出モデルに置き換えた。学習手順は docs/ocr_yolo_training.md。

同梱する .onnx はリポジトリの MIT ではなく AGPL-3.0 (Ultralytics 由来)。
詳細は docs/ocr_model_license.md、表記は onnx/NOTICE.txt。

推論は onnxruntime だけで動く。faster-whisper が Silero VAD 用にすでに
依存しているので、配布物に追加される依存はモデルファイル1つだけ。
NMS込みでエクスポートしてあるので、ここでやるのは前処理(letterbox)と
元画像座標への戻しだけになる。
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

MODEL_FILE_NAME = "chatbox_yolov8n.onnx"
# 学習時と同じ入力サイズ。吹き出しは画面の1%程度しかないことがあり、640まで
# 落とすと取りこぼす(実測: val20枚で1280が19/20、640は16/20)。
DEFAULT_IMAGE_SIZE = 1280
DEFAULT_CONFIDENCE = 0.15
# ultralyticsのletterboxと同じ余白色。学習時の前処理に合わせる。
PAD_COLOR = (114, 114, 114)


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


class BubbleDetector:
    def __init__(
        self,
        model_path: Optional[str] = None,
        image_size: int = DEFAULT_IMAGE_SIZE,
        confidence: float = DEFAULT_CONFIDENCE,
        crop_padding: int = 4,
    ) -> None:
        self.model_path = model_path or findModelPath()
        self.image_size = int(image_size)
        # 実機のワールドや距離によって当たり方が変わるので調整できるようにしておく。
        # 既定0.15は取りこぼしを優先した値(val20枚の実測: 0.15で20/20・余分5、
        # 0.25で19/20・余分2、0.5で18/20・余分0)。余分な候補はOCR側の
        # min_confidenceで文字が読めずに落ちるだけだが、下げすぎるとtickの
        # OCR予算を無駄な切り出しに使う。
        self.confidence = float(confidence)
        self.crop_padding = max(0, int(crop_padding))
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

    def _letterbox(self, frame: np.ndarray) -> Tuple[np.ndarray, float, int, int]:
        h, w = frame.shape[:2]
        scale = min(self.image_size / w, self.image_size / h)
        nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
        resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
        canvas = np.full((self.image_size, self.image_size, 3), PAD_COLOR, dtype=np.uint8)
        dx, dy = (self.image_size - nw) // 2, (self.image_size - nh) // 2
        canvas[dy:dy + nh, dx:dx + nw] = resized
        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        tensor = np.ascontiguousarray(rgb.transpose(2, 0, 1)[None], dtype=np.float32) / 255.0
        return tensor, scale, dx, dy

    def detect(self, frame: np.ndarray) -> List[Tuple[BBox, np.ndarray]]:
        """信頼度の高い順に [(bbox(x,y,w,h), 切り出したBGR画像), ...] を返す。"""
        if not self.isAvailable() or frame is None or frame.size == 0:
            return []
        h, w = frame.shape[:2]
        if h <= 0 or w <= 0:
            return []
        try:
            session = self._ensureSession()
            tensor, scale, dx, dy = self._letterbox(frame)
            outputs = session.run(None, {self._input_name: tensor})[0]
        except Exception:
            errorLogging()
            return []

        results: List[Tuple[float, BBox, np.ndarray]] = []
        for detection in np.asarray(outputs).reshape(-1, 6):
            score = float(detection[4])
            if score < self.confidence:
                continue
            pad = self.crop_padding
            x0 = int(round((detection[0] - dx) / scale)) - pad
            y0 = int(round((detection[1] - dy) / scale)) - pad
            x1 = int(round((detection[2] - dx) / scale)) + pad
            y1 = int(round((detection[3] - dy) / scale)) + pad
            x0, y0 = max(0, x0), max(0, y0)
            x1, y1 = min(w, x1), min(h, y1)
            if x1 - x0 < 2 or y1 - y0 < 2:
                continue
            crop = frame[y0:y1, x0:x1]
            if crop.size == 0:
                continue
            results.append((score, (x0, y0, x1 - x0, y1 - y0), crop))

        results.sort(key=lambda item: item[0], reverse=True)
        return [(bbox, crop) for _, bbox, crop in results]
