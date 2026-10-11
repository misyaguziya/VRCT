# Rust バックエンド設計 付録 A: IPC エンドポイント一覧（2026-10-11）

`src-python/mainloop.py` の `mapping` / `run_mapping` から機械的に作った一覧。Rust 版はこの名前・入出力をそのまま保つ（契約テストの対象）。
「初期化中」が ✗ のものは、初期化が終わるまで 423 を返して再キューされる（`status: False`）。

要求エンドポイント 330 件（`/get/data` 145、`/set/data` 88、`/set/enable` 33、`/set/disable` 33、`/delete/data` 11、`/run/*` 20）。push 用の名前 81 件。領域の分け方はエンドポイント名による機械的なもの。

## 音声認識・マイク/スピーカー（98 件）

| エンドポイント | 初期化中 | Python のハンドラ |
|---|---|---|
| `/set/enable/transcription_send` | ✗ | `setEnableTranscriptionSend` |
| `/set/disable/transcription_send` | ✗ | `setDisableTranscriptionSend` |
| `/set/enable/transcription_receive` | ✗ | `setEnableTranscriptionReceive` |
| `/set/disable/transcription_receive` | ✗ | `setDisableTranscriptionReceive` |
| `/get/data/selectable_transcription_engines` | ✗ | `getTranscriptionEngines` |
| `/get/data/selected_transcription_engine` | ✗ | `getSelectedTranscriptionEngine` |
| `/set/data/selected_transcription_engine` | ✗ | `setSelectedTranscriptionEngine` |
| `/get/data/groq_whisper_auth_key` | ○ | `getGroqWhisperAuthKey` |
| `/set/data/groq_whisper_auth_key` | ○ | `setGroqWhisperAuthKey` |
| `/delete/data/groq_whisper_auth_key` | ○ | `delGroqWhisperAuthKey` |
| `/get/data/selectable_groq_whisper_model_list` | ○ | `getGroqWhisperModelList` |
| `/get/data/selected_groq_whisper_model` | ○ | `getGroqWhisperModel` |
| `/set/data/selected_groq_whisper_model` | ○ | `setGroqWhisperModel` |
| `/get/data/openai_whisper_auth_key` | ○ | `getOpenAIWhisperAuthKey` |
| `/set/data/openai_whisper_auth_key` | ○ | `setOpenAIWhisperAuthKey` |
| `/delete/data/openai_whisper_auth_key` | ○ | `delOpenAIWhisperAuthKey` |
| `/get/data/selectable_openai_whisper_model_list` | ○ | `getOpenAIWhisperModelList` |
| `/get/data/selected_openai_whisper_model` | ○ | `getOpenAIWhisperModel` |
| `/set/data/selected_openai_whisper_model` | ○ | `setOpenAIWhisperModel` |
| `/get/data/custom_whisper_auth_key` | ○ | `getCustomWhisperAuthKey` |
| `/set/data/custom_whisper_auth_key` | ○ | `setCustomWhisperAuthKey` |
| `/delete/data/custom_whisper_auth_key` | ○ | `delCustomWhisperAuthKey` |
| `/get/data/custom_whisper_url` | ○ | `getCustomWhisperURL` |
| `/set/data/custom_whisper_url` | ○ | `setCustomWhisperURL` |
| `/get/data/selectable_custom_whisper_model_list` | ○ | `getCustomWhisperModelList` |
| `/get/data/selected_custom_whisper_model` | ○ | `getCustomWhisperModel` |
| `/set/data/selected_custom_whisper_model` | ○ | `setCustomWhisperModel` |
| `/get/data/deepgram_auth_key` | ○ | `getDeepgramAuthKey` |
| `/set/data/deepgram_auth_key` | ○ | `setDeepgramAuthKey` |
| `/delete/data/deepgram_auth_key` | ○ | `delDeepgramAuthKey` |
| `/get/data/selectable_deepgram_model_list` | ○ | `getDeepgramModelList` |
| `/get/data/selected_deepgram_model` | ○ | `getDeepgramModel` |
| `/set/data/selected_deepgram_model` | ○ | `setDeepgramModel` |
| `/get/data/selectable_transcription_compute_device_list` | ○ | `getComputeDeviceList` |
| `/get/data/selected_transcription_compute_device` | ○ | `getSelectedTranscriptionComputeDevice` |
| `/set/data/selected_transcription_compute_device` | ○ | `setSelectedTranscriptionComputeDevice` |
| `/get/data/selectable_mic_host_list` | ○ | `getMicHostList` |
| `/get/data/selectable_mic_device_list` | ○ | `getMicDeviceList` |
| `/get/data/selectable_speaker_device_list` | ○ | `getSpeakerDeviceList` |
| `/get/data/auto_mic_select` | ○ | `getAutoMicSelect` |
| `/set/enable/auto_mic_select` | ○ | `setEnableAutoMicSelect` |
| `/set/disable/auto_mic_select` | ○ | `setDisableAutoMicSelect` |
| `/get/data/selected_mic_host` | ○ | `getSelectedMicHost` |
| `/set/data/selected_mic_host` | ○ | `setSelectedMicHost` |
| `/get/data/selected_mic_device` | ○ | `getSelectedMicDevice` |
| `/set/data/selected_mic_device` | ○ | `setSelectedMicDevice` |
| `/get/data/mic_threshold` | ○ | `getMicThreshold` |
| `/set/data/mic_threshold` | ○ | `setMicThreshold` |
| `/get/data/mic_automatic_threshold` | ○ | `getMicAutomaticThreshold` |
| `/set/enable/mic_automatic_threshold` | ○ | `setEnableMicAutomaticThreshold` |
| `/set/disable/mic_automatic_threshold` | ○ | `setDisableMicAutomaticThreshold` |
| `/get/data/mic_record_timeout` | ○ | `getMicRecordTimeout` |
| `/set/data/mic_record_timeout` | ○ | `setMicRecordTimeout` |
| `/get/data/mic_phrase_timeout` | ○ | `getMicPhraseTimeout` |
| `/set/data/mic_phrase_timeout` | ○ | `setMicPhraseTimeout` |
| `/get/data/mic_max_phrases` | ○ | `getMicMaxPhrases` |
| `/set/data/mic_max_phrases` | ○ | `setMicMaxPhrases` |
| `/get/data/hotkeys` | ○ | `getHotkeys` |
| `/set/data/hotkeys` | ○ | `setHotkeys` |
| `/get/data/mic_avg_logprob` | ○ | `getMicAvgLogprob` |
| `/set/data/mic_avg_logprob` | ○ | `setMicAvgLogprob` |
| `/get/data/mic_no_speech_prob` | ○ | `getMicNoSpeechProb` |
| `/set/data/mic_no_speech_prob` | ○ | `setMicNoSpeechProb` |
| `/set/enable/check_mic_threshold` | ○ | `setEnableCheckMicThreshold` |
| `/set/disable/check_mic_threshold` | ○ | `setDisableCheckMicThreshold` |
| `/get/data/mic_word_filter` | ○ | `getMicWordFilter` |
| `/set/data/mic_word_filter` | ○ | `setMicWordFilter` |
| `/get/data/auto_speaker_select` | ○ | `getAutoSpeakerSelect` |
| `/set/enable/auto_speaker_select` | ○ | `setEnableAutoSpeakerSelect` |
| `/set/disable/auto_speaker_select` | ○ | `setDisableAutoSpeakerSelect` |
| `/get/data/selected_speaker_device` | ○ | `getSelectedSpeakerDevice` |
| `/set/data/selected_speaker_device` | ○ | `setSelectedSpeakerDevice` |
| `/get/data/speaker_threshold` | ○ | `getSpeakerThreshold` |
| `/set/data/speaker_threshold` | ○ | `setSpeakerThreshold` |
| `/get/data/speaker_automatic_threshold` | ○ | `getSpeakerAutomaticThreshold` |
| `/set/enable/speaker_automatic_threshold` | ○ | `setEnableSpeakerAutomaticThreshold` |
| `/set/disable/speaker_automatic_threshold` | ○ | `setDisableSpeakerAutomaticThreshold` |
| `/get/data/speaker_record_timeout` | ○ | `getSpeakerRecordTimeout` |
| `/set/data/speaker_record_timeout` | ○ | `setSpeakerRecordTimeout` |
| `/get/data/speaker_phrase_timeout` | ○ | `getSpeakerPhraseTimeout` |
| `/set/data/speaker_phrase_timeout` | ○ | `setSpeakerPhraseTimeout` |
| `/get/data/speaker_max_phrases` | ○ | `getSpeakerMaxPhrases` |
| `/set/data/speaker_max_phrases` | ○ | `setSpeakerMaxPhrases` |
| `/get/data/speaker_avg_logprob` | ○ | `getSpeakerAvgLogprob` |
| `/set/data/speaker_avg_logprob` | ○ | `setSpeakerAvgLogprob` |
| `/get/data/speaker_no_speech_prob` | ○ | `getSpeakerNoSpeechProb` |
| `/set/data/speaker_no_speech_prob` | ○ | `setSpeakerNoSpeechProb` |
| `/set/enable/check_speaker_threshold` | ○ | `setEnableCheckSpeakerThreshold` |
| `/set/disable/check_speaker_threshold` | ○ | `setDisableCheckSpeakerThreshold` |
| `/get/data/selectable_whisper_weight_type_dict` | ○ | `getSelectableWhisperWeightTypeDict` |
| `/get/data/selected_whisper_weight_type` | ○ | `getWhisperWeightType` |
| `/set/data/selected_whisper_weight_type` | ○ | `setWhisperWeightType` |
| `/get/data/selected_transcription_compute_type` | ○ | `getSelectedTranscriptionComputeType` |
| `/set/data/selected_transcription_compute_type` | ○ | `setSelectedTranscriptionComputeType` |
| `/run/download_whisper_weight` | ○ | `downloadWhisperWeight` |
| `/get/data/vrc_mic_mute_sync` | ○ | `getVrcMicMuteSync` |
| `/set/enable/vrc_mic_mute_sync` | ○ | `setEnableVrcMicMuteSync` |
| `/set/disable/vrc_mic_mute_sync` | ○ | `setDisableVrcMicMuteSync` |

