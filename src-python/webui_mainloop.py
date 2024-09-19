import sys
import json
import time
from config import config
from threading import Thread
from queue import Queue
import webui_controller as controller
from utils import printLog, printResponse, encodeBase64

config_mapping = {
    "/config/version": {"status": True, "variable":"VERSION"},
    "/config/transparency_range": {"status": True, "variable":"TRANSPARENCY_RANGE"},
    "/config/appearance_theme_list": {"status": True, "variable":"APPEARANCE_THEME_LIST"},
    "/config/ui_scaling_list": {"status": True, "variable":"UI_SCALING_LIST"},
    "/config/textbox_ui_scaling_range": {"status": True, "variable":"TEXTBOX_UI_SCALING_RANGE"},
    "/config/message_box_ratio_range": {"status": True, "variable":"MESSAGE_BOX_RATIO_RANGE"},
    "/config/selectable_ctranslate2_weight_type_dict": {"status": True, "variable":"SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT"},
    "/config/selectable_whisper_weight_type_dict": {"status": True, "variable":"SELECTABLE_WHISPER_WEIGHT_TYPE_DICT"},
    "/config/max_mic_energy_threshold": {"status": True, "variable":"MAX_MIC_ENERGY_THRESHOLD"},
    "/config/max_speaker_energy_threshold": {"status": True, "variable":"MAX_SPEAKER_ENERGY_THRESHOLD"},
    # "/config/enable_translation": {"status": True, "variable":"ENABLE_TRANSLATION"},
    # "/config/enable_transcription_send": {"status": True, "variable":"ENABLE_TRANSCRIPTION_SEND"},
    # "/config/enable_transcription_receive": {"status": True, "variable":"ENABLE_TRANSCRIPTION_RECEIVE"},
    # "/config/enable_foreground": {"status": True, "variable":"ENABLE_FOREGROUND"},
    # "/config/is_reset_button_displayed_for_translation": {"status": True, "variable":"IS_RESET_BUTTON_DISPLAYED_FOR_TRANSLATION"},
    # "/config/is_reset_button_displayed_for_whisper": {"status": True, "variable":"IS_RESET_BUTTON_DISPLAYED_FOR_WHISPER"},
    "/config/selected_tab_no": {"status": True, "variable":"SELECTED_TAB_NO"},
    "/config/selected_translator_engines": {"status": False, "variable":"SELECTED_TRANSLATOR_ENGINES"},
    "/config/selected_tab_your_languages": {"status": True, "variable":"SELECTED_TAB_YOUR_LANGUAGES"},
    "/config/selected_tab_target_languages": {"status": True, "variable":"SELECTED_TAB_TARGET_LANGUAGES"},
    "/config/selected_transcription_engine": {"status": False, "variable":"SELECTED_TRANSCRIPTION_ENGINE"},
    "/config/enable_multi_translation": {"status": True, "variable":"ENABLE_MULTI_LANGUAGE_TRANSLATION"},
    "/config/enable_convert_message_to_romaji": {"status": True, "variable":"ENABLE_CONVERT_MESSAGE_TO_ROMAJI"},
    "/config/enable_convert_message_to_hiragana": {"status": True, "variable":"ENABLE_CONVERT_MESSAGE_TO_HIRAGANA"},
    "/config/is_main_window_sidebar_compact_mode": {"status": True, "variable":"IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE"},
    "/config/transparency": {"status": True, "variable":"TRANSPARENCY"},
    "/config/appearance_theme": {"status": True, "variable":"APPEARANCE_THEME"},
    "/config/ui_scaling": {"status": True, "variable":"UI_SCALING"},
    "/config/textbox_ui_scaling": {"status": True, "variable":"TEXTBOX_UI_SCALING"},
    "/config/message_box_ratio": {"status": True, "variable":"MESSAGE_BOX_RATIO"},
    "/config/font_family": {"status": True, "variable":"FONT_FAMILY"},
    "/config/ui_language": {"status": True, "variable":"UI_LANGUAGE"},
    "/config/enable_restore_main_window_geometry": {"status": True, "variable":"ENABLE_RESTORE_MAIN_WINDOW_GEOMETRY"},
    "/config/main_window_geometry": {"status": True, "variable":"MAIN_WINDOW_GEOMETRY"},
    "/config/enable_mic_automatic_selection": {"status": True, "variable":"ENABLE_MIC_AUTOMATIC_SELECTION"},
    "/config/choice_mic_host": {"status": True, "variable":"CHOICE_MIC_HOST"},
    "/config/choice_mic_device": {"status": True, "variable":"CHOICE_MIC_DEVICE"},
    "/config/input_mic_energy_threshold": {"status": True, "variable":"INPUT_MIC_ENERGY_THRESHOLD"},
    "/config/input_mic_dynamic_energy_threshold": {"status": True, "variable":"INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD"},
    "/config/input_mic_record_timeout": {"status": True, "variable":"INPUT_MIC_RECORD_TIMEOUT"},
    "/config/input_mic_phrase_timeout": {"status": True, "variable":"INPUT_MIC_PHRASE_TIMEOUT"},
    "/config/input_mic_max_phrases": {"status": True, "variable":"INPUT_MIC_MAX_PHRASES"},
    "/config/input_mic_word_filter": {"status": True, "variable":"INPUT_MIC_WORD_FILTER"},
    "/config/input_mic_avg_logprob": {"status": True, "variable":"INPUT_MIC_AVG_LOGPROB"},
    "/config/input_mic_no_speech_prob": {"status": True, "variable":"INPUT_MIC_NO_SPEECH_PROB"},
    "/config/enable_speaker_automatic_selection": {"status": True, "variable":"ENABLE_SPEAKER_AUTOMATIC_SELECTION"},
    "/config/choice_speaker_device": {"status": True, "variable":"CHOICE_SPEAKER_DEVICE"},
    "/config/input_speaker_energy_threshold": {"status": True, "variable":"INPUT_SPEAKER_ENERGY_THRESHOLD"},
    "/config/input_speaker_dynamic_energy_threshold": {"status": True, "variable":"INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD"},
    "/config/input_speaker_record_timeout": {"status": True, "variable":"INPUT_SPEAKER_RECORD_TIMEOUT"},
    "/config/input_speaker_phrase_timeout": {"status": True, "variable":"INPUT_SPEAKER_PHRASE_TIMEOUT"},
    "/config/input_speaker_max_phrases": {"status": True, "variable":"INPUT_SPEAKER_MAX_PHRASES"},
    "/config/input_speaker_avg_logprob": {"status": True, "variable":"INPUT_SPEAKER_AVG_LOGPROB"},
    "/config/input_speaker_no_speech_prob": {"status": True, "variable":"INPUT_SPEAKER_NO_SPEECH_PROB"},
    "/config/osc_ip_address": {"status": True, "variable":"OSC_IP_ADDRESS"},
    "/config/osc_port": {"status": True, "variable":"OSC_PORT"},
    "/config/auth_keys": {"status": False, "variable":"AUTH_KEYS"},
    "/config/use_translation_feature": {"status": True, "variable":"USE_TRANSLATION_FEATURE"},
    "/config/use_whisper_feature": {"status": True, "variable":"USE_WHISPER_FEATURE"},
    "/config/ctranslate2_weight_type": {"status": True, "variable":"CTRANSLATE2_WEIGHT_TYPE"},
    "/config/whisper_weight_type": {"status": True, "variable":"WHISPER_WEIGHT_TYPE"},
    "/config/enable_auto_clear_message_box": {"status": True, "variable":"ENABLE_AUTO_CLEAR_MESSAGE_BOX"},
    "/config/enable_send_only_translated_messages": {"status": True, "variable":"ENABLE_SEND_ONLY_TRANSLATED_MESSAGES"},
    "/config/send_message_button_type": {"status": True, "variable":"SEND_MESSAGE_BUTTON_TYPE"},
    "/config/overlay_settings": {"status": True, "variable":"OVERLAY_SETTINGS"},
    "/config/enable_overlay_small_log": {"status": True, "variable":"ENABLE_OVERLAY_SMALL_LOG"},
    "/config/overlay_small_log_settings": {"status": True, "variable":"OVERLAY_SMALL_LOG_SETTINGS"},
    "/config/overlay_ui_type": {"status": True, "variable":"OVERLAY_UI_TYPE"},
    "/config/enable_send_message_to_vrc": {"status": True, "variable":"ENABLE_SEND_MESSAGE_TO_VRC"},
    "/config/send_message_format": {"status": True, "variable":"SEND_MESSAGE_FORMAT"},
    "/config/send_message_format_with_t": {"status": True, "variable":"SEND_MESSAGE_FORMAT_WITH_T"},
    "/config/received_message_format": {"status": True, "variable":"RECEIVED_MESSAGE_FORMAT"},
    "/config/received_message_format_with_t": {"status": True, "variable":"RECEIVED_MESSAGE_FORMAT_WITH_T"},
    "/config/enable_speaker2chatbox_pass": {"status": True, "variable":"ENABLE_SPEAKER2CHATBOX_PASS"},
    "/config/enable_send_received_message_to_vrc": {"status": True, "variable":"ENABLE_SEND_RECEIVED_MESSAGE_TO_VRC"},
    "/config/enable_logger": {"status": True, "variable":"ENABLE_LOGGER"},
    "/config/enable_vrc_mic_mute_sync": {"status": True, "variable":"ENABLE_VRC_MIC_MUTE_SYNC"},
}

