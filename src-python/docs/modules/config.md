# config.py クラス仕様書

目的: アプリケーションの全設定を集中管理するシングルトン `config`（クラス名: `Config`、インスタンス: `config`）。

特徴:
- JSON シリアライズ対象のプロパティには `@json_serializable('KEY_NAME')` デコレータが付いており、`load_config()` / `saveConfig()` によって `config.json` に永続化されます。
- プロパティは「読み取り専用 (Read Only)」と「読み書き (Read/Write)」に分類されます。読み書き可能なプロパティはバリデーション処理とともに setter が用意されています。
- 設定は内部的に `_config_data` に保持され、`saveConfig()` はデバウンス（2秒）でファイルへ書き込みます。即時書き込みオプションも可能です（saveConfig(..., immediate_save=True)）。

## 生成とライフサイクル
- `Config()` はシングルトン（__new__ で単一インスタンスを生成）。
- `init_config()` でデフォルト値を初期化し、その後 `load_config()` が `config.json` を読み込んで既存値を適用します。

## 主要プロパティ一覧（型・デフォルト・説明）

注: 下は `config.py` の初期化ロジックに基づく抜粋です。`json_serializable` が付与されたキーは `config.json` に書き出されます。

- Read only
  - `VERSION` (str) = "3.2.2"
  - `PATH_LOCAL` (str) = フォロー実行ファイルのディレクトリか、ソースの __file__ のディレクトリ
  - `PATH_CONFIG` (str) = PATH_LOCAL/config.json
  - `PATH_LOGS` (str) = PATH_LOCAL/logs
  - `GITHUB_URL`, `UPDATER_URL`, `BOOTH_URL`, `DOCUMENTS_URL`, `DEEPL_AUTH_KEY_PAGE_URL` (str)
  - `MAX_MIC_THRESHOLD` (int) = 2000
  - `MAX_SPEAKER_THRESHOLD` (int) = 4000
  - `WATCHDOG_TIMEOUT` (int) = 60
  - `WATCHDOG_INTERVAL` (int) = 20
  - `SELECTABLE_*` 系: 各種選択肢のリスト/イテレータ（モデルの重みや言語、UI 言語等）。

- Read/Write（主な項目）
  - `SEND_MESSAGE_FORMAT_PARTS` (dict) = デフォルトで message/translation/translation_first 等を含むフォーマット定義。json_serializable キー: 'SEND_MESSAGE_FORMAT_PARTS'
  - `RECEIVED_MESSAGE_FORMAT_PARTS` (dict)
  - `ENABLE_TRANSLATION` (bool) = False
  - `ENABLE_TRANSCRIPTION_SEND` (bool) = False
  - `ENABLE_TRANSCRIPTION_RECEIVE` (bool) = False
  - `ENABLE_FOREGROUND` (bool) = False
  - `ENABLE_CHECK_ENERGY_SEND` (bool) = False
  - `ENABLE_CHECK_ENERGY_RECEIVE` (bool) = False
  - `SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT` (dict) = {<weight_type>: False, ...}
  - `SELECTABLE_WHISPER_WEIGHT_TYPE_DICT` (dict)
  - `SELECTABLE_TRANSLATION_ENGINE_STATUS` (dict)
  - `SELECTABLE_TRANSCRIPTION_ENGINE_STATUS` (dict)
  - `SELECTED_TAB_NO` (str) = "1" (json_serializable: 'SELECTED_TAB_NO')
  - `SELECTED_TRANSLATION_ENGINES` (dict) = tab毎に選択 ('CTranslate2' 等)
  - `SELECTED_YOUR_LANGUAGES`, `SELECTED_TARGET_LANGUAGES` (dict) = 翻訳元/先の選択と有効フラグ
  - `SELECTED_TRANSCRIPTION_ENGINE` (str) = 'Google'
  - `CONVERT_MESSAGE_TO_ROMAJI` / `CONVERT_MESSAGE_TO_HIRAGANA` (bool)
  - UI 設定: `TRANSPARENCY` (int), `UI_SCALING` (int), `TEXTBOX_UI_SCALING` (int), `MESSAGE_BOX_RATIO` (int)
  - `SEND_MESSAGE_BUTTON_TYPE` (str) = 'show'（候補は SEND_MESSAGE_BUTTON_TYPE_LIST）
  - `SHOW_RESEND_BUTTON` (bool)
  - `FONT_FAMILY` (str) = 'Yu Gothic UI'
  - `UI_LANGUAGE` (str) = 'en'（候補は SELECTABLE_UI_LANGUAGE_LIST）
  - `MAIN_WINDOW_GEOMETRY` (dict) = {x_pos, y_pos, width, height}
  - マイク/スピーカー関係: `AUTO_MIC_SELECT`, `SELECTED_MIC_HOST`, `SELECTED_MIC_DEVICE`, `MIC_THRESHOLD`, `MIC_AUTOMATIC_THRESHOLD`, `MIC_RECORD_TIMEOUT`, `MIC_PHRASE_TIMEOUT`, `MIC_MAX_PHRASES`, `MIC_WORD_FILTER`, `HOTKEYS` 等
  - `PLUGINS_STATUS` (list)
  - マイク転写確度閾値: `MIC_AVG_LOGPROB`, `MIC_NO_SPEECH_PROB`
  - スピーカー関連（同様の項目）: `AUTO_SPEAKER_SELECT`, `SELECTED_SPEAKER_DEVICE`, `SPEAKER_THRESHOLD`, ...
  - `OSC_IP_ADDRESS` (str) = '127.0.0.1'
  - `OSC_PORT` (int) = 9000
  - `AUTH_KEYS` (dict) = {'DeepL_API': None}
  - `USE_EXCLUDE_WORDS` (bool) = True
  - 計算デバイス選択: `SELECTED_TRANSLATION_COMPUTE_DEVICE` / `SELECTED_TRANSCRIPTION_COMPUTE_DEVICE`（`getComputeDeviceList()` に基づくデバイス辞書）
  - 重み/計算タイプ: `CTRANSLATE2_WEIGHT_TYPE`, `WHISPER_WEIGHT_TYPE`, `SELECTED_TRANSLATION_COMPUTE_TYPE`, `SELECTED_TRANSCRIPTION_COMPUTE_TYPE`
  - オーバーレイ設定: `OVERLAY_SMALL_LOG`, `OVERLAY_SMALL_LOG_SETTINGS`, `OVERLAY_LARGE_LOG`, `OVERLAY_LARGE_LOG_SETTINGS`, `OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES` 等
  - VRC/ログ/WebSocket: `SEND_MESSAGE_TO_VRC`, `SEND_RECEIVED_MESSAGE_TO_VRC`, `LOGGER_FEATURE`, `VRC_MIC_MUTE_SYNC`, `NOTIFICATION_VRC_SFX`, `WEBSOCKET_SERVER`, `WEBSOCKET_HOST`, `WEBSOCKET_PORT`

