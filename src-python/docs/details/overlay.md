# overlay - VRオーバーレイ統合システム

## 概要

VRChat向けのOpenVRオーバーレイシステムです。翻訳結果や字幕をVR空間内に表示する機能を提供し、HMD・コントローラー追跡、フェード効果、多言語フォント対応を統合的に管理します。

## 主要コンポーネント

### overlay.py - メインオーバーレイ管理
- OpenVRオーバーレイの生成・配置・制御
- HMD・左手・右手への追跡設定
- フェードイン・フェードアウト効果

### overlay_image.py - 画像生成・描画
- 多言語対応テキスト画像生成  
- メッセージログ・履歴表示
- フォント・レイアウト管理

### overlay_utils.py - 数学的変換ユーティリティ
- 3D座標変換行列計算
- オイラー角・回転行列変換
- 同次座標系変換

## クラス構造

### Overlay クラス (overlay.py)

```python
class Overlay:
    def __init__(self, settings_dict: Dict[str, Dict[str, Any]]) -> None:
        self.system: Optional[Any] = None          # OpenVRシステム
        self.overlay: Optional[Any] = None         # オーバーレイインターface  
        self.handle: Dict[str, Any] = {}           # サイズ別ハンドル
        self.settings: Dict[str, Dict[str, Any]]   # サイズ別設定
        self.lastUpdate: Dict[str, float] = {}     # 最終更新時刻
        self.fadeRatio: Dict[str, float] = {}      # フェード比率
```

VRオーバーレイの総合管理クラス

#### 主要機能
- OpenVRの初期化・管理
- 複数サイズオーバーレイの同時管理
- リアルタイムフェード効果処理
- SteamVR接続状態監視

### OverlayImage クラス (overlay_image.py)

```python
class OverlayImage:
    LANGUAGES = {
        "Default": "NotoSansJP-Regular.ttf",
        "Japanese": "NotoSansJP-Regular.ttf", 
        "Korean": "NotoSansKR-Regular.ttf",
        "Chinese Simplified": "NotoSansSC-Regular.ttf",
        "Chinese Traditional": "NotoSansTC-Regular.ttf"
    }
    
    def __init__(self, root_path: Optional[str] = None) -> None:
        self.message_log: List[dict] = []
        self.root_path: str
```

テキスト画像生成・多言語フォント管理クラス

#### 主要機能
- 多言語フォント自動選択
- メッセージ履歴管理
- 動的画像生成・合成
- UI要素のサイズ計算

## 主要メソッド

### Overlay クラス

#### 初期化・制御

```python
def startOverlay(self) -> None
```

オーバーレイシステム開始

```python
def shutdownOverlay(self) -> None
```

オーバーレイシステム終了・リソース解放

```python
def reStartOverlay(self) -> None  
```

オーバーレイシステム再起動

#### 表示制御

```python
def showOverlay(self, image: Image, size: str) -> None
```

画像をオーバーレイに表示

#### パラメータ
- **image**: 表示するPIL画像
- **size**: オーバーレイサイズ識別子

```python
def setOpacity(self, opacity: float, size: str) -> None
```

オーバーレイ透明度設定

#### パラメータ  
- **opacity**: 透明度（0.0-1.0）
- **size**: 対象サイズ

```python
def setTrackedDeviceRelative(self, tracker: str, size: str) -> None
```

追跡デバイスへのオーバーレイ配置

#### パラメータ
- **tracker**: 追跡デバイス（"HMD", "LeftHand", "RightHand"）
- **size**: オーバーレイサイズ

### OverlayImage クラス

#### 画像生成

```python
def createOverlayImage(self, message: str, language: str, ui_size: dict, 
                      ui_settings: dict, message_log_settings: dict) -> Image
```

オーバーレイ用画像の生成

#### パラメータ
- **message**: 表示メッセージ
- **language**: 言語設定
- **ui_size**: UIサイズ設定
- **ui_settings**: UI表示設定  
- **message_log_settings**: ログ表示設定

