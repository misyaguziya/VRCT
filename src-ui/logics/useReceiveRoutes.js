import * as common from "@logics_common";
import * as main from "@logics_main";
import * as configs from "@logics_configs";
import { _useBackendErrorHandling } from "./_useBackendErrorHandling";

export const ROUTE_META_LIST = [
    // Common
    { endpoint: "/run/feed_watchdog", ns: null, hook_name: null, method_name: null },
    { endpoint: "/run/initialization_progress", ns: common, hook_name: "useInitProgress", method_name: "updateInitProgress" },
    { endpoint: "/run/enable_ai_models", ns: common, hook_name: "useIsVrctAvailable", method_name: "handleAiModelsAvailability" },
    { endpoint: "/get/data/compute_mode", ns: common, hook_name: "useComputeMode", method_name: "updateComputeMode" },

    { endpoint: "/run/update_software", ns: null, hook_name: null, method_name: null },
    { endpoint: "/run/update_cuda_software", ns: null, hook_name: null, method_name: null },

    { endpoint: "/get/data/main_window_geometry", ns: common, hook_name: "useWindow", method_name: "restoreWindowGeometry" },
    { endpoint: "/set/data/main_window_geometry", ns: null, hook_name: null, method_name: null },

    { endpoint: "/run/open_filepath_logs", ns: common, hook_name: "useOpenFolder", method_name: "openedFolder_MessageLogs" },
    { endpoint: "/run/open_filepath_config_file", ns: common, hook_name: "useOpenFolder", method_name: "openedFolder_ConfigFile" },

    // Software Version
    { endpoint: "/get/data/version", ns: common, hook_name: "useSoftwareVersion", method_name: "updateSoftwareVersion" },
    // Latest Software Version Info
    { endpoint: "/run/software_update_info", ns: common, hook_name: "useSoftwareVersion", method_name: "updateSoftwareVersionInfo" },

    { endpoint: "/run/connected_network", ns: common, hook_name: "useHandleNetworkConnection", method_name: "handleNetworkConnection" },
    { endpoint: "/run/enable_osc_query", ns: common, hook_name: "useHandleOscQuery", method_name: "handleOscQuery" },

    // Message (By typing)
    { endpoint: "/run/send_message_box", ns: common, hook_name: "useMessage", method_name: "updateSentMessageLogById" },
    { endpoint: "/run/typing_message_box", ns: null, hook_name: null, method_name: null },
    { endpoint: "/run/stop_typing_message_box", ns: null, hook_name: null, method_name: null },
    // Message Transcription
    { endpoint: "/run/transcription_send_mic_message", ns: common, hook_name: "useMessage", method_name: "addSentMessageLog" },
    { endpoint: "/run/transcription_receive_speaker_message", ns: common, hook_name: "useMessage", method_name: "addReceivedMessageLog" },

    // System Messages
    { endpoint: "/run/word_filter", ns: common, hook_name: "useMessage", method_name: "addSystemMessageLog_FromBackend" },


    // Volume
    { endpoint: "/run/check_mic_volume", ns: common, hook_name: "useVolume", method_name: "updateVolumeVariable_Mic" },
    { endpoint: "/run/check_speaker_volume", ns: common, hook_name: "useVolume", method_name: "updateVolumeVariable_Speaker" },
    { endpoint: "/set/enable/check_mic_threshold", ns: common, hook_name: "useVolume", method_name: "updateMicThresholdCheckStatus" },
    { endpoint: "/set/disable/check_mic_threshold", ns: common, hook_name: "useVolume", method_name: "updateMicThresholdCheckStatus" },
    { endpoint: "/set/enable/check_speaker_threshold", ns: common, hook_name: "useVolume", method_name: "updateSpeakerThresholdCheckStatus" },
    { endpoint: "/set/disable/check_speaker_threshold", ns: common, hook_name: "useVolume", method_name: "updateSpeakerThresholdCheckStatus" },




    // Main Page
    // Page Controls
    { endpoint: "/get/data/main_window_sidebar_compact_mode", ns: main, hook_name: "useIsMainPageCompactMode", method_name: "updateIsMainPageCompactMode" },
    { endpoint: "/set/enable/main_window_sidebar_compact_mode", ns: main, hook_name: "useIsMainPageCompactMode", method_name: "updateIsMainPageCompactMode" },
    { endpoint: "/set/disable/main_window_sidebar_compact_mode", ns: main, hook_name: "useIsMainPageCompactMode", method_name: "updateIsMainPageCompactMode" },

    // Main Functions
    { endpoint: "/set/enable/translation", ns: main, hook_name: "useMainFunction", method_name: "updateTranslationStatus" },
    { endpoint: "/set/disable/translation", ns: main, hook_name: "useMainFunction", method_name: "updateTranslationStatus" },
    { endpoint: "/set/enable/transcription_send", ns: main, hook_name: "useMainFunction", method_name: "updateTranscriptionSendStatus" },
    { endpoint: "/set/disable/transcription_send", ns: main, hook_name: "useMainFunction", method_name: "updateTranscriptionSendStatus" },
    { endpoint: "/set/enable/transcription_receive", ns: main, hook_name: "useMainFunction", method_name: "updateTranscriptionReceiveStatus" },
    { endpoint: "/set/disable/transcription_receive", ns: main, hook_name: "useMainFunction", method_name: "updateTranscriptionReceiveStatus" },

    // Language Settings
    { endpoint: "/get/data/selected_tab_no", ns: main, hook_name: "useLanguageSettings", method_name: "updateSelectedPresetTabNumber" },
    { endpoint: "/set/data/selected_tab_no", ns: main, hook_name: "useLanguageSettings", method_name: "updateSelectedPresetTabNumber" },

    { endpoint: "/get/data/selected_your_languages", ns: main, hook_name: "useLanguageSettings", method_name: "updateSelectedYourLanguages" },
    { endpoint: "/set/data/selected_your_languages", ns: main, hook_name: "useLanguageSettings", method_name: "updateSelectedYourLanguages" },
    { endpoint: "/get/data/selected_target_languages", ns: main, hook_name: "useLanguageSettings", method_name: "updateSelectedTargetLanguages" },
    { endpoint: "/set/data/selected_target_languages", ns: main, hook_name: "useLanguageSettings", method_name: "updateSelectedTargetLanguages" },

    { endpoint: "/get/data/translation_engines", ns: main, hook_name: "useLanguageSettings", method_name: "updateTranslatorAvailability" },
    { endpoint: "/run/translation_engines", ns: main, hook_name: "useLanguageSettings", method_name: "updateTranslatorAvailability" },

    { endpoint: "/get/data/selected_translation_engines", ns: main, hook_name: "useLanguageSettings", method_name: "updateSelectedTranslationEngines" },
    { endpoint: "/set/data/selected_translation_engines", ns: main, hook_name: "useLanguageSettings", method_name: "updateSelectedTranslationEngines" },
    { endpoint: "/run/selected_translation_engines", ns: main, hook_name: "useLanguageSettings", method_name: "updateSelectedTranslationEngines" },

    { endpoint: "/run/swap_your_language_and_target_language", ns: main, hook_name: "useLanguageSettings", method_name: "updateBothSelectedLanguages" },

    // Language Selector
    { endpoint: "/get/data/selectable_language_list", ns: main, hook_name: "useLanguageSettings", method_name: "updateSelectableLanguageList" },


    // Message Input Box
    { endpoint: "/get/data/message_box_ratio", ns: main, hook_name: "useMessageInputBoxRatio", method_name: "updateMessageInputBoxRatio" },
    { endpoint: "/set/data/message_box_ratio", ns: main, hook_name: "useMessageInputBoxRatio", method_name: "updateMessageInputBoxRatio" },



    // Config Page
    // Device
    { endpoint: "/get/data/auto_mic_select", ns: configs, hook_name: "useDevice", method_name: "updateEnableAutoMicSelect" },
    { endpoint: "/set/enable/auto_mic_select", ns: configs, hook_name: "useDevice", method_name: "setSuccessEnableAutoMicSelect" },
    { endpoint: "/set/disable/auto_mic_select", ns: configs, hook_name: "useDevice", method_name: "setSuccessEnableAutoMicSelect" },
    { endpoint: "/get/data/auto_speaker_select", ns: configs, hook_name: "useDevice", method_name: "updateEnableAutoSpeakerSelect" },
    { endpoint: "/set/enable/auto_speaker_select", ns: configs, hook_name: "useDevice", method_name: "setSuccessEnableAutoSpeakerSelect" },
    { endpoint: "/set/disable/auto_speaker_select", ns: configs, hook_name: "useDevice", method_name: "setSuccessEnableAutoSpeakerSelect" },

    // Device (Mic)
    { endpoint: "/get/data/mic_host_list", ns: configs, hook_name: "useDevice", method_name: "updateMicHostList_FromBackend" },
    { endpoint: "/run/mic_host_list", ns: configs, hook_name: "useDevice", method_name: "updateMicHostList_FromBackend" },

    { endpoint: "/get/data/selected_mic_host", ns: configs, hook_name: "useDevice", method_name: "updateSelectedMicHost" },
    { endpoint: "/set/data/selected_mic_host", ns: configs, hook_name: "useDevice", method_name: "setSuccessSelectedMicHost" },


    { endpoint: "/get/data/mic_device_list", ns: configs, hook_name: "useDevice", method_name: "updateMicDeviceList_FromBackend" },
    { endpoint: "/run/mic_device_list", ns: configs, hook_name: "useDevice", method_name: "updateMicDeviceList_FromBackend" },

    { endpoint: "/get/data/selected_mic_device", ns: configs, hook_name: "useDevice", method_name: "updateSelectedMicDevice" },
    { endpoint: "/set/data/selected_mic_device", ns: configs, hook_name: "useDevice", method_name: "setSuccessSelectedMicDevice" },

    { endpoint: "/run/selected_mic_device", ns: configs, hook_name: "useDevice", method_name: "updateSelectedMicHostAndDevice" },

    // Device (Speaker)
    { endpoint: "/get/data/speaker_device_list", ns: configs, hook_name: "useDevice", method_name: "updateSpeakerDeviceList_FromBackend" },
    { endpoint: "/run/speaker_device_list", ns: configs, hook_name: "useDevice", method_name: "updateSpeakerDeviceList_FromBackend" },

    { endpoint: "/get/data/selected_speaker_device", ns: configs, hook_name: "useDevice", method_name: "updateSelectedSpeakerDevice" },
    { endpoint: "/set/data/selected_speaker_device", ns: configs, hook_name: "useDevice", method_name: "setSuccessSelectedSpeakerDevice" },
    { endpoint: "/run/selected_speaker_device", ns: configs, hook_name: "useDevice", method_name: "updateSelectedSpeakerDevice" },

    // Device (Threshold)
    { endpoint: "/get/data/mic_threshold", ns: configs, hook_name: "useDevice",  method_name: "updateMicThreshold" },
    { endpoint: "/set/data/mic_threshold", ns: configs, hook_name: "useDevice",  method_name: "setSuccessMicThreshold" },
    { endpoint: "/get/data/speaker_threshold", ns: configs, hook_name: "useDevice",  method_name: "updateSpeakerThreshold" },
    { endpoint: "/set/data/speaker_threshold", ns: configs, hook_name: "useDevice",  method_name: "setSuccessSpeakerThreshold" },

    { endpoint: "/get/data/mic_automatic_threshold", ns: configs, hook_name: "useDevice",  method_name: "updateEnableAutomaticMicThreshold" },
    { endpoint: "/set/enable/mic_automatic_threshold", ns: configs, hook_name: "useDevice",  method_name: "setSuccessEnableAutomaticMicThreshold" },
    { endpoint: "/set/disable/mic_automatic_threshold", ns: configs, hook_name: "useDevice",  method_name: "setSuccessEnableAutomaticMicThreshold" },
    { endpoint: "/get/data/speaker_automatic_threshold", ns: configs, hook_name: "useDevice",  method_name: "updateEnableAutomaticSpeakerThreshold" },
    { endpoint: "/set/enable/speaker_automatic_threshold", ns: configs, hook_name: "useDevice",  method_name: "setSuccessEnableAutomaticSpeakerThreshold" },
    { endpoint: "/set/disable/speaker_automatic_threshold", ns: configs, hook_name: "useDevice",  method_name: "setSuccessEnableAutomaticSpeakerThreshold" },


    // Appearance
    { endpoint: "/get/data/ui_language", ns: configs, hook_name: "useAppearance", method_name: "updateUiLanguage" },
    { endpoint: "/set/data/ui_language", ns: configs, hook_name: "useAppearance", method_name: "setSuccessUiLanguage" },

    { endpoint: "/get/data/ui_scaling", ns: configs, hook_name: "useAppearance", method_name: "updateUiScaling" },
    { endpoint: "/set/data/ui_scaling", ns: configs, hook_name: "useAppearance", method_name: "setSuccessUiScaling" },

    { endpoint: "/get/data/textbox_ui_scaling", ns: configs, hook_name: "useAppearance", method_name: "updateMessageLogUiScaling" },
    { endpoint: "/set/data/textbox_ui_scaling", ns: configs, hook_name: "useAppearance", method_name: "setSuccessMessageLogUiScaling" },

    { endpoint: "/get/data/send_message_button_type", ns: configs, hook_name: "useAppearance", method_name: "updateSendMessageButtonType" },
    { endpoint: "/set/data/send_message_button_type", ns: configs, hook_name: "useAppearance", method_name: "setSuccessSendMessageButtonType" },

    { endpoint: "/get/data/show_resend_button", ns: configs, hook_name: "useAppearance", method_name: "updateShowResendButton" },
    { endpoint: "/set/enable/show_resend_button", ns: configs, hook_name: "useAppearance", method_name: "setSuccessShowResendButton" },
    { endpoint: "/set/disable/show_resend_button", ns: configs, hook_name: "useAppearance", method_name: "setSuccessShowResendButton" },

    { endpoint: "/get/data/font_family", ns: configs, hook_name: "useAppearance", method_name: "updateSelectedFontFamily" },
    { endpoint: "/set/data/font_family", ns: configs, hook_name: "useAppearance", method_name: "setSuccessSelectedFontFamily" },

    { endpoint: "/get/data/transparency", ns: configs, hook_name: "useAppearance", method_name: "updateTransparency" },
    { endpoint: "/set/data/transparency", ns: configs, hook_name: "useAppearance", method_name: "setSuccessTransparency" },

    // Translation
    { endpoint: "/get/data/deepl_auth_key", ns: configs, hook_name: "useTranslation", method_name: "updateDeepLAuthKey" },
    { endpoint: "/set/data/deepl_auth_key", ns: configs, hook_name: "useTranslation", method_name: "setSuccessDeepLAuthKey" },
    { endpoint: "/delete/data/deepl_auth_key", ns: configs, hook_name: "useTranslation", method_name: "deleteSuccessDeepLAuthKey" },

    // Translation (AI Models)
    { endpoint: "/get/data/ctranslate2_weight_type", ns: configs, hook_name: "useTranslation", method_name: "updateSelectedCTranslate2WeightType" },
    { endpoint: "/set/data/ctranslate2_weight_type", ns: configs, hook_name: "useTranslation", method_name: "setSuccessSelectedCTranslate2WeightType" },

    { endpoint: "/get/data/selectable_ctranslate2_weight_type_dict", ns: configs, hook_name: "useTranslation", method_name: "updateDownloadedCTranslate2WeightTypeStatus" },

    { endpoint: "/run/downloaded_ctranslate2_weight", ns: configs, hook_name: "useTranslation", method_name: "downloadedCTranslate2WeightType" },
    { endpoint: "/run/download_ctranslate2_weight", ns: null, hook_name: null, method_name: null },
    { endpoint: "/run/download_progress_ctranslate2_weight", ns: configs, hook_name: "useTranslation", method_name: "updateDownloadProgressCTranslate2WeightTypeStatus" },

    { endpoint: "/get/data/translation_compute_device_list", ns: configs, hook_name: "useTranslation", method_name: "updateSelectableCTranslate2ComputeDeviceList_FromBackend" },

    { endpoint: "/get/data/selected_translation_compute_device", ns: configs, hook_name: "useTranslation", method_name: "updateSelectedCTranslate2ComputeDevice" },
    { endpoint: "/set/data/selected_translation_compute_device", ns: configs, hook_name: "useTranslation", method_name: "setSuccessSelectedCTranslate2ComputeDevice" },


    // Transcription
    // Transcription (Mic)
    { endpoint: "/get/data/mic_record_timeout", ns: configs, hook_name: "useTranscription", method_name: "updateMicRecordTimeout" },
    { endpoint: "/set/data/mic_record_timeout", ns: configs, hook_name: "useTranscription", method_name: "setSuccessMicRecordTimeout" },

    { endpoint: "/get/data/mic_phrase_timeout", ns: configs, hook_name: "useTranscription", method_name: "updateMicPhraseTimeout" },
    { endpoint: "/set/data/mic_phrase_timeout", ns: configs, hook_name: "useTranscription", method_name: "setSuccessMicPhraseTimeout" },

    { endpoint: "/get/data/mic_max_phrases", ns: configs, hook_name: "useTranscription", method_name: "updateMicMaxWords" },
    { endpoint: "/set/data/mic_max_phrases", ns: configs, hook_name: "useTranscription", method_name: "setSuccessMicMaxWords" },

    { endpoint: "/get/data/mic_word_filter", ns: configs, hook_name: "useTranscription", method_name: "updateMicWordFilterList" },
    { endpoint: "/set/data/mic_word_filter", ns: configs, hook_name: "useTranscription", method_name: "setSuccessMicWordFilterList" },

    // Transcription (Speaker)
    { endpoint: "/get/data/speaker_record_timeout", ns: configs, hook_name: "useTranscription", method_name: "updateSpeakerRecordTimeout" },
    { endpoint: "/set/data/speaker_record_timeout", ns: configs, hook_name: "useTranscription", method_name: "setSuccessSpeakerRecordTimeout" },

    { endpoint: "/get/data/speaker_phrase_timeout", ns: configs, hook_name: "useTranscription", method_name: "updateSpeakerPhraseTimeout" },
    { endpoint: "/set/data/speaker_phrase_timeout", ns: configs, hook_name: "useTranscription", method_name: "setSuccessSpeakerPhraseTimeout" },

    { endpoint: "/get/data/speaker_max_phrases", ns: configs, hook_name: "useTranscription", method_name: "updateSpeakerMaxWords" },
    { endpoint: "/set/data/speaker_max_phrases", ns: configs, hook_name: "useTranscription", method_name: "setSuccessSpeakerMaxWords" },

    // Transcription (AI Models)
    { endpoint: "/get/data/selected_transcription_engine", ns: configs, hook_name: "useTranscription", method_name: "updateSelectedTranscriptionEngine" },
    { endpoint: "/set/data/selected_transcription_engine", ns: configs, hook_name: "useTranscription", method_name: "setSuccessSelectedTranscriptionEngine" },

    { endpoint: "/get/data/whisper_weight_type", ns: configs, hook_name: "useTranscription", method_name: "updateSelectedWhisperWeightType" },
    { endpoint: "/set/data/whisper_weight_type", ns: configs, hook_name: "useTranscription", method_name: "setSuccessSelectedWhisperWeightType" },

    { endpoint: "/get/data/selectable_whisper_weight_type_dict", ns: configs, hook_name: "useTranscription", method_name: "updateDownloadedWhisperWeightTypeStatus" },

    { endpoint: "/run/downloaded_whisper_weight", ns: configs, hook_name: "useTranscription", method_name: "downloadedWhisperWeightType" },
    { endpoint: "/run/download_whisper_weight", ns: null, hook_name: null, method_name: null },
    { endpoint: "/run/download_progress_whisper_weight", ns: configs, hook_name: "useTranscription", method_name: "updateDownloadProgressWhisperWeightTypeStatus" },

    { endpoint: "/get/data/transcription_compute_device_list", ns: configs, hook_name: "useTranscription", method_name: "updateSelectableWhisperComputeDeviceList_FromBackend" },
    { endpoint: "/get/data/selected_transcription_compute_device", ns: configs, hook_name: "useTranscription", method_name: "updateSelectedWhisperComputeDevice" },
    { endpoint: "/set/data/selected_transcription_compute_device", ns: configs, hook_name: "useTranscription", method_name: "setSuccessSelectedWhisperComputeDevice" },

    // VR
    { endpoint: "/get/data/overlay_small_log", ns: configs, hook_name: "useVr", method_name: "updateIsEnabledOverlaySmallLog" },
    { endpoint: "/set/enable/overlay_small_log", ns: configs, hook_name: "useVr", method_name: "setSuccessIsEnabledOverlaySmallLog" },
    { endpoint: "/set/disable/overlay_small_log", ns: configs, hook_name: "useVr", method_name: "setSuccessIsEnabledOverlaySmallLog" },

    { endpoint: "/get/data/overlay_small_log_settings", ns: configs, hook_name: "useVr", method_name: "updateOverlaySmallLogSettings" },
    { endpoint: "/set/data/overlay_small_log_settings", ns: configs, hook_name: "useVr", method_name: "setSuccessOverlaySmallLogSettings" },

    { endpoint: "/get/data/overlay_large_log", ns: configs, hook_name: "useVr", method_name: "updateIsEnabledOverlayLargeLog" },
    { endpoint: "/set/enable/overlay_large_log", ns: configs, hook_name: "useVr", method_name: "setSuccessIsEnabledOverlayLargeLog" },
    { endpoint: "/set/disable/overlay_large_log", ns: configs, hook_name: "useVr", method_name: "setSuccessIsEnabledOverlayLargeLog" },

    { endpoint: "/get/data/overlay_large_log_settings", ns: configs, hook_name: "useVr", method_name: "updateOverlayLargeLogSettings" },
    { endpoint: "/set/data/overlay_large_log_settings", ns: configs, hook_name: "useVr", method_name: "setSuccessOverlayLargeLogSettings" },

    { endpoint: "/get/data/overlay_show_only_translated_messages", ns: configs, hook_name: "useVr", method_name: "updateOverlayShowOnlyTranslatedMessages" },
    { endpoint: "/set/enable/overlay_show_only_translated_messages", ns: configs, hook_name: "useVr", method_name: "setSuccessOverlayShowOnlyTranslatedMessages" },
    { endpoint: "/set/disable/overlay_show_only_translated_messages", ns: configs, hook_name: "useVr", method_name: "setSuccessOverlayShowOnlyTranslatedMessages" },

    { endpoint: "/run/send_text_overlay", ns: null, hook_name: null, method_name: null },


    // Others
    { endpoint: "/get/data/auto_clear_message_box", ns: configs, hook_name: "useOthers", method_name: "updateEnableAutoClearMessageInputBox" },
    { endpoint: "/set/enable/auto_clear_message_box", ns: configs, hook_name: "useOthers", method_name: "setSuccessEnableAutoClearMessageInputBox" },
    { endpoint: "/set/disable/auto_clear_message_box", ns: configs, hook_name: "useOthers", method_name: "setSuccessEnableAutoClearMessageInputBox" },

    { endpoint: "/get/data/send_only_translated_messages", ns: configs, hook_name: "useOthers", method_name: "updateEnableSendOnlyTranslatedMessages" },
    { endpoint: "/set/enable/send_only_translated_messages", ns: configs, hook_name: "useOthers", method_name: "setSuccessEnableSendOnlyTranslatedMessages" },
    { endpoint: "/set/disable/send_only_translated_messages", ns: configs, hook_name: "useOthers", method_name: "setSuccessEnableSendOnlyTranslatedMessages" },

    { endpoint: "/get/data/logger_feature", ns: configs, hook_name: "useOthers", method_name: "updateEnableAutoExportMessageLogs" },
    { endpoint: "/set/enable/logger_feature", ns: configs, hook_name: "useOthers", method_name: "setSuccessEnableAutoExportMessageLogs" },
    { endpoint: "/set/disable/logger_feature", ns: configs, hook_name: "useOthers", method_name: "setSuccessEnableAutoExportMessageLogs" },

    { endpoint: "/get/data/vrc_mic_mute_sync", ns: configs, hook_name: "useOthers", method_name: "updateEnableVrcMicMuteSync_FromBackend" },
    { endpoint: "/set/enable/vrc_mic_mute_sync", ns: configs, hook_name: "useOthers", method_name: "setSuccessEnableVrcMicMuteSync" },
    { endpoint: "/set/disable/vrc_mic_mute_sync", ns: configs, hook_name: "useOthers", method_name: "setSuccessEnableVrcMicMuteSync" },


    { endpoint: "/get/data/send_message_to_vrc", ns: configs, hook_name: "useOthers", method_name: "updateEnableSendMessageToVrc" },
    { endpoint: "/set/enable/send_message_to_vrc", ns: configs, hook_name: "useOthers", method_name: "setSuccessEnableSendMessageToVrc" },
    { endpoint: "/set/disable/send_message_to_vrc", ns: configs, hook_name: "useOthers", method_name: "setSuccessEnableSendMessageToVrc" },

    { endpoint: "/get/data/send_received_message_to_vrc", ns: configs, hook_name: "useOthers", method_name: "updateEnableSendReceivedMessageToVrc" },
    { endpoint: "/set/enable/send_received_message_to_vrc", ns: configs, hook_name: "useOthers", method_name: "setSuccessEnableSendReceivedMessageToVrc" },
    { endpoint: "/set/disable/send_received_message_to_vrc", ns: configs, hook_name: "useOthers", method_name: "setSuccessEnableSendReceivedMessageToVrc" },

    { endpoint: "/get/data/notification_vrc_sfx", ns: configs, hook_name: "useOthers", method_name: "updateEnableNotificationVrcSfx" },
    { endpoint: "/set/enable/notification_vrc_sfx", ns: configs, hook_name: "useOthers", method_name: "setSuccessEnableNotificationVrcSfx" },
    { endpoint: "/set/disable/notification_vrc_sfx", ns: configs, hook_name: "useOthers", method_name: "setSuccessEnableNotificationVrcSfx" },

    // Hotkeys
    { endpoint: "/get/data/hotkeys", ns: configs, hook_name: "useHotkeys", method_name: "updateHotkeys" },
    { endpoint: "/set/data/hotkeys", ns: configs, hook_name: "useHotkeys", method_name: "setSuccessHotkeys" },

    // Plugins
    { endpoint: "/get/data/plugins_status", ns: configs, hook_name: "usePlugins", method_name: "updateSavedPluginsStatus" },
    { endpoint: "/set/data/plugins_status", ns: configs, hook_name: "usePlugins", method_name: "setSuccessSavedPluginsStatus" },

    // Advanced Settings
    { endpoint: "/get/data/osc_ip_address", ns: configs, hook_name: "useAdvancedSettings", method_name: "updateOscIpAddress" },
    { endpoint: "/set/data/osc_ip_address", ns: configs, hook_name: "useAdvancedSettings", method_name: "setSuccessOscIpAddress" },

    { endpoint: "/get/data/osc_port", ns: configs, hook_name: "useAdvancedSettings", method_name: "updateOscPort" },
    { endpoint: "/set/data/osc_port", ns: configs, hook_name: "useAdvancedSettings", method_name: "setSuccessOscPort" },

    { endpoint: "/get/data/websocket_server", ns: configs, hook_name: "useAdvancedSettings", method_name: "updateEnableWebsocket" },
    { endpoint: "/set/enable/websocket_server", ns: configs, hook_name: "useAdvancedSettings", method_name: "setSuccessEnableWebsocket" },
    { endpoint: "/set/disable/websocket_server", ns: configs, hook_name: "useAdvancedSettings", method_name: "setSuccessEnableWebsocket" },

    { endpoint: "/get/data/websocket_host", ns: configs, hook_name: "useAdvancedSettings", method_name: "updateWebsocketHost" },
    { endpoint: "/set/data/websocket_host", ns: configs, hook_name: "useAdvancedSettings", method_name: "setSuccessWebsocketHost" },

    { endpoint: "/get/data/websocket_port", ns: configs, hook_name: "useAdvancedSettings", method_name: "updateWebsocketPort" },
    { endpoint: "/set/data/websocket_port", ns: configs, hook_name: "useAdvancedSettings", method_name: "setSuccessWebsocketPort" },


    // Not Implemented Yet...
    { endpoint: "/get/data/mic_avg_logprob", ns: null, hook_name: null, method_name: null }, // Not implemented on UI yet
    { endpoint: "/get/data/mic_no_speech_prob", ns: null, hook_name: null, method_name: null }, // Not implemented on UI yet
    { endpoint: "/get/data/speaker_avg_logprob", ns: null, hook_name: null, method_name: null }, // Not implemented on UI yet
    { endpoint: "/get/data/speaker_no_speech_prob", ns: null, hook_name: null, method_name: null }, // Not implemented on UI yet
    { endpoint: "/get/data/convert_message_to_romaji", ns: null, hook_name: null, method_name: null }, // Not implemented on UI yet
    { endpoint: "/get/data/convert_message_to_hiragana", ns: null, hook_name: null, method_name: null }, // Not implemented on UI yet
    { endpoint: "/get/data/transcription_engines", ns: null, hook_name: null, method_name: null }, // Not implemented on UI yet. (if ai_models has not been detected, this will be blank array[]. if the ai_models are ok but just network has not connected, it'l be only ["Whisper"])
];

