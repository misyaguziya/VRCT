# config.py ドキュメント

## 概要
`config.py` は、アプリケーションの全設定を一元管理するシングルトンクラス `Config` を提供するモジュール。設定値の読み込み・保存・検証を行い、JSON ファイルへの永続化をデバウンス機能付きで実現する。

## 主要機能
- シングルトンパターンによる設定の一元管理
- JSONファイル (`config.json`) からの設定読み込みと自動保存
- デバウンス機能による書き込み最適化（デフォルト2秒）
- 読み取り専用プロパティと読み書き可能プロパティの明確な分離
- オプショナルモジュールのセーフガードインポート（環境依存の依存関係を安全に処理）
- プロパティセッター内での型チェックとバリデーション
- `@json_serializable` デコレータによる永続化対象プロパティの管理

## アーキテクチャ

### デザインパターン
- **シングルトンパターン**: `__new__` メソッドで単一インスタンスを保証
- **プロパティパターン**: getter/setter による型安全なアクセス制御

### 設定の分類
1. **読み取り専用設定** (Read Only)
   - アプリケーションバージョン、パス、URL、定数など
   - プロパティのみ（setter なし）

2. **ランタイム設定** (Read Write)
   - 機能の有効/無効フラグ
   - 実行時の状態管理
   - JSON保存されない一時的な設定

3. **永続化設定** (Save Json Data)
   - ユーザー設定、デバイス選択、UI設定など
   - `@json_serializable` デコレータでマーク
   - `saveConfig()` 経由で自動保存

## 使用方法

### 基本的な使い方

```python
from config import config

# 設定値の取得（読み取り専用）
version = config.VERSION
app_path = config.PATH_LOCAL

# 設定値の取得（読み書き可能）
current_tab = config.SELECTED_TAB_NO
mic_threshold = config.MIC_THRESHOLD

# 設定値の変更（自動保存される）
config.SELECTED_TAB_NO = "2"
config.MIC_THRESHOLD = 500
config.TRANSPARENCY = 80

# 即座に保存する場合
config.MAIN_WINDOW_GEOMETRY = {"x_pos": 100, "y_pos": 200, "width": 900, "height": 700}
# MESSAGE_BOX_RATIO と MAIN_WINDOW_GEOMETRY は immediate_save=True で即座に保存
```

### デバウンス保存の仕組み

```python
# 通常の設定変更: 2秒後に保存
config.UI_LANGUAGE = "ja"
config.FONT_FAMILY = "Arial"  # 前のタイマーがキャンセルされ、新たに2秒のタイマー開始

# 即座保存が必要な設定: デバウンスなし
config.MESSAGE_BOX_RATIO = 15  # 即座にファイル書き込み
```

## 動作環境・依存関係

### 必須依存
- Python 3.10以上（match-case 構文使用）
- `torch`: CUDA利用可否の判定に使用
- `threading`: デバウンスタイマー用

### オプション依存（セーフガード付き）
以下のモジュールはインポートに失敗しても動作する:
- `device_manager`: デバイス管理（マイク/スピーカー）
- `models.translation.translation_languages`: 翻訳言語リスト
- `models.translation.translation_utils`: CTranslate2 重みリスト
- `models.transcription.transcription_languages`: 音声認識言語リスト
- `models.transcription.transcription_whisper`: Whisper モデルリスト

### プロジェクト内依存
- `utils`: エラーロギング、辞書構造検証、計算デバイスリスト取得

## ファイル構成

### 主要クラス: `Config`

#### クラス属性
```python
_instance: Config | None  # シングルトンインスタンス
_config_data: Dict[str, Any]  # JSON保存用データ
_timer: Optional[threading.Timer]  # デバウンスタイマー
_debounce_time: int = 2  # デバウンス時間（秒）
```

#### 主要メソッド

**初期化・保存**
- `__new__(cls)`: シングルトンインスタンス生成・初期化
- `init_config()`: デフォルト値の設定
- `load_config()`: JSONファイルから設定読み込み
- `saveConfig(key, value, immediate_save=False)`: 設定の保存（デバウンス付き）
- `saveConfigToFile()`: JSONファイルへの即座書き込み

**デコレータ**
- `@json_serializable(var_name)`: 永続化対象プロパティのマーク

### 設定プロパティ一覧

