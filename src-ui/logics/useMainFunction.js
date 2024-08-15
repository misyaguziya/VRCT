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
            if (currentTranslationStatus.data) {
                asyncStdoutToPython({endpoint: "/controller/callback_disable_translation"});
            } else {
                asyncStdoutToPython({endpoint: "/controller/callback_enable_translation"});
            }
            asyncUpdateTranslationStatus(asyncPending);
        },
        currentTranslationStatus: currentTranslationStatus,
        updateTranslationStatus: (payload) => {
            updateTranslationStatus(payload.data);
        },

        toggleTranscriptionSend: () => {
            if (currentTranscriptionSendStatus.data) {
                asyncStdoutToPython({endpoint: "/controller/callback_disable_transcription_send"});
            } else {
                asyncStdoutToPython({endpoint: "/controller/callback_enable_transcription_send"});
            }
            asyncUpdateTranscriptionSendStatus(asyncPending);
        },
        currentTranscriptionSendStatus: currentTranscriptionSendStatus,
        updateTranscriptionSendStatus: (payload) => {
            updateTranscriptionSendStatus(payload.data);
        },

        toggleTranscriptionReceive: () => {
            if (currentTranscriptionReceiveStatus.data) {
                asyncStdoutToPython({endpoint: "/controller/callback_disable_transcription_receive"});
            } else {
                asyncStdoutToPython({endpoint: "/controller/callback_enable_transcription_receive"});
            }
            asyncUpdateTranscriptionReceiveStatus(asyncPending);
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

const asyncTestFunction = (...args) => {
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve(...args);
        }, 3000);
    });
};