import { getCurrent } from "@tauri-apps/api/window";

import {
    useTranslationStatus,
    useTranscriptionSendStatus,
    useTranscriptionReceiveStatus,
    useForegroundStatus,
} from "@store";

import { useStdoutToPython } from "@logics/useStdoutToPython";

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
    const toggleTranslation = () => {
        asyncUpdateTranslationStatus(asyncPending);
        if (currentTranslationStatus.data) {
            asyncStdoutToPython("/controller/callback_disable_translation");
        } else {
            asyncStdoutToPython("/controller/callback_enable_translation");
        }
    };

    const toggleTranscriptionSend = () => {
        asyncUpdateTranscriptionSendStatus(asyncPending);
        if (currentTranscriptionSendStatus.data) {
            asyncStdoutToPython("/controller/callback_disable_transcription_send");
        } else {
            asyncStdoutToPython("/controller/callback_enable_transcription_send");
        }
    };

    const toggleTranscriptionReceive = () => {
        asyncUpdateTranscriptionReceiveStatus(asyncPending);
        if (currentTranscriptionReceiveStatus.data) {
            asyncStdoutToPython("/controller/callback_disable_transcription_receive");
        } else {
            asyncStdoutToPython("/controller/callback_enable_transcription_receive");
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