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
            asyncStdoutToPython({id: "/controller/callback_toggle_translation", data: !currentTranslationStatus.data});
            asyncUpdateTranslationStatus(asyncPending);
        },
        currentTranslationStatus: currentTranslationStatus,
        updateTranslationStatus: (payload) => {
            updateTranslationStatus(payload.data);
        },

        toggleTranscriptionSend: () => {
            asyncStdoutToPython({id: "/controller/callback_toggle_transcription_send", data: !currentTranscriptionSendStatus.data});
            asyncUpdateTranscriptionSendStatus(asyncPending);
        },
        currentTranscriptionSendStatus: currentTranscriptionSendStatus,
        updateTranscriptionSendStatus: (payload) => {
            updateTranscriptionSendStatus(payload.data);
        },

        toggleTranscriptionReceive: () => {
            asyncStdoutToPython({id: "/controller/callback_toggle_transcription_receive", data: !currentTranscriptionReceiveStatus.data});
            asyncUpdateTranscriptionReceiveStatus(asyncPending);
        },
        currentTranscriptionReceiveStatus: currentTranscriptionReceiveStatus,
        updateTranscriptionReceiveStatus: (payload) => {
            updateTranscriptionReceiveStatus(payload.data);
        },

        toggleForeground: () => {
            const main_window = getCurrent();
            const is_foreground_enabled = !currentForegroundStatus.data;
            main_window.setAlwaysOnTop(is_foreground_enabled);
            updateForegroundStatus(is_foreground_enabled);

        },
        currentForegroundStatus: currentForegroundStatus,
    };
};

const asyncTestFunction = (...args) => {
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve(...args);
        }, 3000);
    });
};