# config.py — 完全上書きドキュメント

目的: アプリケーションの全設定を集中管理するシングルトン `config`（クラス名: `Config`、インスタンス: `config`）。

特徴:
- JSON シリアライズ対象のプロパティには `@json_serializable('KEY_NAME')` デコレータが付いており、`load_config()` / `saveConfig()` によって `config.json` に永続化されます。
- プロパティは「読み取り専用 (Read Only)」と「読み書き (Read/Write)」に分類されます。読み書き可能なプロパティはバリデーション処理とともに setter が用意されています。
- 設定は内部的に `_config_data` に保持され、`saveConfig()` はデバウンス（2秒）でファイルへ書き込みます。即時書き込みオプションも可能です（saveConfig(..., immediate_save=True)）。

## 生成とライフサイクル
- `Config()` はシングルトン（__new__ で単一インスタンスを生成）。
- `init_config()` でデフォルト値を初期化し、その後 `load_config()` が `config.json` を読み込んで既存値を適用します。

## 主要プロパティ一覧（型・デフォルト・説明）

注: 下は `config.py` の初期化ロジックに基づく抜粋です。`json_serializable` が付与されたキーは `config.json` に書き出されます。

- Read only
  - `VERSION` (str) = "3.2.2"
  - `PATH_LOCAL` (str) = フォロー実行ファイルのディレクトリか、ソースの __file__ のディレクトリ
  - `PATH_CONFIG` (str) = PATH_LOCAL/config.json
  - `PATH_LOGS` (str) = PATH_LOCAL/logs
  - `GITHUB_URL`, `UPDATER_URL`, `BOOTH_URL`, `DOCUMENTS_URL`, `DEEPL_AUTH_KEY_PAGE_URL` (str)
  - `MAX_MIC_THRESHOLD` (int) = 2000
  - `MAX_SPEAKER_THRESHOLD` (int) = 4000
  - `WATCHDOG_TIMEOUT` (int) = 60
  - `WATCHDOG_INTERVAL` (int) = 20
  - `SELECTABLE_*` 系: 各種選択肢のリスト/イテレータ（モデルの重みや言語、UI 言語等）。