controller_mapping = {
    "/controller/list_language_and_country": {"status": True, "variable":controller.getListLanguageAndCountry},
    "/controller/list_mic_host": {"status": True, "variable":controller.getListInputHost},
    "/controller/list_mic_device": {"status": True, "variable":controller.getListInputDevice},
    "/controller/list_speaker_device": {"status": True, "variable":controller.getListOutputDevice},
    # "/controller/callback_update_software": {"status": True, "variable":controller.callbackUpdateSoftware},
    # "/controller/callback_restart_software": {"status": True, "variable":controller.callbackRestartSoftware},
    "/controller/callback_filepath_logs": {"status": True, "variable":controller.callbackFilepathLogs},
    "/controller/callback_filepath_config_file": {"status": True, "variable":controller.callbackFilepathConfigFile},
    # "/controller/callback_enable_easter_egg": {"status": True, "variable":controller.callbackEnableEasterEgg},
    "/controller/callback_open_config_window": {"status": True, "variable":controller.callbackOpenConfigWindow},
    "/controller/callback_close_config_window": {"status": True, "variable":controller.callbackCloseConfigWindow},
    "/controller/callback_enable_multi_language_translation": {"status": True, "variable":controller.callbackEnableMultiLanguageTranslation},
    "/controller/callback_disable_multi_language_translation": {"status": True, "variable":controller.callbackDisableMultiLanguageTranslation},
    "/controller/callback_enable_convert_message_to_romaji": {"status": True, "variable":controller.callbackEnableConvertMessageToRomaji},
    "/controller/callback_disable_convert_message_to_romaji": {"status": True, "variable":controller.callbackDisableConvertMessageToRomaji},
    "/controller/callback_enable_convert_message_to_hiragana": {"status": True, "variable":controller.callbackEnableConvertMessageToHiragana},
    "/controller/callback_disable_convert_message_to_hiragana": {"status": True, "variable":controller.callbackDisableConvertMessageToHiragana},
    "/controller/callback_enable_main_window_sidebar_compact_mode": {"status": True, "variable":controller.callbackEnableMainWindowSidebarCompactMode},
    "/controller/callback_disable_main_window_sidebar_compact_mode": {"status": True, "variable":controller.callbackDisableMainWindowSidebarCompactMode},
    "/controller/callback_enable_translation": {"status": False, "variable":controller.callbackEnableTranslation},
    "/controller/callback_disable_translation": {"status": False, "variable":controller.callbackDisableTranslation},
    "/controller/callback_enable_transcription_send": {"status": False, "variable":controller.callbackEnableTranscriptionSend},
    "/controller/callback_disable_transcription_send": {"status": False, "variable":controller.callbackDisableTranscriptionSend},
    "/controller/callback_enable_transcription_receive": {"status": False, "variable":controller.callbackEnableTranscriptionReceive},
    "/controller/callback_disable_transcription_receive": {"status": False, "variable":controller.callbackDisableTranscriptionReceive},
    "/controller/callback_messagebox_send": {"status": False, "variable":controller.callbackMessageBoxSend},
    "/controller/callback_messagebox_typing": {"status": False, "variable":controller.callbackMessageBoxTyping},
    "/controller/callback_messagebox_typing_stop": {"status": False, "variable":controller.callbackMessageBoxTypingStop},
    "/controller/callback_enable_foreground": {"status": True, "variable":controller.callbackEnableForeground},
    "/controller/callback_disable_foreground": {"status": True, "variable":controller.callbackDisableForeground},
    "/controller/set_your_language_and_country": {"status": True, "variable":controller.setYourLanguageAndCountry},
    "/controller/set_target_language_and_country": {"status": True, "variable":controller.setTargetLanguageAndCountry},
    "/controller/swap_your_language_and_target_language": {"status": True, "variable":controller.swapYourLanguageAndTargetLanguage},
    "/controller/callback_selected_language_preset_tab": {"status": True, "variable":controller.callbackSelectedLanguagePresetTab},
    "/controller/list_translation_engines": {"status": True, "variable":controller.getTranslationEngines},
    "/controller/callback_set_translation_engines": {"status": True, "variable":controller.callbackSetSelectedTranslationEngines},
    "/controller/callback_set_transparency": {"status": True, "variable":controller.callbackSetTransparency},
    "/controller/callback_set_appearance": {"status": True, "variable":controller.callbackSetAppearance},
    "/controller/callback_set_ui_scaling": {"status": True, "variable":controller.callbackSetUiScaling},
    "/controller/callback_set_textbox_ui_scaling": {"status": True, "variable":controller.callbackSetTextboxUiScaling},
    "/controller/callback_set_message_box_ratio": {"status": True, "variable":controller.callbackSetMessageBoxRatio},
    "/controller/callback_set_font_family": {"status": True, "variable":controller.callbackSetFontFamily},
    "/controller/callback_set_ui_language": {"status": True, "variable":controller.callbackSetUiLanguage},
    "/controller/callback_enable_restore_main_window_geometry": {"status": True, "variable":controller.callbackEnableRestoreMainWindowGeometry},
    "/controller/callback_disable_restore_main_window_geometry": {"status": True, "variable":controller.callbackDisableRestoreMainWindowGeometry},
    "/controller/callback_enable_use_translation_feature": {"status": True, "variable":controller.callbackEnableUseTranslationFeature},
    "/controller/callback_disable_use_translation_feature": {"status": True, "variable":controller.callbackDisableUseTranslationFeature},
    "/controller/callback_set_ctranslate2_weight_type": {"status": True, "variable":controller.callbackSetCtranslate2WeightType},
    "/controller/callback_download_ctranslate2_weight": {"status": True, "variable":controller.callbackDownloadCtranslate2Weight},
    "/controller/callback_set_deepl_auth_key": {"status": True, "variable":controller.callbackSetDeeplAuthKey},
    "/controller/callback_clear_deepl_auth_key": {"status": True, "variable":controller.callbackClearDeeplAuthKey},
    "/controller/callback_enable_mic_automatic_selection": {"status": False, "variable":controller.callbackEnableMicAutomaticSelection},
    "/controller/callback_disable_mic_automatic_selection": {"status": False, "variable":controller.callbackDisableMicAutomaticSelection},
    "/controller/callback_set_mic_host": {"status": True, "variable":controller.callbackSetMicHost},
    "/controller/callback_set_mic_device": {"status": True, "variable":controller.callbackSetMicDevice},
    "/controller/callback_set_mic_energy_threshold": {"status": True, "variable":controller.callbackSetMicEnergyThreshold},
    "/controller/callback_enable_mic_dynamic_energy_threshold": {"status": True, "variable":controller.callbackEnableMicDynamicEnergyThreshold},
    "/controller/callback_disable_mic_dynamic_energy_threshold": {"status": True, "variable":controller.callbackDisableMicDynamicEnergyThreshold},
    "/controller/callback_enable_check_mic_threshold": {"status": True, "variable":controller.callbackEnableCheckMicThreshold},
    "/controller/callback_disable_check_mic_threshold": {"status": True, "variable":controller.callbackDisableCheckMicThreshold},
    "/controller/callback_set_mic_record_timeout": {"status": True, "variable":controller.callbackSetMicRecordTimeout},
    "/controller/callback_set_mic_phrase_timeout": {"status": True, "variable":controller.callbackSetMicPhraseTimeout},
    "/controller/callback_set_mic_max_phrases": {"status": True, "variable":controller.callbackSetMicMaxPhrases},
    "/controller/callback_set_mic_word_filter": {"status": False, "variable":controller.callbackSetMicWordFilter},
    "/controller/callback_delete_mic_word_filter": {"status": False, "variable":controller.callbackDeleteMicWordFilter},
    "/controller/callback_enable_speaker_automatic_selection": {"status": False, "variable":controller.callbackEnableSpeakerAutomaticSelection},
    "/controller/callback_disable_speaker_automatic_selection": {"status": False, "variable":controller.callbackDisableSpeakerAutomaticSelection},
    "/controller/callback_set_speaker_device": {"status": True, "variable":controller.callbackSetSpeakerDevice},
    "/controller/callback_set_speaker_energy_threshold": {"status": True, "variable":controller.callbackSetSpeakerEnergyThreshold},
    "/controller/callback_enable_speaker_dynamic_energy_threshold": {"status": True, "variable":controller.callbackEnableSpeakerDynamicEnergyThreshold},
    "/controller/callback_disable_speaker_dynamic_energy_threshold": {"status": True, "variable":controller.callbackDisableSpeakerDynamicEnergyThreshold},
    "/controller/callback_enable_check_speaker_threshold": {"status": True, "variable":controller.callbackEnableCheckSpeakerThreshold},
    "/controller/callback_disable_check_speaker_threshold": {"status": True, "variable":controller.callbackDisableCheckSpeakerThreshold},
    "/controller/callback_set_speaker_record_timeout": {"status": True, "variable":controller.callbackSetSpeakerRecordTimeout},
    "/controller/callback_set_speaker_phrase_timeout": {"status": True, "variable":controller.callbackSetSpeakerPhraseTimeout},
    "/controller/callback_set_speaker_max_phrases": {"status": True, "variable":controller.callbackSetSpeakerMaxPhrases},
    "/controller/callback_enable_use_whisper_feature": {"status": True, "variable":controller.callbackEnableUseWhisperFeature},
    "/controller/callback_disable_use_whisper_feature": {"status": True, "variable":controller.callbackDisableUseWhisperFeature},
    "/controller/callback_set_whisper_weight_type": {"status": True, "variable":controller.callbackSetWhisperWeightType},
    "/controller/callback_download_whisper_weight": {"status": True, "variable":controller.callbackDownloadWhisperWeight},
    "/controller/callback_set_overlay_settings_opacity": {"status": True, "variable":controller.callbackSetOverlaySettingsOpacity},
    "/controller/callback_set_overlay_settings_ui_scaling": {"status": True, "variable":controller.callbackSetOverlaySettingsUiScaling},
    "/controller/callback_enable_overlay_small_log": {"status": True, "variable":controller.callbackEnableOverlaySmallLog},
    "/controller/callback_disable_overlay_small_log": {"status": True, "variable":controller.callbackDisableOverlaySmallLog},
    "/controller/callback_set_overlay_small_log_settings_x_pos": {"status": True, "variable":controller.callbackSetOverlaySmallLogSettingsXPos},
    "/controller/callback_set_overlay_small_log_settings_y_pos": {"status": True, "variable":controller.callbackSetOverlaySmallLogSettingsYPos},
    "/controller/callback_set_overlay_small_log_settings_z_pos": {"status": True, "variable":controller.callbackSetOverlaySmallLogSettingsZPos},
    "/controller/callback_set_overlay_small_log_settings_x_rotation": {"status": True, "variable":controller.callbackSetOverlaySmallLogSettingsXRotation},
    "/controller/callback_set_overlay_small_log_settings_y_rotation": {"status": True, "variable":controller.callbackSetOverlaySmallLogSettingsYRotation},
    "/controller/callback_set_overlay_small_log_settings_z_rotation": {"status": True, "variable":controller.callbackSetOverlaySmallLogSettingsZRotation},
    "/controller/callback_enable_auto_clear_chatbox": {"status": True, "variable":controller.callbackEnableAutoClearMessageBox},
    "/controller/callback_disable_auto_clear_chatbox": {"status": True, "variable":controller.callbackDisableAutoClearMessageBox},
    "/controller/callback_enable_send_only_translated_messages": {"status": True, "variable":controller.callbackEnableSendOnlyTranslatedMessages},
    "/controller/callback_disable_send_only_translated_messages": {"status": True, "variable":controller.callbackDisableSendOnlyTranslatedMessages},
    "/controller/callback_set_send_message_button_type": {"status": True, "variable":controller.callbackSetSendMessageButtonType},
    "/controller/callback_enable_auto_export_message_logs": {"status": True, "variable":controller.callbackEnableAutoExportMessageLogs},
    "/controller/callback_disable_auto_export_message_logs": {"status": True, "variable":controller.callbackDisableAutoExportMessageLogs},
    "/controller/callback_enable_vrc_mic_mute_sync": {"status": False, "variable":controller.callbackEnableVrcMicMuteSync},
    "/controller/callback_disable_vrc_mic_mute_sync": {"status": False, "variable":controller.callbackDisableVrcMicMuteSync},
    "/controller/callback_enable_send_message_to_vrc": {"status": True, "variable":controller.callbackEnableSendMessageToVrc},
    "/controller/callback_disable_send_message_to_vrc": {"status": True, "variable":controller.callbackDisableSendMessageToVrc},
    "/controller/callback_set_send_message_format": {"status": True, "variable":controller.callbackSetSendMessageFormat},
    "/controller/callback_set_send_message_format_with_t": {"status": True, "variable":controller.callbackSetSendMessageFormatWithT},
    "/controller/callback_set_received_message_format": {"status": True, "variable":controller.callbackSetReceivedMessageFormat},
    "/controller/callback_set_received_message_format_with_t": {"status": True, "variable":controller.callbackSetReceivedMessageFormatWithT},
    "/controller/callback_enable_send_received_message_to_vrc": {"status": True, "variable":controller.callbackEnableSendReceivedMessageToVrc},
    "/controller/callback_disable_send_received_message_to_vrc": {"status": True, "variable":controller.callbackDisableSendReceivedMessageToVrc},
    "/controller/callback_enable_logger": {"status": False, "variable":controller.callbackEnableLogger},
    "/controller/callback_disable_logger": {"status": False, "variable":controller.callbackDisableLogger},
    "/controller/callback_set_osc_ip_address": {"status": True, "variable":controller.callbackSetOscIpAddress},
    "/controller/callback_set_osc_port": {"status": True, "variable":controller.callbackSetOscPort},
}

