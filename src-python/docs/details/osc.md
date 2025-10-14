# osc.py - OSC通信・OSCQueryプロトコル管理

## 概要

VRChatとの高度なOSC（Open Sound Control）通信を管理する包括的なシステムです。基本的なOSCメッセージ送信に加え、OSCQueryプロトコルによる双方向通信、パラメータ監視、自動サービス発見機能を提供します。

## 主要機能

### OSC通信機能
- VRChatチャットボックスへのメッセージ送信
- タイピング状態の制御
- パラメータ値の動的取得

### OSCQuery対応
- 自動サービス発見・接続
- リアルタイムパラメータ監視
- 双方向エンドポイント公開

### 堅牢性機能
- 防御的プログラミング設計
- 欠損ライブラリの優雅な処理
- 自動エラー復旧機構

## クラス構造

### OSCHandler クラス

```python
class OSCHandler:
    def __init__(self, ip_address: str = "127.0.0.1", port: int = 9000) -> None:
        self.is_osc_query_enabled: bool
        self.osc_ip_address: str
        self.osc_port: int
        self.udp_client: udp_client.SimpleUDPClient
        self.osc_server: Optional[osc_server.ThreadingOSCUDPServer]
        self.osc_query_service: Optional[OSCQueryService]
        self.browser: Optional[OSCQueryBrowser]
```

OSC通信の中核管理クラス

#### 属性
- **is_osc_query_enabled**: OSCQuery機能の有効性フラグ
- **osc_ip_address**: 送信先IPアドレス
- **osc_port**: UDP通信ポート
- **udp_client**: OSC送信クライアント
- **osc_server**: ローカルOSCサーバー
- **osc_query_service**: OSCQueryサービスインスタンス
- **browser**: OSCQueryブラウザー

## 主要メソッド

### メッセージ送信

```python
def sendMessage(self, message: str = "", notification: bool = True) -> None
```

VRChatチャットボックスにメッセージを送信

#### パラメータ
- **message**: 送信するテキストメッセージ
- **notification**: 通知フラグ（音・表示の有無）

```python
def sendTyping(self, flag: bool = False) -> None
```

タイピング状態をVRChatに送信

#### パラメータ
- **flag**: タイピング中フラグ

### パラメータ監視

```python
def getOSCParameterMuteSelf() -> Optional[bool]
```

VRChatのMuteSelfパラメータ値を取得

#### 戻り値
- **Optional[bool]**: ミュート状態（取得失敗時はNone）

```python
def getOSCParameterValue(self, address: str) -> Any
```

任意のOSCパラメータ値を取得

#### パラメータ
- **address**: OSCアドレス（例："/avatar/parameters/MuteSelf"）

#### 戻り値
- **Any**: パラメータ値（取得失敗時はNone）

### 設定変更

```python
def setOscIpAddress(self, ip_address: str) -> None
```

送信先IPアドレスを変更し、サービスを再初期化

#### パラメータ
- **ip_address**: 新しいIPアドレス

```python
def setOscPort(self, port: int) -> None
```

送信ポートを変更し、サービスを再初期化

#### パラメータ
- **port**: 新しいUDPポート番号

## 使用方法

### 基本的なメッセージ送信

```python
from models.osc.osc import OSCHandler

# OSCハンドラーの初期化
osc = OSCHandler(ip_address="127.0.0.1", port=9000)

# チャットボックスにメッセージを送信
osc.sendMessage("こんにちは、VRChat！", notification=True)

# タイピング状態の制御
osc.sendTyping(True)   # タイピング開始
# ... 実際のタイピング処理 ...
osc.sendTyping(False)  # タイピング終了

# 再度メッセージ送信
osc.sendMessage("翻訳完了しました", notification=False)
```

### リモートVRChatへの接続

```python
# リモートVRChatインスタンスへの接続
remote_osc = OSCHandler(ip_address="192.168.1.100", port=9000)

# OSCQuery機能は自動的に無効化される
print(f"OSCQuery有効: {remote_osc.getIsOscQueryEnabled()}")  # False

# 基本的なメッセージ送信は利用可能
remote_osc.sendMessage("リモートからの翻訳結果", notification=True)
```

### パラメータ監視（ローカル接続時のみ）

