# models/websocket — 詳細設計

目的: 外部クライアント（例えば第三者のアプリ）へ翻訳済みテキストやイベントをブロードキャストする軽量 WebSocket サーバー。

API:
- class WebSocketServer(host='127.0.0.1', port=8765)
  - start(): 別スレッドで asyncio ループを生成しサーバを起動。
  - stop(): サーバ停止、全クライアント切断。
  - set_message_handler(handler): クライアントからのメッセージ受信時のコールバックを登録。handler(server, websocket, message)
  - send(message): 非同期キューに積んで全クライアントへ送信（スレッドセーフ）。
  - broadcast(message): asyncio を経由して即時ブロードキャスト。

実装上の工夫:
- サーバ本体は別スレッドで asyncio イベントループを run_forever している。
- 送信用に内部キュー `_send_queue` を持ち、_send_loop で順次送信する。これにより GUI 等から安全に send() を呼べる。

依存: websockets（asyncio）

