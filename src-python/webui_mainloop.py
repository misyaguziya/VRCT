import warnings
warnings.simplefilter('ignore', RuntimeWarning)

import sys
import json
import time
from config import config
import webui_controller as controller

config_mapping = {
    "/config/version": "VERSION",
    "/config/transparency_range": "TRANSPARENCY_RANGE",
    "/config/appearance_theme_list": "APPEARANCE_THEME_LIST",
    "/config/ui_scaling_list": "UI_SCALING_LIST",
    "/config/textbox_ui_scaling_range": "TEXTBOX_UI_SCALING_RANGE",
    "/config/message_box_ratio_range": "MESSAGE_BOX_RATIO_RANGE",
    "/config/selectable_ui_languages_dict": "SELECTABLE_UI_LANGUAGES_DICT",
    "/config/selectable_ctranslate2_weight_type_dict": "SELECTABLE_CTRANSLATE2_WEIGHT_TYPE_DICT",
    "/config/selectable_whisper_weight_type_dict": "SELECTABLE_WHISPER_WEIGHT_TYPE_DICT",
    "/config/max_mic_energy_threshold": "MAX_MIC_ENERGY_THRESHOLD",
    "/config/max_speaker_energy_threshold": "MAX_SPEAKER_ENERGY_THRESHOLD",
    "/config/enable_translation": "ENABLE_TRANSLATION",
    "/config/enable_transcription_send": "ENABLE_TRANSCRIPTION_SEND",
    "/config/enable_transcription_receive": "ENABLE_TRANSCRIPTION_RECEIVE",
    "/config/enable_foreground": "ENABLE_FOREGROUND",
    "/config/source_country": "SOURCE_COUNTRY",
    "/config/source_language": "SOURCE_LANGUAGE",
    "/config/target_country": "TARGET_COUNTRY",
    "/config/target_language": "TARGET_LANGUAGE",
    "/config/choice_input_translator": "CHOICE_INPUT_TRANSLATOR",
    "/config/choice_output_translator": "CHOICE_OUTPUT_TRANSLATOR",
    "/config/is_reset_button_displayed_for_translation": "IS_RESET_BUTTON_DISPLAYED_FOR_TRANSLATION",
    "/config/is_reset_button_displayed_for_whisper": "IS_RESET_BUTTON_DISPLAYED_FOR_WHISPER",
    "/config/selected_tab_no": "SELECTED_TAB_NO",
    "/config/selected_tab_your_translator_engines": "SELECTED_TAB_YOUR_TRANSLATOR_ENGINES",
    "/config/selected_tab_target_translator_engines": "SELECTED_TAB_TARGET_TRANSLATOR_ENGINES",
    "/config/selected_tab_your_languages": "SELECTED_TAB_YOUR_LANGUAGES",
    "/config/selected_tab_target_languages": "SELECTED_TAB_TARGET_LANGUAGES",
    "/config/selected_transcription_engine": "SELECTED_TRANSCRIPTION_ENGINE",
    "/config/is_main_window_sidebar_compact_mode": "IS_MAIN_WINDOW_SIDEBAR_COMPACT_MODE",
    "/config/transparency": "TRANSPARENCY",
    "/config/appearance_theme": "APPEARANCE_THEME",
    "/config/ui_scaling": "UI_SCALING",
    "/config/textbox_ui_scaling": "TEXTBOX_UI_SCALING",
    "/config/message_box_ratio": "MESSAGE_BOX_RATIO",
    "/config/font_family": "FONT_FAMILY",
    "/config/ui_language": "UI_LANGUAGE",
    "/config/enable_restore_main_window_geometry": "ENABLE_RESTORE_MAIN_WINDOW_GEOMETRY",
    "/config/main_window_geometry": "MAIN_WINDOW_GEOMETRY",
    "/config/choice_mic_host": "CHOICE_MIC_HOST",
    "/config/choice_mic_device": "CHOICE_MIC_DEVICE",
    "/config/input_mic_energy_threshold": "INPUT_MIC_ENERGY_THRESHOLD",
    "/config/input_mic_dynamic_energy_threshold": "INPUT_MIC_DYNAMIC_ENERGY_THRESHOLD",
    "/config/input_mic_record_timeout": "INPUT_MIC_RECORD_TIMEOUT",
    "/config/input_mic_phrase_timeout": "INPUT_MIC_PHRASE_TIMEOUT",
    "/config/input_mic_max_phrases": "INPUT_MIC_MAX_PHRASES",
    "/config/input_mic_word_filter": "INPUT_MIC_WORD_FILTER",
    "/config/input_mic_avg_logprob": "INPUT_MIC_AVG_LOGPROB",
    "/config/input_mic_no_speech_prob": "INPUT_MIC_NO_SPEECH_PROB",
    "/config/choice_speaker_device": "CHOICE_SPEAKER_DEVICE",
    "/config/input_speaker_energy_threshold": "INPUT_SPEAKER_ENERGY_THRESHOLD",
    "/config/input_speaker_dynamic_energy_threshold": "INPUT_SPEAKER_DYNAMIC_ENERGY_THRESHOLD",
    "/config/input_speaker_record_timeout": "INPUT_SPEAKER_RECORD_TIMEOUT",
    "/config/input_speaker_phrase_timeout": "INPUT_SPEAKER_PHRASE_TIMEOUT",
    "/config/input_speaker_max_phrases": "INPUT_SPEAKER_MAX_PHRASES",
    "/config/input_speaker_avg_logprob": "INPUT_SPEAKER_AVG_LOGPROB",
    "/config/input_speaker_no_speech_prob": "INPUT_SPEAKER_NO_SPEECH_PROB",
    "/config/osc_ip_address": "OSC_IP_ADDRESS",
    "/config/osc_port": "OSC_PORT",
    "/config/auth_keys": "AUTH_KEYS",
    "/config/use_translation_feature": "USE_TRANSLATION_FEATURE",
    "/config/use_whisper_feature": "USE_WHISPER_FEATURE",
    "/config/ctranslate2_weight_type": "CTRANSLATE2_WEIGHT_TYPE",
    "/config/whisper_weight_type": "WHISPER_WEIGHT_TYPE",
    "/config/enable_auto_clear_message_box": "ENABLE_AUTO_CLEAR_MESSAGE_BOX",
    "/config/enable_send_only_translated_messages": "ENABLE_SEND_ONLY_TRANSLATED_MESSAGES",
    "/config/send_message_button_type": "SEND_MESSAGE_BUTTON_TYPE",
    "/config/enable_notice_xsoverlay": "ENABLE_NOTICE_XSOVERLAY",
    "/config/overlay_settings": "OVERLAY_SETTINGS",
    "/config/enable_overlay_small_log": "ENABLE_OVERLAY_SMALL_LOG",
    "/config/overlay_small_log_settings": "OVERLAY_SMALL_LOG_SETTINGS",
    "/config/overlay_ui_type": "OVERLAY_UI_TYPE",
    "/config/enable_send_message_to_vrc": "ENABLE_SEND_MESSAGE_TO_VRC",
    "/config/send_message_format": "SEND_MESSAGE_FORMAT",
    "/config/send_message_format_with_t": "SEND_MESSAGE_FORMAT_WITH_T",
    "/config/received_message_format": "RECEIVED_MESSAGE_FORMAT",
    "/config/received_message_format_with_t": "RECEIVED_MESSAGE_FORMAT_WITH_T",
    "/config/enable_speaker2chatbox_pass": "ENABLE_SPEAKER2CHATBOX_PASS",
    "/config/enable_send_received_message_to_vrc": "ENABLE_SEND_RECEIVED_MESSAGE_TO_VRC",
    "/config/enable_logger": "ENABLE_LOGGER",
    "/config/enable_vrc_mic_mute_sync": "ENABLE_VRC_MIC_MUTE_SYNC",
    "/config/is_config_window_compact_mode": "IS_CONFIG_WINDOW_COMPACT_MODE",
}