#### 戻り値
- **Image**: 生成されたPIL画像

#### 履歴管理

```python
def addMessageLog(self, message: str, timestamp: datetime) -> None
```

メッセージログに新規追加

#### パラメータ
- **message**: 追加するメッセージ
- **timestamp**: タイムスタンプ

```python
def clearMessageLog(self) -> None
```

メッセージログのクリア

## 使用方法

### 基本的なオーバーレイ表示

```python
from models.overlay.overlay import Overlay
from models.overlay.overlay_image import OverlayImage
from PIL import Image

# オーバーレイ設定
settings = {
    "small": {
        "width": 0.3,
        "height": 0.1, 
        "x_pos": 0.0,
        "y_pos": -0.2,
        "z_pos": 1.0,
        "opacity": 0.8,
        "display_duration": 3.0,
        "fadeout_duration": 1.0
    },
    "large": {
        "width": 0.5,
        "height": 0.2,
        "x_pos": 0.0, 
        "y_pos": -0.3,
        "z_pos": 1.2,
        "opacity": 0.9,
        "display_duration": 5.0,
        "fadeout_duration": 1.5
    }
}

# オーバーレイシステム初期化
overlay_system = Overlay(settings)
overlay_image = OverlayImage()

# システム開始
overlay_system.startOverlay()

# 翻訳結果の表示
translation_text = "Hello, world! / こんにちは、世界！"

# 画像生成設定
ui_size = OverlayImage.getUiSizeSmallLog()
ui_settings = {
    "font_size": 20,
    "text_color": (255, 255, 255, 255),
    "background_color": (0, 0, 0, 180)
}
message_log_settings = {
    "enabled": True,
    "max_lines": 5
}

# 画像生成・表示
overlay_img = overlay_image.createOverlayImage(
    message=translation_text,
    language="Japanese",
    ui_size=ui_size,
    ui_settings=ui_settings,
    message_log_settings=message_log_settings
)

# オーバーレイに表示
overlay_system.showOverlay(overlay_img, "small")

# システム終了
import time
time.sleep(10)
overlay_system.shutdownOverlay()
```

### HMD・コントローラー追跡設定

```python
# HMDに固定表示
overlay_system.setTrackedDeviceRelative("HMD", "large")

# 左手コントローラーに追従
overlay_system.setTrackedDeviceRelative("LeftHand", "small")

# 右手コントローラーに追従  
overlay_system.setTrackedDeviceRelative("RightHand", "small")

# 位置・回転の微調整（設定変更）
overlay_system.settings["small"]["x_pos"] = 0.1
overlay_system.settings["small"]["y_pos"] = -0.1
overlay_system.settings["small"]["z_pos"] = 0.8
overlay_system.settings["small"]["x_rotation"] = -30.0
overlay_system.settings["small"]["y_rotation"] = 15.0

# 設定を適用
overlay_system.setTrackedDeviceRelative("LeftHand", "small")
```

### フェード効果制御

```python
# フェード効果設定
overlay_system.updateDisplayDuration(4.0, "large")    # 4秒表示
overlay_system.updateFadeoutDuration(2.0, "large")    # 2秒でフェードアウト

# 即座に透明度変更
overlay_system.setOpacity(0.5, "large")  # 50%透明度

# フェード効果を無効にして固定表示
overlay_system.settings["small"]["fadeout_duration"] = 0
overlay_system.setOpacity(1.0, "small")  # 完全不透明で固定
```

### 多言語対応表示

