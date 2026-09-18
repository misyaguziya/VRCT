"""RapidOCR (ONNX) ラッパー。モデル指定ごとに遅延生成した推論器をキャッシュする。

readtext_bgr(crop) -> [{"text": str, "confidence": float}, ...]。
EasyOCRラッパーと同じ形を返すので、パイプライン側の扱いは変わらない。
例外は投げず、失敗時は空リストを返してそのtickを飛ばす。

EasyOCRから乗り換えた理由と実測は ocr_languages.py と
docs/details/ocr.md を参照。onnxruntime は faster-whisper が
Silero VAD 用に既に依存しているので、追加される実行時依存はない。
"""

from __future__ import annotations

from threading import Lock
from typing import Dict, List, Optional

import numpy as np

from .ocr_languages import OcrModelSpec

try:
    from utils import errorLogging, printLog
except Exception:  # pragma: no cover
    def errorLogging():
        import traceback
        print(traceback.format_exc())

    def printLog(*args, **kwargs):
        print(*args, **kwargs)

try:
    from rapidocr import EngineType, LangRec, ModelType, OCRVersion, RapidOCR  # type: ignore
except Exception:  # pragma: no cover
    RapidOCR = None  # type: ignore
    EngineType = LangRec = ModelType = OCRVersion = None  # type: ignore
    errorLogging()

# 吹き出しの切り出しは小さい(短辺100px前後のこともある)。RapidOCRの既定は
# 短辺を736pxまで拡大する設定 (limit_type="min") なので、そのままだと7倍に
# 引き伸ばして1枚2秒近くかかる。320に下げると実測で2倍以上速くなり、
# 精度は落ちなかった (95枚で中央値 1778ms -> 790ms)。
DET_LIMIT_SIDE_LEN = 320

_engine_cache: Dict[OcrModelSpec, object] = {}
_engine_lock = Lock()


def isAvailable() -> bool:
    return RapidOCR is not None


def getReader(spec: OcrModelSpec) -> Optional[object]:
    """モデル指定に対応する推論器を返す。生成に失敗したら None。"""
    if RapidOCR is None or spec is None:
        return None
    with _engine_lock:
        cached = _engine_cache.get(spec)
        if cached is not None:
            return cached
        try:
            params = {
                # RapidOCRは既定でモデルの読み込み経過をINFOでstderrへ出す。
                # VRCTのstderrはUIのコンソールへ流れて他のログを埋めるので黙らせる。
                "Global.log_level": "error",
                "Det.engine_type": EngineType.ONNXRUNTIME,
                "Rec.engine_type": EngineType.ONNXRUNTIME,
                "Cls.engine_type": EngineType.ONNXRUNTIME,
                "Det.ocr_version": OCRVersion(spec.ocr_version),
                "Rec.ocr_version": OCRVersion(spec.ocr_version),
                "Det.model_type": ModelType(spec.model_type),
                "Rec.model_type": ModelType(spec.model_type),
                "Det.limit_side_len": DET_LIMIT_SIDE_LEN,
            }
            if spec.lang_rec:
                params["Rec.lang_type"] = LangRec(spec.lang_rec)
            engine = RapidOCR(params=params)
        except Exception:
            errorLogging()
            printLog(f"OCR engine: could not load {spec.label}")
            return None
        _engine_cache[spec] = engine
        return engine


def readtext_bgr(reader: object, crop_bgr: np.ndarray, min_confidence: float = 0.5) -> List[dict]:
    if reader is None or crop_bgr is None or crop_bgr.size == 0:
        return []
    try:
        result = reader(crop_bgr)  # type: ignore[operator]
    except Exception:
        errorLogging()
        return []

    texts = list(getattr(result, "txts", None) or [])
    scores = list(getattr(result, "scores", None) or [])
    out: List[dict] = []
    for index, text in enumerate(texts):
        if not isinstance(text, str):
            continue
        text = text.strip()
        if not text:
            continue
        try:
            confidence = float(scores[index]) if index < len(scores) else 0.0
        except (TypeError, ValueError):
            confidence = 0.0
        if confidence < min_confidence:
            continue
        out.append({"text": text, "confidence": confidence})
    return out