#### 読み取り専用設定（23項目）

| プロパティ名 | 型 | 説明 | デフォルト値 |
|------------|----|----|------------|
| `VERSION` | str | アプリケーションバージョン | "3.3.0" |
| `PATH_LOCAL` | str | アプリケーションローカルパス | 実行時決定 |
| `PATH_CONFIG` | str | 設定ファイルパス | `{PATH_LOCAL}/config.json` |
| `PATH_LOGS` | str | ログディレクトリパス | `{PATH_LOCAL}/logs` |
| `GITHUB_URL` | str | GitHub API URL | リポジトリURL |
| `UPDATER_URL` | str | アップデーターAPIの URL | アップデーターURL |
| `BOOTH_URL` | str | Booth 販売ページURL | Booth URL |
| `DOCUMENTS_URL` | str | ドキュメントURL | Notion URL |
| `DEEPL_AUTH_KEY_PAGE_URL` | str | DeepL認証キー取得ページ | DeepL URL |
| `MAX_MIC_THRESHOLD` | int | マイクしきい値の最大値 | 2000 |
| `MAX_SPEAKER_THRESHOLD` | int | スピーカーしきい値の最大値 | 4000 |
| `WATCHDOG_TIMEOUT` | int | Watchdog タイムアウト（秒） | 60 |
| `WATCHDOG_INTERVAL` | int | Watchdog チェック間隔（秒） | 20 |
| `SELECTABLE_TAB_NO_LIST` | List[str] | 選択可能タブ番号 | ["1", "2", "3"] |
| `SELECTED_TAB_TARGET_LANGUAGES_NO_LIST` | List[str] | ターゲット言語タブ番号 | ["1", "2", "3"] |
| `SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_LIST` | List[str] | CTranslate2重みタイプリスト | 動的取得 |
| `SELECTABLE_WHISPER_WEIGHT_TYPE_LIST` | List[str] | Whisper重みタイプリスト | 動的取得 |
| `SELECTABLE_TRANSLATION_ENGINE_LIST` | List[str] | 翻訳エンジンリスト | 動的取得 |
| `SELECTABLE_TRANSCRIPTION_ENGINE_LIST` | List[str] | 音声認識エンジンリスト | 動的取得 |
| `SELECTABLE_UI_LANGUAGE_LIST` | List[str] | UI言語リスト | ["en", "ja", "ko", "zh-Hant", "zh-Hans"] |
| `COMPUTE_MODE` | str | 計算モード | "cuda" or "cpu" |
| `SELECTABLE_COMPUTE_DEVICE_LIST` | List[Dict] | 選択可能な計算デバイスリスト | 動的取得 |
| `SEND_MESSAGE_BUTTON_TYPE_LIST` | List[str] | 送信ボタンタイプリスト | ["show", "hide", "show_and_disable_enter_key"] |

#### ランタイム設定（10項目）

| プロパティ名 | 型 | 説明 | デフォルト値 | JSON保存 |
|------------|----|----|-----------|---------|
| `ENABLE_TRANSLATION` | bool | 翻訳機能有効フラグ | False | なし |
| `ENABLE_TRANSCRIPTION_SEND` | bool | 送信音声認識有効フラグ | False | なし |
| `ENABLE_TRANSCRIPTION_RECEIVE` | bool | 受信音声認識有効フラグ | False | なし |
| `ENABLE_FOREGROUND` | bool | フォアグラウンド有効フラグ | False | なし |
| `ENABLE_CHECK_ENERGY_SEND` | bool | 送信エネルギーチェック有効 | False | なし |
| `ENABLE_CHECK_ENERGY_RECEIVE` | bool | 受信エネルギーチェック有効 | False | なし |
| `SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT` | Dict[str, bool] | CTranslate2重み状態辞書 | {} | なし |
| `SELECTABLE_WHISPER_WEIGHT_TYPE_DICT` | Dict[str, bool] | Whisper重み状態辞書 | {} | なし |
| `SELECTABLE_TRANSLATION_ENGINE_STATUS` | Dict[str, bool] | 翻訳エンジン状態辞書 | {} | なし |
| `SELECTABLE_TRANSCRIPTION_ENGINE_STATUS` | Dict[str, bool] | 音声認識エンジン状態辞書 | {} | なし |

