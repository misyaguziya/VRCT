import sys
import json
import time
from threading import Thread
from queue import Queue
import webui_controller as controller
from utils import printLog, printResponse, encodeBase64

mapping = {
    "/get/version": {"status": True, "variable":controller.getVersion},
    "/get/transparency_range": {"status": True, "variable":controller.getTransparencyRange},
    "/get/appearance_theme_list": {"status": True, "variable":controller.getAppearanceThemesList},
    "/get/ui_scaling_list": {"status": True, "variable":controller.getUiScalingList},
    "/get/textbox_ui_scaling_range": {"status": True, "variable":controller.getTextboxUiScalingRange},
    "/get/message_box_ratio_range": {"status": True, "variable":controller.getMessageBoxRatioRange},
    "/get/selectable_ctranslate2_weight_type_dict": {"status": True, "variable":controller.getSelectableCtranslate2WeightTypeDict},
    "/get/selectable_whisper_weight_type_dict": {"status": True, "variable":controller.getSelectableWhisperModelTypeDict},
    "/get/max_mic_energy_threshold": {"status": True, "variable":controller.getMaxMicEnergyThreshold},
    "/get/max_speaker_energy_threshold": {"status": True, "variable":controller.getMaxSpeakerEnergyThreshold},

    "/set/enable_translation": {"status": False, "variable":controller.setEnableTranslation},
    "/set/disable_translation": {"status": False, "variable":controller.setDisableTranslation},

    "/set/enable_foreground": {"status": True, "variable":controller.setEnableForeground},
    "/set/disable_foreground": {"status": True, "variable":controller.setDisableForeground},

    "/set/enable_config_window": {"status": True, "variable":controller.setEnableConfigWindow},
    "/set/disable_config_window": {"status": True, "variable":controller.setDisableConfigWindow},

    "/get/selected_tab_no": {"status": True, "variable":controller.getSelectedTabNo},
    "/set/selected_tab_no": {"status": True, "variable":controller.setSelectedTabNo},

    "/get/list_translation_engines": {"status": True, "variable":controller.getTranslationEngines},
    "/get/list_languages": {"status": True, "variable":controller.getListLanguageAndCountry},
    "/get/list_mic_host": {"status": True, "variable":controller.getListInputHost},
    "/get/list_mic_device": {"status": True, "variable":controller.getListInputDevice},
    "/get/list_speaker_device": {"status": True, "variable":controller.getListOutputDevice},

    "/get/selected_translator_engines": {"status": False, "variable":controller.getSelectedTranslatorEngines},
    "/set/selected_translator_engines": {"status": True, "variable":controller.setSelectedTranslatorEngines},

    "/get/selected_your_languages": {"status": True, "variable":controller.getSelectedYourLanguages},
    "/set/selected_your_languages": {"status": True, "variable":controller.setSelectedYourLanguages},

    "/get/selected_target_languages": {"status": True, "variable":controller.getSelectedTargetLanguages},
    "/set/selected_target_languages": {"status": True, "variable":controller.setSelectedTargetLanguages},

    "/get/selected_transcription_engine": {"status": False, "variable":controller.getSelectedTranscriptionEngine},

    "/get/multi_language_translation": {"status": True, "variable":controller.getMultiLanguageTranslation},
    "/set/enable_multi_language_translation": {"status": True, "variable":controller.setEnableMultiLanguageTranslation},
    "/set/disable_multi_language_translation": {"status": True, "variable":controller.setDisableMultiLanguageTranslation},

    "/get/convert_message_to_romaji": {"status": True, "variable":controller.getConvertMessageToRomaji},
    "/set/enable_convert_message_to_romaji": {"status": True, "variable":controller.setEnableConvertMessageToRomaji},
    "/set/disable_convert_message_to_romaji": {"status": True, "variable":controller.setDisableConvertMessageToRomaji},

    "/get/convert_message_to_hiragana": {"status": True, "variable":controller.getConvertMessageToHiragana},
    "/set/enable_convert_message_to_hiragana": {"status": True, "variable":controller.setEnableConvertMessageToHiragana},
    "/set/disable_convert_message_to_hiragana": {"status": True, "variable":controller.setDisableConvertMessageToHiragana},

    "/get/main_window_sidebar_compact_mode": {"status": True, "variable":controller.getMainWindowSidebarCompactMode},
    "/set/enable_main_window_sidebar_compact_mode": {"status": True, "variable":controller.setEnableMainWindowSidebarCompactMode},
    "/set/disable_main_window_sidebar_compact_mode": {"status": True, "variable":controller.setDisableMainWindowSidebarCompactMode},

    "/get/transparency": {"status": True, "variable":controller.getTransparency},
    "/set/transparency": {"status": True, "variable":controller.setTransparency},

    "/get/appearance_theme": {"status": True, "variable":controller.getAppearanceTheme},
    "/set/appearance_theme": {"status": True, "variable":controller.setAppearanceTheme},

    "/get/ui_scaling": {"status": True, "variable":controller.getUiScaling},
    "/set/ui_scaling": {"status": True, "variable":controller.setUiScaling},

    "/get/textbox_ui_scaling": {"status": True, "variable":controller.getTextboxUiScaling},
    "/set/textbox_ui_scaling": {"status": True, "variable":controller.setTextboxUiScaling},

    "/get/message_box_ratio": {"status": True, "variable":controller.getMessageBoxRatio},
    "/set/message_box_ratio": {"status": True, "variable":controller.setMessageBoxRatio},

    "/get/font_family": {"status": True, "variable":controller.getFontFamily},
    "/set/font_family": {"status": True, "variable":controller.setFontFamily},

    "/get/ui_language": {"status": True, "variable":controller.getUiLanguage},
    "/set/ui_language": {"status": True, "variable":controller.setUiLanguage},

    "/get/restore_main_window_geometry": {"status": True, "variable":controller.getRestoreMainWindowGeometry},
    "/set/enable_restore_main_window_geometry": {"status": True, "variable":controller.setEnableRestoreMainWindowGeometry},
    "/set/disable_restore_main_window_geometry": {"status": True, "variable":controller.setDisableRestoreMainWindowGeometry},

    "/get/main_window_geometry": {"status": True, "variable":controller.getMainWindowGeometry},
    "/set/main_window_geometry": {"status": True, "variable":controller.setMainWindowGeometry},

    "/get/auto_mic_select": {"status": True, "variable":controller.getAutoMicSelect},
    "/set/enable_auto_mic_select": {"status": True, "variable":controller.setEnableAutoMicSelect},
    "/set/disable_auto_mic_select": {"status": True, "variable":controller.setDisableAutoMicSelect},

    "/get/selected_mic_host": {"status": True, "variable":controller.getSelectedMicHost},
    "/set/selected_mic_host": {"status": True, "variable":controller.setSelectedMicHost},

    "/get/selected_mic_device": {"status": True, "variable":controller.getSelectedMicDevice},
    "/set/selected_mic_device": {"status": True, "variable":controller.setSelectedMicDevice},

    "/get/mic_energy_threshold": {"status": True, "variable":controller.getMicEnergyThreshold},
    "/set/mic_energy_threshold": {"status": True, "variable":controller.setMicEnergyThreshold},

    "/get/mic_dynamic_energy_threshold": {"status": True, "variable":controller.getMicDynamicEnergyThreshold},
    "/set/enable_mic_dynamic_energy_threshold": {"status": True, "variable":controller.setEnableMicDynamicEnergyThreshold},
    "/set/disable_mic_dynamic_energy_threshold": {"status": True, "variable":controller.setDisableMicDynamicEnergyThreshold},

    "/get/mic_record_timeout": {"status": True, "variable":controller.getMicRecordTimeout},
    "/set/mic_record_timeout": {"status": True, "variable":controller.setMicRecordTimeout},

    "/get/mic_phrase_timeout": {"status": True, "variable":controller.getMicPhraseTimeout},
    "/set/mic_phrase_timeout": {"status": True, "variable":controller.setMicPhraseTimeout},

    "/get/mic_max_phrases": {"status": True, "variable":controller.getMicMaxPhrases},
    "/set/mic_max_phrases": {"status": True, "variable":controller.setMicMaxPhrases},

    "/get/mic_word_filter": {"status": True, "variable":controller.getMicWordFilter},
    "/set/mic_word_filter": {"status": True, "variable":controller.setMicWordFilter},
    "/del/mic_word_filter": {"status": True, "variable":controller.delMicWordFilter},

    "/get/mic_avg_logprob": {"status": True, "variable":controller.getMicAvgLogprob},
    "/set/mic_avg_logprob": {"status": True, "variable":controller.setMicAvgLogprob},

    "/get/mic_no_speech_prob": {"status": True, "variable":controller.getMicNoSpeechProb},
    "/set/mic_no_speech_prob": {"status": True, "variable":controller.setMicNoSpeechProb},

    "/get/auto_speaker_select": {"status": True, "variable":controller.getAutoSpeakerSelect},
    "/set/enable_auto_speaker_select": {"status": True, "variable":controller.setEnableAutoSpeakerSelect},
    "/set/disable_auto_speaker_select": {"status": True, "variable":controller.setDisableAutoSpeakerSelect},

    "/get/selected_speaker_device": {"status": True, "variable":controller.getSelectedSpeakerDevice},
    "/set/selected_speaker_device": {"status": True, "variable":controller.setSelectedSpeakerDevice},

    "/get/speaker_energy_threshold": {"status": True, "variable":controller.getSpeakerEnergyThreshold},
    "/set/speaker_energy_threshold": {"status": True, "variable":controller.setSpeakerEnergyThreshold},

    "/get/speaker_dynamic_energy_threshold": {"status": True, "variable":controller.getSpeakerDynamicEnergyThreshold},
    "/set/enable_speaker_dynamic_energy_threshold": {"status": True, "variable":controller.setEnableSpeakerDynamicEnergyThreshold},
    "/set/disable_speaker_dynamic_energy_threshold": {"status": True, "variable":controller.setDisableSpeakerDynamicEnergyThreshold},

    "/get/speaker_record_timeout": {"status": True, "variable":controller.getSpeakerRecordTimeout},
    "/set/speaker_record_timeout": {"status": True, "variable":controller.setSpeakerRecordTimeout},

    "/get/speaker_phrase_timeout": {"status": True, "variable":controller.getSpeakerPhraseTimeout},
    "/set/speaker_phrase_timeout": {"status": True, "variable":controller.setSpeakerPhraseTimeout},

    "/get/speaker_max_phrases": {"status": True, "variable":controller.getSpeakerMaxPhrases},
    "/set/speaker_max_phrases": {"status": True, "variable":controller.setSpeakerMaxPhrases},

    "/get/speaker_avg_logprob": {"status": True, "variable":controller.getSpeakerAvgLogprob},
    "/set/speaker_avg_logprob": {"status": True, "variable":controller.setSpeakerAvgLogprob},

    "/get/speaker_no_speech_prob": {"status": True, "variable":controller.getSpeakerNoSpeechProb},
    "/set/speaker_no_speech_prob": {"status": True, "variable":controller.setSpeakerNoSpeechProb},

    "/get/osc_ip_address": {"status": True, "variable":controller.getOscIpAddress},
    "/set/osc_ip_address": {"status": True, "variable":controller.setOscIpAddress},

    "/get/osc_port": {"status": True, "variable":controller.getOscPort},
    "/set/osc_port": {"status": True, "variable":controller.setOscPort},

    "/get/deepl_auth_key": {"status": False, "variable":controller.getDeepLAuthKey},
    "/set/deepl_auth_key": {"status": False, "variable":controller.setDeeplAuthKey},
    "/del/deepl_auth_key": {"status": False, "variable":controller.delDeeplAuthKey},

    "/get/use_translation_feature": {"status": True, "variable":controller.getUseTranslationFeature},
    "/set/enable_use_translation_feature": {"status": True, "variable":controller.setEnableUseTranslationFeature},
    "/set/disable_use_translation_feature": {"status": True, "variable":controller.setDisableUseTranslationFeature},

    "/get/use_whisper_feature": {"status": True, "variable":controller.getUseWhisperFeature},
    "/set/enable_use_whisper_feature": {"status": True, "variable":controller.setEnableUseWhisperFeature},
    "/set/disable_use_whisper_feature": {"status": True, "variable":controller.setDisableUseWhisperFeature},

    "/get/ctranslate2_weight_type": {"status": True, "variable":controller.getCtranslate2WeightType},
    "/set/ctranslate2_weight_type": {"status": True, "variable":controller.setCtranslate2WeightType},

    "/get/whisper_weight_type": {"status": True, "variable":controller.getWhisperWeightType},
    "/set/whisper_weight_type": {"status": True, "variable":controller.setWhisperWeightType},

    "/get/auto_clear_message_box": {"status": True, "variable":controller.getAutoClearMessageBox},
    "/set/enable_auto_clear_message_box": {"status": True, "variable":controller.setEnableAutoClearMessageBox},
    "/set/disable_auto_clear_message_box": {"status": True, "variable":controller.setDisableAutoClearMessageBox},

    "/get/send_only_translated_messages": {"status": True, "variable":controller.getSendOnlyTranslatedMessages},
    "/set/enable_send_only_translated_messages": {"status": True, "variable":controller.setEnableSendOnlyTranslatedMessages},
    "/set/disable_send_only_translated_messages": {"status": True, "variable":controller.setDisableSendOnlyTranslatedMessages},

    "/get/send_message_button_type": {"status": True, "variable":controller.getSendMessageButtonType},
    "/set/send_message_button_type": {"status": True, "variable":controller.setSendMessageButtonType},

    "/get/overlay_settings": {"status": True, "variable":controller.getOverlaySettings},
    "/set/overlay_settings": {"status": True, "variable":controller.setOverlaySettings},

    "/get/overlay_small_log_settings": {"status": True, "variable":controller.getOverlaySmallLogSettings},
    "/set/overlay_small_log_settings": {"status": True, "variable":controller.setOverlaySmallLogSettings},

    "/get/overlay_small_log": {"status": True, "variable":controller.getOverlaySmallLog},
    "/set/enable_overlay_small_log": {"status": True, "variable":controller.setEnableOverlaySmallLog},
    "/set/disable_overlay_small_log": {"status": True, "variable":controller.setDisableOverlaySmallLog},

    "/get/send_message_to_vrc": {"status": True, "variable":controller.getSendMessageToVrc},
    "/set/enable_send_message_to_vrc": {"status": True, "variable":controller.setEnableSendMessageToVrc},
    "/set/disable_send_message_to_vrc": {"status": True, "variable":controller.setDisableSendMessageToVrc},

    "/get/send_message_format": {"status": True, "variable":controller.getSendMessageFormat},
    "/set/send_message_format": {"status": True, "variable":controller.setSendMessageFormat},

    "/get/send_message_format_with_t": {"status": True, "variable":controller.getSendMessageFormatWithT},
    "/set/send_message_format_with_t": {"status": True, "variable":controller.setSendMessageFormatWithT},

    "/get/received_message_format": {"status": True, "variable":controller.getReceivedMessageFormat},
    "/set/received_message_format": {"status": True, "variable":controller.setReceivedMessageFormat},

    "/get/received_message_format_with_t": {"status": True, "variable":controller.getReceivedMessageFormatWithT},
    "/set/received_message_format_with_t": {"status": True, "variable":controller.setReceivedMessageFormatWithT},

    "/get/speaker2chatbox_pass": {"status": True, "variable":controller.getSpeaker2ChatboxPass},
    "/set/speaker2chatbox_pass": {"status": True, "variable":controller.setSpeaker2ChatboxPass},

    "/get/send_received_message_to_vrc": {"status": True, "variable":controller.getSendReceivedMessageToVrc},
    "/set/enable_send_received_message_to_vrc": {"status": True, "variable":controller.setEnableSendReceivedMessageToVrc},
    "/set/disable_send_received_message_to_vrc": {"status": True, "variable":controller.setDisableSendReceivedMessageToVrc},

    "/get/logger": {"status": True, "variable":controller.getLogger},
    "/set/enable_logger": {"status": True, "variable":controller.setEnableLogger},
    "/set/disable_logger": {"status": True, "variable":controller.setDisableLogger},

    "/get/vrc_mic_mute_sync": {"status": True, "variable":controller.getVrcMicMuteSync},
    "/set/enable_vrc_mic_mute_sync": {"status": True, "variable":controller.setEnableVrcMicMuteSync},
    "/set/disable_vrc_mic_mute_sync": {"status": True, "variable":controller.setDisableVrcMicMuteSync},

    "/set/enable_check_mic_threshold": {"status": True, "variable":controller.setEnableCheckMicThreshold},
    "/set/disable_check_mic_threshold": {"status": True, "variable":controller.setDisableCheckMicThreshold},

    "/set/enable_check_speaker_threshold": {"status": True, "variable":controller.setEnableCheckSpeakerThreshold},
    "/set/disable_check_speaker_threshold": {"status": True, "variable":controller.setDisableCheckSpeakerThreshold},

    # "/run/update_software": {"status": True, "variable":controller.updateSoftware},
    # "/run/restart_software": {"status": True, "variable":controller.restartSoftware},

    "/run/open_filepath_logs": {"status": True, "variable":controller.openFilepathLogs},
    "/run/open_filepath_config_file": {"status": True, "variable":controller.openFilepathConfigFile},

    "/set/enable_transcription_send": {"status": False, "variable":controller.setEnableTranscriptionSend},
    "/set/disable_transcription_send": {"status": False, "variable":controller.setDisableTranscriptionSend},

    "/set/enable_transcription_receive": {"status": False, "variable":controller.setEnableTranscriptionReceive},
    "/set/disable_transcription_receive": {"status": False, "variable":controller.setDisableTranscriptionReceive},

    "/run/send_message_box": {"status": False, "variable":controller.sendMessageBox},
    "/run/typing_message_box": {"status": False, "variable":controller.typingMessageBox},
    "/run/stop_typing_message_box": {"status": False, "variable":controller.stopTypingMessageBox},

    "/run/swap_your_language_and_target_language": {"status": True, "variable":controller.swapYourLanguageAndTargetLanguage},
    "/run/download_ctranslate2_weight": {"status": True, "variable":controller.downloadCtranslate2Weight},
    "/run/download_whisper_weight": {"status": True, "variable":controller.downloadWhisperWeight},
}

