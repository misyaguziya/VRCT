"""
テレメトリコアロジック
- イベント構築・送信
- 重複検出
"""

from .client import AptabaseWrapper
from .state import TelemetryState


class TelemetryCore:
    VALID_CORE_FEATURES = {
        "translation",
        "mic_speech_to_text",
        "speaker_speech_to_text",
        "text_input",
    }
    
    def __init__(self, state: TelemetryState):
        self.state = state
        self.client = None
        try:
            self.client = AptabaseWrapper()
        except Exception:
            self.client = None
    
    async def start(self, app_version: str = "1.0.0"):
        """Aptabase クライアント開始"""
        if self.client is None:
            return
        try:
            await self.client.start(app_version=app_version)
        except Exception:
            self.client = None
    
    async def stop(self):
        """Aptabase クライアント停止"""
        if self.client is not None:
            try:
                await self.client.stop()
            except Exception:
                pass
    
    async def send_event(self, event_name: str, payload: dict = None):
        """イベント送信（非同期）"""
        if self.client is None:
            return
        
        # ペイロード準備
        properties = payload or {}
        
        # イベント送信
        await self.client.track(event_name, properties)
    
    def is_duplicate_core_feature(self, feature: str) -> bool:
        """セッション内の重複チェック"""
        return self.state.has_feature_been_sent(feature)
