---

<!-- プレースホルダ的な一般エンドポイントは削除済み。ドキュメントは `mainloop.py` の `mapping` と `run_mapping` に実装されている具体的なエンドポイントのみを列挙しています -->

## API エンドポイント仕様

概要
- このドキュメントは `mainloop.py` の `mapping` と `run_mapping` に定義された全エンドポイントを列挙します。
- すべてのリクエストは標準入力経由で JSON を一行送る形で受信され、標準出力へ JSON 応答を出力します。

共通リクエスト形式
- JSON オブジェクトを 1 行で標準入力に流します。
- フィールド:
  - `endpoint`: エンドポイント文字列 (例: `/get/data/version`)
  - `data`: 任意（多くの GET 系は null、SET 系は新しい値やオブジェクト）

例
```json
{"endpoint":"/get/data/version","data":null}
```

共通レスポンス形式
- mainloop は各リクエストの処理結果を次の形式で標準出力に出します（内部 util の `printResponse` を経由）:

成功例:
```json
{"status":200,"endpoint":"/get/data/version","result":"3.2.2"}
```

エラー例:
```json
{"status":400,"endpoint":"/set/data/osc_ip_address","result":{"message":"Invalid IP address","data":"127.0.0.1"}}
```

ロック状態と再試行
- `mapping` にある各ハンドラは `"status": True|False` を持ちます。
  - False の場合、`handleRequest` は 423 (Locked endpoint) を返し、メインのハンドラはその要求をキューに戻して待機します（遅延再実行のため）。

run イベント
- `controller` は UI 更新などの非同期通知を行うために `run(status, endpoint, payload)` を呼び出します。これらは `run_mapping` にマップされ、外部 UI には `/run/...` 形式のエンドポイントで配信されます。

以下は `controller.py` から抽出した run イベントと、実際に送られるペイロードの具体例です。UI 側はこれらの JSON 形状を期待することで正しく動作します。

`/run/connected_network` (200)
  - payload: true | false

`/run/enable_ai_models` (200)
  - payload: true | false

`/run/mic_host_list` (200)
  - payload: ["Host 1", "Host 2"]

`/run/mic_device_list` (200)
  - payload: ["Microphone (Realtek)", "Headset Microphone"]

`/run/speaker_device_list` (200)
  - payload: ["Speakers (Realtek)", "Headset"]

`/run/initialization_complete` (200)
  - payload: dict mapping endpoint -> current value (constructed from init_mapping)
  - 例: {"/get/data/version":"3.2.2","/get/data/selected_tab_no":0}

`/run/selected_mic_device` (200)
  - payload: {"host": <host>, "device": <device>}

`/run/selected_speaker_device` (200)
  - payload: string (device name)

`/run/error_device` (400)
  - payload: {"message":"No mic device detected","data": null}

`/run/check_mic_volume` (200)
  - payload: numeric energy value (float)

`/run/check_speaker_volume` (200)
  - payload: numeric energy value (float)

`/run/download_progress_ctranslate2_weight` (200)
  - payload: {"weight_type":"m2m100_418m","progress":0.42}

`/run/downloaded_ctranslate2_weight` (200)
  - payload: "m2m100_418m"

`/run/error_ctranslate2_weight` (400)
  - payload: {"message":"CTranslate2 weight download error","data": null}

`/run/download_progress_whisper_weight` (200)
  - payload: {"weight_type":"base","progress":0.78}

`/run/downloaded_whisper_weight` (200)
  - payload: "base"

`/run/error_whisper_weight` (400)
  - payload: {"message":"Whisper weight download error","data": null}

`/run/word_filter` (200)
  - payload: {"message":"Detected by word filter: <matched_text>"}

`/run/error_translation_engine` (400)
  - payload: {"message":"Translation engine limit error","data": null}

`/run/error_translation_mic_vram_overflow` (400)
  - payload: {"message":"VRAM out of memory during translation of mic","data":"<error_message>"}

`/run/error_translation_speaker_vram_overflow` (400)
  - payload: {"message":"VRAM out of memory during translation of speaker","data":"<error_message>"}

`/run/error_translation_chat_vram_overflow` (400)
  - payload: {"message":"VRAM out of memory during translation of chat","data":"<error_message>"}

`/run/enable_translation` (200/400)
  - payload: on OOM: {"message":"Translation disabled due to VRAM overflow","data": false}