controller_mapping = {
    "/controller/list_language_and_country": controller.getListLanguageAndCountry,
    "/controller/list_mic_host": controller.getListInputHost,
    "/controller/list_mic_device": controller.getListInputDevice,
    "/controller/list_speaker_device": controller.getListOutputDevice,
    "/controller/callback_update_software": controller.callbackUpdateSoftware,
    "/controller/callback_restart_software": controller.callbackRestartSoftware,
    "/controller/callback_filepath_logs": controller.callbackFilepathLogs,
    "/controller/callback_filepath_config_file": controller.callbackFilepathConfigFile,
    # "/controller/callback_enable_easter_egg": controller.callbackEnableEasterEgg,
    "/controller/callback_open_config_window": controller.callbackOpenConfigWindow,
    "/controller/callback_close_config_window": controller.callbackCloseConfigWindow,
    "/controller/callback_enable_main_window_sidebar_compact_mode": controller.callbackEnableMainWindowSidebarCompactMode,
    "/controller/callback_disable_main_window_sidebar_compact_mode": controller.callbackDisableMainWindowSidebarCompactMode,
    "/controller/callback_enable_translation": controller.callbackEnableTranslation,
    "/controller/callback_disable_translation": controller.callbackDisableTranslation,
    "/controller/callback_enable_transcription_send": controller.callbackEnableTranscriptionSend,
    "/controller/callback_disable_transcription_send": controller.callbackDisableTranscriptionSend,
    "/controller/callback_enable_transcription_receive": controller.callbackEnableTranscriptionReceive,
    "/controller/callback_disable_transcription_receive": controller.callbackDisableTranscriptionReceive,
    "/controller/callback_messagebox_press_key_enter": controller.callbackMessageBoxPressKeyEnter,
    "/controller/callback_enable_foreground": controller.callbackEnableForeground,
    "/controller/callback_disable_foreground": controller.callbackDisableForeground,
    "/controller/set_your_language_and_country": controller.setYourLanguageAndCountry,
    "/controller/set_target_language_and_country": controller.setTargetLanguageAndCountry,
    "/controller/swap_your_language_and_target_language": controller.swapYourLanguageAndTargetLanguage,
    "/controller/callback_selected_language_preset_tab": controller.callbackSelectedLanguagePresetTab,
    "/controller/callback_selected_translation_engine": controller.callbackSelectedTranslationEngine,
    "/controller/callback_disable_config_window_compact_mode": controller.callbackEnableConfigWindowCompactMode,
    "/controller/callback_enable_config_window_compact_mode": controller.callbackDisableConfigWindowCompactMode,
    "/controller/callback_set_transparency": controller.callbackSetTransparency,
    "/controller/callback_set_appearance": controller.callbackSetAppearance,
    "/controller/callback_set_ui_scaling": controller.callbackSetUiScaling,
    "/controller/callback_set_textbox_ui_scaling": controller.callbackSetTextboxUiScaling,
    "/controller/callback_set_message_box_ratio": controller.callbackSetMessageBoxRatio,
    "/controller/callback_set_font_family": controller.callbackSetFontFamily,
    "/controller/callback_set_ui_language": controller.callbackSetUiLanguage,
    "/controller/callback_set_enable_restore_main_window_geometry": controller.callbackSetEnableRestoreMainWindowGeometry,
    "/controller/callback_set_use_translation_feature": controller.callbackSetUseTranslationFeature,
    "/controller/callback_set_ctranslate2_weight_type": controller.callbackSetCtranslate2WeightType,
    "/controller/callback_set_deepl_auth_key": controller.callbackSetDeeplAuthKey,
    "/controller/callback_clear_deepl_auth_key": controller.callbackClearDeeplAuthKey,
    "/controller/callback_set_mic_host": controller.callbackSetMicHost,
    "/controller/callback_set_mic_device": controller.callbackSetMicDevice,
    "/controller/callback_set_mic_energy_threshold": controller.callbackSetMicEnergyThreshold,
    "/controller/callback_set_mic_dynamic_energy_threshold": controller.callbackSetMicDynamicEnergyThreshold,
    "/controller/callback_enable_check_mic_threshold": controller.callbackEnableCheckMicThreshold,
    "/controller/callback_disable_check_mic_threshold": controller.callbackDisableCheckMicThreshold,
    "/controller/callback_set_mic_record_timeout": controller.callbackSetMicRecordTimeout,
    "/controller/callback_set_mic_phrase_timeout": controller.callbackSetMicPhraseTimeout,
    "/controller/callback_set_mic_max_phrases": controller.callbackSetMicMaxPhrases,
    "/controller/callback_set_mic_word_filter": controller.callbackSetMicWordFilter,
    "/controller/callback_delete_mic_word_filter": controller.callbackDeleteMicWordFilter,
    "/controller/callback_set_speaker_device": controller.callbackSetSpeakerDevice,
    "/controller/callback_set_speaker_energy_threshold": controller.callbackSetSpeakerEnergyThreshold,
    "/controller/callback_set_speaker_dynamic_energy_threshold": controller.callbackSetSpeakerDynamicEnergyThreshold,
    "/controller/callback_enable_check_speaker_threshold": controller.callbackEnableCheckSpeakerThreshold,
    "/controller/callback_disable_check_speaker_threshold": controller.callbackDisableCheckSpeakerThreshold,
    "/controller/callback_set_speaker_record_timeout": controller.callbackSetSpeakerRecordTimeout,
    "/controller/callback_set_speaker_phrase_timeout": controller.callbackSetSpeakerPhraseTimeout,
    "/controller/callback_set_speaker_max_phrases": controller.callbackSetSpeakerMaxPhrases,
    "/controller/callback_set_use_whisper_feature": controller.callbackSetUserWhisperFeature,
    "/controller/callback_set_whisper_weight_type": controller.callbackSetWhisperWeightType,
    "/controller/callback_set_overlay_settings_opacity": controller.callbackSetOverlaySettingsOpacity,
    "/controller/callback_set_overlay_settings_ui_scaling": controller.callbackSetOverlaySettingsUiScaling,
    "/controller/callback_enable_overlay_small_log": controller.callbackEnableOverlaySmallLog,
    "/controller/callback_disable_overlay_small_log": controller.callbackDisableOverlaySmallLog,
    "/controller/callback_set_overlay_small_log_settings_x_pos": controller.callbackSetOverlaySmallLogSettingsXPos,
    "/controller/callback_set_overlay_small_log_settings_y_pos": controller.callbackSetOverlaySmallLogSettingsYPos,
    "/controller/callback_set_overlay_small_log_settings_z_pos": controller.callbackSetOverlaySmallLogSettingsZPos,
    "/controller/callback_set_overlay_small_log_settings_x_rotation": controller.callbackSetOverlaySmallLogSettingsXRotation,
    "/controller/callback_set_overlay_small_log_settings_y_rotation": controller.callbackSetOverlaySmallLogSettingsYRotation,
    "/controller/callback_set_overlay_small_log_settings_z_rotation": controller.callbackSetOverlaySmallLogSettingsZRotation,
    "/controller/callback_set_enable_auto_clear_chatbox": controller.callbackSetEnableAutoClearMessageBox,
    "/controller/callback_set_send_only_translated_messages": controller.callbackSetEnableSendOnlyTranslatedMessages,
    "/controller/callback_set_send_message_button_type": controller.callbackSetSendMessageButtonType,
    "/controller/callback_enable_notice_xsoverlay": controller.callbackEnableNoticeXsoverlay,
    "/controller/callback_disable_notice_xsoverlay": controller.callbackDisableNoticeXsoverlay,
    "/controller/callback_enable_auto_export_message_logs": controller.callbackEnableAutoExportMessageLogs,
    "/controller/callback_disable_auto_export_message_logs": controller.callbackDisableAutoExportMessageLogs,
    "/controller/callback_enable_vrc_mic_mute_sync": controller.callbackEnableVrcMicMuteSync,
    "/controller/callback_disable_vrc_mic_mute_sync": controller.callbackDisableVrcMicMuteSync,
    "/controller/callback_enable_send_message_to_vrc": controller.callbackEnableSendMessageToVrc,
    "/controller/callback_disable_send_message_to_vrc": controller.callbackDisableSendMessageToVrc,
    "/controller/callback_set_send_message_format": controller.callbackSetSendMessageFormat,
    "/controller/callback_set_send_message_format_with_t": controller.callbackSetSendMessageFormatWithT,
    "/controller/callback_set_received_message_format": controller.callbackSetReceivedMessageFormat,
    "/controller/callback_set_received_message_format_with_t": controller.callbackSetReceivedMessageFormatWithT,
    "/controller/callback_enable_send_received_message_to_vrc": controller.callbackEnableSendReceivedMessageToVrc,
    "/controller/callback_disable_send_received_message_to_vrc": controller.callbackDisableSendReceivedMessageToVrc,
    "/controller/callback_set_osc_ip_address": controller.callbackSetOscIpAddress,
    "/controller/callback_set_osc_port": controller.callbackSetOscPort,
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
    "/controller/callback_disable_transcription_send": {
        "mic":"/action/transcription_send_mic_message_stopped"
        },
    "/controller/callback_enable_transcription_receive": {
        "speaker":"/action/transcription_receive_speaker_message",
        "error_device":"/action/error_device",
        "error_translation_engine":"/action/error_translation_engine",
        },
    "/controller/callback_disable_transcription_receive": {
        "speaker":"/action/transcription_receive_speaker_message_stopped"
        },
    "/controller/callback_enable_check_mic_threshold": {
        "mic":"/action/check_mic_threshold_energy"
        },
    "/controller/callback_messagebox_press_key_enter": {
        "error_translation_engine":"/action/error_translation_engine"
        },
}