#### 永続化設定（60項目以上）

**メインウィンドウ設定**
- `SELECTED_TAB_NO`: 選択中のタブ番号
- `SELECTED_TRANSLATION_ENGINES`: タブごとの翻訳エンジン選択
- `SELECTED_YOUR_LANGUAGES`: タブごとの入力言語設定
- `SELECTED_TARGET_LANGUAGES`: タブごとのターゲット言語設定
- `SELECTED_TRANSCRIPTION_ENGINE`: 音声認識エンジン
- `CONVERT_MESSAGE_TO_ROMAJI`: ローマ字変換有効フラグ
- `CONVERT_MESSAGE_TO_HIRAGANA`: ひらがな変換有効フラグ
- `MAIN_WINDOW_SIDEBAR_COMPACT_MODE`: サイドバーコンパクトモード
- `SEND_MESSAGE_FORMAT_PARTS`: 送信メッセージフォーマット
- `RECEIVED_MESSAGE_FORMAT_PARTS`: 受信メッセージフォーマット

**UIウィンドウ設定**
- `TRANSPARENCY`: ウィンドウ透明度（0-100）
- `UI_SCALING`: UIスケーリング（%）
- `TEXTBOX_UI_SCALING`: テキストボックススケーリング（%）
- `MESSAGE_BOX_RATIO`: メッセージボックス比率（即座保存）
- `SEND_MESSAGE_BUTTON_TYPE`: 送信ボタンタイプ
- `SHOW_RESEND_BUTTON`: 再送信ボタン表示フラグ
- `FONT_FAMILY`: フォントファミリー
- `UI_LANGUAGE`: UI言語
- `MAIN_WINDOW_GEOMETRY`: ウィンドウ位置・サイズ（即座保存）

**マイク設定**
- `AUTO_MIC_SELECT`: 自動マイク選択
- `SELECTED_MIC_HOST`: 選択されたマイクホスト
- `SELECTED_MIC_DEVICE`: 選択されたマイクデバイス
- `MIC_THRESHOLD`: マイクしきい値
- `MIC_AUTOMATIC_THRESHOLD`: 自動しきい値調整
- `MIC_RECORD_TIMEOUT`: 録音タイムアウト（秒）
- `MIC_PHRASE_TIMEOUT`: フレーズタイムアウト（秒）
- `MIC_MAX_PHRASES`: 最大フレーズ数
- `MIC_WORD_FILTER`: ワードフィルターリスト
- `MIC_AVG_LOGPROB`: 平均対数確率しきい値
- `MIC_NO_SPEECH_PROB`: 無音確率しきい値

**スピーカー設定**
- `AUTO_SPEAKER_SELECT`: 自動スピーカー選択
- `SELECTED_SPEAKER_DEVICE`: 選択されたスピーカーデバイス
- `SPEAKER_THRESHOLD`: スピーカーしきい値
- `SPEAKER_AUTOMATIC_THRESHOLD`: 自動しきい値調整
- `SPEAKER_RECORD_TIMEOUT`: 録音タイムアウト（秒）
- `SPEAKER_PHRASE_TIMEOUT`: フレーズタイムアウト（秒）
- `SPEAKER_MAX_PHRASES`: 最大フレーズ数
- `SPEAKER_AVG_LOGPROB`: 平均対数確率しきい値
- `SPEAKER_NO_SPEECH_PROB`: 無音確率しきい値

**モデル設定**
- `SELECTED_TRANSLATION_COMPUTE_DEVICE`: 翻訳計算デバイス
- `SELECTED_TRANSCRIPTION_COMPUTE_DEVICE`: 音声認識計算デバイス
- `CTRANSLATE2_WEIGHT_TYPE`: CTranslate2重みタイプ
- `SELECTED_TRANSLATION_COMPUTE_TYPE`: 翻訳計算タイプ
- `WHISPER_WEIGHT_TYPE`: Whisper重みタイプ
- `SELECTED_TRANSCRIPTION_COMPUTE_TYPE`: 音声認識計算タイプ