`/run/transcription_send_mic_message` (200)
  - payload:
    {
      "original": {"message": "Hello", "transliteration": []},
      "translations": [ {"message":"こんにちは","transliteration":[]}, ... ]
    }

`/run/transcription_receive_speaker_message` (200)
  - payload: same shape as `/run/transcription_send_mic_message`

`/run/software_update_info` (200)
  - payload: e.g. {"has_update": true, "latest_version": "3.3.0"}

`/run/selected_translation_compute_type` (200)
  - payload: string ("auto"|"cpu"|"cuda:0")

`/run/selected_transcription_compute_type` (200)
  - payload: string

`/run/selected_translation_engines` (200)
  - payload: config.SELECTED_TRANSLATION_ENGINES (list/dict per tab)

`/run/translation_engines` (200)
  - payload: ["CTranslate2"]

`/run/initialization_progress` (200)
  - payload: integer (1..4)

`/run/enable_osc_query` (200)
  - payload: {"data": true|false, "disabled_functions": ["vrc_mic_mute_sync"]}


エンドポイント一覧（mapping にある全エンドポイント）

注: 各行の説明では、`method` 的な概念はありません。すべてのエンドポイントは JSON リクエストで同様に呼び出します。`data` の期待値は説明に記載しています。

1) メイン操作

- /set/enable/translation — data: null — 翻訳を有効にします。
  - 成功応答例:
    ```json
    {"status":200, "endpoint":"/set/enable/translation", "result": true}
    ```
  - 失敗例（VRAM OOM を検出して無効化されたケースは run イベントで通知されます）:
    ```json
    {"status":400, "endpoint":"/set/enable/translation", "result":{"message":"Translation disabled due to VRAM overflow","data":false}}
    ```

- /set/disable/translation — data: null — 翻訳を無効にします。
  - 成功応答例:
    ```json
    {"status":200, "endpoint":"/set/disable/translation", "result": false}
    ```

- /set/enable/transcription_send — data: null — マイク転写(送信)を有効化します。
  - 実行はスレッドで開始される場合がある。成功例:
    ```json
    {"status":200, "endpoint":"/set/enable/transcription_send", "result": true}
    ```

- /set/disable/transcription_send — data: null — 停止要求。成功例:
    ```json
    {"status":200, "endpoint":"/set/disable/transcription_send", "result": false}
    ```

- /set/enable/transcription_receive — data: null — スピーカー側の転写を有効化します。
- /set/disable/transcription_receive — data: null — 無効化します。

- /set/enable/foreground — data: null — フォアグラウンド表示を有効化します。
  - 成功例: {"status":200, "endpoint":"/set/enable/foreground", "result": true}

- /get/data/selected_tab_no — data: null — 現在のタブ番号を返します。
  - 例: {"status":200, "endpoint":"/get/data/selected_tab_no", "result": 0}

- /get/data/main_window_sidebar_compact_mode — data: null — サイドバーのコンパクト表示の現在値を返します。
  - 例: {"status":200, "endpoint":"/get/data/main_window_sidebar_compact_mode","result": false}


- /set/data/selected_tab_no — data: int — タブ番号を設定します。
  - リクエスト例: {"endpoint":"/set/data/selected_tab_no","data":1}
  - 成功応答例: {"status":200, "endpoint":"/set/data/selected_tab_no","result":1}

- /get/data/translation_engines — data: null — 利用可能な翻訳エンジン一覧を返します。
  - 例: {"status":200, "endpoint":"/get/data/translation_engines","result":["CTranslate2"]}

- /get/data/selectable_language_list — data: null — 選択可能な言語一覧（言語コード, country 等を含むデータ構造）
  - 例: {"status":200, "endpoint":"/get/data/selectable_language_list","result":[{"language":"English","country":"US"},{"language":"Japanese","country":"JP"}]}

- /get/data/transcription_engines — data: null — 利用可能な転写エンジン一覧
  - 例: {"status":200, "endpoint":"/get/data/transcription_engines","result":["Google","Whisper"]}


- /run/send_message_box — data: {"id": <任意>, "message": "..."}
  - 内部で `Controller.chatMessage` を呼び出します。戻りは変換済メッセージ構造体。
  - リクエスト例:
    ```json
    {"endpoint":"/run/send_message_box","data":{"id":123,"message":"Hello"}}
    ```
  - 成功応答例:
    ```json
    {"status":200,"endpoint":"/run/send_message_box","result":{"id":123,"original":{"message":"Hello","transliteration":[]},"translations":[{"message":"","transliteration":[]}]}}
    ```