action_mapping = {
    "/controller/callback_update_software": {
        "download":"/action/download_software",
        "update":"/action/update_software"
    },
    "/controller/callback_close_config_window": {
        "mic":"/action/transcription_send_mic_message",
        "speaker":"/action/transcription_receive_speaker_message",
        "error_device":"/action/error_device",
        "error_translation_engine":"/action/error_translation_engine",
        "word_filter":"/action/word_filter",
    },
    "/controller/callback_enable_transcription_send": {
        "mic":"/action/transcription_send_mic_message",
        "error_device":"/action/error_device",
        "error_translation_engine":"/action/error_translation_engine",
        "word_filter":"/action/word_filter",
    },
    "/controller/callback_enable_transcription_receive": {
        "speaker":"/action/transcription_receive_speaker_message",
        "error_device":"/action/error_device",
        "error_translation_engine":"/action/error_translation_engine",
    },
    "/controller/callback_enable_check_mic_threshold": {
        "mic":"/action/check_mic_threshold_energy",
        "error_device":"/action/error_device",
    },
    "/controller/callback_enable_check_speaker_threshold": {
        "speaker":"/action/check_speaker_threshold_energy",
        "error_device":"/action/error_device",
    },
    "/controller/callback_messagebox_send": {
        "error_translation_engine":"/action/error_translation_engine"
    },
    "/controller/callback_download_ctranslate2_weight": {
        "download":"/action/download_ctranslate2_weight"
    },
    "/controller/callback_download_whisper_weight": {
        "download":"/action/download_whisper_weight"
    },
    "/controller/callback_enable_mic_automatic_selection": {
        "mic":"/controller/callback_set_mic_host",
    },
    "/controller/callback_enable_speaker_automatic_selection": {
        "speaker":"/controller/callback_set_speaker_device",
    }
}

