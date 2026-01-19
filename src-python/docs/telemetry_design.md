# VRCT Python Sidecar テレメトリ（Aptabase）実装設計書

## 目次
1. [概要](#概要)
2. [基本方針](#基本方針)
3. [アーキテクチャ](#アーキテクチャ)
4. [イベント仕様](#イベント仕様)
5. [データフロー](#データフロー)
6. [API 設計](#api-設計)
7. [実装詳細](#実装詳細)
8. [テスト計画](#テスト計画)
9. [セキュリティとプライバシー](#セキュリティとプライバシー)

---

## 概要

### 目的
VRCT の **匿名な使用状況** を取得し、プロダクトの改善に役立てる。

### 特徴
- **デフォルト有効**：テレメトリはデフォルトで有効化される
- **ユーザーコントロール**：設定から任意でオン/オフ可能
- **プライバシー重視**：個人情報・入力内容・音声データは一切送信しない
- **OSS対応**：透明性と説明可能性を重視した設計
- **安定性優先**：失敗時の再送・保存は行わない

### 使用技術
- **SDK**: Aptabase Python SDK
- **ホスト**：Aptabase クラウド
- **App Key**: コード直埋め込み（環境変数・外部ファイルは未使用）

---

## 基本方針（厳守事項）

| 項目 | 方針 |
|------|------|
| **デフォルト状態** | 有効（`ENABLE_TELEMETRY = true`） |
| **ユーザー制御** | 設定から任意で無効化可能 |
| **無効時の動作** | 一切の通信・スレッド・処理を停止 |
| **送信内容** | イベント名と固定属性のみ |
| **禁止データ** | 個人識別 ID、入力内容、音声データ、UI 状態 |
| **失敗時動作** | 例外を握りつぶし、再送・保存・バッファリング禁止 |
| **オフライン時** | 機能を停止するのみ（アプリ動作に影響なし） |

---

## アーキテクチャ

### ディレクトリ構成
```
src-python/
├── models/
│   └── telemetry/
│       ├── __init__.py          # Public API + singleton管理
│       ├── client.py            # Aptabase wrapper
│       ├── state.py             # Enable/disable、セッション内送信済み機能管理
│       └── core.py              # イベント送信ロジック、重複検出
└── docs/
    └── details/
        └── telemetry.md         # 実装詳細ドキュメント
```

### コンポーネント責任分離

| モジュール | 責任 |
|-----------|------|
| `__init__.py` | パブリック API、シングルトン管理、イベントループ管理 |
| `client.py` | Aptabase SDK ラッパー、HTTP通信、ログレベル設定 |
| `state.py` | ON/OFF 状態、セッション内送信済み機能の追跡 |
| `core.py` | イベント構築・送信、重複検出 |

---

## イベント仕様

### 送信イベント一覧（固定・追加禁止）

| イベント名 | 説明 | ペイロード |
|-----------|------|----------|
| `app_started` | アプリ起動時 | `{}` |
| `app_closed` | アプリ終了時 | `{}` |
| `core_feature` | コア機能開始 | `{"feature": "translation" \| "mic_speech_to_text" \| "speaker_speech_to_text" \| "text_input"}` |
| `settings_opened` | 設定画面を開く | `{}` |
| `config_changed` | 設定変更 | `{"section": str}` |
| `error` | エラー発生 | `{"error_type": str}` |

### `core_feature` イベント詳細

機能の **実処理開始時** のみ送信（1セッション1回のみ）

#### 定義済み種別（拡張禁止）
```python
CORE_FEATURES = {
    "translation": "翻訳機能を使用",
    "mic_speech_to_text": "マイク音声認識（送信側）",
    "speaker_speech_to_text": "スピーカー音声認識（受信側）",
    "text_input": "テキスト入力（チャット送信）"
}
```

#### 送信ルール
- **マイク/スピーカーは必ず分離**：`mic_speech_to_text` と `speaker_speech_to_text` は別イベント
- **1セッション中に同一 feature は1回のみ**：重複送信禁止
- **実処理開始時のみ**：API呼び出し前の段階で送信
- **UI 状態不問**：最前面/最小化のような UI 状態は判定に使用しない

#### 実装例
```python
# 翻訳実行前
telemetry.track_core_feature("translation")
result = translator.translate(...)  # 実処理

# マイク文字起こし開始時
telemetry.track_core_feature("mic_speech_to_text")
recorder.start()  # 実処理

# チャット送信時
telemetry.track_core_feature("text_input")
send_message()  # 実処理
```

---

## データフロー

### 初期化フロー

```
1. アプリ起動
   ↓
2. config.json から ENABLE_TELEMETRY 読込
   ↓
3. telemetry.init(enabled=config.ENABLE_TELEMETRY)
   ├─ enabled=True の場合
   │  ├─ Aptabase SDK 初期化
   │  └─ app_started イベント送信
   └─ enabled=False の場合
      └─ すべての処理をスキップ
```

### イベント送信フロー

```
操作発生（翻訳/ASR/テキスト入力）
   ↓
ENABLE_TELEMETRY チェック
   ├─ False → 何もしない
   └─ True
      ↓
      1セッション内で同一 feature 送信済み?
      ├─ Yes → スキップ
      └─ No
         ↓
         track_core_feature(feature_name)
         ↓
         try:
           Aptabase.track(event)
         except:
           握りつぶし（ログに出力しない）
```

### OFF → ON 時の復帰フロー

```
OFF 状態（設定保存）
   ↓
ユーザーが ON に切り替え
   ↓
telemetry.init(enabled=True)
   ├─ 既知例外は握りつぶし
   ├─ Aptabase 初期化
   ├─ asyncio イベントループ開始
   └─ 次のイベントから通常送信
```

### 設定変更フロー

```
config.json 更新
   ↓
ENABLE_TELEMETRY: false に変更
   ↓
telemetry.shutdown() 
   ├─ asyncio イベントループ停止
   ├─ 内部状態をリセット
   └─ メモリ解放
   ↓
OFF 中のデータは完全破棄
```

---

## API 設計

### パブリック API

```python
# =========================================================================
# INITIALIZATION & SHUTDOWN
# =========================================================================

def telemetry.init(enabled: bool) -> None:
    """
    テレメトリを初期化
    
    Args:
        enabled (bool): テレメトリを有効にするか
        
    Behavior:
        - enabled=True: Aptabase SDK初期化、asyncioイベントループ開始、app_started送信
        - enabled=False: すべてのスキップ、以後のtrack()は何もしない
        - 複数回呼び出し時: _init_called フラグで二重初期化を防止
        
    Exception:
        - SDK初期化失敗時: 例外握りつぶし、機能は停止するが無言
    """
    pass


def telemetry.shutdown() -> None:
    """
    テレメトリを終了
    
    Behavior:
        - app_closed イベント送信
        - asyncio イベントループ停止
        - 内部状態をリセット
        - 例外は握りつぶし（無言）
    """
    pass


# =========================================================================
# EVENT TRACKING
# =========================================================================

def telemetry.track(
    event: str,
    payload: dict | None = None
) -> None:
    """
    汎用イベント送信
    
    Args:
        event (str): イベント名（"app_started", "error" など）
        payload (dict | None): イベントペイロード（デフォルト: None）
        
    Behavior:
        - enabled=False なら何もしない
        - 失敗時は例外を握りつぶし（ログ出力なし）
        - 再送・バッファリングなし
        
    Example:
        telemetry.track("error", {"error_type": "VRAM_ERROR"})
    """
    pass


def telemetry.track_core_feature(feature: str) -> None:
    """
    コア機能イベント送信（重複検出付き）
    
    Args:
        feature (str): 機能名
                      ("translation" | "mic_speech_to_text" | "speaker_speech_to_text" | "text_input")
        
    Behavior:
        - enabled=False なら何もしない
        - 1セッション内で同一 feature の重複送信を防止
        - 実処理開始時に呼び出す（API呼び出し前）
        - 失敗時は例外握りつぶし
        
    Example:
        telemetry.track_core_feature("translation")
        result = translator.translate(...)
    """
    pass


# =========================================================================
# SHUTDOWN
# =========================================================================

def telemetry.shutdown() -> None:
    """
    テレメトリシャットダウン
    
    Behavior:
        - app_closed イベント送信
        - イベントループ停止（フラッシュ待機）
        - Aptabase クライアント停止
        - Tauri sidecar 環境では呼び出し後にプロセス終了
    """
    pass


# =========================================================================
# STATE QUERY
# =========================================================================

def telemetry.is_enabled() -> bool:
    """
    テレメトリが有効か確認
    
    Returns:
        bool: True なら有効、False なら無効
    """
    pass


def telemetry.get_state() -> dict:
    """
    現在の内部状態を取得（デバッグ用）
    
    Returns:
        dict: {
            "enabled": bool,
            "session_features_sent": list[str],
        }
    """
    pass
```

### パブリック API 使用例

#### ケース1: アプリ起動・終了（MVC 準拠）

```python
# model.py
from models.telemetry import telemetry
from config import config

class Model:
    def init(self):
        # ... 既存の初期化処理
        
        # Telemetry 初期化
        try:
            telemetry.init(enabled=config.ENABLE_TELEMETRY)
        except Exception:
            errorLogging()
    
    def shutdown(self):
        """Model cleanup on application shutdown."""
        try:
            # Telemetry 終了（app_closed 送信）
            telemetry.shutdown()
        except Exception:
            errorLogging()
        
        # ... その他のクリーンアップ処理

# controller.py
class Controller:
    def init(self):
        # Model 初期化（telemetry も初期化される）
        model.init()
    
    def shutdown(self):
        # Model シャットダウン（telemetry も終了）
        model.shutdown()
```

#### ケース2: 翻訳機能（MVC 準拠）

```python
# controller.py
def micMessage(self, result: dict):
    # テキスト入力フェーズ
    message = result["text"]
    model.telemetryTouchActivity()  # model 経由でアクティビティ更新
    
    # 翻訳開始前（コア機能イベント送信）
    if config.ENABLE_TRANSLATION:
        model.telemetryTrackCoreFeature("translation")  # model 経由
        translation, success = model.getInputTranslate(message)
        # ... 処理続行
```

#### ケース3: マイク文字起こし（MVC 準拠）

```python
# model.py
def startMicTranscript(self, fnc):
    # マイク開始前（内部で telemetry 呼び出し）
    self.telemetryTrackCoreFeature("mic_speech_to_text")
    
    mic_device = selected_mic_device[0]
    self.mic_audio_recorder = SelectedMicEnergyAndAudioRecorder(...)
    self.mic_audio_recorder.recordIntoQueue(...)
    # ... 処理続行
```

#### ケース4: エラー報告（MVC 準拠）

```python
# controller.py
except Exception as e:
    is_vram_error, error_message = model.detectVRAMError(e)
    if is_vram_error:
        model.telemetryTrack("error", {"error_type": "VRAM_ERROR"})  # model 経由
        # ... エラー処理
```

#### ケース5: 設定変更（MVC 準拠）

```python
# controller.py
def setUiLanguage(data):
    config.UI_LANGUAGE = data
    model.telemetryTrack("config_changed", {"section": "appearance"})  # model 経由
    return {"status": 200, "result": config.UI_LANGUAGE}
```

---

## 実装詳細

### `models/telemetry/__init__.py`

```python
"""
テレメトリ（Aptabase）管理モジュール

パブリック API を提供し、内部実装を隠蔽する。
"""
import asyncio
import threading
from concurrent.futures import Future

from .state import TelemetryState
from .core import TelemetryCore


class Telemetry:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.state = TelemetryState()
        self.core = TelemetryCore(self.state)
        self._loop = None
        self._loop_thread = None
        self._init_called = False
        self._initialized = True
    
    def _start_event_loop(self):
        """バックグラウンドでイベントループを開始"""
        if self._loop_thread is not None and self._loop_thread.is_alive():
            return
        
        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()
        
        self._loop_thread = threading.Thread(target=run_loop, daemon=True, name="telemetry_loop")
        self._loop_thread.start()
        
        # ループが開始されるまで待機
        while self._loop is None:
            pass
    
    def _stop_event_loop(self, timeout: float = 5.0):
        """イベントループを停止（フラッシュ完了を待つ）"""
        if self._loop is None:
            return
        
        # ループにstop()を予約
        self._loop.call_soon_threadsafe(self._loop.stop)
        
        # ループスレッド終了を待機
        if self._loop_thread is not None:
            self._loop_thread.join(timeout=timeout)
        
        self._loop = None
        self._loop_thread = None
    
    def _run_async(self, coro):
        """同期コンテキストから非同期関数を実行"""
        if self._loop is None:
            return
        
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return future.result(timeout=5.0)
        except Exception:
            pass
    
    def _schedule_async(self, coro):
        """非同期タスクをバックグラウンドでスケジュール（待機しない）"""
        if self._loop is None:
            return
        
        try:
            asyncio.run_coroutine_threadsafe(coro, self._loop)
        except Exception:
            pass
    
    def init(self, enabled: bool, app_version: str = "1.0.0"):
        """
        テレメトリ初期化（同期インターフェース）
        
        重要：このメソッドは冪等です。複数回呼ばれても安全です。
        既に初期化済みの場合は、有効/無効の状態のみを更新します。
        """
        # 既に初期化済みの場合は、状態の更新のみ
        if self._init_called:
            self.state.set_enabled(enabled)
            return
        
        # 初回初期化
        self._init_called = True
        self.state.set_enabled(enabled)
        if enabled:
            self._start_event_loop()
            self._run_async(self._init_async(app_version))
    
    async def _init_async(self, app_version: str):
        """非同期初期化処理"""
        await self.core.start(app_version=app_version)
        await self.core.send_event("app_started")
    
    def shutdown(self):
        """テレメトリ終了"""
        try:
            if self.state.is_enabled():
                try:
                    self._run_async(self._shutdown_async())
                except Exception:
                    pass
            
            self._stop_event_loop(timeout=5.0)
        except Exception:
            pass
        finally:
            self.state.reset()
            self._init_called = False
    
    async def _shutdown_async(self):
        """非同期終了処理"""
        await self.core.send_event("app_closed")
        await self.core.stop()
    
    def track(self, event: str, payload: dict = None):
        """汎用イベント送信"""
        if not self.state.is_enabled():
            return
        self._schedule_async(self.core.send_event(event, payload))
    
    def track_core_feature(self, feature: str):
        """コア機能イベント送信"""
        if not self.state.is_enabled():
            return
        if self.core.is_duplicate_core_feature(feature):
            return
        self._schedule_async(self._track_core_feature_async(feature))
    
    async def _track_core_feature_async(self, feature: str):
        """非同期コア機能送信処理"""
        await self.core.send_event("core_feature", {"feature": feature})
        self.state.record_feature_sent(feature)
    
    def is_enabled(self) -> bool:
        """有効状態確認"""
        return self.state.is_enabled()
    
    def get_state(self) -> dict:
        """内部状態取得（デバッグ用）"""
        return self.state.get_debug_info()


# Singleton instance
telemetry = Telemetry()
```

### `models/telemetry/state.py`

```python
"""
テレメトリ状態管理
- enable/disable フラグ
- セッション内送信済み機能リスト
"""
from threading import Lock


class TelemetryState:
    def __init__(self):
        self._enabled = True  # デフォルト有効
        self._session_features_sent = set()
        self._lock = Lock()
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
```

### `models/telemetry/client.py`

```python
"""
Aptabase SDK ラッパー
"""
import json
from typing import Optional, Dict, Any

# Aptabase SDK のインポート
try:
    from aptabase import Client as AptabaseClient
except ImportError:
    AptabaseClient = None


class AptabaseWrapper:
    # App Key は直埋め込み
    APP_KEY = "A-SY-XXXXXXXXXXXXXXX"  # 実装時に実際のキーに置き換え
    
    def __init__(self):
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Aptabase クライアント初期化"""
        if AptabaseClient is None:
            raise ImportError("aptabase library not installed")
        try:
            self.client = AptabaseClient(self.APP_KEY)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Aptabase: {e}")
    
    def track(self, event_name: str, properties: Optional[Dict[str, Any]] = None):
        """イベント送信"""
        if self.client is None:
            raise RuntimeError("Aptabase client not initialized")
        
        try:
            # properties が None なら空辞書
            if properties is None:
                properties = {}
            
            # イベント送信
            self.client.track_event(event_name, properties)
        except Exception as e:
            # 握りつぶし：ログなし
            raise
    
    def close(self):
        """クライアントクローズ"""
        if self.client is not None:
            try:
                # SDK のクローズ処理があれば実行
                if hasattr(self.client, 'close'):
                    self.client.close()
            except Exception:
                pass
```

### `models/telemetry/core.py`

```python
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
            # 初期化失敗時は握りつぶし
            self.client = None
    
    def send_event(self, event_name: str, payload: dict = None):
        """イベント送信"""
        if self.client is None:
            raise RuntimeError("Aptabase client not available")
        
        # ペイロード準備
        properties = payload or {}
        
        # イベント送信
        self.client.track(event_name, properties)
    
    def is_duplicate_core_feature(self, feature: str) -> bool:
        """セッション内の重複チェック"""
        return self.state.has_feature_been_sent(feature)
```

---

## App Closed イベント処理の詳細

### 処理タイミング

`app_closed` イベントはアプリケーション終了時に送信する **最後のイベント** です。以下のタイミングで発火します：

1. **Watchdog タイムアウト**（異常終了）
2. **ユーザーがアプリを閉じる**（正常終了）
3. **KeyboardInterrupt（Ctrl+C）**（強制終了）

### 既存コード構造への組み込み

#### パターン1: mainloop.py の stop() メソッド（MVC 準拠）

```python
# mainloop.py
class Main:
    def stop(self, wait: float = 2.0) -> None:
        """Signal threads to stop and wait for them to finish.

        Args:
            wait: maximum seconds to wait for threads to join.
        """
        # Controller 経由で shutdown（telemetry も含む）
        try:
            self.controller.shutdown()  # model.shutdown() を呼び出し
        except Exception:
            errorLogging()
        
        self._stop_event.set()
        # give threads a chance to exit
        start = time.time()
        for th in self._threads:
            remaining = max(0.0, wait - (time.time() - start))
            th.join(timeout=remaining)
```

**重要**: `controller.shutdown()` は最初に呼び出され、その中で `model.shutdown()` が実行され、最後に `telemetry.shutdown()` が呼び出されます。

#### パターン2: Controller.setWatchdogCallback

Watchdog がタイムアウトした場合も `stop()` 経由で終了するため、上記の実装で自動的に `app_closed` が送信されます。

```python
# mainloop.py
if __name__ == "__main__":
    main_instance.startReceiver()
    main_instance.startHandler()

    # Watchdog タイムアウト時に main_instance.stop() を呼び出し
    # → 自動的に telemetry.shutdown() が実行される
    main_instance.controller.setWatchdogCallback(main_instance.stop)
    
    main_instance.controller.init()
    # ...
```

#### パターン3: KeyboardInterrupt 時

```python
# mainloop.py の Main.start()
def start(self) -> None:
    """Start the main loop to keep the program running."""
    try:
        while not self._stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        self.stop()  # telemetry.shutdown() が呼ばれる
```

### app_closed 送信前の確認事項

`telemetry.shutdown()` が呼ばれる直前に、以下の処理を完了しておくべきです：

| 処理 | タイミング | 理由 |
|------|----------|------|
| **設定保存** | telemetry.shutdown() **前** | 設定が失われるのを防ぐ |
| **ファイルクローズ** | telemetry.shutdown() **前** | ファイルディスクリプタをリソースリークから守る |
| **オーバーレイ終了** | telemetry.shutdown() **前** | VR ウィンドウを正常にクローズ |
| **OSC ハンドラー停止** | telemetry.shutdown() **前** | ネットワークリソースを解放 |
| **モデルクリーンアップ** | telemetry.shutdown() **前** | GPU メモリを解放 |
| **テレメトリ終了** | telemetry.shutdown() | 最後 |

### 実装フローチャート

```
ユーザーがアプリを閉じる / Watchdog タイムアウト / Ctrl+C
    ↓
main_instance.stop() 呼び出し
    ↓
1. try:
     self.controller.shutdown()  # app_closed 送信 + すべてのクリーンアップ
   except:
     pass  # 握りつぶし（通信失敗でも続行）
    ↓
2. self._stop_event.set()
    ↓
3. スレッド停止待機（最大 2.0秒）
    ↓
4. メモリ解放
    ↓
プロセス終了
```

### コード例：model.py でのクリーンアップ

`model.shutdown()` メソッドを追加することで、モデルのリソース解放を統一管理できます：

```python
# model.py
def shutdown(self) -> None:
    """Model cleanup on application shutdown."""
    try:
        # オーバーレイ終了
        if hasattr(self, 'overlay') and self.overlay:
            self.shutdownOverlay()
        
        # Watchdog 停止
        if hasattr(self, 'th_watchdog'):
            self.stopWatchdog()
        
        # WebSocket サーバー停止
        if hasattr(self, 'websocket_server_alive') and self.websocket_server_alive:
            self.stopWebSocketServer()
        
        # OSC ハンドラー停止
        if hasattr(self, 'osc_handler'):
            self.stopReceiveOSC()
        
        # オーディオ停止
        self.stopMicTranscript()
        self.stopSpeakerTranscript()
        self.stopCheckMicEnergy()
        self.stopCheckSpeakerEnergy()
        
        # ロガー停止
        if self.logger:
            self.stopLogger()
        
        # メモリ解放
        gc.collect()
    except Exception:
        errorLogging()
```

その後、mainloop.py で呼び出し：

```python（MVC 準拠）：

```python
# mainloop.py
def stop(self, wait: float = 2.0) -> None:
    """Signal threads to stop and wait for them to finish."""
    
    # Controller 経由でシャットダウン（telemetry + model 含む）
    try:
        self.controller.shutdown()  # model.shutdown() が呼ばれる
    except Exception:
        errorLogging()op_event.set()
    start = time.time()
    for th in self._threads:
        remaining = max(0.0, wait - (time.time() - start))
        th.join(timeout=remaining)
```

### オフライン時の動作

テレメトリが OFF の場合でも、以下のようにコードは安全に機能します：

```python
# telemetry.shutdown() 内の処理（OFF時）
def shutdown(self):
    if self.state.is_enabled():
        try:
            self.core.send_event("app_closed")  # ← 実行される
        except Exception:
            pass
    
    self.state.reset()     # 状態リセット
```

### 通信失敗時の処理

ネットワーク障害で `app_closed` 送信に失敗した場合：

```python
try:
    telemetry.shutdown()  # Aptabase への通信失敗
except Exception:
    pass  # 握りつぶし：エラーメッセージ出力なし
```

**アプリは normal exit します。再送・バッファリング・ログ出力は行いません。**

---

## テスト計画

### ユニットテスト

```python
# test_telemetry.py

def test_init_enabled():
    """初期化時に有効化"""
    telemetry = Telemetry()
    telemetry.init(enabled=True)
    assert telemetry.is_enabled() is True

def test_init_disabled():
    """初期化時に無効化"""
    telemetry = Telemetry()
    telemetry.init(enabled=False)
    assert telemetry.is_enabled() is False

def test_track_when_disabled():
    """無効時にトラック呼び出しが何もしない"""
    telemetry = Telemetry()
    telemetry.init(enabled=False)
    telemetry.track("test_event")  # 例外なし

def test_track_core_feature_no_duplicate():
    """同一feature の重複送信を防止"""
    telemetry = Telemetry()
    telemetry.init(enabled=True)
    
    # 1回目送信
    telemetry.track_core_feature("translation")
    state = telemetry.get_state()
    assert "translation" in state["session_features_sent"]
    
    # 2回目はスキップ（内部的に重複検出）

def test_shutdown_sends_app_closed():
    """shutdown() が app_closed を送信"""
    telemetry = Telemetry()
    telemetry.init(enabled=True)
    telemetry.shutdown()
    # app_closed が送信されたことを確認
```

### 統合テスト

```python
# test_telemetry_integration.py

def test_full_flow():
    """起動～操作～終了の全フロー"""
    from models.telemetry import telemetry
    
    # 起動
    telemetry.init(enabled=True)
    
    # 操作
    telemetry.track_core_feature("translation")
    
    # 終了
    telemetry.shutdown()
    # app_closed 送信確認
```

### テスト環境での設定

```python
# config.py 修正
ENABLE_TELEMETRY = True  # デフォルト有効

# config.json への保存
{
    "ENABLE_TELEMETRY": true
}
```

---

## セキュリティとプライバシー

### データ保護方針

| 項目 | ポリシー | 実装例 |
|------|---------|-------|
| **個人識別 ID** | 送信禁止 | UUID/ユーザーIDなし |
| **入力内容** | 送信禁止 | メッセージ本文送信なし |
| **音声データ** | 送信禁止 | 音声ファイル送信なし |
| **UI 状態** | 使用禁止 | ウィンドウ座標/最小化フラグなし |
| **ログレベル** | HTTPS only | Aptabase 側で暗号化 |

### 実装チェックリスト

- [ ] イベントペイロードに個人情報が含まれていない
- [ ] マイク/スピーカーイベントが分離している
- [ ] OFF 時にすべての通信が停止する
- [ ] 例外が握りつぶされ、ユーザーに見えない
- [ ] Aptabase SDK の最新版を使用
- [ ] App Key がコード内に直埋め込みされている
- [ ] 環境変数・外部ファイルは使用していない

### ユーザーへの通知（OSS 表示文言）

UI に以下を表示：

> This app collects anonymous usage statistics using Aptabase.
> You can disable telemetry at any time in settings.

---

## 実装スケジュール

| フェーズ | タスク | 優先度 |
|---------|--------|--------|
| 1 | `__init__.py`, `state.py` 作成 | 高 |
| 2 | `client.py`, `core.py` 作成 | 高 |
| 3 | `config.py` に `ENABLE_TELEMETRY` 追加 | 高 |
| 4 | `controller.py` に API 呼び出し追加 | 高 |
| 5 | `mainloop.py` に init/shutdown 追加 | 高 |
| 6 | ユニット・統合テスト | 高 |
| 7 | ドキュメント更新 | 中 |
| 8 | UI 文言追加 | 中 |

---

## 完了条件（定義）

- [x] テレメトリ OFF 時、一切の通信が発生しない
- [x] オフライン状態でもアプリが正常に動作する
- [x] `core_feature` は1セッション中に1回のみ送信される
- [x] 個人情報・入力内容・音声データは絶対に送信されない
- [x] 送信失敗時は例外を握りつぶし、無言で続行する
- [x] マイク/スピーカーイベントが分離している

---

## 参考資料

- [Aptabase Python SDK](https://github.com/aptabase/aptabase-python)
- [Aptabase Dashboard](https://aptabase.com)
- [Privacy by Design](https://en.wikipedia.org/wiki/Privacy_by_design)


