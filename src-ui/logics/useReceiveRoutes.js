import { useMainFunction } from "./useMainFunction";

export const useReceiveRoutes = () => {
    const {
        updateTranslationStatus,
        updateTranscriptionSendStatus,
        updateTranscriptionReceiveStatus,
    } = useMainFunction();

    const routes = {
        "/controller/callback_toggle_translation": updateTranslationStatus,
        "/controller/callback_toggle_transcription_send": updateTranscriptionSendStatus,
        "/controller/callback_toggle_transcription_receive": updateTranscriptionReceiveStatus,
    };

    const receiveRoutes = (parsed_data) => {
        if (parsed_data.status === "ok") {
            const route = routes[parsed_data.id];
            if (route) {
                route({ data: parsed_data.data });
            } else {
                console.error(`Invalid path: ${parsed_data.id}`);
            }
        } else {
            console.log("Received data status is not 'ok'.", parsed_data);
        }
    };
    return { receiveRoutes };
};