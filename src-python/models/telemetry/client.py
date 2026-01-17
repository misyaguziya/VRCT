"""
Aptabase SDK ラッパー（非同期版）
"""
from typing import Optional, Dict, Any

# Aptabase SDK のインポート
try:
    from aptabase import Aptabase
except ImportError:
    Aptabase = None


class AptabaseWrapper:
    APP_KEY = "A-US-2082730845"
    
    def __init__(self):
        self.client = None
    
    async def start(self, app_version: str = "1.0.0"):
        """Aptabase クライアント開始"""
        if Aptabase is None:
            raise ImportError("aptabase library not installed")
        try:
            self.client = Aptabase(
                app_key=self.APP_KEY,
                app_version=app_version,
                is_debug=False,
                max_batch_size=25,
                flush_interval=10.0,
                timeout=30.0
            )
            await self.client.start()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Aptabase: {e}")
    
    async def track(self, event_name: str, properties: Optional[Dict[str, Any]] = None):
        """イベント送信（非同期）"""
        if self.client is None:
            return

        # properties が None なら空辞書
        if properties is None:
            properties = {}

        try:
            await self.client.track(event_name, properties)
        except Exception:
            # テレメトリ送信失敗は黙殺（本体処理を止めない）
            pass
    
    async def stop(self):
        """クライアント停止（フラッシュ含む）"""
        if self.client is not None:
            try:
                await self.client.stop()
            except Exception:
                pass
            self.client = None
