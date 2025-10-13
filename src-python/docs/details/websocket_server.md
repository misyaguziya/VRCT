# websocket_server.py - WebSocket通信サーバー

## 概要

非同期WebSocket通信を提供する包括的なサーバーシステムです。クライアント接続管理、メッセージ配信、外部スレッドからの安全な操作を統合し、VRCTアプリケーションとWebフロントエンド間のリアルタイム通信を実現します。

## 主要機能

### 非同期WebSocket通信
- asyncio/websockets による高性能WebSocketサーバー
- 複数クライアント同時接続対応
- 自動接続・切断管理

### メッセージング機能
- リアルタイムメッセージ受信処理
- 全クライアントへのブロードキャスト配信
- カスタムメッセージハンドラー対応

### スレッド間通信
- GUI等の外部スレッドからの安全なメッセージ送信
- 非同期キューによる効率的な通信制御
- スレッドセーフな操作保証

## クラス構造

### WebSocketServer クラス

```python
class WebSocketServer:
    def __init__(self, host: str='127.0.0.1', port: int=8765):
        self.host: str                          # サーバーホスト
        self.port: int                          # サーバーポート
        self.clients: Set[WebSocketServerProtocol] # 接続クライアント集合
        self._message_handler: Optional[Callable]   # メッセージハンドラー
        self._loop: Optional[asyncio.AbstractEventLoop] # イベントループ
        self._server: Optional[websockets.serve]    # WebSocketサーバー
        self._thread: Optional[threading.Thread]    # サーバースレッド
        self._send_queue: Optional[asyncio.Queue]   # 送信キュー
        self.is_running: bool                   # 動作状態フラグ
```

WebSocket通信の中核管理クラス

## 主要メソッド

### サーバー制御

```python
def start_server(self) -> None
```

WebSocketサーバーを開始（バックグラウンドスレッド）

```python
def stop_server(self) -> None
```

WebSocketサーバーを停止・リソース解放

### メッセージハンドリング

```python
def set_message_handler(self, handler: Callable[['WebSocketServer', WebSocketServerProtocol, str], None]) -> None
```

クライアントからのメッセージ受信時コールバック設定

#### パラメータ
- **handler**: メッセージハンドラー関数 `(server, websocket, message) -> None`

### メッセージ送信

```python
def send(self, message: str) -> None
```

外部スレッドから安全にメッセージを全クライアントに送信

#### パラメータ
- **message**: 送信するメッセージ文字列

```python
def broadcast(self, message: str) -> None
```

非同期的に全クライアントにメッセージをブロードキャスト

#### パラメータ
- **message**: ブロードキャストするメッセージ

## 使用方法

### 基本的なWebSocketサーバー

```python
from models.websocket.websocket_server import WebSocketServer
import time
import json

# メッセージハンドラーの定義
def on_message_received(server, websocket, message):
    """クライアントからのメッセージ処理"""
    print(f"クライアントからメッセージ受信: {message}")
    
    try:
        # JSONメッセージの解析
        data = json.loads(message)
        
        if data.get('type') == 'translation_request':
            # 翻訳要求の処理
            handle_translation_request(server, data)
        elif data.get('type') == 'config_update':
            # 設定更新の処理
            handle_config_update(server, data)
        else:
            # エコーバック
            response = {
                'type': 'echo',
                'original_message': data,
                'timestamp': time.time()
            }
            server.broadcast(json.dumps(response))
            
    except json.JSONDecodeError:
        # テキストメッセージの場合
        response = f"受信しました: {message}"
        server.broadcast(response)

def handle_translation_request(server, data):
    """翻訳要求の処理"""
    text = data.get('text', '')
    target_lang = data.get('target_language', 'English')
    
    # 実際の翻訳処理（ここではモック）
    translated_text = f"[{target_lang}] {text}"
    
    response = {
        'type': 'translation_result',
        'original': text,
        'translated': translated_text,
        'target_language': target_lang
    }
    
    server.broadcast(json.dumps(response))

def handle_config_update(server, data):
    """設定更新の処理"""
    config_key = data.get('key')
    config_value = data.get('value')
    
    print(f"設定更新: {config_key} = {config_value}")
    
    response = {
        'type': 'config_updated',
        'key': config_key,
        'value': config_value,
        'status': 'success'
    }
    
    server.broadcast(json.dumps(response))

# WebSocketサーバーの起動
ws_server = WebSocketServer(host='127.0.0.1', port=8765)
ws_server.set_message_handler(on_message_received)
ws_server.start_server()

print("WebSocketサーバーが起動しました: ws://127.0.0.1:8765")

# 定期的なステータス送信
for i in range(10):
    status_message = {
        'type': 'status',
        'server_time': time.time(),
        'uptime': i * 5,
        'connected_clients': len(ws_server.clients)
    }
    
    ws_server.send(json.dumps(status_message))
    time.sleep(5)

# サーバー停止
ws_server.stop_server()
```