```python
# 日本語表示
japanese_text = "これは日本語のテストです"
jp_image = overlay_image.createOverlayImage(
    message=japanese_text,
    language="Japanese",
    ui_size=ui_size,
    ui_settings=ui_settings,
    message_log_settings=message_log_settings
)
overlay_system.showOverlay(jp_image, "large")

# 韓国語表示
korean_text = "이것은 한국어 테스트입니다"
kr_image = overlay_image.createOverlayImage(
    message=korean_text,
    language="Korean", 
    ui_size=ui_size,
    ui_settings=ui_settings,
    message_log_settings=message_log_settings
)
overlay_system.showOverlay(kr_image, "small")

# 中国語（簡体字）表示
chinese_text = "这是中文测试"
cn_image = overlay_image.createOverlayImage(
    message=chinese_text,
    language="Chinese Simplified",
    ui_size=ui_size,
    ui_settings=ui_settings,  
    message_log_settings=message_log_settings
)
overlay_system.showOverlay(cn_image, "large")
```

### メッセージログ機能

```python
from datetime import datetime

# メッセージログの追加
overlay_image.addMessageLog("最初のメッセージ", datetime.now())
overlay_image.addMessageLog("翻訳結果: Hello -> こんにちは", datetime.now())
overlay_image.addMessageLog("音声認識: こんにちは", datetime.now())

# ログ表示設定
log_settings = {
    "enabled": True,
    "max_lines": 3,          # 最大3行表示
    "show_timestamp": True,   # タイムスタンプ表示
    "font_size": 16,
    "text_color": (200, 200, 200, 255)
}

# ログ付きオーバーレイ画像生成
logged_image = overlay_image.createOverlayImage(
    message="新しいメッセージ",
    language="Japanese",
    ui_size=ui_size,
    ui_settings=ui_settings,
    message_log_settings=log_settings
)

overlay_system.showOverlay(logged_image, "large")

# ログクリア
overlay_image.clearMessageLog()
```

## 座標系・変換システム

### 基本座標設定

```python
# HMD基準座標（頭部固定表示）
def getHMDBaseMatrix() -> np.ndarray:
    x_pos = 0.0      # 左右位置
    y_pos = -0.4     # 上下位置（下方向）
    z_pos = 1.0      # 前後位置（前方向）
    x_rotation = 0.0  # X軸回転
    y_rotation = 0.0  # Y軸回転  
    z_rotation = 0.0  # Z軸回転
    
# 左手コントローラー基準座標
def getLeftHandBaseMatrix() -> np.ndarray:
    x_pos = 0.3       # 右側にオフセット
    y_pos = 0.1       # 上方向にオフセット
    z_pos = -0.31     # 手前にオフセット
    x_rotation = -65.0 # 下向きに傾斜
    y_rotation = 165.0 # Y軸回転
    z_rotation = 115.0 # Z軸回転

# 右手コントローラー基準座標  
def getRightHandBaseMatrix() -> np.ndarray:
    x_pos = -0.3       # 左側にオフセット
    y_rotation = -165.0 # 左手と対称
    z_rotation = -115.0 # 左手と対称
```

### 変換行列計算 (overlay_utils.py)

```python
import numpy as np
from models.overlay.overlay_utils import *

# 移動変換
translation = (0.1, -0.2, 0.5)  # x, y, z移動
translation_matrix = calcTranslationMatrix(translation)

# 回転変換（各軸独立）
x_rotation_matrix = calcRotationMatrixX(30.0)  # X軸30度回転
y_rotation_matrix = calcRotationMatrixY(45.0)  # Y軸45度回転
z_rotation_matrix = calcRotationMatrixZ(60.0)  # Z軸60度回転

# オイラー角から回転行列生成
euler_angles = (30.0, 45.0, 60.0)  # X, Y, Z軸回転角度
rotation_matrix = euler_to_rotation_matrix(euler_angles)

# 基本行列への変換適用
base_matrix = getHMDBaseMatrix()
translation = (0.05, -0.1, 0.2)
rotation = (10.0, -5.0, 0.0)
transformed_matrix = transform_matrix(base_matrix, translation, rotation)

# 3x4行列を4x4同次座標に変換  
homogeneous_matrix = toHomogeneous(transformed_matrix)
```

### カスタム配置設定

