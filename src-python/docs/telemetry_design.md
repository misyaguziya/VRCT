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
| **デフォルト状態** | 有効（`telemetry_enabled = true`） |
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
│       ├── state.py             # Enable/disable, last_activity
│       ├── heartbeat.py         # 5分間隔heartbeatスレッド
│       └── core.py              # イベント送信ロジック
└── docs/
    └── details/
        └── telemetry.md         # 実装詳細ドキュメント
```

### コンポーネント責任分離

| モジュール | 責任 |
|-----------|------|
| `__init__.py` | パブリック API、シングルトン管理 |
| `client.py` | Aptabase SDK ラッパー、HTTP通信 |
| `state.py` | ON/OFF 状態、最終操作時刻管理 |
| `heartbeat.py` | 5分間隔スレッド、タイムアウト判定 |
| `core.py` | イベント構築・送信、重複検出 |

---

## イベント仕様

### 送信イベント一覧（固定・追加禁止）

| イベント名 | 説明 | ペイロード |
|-----------|------|----------|
| `app_started` | アプリ起動時 | `{}` |
| `app_closed` | アプリ終了時 | `{}` |
| `session_heartbeat` | 5分間隔アクティブ確認 | `{}` |
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

### Session Heartbeat 仕様

#### アクティブ判定条件
以下のいずれかが発生した場合、セッションはアクティブ

1. **テキスト入力**
   - チャット送信
   - メッセージボックスへの入力
   
2. **ASR 実処理**（マイク or スピーカー）
   - マイク音声認識開始
   - スピーカー音声認識開始
   - 実際の音声処理（UI 状態は使用しない）

#### 送信ルール
- **送信間隔**：5分（300秒）
- **タイムアウト**：最後のアクティビティから5分経過で送信停止
- **復帰条件**：アクティビティ発生 → 次の heartbeat から再開
- **無条件停止**：テレメトリ OFF 時は即座にスレッド停止

#### 実装概略図
```
Timeline:
├─ [Activity] touch_activity() →更新
├─ [300秒待機]
├─ [Check] 最後の操作 < 5分? → Yes → send heartbeat
├─ [300秒待機]
├─ [Check] 最後の操作 < 5分? → No → 待機のみ
└─ [Activity] touch_activity() →復帰 → 次heartbeat送信
```

---

## データフロー

### 初期化フロー

```
1. アプリ起動
   ↓
2. config.json から telemetry_enabled 読込
   ↓
3. telemetry.init(enabled=config.telemetry_enabled)
   ├─ enabled=True の場合
   │  ├─ Aptabase SDK 初期化
   │  ├─ heartbeat スレッド開始
   │  └─ app_started イベント送信
   └─ enabled=False の場合
      └─ すべての処理をスキップ
```

### イベント送信フロー

```
操作発生（翻訳/ASR/テキスト入力）
   ↓
telemetry_enabled チェック
   ├─ False → 何もしない
   └─ True
      ↓
      touch_activity() → 最終時刻更新
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
   ├─ heartbeat スレッド開始
   └─ 次のイベントから通常送信
```

### 設定変更フロー

```
config.json 更新
   ↓
telemetry_enabled: false に変更
   ↓
telemetry.shutdown() 
   ├─ heartbeat スレッド停止
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
        - enabled=True: Aptabase SDK初期化、heartbeat開始、app_started送信
        - enabled=False: すべてのスキップ、以後のtrack()は何もしない
        
    Exception:
        - SDK初期化失敗時: 例外握りつぶし、機能は停止するが無言
    """
    pass


def telemetry.shutdown() -> None:
    """
    テレメトリを終了
    
    Behavior:
        - app_closed イベント送信
        - heartbeat スレッド停止
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
# ACTIVITY TRACKING
# =========================================================================