```python
# ローカル接続でのパラメータ監視
local_osc = OSCHandler(ip_address="127.0.0.1", port=9000)

if local_osc.getIsOscQueryEnabled():
    # MuteSelfパラメータの監視
    mute_status = local_osc.getOSCParameterMuteSelf()
    
    if mute_status is not None:
        if mute_status:
            print("ユーザーはミュート中です")
        else:
            print("ユーザーはミュート解除中です")
    else:
        print("MuteSelfパラメータの取得に失敗しました")
    
    # カスタムパラメータの監視
    custom_value = local_osc.getOSCParameterValue("/avatar/parameters/CustomParam")
    if custom_value is not None:
        print(f"カスタムパラメータ値: {custom_value}")
```

### 双方向OSC通信の設定

```python
def handle_mute_change(address, *args):
    """ミュート状態変更のハンドラー"""
    print(f"ミュート状態が変更されました: {args}")

def handle_typing_change(address, *args):
    """タイピング状態変更のハンドラー"""  
    print(f"タイピング状態: {args}")

def handle_chatbox_input(address, *args):
    """チャットボックス入力のハンドラー"""
    print(f"チャットボックス入力: {args}")

# OSCパラメータハンドラーの設定
osc_handlers = {
    "/avatar/parameters/MuteSelf": handle_mute_change,
    "/chatbox/typing": handle_typing_change,
    "/chatbox/input": handle_chatbox_input
}

osc = OSCHandler()
osc.setDictFilterAndTarget(osc_handlers)

# OSCサーバー開始（OSCQuery自動公開）
osc.receiveOscParameters()

print("OSC受信サーバーが開始されました")
print("VRChatからのパラメータ変更を監視中...")

# メッセージ送信テスト
import time
time.sleep(2)
osc.sendMessage("双方向通信テスト", notification=True)

# 長時間実行
time.sleep(30)

# クリーンアップ
osc.oscServerStop()
```

### 動的設定変更

```python
# 実行時のIP・ポート変更
osc = OSCHandler(ip_address="127.0.0.1", port=9000)

# 初期設定でローカル接続
osc.sendMessage("ローカル接続テスト")

print("リモート接続に切り替え中...")
osc.setOscIpAddress("192.168.1.150")  # 自動的にOSCQueryが無効化
osc.sendMessage("リモート接続テスト")

print("ポート変更...")
osc.setOscPort(9001)
osc.sendMessage("新しいポートでのテスト")

print("ローカル接続に戻る...")
osc.setOscIpAddress("127.0.0.1")  # OSCQueryが再度有効化
osc.sendMessage("ローカル接続復帰テスト")
```

## OSCQuery詳細機能

### 自動サービス発見

```python
class VRChatMonitor:
    """VRChatサービス監視クラス"""
    
    def __init__(self):
        self.osc = OSCHandler()
        self.monitoring = False
    
    def start_monitoring(self):
        """VRChatパラメータの継続監視開始"""
        
        if not self.osc.getIsOscQueryEnabled():
            print("OSCQuery機能が無効です（ローカル接続のみサポート）")
            return
        
        # OSCハンドラー設定
        handlers = {
            "/avatar/parameters/MuteSelf": self.on_mute_change,
            "/avatar/parameters/Voice": self.on_voice_change,
            "/avatar/parameters/Viseme": self.on_viseme_change,
            "/avatar/parameters/GestureLeft": self.on_gesture_left,
            "/avatar/parameters/GestureRight": self.on_gesture_right
        }
        
        self.osc.setDictFilterAndTarget(handlers)
        self.osc.receiveOscParameters()
        
        self.monitoring = True
        print("VRChatパラメータ監視を開始しました")
    
    def on_mute_change(self, address, *args):
        print(f"ミュート状態変更: {args[0] if args else 'Unknown'}")
    
    def on_voice_change(self, address, *args):
        print(f"音声レベル: {args[0] if args else 'Unknown'}")
    
    def on_viseme_change(self, address, *args):
        print(f"口形変化: {args[0] if args else 'Unknown'}")
    
    def on_gesture_left(self, address, *args):
        print(f"左手ジェスチャー: {args[0] if args else 'Unknown'}")
    
    def on_gesture_right(self, address, *args):
        print(f"右手ジェスチャー: {args[0] if args else 'Unknown'}")
    
    def stop_monitoring(self):
        """監視停止"""
        self.osc.oscServerStop()
        self.monitoring = False
        print("VRChatパラメータ監視を停止しました")

# 使用例
monitor = VRChatMonitor()
monitor.start_monitoring()

# 監視中に他の処理を実行
time.sleep(60)  # 1分間監視

monitor.stop_monitoring()
```

