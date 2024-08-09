import { useMainFunction } from "./useMainFunction";
import { useConfig } from "./useConfig";

export const useReceiveRoutes = () => {
    const {
        updateTranslationStatus,
        updateTranscriptionSendStatus,
        updateTranscriptionReceiveStatus,
    } = useMainFunction();

    const {
        updateSoftwareVersion,
    } = useConfig();

    const routes = {
        "/controller/callback_toggle_translation": updateTranslationStatus,
        "/controller/callback_toggle_transcription_send": updateTranscriptionSendStatus,
        "/controller/callback_toggle_transcription_receive": updateTranscriptionReceiveStatus,

        "/config/version": updateSoftwareVersion,
    };

    const receiveRoutes = (parsed_data) => {
        switch (parsed_data.status) {
            case 200:
                const route = routes[parsed_data.endpoint];
                (route) ? route({ data: parsed_data.result }) : console.error(`Invalid endpoint: ${parsed_data.endpoint}`);
                break;

            case 384:
                console.log("from backend:", parsed_data);
                break;

            default:
                console.log("Received data status does not match.", parsed_data);
                break;
        }

    };
    return { receiveRoutes };
};