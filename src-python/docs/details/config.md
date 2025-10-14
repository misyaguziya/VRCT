# config.py - 設定管理モジュール

## 概要

VRCTアプリケーションの全設定を一元管理するモジュールです。シングルトンパターンを採用し、アプリケーション全体で統一された設定アクセスを提供します。JSON設定ファイルの読み書き、設定の永続化、デバウンス機能付き保存機能を提供します。

## 主要機能

### シングルトン設計
- アプリケーション全体で単一の設定インスタンス
- スレッドセーフな設定アクセス
- 遅延初期化による軽量インポート

### 設定永続化
- JSON形式での設定ファイル管理
- デバウンス機能付き自動保存
- 設定変更の即座反映

### 動的設定管理
- 実行時設定変更対応
- デバイス情報の動的取得
- 言語・エンジン設定の自動更新

### 型安全な設定アクセス
- プロパティベースのアクセス制御
- 読み取り専用・読み書き可能設定の分離
- デコレータによるシリアライゼーション管理

## クラス構造

### Config クラス
```python
class Config:
    _instance = None              # シングルトンインスタンス
    _config_data: Dict[str, Any]  # 設定データ
    _timer: Optional[threading.Timer]  # デバウンスタイマー
    _debounce_time: int = 2       # デバウンス時間（秒）
```

## 設定カテゴリ

### 読み取り専用設定

```python
@property
def VERSION(self) -> str
```
- アプリケーションバージョン

```python  
@property
def PATH_LOCAL(self) -> str
```
- ローカルディレクトリパス

```python
@property
def PATH_CONFIG(self) -> str
```
- 設定ファイルパス

### UI・表示設定

```python
@property
def UI_LANGUAGE(self) -> str
```
- UIの表示言語

```python
@property  
def TRANSPARENCY(self) -> int
```
- ウィンドウの透明度（0-100）

```python
@property
def UI_SCALING(self) -> int
```
- UIのスケーリング（50-200%）

```python
@property
def FONT_FAMILY(self) -> str
```
- 使用フォントファミリー

### 翻訳設定

```python
@property
def ENABLE_TRANSLATION(self) -> bool
```
- 翻訳機能の有効・無効

```python
@property
def SELECTED_TRANSLATION_ENGINES(self) -> Dict[str, str]
```
- 選択されている翻訳エンジン

```python
@property
def SELECTED_YOUR_LANGUAGES(self) -> Dict[str, Dict[str, Any]]
```
- 送信言語設定

```python
@property
def SELECTED_TARGET_LANGUAGES(self) -> Dict[str, Dict[str, Any]]
```
- 受信言語設定

### 音声認識設定

```python
@property
def ENABLE_TRANSCRIPTION_SEND(self) -> bool
```
- 送信音声認識の有効・無効

```python
@property
def SELECTED_TRANSCRIPTION_ENGINE(self) -> str
```
- 音声認識エンジン

```python
@property
def SELECTED_MIC_DEVICE(self) -> str
```
- 選択されたマイクデバイス

```python
@property
def MIC_THRESHOLD(self) -> int
```
- マイク音声しきい値

```python
@property
def MIC_RECORD_TIMEOUT(self) -> int
```
- マイク録音タイムアウト（秒）

### VR設定

```python
@property
def OVERLAY_SMALL_LOG(self) -> bool
```
- 小型ログオーバーレイの有効・無効

```python
@property
def OVERLAY_SMALL_LOG_SETTINGS(self) -> Dict[str, Any]
```
- 小型オーバーレイの詳細設定

```python
@property
def OVERLAY_LARGE_LOG_SETTINGS(self) -> Dict[str, Any]
```
- 大型オーバーレイの詳細設定

### 通信設定

```python
@property
def OSC_IP_ADDRESS(self) -> str
```
- OSC通信IPアドレス

```python
@property
def OSC_PORT(self) -> int
```
- OSC通信ポート

```python
@property
def WEBSOCKET_HOST(self) -> str
```
- WebSocketサーバーホスト

```python
@property
def WEBSOCKET_PORT(self) -> int
```
- WebSocketサーバーポート

### 計算デバイス設定

```python
@property
def SELECTED_TRANSLATION_COMPUTE_DEVICE(self) -> Dict[str, Any]
```
- 翻訳用計算デバイス

```python
@property
def SELECTED_TRANSCRIPTION_COMPUTE_DEVICE(self) -> Dict[str, Any]
```
- 音声認識用計算デバイス

## 主要メソッド

### 設定保存

```python
saveConfig(key: str, value: Any, immediate_save: bool = False) -> None
```
- 設定値の保存（デバウンス付き）
- immediate_save=Trueで即座保存

