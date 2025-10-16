import sys
import json
import time
from typing import Any, Tuple
from threading import Thread, Event, Lock
from queue import Queue, Empty
import logging
from controller import Controller  # noqa: E402
from utils import printLog, printResponse, errorLogging, encodeBase64 # noqa: E402

logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

run_mapping = {
    "enable_translation":"/run/enable_translation",
    "enable_transcription_send":"/run/enable_transcription_send",
    "enable_transcription_receive":"/run/enable_transcription_receive",

    "connected_network":"/run/connected_network",
    "enable_ai_models":"/run/enable_ai_models",

    "transcription_mic":"/run/transcription_send_mic_message",
    "transcription_speaker":"/run/transcription_receive_speaker_message",

    "check_mic_volume":"/run/check_mic_volume",
    "check_speaker_volume":"/run/check_speaker_volume",

    "error_device":"/run/error_device",
    "error_translation_engine":"/run/error_translation_engine",

    "error_translation_chat_vram_overflow":"/run/error_translation_chat_vram_overflow",
    "error_translation_mic_vram_overflow":"/run/error_translation_mic_vram_overflow",
    "error_translation_speaker_vram_overflow":"/run/error_translation_speaker_vram_overflow",
    "error_transcription_mic_vram_overflow":"/run/error_transcription_mic_vram_overflow",
    "error_transcription_speaker_vram_overflow":"/run/error_transcription_speaker_vram_overflow",

    "word_filter":"/run/word_filter",

    "download_progress_ctranslate2_weight":"/run/download_progress_ctranslate2_weight",
    "downloaded_ctranslate2_weight":"/run/downloaded_ctranslate2_weight",
    "error_ctranslate2_weight":"/run/error_ctranslate2_weight",
    "download_progress_whisper_weight":"/run/download_progress_whisper_weight",
    "downloaded_whisper_weight":"/run/downloaded_whisper_weight",
    "error_whisper_weight":"/run/error_whisper_weight",

    "selected_mic_device":"/run/selected_mic_device",
    "selected_speaker_device":"/run/selected_speaker_device",

    "selected_translation_engines":"/run/selected_translation_engines",
    "translation_engines":"/run/translation_engines",

    "selected_translation_compute_type":"/run/selected_translation_compute_type",
    "selected_transcription_compute_type":"/run/selected_transcription_compute_type",

    "mic_host_list":"/run/mic_host_list",
    "mic_device_list":"/run/mic_device_list",
    "speaker_device_list":"/run/speaker_device_list",

    "software_update_info":"/run/software_update_info",

    "initialization_progress":"/run/initialization_progress",
    "initialization_complete":"/run/initialization_complete",

    "enable_osc_query":"/run/enable_osc_query",
}

def run(status:int, endpoint:str, result:Any) -> None:
    printResponse(status, endpoint, result)

controller = Controller()
controller.setRunMapping(run_mapping)
controller.setRun(run)

