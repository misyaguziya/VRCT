"""
Heartbeat スレッド管理
- 5分間隔でアクティブ確認
- 操作なしで5分経過したら送信停止
"""
from datetime import datetime
from threading import Thread, Event
import time


class HeartbeatManager:
    INTERVAL = 300  # 5 minutes
    TIMEOUT = 300   # 5 minutes
    
    def __init__(self, state, core, schedule_async):
        self.state = state
        self.core = core
        self.schedule_async = schedule_async
        self.thread = None
        self._stop_event = Event()
    
    def start(self):
        """Heartbeat スレッド開始"""
        if self.thread is not None and self.thread.is_alive():
            return
        self._stop_event.clear()
        self.thread = Thread(target=self._run, daemon=True, name="telemetry_heartbeat")
        self.thread.start()
    
    def stop(self):
        """Heartbeat スレッド停止"""
        self._stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=1.0)
            self.thread = None
    
    def _run(self):
        """Heartbeat ループ"""
        while not self._stop_event.is_set():
            time.sleep(self.INTERVAL)

            if not self.state.is_enabled():
                continue

            last_activity = self.state.get_last_activity()
            if last_activity is None:
                continue

            elapsed = (datetime.now() - last_activity).total_seconds()
            if elapsed < self.TIMEOUT:
                # アクティブなら heartbeat 送信（非同期スケジュール）
                if self.core.client is not None:
                    self.schedule_async(self.core.send_event("session_heartbeat"))