- /run/typing_message_box — data: null — OSC でタイピング状態を伝える場合に使用。成功例: {"status":200,...}
- /run/stop_typing_message_box — data: null — 停止。

- /run/send_text_overlay — data: object — オーバーレイに表示するテキストを更新します。例: {"text":"Hello","lang":"English"}
  - 成功応答は送信した data をそのまま返すことが多い。

- /run/swap_your_language_and_target_language — data: null — 選択中の入出力言語を入れ替えます。成功例: {"status":200, ...}


/run/update_software — data: null — 非同期でアップデート処理を開始します。成功応答: {"status":200, "result": true}
/run/update_cuda_software — data: null — CUDA アップデートを開始します。


/set/enable/transcription_receive — data: null — スピーカー側の転写(受信)を有効化
/set/disable/transcription_receive — data: null — 無効化


/set/enable/foreground — data: null — フォアグラウンド表示を有効化
/set/disable/foreground — data: null — 無効化

- /get/data/selected_tab_no — data: null — 現在のタブ番号を返す
- /set/data/selected_tab_no — data: int — タブ番号を設定

- /get/data/translation_engines — data: null — 使える翻訳エンジン一覧を返す

- /get/data/selected_translation_engines — data: null — 各タブで選択されている翻訳エンジン（タブ別辞書）
  - 例: {"status":200, "endpoint":"/get/data/selected_translation_engines","result":{"0":["CTranslate2"],"1":["CTranslate2"]}}

- /get/data/selected_your_languages — data: null — 各タブの入力言語設定
  - 例: {"status":200, "endpoint":"/get/data/selected_your_languages","result":{"0":{"language":"English","enable":true}}}

- /get/data/selected_target_languages — data: null — 各タブの出力言語設定
  - 例: {"status":200, "endpoint":"/get/data/selected_target_languages","result":{"0":{"1":{"language":"Japanese","enable":true}}}}

- /get/data/selected_transcription_engine — data: null — 現在選択されている転写エンジン
  - 例: {"status":200, "endpoint":"/get/data/selected_transcription_engine","result":"Whisper"}

- /run/send_message_box — data: {"id":..., "message": "..."} — チャット送信を実行（chatMessage を内部呼び出し）
- /run/typing_message_box — data: null — タイピング開始通知（OSC 経由で送信される場合あり）
- /run/stop_typing_message_box — data: null — タイピング停止

- /run/send_text_overlay — data: {text settings...} — オーバーレイ用のテキスト表示を更新

- /run/swap_your_language_and_target_language — data: null — 入出力言語を入れ替え

- /run/update_software — data: null — ソフト更新処理をスレッドで開始
- /run/update_cuda_software — data: null — CUDA 関連更新を開始

2) 表示・外観設定
- /get/data/version — data: null — アプリ版を返す
- /get/data/transparency — data: null — 透過率
- /set/data/transparency — data: int — 透過率を設定
- /get/data/ui_scaling — data: null — UI スケール
- /set/data/ui_scaling — data: int
- /get/data/textbox_ui_scaling, /set/data/textbox_ui_scaling
- /get/data/message_box_ratio, /set/data/message_box_ratio
- /get/data/send_message_button_type, /set/data/send_message_button_type
- /get/data/show_resend_button, /set/enable/show_resend_button, /set/disable/show_resend_button
- /get/data/font_family, /set/data/font_family
- /get/data/ui_language, /set/data/ui_language
- /get/data/main_window_geometry, /set/data/main_window_geometry

3) 計算デバイス関連
- /get/data/compute_mode — data: null — compute mode
- /get/data/translation_compute_device_list — data: null — 選択可能な翻訳デバイス一覧
- /get/data/selected_translation_compute_device — data: null
- /set/data/selected_translation_compute_device — data: device descriptor — 選択
- /get/data/transcription_compute_device_list — same as translation
- /get/data/selected_transcription_compute_device, /set/data/selected_transcription_compute_device

4) 翻訳設定
- /get/data/selectable_ctranslate2_weight_type_dict — data: null — 利用可能な ctranslate2 重みの辞書
- /get/data/ctranslate2_weight_type, /set/data/ctranslate2_weight_type
- /get/data/selected_translation_compute_type, /set/data/selected_translation_compute_type
- /run/download_ctranslate2_weight — data: "weight_type" — 指定した重みをダウンロード（非同期可）
- /get/data/deepl_auth_key — data: null — DeepL API キー（存在すれば返却、セキュリティ上の注意あり）
- /set/data/deepl_auth_key — data: "<key>" — DeepL キーを設定（キー検証あり）
- /delete/data/deepl_auth_key — data: null — DeepL キーを削除