### VRCTアプリケーション統合

```python
class VRCTWebSocketInterface:
    """VRCT用WebSocketインターフェース"""
    
    def __init__(self, controller, port=8765):
        self.controller = controller  # VRCTコントローラー
        self.ws_server = WebSocketServer(host='127.0.0.1', port=port)
        self.ws_server.set_message_handler(self.handle_web_message)
        
    def handle_web_message(self, server, websocket, message):
        """Webクライアントからのメッセージ処理"""
        try:
            data = json.loads(message)
            command = data.get('command')
            
            if command == 'get_config':
                self.send_config(server)
            elif command == 'set_config':
                self.update_config(server, data)
            elif command == 'start_translation':
                self.start_translation_service(server, data)
            elif command == 'stop_translation':
                self.stop_translation_service(server)
            elif command == 'get_status':
                self.send_status(server)
            elif command == 'translate_text':
                self.translate_text(server, data)
            else:
                self.send_error(server, f"未知のコマンド: {command}")
                
        except Exception as e:
            self.send_error(server, f"メッセージ処理エラー: {e}")
    
    def send_config(self, server):
        """設定情報をWebクライアントに送信"""
        config_data = {
            'type': 'config',
            'data': {
                'source_language': self.controller.config.source_language,
                'target_language': self.controller.config.target_language,
                'translation_engine': self.controller.config.translation_engine,
                'osc_enabled': self.controller.config.osc_enabled,
                'overlay_enabled': self.controller.config.overlay_enabled
            }
        }
        server.broadcast(json.dumps(config_data))
    
    def update_config(self, server, data):
        """設定更新"""
        config_updates = data.get('config', {})
        
        for key, value in config_updates.items():
            if hasattr(self.controller.config, key):
                setattr(self.controller.config, key, value)
                print(f"設定更新: {key} = {value}")
        
        # 更新確認を送信
        response = {
            'type': 'config_updated',
            'status': 'success',
            'updated_keys': list(config_updates.keys())
        }
        server.broadcast(json.dumps(response))
    
    def start_translation_service(self, server, data):
        """翻訳サービス開始"""
        try:
            self.controller.start_translation()
            
            response = {
                'type': 'service_status',
                'service': 'translation',
                'status': 'started',
                'message': '翻訳サービスが開始されました'
            }
            server.broadcast(json.dumps(response))
            
        except Exception as e:
            self.send_error(server, f"翻訳サービス開始エラー: {e}")
    
    def stop_translation_service(self, server):
        """翻訳サービス停止"""
        try:
            self.controller.stop_translation()
            
            response = {
                'type': 'service_status',
                'service': 'translation',
                'status': 'stopped',
                'message': '翻訳サービスが停止されました'
            }
            server.broadcast(json.dumps(response))
            
        except Exception as e:
            self.send_error(server, f"翻訳サービス停止エラー: {e}")
    
    def send_status(self, server):
        """システム状態送信"""
        status_data = {
            'type': 'system_status',
            'data': {
                'translation_active': self.controller.is_translation_active(),
                'osc_connected': self.controller.is_osc_connected(),
                'overlay_active': self.controller.is_overlay_active(),
                'connected_clients': len(server.clients),
                'uptime': self.controller.get_uptime(),
                'memory_usage': self.controller.get_memory_usage()
            }
        }
        server.broadcast(json.dumps(status_data))
    
    def translate_text(self, server, data):
        """即座翻訳実行"""
        text = data.get('text', '')
        source_lang = data.get('source_language')
        target_lang = data.get('target_language')
        
        try:
            # 翻訳実行
            result = self.controller.translate_text(
                text, source_lang, target_lang
            )
            
            response = {
                'type': 'translation_result',
                'original': text,
                'translated': result,
                'source_language': source_lang,
                'target_language': target_lang,
                'timestamp': time.time()
            }
            server.broadcast(json.dumps(response))
            
        except Exception as e:
            self.send_error(server, f"翻訳エラー: {e}")
    
    def send_error(self, server, error_message):
        """エラーメッセージ送信"""
        error_data = {
            'type': 'error',
            'message': error_message,
            'timestamp': time.time()
        }
        server.broadcast(json.dumps(error_data))
    
    def start(self):
        """WebSocketインターフェース開始"""
        self.ws_server.start_server()
        print(f"VRCT WebSocketインターフェース開始: ws://127.0.0.1:{self.ws_server.port}")
    
    def stop(self):
        """WebSocketインターフェース停止"""
        self.ws_server.stop_server()
        print("VRCT WebSocketインターフェース停止")
    
    def notify_translation_result(self, original, translated, source_lang, target_lang):
        """翻訳結果の通知（VRCTコントローラーから呼び出し）"""
        notification = {
            'type': 'live_translation',
            'original': original,
            'translated': translated,
            'source_language': source_lang,
            'target_language': target_lang,
            'timestamp': time.time()
        }
        self.ws_server.send(json.dumps(notification))

# 使用例（VRCTアプリケーション内）
# vrct_ws_interface = VRCTWebSocketInterface(controller)
# vrct_ws_interface.start()
```

