# watchdog.py - 軽量監視システム

## 概要

タイムアウトベースの軽量監視（ウォッチドッグ）システムです。定期的な"餌やり"（feed）により正常動作を確認し、指定時間内に餌やりがない場合にコールバック関数を実行する単純で効果的な監視機構を提供します。

## 主要機能

### タイムアウト監視
- 最後の餌やり時刻からの経過時間監視
- 設定可能なタイムアウト閾値
- タイムアウト時の自動コールバック実行

### 柔軟な実行モード
- 単発チェック（手動呼び出し）
- バックグラウンドスレッド実行
- カスタムチェック間隔設定

### 防御的設計
- コールバック例外の隔離処理
- スレッドセーフな制御機構
- 適切なリソース管理

## クラス構造

### Watchdog クラス

```python
class Watchdog:
    def __init__(self, timeout: int = 60, interval: int = 20) -> None:
        self.timeout: int                    # タイムアウト秒数
        self.interval: int                   # チェック間隔秒数  
        self.last_feed_time: float          # 最後の餌やり時刻
        self.callback: Optional[Callable]    # タイムアウト時コールバック
        self._thread: Optional[Thread]       # バックグラウンドスレッド
        self._stop_event: Optional[Event]    # 停止イベント
```

軽量ウォッチドッグの中核クラス

#### パラメータ
- **timeout**: 餌やりなしでタイムアウトするまでの秒数
- **interval**: 監視チェックの推奨間隔秒数

## 主要メソッド

### 基本制御

```python
def feed(self) -> None
```

ウォッチドッグに餌やりを行い、タイマーをリセット

```python
def setCallback(self, callback: Callable[[], None]) -> None
```

タイムアウト時に実行するコールバック関数を設定

#### パラメータ
- **callback**: 引数なしの呼び出し可能オブジェクト

### 監視実行

```python
def start(self) -> None
```

単発のウォッチドッグチェックを実行し、間隔秒数だけスリープ

```python
def start_in_thread(self, daemon: bool = True) -> None
```

バックグラウンドスレッドでウォッチドッグを開始

#### パラメータ
- **daemon**: デーモンスレッドとして実行するかのフラグ

```python
def stop(self, timeout: Optional[float] = None) -> None
```

バックグラウンドスレッドを停止

#### パラメータ
- **timeout**: スレッド終了待機のタイムアウト秒数

## 使用方法

### 基本的な監視システム

```python
from models.watchdog.watchdog import Watchdog
import time

def on_timeout():
    """タイムアウト時の処理"""
    print("警告: システムの応答がありません！")
    # ログ出力、アラート送信、復旧処理等

# ウォッチドッグの初期化
watchdog = Watchdog(timeout=30, interval=10)  # 30秒でタイムアウト、10秒間隔
watchdog.setCallback(on_timeout)

# バックグラウンドで監視開始
watchdog.start_in_thread(daemon=True)

# メインプロセスのシミュレーション
for i in range(10):
    print(f"処理中... {i}")
    
    # 正常な処理では定期的に餌やり
    if i % 3 == 0:  # 3回に1回餌やり
        watchdog.feed()
        print("ウォッチドッグに餌やりしました")
    
    time.sleep(5)

# 監視停止
watchdog.stop()
```

### 手動チェックモード

```python
# 手動でウォッチドッグをチェック
def manual_monitoring_example():
    watchdog = Watchdog(timeout=60, interval=5)
    
    def system_failure_handler():
        print("システム障害を検出しました")
        # 復旧処理、通知等
    
    watchdog.setCallback(system_failure_handler)
    
    # メインループ内で定期チェック
    while True:
        # 何らかの重要な処理
        process_critical_work()
        
        # 処理が正常なら餌やり
        if is_system_healthy():
            watchdog.feed()
        
        # 監視チェック実行（5秒間隔でスリープ）
        watchdog.start()

def process_critical_work():
    """重要な処理のシミュレーション"""
    time.sleep(2)

def is_system_healthy():
    """システム正常性チェックのシミュレーション"""
    import random
    return random.random() > 0.2  # 80%の確率で正常

# manual_monitoring_example()
```

### プロセス監視システム