- Read/Write（主な項目）
  - `SEND_MESSAGE_FORMAT_PARTS` (dict) = デフォルトで message/translation/translation_first 等を含むフォーマット定義。json_serializable キー: 'SEND_MESSAGE_FORMAT_PARTS'
  - `RECEIVED_MESSAGE_FORMAT_PARTS` (dict)
  - `ENABLE_TRANSLATION` (bool) = False
  - `ENABLE_TRANSCRIPTION_SEND` (bool) = False
  - `ENABLE_TRANSCRIPTION_RECEIVE` (bool) = False
  - `ENABLE_FOREGROUND` (bool) = False
  - `ENABLE_CHECK_ENERGY_SEND` (bool) = False
  - `ENABLE_CHECK_ENERGY_RECEIVE` (bool) = False
  - `SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT` (dict) = {<weight_type>: False, ...}
  - `SELECTABLE_WHISPER_WEIGHT_TYPE_DICT` (dict)
  - `SELECTABLE_TRANSLATION_ENGINE_STATUS` (dict)
  - `SELECTABLE_TRANSCRIPTION_ENGINE_STATUS` (dict)
  - `SELECTED_TAB_NO` (str) = "1" (json_serializable: 'SELECTED_TAB_NO')
  - `SELECTED_TRANSLATION_ENGINES` (dict) = tab毎に選択 ('CTranslate2' 等)
  - `SELECTED_YOUR_LANGUAGES`, `SELECTED_TARGET_LANGUAGES` (dict) = 翻訳元/先の選択と有効フラグ
  - `SELECTED_TRANSCRIPTION_ENGINE` (str) = 'Google'
  - `CONVERT_MESSAGE_TO_ROMAJI` / `CONVERT_MESSAGE_TO_HIRAGANA` (bool)
  - UI 設定: `TRANSPARENCY` (int), `UI_SCALING` (int), `TEXTBOX_UI_SCALING` (int), `MESSAGE_BOX_RATIO` (int)
  - `SEND_MESSAGE_BUTTON_TYPE` (str) = 'show'（候補は SEND_MESSAGE_BUTTON_TYPE_LIST）
  - `SHOW_RESEND_BUTTON` (bool)
  - `FONT_FAMILY` (str) = 'Yu Gothic UI'
  - `UI_LANGUAGE` (str) = 'en'（候補は SELECTABLE_UI_LANGUAGE_LIST）
  - `MAIN_WINDOW_GEOMETRY` (dict) = {x_pos, y_pos, width, height}
  - マイク/スピーカー関係: `AUTO_MIC_SELECT`, `SELECTED_MIC_HOST`, `SELECTED_MIC_DEVICE`, `MIC_THRESHOLD`, `MIC_AUTOMATIC_THRESHOLD`, `MIC_RECORD_TIMEOUT`, `MIC_PHRASE_TIMEOUT`, `MIC_MAX_PHRASES`, `MIC_WORD_FILTER`, `HOTKEYS` 等
  - `PLUGINS_STATUS` (list)
  - マイク転写確度閾値: `MIC_AVG_LOGPROB`, `MIC_NO_SPEECH_PROB`
  - スピーカー関連（同様の項目）: `AUTO_SPEAKER_SELECT`, `SELECTED_SPEAKER_DEVICE`, `SPEAKER_THRESHOLD`, ...
  - `OSC_IP_ADDRESS` (str) = '127.0.0.1'
  - `OSC_PORT` (int) = 9000
  - `AUTH_KEYS` (dict) = {'DeepL_API': None}
  - `USE_EXCLUDE_WORDS` (bool) = True
  - 計算デバイス選択: `SELECTED_TRANSLATION_COMPUTE_DEVICE` / `SELECTED_TRANSCRIPTION_COMPUTE_DEVICE`（`getComputeDeviceList()` に基づくデバイス辞書）
  - 重み/計算タイプ: `CTRANSLATE2_WEIGHT_TYPE`, `WHISPER_WEIGHT_TYPE`, `SELECTED_TRANSLATION_COMPUTE_TYPE`, `SELECTED_TRANSCRIPTION_COMPUTE_TYPE`
  - オーバーレイ設定: `OVERLAY_SMALL_LOG`, `OVERLAY_SMALL_LOG_SETTINGS`, `OVERLAY_LARGE_LOG`, `OVERLAY_LARGE_LOG_SETTINGS`, `OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES` 等
  - VRC/ログ/WebSocket: `SEND_MESSAGE_TO_VRC`, `SEND_RECEIVED_MESSAGE_TO_VRC`, `LOGGER_FEATURE`, `VRC_MIC_MUTE_SYNC`, `NOTIFICATION_VRC_SFX`, `WEBSOCKET_SERVER`, `WEBSOCKET_HOST`, `WEBSOCKET_PORT`

