import { translator_status } from "@ui_configs";
import { arrayToObject } from "@utils";

import {
    useNotificationStatus,


    useComputeMode,
    useInitProgress,
    useIsBackendReady,
    useWindow,
    useMessage,
    useVolume,
    useIsSoftwareUpdateAvailable,
} from "@logics_common";

import {
    useMainFunction,
    useSelectableLanguageList,
    useLanguageSettings,
    useIsMainPageCompactMode,
    useMessageInputBoxRatio,
} from "@logics_main";

import {
    useSoftwareVersion,
    useEnableAutoMicSelect,
    useEnableAutoSpeakerSelect,
    useMicHostList,
    useSelectedMicHost,
    useMicDeviceList,
    useSelectedMicDevice,
    useSpeakerDeviceList,
    useSelectedSpeakerDevice,
    useMicThreshold,
    useSpeakerThreshold,
    useEnableAutoClearMessageInputBox,
    useEnableSendOnlyTranslatedMessages,
    useEnableAutoExportMessageLogs,
    useEnableVrcMicMuteSync,
    useEnableSendMessageToVrc,
    useEnableSendReceivedMessageToVrc,
    useSelectedFontFamily,
    useUiLanguage,
    useUiScaling,
    useMessageLogUiScaling,
    useSendMessageButtonType,
    useTransparency,
    useMicRecordTimeout,
    useMicPhraseTimeout,
    useMicMaxWords,
    useMicWordFilterList,
    useSpeakerRecordTimeout,
    useSpeakerPhraseTimeout,
    useSpeakerMaxWords,
    useDeepLAuthKey,
    useCTranslate2WeightTypeStatus,
    useSelectableCTranslate2ComputeDeviceList,
    useSelectedCTranslate2ComputeDevice,
    useSelectableWhisperComputeDeviceList,
    useSelectedWhisperComputeDevice,
    useSelectedCTranslate2WeightType,
    useSelectedTranscriptionEngine,
    useSelectedWhisperWeightType,
    useWhisperWeightTypeStatus,
    useIsEnabledOverlaySmallLog,
    useOverlaySmallLogSettings,
    useIsEnabledOverlayLargeLog,
    useOverlayLargeLogSettings,
    useOverlayShowOnlyTranslatedMessages,
    useOscIpAddress,
    useOscPort,
} from "@logics_configs";

