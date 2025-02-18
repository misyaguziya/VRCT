import sys
import json
import time
from typing import Any
from threading import Thread
from queue import Queue
from controller import Controller
from utils import printLog, printResponse, errorLogging, encodeBase64

run_mapping = {
    "connected_network":"/run/connected_network",
    "enable_ai_models":"/run/enable_ai_models",

    "transcription_mic":"/run/transcription_send_mic_message",
    "transcription_speaker":"/run/transcription_receive_speaker_message",

    "check_mic_volume":"/run/check_mic_volume",
    "check_speaker_volume":"/run/check_speaker_volume",

    "error_device":"/run/error_device",
    "error_translation_engine":"/run/error_translation_engine",
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

    "mic_host_list":"/run/mic_host_list",
    "mic_device_list":"/run/mic_device_list",
    "speaker_device_list":"/run/speaker_device_list",

    "update_software_flag":"/run/update_software_flag",

    "initialization_progress":"/run/initialization_progress",
    "initialization_complete":"/run/initialization_complete",
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

    "/run/download_ctranslate2_weight": {"status": True, "variable":controller.downloadCtranslate2Weight},

    "/get/data/deepl_auth_key": {"status": False, "variable":controller.getDeepLAuthKey},
    "/set/data/deepl_auth_key": {"status": False, "variable":controller.setDeeplAuthKey},
    "/delete/data/deepl_auth_key": {"status": False, "variable":controller.delDeeplAuthKey},

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
    "/get/data/auto_clear_message_box": {"status": True, "variable":controller.getAutoClearMessageBox},
    "/set/enable/auto_clear_message_box": {"status": True, "variable":controller.setEnableAutoClearMessageBox},
    "/set/disable/auto_clear_message_box": {"status": True, "variable":controller.setDisableAutoClearMessageBox},

    "/get/data/send_only_translated_messages": {"status": True, "variable":controller.getSendOnlyTranslatedMessages},
    "/set/enable/send_only_translated_messages": {"status": True, "variable":controller.setEnableSendOnlyTranslatedMessages},
    "/set/disable/send_only_translated_messages": {"status": True, "variable":controller.setDisableSendOnlyTranslatedMessages},

    "/get/data/send_message_button_type": {"status": True, "variable":controller.getSendMessageButtonType},
    "/set/data/send_message_button_type": {"status": True, "variable":controller.setSendMessageButtonType},

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

class Main:
    def __init__(self) -> None:
        self.queue = Queue()
        self.main_loop = True

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

    def handleRequest(self, endpoint, data=None) -> tuple:
        handler = mapping.get(endpoint)
        if handler is None:
            response = "Invalid endpoint"
            status = 404
        elif handler["status"] is False:
            response = "Locked endpoint"
            status = 423
        else:
            try:
                response = handler["variable"](data)
                status = response.get("status", None)
                result = response.get("result", None)
            except Exception as e:
                errorLogging()
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
                    errorLogging()
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

    def start(self) -> None:
        while self.main_loop:
            time.sleep(1)

    def stop(self) -> None:
        self.main_loop = False

if __name__ == "__main__":
    main = Main()
    main.startReceiver()
    main.startHandler()

    controller.setWatchdogCallback(main.stop)
    controller.init()

    # mappingのすべてのstatusをTrueにする
    for key in mapping.keys():
        mapping[key]["status"] = True

    process = "main"
    match process:
        case "main":
            main.start()

        case "test":
            for _ in range(100):
                time.sleep(0.5)
                endpoint = "/get/data/mic_host_list"
                result, status = main.handleRequest(endpoint)
                printResponse(status, endpoint, result)

        case "test_all":
            import time
            for endpoint, value in mapping.items():
                printLog("endpoint", endpoint)

                match endpoint:
                    case  "/run/send_message_box":
                        # handleRequest("/set/enable/translation")
                        # handleRequest("/set/enable/convert_message_to_romaji")
                        data = {"id":"123456", "message":"テスト"}
                    case "/set/data/selected_translation_engines":
                        data = {
                            "1":"CTranslate2",
                            "2":"CTranslate2",
                            "3":"CTranslate2",
                        }
                    case "/set/data/selected_your_languages":
                        data = {
                            "1":{
                                "1":{
                                "language": "English",
                                "country": "Hong Kong"
                                },
                            },
                            "2":{
                                "1":{
                                    "language":"Japanese",
                                    "country":"Japan"
                                },
                            },
                            "3":{
                                "1":{
                                    "language":"Japanese",
                                    "country":"Japan"
                                },
                            },
                        }
                    case "/set/data/selected_target_languages":
                        data ={
                            "1":{
                                "1": {
                                    "language": "Japanese",
                                    "country": "Japan",
                                    "enabled": True,
                                },
                                "secondary": {
                                    "language": "English",
                                    "country": "United States",
                                    "enabled": True,
                                },
                                "tertiary": {
                                    "language": "Chinese Simplified",
                                    "country": "China",
                                    "enabled": True,
                                }
                            },
                            "2":{
                                "1":{
                                    "language":"English",
                                    "country":"United States",
                                    "enabled": True,
                                },
                                "secondary":{
                                    "language":"English",
                                    "country":"United States",
                                    "enabled": True,
                                },
                                "tertiary":{
                                    "language":"English",
                                    "country":"United States",
                                    "enabled": True,
                                },
                            },
                            "3":{
                                "1":{
                                    "language":"English",
                                    "country":"United States",
                                    "enabled": True,
                                },
                                "secondary":{
                                    "language":"English",
                                    "country":"United States",
                                    "enabled": True,
                                },
                                "tertiary":{
                                    "language":"English",
                                    "country":"United States",
                                    "enabled": True,
                                },
                            },
                        }
                    case "/set/data/transparency":
                        data = 0.5
                    case "/set/appearance":
                        data = "Dark"
                    case "/set/data/ui_scaling":
                        data = 1.5
                    case "/set/data/appearance_theme":
                        data = "Dark"
                    case "/set/data/textbox_ui_scaling":
                        data = 1.5
                    case "/set/data/message_box_ratio":
                        data = 0.5
                    case "/set/data/font_family":
                        data = "Yu Gothic UI"
                    case "/set/data/ui_language":
                        data = "ja"
                    case "/set/data/ctranslate2_weight_type":
                        data = "small"
                    case "/set/data/deepl_auth_key":
                        data = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee:fx"
                    case "/set/data/selected_mic_host":
                        data = "MME"
                    case "/set/data/selected_mic_device":
                        data = "マイク (Realtek High Definition Audio)"
                    case "/set/data/mic_threshold":
                        data = 0.5
                    case "/set/data/mic_record_timeout":
                        data = 1
                    case "/set/data/mic_phrase_timeout":
                        data = 5
                    case "/set/data/mic_max_phrases":
                        data = 5
                    case "/set//data/mic_word_filter":
                        data = "test0, test1, test2"
                    case "/set/data/selected_speaker_device":
                        data = "スピーカー (Realtek High Definition Audio)"
                    case "/set/data/speaker_threshold":
                        data = 0.5
                    case "/set/data/speaker_record_timeout":
                        data = 5
                    case "/set/data/speaker_phrase_timeout":
                        data = 5
                    case "/set/data/speaker_max_phrases":
                        data = 5
                    case "/set/data/whisper_weight_type":
                        data = "base"
                    case "/set/data/overlay_settings":
                        data = {
                            "opacity": 0.5,
                            "ui_scaling": 1.5,
                        }
                    case "/set/data/overlay_small_log_settings":
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
                    case "/set/data/send_message_button_type":
                        data = "show"
                    case "/set/data/send_message_format":
                        data = "[message]"
                    case "/set/data/send_message_format_with_t":
                        data = "[message]([translation])"
                    case "/set/data/received_message_format":
                        data = "[message]"
                    case "/set/data/received_message_format_with_t":
                        data = "[message]([translation])"
                    case "/set/data/osc_ip_address":
                        data = "127.0.0.1"
                    case "/set/data/osc_port":
                        data = 8000
                    case "/set/data/speaker_no_speech_prob":
                        data = 0.5
                    case "/set/data/speaker_avg_logprob":
                        data = 0.5
                    case "/set/data/mic_no_speech_prob":
                        data = 0.5
                    case "/set/data/mic_avg_logprob":
                        data = 0.5
                    case _:
                        data = None

                result, status = main.handleRequest(endpoint, data)
                printResponse(status, endpoint, result)
                time.sleep(0.5)