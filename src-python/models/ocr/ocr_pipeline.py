"""OCR pipeline orchestrator: capture → detect → OCR → dedup → callback.

Runs in its own thread. The callback signature mirrors mic/speaker
transcript callbacks so Controller.ocrMessage can reuse the same
translation → UI/overlay flow.

Callback payload:
    {
        "text": str,
        "language": str,     # VRCT source language name ("auto" if unknown)
        "is_final": True,
        "segment_id": str,
        "recognition_error": False,
        "source": "ocr",
    }
"""

from __future__ import annotations

import hashlib
import time
import uuid
from collections import OrderedDict
from threading import Event, Thread
from typing import Callable, List, Optional

import numpy as np

from .ocr_bubble_detector import BubbleDetector
from .ocr_capture import OcrCapture
from . import ocr_engine_easyocr as easyocr_engine
from .ocr_languages import resolveEasyocrLangs

try:
    from utils import errorLogging, printLog
except Exception:  # pragma: no cover
    def errorLogging():
        import traceback
        print(traceback.format_exc())

    def printLog(*args, **kwargs):
        print(*args, **kwargs)


# Upper bound on how many candidate rectangles get OCR'd in a single tick,
# and how long that OCR work may take before the tick yields.
MAX_CANDIDATES_PER_TICK = 6
TICK_OCR_BUDGET_RATIO = 0.8


def _textHash(text: str) -> str:
    return hashlib.blake2b(text.casefold().encode("utf-8"), digest_size=8).hexdigest()


def _similar(a: str, b: str, max_distance: int = 2) -> bool:
    """Cheap bounded edit-distance check for near-duplicate OCR output.

    OCR jitter across frames flips a character or two, which produces a
    different hash for what a human reads as the same bubble. Comparing with
    a small distance budget catches those without a fuzzy-matching dependency.
    """
    if a == b:
        return True
    if abs(len(a) - len(b)) > max_distance:
        return False
    # Classic DP, but bail out as soon as the whole row exceeds the budget.
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(min(
                previous[j] + 1,
                current[j - 1] + 1,
                previous[j - 1] + (ca != cb),
            ))
        if min(current) > max_distance:
            return False
        previous = current
    return previous[-1] <= max_distance


class _DedupCache:
    """Recently-seen bubble texts, keyed by hash.

    Entries store the text itself so near-duplicates can be compared, plus
    the last time the text was *seen* (not the last time it was emitted).
    Refreshing on every sighting means the cooldown is measured from when a
    bubble leaves the screen, so a bubble that lingers is translated once
    rather than re-translated every `cooldown_sec`.
    """

    def __init__(self, max_items: int = 128, evict_after_sec: float = 30.0) -> None:
        self._items: "OrderedDict[str, tuple[float, str, tuple[int, int]]]" = OrderedDict()
        self._max_items = max_items
        self._evict_after = evict_after_sec

    def evictStale(self, now: float) -> None:
        stale = [k for k, (ts, _, _) in self._items.items() if (now - ts) > self._evict_after]
        for k in stale:
            self._items.pop(k, None)
        while len(self._items) > self._max_items:
            self._items.popitem(last=False)

    def seenRecently(self, text_hash: str, text: str, cooldown_sec: float, now: float) -> bool:
        """Return True if this text (or a near-duplicate) is still on cooldown.

        Also refreshes the timestamp of whichever entry matched, so a bubble
        that stays on screen keeps its cooldown alive instead of re-firing.
        """
        entry = self._items.get(text_hash)
        if entry is not None:
            last_ts, _, center = entry
            self._items[text_hash] = (now, text, center)
            self._items.move_to_end(text_hash)
            return (now - last_ts) < cooldown_sec

        for key, (last_ts, prev_text, center) in list(self._items.items()):
            if _similar(text, prev_text):
                self._items[key] = (now, prev_text, center)
                self._items.move_to_end(key)
                return (now - last_ts) < cooldown_sec
        return False

    def record(self, text_hash: str, text: str, bbox_center: tuple, now: float) -> None:
        self._items[text_hash] = (now, text, bbox_center)
        self._items.move_to_end(text_hash)


