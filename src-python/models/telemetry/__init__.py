"""
テレメトリ（Aptabase）管理モジュール

送信するイベントは 2 種類のみ:
    - app_started: 起動時、日次で 1 回のみ
    - error:       エラー発生時、error_code ごとに日次で 1 回のみ

パブリック API を提供し、内部実装を隠蔽する。
"""
import asyncio
import threading
from typing import Optional

# Aptabase → httpx → httpcore → anyio の依存チェーンで、httpx.AsyncClient の
# aclose() が最終的に anyio._core._eventloop.get_async_backend() を呼び、
# そこで anyio._backends._asyncio が遅延 import される。この遅延 import は
# @dataclass を大量に評価するため Python の暗黙 GC (generation 2) を発火し、
# ActiveEndpointTracker が保持している comtypes の COM ポインタを、
# CoInitialize していないテレメトリスレッド上で __del__ → Release() させて
# access violation を起こす。この経路は telemetry.shutdown() の
# _shutdown_async() 中に確定的に踏まれる (crash_trace.log 2026-08-20)。
# 本モジュールは Model.__init__ 経由で起動時に import されるため、
# ここで anyio backend も事前 import しておけば、shutdown 時の遅延 import
# は発生せず GC トリガも消える。
try:
    import anyio._backends._asyncio  # noqa: F401
except Exception:
    pass

# Allow running as a script for quick verification.
try:
    from .state import TelemetryState
    from .core import TelemetryCore
except ImportError:
    import os
    import sys

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from models.telemetry.state import TelemetryState
    from models.telemetry.core import TelemetryCore


class Telemetry:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.state = TelemetryState()
        self.core = TelemetryCore(self.state)
        self._loop = None
        self._loop_thread = None
        self._init_called = False
        self._initialized = True

    # ---- event loop management ----

    def _start_event_loop(self):
        if self._loop_thread is not None and self._loop_thread.is_alive():
            return

        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()

        self._loop_thread = threading.Thread(target=run_loop, daemon=True, name="telemetry_loop")
        self._loop_thread.start()
        while self._loop is None:
            pass

    def _stop_event_loop(self, timeout: float = 5.0):
        if self._loop is None:
            return
        self._loop.call_soon_threadsafe(self._loop.stop)
        if self._loop_thread is not None:
            self._loop_thread.join(timeout=timeout)
        self._loop = None
        self._loop_thread = None

    def _run_async(self, coro):
        if self._loop is None:
            return
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return future.result(timeout=5.0)
        except Exception:
            pass

    def _schedule_async(self, coro):
        if self._loop is None:
            return
        try:
            asyncio.run_coroutine_threadsafe(coro, self._loop)
        except Exception:
            pass

    # ---- public API ----

    def init(self, enabled: bool, app_version: str = "1.0.0", storage_path: Optional[str] = None):
        """テレメトリ初期化（冪等）。

        - 有効時のみイベントループを起動し、app_started を（その日未送信なら）送信する。
        - storage_path が指定されていれば、日次デデュープ用の永続 state ファイルとして使う。
        """
        if storage_path:
            self.state.set_storage_path(storage_path)

        if self._init_called:
            self.state.set_enabled(enabled)
            return

        self._init_called = True
        self.state.set_enabled(enabled)
        if enabled:
            self._start_event_loop()
            self._run_async(self._init_async(app_version))

    async def _init_async(self, app_version: str):
        await self.core.start(app_version=app_version)
        if self.state.should_send_app_started_today():
            await self.core.send_event("app_started")
            self.state.mark_app_started_sent_today()

    def shutdown(self):
        """テレメトリ終了。Aptabase クライアントを停止し、イベントループを閉じる。"""
        try:
            if self.state.is_enabled():
                try:
                    self._run_async(self._shutdown_async())
                except Exception:
                    pass
            self._stop_event_loop(timeout=5.0)
        except Exception:
            pass
        finally:
            self.state.reset()
            self._init_called = False

    async def _shutdown_async(self):
        await self.core.stop()

    def track_error(self, error_code: str):
        """エラーイベント送信（同期インターフェース）。

        - enabled=False では何もしない
        - 同じ error_code はその日すでに送信済みなら無視する
        - 送信スケジュール前に mark_error_sent_today を呼ぶことで、高頻度呼び出しでも重複しない
        """
        if not self.state.is_enabled():
            return
        if not error_code:
            return
        if not self.state.should_send_error_today(error_code):
            return
        # 先にデデュープ状態を確定してから送信する（レース防止）
        self.state.mark_error_sent_today(error_code)
        self._schedule_async(self.core.send_event("error", {"error_code": error_code}))

    def is_enabled(self) -> bool:
        return self.state.is_enabled()

    def get_state(self) -> dict:
        return self.state.get_debug_info()


if __name__ == "__main__":
    # 動作確認: 一時ファイルに state を書きつつ error を 2 回呼んで、1 回のみ送信されることを確認する
    import tempfile
    import time

    with tempfile.TemporaryDirectory() as tmp:
        storage = f"{tmp}/telemetry_state.json"
        telemetry = Telemetry()
        telemetry.init(enabled=True, storage_path=storage)
        telemetry.track_error("DEMO_ERROR")
        telemetry.track_error("DEMO_ERROR")  # 重複、送信されない
        print("state:", telemetry.get_state())
        time.sleep(1)
        telemetry.shutdown()
        print("telemetry demo finished")