```python
class ProcessMonitor:
    """外部プロセス監視システム"""
    
    def __init__(self, process_name, check_interval=30):
        self.process_name = process_name
        self.watchdog = Watchdog(timeout=60, interval=check_interval)
        self.watchdog.setCallback(self.on_process_timeout)
        self.monitoring = False
        
    def on_process_timeout(self):
        """プロセス応答タイムアウト時の処理"""
        print(f"警告: プロセス {self.process_name} が応答しません")
        
        # プロセス存在確認
        if self.is_process_running():
            print("プロセスは実行中ですが応答なし。再起動を試行します。")
            self.restart_process()
        else:
            print("プロセスが停止しています。再起動します。")
            self.start_process()
    
    def is_process_running(self):
        """プロセス実行状態確認"""
        import psutil
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == self.process_name:
                return True
        return False
    
    def start_process(self):
        """プロセス起動"""
        print(f"プロセス {self.process_name} を起動中...")
        # 実際の起動処理
        
    def restart_process(self):
        """プロセス再起動"""
        print(f"プロセス {self.process_name} を再起動中...")
        # 実際の再起動処理
    
    def feed_watchdog(self):
        """外部から呼び出される餌やりメソッド"""
        self.watchdog.feed()
        
    def start_monitoring(self):
        """監視開始"""
        self.monitoring = True
        self.watchdog.start_in_thread(daemon=True)
        print(f"プロセス {self.process_name} の監視を開始しました")
    
    def stop_monitoring(self):
        """監視停止"""
        self.monitoring = False
        self.watchdog.stop()
        print(f"プロセス {self.process_name} の監視を停止しました")

# 使用例
vrchat_monitor = ProcessMonitor("VRChat.exe", check_interval=15)
vrchat_monitor.start_monitoring()

# VRChatプロセスが正常に動作している時の餌やり
# （実際にはVRChatからのOSC通信等で判定）
for _ in range(20):
    time.sleep(10)
    
    if vrchat_monitor.is_process_running():
        vrchat_monitor.feed_watchdog()
        print("VRChat正常動作確認")
    
vrchat_monitor.stop_monitoring()
```

### ネットワーク監視システム

```python
class NetworkWatchdog:
    """ネットワーク接続監視"""
    
    def __init__(self, target_host="8.8.8.8", timeout=45):
        self.target_host = target_host
        self.watchdog = Watchdog(timeout=timeout, interval=15)
        self.watchdog.setCallback(self.on_network_timeout)
        self.last_ping_success = True
    
    def on_network_timeout(self):
        """ネットワークタイムアウト処理"""
        print("ネットワーク接続に問題があります")
        
        # 複数ホストでの確認
        test_hosts = ["8.8.8.8", "1.1.1.1", "google.com"]
        
        for host in test_hosts:
            if self.ping_host(host):
                print(f"{host} への接続は正常です")
                self.watchdog.feed()  # 1つでも成功したら復旧とみなす
                return
        
        print("すべてのホストへの接続に失敗。ネットワーク設定を確認してください。")
        self.handle_network_failure()
    
    def ping_host(self, host):
        """ホストへのping確認"""
        import subprocess
        import platform
        
        # プラットフォームに応じたpingコマンド
        if platform.system().lower() == "windows":
            cmd = ["ping", "-n", "1", "-w", "3000", host]
        else:
            cmd = ["ping", "-c", "1", "-W", "3", host]
        
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, Exception):
            return False
    
    def handle_network_failure(self):
        """ネットワーク障害時の処理"""
        print("ネットワーク障害対応処理を実行中...")
        # DNS設定リセット、ネットワークアダプター再起動等
    
    def check_network_continuously(self):
        """継続的なネットワーク監視"""
        self.watchdog.start_in_thread(daemon=True)
        
        while True:
            if self.ping_host(self.target_host):
                if not self.last_ping_success:
                    print("ネットワーク接続が復旧しました")
                
                self.watchdog.feed()
                self.last_ping_success = True
            else:
                if self.last_ping_success:
                    print("ネットワーク接続に問題が発生しました")
                
                self.last_ping_success = False
            
            time.sleep(10)

# 使用例
network_monitor = NetworkWatchdog(target_host="google.com", timeout=60)

# バックグラウンドでネットワーク監視
import threading
monitor_thread = threading.Thread(target=network_monitor.check_network_continuously, daemon=True)
monitor_thread.start()

# メインプログラムの実行
print("ネットワーク監視システム開始...")
time.sleep(120)  # 2分間監視

network_monitor.watchdog.stop()
```

### システムリソース監視