- /set/data/selected_translation_engines — data: dict/list — 各タブの翻訳エンジン選択を設定します。
  - 例: {"endpoint":"/set/data/selected_translation_engines","data":{"0":["CTranslate2"]}}

- /set/data/selected_transcription_engine — data: string — 現在の転写エンジンを設定します。
  - 例: {"endpoint":"/set/data/selected_transcription_engine","data":"Whisper"}

- /set/enable/main_window_sidebar_compact_mode — data: null — サイドバーをコンパクト表示に設定
  - 例: {"status":200,"endpoint":"/set/enable/main_window_sidebar_compact_mode","result": true}

- /set/disable/main_window_sidebar_compact_mode — data: null — サイドバーのコンパクト表示を解除
  - 例: {"status":200,"endpoint":"/set/disable/main_window_sidebar_compact_mode","result": false}
- /get/data/convert_message_to_romaji, /set/enable/convert_message_to_romaji, /set/disable/convert_message_to_romaji
- /get/data/convert_message_to_hiragana, /set/enable/convert_message_to_hiragana, /set/disable/convert_message_to_hiragana

5) トランスクリプション / デバイス
- /get/data/mic_host_list, /get/data/mic_device_list, /get/data/speaker_device_list
- /get/data/auto_mic_select, /set/enable/auto_mic_select, /set/disable/auto_mic_select
- /get/data/selected_mic_host, /set/data/selected_mic_host
- /get/data/selected_mic_device, /set/data/selected_mic_device
- /get/data/mic_threshold, /set/data/mic_threshold
- /get/data/mic_automatic_threshold, /set/enable/mic_automatic_threshold, /set/disable/mic_automatic_threshold
- /get/data/mic_record_timeout, /set/data/mic_record_timeout
- /get/data/mic_phrase_timeout, /set/data/mic_phrase_timeout
- /get/data/mic_max_phrases, /set/data/mic_max_phrases
- /get/data/hotkeys, /set/data/hotkeys
- /get/data/plugins_status, /set/data/plugins_status
- /get/data/mic_avg_logprob, /set/data/mic_avg_logprob
- /get/data/mic_no_speech_prob, /set/data/mic_no_speech_prob
- /set/enable/check_mic_threshold, /set/disable/check_mic_threshold
- /get/data/mic_word_filter, /set/data/mic_word_filter

6) スピーカー側設定
- /get/data/auto_speaker_select, /set/enable/auto_speaker_select, /set/disable/auto_speaker_select
- /get/data/selected_speaker_device, /set/data/selected_speaker_device
- /get/data/speaker_threshold, /set/data/speaker_threshold
- /get/data/speaker_automatic_threshold, /set/enable/speaker_automatic_threshold, /set/disable/speaker_automatic_threshold
- /get/data/speaker_record_timeout, /set/data/speaker_record_timeout
- /get/data/speaker_phrase_timeout, /set/data/speaker_phrase_timeout
- /get/data/speaker_max_phrases, /set/data/speaker_max_phrases
- /get/data/speaker_avg_logprob, /set/data/speaker_avg_logprob
- /get/data/speaker_no_speech_prob, /set/data/speaker_no_speech_prob
- /set/enable/check_speaker_threshold, /set/disable/check_speaker_threshold

7) Whisper / トランスクリプション重み
- /get/data/selectable_whisper_weight_type_dict
- /get/data/whisper_weight_type, /set/data/whisper_weight_type
- /get/data/selected_transcription_compute_type, /set/data/selected_transcription_compute_type
- /run/download_whisper_weight — data: "weight_type"

8) VR / オーバーレイ
- /get/data/overlay_small_log, /set/enable/overlay_small_log, /set/disable/overlay_small_log
- /get/data/overlay_small_log_settings, /set/data/overlay_small_log_settings
- /get/data/overlay_large_log, /set/enable/overlay_large_log, /set/disable/overlay_large_log
- /get/data/overlay_large_log_settings, /set/data/overlay_large_log_settings
- /get/data/overlay_show_only_translated_messages, /set/enable/overlay_show_only_translated_messages, /set/disable/overlay_show_only_translated_messages