**通信設定**
- `OSC_IP_ADDRESS`: OSC IPアドレス（デフォルト: "127.0.0.1"）
- `OSC_PORT`: OSCポート（デフォルト: 9000）
- `AUTH_KEYS`: 認証キー辞書（DeepL API, Groq API, OpenRouter API等）
- `WEBSOCKET_HOST`: WebSocketホスト
- `WEBSOCKET_PORT`: WebSocketポート
- `WEBSOCKET_SERVER`: WebSocketサーバー有効フラグ（非永続化）

**翻訳エンジン モデル選択**
- `SELECTABLE_GROQ_MODEL_LIST`: 利用可能な Groq モデルリスト（非永続化）
- `SELECTED_GROQ_MODEL`: 選択中の Groq モデル
- `SELECTABLE_OPENROUTER_MODEL_LIST`: 利用可能な OpenRouter モデルリスト（非永続化）
- `SELECTED_OPENROUTER_MODEL`: 選択中の OpenRouter モデル

**オーバーレイ設定**
- `OVERLAY_SMALL_LOG`: 小ログオーバーレイ有効
- `OVERLAY_SMALL_LOG_SETTINGS`: 小ログオーバーレイ設定（位置、回転、表示時間等）
- `OVERLAY_LARGE_LOG`: 大ログオーバーレイ有効
- `OVERLAY_LARGE_LOG_SETTINGS`: 大ログオーバーレイ設定
- `OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES`: 翻訳メッセージのみ表示

**その他設定**
- `HOTKEYS`: ホットキー設定辞書（即座保存）
- `PLUGINS_STATUS`: プラグイン状態リスト（即座保存）
- `USE_EXCLUDE_WORDS`: 除外ワード機能使用フラグ
- `AUTO_CLEAR_MESSAGE_BOX`: メッセージボックス自動クリア
- `SEND_ONLY_TRANSLATED_MESSAGES`: 翻訳メッセージのみ送信
- `SEND_MESSAGE_TO_VRC`: VRChatへメッセージ送信
- `SEND_RECEIVED_MESSAGE_TO_VRC`: 受信メッセージをVRChatへ送信
- `LOGGER_FEATURE`: ロガー機能有効
- `VRC_MIC_MUTE_SYNC`: VRChatマイクミュート同期
- `NOTIFICATION_VRC_SFX`: VRChat通知効果音

## 内部実装の詳細

### デバウンス保存の実装

```python
def saveConfig(self, key: str, value: Any, immediate_save: bool = False) -> None:
    self._config_data[key] = value

    # 既存のタイマーをキャンセル
    if isinstance(self._timer, threading.Timer) and self._timer.is_alive():
        self._timer.cancel()

    if immediate_save:
        self.saveConfigToFile()
    else:
        # 2秒後に保存するタイマーをセット
        self._timer = threading.Timer(self._debounce_time, self.saveConfigToFile)
        self._timer.daemon = True
        self._timer.start()
```

### プロパティのバリデーション例

```python
@SELECTED_TAB_NO.setter
def SELECTED_TAB_NO(self, value):
    if isinstance(value, str):
        if value in self.SELECTABLE_TAB_NO_LIST:
            self._SELECTED_TAB_NO = value
            self.saveConfig(inspect.currentframe().f_code.co_name, value)
```

各setterは以下のパターンを実装:
1. 型チェック (`isinstance`)：**`None` 値は常に許可される** （値をクリアしたい場合への対応）
2. 値の範囲・有効性チェック
3. 内部変数への代入
4. `saveConfig` 呼び出し（永続化対象の場合）

#### 型チェックの詳細（v3.3.0+）

```python
# 型チェック実装：Noneは常に許可
if self.type_ is not None and value is not None and not isinstance(value, self.type_):
    return  # 無視する
```

この変更により、設定値をクリア（None に設定）する用途に対応。例えば認証失敗時に API キーを `None` に設定する場合に有効。

### メッセージフォーマット構造

```python
{
    "message": {
        "prefix": "",  # メッセージ前置文字列
        "suffix": ""   # メッセージ後置文字列
    },
    "separator": "\n",  # メッセージと翻訳の区切り
    "translation": {
        "prefix": "",      # 翻訳前置文字列
        "separator": "\n", # 複数翻訳の区切り
        "suffix": ""       # 翻訳後置文字列
    },
    "translation_first": False  # 翻訳を先に表示するか
}
```

### オーバーレイ設定構造