```python
class SystemResourceWatchdog:
    """システムリソース監視"""
    
    def __init__(self):
        self.cpu_watchdog = Watchdog(timeout=300, interval=30)  # CPU使用率監視
        self.memory_watchdog = Watchdog(timeout=180, interval=20)  # メモリ監視
        
        self.cpu_watchdog.setCallback(self.on_cpu_overload)
        self.memory_watchdog.setCallback(self.on_memory_pressure)
        
        self.cpu_threshold = 80.0    # CPU使用率閾値（%）
        self.memory_threshold = 85.0  # メモリ使用率閾値（%）
    
    def on_cpu_overload(self):
        """CPU過負荷時の処理"""
        print("警告: CPU使用率が長時間高い状態です")
        self.optimize_cpu_usage()
    
    def on_memory_pressure(self):
        """メモリ圧迫時の処理"""
        print("警告: メモリ使用率が危険なレベルです")
        self.free_memory()
    
    def get_cpu_usage(self):
        """CPU使用率取得"""
        import psutil
        return psutil.cpu_percent(interval=1)
    
    def get_memory_usage(self):
        """メモリ使用率取得"""
        import psutil
        return psutil.virtual_memory().percent
    
    def optimize_cpu_usage(self):
        """CPU使用率最適化"""
        print("CPU最適化処理を実行中...")
        # 低優先度プロセスの特定・制限
        # 不要なバックグラウンドタスクの停止等
    
    def free_memory(self):
        """メモリ解放処理"""
        print("メモリ解放処理を実行中...")
        # ガベージコレクション実行
        import gc
        gc.collect()
        # キャッシュクリア等
    
    def monitor_resources(self):
        """リソース監視メインループ"""
        self.cpu_watchdog.start_in_thread(daemon=True)
        self.memory_watchdog.start_in_thread(daemon=True)
        
        while True:
            # CPU使用率チェック
            cpu_usage = self.get_cpu_usage()
            if cpu_usage < self.cpu_threshold:
                self.cpu_watchdog.feed()
            
            # メモリ使用率チェック
            memory_usage = self.get_memory_usage()
            if memory_usage < self.memory_threshold:
                self.memory_watchdog.feed()
            
            print(f"CPU: {cpu_usage:.1f}%, メモリ: {memory_usage:.1f}%")
            time.sleep(5)
    
    def stop_monitoring(self):
        """監視停止"""
        self.cpu_watchdog.stop()
        self.memory_watchdog.stop()

# 使用例
resource_monitor = SystemResourceWatchdog()

# リソース監視開始
import threading
resource_thread = threading.Thread(target=resource_monitor.monitor_resources, daemon=True)
resource_thread.start()

# しばらく監視
time.sleep(60)

resource_monitor.stop_monitoring()
```

## 高度な使用パターン

### 多段階監視システム

```python
class MultilevelWatchdog:
    """多段階警告レベル対応ウォッチドッグ"""
    
    def __init__(self):
        # 異なるタイムアウトレベル
        self.warning_watchdog = Watchdog(timeout=30, interval=10)   # 警告レベル
        self.critical_watchdog = Watchdog(timeout=60, interval=15)  # 危険レベル
        self.emergency_watchdog = Watchdog(timeout=120, interval=20) # 緊急レベル
        
        # 各レベルのコールバック設定
        self.warning_watchdog.setCallback(self.on_warning)
        self.critical_watchdog.setCallback(self.on_critical)
        self.emergency_watchdog.setCallback(self.on_emergency)
        
        self.alert_level = "normal"
    
    def on_warning(self):
        """警告レベルのコールバック"""
        self.alert_level = "warning"
        print("⚠️  警告: システムの応答が遅くなっています")
        # 軽度の対応処理
    
    def on_critical(self):
        """危険レベルのコールバック"""  
        self.alert_level = "critical"
        print("🔴 危険: システムの重大な問題を検出")
        # 中程度の復旧処理
    
    def on_emergency(self):
        """緊急レベルのコールバック"""
        self.alert_level = "emergency"
        print("🚨 緊急: システムが完全に応答停止")
        # 強制復旧・再起動処理
    
    def feed_all(self):
        """すべてのウォッチドッグに餌やり"""
        self.warning_watchdog.feed()
        self.critical_watchdog.feed()
        self.emergency_watchdog.feed()
        
        if self.alert_level != "normal":
            print("✅ システム復旧確認")
            self.alert_level = "normal"
    
    def start_monitoring(self):
        """多段階監視開始"""
        self.warning_watchdog.start_in_thread(daemon=True)
        self.critical_watchdog.start_in_thread(daemon=True)
        self.emergency_watchdog.start_in_thread(daemon=True)
    
    def stop_monitoring(self):
        """監視停止"""
        self.warning_watchdog.stop()
        self.critical_watchdog.stop()
        self.emergency_watchdog.stop()

# 使用例
multilevel_monitor = MultilevelWatchdog()
multilevel_monitor.start_monitoring()

# 正常時は定期餌やり、異常時は餌やり停止で段階的警告
for i in range(30):
    time.sleep(5)
    
    # 時々餌やりを忘れるシミュレーション
    if i % 7 != 0:  # 7回に1回は餌やりしない
        multilevel_monitor.feed_all()
    
    print(f"現在の警告レベル: {multilevel_monitor.alert_level}")

multilevel_monitor.stop_monitoring()
```

## エラーハンドリング・防御機構

### 例外安全性

