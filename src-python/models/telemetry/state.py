"""
テレメトリ状態管理
- enable/disable フラグ
- 最終操作時刻
- セッション内送信済み機能リスト
"""
from datetime import datetime
from threading import Lock


class TelemetryState:
    def __init__(self):
        self._enabled = True  # デフォルト有効
        self._session_features_sent = set()
        self._lock = Lock()
    
    def set_enabled(self, value: bool):
        """有効/無効設定"""
        with self._lock:
            self._enabled = bool(value)
            if not self._enabled:
                self._session_features_sent.clear()
    
    def is_enabled(self) -> bool:
        """有効状態確認"""
        with self._lock:
            return self._enabled
    
    def record_feature_sent(self, feature: str):
        """送信済み機能を記録"""
        with self._lock:
            self._session_features_sent.add(feature)
    
    def has_feature_been_sent(self, feature: str) -> bool:
        """機能がこのセッション内で送信済みか"""
        with self._lock:
            return feature in self._session_features_sent
    
    def reset(self):
        """状態をリセット"""
        with self._lock:
            self._session_features_sent.clear()
    
    def get_debug_info(self) -> dict:
        """デバッグ用情報取得"""
        with self._lock:
            return {
                "enabled": self._enabled,
                "session_features_sent": list(self._session_features_sent),
            }