### リアルタイム監視ダッシュボード

```python
class MonitoringDashboard:
    """リアルタイム監視ダッシュボード"""
    
    def __init__(self, system_components, port=8766):
        self.components = system_components
        self.ws_server = WebSocketServer(host='127.0.0.1', port=port)
        self.ws_server.set_message_handler(self.handle_dashboard_message)
        self.monitoring_active = False
        
    def handle_dashboard_message(self, server, websocket, message):
        """ダッシュボードからのメッセージ処理"""
        try:
            data = json.loads(message)
            action = data.get('action')
            
            if action == 'start_monitoring':
                self.start_monitoring(server)
            elif action == 'stop_monitoring':
                self.stop_monitoring(server)
            elif action == 'get_metrics':
                self.send_metrics(server)
            elif action == 'get_logs':
                self.send_logs(server, data.get('limit', 100))
            
        except Exception as e:
            self.send_dashboard_error(server, str(e))
    
    def start_monitoring(self, server):
        """監視開始"""
        if not self.monitoring_active:
            self.monitoring_active = True
            
            # 監視スレッド開始
            import threading
            monitor_thread = threading.Thread(
                target=self.monitoring_loop, 
                args=(server,), 
                daemon=True
            )
            monitor_thread.start()
            
            response = {
                'type': 'monitoring_status',
                'status': 'started'
            }
            server.broadcast(json.dumps(response))
    
    def stop_monitoring(self, server):
        """監視停止"""
        self.monitoring_active = False
        
        response = {
            'type': 'monitoring_status',
            'status': 'stopped'
        }
        server.broadcast(json.dumps(response))
    
    def monitoring_loop(self, server):
        """リアルタイム監視ループ"""
        while self.monitoring_active:
            try:
                # システムメトリクス収集
                metrics = self.collect_metrics()
                
                # ダッシュボードに送信
                dashboard_data = {
                    'type': 'live_metrics',
                    'metrics': metrics,
                    'timestamp': time.time()
                }
                server.broadcast(json.dumps(dashboard_data))
                
                time.sleep(2)  # 2秒間隔で更新
                
            except Exception as e:
                print(f"監視ループエラー: {e}")
                time.sleep(5)
    
    def collect_metrics(self):
        """システムメトリクス収集"""
        import psutil
        
        metrics = {
            'system': {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent
            },
            'network': {
                'bytes_sent': psutil.net_io_counters().bytes_sent,
                'bytes_recv': psutil.net_io_counters().bytes_recv
            },
            'vrct': {
                'translation_count': self.components.get('translation_count', 0),
                'osc_messages_sent': self.components.get('osc_count', 0),
                'overlay_updates': self.components.get('overlay_count', 0),
                'active_connections': len(self.ws_server.clients)
            }
        }
        
        return metrics
    
    def send_metrics(self, server):
        """メトリクス送信"""
        metrics = self.collect_metrics()
        
        response = {
            'type': 'metrics_snapshot',
            'metrics': metrics,
            'timestamp': time.time()
        }
        server.broadcast(json.dumps(response))
    
    def send_logs(self, server, limit):
        """ログ送信"""
        # ログファイルから最新のログを取得（実装例）
        logs = self.get_recent_logs(limit)
        
        response = {
            'type': 'log_data',
            'logs': logs,
            'count': len(logs)
        }
        server.broadcast(json.dumps(response))
    
    def get_recent_logs(self, limit):
        """最新ログ取得"""
        # 実際のログファイル読み込み処理
        mock_logs = [
            {'level': 'INFO', 'message': 'システム開始', 'timestamp': time.time() - 60},
            {'level': 'DEBUG', 'message': '翻訳処理完了', 'timestamp': time.time() - 30},
            {'level': 'WARNING', 'message': 'メモリ使用量増加', 'timestamp': time.time() - 10}
        ]
        return mock_logs[-limit:]
    
    def send_dashboard_error(self, server, error_message):
        """ダッシュボードエラー送信"""
        error_data = {
            'type': 'dashboard_error',
            'message': error_message,
            'timestamp': time.time()
        }
        server.broadcast(json.dumps(error_data))
    
    def start_dashboard(self):
        """ダッシュボード開始"""
        self.ws_server.start_server()
        print(f"監視ダッシュボード開始: ws://127.0.0.1:{self.ws_server.port}")
    
    def stop_dashboard(self):
        """ダッシュボード停止"""
        self.monitoring_active = False
        self.ws_server.stop_server()

# 使用例
system_components = {
    'translation_count': 150,
    'osc_count': 75,
    'overlay_count': 200
}

dashboard = MonitoringDashboard(system_components)
dashboard.start_dashboard()

# しばらく実行
time.sleep(60)

dashboard.stop_dashboard()
```

