"""
Aptabase SDK ラッパー（非同期版）
"""
import logging
from typing import Optional, Dict, Any

# Aptabase SDK のインポート
try:
    from aptabase import Aptabase
except ImportError:
    Aptabase = None

try:
    from build_channel import BUILD_CHANNEL
except ImportError:
    import os
    import sys

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from build_channel import BUILD_CHANNEL


class AptabaseWrapper:
    # stable/beta で別の Aptabase プロジェクトを使う。どちらを使うかは
    # build_channel.BUILD_CHANNEL の1行だけで切り替える（マージ時の
    # APP_KEY 取り違えを防ぐため）。
    APP_KEYS = {
        "stable": "A-US-3414271507",
        "beta": "A-US-6044063021",
    }
    APP_KEY = APP_KEYS[BUILD_CHANNEL]

    def __init__(self):
        self.client = None
        # Suppress noisy logs from the Aptabase SDK (only CRITICAL allowed)
        logging.getLogger("aptabase").setLevel(logging.CRITICAL)
    
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
