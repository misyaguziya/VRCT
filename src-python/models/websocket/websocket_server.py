import asyncio
import threading
import websockets
from websockets.legacy.server import WebSocketServerProtocol
from typing import Callable, Set, Optional

class WebSocketServer:
    """
    WebSocketサーバーを管理するクラス。
    主な機能:
    - サーバーの起動・停止
    - クライアント接続管理 (接続/切断の追跡)
    - メッセージ受信のコールバック処理
    - メッセージのブロードキャスト機能
    - GUIスレッド等からメッセージ送信するためのキュー
    """
    def __init__(self, host: str='localhost', port: int=8765):
        """
        サーバーのホスト名とポートを指定して初期化します。
        """
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()  # 接続クライアント集合
        self._message_handler: Optional[Callable[['WebSocketServer', WebSocketServerProtocol, str], None]] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._server: Optional[websockets.serve] = None
        self._thread: Optional[threading.Thread] = None
        self._send_queue: Optional[asyncio.Queue] = None  # 外部スレッド向け非同期キュー
        self.is_running: bool = False  # サーバーの起動状態を示すフラグ

    def set_message_handler(self, handler: Callable[['WebSocketServer', WebSocketServerProtocol, str], None]):
        """
        クライアントからメッセージ受信時に呼び出すコールバックを設定します。
        コールバックのシグネチャ: (server, websocket, message) -> None
        """
        self._message_handler = handler

    async def _handler(self, websocket):
        """
        単一クライアントとのセッションを処理するハンドラです。
        新規接続時にクライアントを集合に追加し、メッセージを受信してコールバックを呼び出します。
        切断時には集合からクライアントを削除します。
        """
        # 接続クライアントを集合に追加
        self.clients.add(websocket)
        try:
            async for message in websocket:
                # メッセージ受信時にコールバック呼び出し
                if self._message_handler:
                    self._message_handler(self, websocket, message)
        except websockets.exceptions.ConnectionClosed:
            # クライアントが切断した場合
            pass
        finally:
            # 切断時に集合から削除
            self.clients.remove(websocket)

    async def _broadcast_async(self, message: str):
        """
        すべての接続クライアントにメッセージを送信する非同期メソッド。
        """
        if not self.clients:
            return
        # 全クライアントへ並列に送信
        await asyncio.gather(
            *[client.send(message) for client in self.clients],
            return_exceptions=True
        )

    async def _send_loop(self):
        """
        内部キューからメッセージを取り出し、すべてのクライアントに送信するループ処理。
        GUIなど他スレッドから送信メッセージをキューに入れてもらい、このコルーチンで配信します。
        """
        assert self._send_queue is not None
        while True:
            message = await self._send_queue.get()
            if message is None:
                # Noneを受け取ったらシャットダウン指示とみなしてループを抜ける
                break
            await self._broadcast_async(message)

    def send(self, message: str):
        """
        外部スレッドからサーバーにメッセージを送信するためのメソッドです。
        イベントループ上で安全にキューにメッセージを積み、_send_loop()経由でブロードキャストします。
        """
        if self._loop and self._send_queue:
            # キューにput_nowaitするコールをイベントループにスケジュール
            self._loop.call_soon_threadsafe(self._send_queue.put_nowait, message)

    def broadcast(self, message: str):
        """
        外部スレッドや他コルーチンから全クライアントにメッセージを送信するユーティリティ。
        asyncio.run_coroutine_threadsafe を使ってループ上でブロードキャストを実行します。
        """
        if self._loop:
            # コルーチン自体をrun_coroutine_threadsafeに渡す
            asyncio.run_coroutine_threadsafe(
                self._broadcast_async(message), self._loop
            )

    def start(self):
        """
        サーバーを起動します。新しいスレッド上で asyncio イベントループを動かし、serve()を実行します。
        """
        if self._thread and self._thread.is_alive():
            return  # 既に起動中
        # 新しいスレッドでイベントループを開始
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        """
        別スレッド上で実行されるイベントループ用のメソッド。
        サーバーの起動と、送信用キューのタスク登録を行います。
        """
        # 新しいイベントループを作成してこのスレッドの現在のループとして設定
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        async def setup_server():
            # サーバーを起動し、listenを開始
            self._server = await websockets.serve(self._handler, self.host, self.port)
            # 送信キューを初期化
            self._send_queue = asyncio.Queue()
            # 送信ループタスクを開始
            self._loop.create_task(self._send_loop())
            # サーバーの起動を待機
        # 設定関数を実行してサーバーを起動
        self._loop.run_until_complete(setup_server())
        self.is_running = True
        # サーバーが起動したら、接続待機を開始
        # print(f"WebSocket server started on ws://{self.host}:{self.port}")
        try:
            # サーバーが停止するまでループを継続
            self._loop.run_forever()
        finally:
            # 停止指示が出たらすべての接続を閉じ、イベントループを終了
            self._loop.run_until_complete(self._shutdown())
            self._loop.close()

    async def _shutdown(self):
        """
        サーバーとクライアントを安全にシャットダウンする非同期処理。
        serveオブジェクトをcloseし、wait_closed()で完全に終了を待ちます。
        さらに接続中の各WebSocketをcloseします。
        """
        # サーバーのListenを停止
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        # 接続中クライアントを順次クローズ
        for ws in list(self.clients):
            try:
                await ws.close()
            except Exception:
                pass

    def stop(self):
        """
        サーバーを停止します。別スレッドで動作中のイベントループに停止を指示し、スレッドを終了させます。
        """
        self.is_running = False
        if self._loop:
            # サーバーのlistenを停止し、ループ停止をスケジュール
            self._loop.call_soon_threadsafe(self._server.close)
            # None をキューに入れて_send_loopを抜けさせる
            self._loop.call_soon_threadsafe(self._send_queue.put_nowait, None)
            # ループ停止
            self._loop.call_soon_threadsafe(self._loop.stop)
        # スレッドの終了を待つ
        if self._thread:
            self._thread.join()

if __name__ == "__main__":
    # テスト用の簡単なメッセージハンドラ
    def message_handler(server: WebSocketServer, websocket: WebSocketServerProtocol, message: str):
        print(f"Received message from {websocket.remote_address}: {message}")
        server.send(f"Echo: {message}")

    def send_message(server: WebSocketServer, message: str):
        server.send(message)

    # メイン処理を非同期関数に変更
    async def main():
        # サーバーを起動してメッセージハンドラを設定
        ws_server = WebSocketServer()
        ws_server.set_message_handler(message_handler)
        ws_server.start()
        print("WebSocket server started.")
        # 定期的にサーバーからメッセージを送信する例
        import threading
        import time
        def periodic_send():
            print("Starting periodic message sender...")
            while ws_server.is_running:
                time.sleep(5)
                print("Sending periodic message...")
                send_message(ws_server, "Periodic message")
            print("Periodic message sender stopped.")
        # 別スレッドで定期的にメッセージを送信
        time.sleep(5)
        send_thread = threading.Thread(target=periodic_send, daemon=True)
        send_thread.start()
        # メインスレッドでサーバーを動かし続ける
        try:
            while True:
                # 非同期スリープで待機
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            # Ctrl+Cでサーバーを停止
            print("Stopping WebSocket server...")
            ws_server.stop()

    # 非同期メイン関数を実行
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopping WebSocket server...")