mapping = {
    # Main Window
    "/set/enable/translation": {"status": False, "variable":controller.setEnableTranslation},
    "/set/disable/translation": {"status": False, "variable":controller.setDisableTranslation},

    "/set/enable/transcription_send": {"status": False, "variable":controller.setEnableTranscriptionSend},
    "/set/disable/transcription_send": {"status": False, "variable":controller.setDisableTranscriptionSend},

    "/set/enable/transcription_receive": {"status": False, "variable":controller.setEnableTranscriptionReceive},
    "/set/disable/transcription_receive": {"status": False, "variable":controller.setDisableTranscriptionReceive},

    "/set/enable/foreground": {"status": True, "variable":controller.setEnableForeground},
    "/set/disable/foreground": {"status": True, "variable":controller.setDisableForeground},

    "/get/data/selected_tab_no": {"status": True, "variable":controller.getSelectedTabNo},
    "/set/data/selected_tab_no": {"status": True, "variable":controller.setSelectedTabNo},

    "/get/data/main_window_sidebar_compact_mode": {"status": True, "variable":controller.getMainWindowSidebarCompactMode},
    "/set/enable/main_window_sidebar_compact_mode": {"status": True, "variable":controller.setEnableMainWindowSidebarCompactMode},
    "/set/disable/main_window_sidebar_compact_mode": {"status": True, "variable":controller.setDisableMainWindowSidebarCompactMode},

    "/get/data/translation_engines": {"status": True, "variable":controller.getTranslationEngines},
    "/get/data/selectable_language_list": {"status": True, "variable":controller.getListLanguageAndCountry},

    "/get/data/selected_translation_engines": {"status": False, "variable":controller.getSelectedTranslationEngines},
    "/set/data/selected_translation_engines": {"status": True, "variable":controller.setSelectedTranslationEngines},

    "/get/data/selected_your_languages": {"status": True, "variable":controller.getSelectedYourLanguages},
    "/set/data/selected_your_languages": {"status": True, "variable":controller.setSelectedYourLanguages},

    "/get/data/selected_target_languages": {"status": True, "variable":controller.getSelectedTargetLanguages},
    "/set/data/selected_target_languages": {"status": True, "variable":controller.setSelectedTargetLanguages},

    "/get/data/transcription_engines": {"status": False, "variable":controller.getTranscriptionEngines},
    "/get/data/selected_transcription_engine": {"status": False, "variable":controller.getSelectedTranscriptionEngine},
    "/set/data/selected_transcription_engine": {"status": False, "variable":controller.setSelectedTranscriptionEngine},

    "/run/send_message_box": {"status": False, "variable":controller.sendMessageBox},
    "/run/typing_message_box": {"status": False, "variable":controller.typingMessageBox},
    "/run/stop_typing_message_box": {"status": False, "variable":controller.stopTypingMessageBox},

    "/run/send_text_overlay": {"status": True, "variable":controller.sendTextOverlay},

    "/run/swap_your_language_and_target_language": {"status": True, "variable":controller.swapYourLanguageAndTargetLanguage},

    "/run/update_software": {"status": True, "variable":controller.updateSoftware},
    "/run/update_cuda_software": {"status": True, "variable":controller.updateCudaSoftware},

    # Config Window
    # Appearance
    "/get/data/version": {"status": True, "variable":controller.getVersion},

    "/get/data/transparency": {"status": True, "variable":controller.getTransparency},
    "/set/data/transparency": {"status": True, "variable":controller.setTransparency},

    "/get/data/ui_scaling": {"status": True, "variable":controller.getUiScaling},
    "/set/data/ui_scaling": {"status": True, "variable":controller.setUiScaling},

    "/get/data/textbox_ui_scaling": {"status": True, "variable":controller.getTextboxUiScaling},
    "/set/data/textbox_ui_scaling": {"status": True, "variable":controller.setTextboxUiScaling},

    "/get/data/message_box_ratio": {"status": True, "variable":controller.getMessageBoxRatio},
    "/set/data/message_box_ratio": {"status": True, "variable":controller.setMessageBoxRatio},

    "/get/data/send_message_button_type": {"status": True, "variable":controller.getSendMessageButtonType},
    "/set/data/send_message_button_type": {"status": True, "variable":controller.setSendMessageButtonType},

    "/get/data/show_resend_button": {"status": True, "variable":controller.getShowResendButton},
    "/set/enable/show_resend_button": {"status": True, "variable":controller.setEnableShowResendButton},
    "/set/disable/show_resend_button": {"status": True, "variable":controller.setDisableShowResendButton},

    "/get/data/font_family": {"status": True, "variable":controller.getFontFamily},
    "/set/data/font_family": {"status": True, "variable":controller.setFontFamily},

    "/get/data/ui_language": {"status": True, "variable":controller.getUiLanguage},
    "/set/data/ui_language": {"status": True, "variable":controller.setUiLanguage},

    "/get/data/main_window_geometry": {"status": True, "variable":controller.getMainWindowGeometry},
    "/set/data/main_window_geometry": {"status": True, "variable":controller.setMainWindowGeometry},

    # Compute device
    "/get/data/compute_mode": {"status": True, "variable":controller.getComputeMode},
    "/get/data/translation_compute_device_list": {"status": True, "variable":controller.getComputeDeviceList},
    "/get/data/selected_translation_compute_device": {"status": True, "variable":controller.getSelectedTranslationComputeDevice},
    "/set/data/selected_translation_compute_device": {"status": True, "variable":controller.setSelectedTranslationComputeDevice},
    "/get/data/transcription_compute_device_list": {"status": True, "variable":controller.getComputeDeviceList},
    "/get/data/selected_transcription_compute_device": {"status": True, "variable":controller.getSelectedTranscriptionComputeDevice},
    "/set/data/selected_transcription_compute_device": {"status": True, "variable":controller.setSelectedTranscriptionComputeDevice},

    # Translation
    "/get/data/selectable_ctranslate2_weight_type_dict": {"status": True, "variable":controller.getSelectableCtranslate2WeightTypeDict},

    "/get/data/ctranslate2_weight_type": {"status": True, "variable":controller.getCtranslate2WeightType},
    "/set/data/ctranslate2_weight_type": {"status": True, "variable":controller.setCtranslate2WeightType},

    "/get/data/selected_translation_compute_type": {"status": True, "variable":controller.getSelectedTranslationComputeType},
    "/set/data/selected_translation_compute_type": {"status": True, "variable":controller.setSelectedTranslationComputeType},

    "/run/download_ctranslate2_weight": {"status": True, "variable":controller.downloadCtranslate2Weight},

    "/get/data/deepl_auth_key": {"status": False, "variable":controller.getDeepLAuthKey},
    "/set/data/deepl_auth_key": {"status": False, "variable":controller.setDeeplAuthKey},
    "/delete/data/deepl_auth_key": {"status": False, "variable":controller.delDeeplAuthKey},

    "/get/data/plamo_model_list": {"status": False, "variable":controller.getPlamoModelList},
    "/get/data/plamo_model": {"status": False, "variable":controller.getPlamoModel},
    "/set/data/plamo_model": {"status": False, "variable":controller.setPlamoModel},
    "/get/data/plamo_auth_key": {"status": False, "variable":controller.getPlamoAuthKey},
    "/set/data/plamo_auth_key": {"status": False, "variable":controller.setPlamoAuthKey},
    "/delete/data/plamo_auth_key": {"status": False, "variable":controller.delPlamoAuthKey},

    "/get/data/gemini_model_list": {"status": True, "variable":controller.getGeminiModelList},
    "/get/data/gemini_model": {"status": True, "variable":controller.getGeminiModel},
    "/set/data/gemini_model": {"status": True, "variable":controller.setGeminiModel},
    "/get/data/gemini_auth_key": {"status": True, "variable":controller.getGeminiAuthKey},
    "/set/data/gemini_auth_key": {"status": True, "variable":controller.setGeminiAuthKey},
    "/delete/data/gemini_auth_key": {"status": True, "variable":controller.delGeminiAuthKey},

    "/get/data/openai_model_list": {"status": True, "variable":controller.getOpenAIModelList},
    "/get/data/openai_model": {"status": True, "variable":controller.getOpenAIModel},
    "/set/data/openai_model": {"status": True, "variable":controller.setOpenAIModel},
    "/get/data/openai_auth_key": {"status": True, "variable":controller.getOpenAIAuthKey},
    "/set/data/openai_auth_key": {"status": True, "variable":controller.setOpenAIAuthKey},
    "/delete/data/openai_auth_key": {"status": True, "variable":controller.delOpenAIAuthKey},

    "/get/data/convert_message_to_romaji": {"status": True, "variable":controller.getConvertMessageToRomaji},
    "/set/enable/convert_message_to_romaji": {"status": True, "variable":controller.setEnableConvertMessageToRomaji},
    "/set/disable/convert_message_to_romaji": {"status": True, "variable":controller.setDisableConvertMessageToRomaji},

    "/get/data/convert_message_to_hiragana": {"status": True, "variable":controller.getConvertMessageToHiragana},
    "/set/enable/convert_message_to_hiragana": {"status": True, "variable":controller.setEnableConvertMessageToHiragana},
    "/set/disable/convert_message_to_hiragana": {"status": True, "variable":controller.setDisableConvertMessageToHiragana},

    # Transcription
    "/get/data/mic_host_list": {"status": True, "variable":controller.getMicHostList},
    "/get/data/mic_device_list": {"status": True, "variable":controller.getMicDeviceList},
    "/get/data/speaker_device_list": {"status": True, "variable":controller.getSpeakerDeviceList},

    # "/get/data/max_mic_threshold": {"status": True, "variable":controller.getMaxMicThreshold},
    # "/get/data/max_speaker_threshold": {"status": True, "variable":controller.getMaxSpeakerThreshold},

    "/get/data/auto_mic_select": {"status": True, "variable":controller.getAutoMicSelect},
    "/set/enable/auto_mic_select": {"status": True, "variable":controller.setEnableAutoMicSelect},
    "/set/disable/auto_mic_select": {"status": True, "variable":controller.setDisableAutoMicSelect},

    "/get/data/selected_mic_host": {"status": True, "variable":controller.getSelectedMicHost},
    "/set/data/selected_mic_host": {"status": True, "variable":controller.setSelectedMicHost},

    "/get/data/selected_mic_device": {"status": True, "variable":controller.getSelectedMicDevice},
    "/set/data/selected_mic_device": {"status": True, "variable":controller.setSelectedMicDevice},

    "/get/data/mic_threshold": {"status": True, "variable":controller.getMicThreshold},
    "/set/data/mic_threshold": {"status": True, "variable":controller.setMicThreshold},

    "/get/data/mic_automatic_threshold": {"status": True, "variable":controller.getMicAutomaticThreshold},
    "/set/enable/mic_automatic_threshold": {"status": True, "variable":controller.setEnableMicAutomaticThreshold},
    "/set/disable/mic_automatic_threshold": {"status": True, "variable":controller.setDisableMicAutomaticThreshold},

    "/get/data/mic_record_timeout": {"status": True, "variable":controller.getMicRecordTimeout},
    "/set/data/mic_record_timeout": {"status": True, "variable":controller.setMicRecordTimeout},

    "/get/data/mic_phrase_timeout": {"status": True, "variable":controller.getMicPhraseTimeout},
    "/set/data/mic_phrase_timeout": {"status": True, "variable":controller.setMicPhraseTimeout},

    "/get/data/mic_max_phrases": {"status": True, "variable":controller.getMicMaxPhrases},
    "/set/data/mic_max_phrases": {"status": True, "variable":controller.setMicMaxPhrases},

    "/get/data/hotkeys": {"status": True, "variable":controller.getHotkeys},
    "/set/data/hotkeys": {"status": True, "variable":controller.setHotkeys},

    "/get/data/plugins_status": {"status": True, "variable":controller.getPluginsStatus},
    "/set/data/plugins_status": {"status": True, "variable":controller.setPluginsStatus},

    "/get/data/mic_avg_logprob": {"status": True, "variable":controller.getMicAvgLogprob},
    "/set/data/mic_avg_logprob": {"status": True, "variable":controller.setMicAvgLogprob},

    "/get/data/mic_no_speech_prob": {"status": True, "variable":controller.getMicNoSpeechProb},
    "/set/data/mic_no_speech_prob": {"status": True, "variable":controller.setMicNoSpeechProb},

    "/set/enable/check_mic_threshold": {"status": True, "variable":controller.setEnableCheckMicThreshold},
    "/set/disable/check_mic_threshold": {"status": True, "variable":controller.setDisableCheckMicThreshold},

    "/get/data/mic_word_filter": {"status": True, "variable":controller.getMicWordFilter},
    "/set/data/mic_word_filter": {"status": True, "variable":controller.setMicWordFilter},

    "/get/data/auto_speaker_select": {"status": True, "variable":controller.getAutoSpeakerSelect},
    "/set/enable/auto_speaker_select": {"status": True, "variable":controller.setEnableAutoSpeakerSelect},
    "/set/disable/auto_speaker_select": {"status": True, "variable":controller.setDisableAutoSpeakerSelect},

    "/get/data/selected_speaker_device": {"status": True, "variable":controller.getSelectedSpeakerDevice},
    "/set/data/selected_speaker_device": {"status": True, "variable":controller.setSelectedSpeakerDevice},

    "/get/data/speaker_threshold": {"status": True, "variable":controller.getSpeakerThreshold},
    "/set/data/speaker_threshold": {"status": True, "variable":controller.setSpeakerThreshold},

    "/get/data/speaker_automatic_threshold": {"status": True, "variable":controller.getSpeakerAutomaticThreshold},
    "/set/enable/speaker_automatic_threshold": {"status": True, "variable":controller.setEnableSpeakerAutomaticThreshold},
    "/set/disable/speaker_automatic_threshold": {"status": True, "variable":controller.setDisableSpeakerAutomaticThreshold},

    "/get/data/speaker_record_timeout": {"status": True, "variable":controller.getSpeakerRecordTimeout},
    "/set/data/speaker_record_timeout": {"status": True, "variable":controller.setSpeakerRecordTimeout},

    "/get/data/speaker_phrase_timeout": {"status": True, "variable":controller.getSpeakerPhraseTimeout},
    "/set/data/speaker_phrase_timeout": {"status": True, "variable":controller.setSpeakerPhraseTimeout},

    "/get/data/speaker_max_phrases": {"status": True, "variable":controller.getSpeakerMaxPhrases},
    "/set/data/speaker_max_phrases": {"status": True, "variable":controller.setSpeakerMaxPhrases},

    "/get/data/speaker_avg_logprob": {"status": True, "variable":controller.getSpeakerAvgLogprob},
    "/set/data/speaker_avg_logprob": {"status": True, "variable":controller.setSpeakerAvgLogprob},

    "/get/data/speaker_no_speech_prob": {"status": True, "variable":controller.getSpeakerNoSpeechProb},
    "/set/data/speaker_no_speech_prob": {"status": True, "variable":controller.setSpeakerNoSpeechProb},

    "/set/enable/check_speaker_threshold": {"status": True, "variable":controller.setEnableCheckSpeakerThreshold},
    "/set/disable/check_speaker_threshold": {"status": True, "variable":controller.setDisableCheckSpeakerThreshold},

    "/get/data/selectable_whisper_weight_type_dict": {"status": True, "variable":controller.getSelectableWhisperWeightTypeDict},

    "/get/data/whisper_weight_type": {"status": True, "variable":controller.getWhisperWeightType},
    "/set/data/whisper_weight_type": {"status": True, "variable":controller.setWhisperWeightType},

    "/get/data/selected_transcription_compute_type": {"status": True, "variable":controller.getSelectedTranscriptionComputeType},
    "/set/data/selected_transcription_compute_type": {"status": True, "variable":controller.setSelectedTranscriptionComputeType},

    "/run/download_whisper_weight": {"status": True, "variable":controller.downloadWhisperWeight},

    # VR
    "/get/data/overlay_small_log": {"status": True, "variable":controller.getOverlaySmallLog},
    "/set/enable/overlay_small_log": {"status": True, "variable":controller.setEnableOverlaySmallLog},
    "/set/disable/overlay_small_log": {"status": True, "variable":controller.setDisableOverlaySmallLog},

    "/get/data/overlay_small_log_settings": {"status": True, "variable":controller.getOverlaySmallLogSettings},
    "/set/data/overlay_small_log_settings": {"status": True, "variable":controller.setOverlaySmallLogSettings},

    "/get/data/overlay_large_log": {"status": True, "variable":controller.getOverlayLargeLog},
    "/set/enable/overlay_large_log": {"status": True, "variable":controller.setEnableOverlayLargeLog},
    "/set/disable/overlay_large_log": {"status": True, "variable":controller.setDisableOverlayLargeLog},

    "/get/data/overlay_large_log_settings": {"status": True, "variable":controller.getOverlayLargeLogSettings},
    "/set/data/overlay_large_log_settings": {"status": True, "variable":controller.setOverlayLargeLogSettings},

    "/get/data/overlay_show_only_translated_messages": {"status": True, "variable":controller.getOverlayShowOnlyTranslatedMessages},
    "/set/enable/overlay_show_only_translated_messages": {"status": True, "variable":controller.setEnableOverlayShowOnlyTranslatedMessages},
    "/set/disable/overlay_show_only_translated_messages": {"status": True, "variable":controller.setDisableOverlayShowOnlyTranslatedMessages},

    # Others
    "/get/data/send_message_format_parts": {"status": True, "variable":controller.getSendMessageFormatParts},
    "/set/data/send_message_format_parts": {"status": True, "variable":controller.setSendMessageFormatParts},
    "/get/data/received_message_format_parts": {"status": True, "variable":controller.getReceivedMessageFormatParts},
    "/set/data/received_message_format_parts": {"status": True, "variable":controller.setReceivedMessageFormatParts},

    "/get/data/auto_clear_message_box": {"status": True, "variable":controller.getAutoClearMessageBox},
    "/set/enable/auto_clear_message_box": {"status": True, "variable":controller.setEnableAutoClearMessageBox},
    "/set/disable/auto_clear_message_box": {"status": True, "variable":controller.setDisableAutoClearMessageBox},

    "/get/data/send_only_translated_messages": {"status": True, "variable":controller.getSendOnlyTranslatedMessages},
    "/set/enable/send_only_translated_messages": {"status": True, "variable":controller.setEnableSendOnlyTranslatedMessages},
    "/set/disable/send_only_translated_messages": {"status": True, "variable":controller.setDisableSendOnlyTranslatedMessages},

    "/get/data/logger_feature": {"status": True, "variable":controller.getLoggerFeature},
    "/set/enable/logger_feature": {"status": True, "variable":controller.setEnableLoggerFeature},
    "/set/disable/logger_feature": {"status": True, "variable":controller.setDisableLoggerFeature},

    "/run/open_filepath_logs": {"status": True, "variable":controller.openFilepathLogs},

    "/get/data/vrc_mic_mute_sync": {"status": True, "variable":controller.getVrcMicMuteSync},
    "/set/enable/vrc_mic_mute_sync": {"status": True, "variable":controller.setEnableVrcMicMuteSync},
    "/set/disable/vrc_mic_mute_sync": {"status": True, "variable":controller.setDisableVrcMicMuteSync},

    "/get/data/send_message_to_vrc": {"status": True, "variable":controller.getSendMessageToVrc},
    "/set/enable/send_message_to_vrc": {"status": True, "variable":controller.setEnableSendMessageToVrc},
    "/set/disable/send_message_to_vrc": {"status": True, "variable":controller.setDisableSendMessageToVrc},

    "/get/data/send_received_message_to_vrc": {"status": True, "variable":controller.getSendReceivedMessageToVrc},
    "/set/enable/send_received_message_to_vrc": {"status": True, "variable":controller.setEnableSendReceivedMessageToVrc},
    "/set/disable/send_received_message_to_vrc": {"status": True, "variable":controller.setDisableSendReceivedMessageToVrc},

    # WebSocket Settings
    "/get/data/websocket_host": {"status": True, "variable":controller.getWebSocketHost},
    "/set/data/websocket_host": {"status": True, "variable":controller.setWebSocketHost},
    "/get/data/websocket_port": {"status": True, "variable":controller.getWebSocketPort},
    "/set/data/websocket_port": {"status": True, "variable":controller.setWebSocketPort},
    "/get/data/websocket_server": {"status": True, "variable":controller.getWebSocketServer},
    "/set/enable/websocket_server": {"status": True, "variable":controller.setEnableWebSocketServer},
    "/set/disable/websocket_server": {"status": True, "variable":controller.setDisableWebSocketServer},

    # Advanced Settings
    "/get/data/osc_ip_address": {"status": True, "variable":controller.getOscIpAddress},
    "/set/data/osc_ip_address": {"status": True, "variable":controller.setOscIpAddress},

    "/get/data/osc_port": {"status": True, "variable":controller.getOscPort},
    "/set/data/osc_port": {"status": True, "variable":controller.setOscPort},

    "/get/data/notification_vrc_sfx": {"status": True, "variable":controller.getNotificationVrcSfx},
    "/set/enable/notification_vrc_sfx": {"status": True, "variable":controller.setEnableNotificationVrcSfx},
    "/set/disable/notification_vrc_sfx": {"status": True, "variable":controller.setDisableNotificationVrcSfx},

    "/run/open_filepath_config_file": {"status": True, "variable":controller.openFilepathConfigFile},

    # "/run/start_watchdog": {"status": True, "variable":controller.startWatchdog},
    "/run/feed_watchdog": {"status": True, "variable":controller.feedWatchdog},
    # "/run/stop_watchdog": {"status": True, "variable":controller.stopWatchdog},
}