```python
def safe_callback_example():
    """安全なコールバック実装例"""
    
    def potentially_failing_callback():
        """例外を起こす可能性があるコールバック"""
        print("重要な処理を実行中...")
        
        # 何らかの理由で例外が発生
        raise RuntimeError("処理中にエラーが発生しました")
    
    # ウォッチドッグは例外を隔離するため、システム全体は継続動作
    watchdog = Watchdog(timeout=10, interval=5)
    watchdog.setCallback(potentially_failing_callback)
    
    # エラーが発生してもウォッチドッグ自体は停止しない
    watchdog.start_in_thread(daemon=True)
    
    # 通常の処理継続
    for i in range(5):
        time.sleep(3)
        watchdog.feed()
        print(f"メイン処理継続中: {i}")
    
    watchdog.stop()
    print("ウォッチドッグは例外に関係なく正常に停止しました")

safe_callback_example()
```

### 堅牢なスレッド制御

```python
class RobustWatchdog:
    """より堅牢なウォッチドッグ実装"""
    
    def __init__(self, timeout=60, interval=20):
        self.base_watchdog = Watchdog(timeout, interval)
        self.restart_count = 0
        self.max_restarts = 3
        
    def robust_callback(self):
        """自動復旧機能付きコールバック"""
        try:
            print(f"問題検出（再起動回数: {self.restart_count}/{self.max_restarts}）")
            
            if self.restart_count < self.max_restarts:
                self.attempt_recovery()
                self.restart_count += 1
            else:
                print("最大再起動回数に達しました。管理者に連絡してください。")
                self.emergency_shutdown()
                
        except Exception as e:
            print(f"復旧処理中にエラー: {e}")
    
    def attempt_recovery(self):
        """復旧処理の試行"""
        print("自動復旧処理を実行中...")
        time.sleep(2)  # 復旧処理のシミュレーション
        
        # 復旧成功時はカウンターリセット
        if self.check_system_health():
            self.restart_count = 0
            self.base_watchdog.feed()
            print("復旧成功")
        else:
            print("復旧失敗")
    
    def check_system_health(self):
        """システム正常性確認"""
        # 実際のヘルスチェックロジック
        import random
        return random.random() > 0.3  # 70%成功率
    
    def emergency_shutdown(self):
        """緊急停止処理"""
        print("緊急停止処理を実行します")
        # 安全な停止処理
    
    def start_robust_monitoring(self):
        """堅牢監視開始"""
        self.base_watchdog.setCallback(self.robust_callback)
        self.base_watchdog.start_in_thread(daemon=True)
    
    def feed(self):
        """餌やり（成功時はカウンターリセット）"""
        self.base_watchdog.feed()
        self.restart_count = 0
    
    def stop(self):
        """監視停止"""
        self.base_watchdog.stop()

# 使用例
robust_monitor = RobustWatchdog(timeout=20, interval=8)
robust_monitor.start_robust_monitoring()

# 不安定なシステムのシミュレーション
for i in range(15):
    time.sleep(3)
    
    # 時々システム異常をシミュレート
    if random.random() > 0.7:  # 30%の確率で異常
        print("システム異常発生...")
        # 餌やりしない
    else:
        robust_monitor.feed()
        print("システム正常動作")

robust_monitor.stop()
```

## 性能・リソース考慮事項

### 軽量設計の特徴
- 最小限のメモリフットプリント
- 効率的なスレッド利用
- CPU使用量の最適化

### 推奨設定値
```python
# 用途別推奨設定
usage_patterns = {
    "realtime_monitoring": {
        "timeout": 10,    # 10秒
        "interval": 2     # 2秒間隔
    },
    "service_monitoring": {
        "timeout": 60,    # 1分
        "interval": 15    # 15秒間隔
    },
    "batch_processing": {
        "timeout": 300,   # 5分
        "interval": 60    # 1分間隔
    },
    "background_tasks": {
        "timeout": 1800,  # 30分  
        "interval": 300   # 5分間隔
    }
}
```

## 依存関係・要件

### 必須依存関係
- `threading`: スレッド制御
- `time`: 時刻管理
- 標準ライブラリのみ（外部依存なし）

### システム要件
- Python 3.7以上
- マルチスレッド対応OS
- 最小限のシステムリソース

## 注意事項・制限

### 設計上の制限
- 単純なタイムアウトベース監視のみ
- 複雑な条件判定は非対応
- ネットワーク監視等は上位層で実装

### 使用上の注意
- コールバック関数は軽量に保つ
- 長時間ブロックする処理は避ける
- 適切なタイムアウト値の設定が重要

## 関連モジュール

- `threading`: スレッド管理
- `config.py`: 監視設定管理
- `utils.py`: エラーログ・ユーティリティ
- `controller.py`: 監視制御インターフェース

## 将来の改善点

- より複雑な監視条件のサポート
- 監視統計・メトリクス収集機能
- 設定可能な復旧戦略
- 分散監視システムとの連携
- Webインターフェースでの監視状態表示