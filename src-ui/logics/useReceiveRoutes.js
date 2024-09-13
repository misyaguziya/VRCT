import { arrayToObject } from "@utils/arrayToObject";
import { useMainFunction } from "./useMainFunction";
import { useMessage } from "./useMessage";
import { useVolume } from "./useVolume";

import { useSoftwareVersion } from "@logics_configs/useSoftwareVersion";
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
    const {
        updateTranslationStatus,
        updateTranscriptionSendStatus,
        updateTranscriptionReceiveStatus,
    } = useMainFunction();

    const {
        updateSentMessageLogById,
        addSentMessageLog,
        addReceivedMessageLog,
    } = useMessage();

    const { updateSoftwareVersion } = useSoftwareVersion();
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
        "/controller/callback_enable_translation": updateTranslationStatus,
        "/controller/callback_disable_translation": updateTranslationStatus,
        "/controller/callback_enable_transcription_send": updateTranscriptionSendStatus,
        "/controller/callback_disable_transcription_send": updateTranscriptionSendStatus,
        "/controller/callback_enable_transcription_receive": updateTranscriptionReceiveStatus,
        "/controller/callback_disable_transcription_receive": updateTranscriptionReceiveStatus,


        "/config/version": updateSoftwareVersion,

        "/controller/list_mic_host": (payload) => updateMicHostList(arrayToObject(payload)),
        "/config/choice_mic_host": updateSelectedMicHost,
        "/controller/callback_set_mic_host": (payload) => {
            updateSelectedMicHost(payload.host);
            updateSelectedMicDevice(payload.device);
        },

        "/controller/list_mic_device": (payload) => updateMicDeviceList(arrayToObject(payload)),
        "/config/choice_mic_device": updateSelectedMicDevice,
        "/controller/callback_set_mic_device": updateSelectedMicDevice,

        "/controller/list_speaker_device": (payload) => updateSpeakerDeviceList(arrayToObject(payload)),
        "/config/choice_speaker_device": updateSelectedSpeakerDevice,
        "/controller/callback_set_speaker_device": updateSelectedSpeakerDevice,

        "/action/check_mic_threshold_energy": updateVolumeVariable_Mic,
        "/action/check_speaker_threshold_energy": updateVolumeVariable_Speaker,
        "/controller/callback_enable_check_mic_threshold": () => updateMicThresholdCheckStatus(true),
        "/controller/callback_disable_check_mic_threshold": () => updateMicThresholdCheckStatus(false),
        "/controller/callback_enable_check_speaker_threshold": () => updateSpeakerThresholdCheckStatus(true),
        "/controller/callback_disable_check_speaker_threshold": () => updateSpeakerThresholdCheckStatus(false),

        "/config/enable_auto_clear_message_box": updateEnableAutoClearMessageBox,
        "/controller/callback_enable_auto_clear_chatbox": updateEnableAutoClearMessageBox,
        "/controller/callback_disable_auto_clear_chatbox": updateEnableAutoClearMessageBox,

        "/config/send_message_button_type": updateSendMessageButtonType,
        "/controller/callback_set_send_message_button_type": updateSendMessageButtonType,

        "/config/input_mic_energy_threshold": updateMicThreshold,
        "/controller/callback_set_mic_energy_threshold": updateMicThreshold,
        "/config/input_speaker_energy_threshold": updateSpeakerThreshold,
        "/controller/callback_set_speaker_energy_threshold": updateSpeakerThreshold,

        "/config/input_mic_dynamic_energy_threshold": updateEnableAutomaticMicThreshold,
        "/controller/callback_enable_mic_dynamic_energy_threshold": updateEnableAutomaticMicThreshold,
        "/controller/callback_disable_mic_dynamic_energy_threshold": updateEnableAutomaticMicThreshold,
        "/config/input_speaker_dynamic_energy_threshold": updateEnableAutomaticSpeakerThreshold,
        "/controller/callback_enable_speaker_dynamic_energy_threshold": updateEnableAutomaticSpeakerThreshold,

        "/config/ui_language": updateUiLanguage,
        "/controller/callback_set_ui_language": updateUiLanguage,


        "/controller/callback_messagebox_send": updateSentMessageLogById,
        "/action/transcription_send_mic_message": addSentMessageLog,
        "/action/transcription_receive_speaker_message": addReceivedMessageLog
    };

    const receiveRoutes = (parsed_data) => {
        switch (parsed_data.status) {
            case 200:
                const route = routes[parsed_data.endpoint];
                (route) ? route(parsed_data.result) : console.error(`Invalid endpoint: ${parsed_data.endpoint}`);
                break;

            case 348:
                console.log("from backend:", parsed_data);
                break;

            default:
                console.log("Received data status does not match.", parsed_data);
                break;
        }

    };
    return { receiveRoutes };
};