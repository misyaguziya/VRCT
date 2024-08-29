import { getCurrent } from "@tauri-apps/api/window";

import {
    useTranslationStatus,
    useTranscriptionSendStatus,
    useTranscriptionReceiveStatus,
    useForegroundStatus,
} from "@store";

import { useStdoutToPython } from "./useStdoutToPython";

export const useMainFunction = () => {
    const {
        currentTranslationStatus,
        updateTranslationStatus,
        asyncUpdateTranslationStatus,
    } = useTranslationStatus();
    const {
        currentTranscriptionSendStatus,
        updateTranscriptionSendStatus,
        asyncUpdateTranscriptionSendStatus,
    } = useTranscriptionSendStatus();
    const {
        currentTranscriptionReceiveStatus,
        updateTranscriptionReceiveStatus,
        asyncUpdateTranscriptionReceiveStatus,
    } = useTranscriptionReceiveStatus();
    const {
        currentForegroundStatus,
        updateForegroundStatus,
    } = useForegroundStatus();

    const { asyncStdoutToPython } = useStdoutToPython();

    const asyncPending = () => new Promise(() => {});
    return {
        toggleTranslation: () => {
            asyncUpdateTranslationStatus(asyncPending);
            if (currentTranslationStatus.data) {
                asyncStdoutToPython("/controller/callback_disable_translation");
            } else {
                asyncStdoutToPython("/controller/callback_enable_translation");
            }
        },
        currentTranslationStatus: currentTranslationStatus,
        updateTranslationStatus: (payload) => {
            updateTranslationStatus(payload.data);
        },

        toggleTranscriptionSend: () => {
            asyncUpdateTranscriptionSendStatus(asyncPending);
            if (currentTranscriptionSendStatus.data) {
                asyncStdoutToPython("/controller/callback_disable_transcription_send");
            } else {
                asyncStdoutToPython("/controller/callback_enable_transcription_send");
            }
        },
        currentTranscriptionSendStatus: currentTranscriptionSendStatus,
        updateTranscriptionSendStatus: (payload) => {
            updateTranscriptionSendStatus(payload.data);
        },

        toggleTranscriptionReceive: () => {
            asyncUpdateTranscriptionReceiveStatus(asyncPending);
            if (currentTranscriptionReceiveStatus.data) {
                asyncStdoutToPython("/controller/callback_disable_transcription_receive");
            } else {
                asyncStdoutToPython("/controller/callback_enable_transcription_receive");
            }
        },
        currentTranscriptionReceiveStatus: currentTranscriptionReceiveStatus,
        updateTranscriptionReceiveStatus: (payload) => {
            updateTranscriptionReceiveStatus(payload.data);
        },

        toggleForeground: () => {
            const main_page = getCurrent();
            const is_foreground_enabled = !currentForegroundStatus.data;
            main_page.setAlwaysOnTop(is_foreground_enabled);
            updateForegroundStatus(is_foreground_enabled);

        },
        currentForegroundStatus: currentForegroundStatus,
    };
};