```python
# カスタム位置でのオーバーレイ配置
def createCustomOverlay(overlay_system, custom_pos, custom_rot, size):
    """カスタム位置・回転でのオーバーレイ設定"""
    
    # 設定を動的に変更
    overlay_system.settings[size]["x_pos"] = custom_pos[0]
    overlay_system.settings[size]["y_pos"] = custom_pos[1]  
    overlay_system.settings[size]["z_pos"] = custom_pos[2]
    overlay_system.settings[size]["x_rotation"] = custom_rot[0]
    overlay_system.settings[size]["y_rotation"] = custom_rot[1]
    overlay_system.settings[size]["z_rotation"] = custom_rot[2]
    
    # 追跡デバイス設定を再適用
    overlay_system.setTrackedDeviceRelative("HMD", size)

# 使用例：カスタム配置
custom_position = (0.2, -0.3, 0.8)    # やや右下前方
custom_rotation = (-15.0, 10.0, 5.0)  # 軽く傾斜
createCustomOverlay(overlay_system, custom_position, custom_rotation, "large")
```

## 高度な機能

### 動的サイズ・レイアウト管理

```python
class AdaptiveOverlayManager:
    """適応的オーバーレイ管理クラス"""
    
    def __init__(self, base_overlay_system, base_overlay_image):
        self.overlay = base_overlay_system
        self.image_gen = base_overlay_image
        self.current_layout = "compact"
        
    def adaptLayoutToContent(self, message, language):
        """コンテンツに応じたレイアウト自動調整"""
        
        # メッセージ長に応じてサイズ決定
        if len(message) < 50:
            layout = "compact"
            size_key = "small"
        elif len(message) < 150:
            layout = "standard" 
            size_key = "medium"
        else:
            layout = "expanded"
            size_key = "large"
            
        # 言語に応じたフォントサイズ調整
        if language in ["Chinese Simplified", "Chinese Traditional"]:
            font_scale = 1.1  # 中国語は少し大きめ
        elif language == "Korean":
            font_scale = 1.05 # 韓国語は微調整
        else:
            font_scale = 1.0  # 日本語・その他
            
        # UI設定の動的生成
        ui_size = self.getAdaptiveUiSize(layout)
        ui_settings = {
            "font_size": int(18 * font_scale),
            "line_height": int(24 * font_scale),
            "text_color": (255, 255, 255, 255),
            "background_color": (0, 0, 0, 200),
            "border_width": 2,
            "border_color": (100, 150, 255, 255)
        }
        
        return ui_size, ui_settings, size_key
    
    def getAdaptiveUiSize(self, layout):
        """レイアウトに応じたUIサイズ取得"""
        
        layouts = {
            "compact": {
                "width": 400,
                "height": 100,
                "margin": 10,
                "padding": 8
            },
            "standard": {
                "width": 600,
                "height": 150,
                "margin": 15,
                "padding": 12
            },
            "expanded": {
                "width": 800,
                "height": 200,
                "margin": 20,
                "padding": 16
            }
        }
        
        return layouts.get(layout, layouts["standard"])

# 使用例
adaptive_manager = AdaptiveOverlayManager(overlay_system, overlay_image)

messages = [
    ("Hello!", "English"),
    ("これは中程度の長さのメッセージです。翻訳結果を表示します。", "Japanese"),
    ("这是一个很长的消息，用来测试自适应布局功能。当消息内容很长时，系统会自动选择更大的显示区域，并调整字体大小以确保良好的可读性。", "Chinese Simplified")
]

for message, language in messages:
    # 自動レイアウト調整
    ui_size, ui_settings, size_key = adaptive_manager.adaptLayoutToContent(message, language)
    
    # 画像生成・表示
    adaptive_image = overlay_image.createOverlayImage(
        message=message,
        language=language,
        ui_size=ui_size,
        ui_settings=ui_settings,
        message_log_settings={"enabled": True, "max_lines": 3}
    )
    
    overlay_system.showOverlay(adaptive_image, size_key)
    time.sleep(3)
```