export const useReceiveRoutes = () => {
    const { updateComputeMode } = useComputeMode();
    const { updateInitProgress } = useInitProgress();
    const { updateIsBackendReady } = useIsBackendReady();
    const { restoreWindowGeometry } = useWindow();
    const { updateIsMainPageCompactMode } = useIsMainPageCompactMode();
    const {
        updateTranslationStatus,
        updateTranscriptionSendStatus,
        updateTranscriptionReceiveStatus,
    } = useMainFunction();
    const {
        updateSelectedPresetTabNumber,
        updateEnableMultiTranslation,
        updateSelectedYourLanguages,
        updateSelectedTargetLanguages,
        updateTranslationEngines,
        updateSelectedTranslationEngines,
    } = useLanguageSettings();
    const { updateSelectableLanguageList } = useSelectableLanguageList();
    const {
        updateSentMessageLogById,
        addSentMessageLog,
        addReceivedMessageLog,
    } = useMessage();
    const { updateIsSoftwareUpdateAvailable } = useIsSoftwareUpdateAvailable();
    const { updateSoftwareVersion } = useSoftwareVersion();
    const { updateEnableAutoMicSelect } = useEnableAutoMicSelect();
    const { updateEnableAutoSpeakerSelect } = useEnableAutoSpeakerSelect();
    const { updateMicHostList } = useMicHostList();
    const { updateSelectedMicHost } = useSelectedMicHost();
    const { updateMicDeviceList } = useMicDeviceList();
    const { updateSelectedMicDevice } = useSelectedMicDevice();
    const { updateSpeakerDeviceList } = useSpeakerDeviceList();
    const { updateSelectedSpeakerDevice } = useSelectedSpeakerDevice();
    const { updateMicThreshold, updateEnableAutomaticMicThreshold } = useMicThreshold();
    const { updateSpeakerThreshold, updateEnableAutomaticSpeakerThreshold } = useSpeakerThreshold();

    const { updateEnableAutoClearMessageInputBox } = useEnableAutoClearMessageInputBox();
    const { updateEnableSendOnlyTranslatedMessages } = useEnableSendOnlyTranslatedMessages();
    const { updateEnableAutoExportMessageLogs } = useEnableAutoExportMessageLogs();
    const { updateEnableVrcMicMuteSync } = useEnableVrcMicMuteSync();
    const { updateEnableSendMessageToVrc } = useEnableSendMessageToVrc();
    const { updateEnableSendReceivedMessageToVrc } = useEnableSendReceivedMessageToVrc();

    const { updateSendMessageButtonType } = useSendMessageButtonType();
    const { updateUiLanguage } = useUiLanguage();
    const { updateUiScaling } = useUiScaling();
    const { updateMessageLogUiScaling } = useMessageLogUiScaling();
    const {
        updateVolumeVariable_Mic,
        updateVolumeVariable_Speaker,
        updateMicThresholdCheckStatus,
        updateSpeakerThresholdCheckStatus,
    } = useVolume();

    const { updateMessageInputBoxRatio } = useMessageInputBoxRatio();
    const { updateSelectedFontFamily } = useSelectedFontFamily();
    const { updateTransparency } = useTransparency();

    const { updateMicRecordTimeout } = useMicRecordTimeout();
    const { updateMicPhraseTimeout } = useMicPhraseTimeout();
    const { updateMicMaxWords } = useMicMaxWords();
    const { updateMicWordFilterList } = useMicWordFilterList();

    const { updateSpeakerRecordTimeout } = useSpeakerRecordTimeout();
    const { updateSpeakerPhraseTimeout } = useSpeakerPhraseTimeout();
    const { updateSpeakerMaxWords } = useSpeakerMaxWords();

    const { updateDeepLAuthKey } = useDeepLAuthKey();
    const { updateSelectedCTranslate2WeightType } = useSelectedCTranslate2WeightType();
    const {
        updateDownloadedCTranslate2WeightTypeStatus,
        updateDownloadProgressCTranslate2WeightTypeStatus,
        downloadedCTranslate2WeightType,
    } = useCTranslate2WeightTypeStatus();
    const { updateSelectableCTranslate2ComputeDeviceList } = useSelectableCTranslate2ComputeDeviceList();
    const { updateSelectedCTranslate2ComputeDevice } = useSelectedCTranslate2ComputeDevice();
    const { updateSelectableWhisperComputeDeviceList } = useSelectableWhisperComputeDeviceList();
    const { updateSelectedWhisperComputeDevice } = useSelectedWhisperComputeDevice();

    const { updateSelectedTranscriptionEngine } = useSelectedTranscriptionEngine();
    const { updateSelectedWhisperWeightType } = useSelectedWhisperWeightType();
    const {
        updateDownloadedWhisperWeightTypeStatus,
        updateDownloadProgressWhisperWeightTypeStatus,
        downloadedWhisperWeightType,
    } = useWhisperWeightTypeStatus();

    const { updateOverlaySmallLogSettings } = useOverlaySmallLogSettings();
    const { updateIsEnabledOverlaySmallLog } = useIsEnabledOverlaySmallLog();
    const { updateOverlayLargeLogSettings } = useOverlayLargeLogSettings();
    const { updateIsEnabledOverlayLargeLog } = useIsEnabledOverlayLargeLog();
    const { updateOverlayShowOnlyTranslatedMessages } = useOverlayShowOnlyTranslatedMessages();

    const { updateOscIpAddress } = useOscIpAddress();
    const { updateOscPort } = useOscPort();



    const { showNotification_Success, showNotification_Error } = useNotificationStatus();

    const routes = {
        // Common
        "/run/feed_watchdog": () => {},
        "/run/initialization_progress": updateInitProgress,
        "/get/data/compute_mode": updateComputeMode,
        "/get/data/main_window_geometry": restoreWindowGeometry,
        "/set/data/main_window_geometry": () => {},
        "/run/open_filepath_logs": () => console.log("Opened Directory, Message Logs"),
        "/run/open_filepath_config_file": () => console.log("Opened Directory, Config File"),
        "/run/update_software_flag": updateIsSoftwareUpdateAvailable,

        // Main Page
        // Page Controls
        "/get/data/main_window_sidebar_compact_mode": updateIsMainPageCompactMode,
        "/set/enable/main_window_sidebar_compact_mode": updateIsMainPageCompactMode,
        "/set/disable/main_window_sidebar_compact_mode": updateIsMainPageCompactMode,
        // Main Functions
        "/set/enable/translation": updateTranslationStatus,
        "/set/disable/translation": updateTranslationStatus,
        "/set/enable/transcription_send": updateTranscriptionSendStatus,
        "/set/disable/transcription_send": updateTranscriptionSendStatus,
        "/set/enable/transcription_receive": updateTranscriptionReceiveStatus,
        "/set/disable/transcription_receive": updateTranscriptionReceiveStatus,

        // Language Settings
        "/get/data/selected_tab_no": updateSelectedPresetTabNumber,
        "/set/data/selected_tab_no": updateSelectedPresetTabNumber,
        "/get/data/multi_language_translation": updateEnableMultiTranslation,
        "/get/data/selected_your_languages": updateSelectedYourLanguages,
        "/set/data/selected_your_languages": updateSelectedYourLanguages,
        "/get/data/selected_target_languages": updateSelectedTargetLanguages,
        "/set/data/selected_target_languages": updateSelectedTargetLanguages,

        "/get/data/translation_engines": (payload) => {
            const updateTranslatorAvailability = (keys) => {
                return translator_status.map(translator => ({
                    ...translator,
                    is_available: keys.includes(translator.id),
                }));
            };
            const updated_list = updateTranslatorAvailability(payload);
            updateTranslationEngines(updated_list);
        },
        "/run/translation_engines": (payload) => {
            const updateTranslatorAvailability = (keys) => {
                return translator_status.map(translator => ({
                    ...translator,
                    is_available: keys.includes(translator.id),
                }));
            };
            const updated_list = updateTranslatorAvailability(payload);
            updateTranslationEngines(updated_list);
        },
        "/get/data/selected_translation_engines": updateSelectedTranslationEngines,
        "/set/data/selected_translation_engines": updateSelectedTranslationEngines,
        "/run/selected_translation_engines": updateSelectedTranslationEngines,

        "/run/swap_your_language_and_target_language": (payload) => {
            updateSelectedYourLanguages(payload.your);
            updateSelectedTargetLanguages(payload.target);
        },


        // Language Selector
        "/get/data/selectable_language_list": updateSelectableLanguageList,

        // Message
        "/run/send_message_box": updateSentMessageLogById,
        "/run/typing_message_box": ()=>{},
        "/run/stop_typing_message_box": ()=>{},
        "/run/transcription_send_mic_message": addSentMessageLog,
        "/run/transcription_receive_speaker_message": addReceivedMessageLog,

        // Message Box
        "/get/data/message_box_ratio": updateMessageInputBoxRatio,
        "/set/data/message_box_ratio": updateMessageInputBoxRatio,


        // Config Page
        // Common
        "/get/data/version": updateSoftwareVersion,

        // Device Tab
        "/get/data/auto_mic_select": updateEnableAutoMicSelect,
        "/set/enable/auto_mic_select": updateEnableAutoMicSelect,
        "/set/disable/auto_mic_select": updateEnableAutoMicSelect,
        "/get/data/auto_speaker_select": updateEnableAutoSpeakerSelect,
        "/set/enable/auto_speaker_select": updateEnableAutoSpeakerSelect,
        "/set/disable/auto_speaker_select": updateEnableAutoSpeakerSelect,

        "/get/data/mic_host_list": (payload) => updateMicHostList(arrayToObject(payload)),
        "/run/mic_host_list": (payload) => updateMicHostList(arrayToObject(payload)),
        "/get/data/selected_mic_host": updateSelectedMicHost,
        "/set/data/selected_mic_host": (payload) => {
            updateSelectedMicHost(payload.host);
            updateSelectedMicDevice(payload.device);
        },

        "/get/data/mic_device_list": (payload) => updateMicDeviceList(arrayToObject(payload)),
        "/run/mic_device_list": (payload) => updateMicDeviceList(arrayToObject(payload)),
        "/get/data/selected_mic_device": updateSelectedMicDevice,
        "/set/data/selected_mic_device": updateSelectedMicDevice,

        "/run/selected_mic_device": (payload) => {
            updateSelectedMicHost(payload.host);
            updateSelectedMicDevice(payload.device);
        },

        "/get/data/speaker_device_list": (payload) => updateSpeakerDeviceList(arrayToObject(payload)),
        "/run/speaker_device_list": (payload) => updateSpeakerDeviceList(arrayToObject(payload)),
        "/get/data/selected_speaker_device": updateSelectedSpeakerDevice,
        "/set/data/selected_speaker_device": updateSelectedSpeakerDevice,
        "/run/selected_speaker_device": updateSelectedSpeakerDevice,

        "/run/check_mic_volume": updateVolumeVariable_Mic,
        "/run/check_speaker_volume": updateVolumeVariable_Speaker,
        "/set/enable/check_mic_threshold": updateMicThresholdCheckStatus,
        "/set/disable/check_mic_threshold": updateMicThresholdCheckStatus,
        "/set/enable/check_speaker_threshold": updateSpeakerThresholdCheckStatus,
        "/set/disable/check_speaker_threshold": updateSpeakerThresholdCheckStatus,

        "/get/data/mic_threshold": updateMicThreshold,
        "/set/data/mic_threshold": updateMicThreshold,
        "/get/data/speaker_threshold": updateSpeakerThreshold,
        "/set/data/speaker_threshold": updateSpeakerThreshold,

        "/get/data/mic_automatic_threshold": updateEnableAutomaticMicThreshold,
        "/set/enable/mic_automatic_threshold": updateEnableAutomaticMicThreshold,
        "/set/disable/mic_automatic_threshold": updateEnableAutomaticMicThreshold,
        "/get/data/speaker_automatic_threshold": updateEnableAutomaticSpeakerThreshold,
        "/set/enable/speaker_automatic_threshold": updateEnableAutomaticSpeakerThreshold,
        "/set/disable/speaker_automatic_threshold": updateEnableAutomaticSpeakerThreshold,

        // Appearance
        "/get/data/ui_language": updateUiLanguage,
        "/set/data/ui_language": updateUiLanguage,

        "/get/data/ui_scaling": updateUiScaling,
        "/set/data/ui_scaling": updateUiScaling,

        "/get/data/textbox_ui_scaling": updateMessageLogUiScaling,
        "/set/data/textbox_ui_scaling": updateMessageLogUiScaling,

        "/get/data/send_message_button_type": updateSendMessageButtonType,
        "/set/data/send_message_button_type": updateSendMessageButtonType,

        "/get/data/font_family": updateSelectedFontFamily,
        "/set/data/font_family": updateSelectedFontFamily,

        "/get/data/transparency": updateTransparency,
        "/set/data/transparency": updateTransparency,

        // Translation
        "/get/data/deepl_auth_key": updateDeepLAuthKey,
        "/set/data/deepl_auth_key": updateDeepLAuthKey,
        "/delete/data/deepl_auth_key": () => updateDeepLAuthKey(""),

        "/get/data/ctranslate2_weight_type": updateSelectedCTranslate2WeightType,
        "/set/data/ctranslate2_weight_type": updateSelectedCTranslate2WeightType,

        "/get/data/selectable_ctranslate2_weight_type_dict": updateDownloadedCTranslate2WeightTypeStatus,

        "/get/data/translation_compute_device_list": (payload) => updateSelectableCTranslate2ComputeDeviceList(transformToIndexedArray(payload)),
        "/get/data/selected_translation_compute_device": updateSelectedCTranslate2ComputeDevice,
        "/set/data/selected_translation_compute_device": updateSelectedCTranslate2ComputeDevice,

        "/run/downloaded_ctranslate2_weight": downloadedCTranslate2WeightType,
        "/run/download_ctranslate2_weight": () => {},
        "/run/download_progress_ctranslate2_weight": updateDownloadProgressCTranslate2WeightTypeStatus,

        // Transcription
        "/get/data/mic_record_timeout": updateMicRecordTimeout,
        "/set/data/mic_record_timeout": updateMicRecordTimeout,

        "/get/data/mic_phrase_timeout": updateMicPhraseTimeout,
        "/set/data/mic_phrase_timeout": updateMicPhraseTimeout,

        "/get/data/mic_max_phrases": updateMicMaxWords,
        "/set/data/mic_max_phrases": updateMicMaxWords,

        "/get/data/mic_word_filter": (payload) => {
            updateMicWordFilterList((prev_list) => {
                const updated_list = [...prev_list.data];
                for (const value of payload) {
                    const existing_item = updated_list.find(item => item.value === value);
                    if (existing_item) {
                        existing_item.is_redoable = false;
                    } else {
                        updated_list.push({ value, is_redoable: false });
                    }
                }
                return updated_list;
            });
        },
        "/set/data/mic_word_filter": (payload) => {
            updateMicWordFilterList((prev_list) => {
                const updated_list = [...prev_list.data];
                for (const value of payload) {
                    const existing_item = updated_list.find(item => item.value === value);
                    if (existing_item) {
                        existing_item.is_redoable = false;
                    } else {
                        updated_list.push({ value, is_redoable: false });
                    }
                }
                return updated_list;
            });
        },

        "/get/data/speaker_record_timeout": updateSpeakerRecordTimeout,
        "/set/data/speaker_record_timeout": updateSpeakerRecordTimeout,

        "/get/data/speaker_phrase_timeout": updateSpeakerPhraseTimeout,
        "/set/data/speaker_phrase_timeout": updateSpeakerPhraseTimeout,

        "/get/data/speaker_max_phrases": updateSpeakerMaxWords,
        "/set/data/speaker_max_phrases": updateSpeakerMaxWords,

        "/get/data/selected_transcription_engine": updateSelectedTranscriptionEngine,
        "/set/data/selected_transcription_engine": updateSelectedTranscriptionEngine,

        "/get/data/whisper_weight_type": updateSelectedWhisperWeightType,
        "/set/data/whisper_weight_type": updateSelectedWhisperWeightType,

        "/get/data/selectable_whisper_weight_type_dict": updateDownloadedWhisperWeightTypeStatus,

        "/run/downloaded_whisper_weight": downloadedWhisperWeightType,
        "/run/download_whisper_weight": () => {},
        "/run/download_progress_whisper_weight": updateDownloadProgressWhisperWeightTypeStatus,

        "/get/data/transcription_compute_device_list": (payload) => updateSelectableWhisperComputeDeviceList(transformToIndexedArray(payload)),
        "/get/data/selected_transcription_compute_device": updateSelectedWhisperComputeDevice,
        "/set/data/selected_transcription_compute_device": updateSelectedWhisperComputeDevice,

        // VR
        "/get/data/overlay_small_log": updateIsEnabledOverlaySmallLog,
        "/set/enable/overlay_small_log": updateIsEnabledOverlaySmallLog,
        "/set/disable/overlay_small_log": updateIsEnabledOverlaySmallLog,

        "/get/data/overlay_small_log_settings": updateOverlaySmallLogSettings,
        "/set/data/overlay_small_log_settings": updateOverlaySmallLogSettings,

        "/get/data/overlay_large_log": updateIsEnabledOverlayLargeLog,
        "/set/enable/overlay_large_log": updateIsEnabledOverlayLargeLog,
        "/set/disable/overlay_large_log": updateIsEnabledOverlayLargeLog,

        "/get/data/overlay_large_log_settings": updateOverlayLargeLogSettings,
        "/set/data/overlay_large_log_settings": updateOverlayLargeLogSettings,

        "/get/data/overlay_show_only_translated_messages": updateOverlayShowOnlyTranslatedMessages,
        "/set/enable/overlay_show_only_translated_messages": updateOverlayShowOnlyTranslatedMessages,
        "/set/disable/overlay_show_only_translated_messages": updateOverlayShowOnlyTranslatedMessages,

        // Others Tab
        "/get/data/auto_clear_message_box": updateEnableAutoClearMessageInputBox,
        "/set/enable/auto_clear_message_box": updateEnableAutoClearMessageInputBox,
        "/set/disable/auto_clear_message_box": updateEnableAutoClearMessageInputBox,

        "/get/data/send_only_translated_messages": updateEnableSendOnlyTranslatedMessages,
        "/set/enable/send_only_translated_messages": updateEnableSendOnlyTranslatedMessages,
        "/set/disable/send_only_translated_messages": updateEnableSendOnlyTranslatedMessages,

        "/get/data/logger_feature": updateEnableAutoExportMessageLogs,
        "/set/enable/logger_feature": updateEnableAutoExportMessageLogs,
        "/set/disable/logger_feature": updateEnableAutoExportMessageLogs,

        "/get/data/vrc_mic_mute_sync": updateEnableVrcMicMuteSync,
        "/set/enable/vrc_mic_mute_sync": updateEnableVrcMicMuteSync,
        "/set/disable/vrc_mic_mute_sync": updateEnableVrcMicMuteSync,

        "/get/data/send_message_to_vrc": updateEnableSendMessageToVrc,
        "/set/enable/send_message_to_vrc": updateEnableSendMessageToVrc,
        "/set/disable/send_message_to_vrc": updateEnableSendMessageToVrc,

        "/get/data/send_received_message_to_vrc": updateEnableSendReceivedMessageToVrc,
        "/set/enable/send_received_message_to_vrc": updateEnableSendReceivedMessageToVrc,
        "/set/disable/send_received_message_to_vrc": updateEnableSendReceivedMessageToVrc,

        // Advanced Settings
        "/get/data/osc_ip_address": updateOscIpAddress,
        "/set/data/osc_ip_address": updateOscIpAddress,

        "/get/data/osc_port": updateOscPort,
        "/set/data/osc_port": updateOscPort,

        "/get/data/mic_avg_logprob": ()=>{}, // Not implemented on UI yet
        "/get/data/mic_no_speech_prob": ()=>{}, // Not implemented on UI yet
        "/get/data/speaker_avg_logprob": ()=>{}, // Not implemented on UI yet
        "/get/data/speaker_no_speech_prob": ()=>{}, // Not implemented on UI yet
    };

    const error_routes = {
        "/set/data/mic_record_timeout": updateMicRecordTimeout,
        "/set/data/mic_phrase_timeout": updateMicPhraseTimeout,
        "/set/data/mic_max_phrases": updateMicMaxWords,

        "/set/data/speaker_record_timeout": updateSpeakerRecordTimeout,
        "/set/data/speaker_phrase_timeout": updateSpeakerPhraseTimeout,
        "/set/data/speaker_max_phrases": updateSpeakerMaxWords,

        "/set/data/deepl_auth_key": updateDeepLAuthKey,
    };


    const receiveRoutes = (parsed_data) => {
        const initDataSyncProcess = (payload) => {
            for (const [endpoint, value] of Object.entries(payload)) {
                const route = routes[endpoint];
                (route) ? route(value) : console.error(`Invalid endpoint: ${endpoint}\nvalue: ${JSON.stringify(value)}`);
            }
        };

        switch (parsed_data.status) {
            case 200:
                if (parsed_data.endpoint === "/run/initialization_complete") {
                    initDataSyncProcess(parsed_data.result);
                    updateIsBackendReady(true);
                    break;
                };
                const route = routes[parsed_data.endpoint];
                (route) ? route(parsed_data.result) : console.error(`Invalid endpoint: ${parsed_data.endpoint}\nresult: ${JSON.stringify(parsed_data.result)}`);
                break;

            case 400:
                const error_route = error_routes[parsed_data.endpoint];
                (error_route) ? error_route(parsed_data.result.data) : console.error(`Invalid endpoint: ${parsed_data.endpoint}\nresult: ${JSON.stringify(parsed_data.result)}`);
                console.error(`status 400: ${JSON.stringify(parsed_data.result)}`);
                showNotification_Error(parsed_data.result.message);
                break;

            case 348:
                // console.log(`from backend: %c ${JSON.stringify(parsed_data)}`, style_348);
                break;

            default:
                console.log("Received data status does not match.", parsed_data);
                break;
        }

    };
    return { receiveRoutes };
};

const style_348 = [
    "color: gray",
].join(";");

const transformToIndexedArray = (devices) => {
    return devices.reduce((result, device, index) => {
        result[index] = device;
        return result;
    }, {});
};