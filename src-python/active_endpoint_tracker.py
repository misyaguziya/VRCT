"""アクティブなオーディオエンドポイントを追跡するトラッカー。

Windows のオーディオ API (pycaw 経由の IAudioMeterInformation) で
全 render/capture エンドポイントのピーク音量を短周期でポーリングし、
「実際に音声が流れている / 拾われている」エンドポイントを判定する。

用途:
    Auto Select 機能で「OS の既定デバイス」ではなく「今実際に音声が
    再生されているデバイス」を追跡したい (VRChat ユースでの
    ゲーム音出力デバイス自動選択など)。

設計方針:
    - ポーリング間隔 (POLL_INTERVAL_SEC): 250ms。人間の体感で十分応答的、
      COM 負荷も低い。
    - ローリングウィンドウ (WINDOW_SEC): 3s の最大ピークで判定。
      音声の切れ目でフリップしないため。
    - ヒステリシス: 現在選択中のエンドポイントは、他候補が SWITCH_RATIO 倍
      以上のピークを SWITCH_HOLD_SEC 継続で出したときだけ切替える。
    - 全エンドポイントが SILENT_THRESHOLD 以下なら None を返す。
      呼び出し側は既存の Multimedia default 追跡にフォールバックする想定
      (このモジュール自身は default を知らない)。
"""

from __future__ import annotations

import time
from collections import deque
from ctypes import POINTER, cast
from threading import Event, Lock, Thread
from typing import Callable, Optional

try:
    import comtypes
    from comtypes import CLSCTX_ALL, CLSCTX_INPROC_SERVER
    from pycaw.constants import CLSID_MMDeviceEnumerator
    from pycaw.pycaw import (
        DEVICE_STATE,
        AudioUtilities,
        EDataFlow,
        IAudioMeterInformation,
        IMMDeviceEnumerator,
    )
    _PYCAW_AVAILABLE = True
except Exception:  # pragma: no cover - Windows/pycaw が無い環境
    comtypes = None  # type: ignore
    _PYCAW_AVAILABLE = False

from utils import errorLogging


