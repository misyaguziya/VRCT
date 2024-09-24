import { getCurrent } from "@tauri-apps/api/window";

import {
    useStore_TranslationStatus,
    useStore_TranscriptionSendStatus,
    useStore_TranscriptionReceiveStatus,
    useStore_ForegroundStatus,
} from "@store";

import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useMainFunction = () => {
    const {
        currentTranslationStatus,
        updateTranslationStatus,
        pendingTranslationStatus,
    } = useStore_TranslationStatus();
    const {
        currentTranscriptionSendStatus,
        updateTranscriptionSendStatus,
        pendingTranscriptionSendStatus,
    } = useStore_TranscriptionSendStatus();
    const {
        currentTranscriptionReceiveStatus,
        updateTranscriptionReceiveStatus,
        pendingTranscriptionReceiveStatus,
    } = useStore_TranscriptionReceiveStatus();
    const {
        currentForegroundStatus,
        updateForegroundStatus,
    } = useStore_ForegroundStatus();

    const { asyncStdoutToPython } = useStdoutToPython();

    const toggleTranslation = () => {
        pendingTranslationStatus();
        if (currentTranslationStatus.data) {
            asyncStdoutToPython("/set/disable/translation");
        } else {
            asyncStdoutToPython("/set/enable/translation");
        }
    };

    const toggleTranscriptionSend = () => {
        pendingTranscriptionSendStatus();
        if (currentTranscriptionSendStatus.data) {
            asyncStdoutToPython("/set/disable/transcription_send");
        } else {
            asyncStdoutToPython("/set/enable/transcription_send");
        }
    };

    const toggleTranscriptionReceive = () => {
        pendingTranscriptionReceiveStatus();
        if (currentTranscriptionReceiveStatus.data) {
            asyncStdoutToPython("/set/disable/transcription_receive");
        } else {
            asyncStdoutToPython("/set/enable/transcription_receive");
        }
    };

    const toggleForeground = () => {
        const main_page = getCurrent();
        const is_foreground_enabled = !currentForegroundStatus.data;
        main_page.setAlwaysOnTop(is_foreground_enabled);
        updateForegroundStatus(is_foreground_enabled);
    };

    return {
        currentTranslationStatus,
        toggleTranslation,
        updateTranslationStatus,

        currentTranscriptionSendStatus,
        toggleTranscriptionSend,
        updateTranscriptionSendStatus,

        currentTranscriptionReceiveStatus,
        toggleTranscriptionReceive,
        updateTranscriptionReceiveStatus,

        currentForegroundStatus,
        toggleForeground,
        updateForegroundStatus,

    };
};