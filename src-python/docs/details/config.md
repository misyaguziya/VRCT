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

## 最近の更新 (2025-10-20)

### LMStudio / Ollama ローカル LLM 設定プロパティ追加

- `LMSTUDIO_URL` / `SELECTABLE_LMSTUDIO_MODEL_LIST` / `SELECTED_LMSTUDIO_MODEL`
- `SELECTABLE_OLLAMA_MODEL_LIST` / `SELECTED_OLLAMA_MODEL`

ローカル推論エンジン接続用 URL と動的モデルリスト取得・選択プロパティを追加。認証は不要で接続テスト後自動でモデルリストを更新。

### モデル選択プロパティ名称統一

Plamo / Gemini / OpenAI の選択モデルを `PLAMO_MODEL` / `GEMINI_MODEL` / `OPENAI_MODEL` から `SELECTED_PLAMO_MODEL` / `SELECTED_GEMINI_MODEL` / `SELECTED_OPENAI_MODEL` へ統一。設定 JSON の保存キーも `SELECTED_*` に変更し UI との整合性を確保。

### CTranslate2 言語マッピング構造変更対応

`translation_lang` 内の CTranslate2 言語辞書が `translation_lang["CTranslate2"][weight_type]["source"|"target"]` へネスト化。`CTRANSLATE2_WEIGHT_TYPE` プロパティがアクセスのキーとなるため、重みタイプ変更時に翻訳エンジン再初期化が必要。

### YAML 言語外部定義導入

`loadTranslationLanguages()` を初期化時に呼び出し、`models/translation/languages/languages.yml` を読み込んで既存マッピングへマージ。失敗時は空辞書フォールバック。動的言語追加がコード改修無しで可能になったため設定初期化の失敗ログ確認が重要。

### OpenAI モデルリスト自動更新

`setOpenAIAuthKey()` 成功後に `SELECTABLE_OPENAI_MODEL_LIST` を取得し未選択の場合は先頭を自動選択。Gemini / Plamo / LMStudio / Ollama も同様に認証/接続確立時にリスト更新と未選択モデル補完。

### フォント設定のパッケージ対応

`overlay_image.py` で PyInstaller ビルド環境（`_internal/fonts/`）検出を追加。開発環境とバンドル後でフォント探索パスが異なるため、`FONT_FAMILY` はファイル名基準のまま変更無し。

### 依存関係追加

- `PyYAML`: 言語マッピング YAML 読み込み
- `google-genai`: Gemini 連携
- `grpcio`: OpenAI 連携（ストリーミング等）

### VRAM エラー時の自動フォールバック

翻訳有効化や翻訳実行時に VRAM 不足検出で `ENABLE_TRANSLATION` を False にし CTranslate2 へ強制切替。設定値は保持されるが UI には無効化状態を通知。再度有効化要求時に重いモデル再初期化を試行。

### テスト関連

包括的翻訳ペアテストにより `SELECTED_*` モデルと言語マッピング組合せを大量実行。設定値の変更頻度増加に伴いデバウンス 2 秒でファイル書き込み負荷を抑制。

### 影響まとめ

| 項目 | 内容 |
|------|------|
| ローカルLLM | LMStudio / Ollama の導入でオフライン翻訳拡張 |
| プロパティ統一 | SELECTED_* 命名で一貫性・ドキュメント整備性向上 |
| 言語ネスト化 | CTranslate2 重みタイプ切替処理の再初期化必要性増加 |
| YAML外部化 | 言語追加が設定初期化のみで反映可能 |
| モデルリスト自動更新 | 認証後の選択ミス防止・初回 UX 改善 |
| フォント探索 | PyInstaller ビルド後でも同一コードで動作 |
| 依存追加 | 新機能対応で環境構築ステップ増加 |
| VRAM検知 | 安全停止と軽量エンジン切替で安定性向上 |
| テスト増強 | 大量ペア検証で言語/モデル設定の信頼性向上 |