def telemetry.touch_activity() -> None:
    """
    最終アクティビティ時刻を更新（heartbeat判定用）
    
    Behavior:
        - enabled=False なら何もしない
        - 内部的に datetime.now() を記録
        - 自動呼び出し: track_core_feature() 内から呼び出される
        - 手動呼び出し: テキスト入力検出時など、明示的に呼び出し可
        
    Example:
        # テキスト入力時
        telemetry.touch_activity()
        
        # track_core_feature() は内部で自動呼び出し
        telemetry.track_core_feature("translation")
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
            "last_activity": datetime | None,
            "session_features_sent": list[str],
            "heartbeat_active": bool,
        }
    """
    pass
```

### パブリック API 使用例

#### ケース1: アプリ起動・終了

```python
# mainloop.py
from models.telemetry import telemetry
from config import config

# 起動時
def app_startup():
    telemetry.init(enabled=config.TELEMETRY_ENABLED)
    # ... 他の初期化処理

# 終了時
def app_shutdown():
    telemetry.shutdown()
    # ... 他のクリーンアップ
```

#### ケース2: 翻訳機能

```python
# controller.py
def micMessage(self, result: dict):
    # テキスト入力フェーズ（テキスト入力イベント用）
    message = result["text"]
    telemetry.touch_activity()
    
    # 翻訳開始前（コア機能イベント送信）
    if config.ENABLE_TRANSLATION:
        telemetry.track_core_feature("translation")
        translation, success = model.getInputTranslate(message)
        # ... 処理続行
```

#### ケース3: マイク文字起こし

```python
# model.py
def startMicTranscript(self, fnc):
    # マイク開始前
    telemetry.track_core_feature("mic_speech_to_text")
    
    mic_device = selected_mic_device[0]
    self.mic_audio_recorder = SelectedMicEnergyAndAudioRecorder(...)
    self.mic_audio_recorder.recordIntoQueue(...)
    # ... 処理続行
```

#### ケース4: エラー報告

```python
# controller.py
except Exception as e:
    is_vram_error, error_message = model.detectVRAMError(e)
    if is_vram_error:
        telemetry.track("error", {"error_type": "VRAM_ERROR"})
        # ... エラー処理
```

#### ケース5: 設定変更

```python
# controller.py
def setUiLanguage(data):
    config.UI_LANGUAGE = data
    telemetry.track("config_changed", {"section": "appearance"})
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
from .state import TelemetryState
from .heartbeat import HeartbeatManager
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
        self.heartbeat = HeartbeatManager(self.state)
        self.core = TelemetryCore(self.state)
        self._initialized = True
    
    def init(self, enabled: bool):
        """テレメトリ初期化"""
        self.state.set_enabled(enabled)
        if enabled:
            try:
                self.core.send_event("app_started")
                self.heartbeat.start()
            except Exception:
                pass  # 握りつぶし
    
    def shutdown(self):
        """テレメトリ終了"""
        if self.state.is_enabled():
            try:
                self.core.send_event("app_closed")
            except Exception:
                pass
        self.heartbeat.stop()
        self.state.reset()
    
    def track(self, event: str, payload: dict = None):
        """汎用イベント送信"""
        if not self.state.is_enabled():
            return
        try:
            self.core.send_event(event, payload)
        except Exception:
            pass
    
    def track_core_feature(self, feature: str):
        """コア機能イベント送信（重複検出付き）"""
        if not self.state.is_enabled():
            return
        self.state.touch_activity()
        if self.core.is_duplicate_core_feature(feature):
            return
        try:
            self.core.send_event("core_feature", {"feature": feature})
            self.state.record_feature_sent(feature)
        except Exception:
            pass
    
    def touch_activity(self):
        """アクティビティ時刻更新"""
        if self.state.is_enabled():
            self.state.touch_activity()
    
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
- 最終操作時刻
- セッション内送信済み機能リスト
"""
from datetime import datetime
from threading import Lock


class TelemetryState:
    def __init__(self):
        self._enabled = True  # デフォルト有効
        self._last_activity = None
        self._session_features_sent = set()
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
    
    def touch_activity(self):
        """最終操作時刻更新"""
        with self._lock:
            self._last_activity = datetime.now()
    
    def get_last_activity(self) -> datetime:
        """最終操作時刻取得"""
        with self._lock:
            return self._last_activity
    
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
            self._last_activity = None
            self._session_features_sent.clear()
    
    def get_debug_info(self) -> dict:
        """デバッグ用情報取得"""
        with self._lock:
            return {
                "enabled": self._enabled,
                "last_activity": self._last_activity.isoformat() if self._last_activity else None,
                "session_features_sent": list(self._session_features_sent),
            }
```

### `models/telemetry/heartbeat.py`

```python
"""
Heartbeat スレッド管理
- 5分間隔でアクティブ確認
- 操作なしで5分経過したら送信停止
"""
from datetime import datetime, timedelta
from threading import Thread, Event
import time


class HeartbeatManager:
    INTERVAL = 300  # 5 minutes
    TIMEOUT = 300   # 5 minutes
    
    def __init__(self, state):
        self.state = state
        self.thread = None
        self._stop_event = Event()
    
    def start(self):
        """Heartbeat スレッド開始"""
        if self.thread is not None and self.thread.is_alive():
            return
        self._stop_event.clear()
        self.thread = Thread(target=self._run, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Heartbeat スレッド停止"""
        self._stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=1.0)
            self.thread = None
    
    def _run(self):
        """Heartbeat ループ"""
        while not self._stop_event.is_set():
            try:
                time.sleep(self.INTERVAL)
                
                if not self.state.is_enabled():
                    continue
                
                last_activity = self.state.get_last_activity()
                if last_activity is None:
                    continue
                
                elapsed = (datetime.now() - last_activity).total_seconds()
                if elapsed < self.TIMEOUT:
                    # アクティブなら heartbeat 送信
                    from .core import TelemetryCore
                    try:
                        core = TelemetryCore(self.state)
                        core.send_event("session_heartbeat")
                    except Exception:
                        pass  # 握りつぶし
            except Exception:
                pass  # スレッド不停止のため握りつぶし
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

