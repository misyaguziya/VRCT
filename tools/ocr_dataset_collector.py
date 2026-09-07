"""OCR吹き出し検出モデルの学習データ収集ツール(開発用、VRCTには同梱しない)。

本番の `models/ocr/ocr_capture.OcrCapture` (HWND/OpenVRを自動切替する
本番と同じキャプチャ経路) をそのまま使い、VRChatをプレイしながら任意の
タイミングでスクリーンショットを撮って以下のいずれかに振り分ける:

- positive/ : 実際のチャット吹き出しが写っている画像 (後でbboxアノテーション
  が必要)
- negative/ : 吹き出しは写っていないが、紛らわしいワールド側UI/看板等の
  テキストが写っている画像 (bbox不要、そのままYOLOの「背景」学習に使える)

使い方:
    python tools/ocr_dataset_collector.py <session_name>

    例: python tools/ocr_dataset_collector.py factory_world_desktop

session_name はワールド名や条件(デスクトップ/VR、明るい/暗い等)を表す
任意の文字列。同じワールドで複数回に分けて集める場合も、同じ
session_name を指定すればファイルが追記されていく(上書きされない)。

操作方法 (VRChatを操作しながら、このコンソールにフォーカスを移して入力):
    Enter (何も入力せず)  -> 直前のキャプチャを「吹き出しあり」として保存
    n + Enter             -> 直前のキャプチャを「吹き出しなし/紛らわしいUI」として保存
    r + Enter             -> 保存せずに現在のプレビュー(最新フレームの状態)を再取得
    q + Enter             -> 終了

実際には「入力した瞬間」ではなく「直前に自動取得しておいた最新フレーム」を
保存する(VRChat側にフォーカスがある間に良い瞬間を見て、コンソールに
戻ってから確定するまでのタイムラグでシーンが変わってしまうのを防ぐため、
背景スレッドが常に最新フレームを取得し続ける)。
"""

from __future__ import annotations

import os
import sys
import threading
import time
from datetime import datetime

_SRC_PYTHON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src-python")
sys.path.insert(0, _SRC_PYTHON)

import cv2  # noqa: E402

from models.ocr.ocr_capture import OcrCapture  # noqa: E402

_CAPTURE_INTERVAL_SEC = 1.0


class _LatestFrameGrabber:
    """背景スレッドで常に最新フレームを取得し続ける。

    コンソールでの操作(Enter押下等)にかかる時間ぶん古いフレームを保存する
    事態を避けるための、単純なポーリングスレッド。
    """

    def __init__(self, capture: OcrCapture) -> None:
        self._capture = capture
        self._latest = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2.0)

    def _run(self) -> None:
        while not self._stop.is_set():
            frame = self._capture.get()
            if frame is not None:
                with self._lock:
                    self._latest = frame
            time.sleep(_CAPTURE_INTERVAL_SEC)

    def latest(self):
        with self._lock:
            return None if self._latest is None else self._latest.copy()


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python tools/ocr_dataset_collector.py <session_name> [--out DIR]")
        sys.exit(1)
    session_name = sys.argv[1]
    out_root = "dataset_collected"
    if "--out" in sys.argv:
        out_root = sys.argv[sys.argv.index("--out") + 1]

    pos_dir = os.path.join(out_root, session_name, "positive")
    neg_dir = os.path.join(out_root, session_name, "negative")
    os.makedirs(pos_dir, exist_ok=True)
    os.makedirs(neg_dir, exist_ok=True)

    capture = OcrCapture(window_title="VRChat")
    grabber = _LatestFrameGrabber(capture)
    grabber.start()

    pos_count = len(os.listdir(pos_dir))
    neg_count = len(os.listdir(neg_dir))

    print(f"[session={session_name}] backend selection is automatic (HWND / OpenVR mirror).")
    print(f"positive so far: {pos_count}, negative so far: {neg_count}")
    print("Enter=save as POSITIVE(bubble visible)  n+Enter=save as NEGATIVE  r+Enter=refresh  q+Enter=quit")

    try:
        while True:
            cmd = input("> ").strip().lower()
            if cmd == "q":
                break
            if cmd == "r":
                print("(refreshed - the grabber thread always keeps the latest frame anyway)")
                continue

            frame = grabber.latest()
            if frame is None:
                print("[WARN] no frame captured yet (is VRChat running and visible?)")
                continue

            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            if cmd == "n":
                path = os.path.join(neg_dir, f"{session_name}_{ts}.png")
                cv2.imwrite(path, frame)
                neg_count += 1
                print(f"[saved NEGATIVE] {path}  (negative total: {neg_count})")
            else:
                path = os.path.join(pos_dir, f"{session_name}_{ts}.png")
                cv2.imwrite(path, frame)
                pos_count += 1
                print(f"[saved POSITIVE] {path}  (positive total: {pos_count})")
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        grabber.stop()
        capture.close()
        print(f"done. positive={pos_count} negative={neg_count} under {os.path.join(out_root, session_name)}")


if __name__ == "__main__":
    main()