## セッタのバリデーション
- 多くの setter は型チェックと候補値チェック（リストや辞書のキー整合性）を行います。例:
  - `SELECTED_MIC_DEVICE` は `device_manager.getMicDevices()` の一覧に存在する名前であること。
  - `SELECTED_TRANSLATION_COMPUTE_TYPE` は `SELECTED_TRANSLATION_COMPUTE_DEVICE['compute_types']` に含まれる文字列であること。
  - UI 関連の集合は `SELECTABLE_UI_LANGUAGE_LIST` などの一覧に従う。

## 永続化の詳細
- `load_config()` は `config.json` が存在し、かつ中身がある場合に読み込みを試み、ファイル中のキーを `setattr(self, key, value)` して既存の setter を利用して適用します。
- 読み込み後、`json_serializable` 指定された全キーを `_config_data` に書き戻し、ファイルを上書き（常に書く）。

## 使い方の例

以下は `config` を使った典型的なコード例です。

```python
from config import config

# 値の参照
print('App version:', config.VERSION)
print('Current UI language:', config.UI_LANGUAGE)

# 値の更新（setter を通す）
config.UI_LANGUAGE = 'ja'
config.SEND_MESSAGE_TO_VRC = False

# 複雑な dict を設定する例（メッセージフォーマットを上書き）
config.SEND_MESSAGE_FORMAT_PARTS = {
    'message': {'prefix': '[YOU] ', 'suffix': ''},
    'separator': '\n',
    'translation': {'prefix': '[TR] ', 'separator': '\n', 'suffix': ''},
    'translation_first': True,
}

# 即時保存したい場合（即座に config.json を上書き）
config.saveConfig('CUSTOM_SAVE', {'foo': 'bar'}, immediate_save=True)
```

## エッジケース / 注意点
- `load_config()` はファイル値を setter 経由で当てはめるため、ファイルに古いキーや予期しない型があると setter によって無視されることがあります（例: 言語キーが不正の場合）。
- `saveConfig()` はデバウンスされるため、高頻度の設定変更では複数の変更がまとめて書き込まれます。即時書き込みが必要な操作（重要な鍵の更新など）は `immediate_save=True` を使ってください。
- `SELECTABLE_*` 系や `*_DICT` 系は初期化時に外部モジュール（翻訳リソース、whisper_models、device_manager 等）から生成されます。これらが利用できない環境ではデフォルトが空になる可能性があります。

## 推奨改善点（将来的なドキュメント／実装）
- 設定スキーマを JSON Schema で定義し、load 時の検証を明確化すると安全性が向上します。
- 設定変更イベントを発火する仕組み（observer パターン）を導入すると、Controller/Model 側の再初期化処理をより明確に実装できます。

---

このファイルは `config.py` の実装に基づいて自動生成的に作成されたドキュメント（overwrite）です。実装の微細な差分は `config.py` を参照してください。

## 詳細設計

目的: アプリケーションの全設定を保持するシングルトン `config`。

ポイント:
- JSON シリアライズ可能な設定値には `@json_serializable` デコレータが付与され、save 操作でファイルへ書き出される。
- 多数のプロパティが定義され、読み取り専用 (Read Only) と 読み書き (Read/Write) が混在する。
- 設定項目の例:
  - ENABLE_TRANSLATION, ENABLE_TRANSCRIPTION_SEND, ENABLE_TRANSCRIPTION_RECEIVE
  - SELECTED_MIC_HOST, SELECTED_MIC_DEVICE, SELECTED_SPEAKER_DEVICE
  - SELECTED_TRANSLATION_ENGINES, SELECTED_YOUR_LANGUAGES, SELECTED_TARGET_LANGUAGES
  - PATH_LOCAL, PATH_LOGS, VERSION, GITHUB_URL, UPDATER_URL
  - SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT / SELECTABLE_WHISPER_WEIGHT_TYPE_DICT
  - COMPUTE 関連: SELECTABLE_COMPUTE_DEVICE_LIST, SELECTED_TRANSLATION_COMPUTE_DEVICE, SELECTED_TRANSCRIPTION_COMPUTE_DEVICE

設計上の契約:
- 全ての get/set は辞書形で status/result を返す Controller の呼び出しに合わせて変換される。
- 外部から設定を変更した際は必要に応じて Model/Controller による再初期化処理を呼ぶ。

検討事項:
- 現状は設定変更が即時反映されるが、一部操作は再初期化（モデルロード、デバイス再取得）を要求するため Controller 側で連携している。