## 翻訳・LLM（78 件）

| エンドポイント | 初期化中 | Python のハンドラ |
|---|---|---|
| `/set/enable/translation` | ✗ | `setEnableTranslation` |
| `/set/disable/translation` | ✗ | `setDisableTranslation` |
| `/get/data/selectable_translation_engines` | ○ | `getTranslationEngines` |
| `/get/data/selectable_language_list` | ○ | `getListLanguageAndCountry` |
| `/get/data/selected_translation_engines` | ✗ | `getSelectedTranslationEngines` |
| `/set/data/selected_translation_engines` | ○ | `setSelectedTranslationEngines` |
| `/get/data/selected_your_languages` | ○ | `getSelectedYourLanguages` |
| `/set/data/selected_your_languages` | ○ | `setSelectedYourLanguages` |
| `/get/data/selected_target_languages` | ○ | `getSelectedTargetLanguages` |
| `/set/data/selected_target_languages` | ○ | `setSelectedTargetLanguages` |
| `/run/swap_your_language_and_target_language` | ○ | `swapYourLanguageAndTargetLanguage` |
| `/get/data/ui_language` | ○ | `getUiLanguage` |
| `/set/data/ui_language` | ○ | `setUiLanguage` |
| `/get/data/selectable_translation_compute_device_list` | ○ | `getComputeDeviceList` |
| `/get/data/selected_translation_compute_device` | ○ | `getSelectedTranslationComputeDevice` |
| `/set/data/selected_translation_compute_device` | ○ | `setSelectedTranslationComputeDevice` |
| `/get/data/selectable_ctranslate2_weight_type_dict` | ○ | `getSelectableCtranslate2WeightTypeDict` |
| `/get/data/selected_ctranslate2_weight_type` | ○ | `getCtranslate2WeightType` |
| `/set/data/selected_ctranslate2_weight_type` | ○ | `setCtranslate2WeightType` |
| `/get/data/selected_translation_compute_type` | ○ | `getSelectedTranslationComputeType` |
| `/set/data/selected_translation_compute_type` | ○ | `setSelectedTranslationComputeType` |
| `/run/download_ctranslate2_weight` | ○ | `downloadCtranslate2Weight` |
| `/get/data/deepl_auth_key` | ✗ | `getDeepLAuthKey` |
| `/set/data/deepl_auth_key` | ✗ | `setDeeplAuthKey` |
| `/delete/data/deepl_auth_key` | ✗ | `delDeeplAuthKey` |
| `/get/data/selectable_plamo_model_list` | ✗ | `getPlamoModelList` |
| `/get/data/selected_plamo_model` | ✗ | `getPlamoModel` |
| `/set/data/selected_plamo_model` | ✗ | `setPlamoModel` |
| `/get/data/plamo_auth_key` | ✗ | `getPlamoAuthKey` |
| `/set/data/plamo_auth_key` | ✗ | `setPlamoAuthKey` |
| `/delete/data/plamo_auth_key` | ✗ | `delPlamoAuthKey` |
| `/get/data/selectable_gemini_model_list` | ○ | `getGeminiModelList` |
| `/get/data/selected_gemini_model` | ○ | `getGeminiModel` |
| `/set/data/selected_gemini_model` | ○ | `setGeminiModel` |
| `/get/data/gemini_auth_key` | ○ | `getGeminiAuthKey` |
| `/set/data/gemini_auth_key` | ○ | `setGeminiAuthKey` |
| `/delete/data/gemini_auth_key` | ○ | `delGeminiAuthKey` |
| `/get/data/selectable_openai_model_list` | ○ | `getOpenAIModelList` |
| `/get/data/selected_openai_model` | ○ | `getOpenAIModel` |
| `/set/data/selected_openai_model` | ○ | `setOpenAIModel` |
| `/get/data/openai_auth_key` | ○ | `getOpenAIAuthKey` |
| `/set/data/openai_auth_key` | ○ | `setOpenAIAuthKey` |
| `/delete/data/openai_auth_key` | ○ | `delOpenAIAuthKey` |
| `/get/data/selectable_groq_model_list` | ○ | `getGroqModelList` |
| `/get/data/selected_groq_model` | ○ | `getGroqModel` |
| `/set/data/selected_groq_model` | ○ | `setGroqModel` |
| `/get/data/groq_auth_key` | ○ | `getGroqAuthKey` |
| `/set/data/groq_auth_key` | ○ | `setGroqAuthKey` |
| `/delete/data/groq_auth_key` | ○ | `delGroqAuthKey` |
| `/get/data/selectable_openrouter_model_list` | ○ | `getOpenRouterModelList` |
| `/get/data/selected_openrouter_model` | ○ | `getOpenRouterModel` |
| `/set/data/selected_openrouter_model` | ○ | `setOpenRouterModel` |
| `/get/data/openrouter_auth_key` | ○ | `getOpenRouterAuthKey` |
| `/set/data/openrouter_auth_key` | ○ | `setOpenRouterAuthKey` |
| `/delete/data/openrouter_auth_key` | ○ | `delOpenRouterAuthKey` |
| `/get/data/connected_lmstudio` | ○ | `getTranslatorLMStudioConnection` |
| `/run/lmstudio_connection` | ○ | `checkTranslatorLMStudioConnection` |
| `/get/data/selectable_lmstudio_model_list` | ○ | `getTranslatorLMStudioModelList` |
| `/get/data/selected_lmstudio_model` | ○ | `getTranslatorLMStudioModel` |
| `/set/data/selected_lmstudio_model` | ○ | `setTranslatorLMStudioModel` |
| `/get/data/lmstudio_url` | ○ | `getTranslatorLMStudioURL` |
| `/set/data/lmstudio_url` | ○ | `setTranslatorLMStudioURL` |
| `/get/data/openai_compatible_auth_key` | ○ | `getOpenAICompatibleAuthKey` |
| `/set/data/openai_compatible_auth_key` | ○ | `setOpenAICompatibleAuthKey` |
| `/delete/data/openai_compatible_auth_key` | ○ | `delOpenAICompatibleAuthKey` |
| `/get/data/openai_compatible_url` | ○ | `getOpenAICompatibleURL` |
| `/set/data/openai_compatible_url` | ○ | `setOpenAICompatibleURL` |
| `/get/data/selectable_openai_compatible_model_list` | ○ | `getOpenAICompatibleModelList` |
| `/get/data/selected_openai_compatible_model` | ○ | `getOpenAICompatibleModel` |
| `/set/data/selected_openai_compatible_model` | ○ | `setOpenAICompatibleModel` |
| `/get/data/connected_ollama` | ○ | `getTranslatorOllamaConnection` |
| `/run/ollama_connection` | ○ | `checkTranslatorOllamaConnection` |
| `/get/data/selectable_ollama_model_list` | ○ | `getTranslatorOllamaModelList` |
| `/get/data/selected_ollama_model` | ○ | `getTranslatorOllamaModel` |
| `/set/data/selected_ollama_model` | ○ | `setTranslatorOllamaModel` |
| `/get/data/selectable_ocr_source_languages` | ○ | `getSelectableOcrSourceLanguages` |
| `/get/data/ocr_source_language` | ○ | `getOcrSourceLanguage` |
| `/set/data/ocr_source_language` | ○ | `setOcrSourceLanguage` |

