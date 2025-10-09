# Run events payloads

このファイルは `controller.py` 内で `self.run(status, run_mapping["key"], payload)` として発行される全ての run イベントの鍵と、実際に渡されるペイロードの具体例を列挙します。

---

## 抽出済み run イベント一覧（正規化済み）

以下は controller.py の self.run 呼び出しを解析して抽出した run イベントです。名称は `mainloop.py` の `run_mapping` に合わせて正規化しています。

- connected_network (200)
	- payload: true | false

- enable_ai_models (200)
	- payload: true | false

- mic_host_list (200)
	- payload: list[str]

- mic_device_list (200)
	- payload: list[str]

- speaker_device_list (200)
	- payload: list[str]

- initialization_complete (200)
	- payload: dict mapping endpoint -> current value (constructed from init_mapping)

- selected_mic_device (200)
	- payload: {"host": <host>, "device": <device>}

- selected_speaker_device (200)
	- payload: string (device name)

- error_device (400)
	- payload: {"message": <message>, "data": null}

- check_mic_volume (200)
	- payload: numeric energy value (float)

- check_speaker_volume (200)
	- payload: numeric energy value (float)

- download_progress_ctranslate2_weight (200)
	- payload: {"weight_type": <str>, "progress": <float>}

- downloaded_ctranslate2_weight (200)
	- payload: <weight_type:str>

- error_ctranslate2_weight (400)
	- payload: {"message":"CTranslate2 weight download error","data": null}

- download_progress_whisper_weight (200)
	- payload: {"weight_type": <str>, "progress": <float>}

- downloaded_whisper_weight (200)
	- payload: <weight_type:str>

- error_whisper_weight (400)
	- payload: {"message":"Whisper weight download error","data": null}

- word_filter (200)
	- payload: {"message": "Detected by word filter: <matched_text>"}

- error_translation_engine (400)
	- payload: {"message":"Translation engine limit error","data": null}

- error_translation_mic_vram_overflow (400)
	- payload: {"message":"VRAM out of memory during translation of mic","data": <error_message:str>}

- error_translation_speaker_vram_overflow (400)
	- payload: {"message":"VRAM out of memory during translation of speaker","data": <error_message:str>}

- error_translation_chat_vram_overflow (400)
	- payload: {"message":"VRAM out of memory during translation of chat","data": <error_message:str>}

- enable_translation (400 or 200)
	- payload example on OOM: {"message":"Translation disabled due to VRAM overflow","data": false}

- transcription_send_mic_message (200)
	- payload: {
		"original": {"message": <str>, "transliteration": <list|[]>},
		"translations": [ {"message": <str>, "transliteration": <list|[]>}, ... ]
	}

- transcription_receive_speaker_message (200)
	- payload: same shape as transcription_send_mic_message

- software_update_info (200)
	- payload: dict (e.g. {"has_update": true, "latest_version": "3.3.0"})

- selected_translation_compute_type (200)
	- payload: string e.g. "auto" | "cpu" | "cuda:0"

- selected_transcription_compute_type (200)
	- payload: string

- selected_translation_compute_device (200)
	- payload: device descriptor (object) — `config.SELECTED_TRANSLATION_COMPUTE_DEVICE` の現在値。

- selected_translation_engines (200)
	- payload: config.SELECTED_TRANSLATION_ENGINES (list/dict per tab)

- translation_engines (200)
	- payload: list of selectable engines (e.g. ["CTranslate2"]) 

- initialization_progress (200)
	- payload: integer stage (used values in code: 1..4)

- enable_osc_query (200)
	- payload: {"data": true|false, "disabled_functions": [<str>...]}

- enable_transcription_receive (200)
	- payload: boolean (true when transcription receive enabled)

- error_transcription_mic_vram_overflow (400)
	- payload: {"message":"VRAM out of memory during mic transcription","data": <error_message:str>}

- error_transcription_speaker_vram_overflow (400)
	- payload: {"message":"VRAM out of memory during speaker transcription","data": <error_message:str>}

---

注: 上記は controller.py の self.run 呼び出しを解析して作成した "実際に送られる" ペイロード例です。UI 側はこれらの形を期待してコーディングしてください。状況によっては model 層からの戻り値の具象型が変化するため、実装では型チェック/存在チェックを行ってください。