9) その他設定
- /get/data/send_message_format_parts, /set/data/send_message_format_parts
- /get/data/received_message_format_parts, /set/data/received_message_format_parts
- /get/data/auto_clear_message_box, /set/enable/auto_clear_message_box, /set/disable/auto_clear_message_box
- /get/data/send_only_translated_messages, /set/enable/send_only_translated_messages, /set/disable/send_only_translated_messages
- /get/data/logger_feature, /set/enable/logger_feature, /set/disable/logger_feature
- /run/open_filepath_logs
- /get/data/vrc_mic_mute_sync, /set/enable/vrc_mic_mute_sync, /set/disable/vrc_mic_mute_sync
- /get/data/send_message_to_vrc, /set/enable/send_message_to_vrc, /set/disable/send_message_to_vrc
- /get/data/send_received_message_to_vrc, /set/enable/send_received_message_to_vrc, /set/disable/send_received_message_to_vrc

10) WebSocket
- /get/data/websocket_host, /set/data/websocket_host
- /get/data/websocket_port, /set/data/websocket_port
- /get/data/websocket_server, /set/enable/websocket_server, /set/disable/websocket_server

11) OSC / 高度設定
- /get/data/osc_ip_address, /set/data/osc_ip_address
- /get/data/osc_port, /set/data/osc_port
- /get/data/notification_vrc_sfx, /set/enable/notification_vrc_sfx, /set/disable/notification_vrc_sfx
- /run/open_filepath_config_file
- /run/feed_watchdog

挙動メモ / 注意点
- `data` は受信時に `encodeBase64` が適用される場合があります（バイナリや特殊文字対策）。
- いくつかのエンドポイントは内部的にバックグラウンドスレッドを立ち上げます（ダウンロード・更新処理・transliteration 等）。
- 翻訳・転写関連は VRAM OOM を検知すると自動的に関連機能を無効化し、UI に 400 系の run イベントを送信します。API 消費者はこれらの run イベントを監視する必要があります。

次の作業
- `docs/modules/controller.md` に記載した Controller のメソッド詳細と紐付けて、各エンドポイントごとに具体的な request/response のサンプル（body の構造）を追加します。
### API / メッセージマッピング（詳細）

このアプリは stdin/stdout を通じた 1 行 JSON メッセージで制御します。内部では `mainloop.py` の `mapping` が受信 endpoint を Controller のメソッドに結び付け、`run_mapping` が非同期通知のエンドポイントを定義します。

受信メッセージ（stdin）
```json
{ "endpoint": "/set/data/selected_tab_no", "data": 0 }
```

送信メッセージ（stdout）
- 成功: printResponse が次を出力します。
```json
{ "status": 200, "endpoint": "/get/data/version", "result": "3.2.2" }
```
- エラー:
```json
{ "status": 400, "endpoint": "/set/data/osc_ip_address", "result": {"message":"Invalid IP address","data":"127.0.0.1"} }
```

動作原則
- `/get/data/*` : Controller の getter を呼び、設定やリストを返す。
- `/set/data/*` : Controller の setter を呼び、設定を変更して新値を返す。
- `/run/*` : 非同期アクションや UI ボタンが実行する処理（ダウンロード、更新、送信など）。
- `mapping` の `"status": False` はロック（423 を返し、要求はキューに戻され再試行される）。

表記ルール
- Controller メソッドは `Controller.<method>` の形式で明記。
- `run events` は Controller が UI に通知する `run_mapping` の `/run/...` エンドポイント名を列挙します。

以下は `mainloop.py` の `mapping` に基づいた、主要エンドポイントの詳細（カテゴリ順）。

1) メイン操作（チャット／翻訳／転写）

- Endpoint: `/set/enable/translation`
  - Controller: `Controller.setEnableTranslation`
  - data: null
  - success: {status:200, result: true}
  - error example: {status:400, result:{message:"Translation disabled due to VRAM overflow", data: False}}
  - run events: `/run/enable_translation` を発行して UI に状態を通知する。

- Endpoint: `/set/disable/translation`
  - Controller: `Controller.setDisableTranslation`
  - data: null
  - success: {status:200, result: false}
  - run events: `/run/enable_translation`

- Endpoint: `/set/enable/transcription_send`
  - Controller: `Controller.setEnableTranscriptionSend`
  - data: null
  - success: {status:200, result: true}
  - side-effect: `Controller.startThreadingTranscriptionSendMessage` を呼びバックグラウンドで音声転写を開始する。
  - run events: `/run/enable_transcription_send`

- Endpoint: `/set/disable/transcription_send`
  - Controller: `Controller.setDisableTranscriptionSend`
  - data: null
  - success: {status:200, result: false}