### 高度なメッセージルーティング

```python
class WebSocketRouter:
    """WebSocketメッセージルーティングシステム"""
    
    def __init__(self, port=8767):
        self.ws_server = WebSocketServer(host='127.0.0.1', port=port)
        self.ws_server.set_message_handler(self.route_message)
        self.routes = {}
        self.middleware = []
        self.client_subscriptions = {}
        
    def add_route(self, message_type, handler):
        """メッセージタイプに対するハンドラー登録"""
        self.routes[message_type] = handler
    
    def add_middleware(self, middleware_func):
        """ミドルウェア追加"""
        self.middleware.append(middleware_func)
    
    def route_message(self, server, websocket, message):
        """メッセージルーティング処理"""
        try:
            # JSON解析
            data = json.loads(message)
            message_type = data.get('type')
            
            # ミドルウェア実行
            for middleware in self.middleware:
                data = middleware(data, websocket)
                if data is None:  # ミドルウェアがNoneを返した場合は処理中断
                    return
            
            # ルーティング実行
            if message_type in self.routes:
                handler = self.routes[message_type]
                response = handler(data, websocket, server)
                
                if response:
                    server.broadcast(json.dumps(response))
            else:
                # 未定義メッセージタイプ
                error_response = {
                    'type': 'error',
                    'message': f'未対応メッセージタイプ: {message_type}',
                    'original_type': message_type
                }
                websocket.send(json.dumps(error_response))
                
        except json.JSONDecodeError as e:
            error_response = {
                'type': 'error', 
                'message': f'JSON解析エラー: {e}'
            }
            websocket.send(json.dumps(error_response))
        except Exception as e:
            error_response = {
                'type': 'error',
                'message': f'処理エラー: {e}'
            }
            websocket.send(json.dumps(error_response))
    
    def subscription_middleware(self, data, websocket):
        """購読管理ミドルウェア"""
        message_type = data.get('type')
        
        if message_type == 'subscribe':
            # 購読登録
            topics = data.get('topics', [])
            client_id = id(websocket)
            self.client_subscriptions[client_id] = topics
            
            response = {
                'type': 'subscription_confirmed',
                'topics': topics
            }
            websocket.send(json.dumps(response))
            return None  # 処理終了
            
        elif message_type == 'unsubscribe':
            # 購読解除
            client_id = id(websocket)
            if client_id in self.client_subscriptions:
                del self.client_subscriptions[client_id]
            
            response = {
                'type': 'unsubscription_confirmed'
            }
            websocket.send(json.dumps(response))
            return None
        
        return data  # そのまま次の処理に進む
    
    def authentication_middleware(self, data, websocket):
        """認証ミドルウェア"""
        # 簡易認証例
        api_key = data.get('api_key')
        
        if api_key != 'valid_api_key_123':
            error_response = {
                'type': 'authentication_error',
                'message': '無効なAPIキー'
            }
            websocket.send(json.dumps(error_response))
            return None
        
        return data
    
    def logging_middleware(self, data, websocket):
        """ログ記録ミドルウェア"""
        client_ip = websocket.remote_address[0] if websocket.remote_address else 'unknown'
        message_type = data.get('type', 'unknown')
        
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {client_ip} -> {message_type}")
        
        return data
    
    def broadcast_to_subscribers(self, topic, message_data):
        """購読者へのトピック配信"""
        message_data['topic'] = topic
        message_json = json.dumps(message_data)
        
        for client_id, topics in self.client_subscriptions.items():
            if topic in topics:
                # 該当クライアントを検索
                for client in self.ws_server.clients:
                    if id(client) == client_id:
                        try:
                            client.send(message_json)
                        except Exception as e:
                            print(f"配信エラー: {e}")
                        break
    
    def start_router(self):
        """ルーター開始"""
        self.ws_server.start_server()
        print(f"WebSocketルーター開始: ws://127.0.0.1:{self.ws_server.port}")
    
    def stop_router(self):
        """ルーター停止"""
        self.ws_server.stop_server()

# 使用例
def handle_chat_message(data, websocket, server):
    """チャットメッセージハンドラー"""
    username = data.get('username', 'Anonymous')
    message = data.get('message', '')
    
    response = {
        'type': 'chat_broadcast',
        'username': username,
        'message': message,
        'timestamp': time.time()
    }
    
    return response

def handle_translation_request(data, websocket, server):
    """翻訳要求ハンドラー"""
    text = data.get('text', '')
    # 翻訳処理（モック）
    translated = f"[翻訳] {text}"
    
    response = {
        'type': 'translation_response',
        'original': text,
        'translated': translated
    }
    
    return response

# ルーター設定
router = WebSocketRouter()

# ミドルウェア登録
router.add_middleware(router.logging_middleware)
router.add_middleware(router.subscription_middleware)
# router.add_middleware(router.authentication_middleware)  # 認証が必要な場合

# ルート登録
router.add_route('chat_message', handle_chat_message)
router.add_route('translation_request', handle_translation_request)

router.start_router()

# トピック配信テスト
time.sleep(2)
router.broadcast_to_subscribers('system_updates', {
    'type': 'system_notification',
    'message': 'システム更新完了',
    'severity': 'info'
})

time.sleep(10)
router.stop_router()
```