## 音訳（6 件）

| エンドポイント | 初期化中 | Python のハンドラ |
|---|---|---|
| `/get/data/convert_message_to_romaji` | ○ | `getConvertMessageToRomaji` |
| `/set/enable/convert_message_to_romaji` | ○ | `setEnableConvertMessageToRomaji` |
| `/set/disable/convert_message_to_romaji` | ○ | `setDisableConvertMessageToRomaji` |
| `/get/data/convert_message_to_hiragana` | ○ | `getConvertMessageToHiragana` |
| `/set/enable/convert_message_to_hiragana` | ○ | `setEnableConvertMessageToHiragana` |
| `/set/disable/convert_message_to_hiragana` | ○ | `setDisableConvertMessageToHiragana` |

## VR オーバーレイ（40 件）

| エンドポイント | 初期化中 | Python のハンドラ |
|---|---|---|
| `/run/send_text_overlay` | ○ | `sendTextOverlay` |
| `/get/data/overlay_small_log` | ○ | `getOverlaySmallLog` |
| `/set/enable/overlay_small_log` | ○ | `setEnableOverlaySmallLog` |
| `/set/disable/overlay_small_log` | ○ | `setDisableOverlaySmallLog` |
| `/get/data/overlay_small_log_settings` | ○ | `getOverlaySmallLogSettings` |
| `/run/vr_panel_tooltip` | ✗ | `setVrPanelTooltip` |
| `/run/vr_panel_windows` | ✗ | `setVrPanelWindows` |
| `/run/vr_panel_recall_log` | ✗ | `recallVrPanelLog` |
| `/run/vr_launcher_reset` | ✗ | `resetVrLauncher` |
| `/get/data/overlay_vr_panel_opacity` | ○ | `getOverlayVrPanelOpacity` |
| `/get/data/overlay_vr_panel_anchor` | ○ | `getOverlayVrPanelAnchor` |
| `/get/data/vr_panel_layout` | ○ | `getVrPanelLayout` |
| `/run/vr_panel_layout_rendered` | ○ | `setVrPanelLayoutRendered` |
| `/set/data/overlay_vr_panel_anchor` | ○ | `setOverlayVrPanelAnchor` |
| `/get/data/overlay_vr_panel_locked` | ○ | `getOverlayVrPanelLocked` |
| `/get/data/overlay_vr_panel_font_size` | ○ | `getOverlayVrPanelFontSize` |
| `/get/data/overlay_vr_launcher_hand` | ○ | `getOverlayVrLauncherHand` |
| `/set/data/overlay_vr_launcher_hand` | ○ | `setOverlayVrLauncherHand` |
| `/get/data/overlay_vr_launcher_auto_hide` | ○ | `getOverlayVrLauncherAutoHide` |
| `/set/enable/overlay_vr_launcher_auto_hide` | ○ | `setEnableOverlayVrLauncherAutoHide` |
| `/set/disable/overlay_vr_launcher_auto_hide` | ○ | `setDisableOverlayVrLauncherAutoHide` |
| `/get/data/overlay_vr_tooltip` | ○ | `getOverlayVrTooltip` |
| `/set/enable/overlay_vr_tooltip` | ○ | `setEnableOverlayVrTooltip` |
| `/set/disable/overlay_vr_tooltip` | ○ | `setDisableOverlayVrTooltip` |
| `/set/data/overlay_vr_panel_font_size` | ○ | `setOverlayVrPanelFontSize` |
| `/set/enable/overlay_vr_panel_locked` | ○ | `setEnableOverlayVrPanelLocked` |
| `/set/disable/overlay_vr_panel_locked` | ○ | `setDisableOverlayVrPanelLocked` |
| `/set/data/overlay_vr_panel_opacity` | ○ | `setOverlayVrPanelOpacity` |
| `/set/data/overlay_small_log_settings` | ○ | `setOverlaySmallLogSettings` |
| `/get/data/overlay_large_log` | ○ | `getOverlayLargeLog` |
| `/get/data/overlay_vr_panel` | ○ | `getOverlayVrPanel` |
| `/set/enable/overlay_vr_panel` | ○ | `setEnableOverlayVrPanel` |
| `/set/disable/overlay_vr_panel` | ○ | `setDisableOverlayVrPanel` |
| `/set/enable/overlay_large_log` | ○ | `setEnableOverlayLargeLog` |
| `/set/disable/overlay_large_log` | ○ | `setDisableOverlayLargeLog` |
| `/get/data/overlay_large_log_settings` | ○ | `getOverlayLargeLogSettings` |
| `/set/data/overlay_large_log_settings` | ○ | `setOverlayLargeLogSettings` |
| `/get/data/overlay_show_only_translated_messages` | ○ | `getOverlayShowOnlyTranslatedMessages` |
| `/set/enable/overlay_show_only_translated_messages` | ○ | `setEnableOverlayShowOnlyTranslatedMessages` |
| `/set/disable/overlay_show_only_translated_messages` | ○ | `setDisableOverlayShowOnlyTranslatedMessages` |