- Endpoint: `/run/send_message_box`
  - Controller: `Controller.sendMessageBox` -> 内部で `Controller.chatMessage`
  - data: {"id": <任意>, "message": "..."}
  - success example: {status:200, result: {"id":123, "original":{...}, "translations":[...]}}
  - run events: 転送先言語や翻訳結果があれば `/run/transcription_send_mic_message` などが発行される。

- Endpoint: `/run/send_text_overlay`
  - Controller: `Controller.sendTextOverlay`
  - data: object (例: {"text":"Hello","lang":"English"})
  - success: echo back the data
  - side-effect: オーバーレイ更新（small/large に応じた出力）

2) 表示 / 外観設定
- Endpoint: `/get/data/version`
  - Controller: `Controller.getVersion`
  - data: null
  - success: {status:200, result: config.VERSION}

- Endpoint: `/get/data/transparency` / `/set/data/transparency`
  - Controller: `Controller.getTransparency` / `Controller.setTransparency`
  - data for set: integer (0-255 等、設定側で検証)
  - success example: {status:200, result: <int>}

（UI スケーリング、textbox スケーリング、font_family, ui_language 等の /get と /set は同様のパターン: Controller の getXXX / setXXX を呼ぶ）

3) 計算デバイス関連
- Endpoint: `/get/data/translation_compute_device_list` -> `Controller.getComputeDeviceList`
  - data: null
  - result: list of device descriptors (構造は `config.SELECTABLE_COMPUTE_DEVICE_LIST` に従う)

- Endpoint: `/set/data/selected_translation_compute_device`
  - Controller: `Controller.setSelectedTranslationComputeDevice`
  - data: device descriptor (例: {"name":"cuda:0","type":"gpu"})
  - side-effects: `model.setChangedTranslatorParameters(True)` が呼ばれ、実行時にモデル再ロードが必要な場合がある。
  - success: {status:200, result: selected_device}

4) 翻訳／重み管理
- Endpoint: `/get/data/selectable_ctranslate2_weight_type_dict`
  - Controller: `Controller.getSelectableCtranslate2WeightTypeDict`
  - result: dict mapping weight_type -> bool

- Endpoint: `/run/download_ctranslate2_weight`
  - Controller: `Controller.downloadCtranslate2Weight`
  - data: "weight_type" (例: "m2m100_418m")
  - behavior: 非同期フラグでスレッド起動可能。進捗は run events `/run/download_progress_ctranslate2_weight` を発行。完了時に `/run/downloaded_ctranslate2_weight`。

- Endpoint: `/set/data/deepl_auth_key`
  - Controller: `Controller.setDeeplAuthKey`
  - data: string (API key)
  - behavior: 内部で `model.authenticationTranslatorDeepLAuthKey` を実行して検証。失敗時は 400 を返す。

5) トランスクリプション / デバイス
- Endpoint: `/get/data/mic_host_list` -> `Controller.getMicHostList`
  - data: null
  - result: dict/list of hosts

- Endpoint: `/set/data/selected_mic_host` -> `Controller.setSelectedMicHost`
  - data: host identifier (string)
  - side-effects: デフォルトデバイスを `model.getMicDefaultDevice()` で選択し、エネルギーチェックや転写スレッドの再起動が発生する場合がある。

- Endpoint: `/set/data/mic_threshold` -> `Controller.setMicThreshold`
  - data: integer
  - validation: 0 <= value <= config.MAX_MIC_THRESHOLD
  - success: {status:200, result: new_value}  error: 400 with message and old value

6) スピーカー関連（受信）
- Endpoint: `/set/data/selected_speaker_device` -> `Controller.setSelectedSpeakerDevice`
  - data: device descriptor
  - side-effects: スピーカー転写スレッド（ENABLE_CHECK_ENERGY_RECEIVE）を再起動する可能性あり

7) Whisper / トランスクリプション重み
- Endpoint: `/run/download_whisper_weight`
  - Controller: `Controller.downloadWhisperWeight`
  - data: "weight_type"
  - run events: `/run/download_progress_whisper_weight`, `/run/downloaded_whisper_weight`

8) オーバーレイ / VR
- Endpoint: `/set/enable/overlay_small_log` -> `Controller.setEnableOverlaySmallLog`
  - side-effect: `model.startOverlay()` を呼び、`model.updateOverlaySmallLog` で描画が更新される

