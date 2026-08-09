"""EasyOCR wrapper with lazy singleton reader.

readtext_bgr(crop) -> list of {"text": str, "confidence": float}. Never
raises: on any failure returns an empty list so the pipeline just skips
that tick.
"""

from __future__ import annotations

from threading import Lock
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import easyocr  # type: ignore
except Exception:  # pragma: no cover
    easyocr = None  # type: ignore

try:
    from utils import errorLogging, printLog
except Exception:  # pragma: no cover
    def errorLogging():
        import traceback
        print(traceback.format_exc())

    def printLog(*args, **kwargs):
        print(*args, **kwargs)


_reader_cache: Dict[Tuple[Tuple[str, ...], bool], object] = {}
_reader_lock = Lock()


def isAvailable() -> bool:
    return easyocr is not None


def getReader(langs: List[str], use_gpu: bool) -> Optional[object]:
    if easyocr is None:
        return None
    key = (tuple(langs), bool(use_gpu))
    with _reader_lock:
        cached = _reader_cache.get(key)
        if cached is not None:
            return cached
        try:
            reader = easyocr.Reader(list(langs), gpu=bool(use_gpu), verbose=False)
        except Exception:
            errorLogging()
            # Retry once with GPU disabled — GPU init failure is the common
            # cause (no CUDA / VRAM tight after whisper loaded).
            if use_gpu:
                try:
                    reader = easyocr.Reader(list(langs), gpu=False, verbose=False)
                except Exception:
                    errorLogging()
                    return None
            else:
                return None
        _reader_cache[key] = reader
        return reader


def readtext_bgr(reader: object, crop_bgr: np.ndarray, min_confidence: float = 0.5) -> List[dict]:
    if reader is None or crop_bgr is None or crop_bgr.size == 0:
        return []
    try:
        # EasyOCR accepts BGR ndarrays directly.
        raw = reader.readtext(crop_bgr, detail=1, paragraph=False)  # type: ignore[attr-defined]
    except Exception:
        errorLogging()
        return []
    out: List[dict] = []
    for item in raw:
        try:
            # EasyOCR returns (bbox_points, text, confidence)
            _bbox, text, conf = item[0], item[1], item[2]
        except Exception:
            continue
        try:
            conf_f = float(conf)
        except Exception:
            conf_f = 0.0
        if not isinstance(text, str):
            continue
        text = text.strip()
        if not text:
            continue
        if conf_f < min_confidence:
            continue
        out.append({"text": text, "confidence": conf_f})
    return out