## OCR（10 件）

| エンドポイント | 初期化中 | Python のハンドラ |
|---|---|---|
| `/set/enable/ocr_capture` | ✗ | `setEnableOcrCapture` |
| `/set/disable/ocr_capture` | ✗ | `setDisableOcrCapture` |
| `/get/data/ocr_window_title` | ○ | `getOcrWindowTitle` |
| `/set/data/ocr_window_title` | ○ | `setOcrWindowTitle` |
| `/get/data/ocr_poll_interval_ms` | ○ | `getOcrPollIntervalMs` |
| `/set/data/ocr_poll_interval_ms` | ○ | `setOcrPollIntervalMs` |
| `/get/data/ocr_min_confidence` | ○ | `getOcrMinConfidence` |
| `/set/data/ocr_min_confidence` | ○ | `setOcrMinConfidence` |
| `/get/data/ocr_bubble_min_text_length` | ○ | `getOcrBubbleMinTextLength` |
| `/set/data/ocr_bubble_min_text_length` | ○ | `setOcrBubbleMinTextLength` |

## OSC・VRChat（21 件）

| エンドポイント | 初期化中 | Python のハンドラ |
|---|---|---|
| `/run/send_message_box` | ✗ | `sendMessageBox` |
| `/run/typing_message_box` | ✗ | `typingMessageBox` |
| `/run/stop_typing_message_box` | ✗ | `stopTypingMessageBox` |
| `/get/data/message_box_ratio` | ○ | `getMessageBoxRatio` |
| `/set/data/message_box_ratio` | ○ | `setMessageBoxRatio` |
| `/get/data/auto_clear_message_box` | ○ | `getAutoClearMessageBox` |
| `/set/enable/auto_clear_message_box` | ○ | `setEnableAutoClearMessageBox` |
| `/set/disable/auto_clear_message_box` | ○ | `setDisableAutoClearMessageBox` |
| `/get/data/send_message_to_vrc` | ○ | `getSendMessageToVrc` |
| `/set/enable/send_message_to_vrc` | ○ | `setEnableSendMessageToVrc` |
| `/set/disable/send_message_to_vrc` | ○ | `setDisableSendMessageToVrc` |
| `/get/data/send_received_message_to_vrc` | ○ | `getSendReceivedMessageToVrc` |
| `/set/enable/send_received_message_to_vrc` | ○ | `setEnableSendReceivedMessageToVrc` |
| `/set/disable/send_received_message_to_vrc` | ○ | `setDisableSendReceivedMessageToVrc` |
| `/get/data/osc_ip_address` | ○ | `getOscIpAddress` |
| `/set/data/osc_ip_address` | ○ | `setOscIpAddress` |
| `/get/data/osc_port` | ○ | `getOscPort` |
| `/set/data/osc_port` | ○ | `setOscPort` |
| `/get/data/notification_vrc_sfx` | ○ | `getNotificationVrcSfx` |
| `/set/enable/notification_vrc_sfx` | ○ | `setEnableNotificationVrcSfx` |
| `/set/disable/notification_vrc_sfx` | ○ | `setDisableNotificationVrcSfx` |