9) WebSocket / OSC / Watchdog
- Endpoint: `/set/data/websocket_host` -> `Controller.setWebSocketHost`
  - validation: IP 形式チェック (`isValidIpAddress`)
  - if WebSocket server running: attempts to restart server on new host/port (checks availability via `isAvailableWebSocketServer`)

- Endpoint: `/set/data/osc_ip_address` -> `Controller.setOscIpAddress`
  - validation: IP 形式。失敗時は 400 を返す。

- Endpoint: `/run/feed_watchdog` -> `Controller.feedWatchdog`
  - Controller: `Controller.feedWatchdog` ➜ `model.feedWatchdog()`

共通的な失敗モード（クライアント実装者向けメモ）
- 無効なパラメータ: 400 と {message,data} を返す。
- ロック: 423 (Locked endpoint) — UI 側はリトライまたはキュー内での再試行を待つ。
- 内部エラー: 500 とエラーメッセージ（詳細はログ）を返す。
- VRAM OOM / モデルエラー: Controller は `model.detectVRAMError` を使い、必要に応じて機能無効化と run イベントで通知する。

付録: すぐ使える呼び出し例
- バージョン取得
```json
{ "endpoint": "/get/data/version", "data": null }
```

- タブ切替
```json
{ "endpoint": "/set/data/selected_tab_no", "data": 1 }
```

- メッセージ送信（チャット）
```json
{ "endpoint": "/run/send_message_box", "data": {"id": 555, "message": "Hello world"} }
```

次の作業
- ① `docs/modules/controller.md` の各メソッドとこの `docs/api.md` を突き合わせ、未記載の `run_mapping` イベントのペイロード例を追加します。
- ② 軽い品質ゲート（README と runtime 注意の草案作成）を実行します。

## エンドポイント別 JSON スキーマ（補完）

このセクションでは `mainloop.py` の `mapping` に定義された全エンドポイントをパターンごとに整理し、クライアントが送信すべき `request` と期待される `response` の JSON スキーマを明示します。多数のエンドポイントは共通パターンに従うため、パターン定義と代表例でほとんどのケースをカバーしています。

共通ルール
- リクエストは必ず 1 行 JSON: {"endpoint": "<path>", "data": <any|null>}。
- レスポンスは {"status": <int>, "endpoint": "<path>", "result": <any>} の形式（内部の `printResponse` により出力）。