### パフォーマンス監視・最適化

```python
class OverlayPerformanceMonitor:
    """オーバーレイパフォーマンス監視クラス"""
    
    def __init__(self, overlay_system):
        self.overlay = overlay_system
        self.frame_times = []
        self.update_counts = {}
        
    def monitorFrameRate(self, duration=10.0):
        """フレームレート監視"""
        
        start_time = time.monotonic()
        frame_count = 0
        
        while time.monotonic() - start_time < duration:
            frame_start = time.monotonic()
            
            # フレーム処理（空の処理）
            time.sleep(1/90)  # 90Hz目標
            
            frame_end = time.monotonic()
            self.frame_times.append(frame_end - frame_start)
            frame_count += 1
            
        # 統計計算
        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        avg_fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
        
        print(f"平均フレーム時間: {avg_frame_time*1000:.2f}ms")
        print(f"平均FPS: {avg_fps:.1f}")
        print(f"総フレーム数: {frame_count}")
        
        return avg_fps
    
    def optimizeSettings(self, target_fps=60):
        """パフォーマンス目標に基づく設定最適化"""
        
        current_fps = self.monitorFrameRate(5.0)
        
        if current_fps < target_fps * 0.8:
            print("パフォーマンス不足。設定を軽量化します...")
            
            # フェード処理間隔を延長
            for size in self.overlay.settings:
                self.overlay.settings[size]["fadeout_duration"] *= 1.5
                
            # 更新頻度を下げる
            # (mainloopの sleep_time 調整は overlay.py 内で実装)
            
        elif current_fps > target_fps * 1.2:
            print("パフォーマンスに余裕があります。品質を向上します...")
            
            # より滑らかなフェード
            for size in self.overlay.settings:
                self.overlay.settings[size]["fadeout_duration"] *= 0.8

# 使用例
performance_monitor = OverlayPerformanceMonitor(overlay_system)
performance_monitor.monitorFrameRate(10.0)
performance_monitor.optimizeSettings(target_fps=60)
```

## エラーハンドリング・復旧

### 堅牢な接続管理

```python
class RobustOverlaySystem:
    """堅牢性を高めたオーバーレイシステム"""
    
    def __init__(self, settings_dict):
        self.base_overlay = Overlay(settings_dict)
        self.connection_retries = 3
        self.auto_reconnect = True
        
    def safeStartOverlay(self, max_retries=None):
        """安全なオーバーレイ開始（リトライ機構付き）"""
        
        retries = max_retries or self.connection_retries
        
        for attempt in range(retries):
            try:
                # SteamVR接続確認
                if not self.base_overlay.checkSteamvrRunning():
                    print("SteamVRが起動していません。待機中...")
                    time.sleep(5)
                    continue
                
                # オーバーレイ開始
                self.base_overlay.startOverlay()
                
                # 初期化完了まで待機
                timeout = 10.0
                start_time = time.monotonic()
                
                while not self.base_overlay.initialized and time.monotonic() - start_time < timeout:
                    time.sleep(0.1)
                
                if self.base_overlay.initialized:
                    print("オーバーレイシステム開始完了")
                    return True
                else:
                    print(f"初期化タイムアウト（試行 {attempt + 1}/{retries}）")
                    
            except Exception as e:
                print(f"オーバーレイ開始エラー（試行 {attempt + 1}/{retries}）: {e}")
                
                # 既存システムのクリーンアップ
                try:
                    self.base_overlay.shutdownOverlay()
                except Exception:
                    pass
                
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # 指数バックオフ
        
        print("オーバーレイシステムの開始に失敗しました")
        return False
    
    def monitorConnection(self):
        """接続監視・自動復旧"""
        
        while self.auto_reconnect:
            try:
                if self.base_overlay.initialized and not self.base_overlay.checkActive():
                    print("OpenVR接続が切断されました。再接続を試行します...")
                    
                    self.base_overlay.shutdownOverlay()
                    time.sleep(2)
                    
                    if self.safeStartOverlay():
                        print("オーバーレイシステムが復旧しました")
                    else:
                        print("復旧に失敗しました")
                        
                time.sleep(1)
                
            except Exception as e:
                print(f"接続監視エラー: {e}")
                time.sleep(5)

# 使用例
robust_overlay = RobustOverlaySystem(settings)

# 安全な開始
if robust_overlay.safeStartOverlay():
    # 接続監視開始（別スレッド）
    import threading
    monitor_thread = threading.Thread(target=robust_overlay.monitorConnection, daemon=True)
    monitor_thread.start()
    
    # 通常の操作
    overlay_img = overlay_image.createOverlayImage(...)
    robust_overlay.base_overlay.showOverlay(overlay_img, "small")
```

