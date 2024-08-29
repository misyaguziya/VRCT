import { useMainFunction } from "./useMainFunction";
import { useConfig } from "./useConfig";
import { useMessage } from "./useMessage";

export const useReceiveRoutes = () => {
    const {
        updateTranslationStatus,
        updateTranscriptionSendStatus,
        updateTranscriptionReceiveStatus,
    } = useMainFunction();

    const {
        updateSentMessageLog,
        addSentMessageLog,
        addReceivedMessageLog,
    } = useMessage();

    const {
        updateSoftwareVersion,
    } = useConfig();

    const routes = {
        "/controller/callback_enable_translation": updateTranslationStatus,
        "/controller/callback_disable_translation": updateTranslationStatus,
        "/controller/callback_enable_transcription_send": updateTranscriptionSendStatus,
        "/controller/callback_disable_transcription_send": updateTranscriptionSendStatus,
        "/controller/callback_enable_transcription_receive": updateTranscriptionReceiveStatus,
        "/controller/callback_disable_transcription_receive": updateTranscriptionReceiveStatus,

        "/config/version": updateSoftwareVersion,

        "/controller/callback_messagebox_press_key_enter": updateSentMessageLog,
        "/action/transcription_send_mic_message": addSentMessageLog,
        "/action/transcription_receive_speaker_message": addReceivedMessageLog
    };

    const receiveRoutes = (parsed_data) => {
        switch (parsed_data.status) {
            case 200:
                const route = routes[parsed_data.endpoint];
                (route) ? route({ data: parsed_data.result }) : console.error(`Invalid endpoint: ${parsed_data.endpoint}`);
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