## WebSocket・OBS・クリップボード（30 件）

| エンドポイント | 初期化中 | Python のハンドラ |
|---|---|---|
| `/get/data/websocket_host` | ○ | `getWebSocketHost` |
| `/set/data/websocket_host` | ○ | `setWebSocketHost` |
| `/get/data/websocket_port` | ○ | `getWebSocketPort` |
| `/set/data/websocket_port` | ○ | `setWebSocketPort` |
| `/get/data/websocket_auth_token` | ○ | `getWebSocketAuthToken` |
| `/get/data/websocket_server` | ○ | `getWebSocketServer` |
| `/set/enable/websocket_server` | ○ | `setEnableWebSocketServer` |
| `/set/disable/websocket_server` | ○ | `setDisableWebSocketServer` |
| `/get/data/obs_browser_source` | ○ | `getObsBrowserSource` |
| `/set/enable/obs_browser_source` | ○ | `setEnableObsBrowserSource` |
| `/set/disable/obs_browser_source` | ○ | `setDisableObsBrowserSource` |
| `/get/data/obs_browser_source_port` | ○ | `getObsBrowserSourcePort` |
| `/set/data/obs_browser_source_port` | ○ | `setObsBrowserSourcePort` |
| `/get/data/obs_browser_source_max_messages` | ○ | `getObsBrowserSourceMaxMessages` |
| `/set/data/obs_browser_source_max_messages` | ○ | `setObsBrowserSourceMaxMessages` |
| `/get/data/obs_browser_source_display_duration` | ○ | `getObsBrowserSourceDisplayDuration` |
| `/set/data/obs_browser_source_display_duration` | ○ | `setObsBrowserSourceDisplayDuration` |
| `/get/data/obs_browser_source_fadeout_duration` | ○ | `getObsBrowserSourceFadeoutDuration` |
| `/set/data/obs_browser_source_fadeout_duration` | ○ | `setObsBrowserSourceFadeoutDuration` |
| `/get/data/obs_browser_source_font_size` | ○ | `getObsBrowserSourceFontSize` |
| `/set/data/obs_browser_source_font_size` | ○ | `setObsBrowserSourceFontSize` |
| `/get/data/obs_browser_source_font_color` | ○ | `getObsBrowserSourceFontColor` |
| `/set/data/obs_browser_source_font_color` | ○ | `setObsBrowserSourceFontColor` |
| `/get/data/obs_browser_source_font_outline_thickness` | ○ | `getObsBrowserSourceFontOutlineThickness` |
| `/set/data/obs_browser_source_font_outline_thickness` | ○ | `setObsBrowserSourceFontOutlineThickness` |
| `/get/data/obs_browser_source_font_outline_color` | ○ | `getObsBrowserSourceFontOutlineColor` |
| `/set/data/obs_browser_source_font_outline_color` | ○ | `setObsBrowserSourceFontOutlineColor` |
| `/get/data/clipboard` | ○ | `getClipboard` |
| `/set/enable/clipboard` | ○ | `setEnableClipboard` |
| `/set/disable/clipboard` | ○ | `setDisableClipboard` |