## VR UI（手首のランチャーとウィンドウ）

字幕のオーバーレイとは別に、VR 内で操作できる画面（ログ・言語・設定のウィンドウ、機能の ON/OFF を並べたランチャー）を出す機能。設定 `OVERLAY_VR_PANEL` が ON の間だけ動く。OFF の間は、ランチャーも含めて隠し、撮影しない。GL と、ツールバー・枠・吹き出しなどの追加のオーバーレイは、初めて ON になったときに作る。作業の経緯・実機で確かめた罠は `docs/vr_ui_handover.md` に残している。

### 構成

```
Tauri (src-tauri/src/lib.rs)  set_vr_panel_window
  └─ "VRCT VR Panel" ウィンドウ (画面外 / vr.html / src-ui/views/vr/)   … VR UI が ON の間だけ作る
        ↑ 状態は VrPanelSyncController.jsx が全 atom を一方向に同期（メイン → VR）
Python (src-python/models/overlay/)
  ├─ overlay.py          Overlay クラス (1 本の mainloop スレッドが全オーバーレイを動かす)
  ├─ window_capture.py   ウィンドウ撮影 (Windows.Graphics.Capture) と入力 (PostMessage)
  ├─ overlay_utils.py    行列ユーティリティ
  └─ overlay_tooltip.py  吹き出しの入力検証・世代 marker・透明マスク
```

- **1 枚の画面に全領域を並べて、1 回だけ撮影する**。領域は panel(ログ) / launcher / popup / toolbar / tooltip。撮った画像を 1 つの OpenGL テクスチャに書き、各領域のオーバーレイへ `setOverlayTexture` で渡して `setOverlayTextureBounds` で切り出す。並びは `vr_layout.json` と `computeVrLayout`（ログの大きさで変わる）。
- SteamVR の GL テクスチャは**最初の大きさで固定**される。最大の並び (`MAX_LAYOUT`) が入る大きさで 1 回だけ作り、以後は bounds で縮める。GL コンテキスト（glfw の非表示ウィンドウ）は作ったスレッドで使い、片付けも overlay スレッドで行う。依存: glfw / PyOpenGL / windows-capture。
- **撮影**: 既定は `WindowStream`（WGC。届いた最新の画像を受け取るだけ）。使えない・止まったときは PrintWindow に戻る。PrintWindow は相手の UI スレッドを待つので**使い捨てスレッド**で行い、結果は overlay スレッドだけが処理する。
- **入力**: WebView 内の `Chrome_RenderWidgetHostHWND` へ PostMessage（OS のカーソルは動かさない）。WebView2 は本物のカーソルでしかホバーを判定しないので、ポインタ位置（`/run/vr_panel_pointer`）から `data-vr-hover` を付けて代用する。
- 画面の拡大率（DPI）が違っても同じに見えるよう、撮影画像の大きさ／論理 px の比で各領域の位置を計算する。

### 通信と安全