export const useReceiveRoutes = () => {
    const { showNotification_Error } = common.useNotificationStatus();
    const { errorHandling_Backend } = _useBackendErrorHandling();
    const { updateIsBackendReady } = common.useIsBackendReady();

    const handleInvalidEndpoint = (parsed_data) => {
        console.error(`Invalid endpoint: ${parsed_data.endpoint}\nresult: ${JSON.stringify(parsed_data.result)}`);
    };

    const hook_results = {};
    ROUTE_META_LIST.forEach(({ ns, hook_name }) => {
        if (ns && hook_name && !(hook_name in hook_results)) {
            hook_results[hook_name] = ns[hook_name]();
        }
    });

    const noop = () => {};

    const routes = Object.fromEntries(
        ROUTE_META_LIST.map(({ endpoint, hook_name, method_name }) => {
            const result_obj = hook_results[hook_name] || {};
            const fn = result_obj[method_name];
            return [endpoint, typeof fn === "function" ? fn : noop];
        })
    );


    const receiveRoutes = (parsed_data) => {
        const { endpoint, status, result } = parsed_data;

        if (endpoint === "/run/initialization_complete") {
            Object.entries(result).forEach(([ep, value]) => {
                if (ep in routes) {
                    routes[ep](value);
                } else {
                    handleInvalidEndpoint({ endpoint: ep, result: value });
                }
            });
            updateIsBackendReady(true);
            return;
        }


        switch (status) {
            case 200:
                if (endpoint in routes) {
                    routes[endpoint](result);
                } else {
                    handleInvalidEndpoint(parsed_data);
                }
                break;

            case 400:
                errorHandling_Backend({
                    message: parsed_data.result.message,
                    data: parsed_data.result.data,
                    endpoint: parsed_data.endpoint,
                    result: parsed_data.result,
                });
                break;

            case 348:
                // console.log(`from backend: %c ${JSON.stringify(parsed_data)}`, style_348);
                break;

            case 500:
                showNotification_Error(
                    `An error occurred. Please restart VRCT or contact the developers. ${JSON.stringify(parsed_data.result)}`, { hide_duration: null });
                break;

            default:
                console.log("Received data status does not match.", parsed_data);
        }
    };

    return { receiveRoutes };
};

const style_348 = [
    "color: gray",
].join(";");