def test_heartbeat_sends_when_active():
    """5分操作なしなら heartbeat 送信"""
    # heartbeat スレッドがちゃんと5分待機後に
    # touch_activity() 後のアクティブ判定で送信

def test_heartbeat_stops_when_inactive():
    """5分以上操作なしなら heartbeat 停止"""
    # last_activity が 5分以上古い場合、
    # heartbeat 送信しない

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
    telemetry.touch_activity()
    
    # 5分待機（テスト時は短縮）
    # heartbeat 送信確認
    
    # 終了
    telemetry.shutdown()
    # app_closed 送信確認
```

### テスト環境での設定

```python
# config.py 修正
TELEMETRY_ENABLED = True  # デフォルト有効

# config.json への保存
{
    "telemetry_enabled": true
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
- [ ] heartbeat が UI 状態に依存していない
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
| 3 | `heartbeat.py` 作成・テスト | 高 |
| 4 | `config.py` に `telemetry_enabled` 追加 | 高 |
| 5 | `controller.py` に API 呼び出し追加 | 高 |
| 6 | `mainloop.py` に init/shutdown 追加 | 高 |
| 7 | ユニット・統合テスト | 高 |
| 8 | ドキュメント更新 | 中 |
| 9 | UI 文言追加 | 中 |

---

## 完了条件（定義）

- [x] テレメトリ OFF 時、一切の通信が発生しない
- [x] オフライン状態でもアプリが正常に動作する
- [x] `core_feature` は1セッション中に1回のみ送信される
- [x] heartbeat は 5分以上操作がないと送信を停止する
- [x] 個人情報・入力内容・音声データは絶対に送信されない
- [x] 送信失敗時は例外を握りつぶし、無言で続行する
- [x] マイク/スピーカーイベントが分離している

---

## 参考資料

- [Aptabase Python SDK](https://github.com/aptabase/aptabase-python)
- [Aptabase Dashboard](https://aptabase.com)
- [Privacy by Design](https://en.wikipedia.org/wiki/Privacy_by_design)