- メイン → VR: 全 atom を `vr-panel-state` で同期する。Tauri の `emit` はオブジェクトのキーを辞書順に並べ替えるため、順序に意味のある値は順序つきの形 (`encodeOrdered`) で送り、VR とメインの比較に `JSON.stringify` を使わない。
- VR → バックエンド: VR 画面から直接は送らず、メインウィンドウが代理で送る。送れるのは `/get|set|run/` だけで、`/run/shutdown`、更新、設定ファイル・ログを開く、モデルのダウンロード、認証キー系は拒否する (`isRelayAllowed`)。設定画面を開いている間は、ウィンドウの開閉などを除いて拒否する。

### ランチャー

- 手首（左右は設定）に付く。`launcher_auto_hide` が ON なら、手首を見たときだけ出る（面の向き 45° 以内かつ視線 40° 以内が 0.05 秒続いたら出す。外れて 0.3 秒で消す。0.1 秒でフェード）。レーザーを当てている間は消さない。出始めの 0.2 秒は押せない。
- 左端に VRCT のマーク（吹き出し）を常に出す。ランチャーの領域は 952×128px（`LAUNCHER_WIDTH_PX`。マークの 60px を足しても、ボタンの大きさは 880px 幅のときと同じ）。横幅は `ui_scaling`（m）で、既定は 0.303。
- ログボタンの 600ms 長押しで、見失ったログを目の前へ呼び戻す (`/run/vr_panel_recall_log`)。
- **操作の吹き出し**（`OVERLAY_VR_TOOLTIP`、既定 ON）: 別のオーバーレイ（`VRCT_tooltip`）。VR 画面が描いた吹き出しを撮影し、画像に埋めた世代 marker（epoch 48bit / revision 32bit の 80 セル）が現在の要求と一致したときだけ表示する（古い撮影結果が混ざらないため）。

### 起動演出（`launcher_intro_state`）

VR UI を ON にして**最初に**ランチャーを出すときだけ再生する。状態は Python が持つ（idle / pending / playing）。変わったら `/run/vr_panel_launcher_intro` で UI へ送る。状態を送る形（イベントではなく状態）なので、再接続や遅れで古い演出を再生しない。

1. VR UI が ON になる（init / OFF→ON）と pending。中身は出さない。
2. 画面が一度撮れた (`panel_last_raw`) 時点で、ヘッドセットを着けていれば (`headsetWorn`)、頭の正面（視線の先 0.7m）にランチャーのオーバーレイごと出して playing にする。着用が分からない・手首を見たほうが先なら、手首でそのまま playing にする（どちらでも、ランチャーが出なくなることがないように）。
3. 正面（1.0 秒）では視線に追従し、飛び始める位置で固定する。VR 画面は VRCT のアイコンだけを大きく出す（手首の大きさの 7.5 倍。領域は高さ約 128px なので、大きいほど荒い）。
4. 手首（0.6 秒）へだんだん速く吸い寄せ、掛け算で縮める（`introFlightPose`。向きは slerp）。手首が追跡できないときは今の場所で待ち、時間切れで通常の位置へ戻す。
5. 着いたらロゴ入りのカプセルが現れ、文字だけが消え、吹き出しは左端へスライドして残り（本物のマークの位置で入れ替わる）、カプセルが横に開いてボタンが並ぶ（VR 画面の CSS）。全体で約 3.2 秒。この間 (`_LAUNCHER_INTRO_SEC`=3.7 秒) は出し続け、押せない。

- 演出中は、領域の外側（VR 画面の背景色 `#151517`）を透明にする (`introKeyAlpha`)。領域の左上の角のピクセルを背景色として使う。VR 画面は不透明にしか描けないため。色との差が小さいほど透明にし、透明にした部分は色も 0 にする。
- 時間は Python (`_INTRO_FRONT_SEC` など) と `VrLauncher.module.scss` の `intro_*` を**一緒に**変える。

### スレッドと負荷

