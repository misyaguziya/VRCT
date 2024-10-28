import { translator_status } from "@data";
import { arrayToObject } from "@utils/arrayToObject";

import {
    useWindow,
    useMessage,
    useVolume,
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
    useOverlaySettings,
    useOverlaySmallLogSettings,
    useOscIpAddress,
    useOscPort,
} from "@logics_configs";

export const useReceiveRoutes = () => {
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

    const { updateOverlaySettings } = useOverlaySettings();
    const { updateOverlaySmallLogSettings } = useOverlaySmallLogSettings();

    const { updateOscIpAddress } = useOscIpAddress();
    const { updateOscPort } = useOscPort();

    const routes = {
        // Common
        "/run/feed_watchdog": () => {},
        "/get/data/main_window_geometry": restoreWindowGeometry,
        "/set/data/main_window_geometry": () => {},
        "/run/open_filepath_logs": () => console.log("Opened Directory, Message Logs"),
        "/run/open_filepath_config_file": () => console.log("Opened Directory, Config File"),

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
                    is_available: keys.includes(translator.translator_id),
                }));
            };
            const updated_list = updateTranslatorAvailability(payload);
            updateTranslationEngines(updated_list);
        },
        "/run/translation_engines": (payload) => {
            const updateTranslatorAvailability = (keys) => {
                return translator_status.map(translator => ({
                    ...translator,
                    is_available: keys.includes(translator.translator_id),
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

        // VR
        "/get/data/overlay_settings": updateOverlaySettings,
        "/set/data/overlay_settings": updateOverlaySettings,

        "/get/data/overlay_small_log_settings": updateOverlaySmallLogSettings,
        "/set/data/overlay_small_log_settings": updateOverlaySmallLogSettings,

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

        // Advanced Settings
        "/get/data/osc_ip_address": updateOscIpAddress,
        "/set/data/osc_ip_address": updateOscIpAddress,

        "/get/data/osc_port": updateOscPort,
        "/set/data/osc_port": updateOscPort,
    };

    const error_routes = {
        "/set/data/mic_record_timeout": updateMicRecordTimeout,
        "/set/data/mic_phrase_timeout": updateMicPhraseTimeout,
        "/set/data/mic_max_phrases": updateMicMaxWords,

        "/set/data/speaker_record_timeout": updateSpeakerRecordTimeout,
        "/set/data/speaker_phrase_timeout": updateSpeakerPhraseTimeout,
        "/set/data/speaker_max_phrases": updateSpeakerMaxWords,
    };


    const receiveRoutes = (parsed_data) => {
        const initDataSyncProcess = (payload) => {
            for (const [endpoint, value] of Object.entries(payload)) {
                const route = routes[endpoint];
                (route) ? route(value) : console.error(`Invalid endpoint: ${endpoint}\vvalue: ${JSON.stringify(value)}`);
            }
        };

        switch (parsed_data.status) {
            case 200:
                if (parsed_data.endpoint === "/run/initialization_complete") {
                    initDataSyncProcess(parsed_data.result);
                    break;
                };
                const route = routes[parsed_data.endpoint];
                (route) ? route(parsed_data.result) : console.error(`Invalid endpoint: ${parsed_data.endpoint}\nresult: ${JSON.stringify(parsed_data.result)}`);
                break;

            case 400:
                const error_route = error_routes[parsed_data.endpoint];
                (error_route) ? error_route(parsed_data.result.data) : console.error(`Invalid endpoint: ${parsed_data.endpoint}\nresult: ${JSON.stringify(parsed_data.result)}`);
                console.error(`status 400: ${JSON.stringify(parsed_data.result)}`);
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