1) /get/data/* パターン（読み取り）
- request.data: null
- response.result: 直ちに返せる JSON 値（数値／文字列／配列／辞書）
- schema（JSON Schema 風の簡易表記）:

  request:
  {
    "endpoint": "/get/data/<name>",
    "data": null
  }

  response:
  {
    "status": 200,
    "endpoint": "/get/data/<name>",
    "result": <Any>
  }

  代表例:
  - `/get/data/version` → result: string
    {"status":200,"endpoint":"/get/data/version","result":"3.2.2"}
  - `/get/data/mic_device_list` → result: ["Device 1", "Device 2"]

2) /set/data/* パターン（書き込み）
- request.data: セッタが期待する型（下に代表的な型を列挙）
- response.result: 新しい値または検証済の値（成功時）
- error: バリデーション失敗時は status 400 と {message,data}

  共通 request/response:

  request:
  {
    "endpoint": "/set/data/<name>",
    "data": <value>
  }

  response (success):
  {
    "status":200,
    "endpoint":"/set/data/<name>",
    "result": <new_value>
  }

  response (validation error):
  {
    "status":400,
    "endpoint":"/set/data/<name>",
    "result": {"message": "<reason>", "data": <current_value>} 
  }

  代表的リクエスト型一覧（多くはこの型いずれか）:
  - int: `/set/data/selected_tab_no`, `/set/data/transparency`, `/set/data/mic_threshold` など
  - string: `/set/data/selected_mic_host`, `/set/data/selected_speaker_device`, `/set/data/deepl_auth_key` など
  - dict/object: `/set/data/selected_your_languages`, `/set/data/selected_target_languages`, `/set/data/send_message_format_parts` など
  - list: `/set/data/mic_word_filter` など

3) フラグ切替（enable / disable）

- 概要: 機能の有効化／無効化を行うエンドポイント群は、実装で定義された具体的なエンドポイント名（例: `/set/enable/translation`, `/set/disable/translation`, `/set/enable/foreground` など）で提供されています。本ドキュメントでは umbrella 的な汎用トークン（`/set/enable` や `/set/disable` 単体）は記載せず、実際に実装で定義されている concrete エンドポイントのみを列挙しています。

- 振る舞いの要点:
  - リクエストの `data` は通常 `null` です。
  - 成功応答は多くの場合 boolean を返します（例: `{ "status":200, "endpoint":"/set/enable/foreground", "result": true }`）。
  - 条件により有効化/無効化ができない場合は 400 を返し、`{ "message": "...", "data": <current_value> }` の形で詳細が返されます。

具体的なフラグ切替エンドポイントはドキュメント本文の各該当箇所で個別に列挙しています（例: `/set/enable/translation`, `/set/disable/translation`, `/set/enable/transcription_send`, `/set/disable/transcription_send`, `/set/enable/main_window_sidebar_compact_mode`, など）。

4) /run/*（アクション・実行系）
- request.data: アクションに依存（例: `/run/send_message_box` は {id, message}）
- response.result: 多くは action の結果（True/False, object）を返す
- 非同期で UI 更新を行う場合は `Controller.run(...)` により `/run/...` 形式の通知が stdout に出力される

  代表例:
  - `/run/send_message_box`
    request.data: {"id": <any>, "message": "<string>"}
    response.result: {
      "id": <any>,
      "original": {"message": "<string>", "transliteration": [<strings>] },
      "translations": [ {"message":"<string>", "transliteration":[...]}, ... ]
    }

  - `/run/download_ctranslate2_weight`
    request.data: "<weight_type>" (string)
    response.result: true
    progress: `/run/download_progress_ctranslate2_weight` -> {"weight_type":"...","progress":0.0..1.0}
    complete: `/run/downloaded_ctranslate2_weight` -> "<weight_type>"

5) WebSocket / OSC / Watchdog 関連
- `/set/data/websocket_host` : request.data:string(host) → response: {status:200, result: host} または 400 (not available)
- `/set/data/osc_ip_address` : request.data:string(ip) → validation via `isValidIpAddress` → 400 on invalid
- `/run/feed_watchdog`: request.data:null → response: {status:200,result:true}

6) エラー応答の標準形
- Validation / domain error : status 400, result: {"message": "<説明>", "data": <current_or_invalid_value>}
- Locked endpoint: status 423, result: "Locked endpoint"（mainloop が再試行のためキューに戻す）
- Internal error: status 500, result: "<exception string>"

7) run events（UI 更新通知）- 参考（主要イベントのみ再掲）
- `/run/connected_network` : bool
- `/run/enable_ai_models` : bool
- `/run/initialization_progress` : int (1..4)
 - `/run/transcription_send_mic_message` / `/run/transcription_receive_speaker_message` : オブジェクト（original/translations, see above）

追加の run イベント（ランタイム検証で未記載と判定されたため追記）:

- `/run/enable_transcription_receive` : bool
  - 説明: スピーカー側転写（transcription receive）の有効/無効を UI に通知します。

- `/run/transcription_send_mic_message` : object
  - payload: 同 `/run/transcription_send_mic_message` の構造（original + translations）
  - 説明: マイク側で転写結果が生成され、UI に送信するための通知です。

- `/run/transcription_receive_speaker_message` : object
  - payload: 同 `/run/transcription_receive_speaker_message` の構造
  - 説明: スピーカー側で転写結果が生成されたときに発行されます。

- `/run/error_transcription_mic_vram_overflow` : object (400)
  - payload: {"message": "VRAM out of memory during mic transcription", "data": "<error message>"}
  - 説明: マイク転写中に VRAM OOM が発生した際に通知します。

- `/run/error_transcription_speaker_vram_overflow` : object (400)
  - payload: {"message": "VRAM out of memory during speaker transcription", "data": "<error message>"}
  - 説明: スピーカー転写中に VRAM OOM が発生した際に通知します。

補遺: 全エンドポイント一覧と期待型の速見表
- `/get/data/*` : data=null -> result: primitive|array|object
- `/set/data/*` : data: 型指定 (int|string|dict|list) -> result: new value or validation error
- `/set/enable/*` `/set/disable/*` : data=null -> result: bool
- `/run/*` : data: action-specific -> result: action result object / bool

ファイルの更新履歴
- このドキュメントは `mainloop.py` の `mapping` と `controller.py` の `run_mapping` を参照して作成しました。将来的にエンドポイントを追加した場合は同じ箇所を参照して本ドキュメントを更新してください。

----

完了: エンドポイント別スキーマの補完を行いました。次は軽い品質ゲート（lint/typecheck）の実行を提案します。