- overlay スレッドは優先度を上げ (ABOVE_NORMAL)、OCR のスレッドと ONNX の作業スレッドは下げる (BELOW_NORMAL。`BackgroundThreads`)。ONNX のスレッド数は `ocr_onnx_threads()`（最大 4）。
- SteamVR の起動確認は Toolhelp（約 15ms）。`psutil.process_iter` は約 2 秒かかり、OCR 中に VR UI が遅れる原因だった。
- SteamVR につながらないときは 10 秒ごとに確かめ直す（ログは最初の 1 回だけ）。OFF にすると止まる。
- 診断ログ: `overlay: 処理に時間がかかっています`（10 秒ごとの最大 ms）、`処理が止まっています`、`VR画面の撮影に時間がかかっています`、`overlay layout: ...`。段階は `markStep` で記録する。

### 実機でしか確認できないこと

HMD の見え方、WGC の滑らかさ（約 16fps）、DPI 125/150%、Windows 10 での WGC、機種ごとの着用判定（`getTrackedDeviceActivityLevel`）、配布ビルドに `glfw3.dll` などが入ること。テストは偽の OpenVR で状態遷移を確かめるまで。

## 依存関係・システム要件

### 必須依存関係
- `openvr`: OpenVR Python バインディング
- `numpy`: 数値計算・行列演算
- `PIL (Pillow)`: 画像処理・生成
- `psutil`: プロセス監視

### システム要件
```python
system_requirements = {
    "steamvr": "SteamVR環境必須",
    "openvr_runtime": "OpenVR Runtime",
    "vr_headset": "対応VRヘッドセット（Oculus, Vive, Index等）",
    "graphics": "VR対応GPU",
    "python": "Python 3.7以上"
}

performance_requirements = {
    "cpu": "VR処理に十分なCPU性能",
    "memory": "追加メモリ使用量 ~100-500MB",
    "disk_space": "フォントファイル用容量 ~50MB"
}
```

### オプション依存関係
- `utils.errorLogging`: エラーログ機能（フォールバック処理あり）

## 注意事項・制限

### VR環境制限
- SteamVRが起動していない場合は動作不可
- VRヘッドセットが接続されていない場合は制限あり
- OpenVRドライバーの互換性に依存

### パフォーマンス制限
- リアルタイム描画処理によるCPU・GPU負荷
- フォントレンダリングによるメモリ使用量
- 高解像度VRディスプレイでの描画負荷

### プラットフォーム制限
```python
platform_limitations = {
    "windows": "主要サポートプラットフォーム",
    "linux": "SteamVR Linux版での制限あり", 
    "macos": "SteamVR macOS版サポート終了により制限",
    "mobile_vr": "OpenVR非対応のため利用不可"
}
```

## 関連モジュール

- `config.py`: オーバーレイ設定管理
- `controller.py`: オーバーレイ制御インターフェース  
- `model.py`: オーバーレイ機能統合
- `utils.py`: エラーログ・ユーティリティ

## 最近の更新 (2025-10-20)

### フォント探索仕様の強化

`overlay_image.py` に PyInstaller ビルド後の `_internal/fonts/` ディレクトリ検出ロジックを追加。以下の優先順位でフォントディレクトリを探索:

1. `root_path/_internal/fonts/` (PyInstallerバンドル環境)
2. `src-python/models/overlay/fonts/` (開発環境相対パス)
3. `models/overlay/fonts/` (直接実行時)

見つからない場合は `FileNotFoundError` で早期通知。これにより配布バイナリと開発環境で同一コードパスを維持。

### 影響

| 項目 | 内容 |
|------|------|
| PyInstaller対応 | バンドル後のフォント読み込み失敗を防止 |
| 移植性 | 環境差異をコード内条件分岐で吸収 |
| エラー検知 | フォント未配置時の早期例外で不正描画防止 |


## 将来の改善点

- よりリッチなUI要素対応
- アニメーション・エフェクト機能
- カスタムフォント・テーマシステム
- パフォーマンス監視・自動最適化
- 他のVRプラットフォーム対応検討
