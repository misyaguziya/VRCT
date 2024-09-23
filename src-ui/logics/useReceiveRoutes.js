import { translator_status } from "@data";

import { arrayToObject } from "@utils/arrayToObject";
import { useMainFunction } from "@logics_main/useMainFunction";
import { useMessage } from "@logics_common/useMessage";
import { useSelectableLanguageList } from "@logics_main/useSelectableLanguageList";
import { useLanguageSettings } from "@logics_main/useLanguageSettings";
import { useIsMainPageCompactMode } from "@logics_main/useIsMainPageCompactMode";
import { useVolume } from "@logics_common/useVolume";


import { useSoftwareVersion } from "@logics_configs/useSoftwareVersion";
import { useEnableAutoMicSelect } from "@logics_configs/useEnableAutoMicSelect";
import { useEnableAutoSpeakerSelect } from "@logics_configs/useEnableAutoSpeakerSelect";
import { useMicHostList } from "@logics_configs/useMicHostList";
import { useSelectedMicHost } from "@logics_configs/useSelectedMicHost";
import { useMicDeviceList } from "@logics_configs/useMicDeviceList";
import { useSelectedMicDevice } from "@logics_configs/useSelectedMicDevice";
import { useSpeakerDeviceList } from "@logics_configs/useSpeakerDeviceList";
import { useSelectedSpeakerDevice } from "@logics_configs/useSelectedSpeakerDevice";
import { useMicThreshold } from "@logics_configs/useMicThreshold";
import { useSpeakerThreshold } from "@logics_configs/useSpeakerThreshold";
import { useEnableAutoClearMessageBox } from "@logics_configs/useEnableAutoClearMessageBox";
import { useSendMessageButtonType } from "@logics_configs/useSendMessageButtonType";

import { useUiLanguage } from "@logics_configs/useUiLanguage";

