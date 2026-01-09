"""
テレメトリ（Aptabase）管理モジュール

パブリック API を提供し、内部実装を隠蔽する。
"""
import asyncio
import threading
from concurrent.futures import Future

# Allow running as a script for quick verification.
try:
    from .state import TelemetryState
    from .heartbeat import HeartbeatManager
    from .core import TelemetryCore
except ImportError:
    import os
    import sys

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from models.telemetry.state import TelemetryState
    from models.telemetry.heartbeat import HeartbeatManager
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
        self.heartbeat = HeartbeatManager(self.state, self.core, self._schedule_async_with_loop)
        self._loop = None
        self._loop_thread = None
        self._initialized = True
    
    def _start_event_loop(self):
        """バックグラウンドでイベントループを開始"""
        if self._loop_thread is not None and self._loop_thread.is_alive():
            return
        
        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()
        
        self._loop_thread = threading.Thread(target=run_loop, daemon=True, name="telemetry_loop")
        self._loop_thread.start()
        
        # ループが開始されるまで待機
        while self._loop is None:
            pass
    
    def _stop_event_loop(self, timeout: float = 5.0):
        """イベントループを停止（フラッシュ完了を待つ）"""
        if self._loop is None:
            return
        
        # ループにstop()を予約
        self._loop.call_soon_threadsafe(self._loop.stop)
        
        # ループスレッド終了を待機
        if self._loop_thread is not None:
            self._loop_thread.join(timeout=timeout)
        
        self._loop = None
        self._loop_thread = None
    
    def _run_async(self, coro):
        """同期コンテキストから非同期関数を実行"""
        if self._loop is None:
            return
        
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            # タイムアウト付きで待機（ブロッキングしすぎないように）
            return future.result(timeout=5.0)
        except Exception:
            # テレメトリ失敗は黙殺
            pass
    
    def _schedule_async(self, coro):
        """非同期タスクをバックグラウンドでスケジュール（待機しない）"""
        if self._loop is None:
            return
        
        try:
            asyncio.run_coroutine_threadsafe(coro, self._loop)
        except Exception:
            pass
    
    def _schedule_async_with_loop(self, coro):
        """ループ取得とスケジューリングのヘルパー（heartbeat用）"""
        return self._schedule_async(coro)
    
    def init(self, enabled: bool, app_version: str = "1.0.0"):
        """テレメトリ初期化（同期インターフェース）"""
        self.state.set_enabled(enabled)
        if enabled:
            self._start_event_loop()
            self._run_async(self._init_async(app_version))
    
    async def _init_async(self, app_version: str):
        """非同期初期化処理"""
        await self.core.start(app_version=app_version)
        await self.core.send_event("app_started")
        self.heartbeat.start()
    
    def shutdown(self):
        """テレメトリ終了（同期インターフェース）
        
        重要：Tauri sidecar環境では、このメソッド実行後にプロセス終了が発生します。
        app_closed イベントが確実に送信されるように、以下の手順を実行します：
        1. heartbeat スレッド停止
        2. app_closed イベント送信を同期待機
        3. Aptabase クライアント停止（フラッシュ含む）
        4. イベントループ完全停止を待機
        """
        try:
            # Step 1: Heartbeat 停止（5分待機中の送信を防ぐ）
            self.heartbeat.stop()
            
            # Step 2-3: app_closed 送信とクライアント停止を同期待機
            if self.state.is_enabled():
                try:
                    # _run_async で最大5秒間待機（Aptabase のフラッシュ含む）
                    self._run_async(self._shutdown_async())
                except Exception:
                    pass
            
            # Step 4: イベントループを完全停止（フラッシュ確認を待つ）
            # sidecar 終了前に確実に完了させるため、タイムアウトを長めに設定
            self._stop_event_loop(timeout=5.0)
        except Exception:
            # どの段階で失敗してもプロセス終了処理は進行させる
            pass
        finally:
            # 状態をリセット
            self.state.reset()
    
    async def _shutdown_async(self):
        """非同期終了処理"""
        await self.core.send_event("app_closed")
        await self.core.stop()
    
    def track(self, event: str, payload: dict = None):
        """汎用イベント送信（同期インターフェース）"""
        if not self.state.is_enabled():
            return
        self._schedule_async(self.core.send_event(event, payload))
    
    def track_core_feature(self, feature: str):
        """コア機能イベント送信（同期インターフェース）"""
        if not self.state.is_enabled():
            return
        self.state.touch_activity()
        if self.core.is_duplicate_core_feature(feature):
            return
        self._schedule_async(self._track_core_feature_async(feature))
    
    async def _track_core_feature_async(self, feature: str):
        """非同期コア機能送信処理"""
        await self.core.send_event("core_feature", {"feature": feature})
        self.state.record_feature_sent(feature)
    
    def touch_activity(self):
        """アクティビティ時刻更新"""
        if self.state.is_enabled():
            self.state.touch_activity()
    
    def is_enabled(self) -> bool:
        """有効状態確認"""
        return self.state.is_enabled()
    
    def get_state(self) -> dict:
        """内部状態取得（デバッグ用）"""
        return self.state.get_debug_info()


if __name__ == "__main__":
    # 同期インターフェースのデモ
    telemetry = Telemetry()
    telemetry.init(enabled=True)
    telemetry.track("debug_test", {"message": "telemetry main demo"})
    telemetry.track_core_feature("text_input")
    telemetry.touch_activity()
    print("state:", telemetry.get_state())
    
    # イベント送信完了を待つ
    import time
    time.sleep(2)
    
    telemetry.shutdown()
    print("telemetry demo finished")