```python
{
    "x_pos": 0.0,          # X座標
    "y_pos": 0.0,          # Y座標
    "z_pos": 0.0,          # Z座標
    "x_rotation": 0.0,     # X軸回転
    "y_rotation": 0.0,     # Y軸回転
    "z_rotation": 0.0,     # Z軸回転
    "display_duration": 5, # 表示時間（秒）
    "fadeout_duration": 2, # フェードアウト時間（秒）
    "opacity": 1.0,        # 不透明度（0.0-1.0）
    "ui_scaling": 1.0,     # UIスケーリング
    "tracker": "HMD"       # トラッカー ("HMD", "LeftHand", "RightHand")
}
```

## エラーハンドリング

### セーフガードインポート
```python
try:
    from device_manager import device_manager
except Exception:
    device_manager = None  # フォールバック値
```

全ての外部モジュールインポートはtry-exceptでラップされており、インポート失敗時でも `Config` クラスは正常に動作する。

### 初期化エラー
```python
def __new__(cls):
    if cls._instance is None:
        cls._instance = super(Config, cls).__new__(cls)
        try:
            cls._instance.init_config()
        except Exception:
            errorLogging()  # エラーをログに記録
        try:
            cls._instance.load_config()
        except Exception:
            errorLogging()
    return cls._instance
```

初期化とロード処理はそれぞれ独立してエラーハンドリングされる。

### 設定ロード時のエラー
```python
for key, value in self._config_data.items():
    try:
        setattr(self, key, value)
    except Exception:
        errorLogging()  # 個別設定の読み込み失敗は継続
```

JSONから読み込んだ設定のうち、不正な値があっても他の設定の読み込みは継続される。

## パフォーマンス考慮事項

1. **デバウンス保存**: 頻繁な設定変更時にI/Oを削減
2. **遅延初期化**: オプションモジュールは必要時のみロード
3. **シングルトン**: 設定オブジェクトの複製を防止
4. **デーモンスレッド**: タイマースレッドはメインスレッド終了時に自動終了

## セキュリティ考慮事項

1. **認証キー**: `AUTH_KEYS` に格納される外部APIキーは平文でJSON保存される
2. **パス検証**: IP アドレスは `isValidIpAddress` でバリデーション
3. **型安全性**: 全てのセッターで型チェック実施

## テスト推奨事項

### 単体テスト
```python
def test_config_singleton():
    config1 = Config()
    config2 = Config()
    assert config1 is config2

def test_debounce_save():
    config.UI_LANGUAGE = "ja"
    time.sleep(1)
    config.UI_LANGUAGE = "en"
    # 2秒以内の変更は1回のみ保存される
    time.sleep(2.5)
    # ここで保存完了
```

### バリデーションテスト
```python
def test_invalid_tab_no():
    config.SELECTED_TAB_NO = "invalid"  # 無視される
    assert config.SELECTED_TAB_NO != "invalid"
```

### オプション依存のテスト
```python
def test_missing_device_manager():
    # device_manager が None でも動作すること
    assert config.SELECTABLE_COMPUTE_DEVICE_LIST is not None
```

## マイグレーション

### 設定ファイルのバージョンアップ
`load_config()` は存在しないキーを無視し、`init_config()` のデフォルト値を使用する。新しいバージョンでキーが追加された場合:

1. 既存キーはJSONから読み込まれる
2. 新規キーは `init_config()` のデフォルト値が使用される
3. 次回保存時に全てのキーがJSON に書き込まれる

## 制限事項

1. **マルチプロセス**: シングルトンはプロセス単位。マルチプロセス環境では各プロセスが独立したインスタンスを持つ
2. **スレッドセーフティ**: プロパティアクセス自体はスレッドセーフではない（保存タイマーのみスレッド対応）
3. **循環参照**: `device_manager` と `config` 間の循環参照に注意
4. **JSON制限**: JSON にシリアライズ可能な型のみ保存可能

## ライセンス
プロジェクトのルートディレクトリの `LICENSE` ファイルを参照

## 関連ドキュメント
- `controller.md`: Controller クラスの設定使用方法
- `mainloop.md`: メインループでの設定参照
- `仕様書.md`: 全体仕様
- `設計書.md`: システム設計

## 変更履歴

### v3.3.0
- 現行バージョン
- WebSocket サーバー設定追加
- オーバーレイ設定の拡張