export const useReceiveRoutes = () => {
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
    const { updateEnableAutoClearMessageBox }  = useEnableAutoClearMessageBox();
    const { updateSendMessageButtonType } = useSendMessageButtonType();
    const { updateUiLanguage } = useUiLanguage();
    const {
        updateVolumeVariable_Mic,
        updateVolumeVariable_Speaker,
        updateMicThresholdCheckStatus,
        updateSpeakerThresholdCheckStatus,
    } = useVolume();

    const routes = {
        // Main Page
        // Page Controls
        "/get/main_window_sidebar_compact_mode": updateIsMainPageCompactMode,
        "/set/enable_main_window_sidebar_compact_mode": updateIsMainPageCompactMode,
        "/set/disable_main_window_sidebar_compact_mode": updateIsMainPageCompactMode,
        // Main Functions
        "/set/enable_translation": updateTranslationStatus,
        "/set/disable_translation": updateTranslationStatus,
        "/set/enable_transcription_send": updateTranscriptionSendStatus,
        "/set/disable_transcription_send": updateTranscriptionSendStatus,
        "/set/enable_transcription_receive": updateTranscriptionReceiveStatus,
        "/set/disable_transcription_receive": updateTranscriptionReceiveStatus,

        // Language Settings
        "/get/selected_tab_no": updateSelectedPresetTabNumber,
        "/set/selected_tab_no": updateSelectedPresetTabNumber,
        "/get/multi_language_translation": updateEnableMultiTranslation,
        "/get/selected_your_languages": updateSelectedYourLanguages,
        "/set/selected_your_languages": updateSelectedYourLanguages,
        "/get/selected_target_languages": updateSelectedTargetLanguages,
        "/set/selected_target_languages": updateSelectedTargetLanguages,
        "/get/list_translation_engines": (payload) => {
            const updateTranslatorAvailability = (keys) => {
                return translator_status.map(translator => ({
                    ...translator,
                    is_available: keys.includes(translator.translator_id),
                }));
            };

            const updated_list = updateTranslatorAvailability(payload);

            updateTranslationEngines(updated_list);
        },
        "/get/selected_translator_engines": updateSelectedTranslationEngines,
        "/set/selected_translator_engines": updateSelectedTranslationEngines,

        "/run/swap_your_language_and_target_language": (payload) => {
            updateSelectedYourLanguages(payload.your);
            updateSelectedTargetLanguages(payload.target);
        },


        // Language Selector
        "/get/list_languages": updateSelectableLanguageList,

        // Message
        "/run/send_message_box": updateSentMessageLogById,
        "/action/transcription_send_mic_message": addSentMessageLog,
        "/action/transcription_receive_speaker_message": addReceivedMessageLog,


        // Config Page
        // Common
        "/get/version": updateSoftwareVersion,

        // Device Tab
        "/get/auto_mic_select": updateEnableAutoMicSelect,
        "/set/enable_auto_mic_select": updateEnableAutoMicSelect,
        "/set/disable_auto_mic_select": updateEnableAutoMicSelect,
        "/get/auto_speaker_select": updateEnableAutoSpeakerSelect,
        "/set/enable_auto_speaker_select": updateEnableAutoSpeakerSelect,
        "/set/disable_auto_speaker_select": updateEnableAutoSpeakerSelect,

        "/get/list_mic_host": (payload) => updateMicHostList(arrayToObject(payload)),
        "/get/selected_mic_host": updateSelectedMicHost,
        "/set/selected_mic_host": (payload) => {
            updateSelectedMicHost(payload.host);
            updateSelectedMicDevice(payload.device);
        },

        "/get/list_mic_device": (payload) => updateMicDeviceList(arrayToObject(payload)),
        "/get/selected_mic_device": updateSelectedMicDevice,
        "/set/selected_mic_device": updateSelectedMicDevice,

        "/get/list_speaker_device": (payload) => updateSpeakerDeviceList(arrayToObject(payload)),
        "/get/selected_speaker_device": updateSelectedSpeakerDevice,
        "/set/selected_speaker_device": updateSelectedSpeakerDevice,

        "/action/check_mic_threshold_energy": updateVolumeVariable_Mic,
        "/action/check_speaker_threshold_energy": updateVolumeVariable_Speaker,
        "/set/enable_check_mic_threshold": updateMicThresholdCheckStatus,
        "/set/disable_check_mic_threshold": updateMicThresholdCheckStatus,
        "/set/enable_check_speaker_threshold": updateSpeakerThresholdCheckStatus,
        "/set/disable_check_speaker_threshold": updateSpeakerThresholdCheckStatus,

        "/get/mic_energy_threshold": updateMicThreshold,
        "/set/mic_energy_threshold": updateMicThreshold,
        "/get/speaker_energy_threshold": updateSpeakerThreshold,
        "/set/speaker_energy_threshold": updateSpeakerThreshold,

        "/get/mic_dynamic_energy_threshold": updateEnableAutomaticMicThreshold,
        "/set/enable_mic_dynamic_energy_threshold": updateEnableAutomaticMicThreshold,
        "/set/disable_mic_dynamic_energy_threshold": updateEnableAutomaticMicThreshold,
        "/get/speaker_dynamic_energy_threshold": updateEnableAutomaticSpeakerThreshold,
        "/set/enable_speaker_dynamic_energy_threshold": updateEnableAutomaticSpeakerThreshold,
        "/set/disable_speaker_dynamic_energy_threshold": updateEnableAutomaticSpeakerThreshold,

        // Appearance
        "/get/ui_language": updateUiLanguage,
        "/set/ui_language": updateUiLanguage,

        // Others Tab
        "/get/auto_clear_message_box": updateEnableAutoClearMessageBox,
        "/set/enable_auto_clear_message_box": updateEnableAutoClearMessageBox,
        "/set/disable_auto_clear_message_box": updateEnableAutoClearMessageBox,

        "/get/send_message_button_type": updateSendMessageButtonType,
        "/set/send_message_button_type": updateSendMessageButtonType,
    };

    const receiveRoutes = (parsed_data) => {
        switch (parsed_data.status) {
            case 200:
                const route = routes[parsed_data.endpoint];
                (route) ? route(parsed_data.result) : console.error(`Invalid endpoint: ${parsed_data.endpoint}\nresult: ${JSON.stringify(parsed_data.result)}`);
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