```python
saveConfigToFile() -> None
```
- 設定ファイルへの直接保存

### 初期化・設定読み込み

```python
init_config() -> None
```
- 設定の初期化
- デフォルト値の設定

```python
load_config() -> None
```
- 設定ファイルからの読み込み
- 存在しない場合はデフォルト設定を作成

## デコレータ機能

### @json_serializable
```python
@json_serializable("setting_name")
@property
def SETTING_NAME(self) -> Any:
```
- 設定のJSONシリアライゼーション対象指定
- 自動的にconfig.jsonに保存される設定を定義

## 使用方法

### 基本的な使い方

```python
from config import config

# 設定値の取得
version = config.VERSION
ui_language = config.UI_LANGUAGE
translation_enabled = config.ENABLE_TRANSLATION

# 設定値の変更
config.UI_LANGUAGE = "ja"
config.TRANSPARENCY = 80
config.MIC_THRESHOLD = 1500
```

### 複雑な設定の変更

```python
# 翻訳エンジンの設定
engines = config.SELECTED_TRANSLATION_ENGINES
engines["1"] = "DeepL"
config.SELECTED_TRANSLATION_ENGINES = engines

# オーバーレイ設定の変更
overlay_settings = config.OVERLAY_SMALL_LOG_SETTINGS
overlay_settings["x_pos"] = 0.5
overlay_settings["opacity"] = 0.8
config.OVERLAY_SMALL_LOG_SETTINGS = overlay_settings
```

### 即座保存

```python
# 重要な設定変更時の即座保存
config.saveConfig("ENABLE_TRANSLATION", True, immediate_save=True)
```

## 設定ファイル形式

設定は`config.json`ファイルにJSON形式で保存されます：

```json
{
    "UI_LANGUAGE": "ja",
    "TRANSPARENCY": 85,
    "UI_SCALING": 100,
    "ENABLE_TRANSLATION": true,
    "SELECTED_TRANSLATION_ENGINES": {
        "1": "DeepL",
        "2": "Google",
        "3": "CTranslate2"
    },
    "OVERLAY_SMALL_LOG_SETTINGS": {
        "x_pos": 0.0,
        "y_pos": -0.4,
        "z_pos": 1.0,
        "opacity": 1.0,
        "ui_scaling": 1.0,
        "display_duration": 5,
        "fadeout_duration": 1
    }
}
```

## デフォルト設定

### UI設定
- UI言語: "en"（英語）
- 透明度: 85%
- UIスケーリング: 100%
- フォント: "Noto Sans JP"

### 翻訳設定
- 翻訳機能: 無効
- デフォルトエンジン: "Google"
- 送信言語: English（US）
- 受信言語: 日本語

### 音声認識設定
- 送信音声認識: 無効
- 受信音声認識: 無効
- 音声認識エンジン: "Google"
- マイクしきい値: 300

### VR設定
- 小型オーバーレイ: 無効
- 大型オーバーレイ: 無効
- オーバーレイ位置: HMD正面

### 通信設定
- OSC IP: "127.0.0.1"
- OSC ポート: 9000
- WebSocket ホスト: "127.0.0.1"
- WebSocket ポート: 8765

## 依存関係

### 必須依存関係
- `json`: 設定ファイルのシリアライゼーション
- `threading`: デバウンス機能
- `typing`: 型注釈

### オプション依存関係
- `device_manager`: デバイス情報取得
- `torch`: CUDA計算デバイス情報
- 各種モデルモジュール: 言語・エンジン情報

## エラーハンドリング

- 設定ファイル読み込みエラーの適切な処理
- 不正な設定値の検証・補正
- オプション依存関係の欠如に対するフォールバック
- ファイル書き込みエラーの処理

## パフォーマンス特性

### デバウンス機能
- 設定変更から2秒後に自動保存
- 連続する変更の統合
- I/O負荷の軽減

### 遅延初期化
- 重い依存関係の遅延読み込み
- インポート時間の短縮

### メモリ効率
- 設定データのシングルトン管理
- 不要な複製の防止

## 注意事項

- 設定変更は即座にメモリに反映される
- ファイル保存はデバウンス機能により遅延される
- 重要な設定はimmediate_save=Trueを使用
- オプション依存関係の欠如時はデフォルト値を使用
- 不正な設定値は自動的に補正される
- 設定ファイルが破損した場合は新規作成される

## セキュリティ考慮事項

- 設定ファイルの適切な権限管理
- 外部入力値の検証
- APIキー等の機密情報の適切な取り扱い
- パスインジェクション攻撃の防止