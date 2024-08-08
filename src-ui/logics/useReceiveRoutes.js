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
        if (parsed_data.status === 200) {
            const route = routes[parsed_data.endpoint];
            if (route) {
                route({ data: parsed_data.result });
            } else {
                console.error(`Invalid path: ${parsed_data.endpoint}`);
            }
        } else {
            console.log("Received data status is not '200'.", parsed_data);
        }
    };
    return { receiveRoutes };
};