### リアルタイムパラメータ追跡

```python
class ParameterTracker:
    """パラメータ値の追跡・履歴管理"""
    
    def __init__(self, osc_handler):
        self.osc = osc_handler
        self.parameter_history = {}
        self.tracking_active = False
    
    def track_parameter(self, address, interval=0.1):
        """指定されたパラメータを定期監視"""
        
        import threading
        
        def monitoring_loop():
            while self.tracking_active:
                try:
                    value = self.osc.getOSCParameterValue(address)
                    if value is not None:
                        timestamp = time.time()
                        
                        if address not in self.parameter_history:
                            self.parameter_history[address] = []
                        
                        # 値が変更された場合のみ記録
                        if (not self.parameter_history[address] or 
                            self.parameter_history[address][-1][1] != value):
                            
                            self.parameter_history[address].append((timestamp, value))
                            print(f"{address}: {value} (時刻: {timestamp:.2f})")
                            
                            # 履歴サイズ制限（最新100件まで）
                            if len(self.parameter_history[address]) > 100:
                                self.parameter_history[address] = self.parameter_history[address][-100:]
                    
                    time.sleep(interval)
                
                except Exception as e:
                    print(f"パラメータ追跡エラー: {e}")
                    time.sleep(interval)
        
        self.tracking_active = True
        thread = threading.Thread(target=monitoring_loop, daemon=True)
        thread.start()
    
    def stop_tracking(self):
        """追跡停止"""
        self.tracking_active = False
    
    def get_parameter_history(self, address):
        """パラメータの履歴取得"""
        return self.parameter_history.get(address, [])
    
    def get_latest_value(self, address):
        """最新パラメータ値取得"""
        history = self.get_parameter_history(address)
        return history[-1][1] if history else None

# 使用例
osc = OSCHandler()
tracker = ParameterTracker(osc)

# MuteSelfパラメータの追跡開始
tracker.track_parameter("/avatar/parameters/MuteSelf", interval=0.5)

# しばらく監視
time.sleep(30)

# 結果確認
mute_history = tracker.get_parameter_history("/avatar/parameters/MuteSelf")
print(f"MuteSelf変更履歴: {len(mute_history)}件")

for timestamp, value in mute_history[-5:]:  # 最新5件表示
    print(f"  {time.ctime(timestamp)}: {value}")

tracker.stop_tracking()
```

## エラーハンドリング・復旧機構

### 堅牢な接続管理

```python
class RobustOSCHandler:
    """堅牢性を高めたOSCハンドラー"""
    
    def __init__(self, ip_address="127.0.0.1", port=9000):
        self.osc = OSCHandler(ip_address, port)
        self.connection_retries = 3
        self.retry_delay = 1.0
    
    def safe_send_message(self, message, notification=True, max_retries=None):
        """安全なメッセージ送信（リトライ機構付き）"""
        
        retries = max_retries or self.connection_retries
        
        for attempt in range(retries):
            try:
                self.osc.sendMessage(message, notification)
                return True
                
            except Exception as e:
                print(f"送信試行 {attempt + 1}/{retries} 失敗: {e}")
                
                if attempt < retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # 指数バックオフ
                    
                    # 接続再初期化を試行
                    try:
                        self.osc.udp_client = udp_client.SimpleUDPClient(
                            self.osc.osc_ip_address, 
                            self.osc.osc_port
                        )
                    except Exception as reconnect_error:
                        print(f"再接続失敗: {reconnect_error}")
        
        print(f"メッセージ送信に失敗しました: '{message}'")
        return False
    
    def safe_get_parameter(self, address, timeout=5.0):
        """安全なパラメータ取得（タイムアウト付き）"""
        
        if not self.osc.getIsOscQueryEnabled():
            return None
        
        import threading
        import queue
        
        result_queue = queue.Queue()
        
        def parameter_getter():
            try:
                value = self.osc.getOSCParameterValue(address)
                result_queue.put(value)
            except Exception as e:
                result_queue.put(e)
        
        # タイムアウト付きでパラメータ取得
        thread = threading.Thread(target=parameter_getter, daemon=True)
        thread.start()
        
        try:
            result = result_queue.get(timeout=timeout)
            if isinstance(result, Exception):
                raise result
            return result
            
        except queue.Empty:
            print(f"パラメータ取得タイムアウト: {address}")
            return None

# 使用例
robust_osc = RobustOSCHandler()

# 堅牢な送信
success = robust_osc.safe_send_message("堅牢性テスト", notification=True)
print(f"送信成功: {success}")

# 安全なパラメータ取得
mute_value = robust_osc.safe_get_parameter("/avatar/parameters/MuteSelf", timeout=3.0)
print(f"MuteSelf値: {mute_value}")
```