class ActiveEndpointTracker:
    """指定 flow (render/capture) のオーディオエンドポイントを peak で監視する。

    使い方:
        tracker = ActiveEndpointTracker("render")
        tracker.set_on_change_callback(lambda name: print("active:", name))
        tracker.start()
        ...
        tracker.stop()

    on_change コールバックは監視スレッドから呼ばれる。長時間ブロックすると
    poll 間隔が延びるため、呼び出し側で enqueue するなど非同期化することを
    推奨する (device_manager と AudioLifecycleWorker のペア参照)。
    """

    POLL_INTERVAL_SEC: float = 0.25
    WINDOW_SEC: float = 3.0
    SILENT_THRESHOLD: float = 0.001
    SWITCH_RATIO: float = 2.0
    SWITCH_HOLD_SEC: float = 1.0

    def __init__(self, flow: str) -> None:
        if flow not in ("render", "capture"):
            raise ValueError(f"flow must be 'render' or 'capture', got {flow!r}")
        self._flow: str = flow
        if _PYCAW_AVAILABLE:
            self._flow_value = (
                EDataFlow.eRender.value if flow == "render" else EDataFlow.eCapture.value
            )
        else:
            self._flow_value = 0

        self._stop_event: Event = Event()
        self._thread: Optional[Thread] = None
        self._on_change_cb: Optional[Callable[[Optional[str]], None]] = None

        # 「現在アクティブと判定されているエンドポイント」の FriendlyName
        # (or None = 無音)。外部から get_active_endpoint_name() でも参照可。
        self._current_endpoint_name: Optional[str] = None
        # per-endpoint (name) の直近ピーク履歴: {name: deque of (timestamp, peak)}
        self._history: dict[str, deque] = {}
        # 切替候補 (candidate_name, first_seen_timestamp)
        self._switch_candidate: Optional[tuple] = None
        self._lock: Lock = Lock()

    def set_on_change_callback(self, cb: Optional[Callable[[Optional[str]], None]]) -> None:
        self._on_change_cb = cb

    def get_active_endpoint_name(self) -> Optional[str]:
        with self._lock:
            return self._current_endpoint_name

    def start(self) -> None:
        if not _PYCAW_AVAILABLE:
            return
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            try:
                self._thread.join(timeout=0.5)
            except Exception:
                pass

    # --- 内部実装 ------------------------------------------------------------

    def _run(self) -> None:
        try:
            comtypes.CoInitialize()
        except Exception:
            errorLogging()
            return
        try:
            while not self._stop_event.is_set():
                try:
                    self._poll_once()
                except Exception:
                    errorLogging()
                # stop_event でも即抜けできるよう wait を使う
                if self._stop_event.wait(timeout=self.POLL_INTERVAL_SEC):
                    break
        finally:
            try:
                comtypes.CoUninitialize()
            except Exception:
                pass

    def _poll_once(self) -> None:
        now = time.monotonic()
        endpoints = self._enumerate_endpoints_with_meters()
        peaks: dict[str, float] = {}
        for name, meter in endpoints:
            try:
                peaks[name] = float(meter.GetPeakValue())
            except Exception:
                continue

        with self._lock:
            self._update_history(peaks, now)
            new_selected = self._decide_selected(now)
            changed = new_selected != self._current_endpoint_name
            self._current_endpoint_name = new_selected

        if changed and self._on_change_cb is not None:
            try:
                self._on_change_cb(new_selected)
            except Exception:
                errorLogging()

    def _update_history(self, peaks: dict[str, float], now: float) -> None:
        """peaks の内容を _history に追加、ウィンドウ外を破棄、
        消えたエンドポイントの履歴を破棄する。純粋なメソッド (COM 依存無し)。
        """
        for name, peak in peaks.items():
            hist = self._history.setdefault(name, deque())
            hist.append((now, peak))
            cutoff = now - self.WINDOW_SEC
            while hist and hist[0][0] < cutoff:
                hist.popleft()
        for gone in list(self._history.keys()):
            if gone not in peaks:
                del self._history[gone]

    def _decide_selected(self, now: float) -> Optional[str]:
        """現在の履歴とヒステリシス状態から選択エンドポイント名を決定する。
        純粋なメソッド (テストのために切り出し)。
        """
        rolling = {
            name: max((p for _, p in hist), default=0.0)
            for name, hist in self._history.items()
        }
        active = [(n, mx) for n, mx in rolling.items() if mx > self.SILENT_THRESHOLD]
        selected = self._current_endpoint_name

        if not active:
            # 全て silent → 現在の選択を維持 (無音時のフリップ抑制)
            self._switch_candidate = None
            return selected

        active.sort(key=lambda x: x[1], reverse=True)
        best_name, best_peak = active[0]

        if selected is None or selected not in rolling:
            # 未選択 or 選択中が消えた → best を即採用
            self._switch_candidate = None
            return best_name

        if best_name == selected:
            self._switch_candidate = None
            return selected

        cur_peak = rolling.get(selected, 0.0)
        # ヒステリシス: SWITCH_RATIO 倍以上を SWITCH_HOLD_SEC 継続で切替
        if best_peak >= cur_peak * self.SWITCH_RATIO:
            if (
                self._switch_candidate is None
                or self._switch_candidate[0] != best_name
            ):
                self._switch_candidate = (best_name, now)
                return selected
            if now - self._switch_candidate[1] >= self.SWITCH_HOLD_SEC:
                self._switch_candidate = None
                return best_name
            return selected

        # 差が閾値未満なら候補をリセット
        self._switch_candidate = None
        return selected

    def _enumerate_endpoints_with_meters(self) -> list[tuple[str, object]]:
        """(FriendlyName, IAudioMeterInformation) の list を返す。

        アクティブ状態 (DEVICE_STATE.ACTIVE) の指定 flow のエンドポイントのみ。
        FriendlyName は pyaudiowpatch の device['name'] とマッチする
        (WASAPI ホスト経由でエンドポイントを見た場合)。
        """
        result: list[tuple[str, object]] = []
        try:
            enumerator = comtypes.CoCreateInstance(
                CLSID_MMDeviceEnumerator,
                IMMDeviceEnumerator,
                CLSCTX_INPROC_SERVER,
            )
            collection = enumerator.EnumAudioEndpoints(
                self._flow_value, DEVICE_STATE.ACTIVE.value
            )
            count = collection.GetCount()
            for i in range(count):
                dev = collection.Item(i)
                if dev is None:
                    continue
                try:
                    audio_dev = AudioUtilities.CreateDevice(dev)
                    name = audio_dev.FriendlyName
                    activated = dev.Activate(
                        IAudioMeterInformation._iid_, CLSCTX_ALL, None
                    )
                    meter = cast(activated, POINTER(IAudioMeterInformation))
                    result.append((name, meter))
                except Exception:
                    # 個別デバイスの列挙失敗は無視 (他のデバイスの取得は続行)
                    continue
        except Exception:
            errorLogging()
        return result