## 高度な機能・パターン

### 接続プール管理

```python
class ConnectionPoolManager:
    """WebSocket接続プール管理"""
    
    def __init__(self):
        self.pools = {}  # pool_name -> set of websockets
        
    def assign_to_pool(self, websocket, pool_name):
        """クライアントをプールに割り当て"""
        if pool_name not in self.pools:
            self.pools[pool_name] = set()
        
        self.pools[pool_name].add(websocket)
        print(f"クライアントを {pool_name} プールに追加")
    
    def remove_from_pools(self, websocket):
        """すべてのプールからクライアントを削除"""
        for pool_name, pool in self.pools.items():
            if websocket in pool:
                pool.discard(websocket)
                print(f"クライアントを {pool_name} プールから削除")
    
    def broadcast_to_pool(self, pool_name, message):
        """特定プールに対してブロードキャスト"""
        if pool_name in self.pools:
            for websocket in self.pools[pool_name].copy():
                try:
                    websocket.send(message)
                except Exception:
                    # 切断されたクライアントを削除
                    self.pools[pool_name].discard(websocket)
    
    def get_pool_stats(self):
        """プール統計情報"""
        stats = {}
        for pool_name, pool in self.pools.items():
            stats[pool_name] = len(pool)
        return stats
```

### メッセージ永続化・再送機能