## 更新・テレメトリー・計算デバイス（11 件）

| エンドポイント | 初期化中 | Python のハンドラ |
|---|---|---|
| `/get/data/selectable_release_channels` | ○ | `getSelectableReleaseChannels` |
| `/get/data/release_channel` | ○ | `getSelectedReleaseChannel` |
| `/set/data/release_channel` | ○ | `setSelectedReleaseChannel` |
| `/get/data/available_releases` | ○ | `listAvailableReleases` |
| `/get/data/telemetry` | ○ | `getTelemetry` |
| `/set/enable/telemetry` | ○ | `setEnableTelemetry` |
| `/set/disable/telemetry` | ○ | `setDisableTelemetry` |
| `/run/update_software` | ○ | `updateSoftware` |
| `/run/update_cuda_software` | ○ | `updateCudaSoftware` |
| `/get/data/version` | ○ | `getVersion` |
| `/get/data/compute_mode` | ○ | `getComputeMode` |

## アプリ・UI・その他（36 件）

| エンドポイント | 初期化中 | Python のハンドラ |
|---|---|---|
| `/set/enable/foreground` | ○ | `setEnableForeground` |
| `/set/disable/foreground` | ○ | `setDisableForeground` |
| `/get/data/selected_tab_no` | ○ | `getSelectedTabNo` |
| `/set/data/selected_tab_no` | ○ | `setSelectedTabNo` |
| `/get/data/main_window_sidebar_compact_mode` | ○ | `getMainWindowSidebarCompactMode` |
| `/set/enable/main_window_sidebar_compact_mode` | ○ | `setEnableMainWindowSidebarCompactMode` |
| `/set/disable/main_window_sidebar_compact_mode` | ○ | `setDisableMainWindowSidebarCompactMode` |
| `/run/shutdown` | ○ | `shutdown` |
| `/get/data/transparency` | ○ | `getTransparency` |
| `/set/data/transparency` | ○ | `setTransparency` |
| `/get/data/ui_scaling` | ○ | `getUiScaling` |
| `/set/data/ui_scaling` | ○ | `setUiScaling` |
| `/get/data/textbox_ui_scaling` | ○ | `getTextboxUiScaling` |
| `/set/data/textbox_ui_scaling` | ○ | `setTextboxUiScaling` |
| `/get/data/send_message_button_type` | ○ | `getSendMessageButtonType` |
| `/set/data/send_message_button_type` | ○ | `setSendMessageButtonType` |
| `/get/data/show_resend_button` | ○ | `getShowResendButton` |
| `/set/enable/show_resend_button` | ○ | `setEnableShowResendButton` |
| `/set/disable/show_resend_button` | ○ | `setDisableShowResendButton` |
| `/get/data/font_family` | ○ | `getFontFamily` |
| `/set/data/font_family` | ○ | `setFontFamily` |
| `/get/data/main_window_geometry` | ○ | `getMainWindowGeometry` |
| `/set/data/main_window_geometry` | ○ | `setMainWindowGeometry` |
| `/get/data/send_message_format_parts` | ○ | `getSendMessageFormatParts` |
| `/set/data/send_message_format_parts` | ○ | `setSendMessageFormatParts` |
| `/get/data/received_message_format_parts` | ○ | `getReceivedMessageFormatParts` |
| `/set/data/received_message_format_parts` | ○ | `setReceivedMessageFormatParts` |
| `/get/data/send_only_translated_messages` | ○ | `getSendOnlyTranslatedMessages` |
| `/set/enable/send_only_translated_messages` | ○ | `setEnableSendOnlyTranslatedMessages` |
| `/set/disable/send_only_translated_messages` | ○ | `setDisableSendOnlyTranslatedMessages` |
| `/get/data/logger_feature` | ○ | `getLoggerFeature` |
| `/set/enable/logger_feature` | ○ | `setEnableLoggerFeature` |
| `/set/disable/logger_feature` | ○ | `setDisableLoggerFeature` |
| `/run/open_filepath_logs` | ○ | `openFilepathLogs` |
| `/run/open_filepath_config_file` | ○ | `openFilepathConfigFile` |
| `/run/feed_watchdog` | ○ | `feedWatchdog` |