class Action:
    def __init__(self, endpoints:dict) -> None:
        self.endpoints = endpoints

    def transmit(self, key:str, data:dict) -> None:
        if key not in self.endpoints:
            printLog("Invalid endpoint", key)
        else:
            status = data.get("status", None)
            result = data.get("result", None)
            printResponse(status, self.endpoints[key], result)

class Main:
    def __init__(self) -> None:
        self.queue_config = Queue()
        self.queue_controller = Queue()

    def receiver(self) -> None:
        while True:
            received_data = sys.stdin.readline().strip()
            received_data = json.loads(received_data)

            if received_data:
                endpoint = received_data.get("endpoint", None)
                data = received_data.get("data", None)
                data = encodeBase64(data) if data is not None else None
                printLog(endpoint, {"receive_data":data})

                match endpoint.split("/")[1]:
                    case "config":
                        self.queue_config.put(endpoint)
                    case "controller":
                        self.queue_controller.put((endpoint, data))
                    case _:
                        pass

    def startReceiver(self) -> None:
        th_receiver = Thread(target=self.receiver)
        th_receiver.daemon = True
        th_receiver.start()

    def handleConfigRequest(self, endpoint):
        handler = config_mapping.get(endpoint)
        if handler is None:
            response = "Invalid endpoint"
            status = 404
        elif handler["status"] is False:
            response = "Locked endpoint"
            status = 423
        else:
            response = getattr(config, handler["variable"])
            status = 200
        return response, status

    def handleControllerRequest(self, endpoint, data=None):
        handler = controller_mapping.get(endpoint)
        if handler is None:
            response = "Invalid endpoint"
            status = 404
        elif handler["status"] is False:
            response = "Locked endpoint"
            status = 423
        else:
            action_endpoint = action_mapping.get(endpoint, None)
            try:
                if action_endpoint is not None:
                    response = handler["variable"](data, Action(action_endpoint).transmit)
                else:
                    response = handler["variable"](data)
                status = response.get("status", None)
                result = response.get("result", None)
            except Exception as e:
                result = str(e)
                status = 500
        return result, status

    def configHandler(self) -> None:
        while True:
            if not self.queue_config.empty():
                endpoint = self.queue_config.get()
                try:
                    result, status = self.handleConfigRequest(endpoint)
                except Exception as e:
                    import traceback
                    with open('error.log', 'a') as f:
                        traceback.print_exc(file=f)
                    result = str(e)
                    status = 500

                if status == 423:
                    self.queue_config.put(endpoint)
                else:
                    printLog(endpoint, {"send_data":result})
                    printResponse(status, endpoint, result)
            time.sleep(0.1)

    def startConfigHandler(self) -> None:
        th_config = Thread(target=self.configHandler)
        th_config.daemon = True
        th_config.start()

    def controllerHandler(self) -> None:
        while True:
            if not self.queue_controller.empty():
                try:
                    endpoint, data = self.queue_controller.get()
                    result, status = self.handleControllerRequest(endpoint, data)
                except Exception as e:
                    import traceback
                    with open('error.log', 'a') as f:
                        traceback.print_exc(file=f)
                    result = str(e)
                    status = 500

                if status == 423:
                    self.queue_controller.put((endpoint, data))
                else:
                    printLog(endpoint, {"send_data":result})
                    printResponse(status, endpoint, result)
            time.sleep(0.1)

    def startControllerHandler(self) -> None:
        th_controller = Thread(target=self.controllerHandler)
        th_controller.daemon = True
        th_controller.start()

    def loop(self) -> None:
        while True:
            time.sleep(1)

