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
    const { updateMicThreshold } = useMicThreshold();
    const { updateSpeakerThreshold } = useSpeakerThreshold();
    const { updateEnableAutoClearMessageBox }  = useEnableAutoClearMessageBox();
    const { updateSendMessageButtonType } = useSendMessageButtonType();


    const { updateVolumeVariable_Mic, updateVolumeVariable_Speaker } = useVolume();

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

        "/config/enable_auto_clear_message_box": updateEnableAutoClearMessageBox,
        "/controller/callback_enable_auto_clear_chatbox": updateEnableAutoClearMessageBox,
        "/controller/callback_disable_auto_clear_chatbox": updateEnableAutoClearMessageBox,

        "/config/send_message_button_type": updateSendMessageButtonType,
        "/controller/callback_set_send_message_button_type": updateSendMessageButtonType,

        "/config/input_mic_energy_threshold": updateMicThreshold,
        "/controller/callback_set_mic_energy_threshold": updateMicThreshold,
        "/config/input_speaker_energy_threshold": updateSpeakerThreshold,
        "/controller/callback_set_speaker_energy_threshold": updateSpeakerThreshold,


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