## push（バックエンド→UI、81 件）

| 内部名 | エンドポイント |
|---|---|
| `enable_translation` | `/run/enable_translation` |
| `enable_transcription_send` | `/run/enable_transcription_send` |
| `enable_transcription_receive` | `/run/enable_transcription_receive` |
| `disable_transcription_send` | `/set/disable/transcription_send` |
| `disable_transcription_receive` | `/set/disable/transcription_receive` |
| `disable_check_mic_threshold` | `/set/disable/check_mic_threshold` |
| `disable_check_speaker_threshold` | `/set/disable/check_speaker_threshold` |
| `connected_network` | `/run/connected_network` |
| `enable_ai_models` | `/run/enable_ai_models` |
| `update_software` | `/run/update_software` |
| `update_cuda_software` | `/run/update_cuda_software` |
| `transcription_mic` | `/run/transcription_send_mic_message` |
| `transcription_speaker` | `/run/transcription_receive_speaker_message` |
| `transcription_ocr` | `/run/transcription_ocr_message` |
| `enable_ocr_capture` | `/run/enable_ocr_capture` |
| `check_mic_volume` | `/run/check_mic_volume` |
| `check_speaker_volume` | `/run/check_speaker_volume` |
| `error_device` | `/run/error_device` |
| `error_translation_engine` | `/run/error_translation_engine` |
| `error_translation_chat_vram_overflow` | `/run/error_translation_chat_vram_overflow` |
| `error_translation_mic_vram_overflow` | `/run/error_translation_mic_vram_overflow` |
| `error_translation_speaker_vram_overflow` | `/run/error_translation_speaker_vram_overflow` |
| `error_transcription_mic_vram_overflow` | `/run/error_transcription_mic_vram_overflow` |
| `error_transcription_speaker_vram_overflow` | `/run/error_transcription_speaker_vram_overflow` |
| `word_filter` | `/run/word_filter` |
| `transcription_recognition_error` | `/run/transcription_recognition_error` |
| `download_progress_ctranslate2_weight` | `/run/download_progress_ctranslate2_weight` |
| `downloaded_ctranslate2_weight` | `/run/downloaded_ctranslate2_weight` |
| `error_ctranslate2_weight` | `/run/error_ctranslate2_weight` |
| `download_progress_whisper_weight` | `/run/download_progress_whisper_weight` |
| `downloaded_whisper_weight` | `/run/downloaded_whisper_weight` |
| `error_whisper_weight` | `/run/error_whisper_weight` |
| `selected_mic_host` | `/run/selected_mic_host` |
| `selected_mic_device` | `/run/selected_mic_device` |
| `selected_speaker_device` | `/run/selected_speaker_device` |
| `selected_translation_engines` | `/run/selected_translation_engines` |
| `translation_engines` | `/run/translation_engines` |
| `selected_your_languages` | `/run/selected_your_languages` |
| `selected_target_languages` | `/run/selected_target_languages` |
| `selectable_language_list` | `/run/selectable_language_list` |
| `selected_translation_compute_type` | `/run/selected_translation_compute_type` |
| `selected_transcription_compute_type` | `/run/selected_transcription_compute_type` |
| `selectable_plamo_model_list` | `/run/selectable_plamo_model_list` |
| `selected_plamo_model` | `/run/selected_plamo_model` |
| `selectable_gemini_model_list` | `/run/selectable_gemini_model_list` |
| `selected_gemini_model` | `/run/selected_gemini_model` |
| `selectable_openai_model_list` | `/run/selectable_openai_model_list` |
| `selected_openai_model` | `/run/selected_openai_model` |
| `selectable_groq_model_list` | `/run/selectable_groq_model_list` |
| `selected_groq_model` | `/run/selected_groq_model` |
| `selectable_openrouter_model_list` | `/run/selectable_openrouter_model_list` |
| `selected_openrouter_model` | `/run/selected_openrouter_model` |
| `selectable_lmstudio_model_list` | `/run/selectable_lmstudio_model_list` |
| `selected_lmstudio_model` | `/run/selected_lmstudio_model` |
| `selectable_openai_compatible_model_list` | `/run/selectable_openai_compatible_model_list` |
| `selected_openai_compatible_model` | `/run/selected_openai_compatible_model` |
| `selectable_ollama_model_list` | `/run/selectable_ollama_model_list` |
| `selected_ollama_model` | `/run/selected_ollama_model` |
| `selectable_groq_whisper_model_list` | `/run/selectable_groq_whisper_model_list` |
| `selected_groq_whisper_model` | `/run/selected_groq_whisper_model` |
| `selectable_openai_whisper_model_list` | `/run/selectable_openai_whisper_model_list` |
| `selected_openai_whisper_model` | `/run/selected_openai_whisper_model` |
| `selectable_custom_whisper_model_list` | `/run/selectable_custom_whisper_model_list` |
| `selected_custom_whisper_model` | `/run/selected_custom_whisper_model` |
| `selectable_deepgram_model_list` | `/run/selectable_deepgram_model_list` |
| `selected_deepgram_model` | `/run/selected_deepgram_model` |
| `overlay_small_log_settings` | `/run/overlay_small_log_settings` |
| `vr_panel_pointer` | `/run/vr_panel_pointer` |
| `vr_panel_log_out_of_view` | `/run/vr_panel_log_out_of_view` |
| `overlay_vr_launcher_hand` | `/run/overlay_vr_launcher_hand` |
| `vr_panel_launcher_intro` | `/run/vr_panel_launcher_intro` |
| `overlay_vr_panel_anchor` | `/run/overlay_vr_panel_anchor` |
| `vr_panel_layout` | `/run/vr_panel_layout` |
| `overlay_large_log_settings` | `/run/overlay_large_log_settings` |
| `selectable_mic_host_list` | `/run/selectable_mic_host_list` |
| `selectable_mic_device_list` | `/run/selectable_mic_device_list` |
| `selectable_speaker_device_list` | `/run/selectable_speaker_device_list` |
| `software_update_info` | `/run/software_update_info` |
| `initialization_progress` | `/run/initialization_progress` |
| `initialization_complete` | `/run/initialization_complete` |
| `enable_osc_query` | `/run/enable_osc_query` |