if __name__ == "__main__":
    main = Main()
    main.startReceiver()
    main.startConfigHandler()
    main.startControllerHandler()

    controller.init({
        "download_ctranslate2": Action(action_mapping["/controller/callback_download_ctranslate2_weight"]).transmit,
        "download_whisper": Action(action_mapping["/controller/callback_download_whisper_weight"]).transmit,
        "update_selected_mic_device": Action(action_mapping["/controller/callback_enable_mic_automatic_selection"]).transmit,
        "update_selected_speaker_device": Action(action_mapping["/controller/callback_enable_speaker_automatic_selection"]).transmit,
    })

    # mappingのすべてのstatusをTrueにする
    for key in config_mapping.keys():
        config_mapping[key]["status"] = True
    for key in controller_mapping.keys():
        controller_mapping[key]["status"] = True

    process = "test_all"
    match process:
        case "main":
            main.loop()

        case "test":
            for _ in range(100):
                time.sleep(0.5)
                endpoint = "/controller/list_mic_host"
                result, status = main.handleControllerRequest(endpoint)
                printResponse(status, endpoint, result)

        case "test_all":
            import time
            for endpoint, value in config_mapping.items():
                result, status = main.handleConfigRequest(endpoint)
                printResponse(status, endpoint, result)
                time.sleep(0.1)

            for endpoint, value in controller_mapping.items():
                printLog("endpoint", endpoint)

                match endpoint:
                    case  "/controller/callback_messagebox_send":
                        # handleControllerRequest("/controller/callback_enable_translation")
                        # handleControllerRequest("/controller/callback_enable_convert_message_to_romaji")
                        data = {"id":"123456", "message":"テスト"}
                    case "/controller/callback_set_translation_engines":
                        data = {
                            "1":"CTranslate2",
                            "2":"CTranslate2",
                            "3":"CTranslate2",
                        }
                    case "/controller/set_your_language_and_country":
                        data = {
                            "1":{
                                "primary":{
                                "language": "English",
                                "country": "Hong Kong"
                                },
                            },
                            "2":{
                                "primary":{
                                    "language":"Japanese",
                                    "country":"Japan"
                                },
                            },
                            "3":{
                                "primary":{
                                    "language":"Japanese",
                                    "country":"Japan"
                                },
                            },
                        }
                    case "/controller/set_target_language_and_country":
                        data ={
                            "1":{
                                "primary": {
                                    "language": "Japanese",
                                    "country": "Japan"
                                },
                                "secondary": {
                                    "language": "English",
                                    "country": "United States"
                                },
                                "tertiary": {
                                    "language": "Chinese Simplified",
                                    "country": "China"
                                }
                            },
                            "2":{
                                "primary":{
                                    "language":"English",
                                    "country":"United States",
                                },
                                "secondary":{
                                    "language":"English",
                                    "country":"United States"
                                },
                                "tertiary":{
                                    "language":"English",
                                    "country":"United States"
                                },
                            },
                            "3":{
                                "primary":{
                                    "language":"English",
                                    "country":"United States",
                                },
                                "secondary":{
                                    "language":"English",
                                    "country":"United States"
                                },
                                "tertiary":{
                                    "language":"English",
                                    "country":"United States"
                                },
                            },
                        }
                    case "/controller/callback_set_transparency":
                        data = 0.5
                    case "/controller/callback_set_appearance":
                        data = "Dark"
                    case "/controller/callback_set_ui_scaling":
                        data = 1.5
                    case "/controller/callback_set_textbox_ui_scaling":
                        data = 1.5
                    case "/controller/callback_set_message_box_ratio":
                        data = 0.5
                    case "/controller/callback_set_font_family":
                        data = "Yu Gothic UI"
                    case "/controller/callback_set_ui_language":
                        data = "ja"
                    case "/controller/callback_set_ctranslate2_weight_type":
                        data = "Small"
                    case "/controller/callback_set_deepl_auth_key":
                        data = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee:fx"
                    case "/controller/callback_set_mic_host":
                        data = "MME"
                    case "/controller/callback_set_mic_device":
                        data = "マイク (Realtek High Definition Audio)"
                    case "/controller/callback_set_mic_energy_threshold":
                        data = 0.5
                    case "/controller/callback_set_mic_record_timeout":
                        data = 5
                    case "/controller/callback_set_mic_phrase_timeout":
                        data = 5
                    case "/controller/callback_set_mic_max_phrases":
                        data = 5
                    case "/controller/callback_set_mic_word_filter":
                        data = "test0, test1, test2"
                    case "/controller/callback_delete_mic_word_filter":
                        data = "test1"
                    case "/controller/callback_set_speaker_device":
                        data = "スピーカー (Realtek High Definition Audio)"
                    case "/controller/callback_set_speaker_energy_threshold":
                        data = 0.5
                    case "/controller/callback_set_speaker_record_timeout":
                        data = 5
                    case "/controller/callback_set_speaker_phrase_timeout":
                        data = 5
                    case "/controller/callback_set_speaker_max_phrases":
                        data = 5
                    case "/controller/callback_set_whisper_weight_type":
                        data = "base"
                    case "/controller/callback_set_overlay_settings_opacity":
                        data = 0.5
                    case "/controller/callback_set_overlay_settings_ui_scaling":
                        data = 1.5
                    case "/controller/callback_set_overlay_small_log_settings_x_pos":
                        data = 0
                    case "/controller/callback_set_overlay_small_log_settings_y_pos":
                        data = 0
                    case "/controller/callback_set_overlay_small_log_settings_z_pos":
                        data = 0
                    case "/controller/callback_set_overlay_small_log_settings_x_rotation":
                        data = 0
                    case "/controller/callback_set_overlay_small_log_settings_y_rotation":
                        data = 0
                    case "/controller/callback_set_overlay_small_log_settings_z_rotation":
                        data = 0
                    case "/controller/callback_set_send_message_button_type":
                        data = "show"
                    case "/controller/callback_set_send_message_format":
                        data = "[message]"
                    case "/controller/callback_set_send_message_format_with_t":
                        data = "[message]([translation])"
                    case "/controller/callback_set_received_message_format":
                        data = "[message]"
                    case "/controller/callback_set_received_message_format_with_t":
                        data = "[message]([translation])"
                    case "/controller/callback_set_osc_ip_address":
                        data = "127.0.0.1"
                    case "/controller/callback_set_osc_port":
                        data = 8000
                    case _:
                        data = None

                result, status = main.handleControllerRequest(endpoint, data)
                printResponse(status, endpoint, result)
                time.sleep(0.5)