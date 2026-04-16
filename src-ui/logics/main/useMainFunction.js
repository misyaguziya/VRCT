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

    const createTogglePair = (pendingFn, updateFn, endpointName) => {
        const setFn = (to_enable) => {
            pendingFn();
            if (to_enable) {
                asyncStdoutToPython(`/set/enable/${endpointName}`);
            } else {
                asyncStdoutToPython(`/set/disable/${endpointName}`);
            }
        };
        const toggleFn = () => {
            updateFn(prev_state => {
                if (prev_state.state === "ok") setFn(!prev_state.data);
            }, { set_state: "pending" });
        };
        return { setFn, toggleFn };
    };

    const { setFn: setTranslation, toggleFn: toggleTranslation } = createTogglePair(
        pendingTranslationStatus, updateTranslationStatus, "translation"
    );
    const { setFn: setTranscriptionSend, toggleFn: toggleTranscriptionSend } = createTogglePair(
        pendingTranscriptionSendStatus, updateTranscriptionSendStatus, "transcription_send"
    );
    const { setFn: setTranscriptionReceive, toggleFn: toggleTranscriptionReceive } = createTogglePair(
        pendingTranscriptionReceiveStatus, updateTranscriptionReceiveStatus, "transcription_receive"
    );


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
        pendingTranslationStatus, // Exception.(It shouldn't be used in other function, normally.)

        currentTranscriptionSendStatus,
        toggleTranscriptionSend,
        updateTranscriptionSendStatus,
        setTranscriptionSend,
        pendingTranscriptionSendStatus, // Exception.(It shouldn't be used in other function, normally.)

        currentTranscriptionReceiveStatus,
        toggleTranscriptionReceive,
        updateTranscriptionReceiveStatus,
        setTranscriptionReceive,
        pendingTranscriptionReceiveStatus, // Exception.(It shouldn't be used in other function, normally.)

        currentForegroundStatus,
        toggleForeground,
        updateForegroundStatus,

    };
};