## パフォーマンス最適化

### 効率的な通信管理

```python
class OptimizedOSCHandler:
    """パフォーマンス最適化OSCハンドラー"""
    
    def __init__(self, ip_address="127.0.0.1", port=9000):
        self.osc = OSCHandler(ip_address, port)
        self.message_queue = []
        self.batch_size = 10
        self.batch_interval = 0.1
        self.last_batch_time = 0
        
    def queue_message(self, message, notification=True):
        """メッセージをキューに追加（バッチ送信用）"""
        
        self.message_queue.append((message, notification))
        
        # バッチサイズまたは時間間隔でフラッシュ
        current_time = time.time()
        
        if (len(self.message_queue) >= self.batch_size or 
            current_time - self.last_batch_time >= self.batch_interval):
            self.flush_messages()
    
    def flush_messages(self):
        """キューされたメッセージを一括送信"""
        
        if not self.message_queue:
            return
        
        # 最新のメッセージのみ送信（重複排除）
        if len(self.message_queue) > 1:
            # 最後のメッセージを優先
            last_message, last_notification = self.message_queue[-1]
            self.osc.sendMessage(last_message, last_notification)
        else:
            message, notification = self.message_queue[0]
            self.osc.sendMessage(message, notification)
        
        # キューをクリア
        self.message_queue.clear()
        self.last_batch_time = time.time()
    
    def send_immediate(self, message, notification=True):
        """即座にメッセージ送信（キューをバイパス）"""
        self.flush_messages()  # 既存キューを先にフラッシュ
        self.osc.sendMessage(message, notification)

# 使用例
optimized_osc = OptimizedOSCHandler()

# 複数のメッセージを効率的に送信
for i in range(20):
    optimized_osc.queue_message(f"バッチメッセージ {i}")
    time.sleep(0.05)  # 短い間隔

# 残りのメッセージをフラッシュ
optimized_osc.flush_messages()

# 即座に送信が必要な重要メッセージ
optimized_osc.send_immediate("緊急メッセージ", notification=True)
```

## 依存関係・要件

### 必須依存関係
- `pythonosc`: 基本OSC通信ライブラリ
- `threading`: 並行処理制御
- `time`: 時間管理機能

### オプション依存関係
- `tinyoscquery`: OSCQuery機能（ローカル接続時のみ）
- `utils`: エラーログ機能（フォールバック処理あり）

### システム要件
```python
# 最小システム要件
requirements = {
    "python_version": "3.7+",
    "network": "UDP通信対応",
    "vrchat_version": "OSCサポート版（2022年8月以降）",
    "local_ports": "空きUDP/TCPポート（OSCQuery使用時）"
}

# 推奨環境
recommended = {
    "network_latency": "< 10ms（ローカル接続）",
    "cpu_usage": "OSCQuery使用時は追加CPU負荷",
    "memory": "tinyoscquery使用時は追加メモリ"
}
```

## 注意事項・制限

### OSCQuery制限
- ローカルホスト（127.0.0.1/localhost）接続時のみ利用可能
- tinyoscqueryライブラリが必要
- ファイアウォール設定によっては動作しない可能性

### 通信制限
- UDPプロトコルのため送達保証なし
- VRChatのOSC受信制限（レート制限あり）
- ネットワーク環境による遅延・パケット loss

### プラットフォーム依存
```python
# 既知の制限事項
limitations = {
    "windows": "Windowsファイアウォールの設定が必要な場合あり",
    "macos": "セキュリティ設定によるポート制限の可能性",
    "linux": "一部のLinuxディストリビューションでの互換性問題",
    "vrchat_platform": "PC版VRChatのみOSCサポート"
}
```

## 関連モジュール

- `config.py`: OSC設定管理
- `controller.py`: OSC機能制御インターフェース
- `model.py`: OSC機能統合
- `utils.py`: エラーログ・ネットワークユーティリティ

## 将来の改善点

- より高度なOSCQueryパラメータ監視
- カスタムOSCプロトコル拡張
- パフォーマンス監視・分析機能
- 自動再接続・復旧機構の改善
- VRChatアバター固有パラメータ対応