import { store } from "@store";

import {
    useStore_TranslationStatus,
    useStore_TranscriptionSendStatus,
    useStore_TranscriptionReceiveStatus,
    useStore_ForegroundStatus,
} from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useMainFunction = () => {
    const appWindow = store.appWindow;

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

    const setTranslation = (to_enable) => {
        pendingTranslationStatus();
        if (to_enable) {
            asyncStdoutToPython("/set/enable/translation");
        } else {
            asyncStdoutToPython("/set/disable/translation");
        }
    };
    const toggleTranslation = () => {
        updateTranslationStatus(prev_state => {
            if (prev_state.state === "ok") setTranslation(!prev_state.data);
        }, { set_state: "pending" });
    };

    const setTranscriptionSend = (to_enable) => {
        pendingTranscriptionSendStatus();
        if (to_enable) {
            asyncStdoutToPython("/set/enable/transcription_send");
        } else {
            asyncStdoutToPython("/set/disable/transcription_send");
        }
    };
    const toggleTranscriptionSend = () => {
        updateTranscriptionSendStatus(prev_state => {
            if (prev_state.state === "ok") setTranscriptionSend(!prev_state.data);
        }, { set_state: "pending" });
    };

    const setTranscriptionReceive = (to_enable) => {
        pendingTranscriptionReceiveStatus();
        if (to_enable) {
            asyncStdoutToPython("/set/enable/transcription_receive");
        } else {
            asyncStdoutToPython("/set/disable/transcription_receive");
        }
    };
    const toggleTranscriptionReceive = () => {
        updateTranscriptionReceiveStatus(prev_state => {
            if (prev_state.state === "ok") setTranscriptionReceive(!prev_state.data);
        }, { set_state: "pending" });
    };


    const toggleForeground = async () => {
        const is_foreground_enabled = !currentForegroundStatus.data;
        await appWindow.setAlwaysOnTop(is_foreground_enabled);
        updateForegroundStatus(is_foreground_enabled);
    };

    return {
        currentTranslationStatus,
        toggleTranslation,
        updateTranslationStatus,
        setTranslation,

        currentTranscriptionSendStatus,
        toggleTranscriptionSend,
        updateTranscriptionSendStatus,
        setTranscriptionSend,

        currentTranscriptionReceiveStatus,
        toggleTranscriptionReceive,
        updateTranscriptionReceiveStatus,
        setTranscriptionReceive,

        currentForegroundStatus,
        toggleForeground,
        updateForegroundStatus,

    };
};