```python
class PersistentMessageSystem:
    """メッセージ永続化・再送システム"""
    
    def __init__(self, max_history=1000):
        self.message_history = []
        self.max_history = max_history
        self.client_last_seen = {}  # client_id -> last_message_id
        
    def store_message(self, message_data):
        """メッセージを履歴に保存"""
        message_id = len(self.message_history)
        stored_message = {
            'id': message_id,
            'data': message_data,
            'timestamp': time.time()
        }
        
        self.message_history.append(stored_message)
        
        # 履歴サイズ制限
        if len(self.message_history) > self.max_history:
            self.message_history = self.message_history[-self.max_history:]
        
        return message_id
    
    def get_missed_messages(self, client_id, last_seen_id):
        """クライアントが見逃したメッセージを取得"""
        missed_messages = []
        
        for msg in self.message_history:
            if msg['id'] > last_seen_id:
                missed_messages.append(msg)
        
        return missed_messages
    
    def client_reconnected(self, websocket, client_id):
        """クライアント再接続時の処理"""
        last_seen = self.client_last_seen.get(client_id, -1)
        missed_messages = self.get_missed_messages(client_id, last_seen)
        
        # 見逃したメッセージを再送
        for msg in missed_messages:
            try:
                recovery_data = {
                    'type': 'message_recovery',
                    'original_message': msg['data'],
                    'message_id': msg['id'],
                    'original_timestamp': msg['timestamp']
                }
                websocket.send(json.dumps(recovery_data))
            except Exception as e:
                print(f"メッセージ再送エラー: {e}")
        
        print(f"クライアント {client_id} に {len(missed_messages)} 件のメッセージを再送")
    
    def update_client_position(self, client_id, message_id):
        """クライアントの最新メッセージ位置更新"""
        self.client_last_seen[client_id] = message_id
```

## パフォーマンス・スケーラビリティ

### 負荷分散・最適化

