"""Detect candidate VRChat chat-bubble regions in a captured frame.

VRChat chat bubbles are semi-transparent rounded panels floating above
avatars. This detector uses a color/contour heuristic to enumerate
candidate ROIs before we spend cycles on OCR:

1. Convert to grayscale, blur, then threshold to isolate bright-on-dark
   text-ish areas plus the darker bubble backing plate.
2. Morphologically close text lines together so a paragraph forms one
   contiguous blob.
3. Take contour bounding rects and filter by aspect ratio, size, and
   position (exclude far edges where HUD/nameplate strips live).
4. Return a list of (bbox, crop_bgr) tuples for the OCR engine.

The thresholds are intentionally lenient — false positives are cheaper
than false negatives here because the OCR engine + min-confidence knob
filters out noise crops that contain no readable text.
"""

from __future__ import annotations

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


BBox = Tuple[int, int, int, int]  # (x, y, w, h)


class BubbleDetector:
    def __init__(
        self,
        min_area_ratio: float = 0.0008,
        max_area_ratio: float = 0.20,
        min_aspect: float = 1.2,
        max_aspect: float = 20.0,
        edge_margin_ratio: float = 0.03,
        exclude_bottom_ratio: float = 0.15,
        collar_width: int = 3,
        max_collar_std: float = 5.0,
        center_bias_weight: float = 0.5,
        upper_bias_weight: float = 0.35,
    ) -> None:
        self.min_area_ratio = min_area_ratio
        self.max_area_ratio = max_area_ratio
        self.min_aspect = min_aspect
        self.max_aspect = max_aspect
        self.edge_margin_ratio = edge_margin_ratio
        self.exclude_bottom_ratio = exclude_bottom_ratio
        # VRChatのチャット吹き出しは、ワールド制作者が作る看板/UIパネルとは
        # 描画のされ方(アバター頭上に浮かぶワールド内3D要素)自体は同じだが、
        # 見た目の背景がVRChatクライアント自身が描く単色でフラットな半透明
        # パネルである点が違う(ワールド側のテキストは木目・紙・金属等の
        # テクスチャの上に直接乗っていることが多い)。bboxのすぐ外側、幅
        # collar_width pxだけの細い縁の色ばらつきを見ることでこれを判別する
        # (2026-09-07、実機で「工場ゲームのUIパネル文字を吹き出しと誤認する」
        # regressionを受けて追加。ユーザー提供の実データ80枚
        # (メッセージ送信→スクリーンショットのペア) で校正: 本物の吹き出しは
        # 縁のstdの中央値2.0、他の候補は中央値9.8で、閾値5.0で本物の91%を
        # 保持しつつ他候補の78%を弾けることを確認した)。
        self.collar_width = collar_width
        self.max_collar_std = max_collar_std
        # 吹き出しはアバター頭上、つまり画面中央〜上寄りに現れやすい。
        # ハード排除はせず、複数候補が競合したときのOCR予算(tick_budget)の
        # 優先順位付けとして使う「ソート補正」に留める(ユーザー指示: 画面端に
        # 出る吹き出しも取りこぼしたくないため)。
        self.center_bias_weight = center_bias_weight
        self.upper_bias_weight = upper_bias_weight

    def isAvailable(self) -> bool:
        return cv2 is not None

    def detect(self, frame: np.ndarray) -> List[Tuple[BBox, np.ndarray]]:
        if not self.isAvailable() or frame is None or frame.size == 0:
            return []
        h, w = frame.shape[:2]
        frame_area = float(h * w)
        if frame_area <= 0:
            return []

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (3, 3), 0)
            # Adaptive threshold catches both light-on-dark and dark-on-light
            # panel-vs-text combinations without hard-coding VRChat's palette.
            binary = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV,
                31,
                7,
            )
            # Close text into paragraph-sized blobs.
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 5))
            closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        except Exception:
            return []

        try:
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        except Exception:
            return []

        margin_x = int(w * self.edge_margin_ratio)
        margin_y = int(h * self.edge_margin_ratio)
        bottom_hud_y = int(h * (1.0 - self.exclude_bottom_ratio))

        results: List[Tuple[BBox, np.ndarray]] = []
        for cnt in contours:
            x, y, cw, ch = cv2.boundingRect(cnt)
            if cw <= 0 or ch <= 0:
                continue
            area = float(cw * ch)
            area_ratio = area / frame_area
            if area_ratio < self.min_area_ratio or area_ratio > self.max_area_ratio:
                continue
            aspect = cw / float(ch)
            if aspect < self.min_aspect or aspect > self.max_aspect:
                continue
            # Reject anything hugging the frame borders (world sign / HUD).
            if x < margin_x or y < margin_y:
                continue
            if (x + cw) > (w - margin_x):
                continue
            # Reject bottom HUD strip (nameplate, notifications, VRChat menu).
            if y > bottom_hud_y:
                continue

            # Pad the crop slightly so OCR sees full glyph boundaries.
            pad = 4
            x0 = max(0, x - pad)
            y0 = max(0, y - pad)
            x1 = min(w, x + cw + pad)
            y1 = min(h, y + ch + pad)
            crop = frame[y0:y1, x0:x1]
            if crop.size == 0:
                continue

            collar_std = self._collarStd(frame, x0, y0, x1, y1)
            if collar_std is not None and collar_std > self.max_collar_std:
                continue

            results.append(((x0, y0, x1 - x0, y1 - y0), crop))

        # 面積優先を基本としつつ、画面中央/上寄りの候補を軽く優先する
        # (アバター頭上に出る吹き出しの典型的な位置)。ハード排除はしない
        # ので、画面端の吹き出しも面積が大きければ上位に残る。
        results.sort(key=lambda item: self._score(item[0], w, h), reverse=True)
        return results

    def _collarStd(self, frame: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> Optional[float]:
        """bbox (x0,y0,x1,y1) のすぐ外側、幅 collar_width px だけの細い縁の
        色ばらつき(RGB各chの標準偏差の平均)を返す。ワールドの3Dシーン本体に
        入り込まないよう意図的に薄く取る(厚いパディングだとVRChatの吹き出し
        パネル自体の外側の背景まで拾ってしまい判別に使えなくなる)。
        測定できるピクセル数が少なすぎる場合は None (判定不能、フィルタしない)。
        """
        h, w = frame.shape[:2]
        collar = self.collar_width
        ox0, oy0 = max(0, x0 - collar), max(0, y0 - collar)
        ox1, oy1 = min(w, x1 + collar), min(h, y1 + collar)
        outer = frame[oy0:oy1, ox0:ox1]
        if outer.size == 0:
            return None
        mask = np.ones(outer.shape[:2], dtype=bool)
        iy0, ix0 = y0 - oy0, x0 - ox0
        iy1, ix1 = iy0 + (y1 - y0), ix0 + (x1 - x0)
        mask[max(0, iy0):max(0, iy1), max(0, ix0):max(0, ix1)] = False
        if mask.sum() < 8:
            return None
        collar_pixels = outer[mask].astype(np.float32)
        return float(collar_pixels.std(axis=0).mean())

    def _score(self, bbox: BBox, frame_w: int, frame_h: int) -> float:
        x, y, bw, bh = bbox
        area = float(bw * bh)
        cx = x + bw / 2.0
        cy = y + bh / 2.0
        horiz_ratio = abs(cx - frame_w / 2.0) / (frame_w / 2.0)  # 0=中央, ~1=画面端
        vert_ratio = cy / frame_h  # 0=最上部, 1=最下部
        position_score = max(
            0.15,
            1.0 - self.center_bias_weight * horiz_ratio - self.upper_bias_weight * vert_ratio,
        )
        return area * position_score
