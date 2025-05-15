import asyncio
import json
import logging
from typing import Dict, Set, Optional
import websockets
from websockets.server import WebSocketServerProtocol

class WebSocketServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.server = None
        self.is_running = False
        self.logger = logging.getLogger('websocket_server')

    async def register(self, websocket: WebSocketServerProtocol):
        """クライアント接続を登録する"""
        self.clients.add(websocket)
        self.logger.info(f"クライアント接続: {websocket.remote_address}, 現在の接続数: {len(self.clients)}")

    async def unregister(self, websocket: WebSocketServerProtocol):
        """クライアント接続を解除する"""
        self.clients.remove(websocket)
        self.logger.info(f"クライアント切断: {websocket.remote_address}, 現在の接続数: {len(self.clients)}")

    async def handler(self, websocket: WebSocketServerProtocol, path: str):
        """WebSocket接続ハンドラー"""
        await self.register(websocket)
        try:
            async for message in websocket:
                # クライアントからのメッセージを処理（必要に応じて）
                # 現在はクライアントからのメッセージは特に処理していません
                self.logger.debug(f"クライアントからのメッセージ: {message}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)

    async def broadcast(self, message: Dict):
        """全クライアントにメッセージをブロードキャストする"""
        if not self.clients:
            return

        json_message = json.dumps(message)
        tasks = [client.send(json_message) for client in self.clients]
        await asyncio.gather(*tasks, return_exceptions=True)

    def send_transcription(self, transcription_data: Dict):
        """文字起こし結果を送信する関数（通常のコードから呼び出し可能）"""
        if not self.is_running or not self.clients:
            return

        # asyncioのイベントループがあれば利用し、なければ新たに作成
        loop = asyncio.get_event_loop() if asyncio.get_event_loop().is_running() else asyncio.new_event_loop()
        
        # ブロードキャスト関数を実行
        asyncio.run_coroutine_threadsafe(
            self.broadcast(transcription_data),
            loop
        )

    async def start_server(self):
        """WebSocketサーバーを起動する"""
        if not self.is_running:
            self.server = await websockets.serve(self.handler, self.host, self.port)
            self.is_running = True
            self.logger.info(f"WebSocketサーバーを起動しました - {self.host}:{self.port}")
            return True
        return False

    def start(self):
        """非同期ループでWebSocketサーバーを起動する（通常のコードから呼び出し可能）"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.start_server())
        # バックグラウンドでループを実行
        self._task = asyncio.run_coroutine_threadsafe(self._run_forever(), loop)

    async def _run_forever(self):
        """サーバーを永続的に実行する"""
        while self.is_running:
            await asyncio.sleep(0.1)

    async def stop_server(self):
        """WebSocketサーバーを停止する"""
        if self.is_running and self.server:
            self.server.close()
            await self.server.wait_closed()
            self.is_running = False
            self.clients.clear()
            self.logger.info("WebSocketサーバーを停止しました")
            return True
        return False

    def stop(self):
        """WebSocketサーバーを停止する（通常のコードから呼び出し可能）"""
        if not self.is_running:
            return

        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(self.stop_server(), loop)