def handleConfigRequest(endpoint):
    handler = config_mapping.get(endpoint)
    if handler is None:
        response = "Invalid endpoint"
        status = 404
    else:
        response = getattr(config, handler)
        status = 200
    return response, status

def handleControllerRequest(endpoint, data=None):
    handler = controller_mapping.get(endpoint)
    if handler is None:
        response = "Invalid endpoint"
        status = 404
    else:
        action_endpoint = action_mapping.get(endpoint, None)
        if action_endpoint is not None:
            response = handler(data, Action(action_endpoint).transmit)
        else:
            response = handler(data)
        status = response.get("status", None)
        result = response.get("result", None)
    return result, status

class Action:
    def __init__(self, endpoints:dict) -> None:
        self.endpoints = endpoints

    def transmit(self, key:str, data:dict) -> None:
        status = data.get("status", None)
        result = data.get("result", None)
        response = {
            "endpoint": self.endpoints[key],
            "status": status,
            "result": result,
        }
        response = json.dumps(response)
        print(response, flush=True)

def main():
    received_data = sys.stdin.readline().strip()
    received_data = json.loads(received_data)

    with open('process.log', 'a') as f:
        f.write(f"received_data: {received_data}\n")

    if received_data:
        # response_data = {
        #     "status": 200,
        #     "id": received_data["id"],
        #     "data": received_data["data"],
        # }
        # response = json.dumps(response_data)
        # time.sleep(2)
        # print(response, flush=True)

        endpoint = received_data.get("endpoint", None)
        data = received_data.get("data", None)

        with open('process.log', 'a') as f:
            f.write(f"received_data : endpoint: {endpoint}, data:{data}\n")

        try:
            match endpoint.split("/")[1]:
                case "config":
                    result_data, status = handleConfigRequest(endpoint)
                case "controller":
                    result_data, status = handleControllerRequest(endpoint, data)
                case _:
                    pass
        except Exception as e:
            result_data = str(e)
            status = 500

        response = {
            "status": status,
            "endpoint": endpoint,
            "result": result_data,
        }

        response = json.dumps(response)
        with open('process.log', 'a') as f:
            f.write(f"response: {response}\n")

        print(response, flush=True)

if __name__ == "__main__":
    # endpoint = "/controller/list_mic_host"
    # data = None
    # response_data, status = handleControllerRequest(endpoint, data)
    # response = {
    #     "status": status,
    #     "endpoint": endpoint,
    #     "data": response_data,
    # }
    # response = json.dumps(response)
    # print(response, flush=True)

    try:
        controller.init()
        print(json.dumps({"log": "Initialization from Python."}), flush=True)
        while True:
            main()
    except Exception:
        import traceback
        with open('error.log', 'a') as f:
            traceback.print_exc(file=f)