```python
class OptimizedWebSocketServer(WebSocketServer):
    """最適化されたWebSocketサーバー"""
    
    def __init__(self, host='127.0.0.1', port=8765):
        super().__init__(host, port)
        self.message_stats = {
            'total_messages': 0,
            'messages_per_second': 0,
            'last_reset_time': time.time()
        }
        self.compression_enabled = True
        self.batch_size = 50
        self.batch_timeout = 0.1
        
    def enable_message_batching(self, batch_size=50, timeout=0.1):
        """メッセージバッチング有効化"""
        self.batch_size = batch_size
        self.batch_timeout = timeout
        
    async def optimized_broadcast(self, message_batch):
        """最適化されたバッチブロードキャスト"""
        if not self.clients:
            return
            
        # 圧縮対応
        if self.compression_enabled and len(message_batch) > 1:
            # 複数メッセージをまとめて送信
            combined_message = json.dumps({
                'type': 'batch',
                'messages': message_batch,
                'count': len(message_batch)
            })
        else:
            combined_message = json.dumps(message_batch[0])
        
        # 並列送信（エラー処理付き）
        send_tasks = []
        for client in self.clients.copy():
            send_tasks.append(self.safe_send(client, combined_message))
        
        results = await asyncio.gather(*send_tasks, return_exceptions=True)
        
        # 失敗したクライアントを削除
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_client = list(self.clients)[i]
                self.clients.discard(failed_client)
                print(f"クライアント削除（送信失敗）: {result}")
        
        # 統計更新
        self.update_message_stats(len(message_batch))
    
    async def safe_send(self, client, message):
        """安全なメッセージ送信"""
        try:
            await client.send(message)
        except Exception as e:
            raise e  # gather で捕捉される
    
    def update_message_stats(self, message_count):
        """メッセージ統計更新"""
        self.message_stats['total_messages'] += message_count
        
        current_time = time.time()
        time_diff = current_time - self.message_stats['last_reset_time']
        
        if time_diff >= 1.0:  # 1秒ごとに速度計算
            self.message_stats['messages_per_second'] = message_count / time_diff
            self.message_stats['last_reset_time'] = current_time
    
    def get_performance_stats(self):
        """パフォーマンス統計取得"""
        return {
            'connected_clients': len(self.clients),
            'total_messages': self.message_stats['total_messages'],
            'messages_per_second': self.message_stats['messages_per_second'],
            'compression_enabled': self.compression_enabled,
            'batch_size': self.batch_size
        }
```

## 依存関係・システム要件

### 必須依存関係
- `asyncio`: 非同期処理フレームワーク
- `websockets`: WebSocketライブラリ
- `threading`: マルチスレッド制御
- `json`: JSON形式データ処理

### システム要件
```python
system_requirements = {
    "python_version": "3.7以上",
    "asyncio_support": "非同期処理対応",
    "network_stack": "TCP/WebSocket対応",
    "memory": "同時接続数に応じた十分なメモリ"
}

performance_characteristics = {
    "concurrent_connections": "数百～数千接続対応",
    "message_throughput": "秒間数千メッセージ処理可能", 
    "latency": "低レイテンシー（ミリ秒オーダー）",
    "memory_per_connection": "約1-5MB（接続当たり）"
}
```

### オプション依存関係
- `ujson`: 高速JSON処理（パフォーマンス向上）
- `compression`: メッセージ圧縮（帯域節約）

## 注意事項・制限

### ネットワーク制限
- ファイアウォール設定の要確認
- プロキシ環境での制限可能性
- ブラウザーのWebSocket接続制限

### スケーラビリティ制限
- 単一プロセスでの同時接続数制限
- メモリ使用量の線形増加
- CPU集約的な処理での性能劣化

### セキュリティ考慮事項
```python
security_considerations = {
    "authentication": "認証機構の実装推奨",
    "authorization": "適切な認可制御",
    "rate_limiting": "レート制限の実装",
    "input_validation": "入力データの検証必須",
    "cors_policy": "CORS設定の適切な構成"
}
```

## 関連モジュール

- `config.py`: WebSocket設定管理
- `controller.py`: WebSocket制御インターフェース
- `utils.py`: エラーログ・ユーティリティ
- `model.py`: WebSocket機能統合

## 将来の改善点

- Redis等を用いたメッセージブローカー連携
- 負荷分散・クラスタリング対応
- より高度な認証・認可システム
- WebRTC等のより高速な通信プロトコル対応
- GraphQL over WebSocketサポート
- リアルタイム監視・分析機能の強化