init_mapping = {key:value for key, value in mapping.items() if key.startswith("/get/data/")}
controller.setInitMapping(init_mapping)

DEFAULT_WORKER_COUNT = 3  # 必要なら増やす

class Main:
    def __init__(self, controller_instance: Controller, mapping_data: dict, worker_count: int = DEFAULT_WORKER_COUNT) -> None:
        self.queue: Queue[Tuple[str, Any]] = Queue()
        self._stop_event: Event = Event()
        self.controller = controller_instance
        self.mapping = mapping_data
        self._threads: list[Thread] = []
        self._worker_count = worker_count

        # エンドポイントごとの排他制御用 Lock を作成
        # enable/disable ペアは同じロックキーに正規化する
        def _canonical_lock_key(endpoint: str) -> str:
            if not isinstance(endpoint, str):
                return str(endpoint)
            if endpoint.startswith("/set/enable/"):
                return "/lock/set/" + endpoint[len("/set/enable/"):]
            if endpoint.startswith("/set/disable/"):
                return "/lock/set/" + endpoint[len("/set/disable/"):]
            return endpoint

        # mapping に含まれるすべてのエンドポイントを走査して正規化キー集合を作る
        lock_keys = set()
        for key in self.mapping.keys():
            lock_keys.add(_canonical_lock_key(key))

        # 正規化キーごとに Lock を割り当てる
        self._endpoint_locks: dict[str, Lock] = {k: Lock() for k in lock_keys}

        # 正規化関数をインスタンスに保存
        self._canonical_lock_key = _canonical_lock_key

    def receiver(self) -> None:
        """Read lines from stdin, parse JSON and enqueue requests.

        Uses blocking readline but honors stop via _stop_event checked between reads.
        """
        while not self._stop_event.is_set():
            try:
                line = sys.stdin.readline()
                if not line:
                    # EOF reached; sleep briefly and re-check stop event
                    time.sleep(0.1)
                    continue
                received_data = json.loads(line.strip())

                if received_data:
                    endpoint = received_data.get("endpoint")
                    data = received_data.get("data")
                    data = encodeBase64(data) if data is not None else None
                    printLog(endpoint, {"receive_data": data})
                    self.queue.put((endpoint, data))
            except json.JSONDecodeError:
                # malformed input; log and continue
                errorLogging()
            except Exception:
                errorLogging()

    def startReceiver(self) -> None:
        th_receiver = Thread(target=self.receiver, name="main_receiver")
        th_receiver.daemon = True
        th_receiver.start()
        self._threads.append(th_receiver)

    def handleRequest(self, endpoint: str, data: Any = None) -> tuple:
        result = None  # デフォルト値を設定
        status = 500   # デフォルト値を設定

        handler = self.mapping.get(endpoint)
        if handler is None:
            response = "Invalid endpoint"
            status = 404
        elif handler["status"] is False:
            response = "Locked endpoint"
            status = 423
        else:
            try:
                response = handler["variable"](data)
                status = response.get("status")
                result = response.get("result")
                time.sleep(0.2)  # 処理の安定化のために少し待機
            except Exception:
                errorLogging()
                result = "Internal error"
                status = 500

        return result, status

    def _call_handler(self, endpoint: str, data: Any = None) -> tuple:
        result = None
        status = 500
        handler = self.mapping.get(endpoint)
        if handler is None:
            response = "Invalid endpoint"
            status = 404
        else:
            try:
                response = handler["variable"](data)
                status = response.get("status", 500)
                result = response.get("result", None)
                time.sleep(0.2)
            except Exception:
                errorLogging()
                result = "Internal error"
                status = 500
        return result, status

    def handler(self) -> None:
        while not self._stop_event.is_set():
            try:
                endpoint, data = self.queue.get(timeout=0.5)
            except Empty:
                continue

            # endpoint をロック用の正規化キーに変換してロックを取得
            lock_key = self._canonical_lock_key(endpoint)
            lock = self._endpoint_locks.get(lock_key)

            if lock is not None:
                acquired = lock.acquire(blocking=False)
                if not acquired:
                    # 同一機能で既に処理中 -> 少し待って再キュー
                    time.sleep(0.05)
                    self.queue.put((endpoint, data))
                    continue
                try:
                    result, status = self._call_handler(endpoint, data)
                finally:
                    lock.release()
            else:
                result, status = self._call_handler(endpoint, data)

            if status == 423:
                time.sleep(0.1)
                self.queue.put((endpoint, data))
            else:
                printLog(endpoint, {"status": status, "send_data": result})
                printResponse(status, endpoint, result)

    def startHandler(self) -> None:
        for i in range(max(1, self._worker_count)):
            th_handler = Thread(target=self.handler, name=f"main_handler_{i}")
            th_handler.daemon = True
            th_handler.start()
            self._threads.append(th_handler)

    def start(self) -> None:
        """Start receiver and handler threads."""
        self.startReceiver()
        self.startHandler()

    def stop(self, wait: float = 2.0) -> None:
        """Signal threads to stop and wait for them to finish.

        Args:
            wait: maximum seconds to wait for threads to join.
        """
        self._stop_event.set()
        # give threads a chance to exit
        start = time.time()
        for th in self._threads:
            remaining = max(0.0, wait - (time.time() - start))
            th.join(timeout=remaining)

# 外部から参照可能なインスタンスを提供
main_instance = Main(controller_instance=controller, mapping_data=mapping)

if __name__ == "__main__":
    main_instance.startReceiver()
    main_instance.startHandler()

    main_instance.controller.setWatchdogCallback(main_instance.stop)
    main_instance.controller.init()

    # mappingのすべてのstatusをTrueにする
    for key in mapping.keys():
        mapping[key]["status"] = True

    main_instance.start()