class OcrPipeline:
    def __init__(
        self,
        callback: Callable[[dict], None],
        source_language: str = "auto",
        window_title: str = "VRChat",
        poll_interval_ms: int = 750,
        min_confidence: float = 0.55,
        use_gpu: bool = True,
        min_text_length: int = 2,
        dedup_cooldown_sec: int = 8,
    ) -> None:
        self._callback = callback
        self._source_language = source_language or "auto"
        self._window_title = window_title or "VRChat"
        self._poll_interval = max(0.1, poll_interval_ms / 1000.0)
        # Keep OCR work inside a fraction of the poll interval so the loop
        # stays responsive to stop() and does not run back-to-back.
        self._tick_budget = self._poll_interval * TICK_OCR_BUDGET_RATIO
        self._min_confidence = float(min_confidence)
        self._use_gpu = bool(use_gpu)
        self._min_text_length = max(1, int(min_text_length))
        self._dedup_cooldown = max(1, int(dedup_cooldown_sec))

        self._stop_event = Event()
        self._thread: Optional[Thread] = None
        self._capture: Optional[OcrCapture] = None
        self._detector = BubbleDetector()
        self._dedup = _DedupCache()
        self._reader = None

    def isEngineAvailable(self) -> bool:
        return easyocr_engine.isAvailable() and self._detector.isAvailable()

    def start(self) -> bool:
        if not self.isEngineAvailable():
            printLog("OCR pipeline: engine or opencv unavailable, refusing to start")
            return False
        if self._thread is not None and self._thread.is_alive():
            return True
        self._stop_event.clear()
        langs = resolveEasyocrLangs(self._source_language)
        self._reader = easyocr_engine.getReader(langs, self._use_gpu)
        if self._reader is None:
            printLog("OCR pipeline: EasyOCR reader init failed")
            self.stop()
            return False
        self._thread = Thread(target=self._run, name="ocr_pipeline", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop_event.set()
        th = self._thread
        if th is not None:
            try:
                th.join(timeout=5.0)
            except Exception:
                pass
        self._thread = None
        # _run() closes self._capture itself before exiting — capture
        # backends hold OS resources (GDI DCs, OpenVR handles) tied to the
        # thread that created them, so tearing down from here is unsafe.
        self._capture = None

    def _emit(self, text: str) -> None:
        try:
            self._callback({
                "text": text,
                "language": self._source_language if self._source_language != "auto" else None,
                "is_final": True,
                "segment_id": uuid.uuid4().hex,
                "recognition_error": False,
                "source": "ocr",
            })
        except Exception:
            errorLogging()

    def _run(self) -> None:
        # Capture backends hold OS resources tied to the creating thread,
        # so construct on this thread rather than the one that called start().
        self._capture = OcrCapture(window_title=self._window_title)
        try:
            while not self._stop_event.is_set():
                start_t = time.monotonic()
                try:
                    self._tick()
                except Exception:
                    errorLogging()
                elapsed = time.monotonic() - start_t
                sleep_for = self._poll_interval - elapsed
                if sleep_for > 0:
                    self._stop_event.wait(sleep_for)
        finally:
            try:
                self._capture.close()
            except Exception:
                pass

    def _tick(self) -> None:
        if self._capture is None or self._reader is None:
            return
        frame = self._capture.get()
        if frame is None:
            return
        candidates = self._detector.detect(frame)
        if not candidates:
            return

        # A noisy frame (busy world, text-heavy UI) can yield dozens of
        # candidate rectangles. Running OCR on all of them would stall the
        # loop for seconds and starve the GPU that whisper is sharing, so
        # only the largest few — which the detector already sorted first —
        # get an OCR budget on any single tick.
        candidates = candidates[:MAX_CANDIDATES_PER_TICK]

        now = time.monotonic()
        self._dedup.evictStale(now)
        deadline = now + self._tick_budget

        for bbox, crop in candidates:
            if self._stop_event.is_set():
                return
            if time.monotonic() > deadline:
                break
            words = easyocr_engine.readtext_bgr(self._reader, crop, self._min_confidence)
            if not words:
                continue
            merged = self._mergeWords(words)
            if len(merged) < self._min_text_length:
                continue
            h = _textHash(merged)
            if self._dedup.seenRecently(h, merged, self._dedup_cooldown, now):
                continue
            cx = int(bbox[0] + bbox[2] / 2)
            cy = int(bbox[1] + bbox[3] / 2)
            self._dedup.record(h, merged, (cx, cy), now)
            self._emit(merged)

    @staticmethod
    def _mergeWords(words: List[dict]) -> str:
        parts = [w["text"] for w in words if isinstance(w.get("text"), str)]
        # Join with spaces; VRChat bubbles tend to be single-line, so this
        # matches typical human reading order well enough for translation.
        return " ".join(p.strip() for p in parts if p.strip()).strip()