action_mapping = {
    "/run/update_software": {
        "download":"/action/download_software",
        "update":"/action/update_software"
    },
    "/set/disable_config_window": {
        "mic":"/action/transcription_send_mic_message",
        "speaker":"/action/transcription_receive_speaker_message",
        "error_device":"/action/error_device",
        "error_translation_engine":"/action/error_translation_engine",
        "word_filter":"/action/word_filter",
    },
    "/set/enable_transcription_send": {
        "mic":"/action/transcription_send_mic_message",
        "error_device":"/action/error_device",
        "error_translation_engine":"/action/error_translation_engine",
        "word_filter":"/action/word_filter",
    },
    "/set/enable_transcription_receive": {
        "speaker":"/action/transcription_receive_speaker_message",
        "error_device":"/action/error_device",
        "error_translation_engine":"/action/error_translation_engine",
    },
    "/set/enable_check_mic_threshold": {
        "mic":"/action/check_mic_threshold_energy",
        "error_device":"/action/error_device",
    },
    "/set/enable_check_speaker_threshold": {
        "speaker":"/action/check_speaker_threshold_energy",
        "error_device":"/action/error_device",
    },
    "/run/send_message_box": {
        "error_translation_engine":"/action/error_translation_engine"
    },
    "/run/download_ctranslate2_weight": {
        "download":"/action/download_ctranslate2_weight"
    },
    "/run/download_whisper_weight": {
        "download":"/action/download_whisper_weight"
    },
    "/set/enable_auto_mic_select": {
        "mic":"/set/selected_mic_host",
    },
    "/set/enable_auto_speaker_select": {
        "speaker":"/set/selected_speaker_device",
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
        self.queue = Queue()

    def receiver(self) -> None:
        while True:
            received_data = sys.stdin.readline().strip()
            received_data = json.loads(received_data)

            if received_data:
                endpoint = received_data.get("endpoint", None)
                data = received_data.get("data", None)
                data = encodeBase64(data) if data is not None else None
                printLog(endpoint, {"receive_data":data})
                self.queue.put((endpoint, data))

    def startReceiver(self) -> None:
        th_receiver = Thread(target=self.receiver)
        th_receiver.daemon = True
        th_receiver.start()

    def handleRequest(self, endpoint, data=None):
        handler = mapping.get(endpoint)
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

    def handler(self) -> None:
        while True:
            if not self.queue.empty():
                try:
                    endpoint, data = self.queue.get()
                    result, status = self.handleRequest(endpoint, data)
                except Exception as e:
                    import traceback
                    with open('error.log', 'a') as f:
                        traceback.print_exc(file=f)
                    result = str(e)
                    status = 500

                if status == 423:
                    self.queue.put((endpoint, data))
                else:
                    printLog(endpoint, {"send_data":result})
                    printResponse(status, endpoint, result)
            time.sleep(0.1)

    def startHandler(self) -> None:
        th_handler = Thread(target=self.handler)
        th_handler.daemon = True
        th_handler.start()

    def loop(self) -> None:
        while True:
            time.sleep(1)

if __name__ == "__main__":
    main = Main()
    main.startReceiver()
    main.startHandler()

    controller.init({
        "download_ctranslate2": Action(action_mapping["/run/download_ctranslate2_weight"]).transmit,
        "download_whisper": Action(action_mapping["/run/download_whisper_weight"]).transmit,
        "update_selected_mic_device": Action(action_mapping["/set/enable_auto_mic_select"]).transmit,
        "update_selected_speaker_device": Action(action_mapping["/set/enable_auto_speaker_select"]).transmit,
    })

    # mappingのすべてのstatusをTrueにする
    for key in mapping.keys():
        mapping[key]["status"] = True

    process = "main"
    match process:
        case "main":
            main.loop()

        case "test":
            for _ in range(100):
                time.sleep(0.5)
                endpoint = "/get/list_mic_host"
                result, status = main.handleRequest(endpoint)
                printResponse(status, endpoint, result)

        case "test_all":
            import time
            for endpoint, value in mapping.items():
                printLog("endpoint", endpoint)

                match endpoint:
                    case  "/run/send_message_box":
                        # handleRequest("/set/enable_translation")
                        # handleRequest("/set/enable_convert_message_to_romaji")
                        data = {"id":"123456", "message":"テスト"}
                    case "/set/selected_translator_engines":
                        data = {
                            "1":"CTranslate2",
                            "2":"CTranslate2",
                            "3":"CTranslate2",
                        }
                    case "/set/selected_your_languages":
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
                    case "/set/selected_target_languages":
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
                    case "/set/transparency":
                        data = 0.5
                    case "/set/appearance":
                        data = "Dark"
                    case "/set/ui_scaling":
                        data = 1.5
                    case "/set/textbox_ui_scaling":
                        data = 1.5
                    case "/set/message_box_ratio":
                        data = 0.5
                    case "/set/font_family":
                        data = "Yu Gothic UI"
                    case "/set/ui_language":
                        data = "ja"
                    case "/set/ctranslate2_weight_type":
                        data = "Small"
                    case "/set/deepl_auth_key":
                        data = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee:fx"
                    case "/set/selected_mic_host":
                        data = "MME"
                    case "/set/selected_mic_device":
                        data = "マイク (Realtek High Definition Audio)"
                    case "/set/mic_energy_threshold":
                        data = 0.5
                    case "/set/mic_record_timeout":
                        data = 1
                    case "/set/mic_phrase_timeout":
                        data = 5
                    case "/set/input_set_mic_max_phrases":
                        data = 5
                    case "/set/mic_word_filter":
                        data = "test0, test1, test2"
                    case "/del/mic_word_filter":
                        data = "test1"
                    case "/set/selected_speaker_device":
                        data = "スピーカー (Realtek High Definition Audio)"
                    case "/set/speaker_energy_threshold":
                        data = 0.5
                    case "/set/speaker_record_timeout":
                        data = 5
                    case "/set/speaker_phrase_timeout":
                        data = 5
                    case "/set/speaker_max_phrases":
                        data = 5
                    case "/set/whisper_weight_type":
                        data = "base"
                    case "/set/overlay_settings":
                        data = {
                            "opacity": 0.5,
                            "ui_scaling": 1.5,
                        }
                    case "/set/overlay_small_log_settings":
                        data = {
                            "x_pos": 0,
                            "y_pos": 0,
                            "z_pos": 0,
                            "x_rotation": 0,
                            "y_rotation": 0,
                            "z_rotation": 0,
                            "display_duration": 5,
                            "fadeout_duration": 0.5,
                        }
                    case "/set/send_message_button_type":
                        data = "show"
                    case "/set/send_message_format":
                        data = "[message]"
                    case "/set/send_message_format_with_t":
                        data = "[message]([translation])"
                    case "/set/received_message_format":
                        data = "[message]"
                    case "/set/received_message_format_with_t":
                        data = "[message]([translation])"
                    case "/set/osc_ip_address":
                        data = "127.0.0.1"
                    case "/set/osc_port":
                        data = 8000
                    case "/set/speaker_no_speech_prob":
                        data = 0.5
                    case "/set/speaker_avg_logprob":
                        data = 0.5
                    case "/set/mic_no_speech_prob":
                        data = 0.5
                    case "/set/mic_avg_logprob":
                        data = 0.5
                    case "/set/mic_max_phrases":
                        data = 5
                    case _:
                        data = None

                result, status = main.handleRequest(endpoint, data)
                printResponse(status, endpoint, result)
                time.sleep(0.5)