import { getCurrent } from "@tauri-apps/api/window";

import {
    useState_Translation,
    useState_TranscriptionSend,
    useState_TranscriptionReceive,
    useState_Foreground,
} from "@store";

import { useStdoutToPython } from "./useStdoutToPython";

export const useMainFunction = () => {
    const {
        currentState_Translation,
        updateState_Translation,
        asyncUpdateState_Translation,
    } = useState_Translation();
    const {
        currentState_TranscriptionSend,
        updateState_TranscriptionSend,
        asyncUpdateState_TranscriptionSend,
    } = useState_TranscriptionSend();
    const {
        currentState_TranscriptionReceive,
        updateState_TranscriptionReceive,
        asyncUpdateState_TranscriptionReceive,
    } = useState_TranscriptionReceive();
    const {
        currentState_Foreground,
        updateState_Foreground,
    } = useState_Foreground();

    const { asyncStdoutToPython } = useStdoutToPython();

    const asyncPending = () => new Promise(() => {});
    return {
        toggleTranslation: () => {
            asyncStdoutToPython({id: "/controller/callback_toggle_translation", data: !currentState_Translation.data});
            asyncUpdateState_Translation(asyncPending);
        },
        currentState_Translation: currentState_Translation,
        updateState_Translation: (payload) => {
            updateState_Translation(payload.data);
        },

        toggleTranscriptionSend: () => {
            asyncStdoutToPython({id: "/controller/callback_toggle_transcription_send", data: !currentState_TranscriptionSend.data});
            asyncUpdateState_TranscriptionSend(asyncPending);
        },
        currentState_TranscriptionSend: currentState_TranscriptionSend,
        updateState_TranscriptionSend: (payload) => {
            updateState_TranscriptionSend(payload.data);
        },

        toggleTranscriptionReceive: () => {
            asyncStdoutToPython({id: "/controller/callback_toggle_transcription_receive", data: !currentState_TranscriptionReceive.data});
            asyncUpdateState_TranscriptionReceive(asyncPending);
        },
        currentState_TranscriptionReceive: currentState_TranscriptionReceive,
        updateState_TranscriptionReceive: (payload) => {
            updateState_TranscriptionReceive(payload.data);
        },

        toggleForeground: () => {
            const main_window = getCurrent();
            const is_foreground_enabled = !currentState_Foreground.data;
            main_window.setAlwaysOnTop(is_foreground_enabled);
            updateState_Foreground(is_foreground_enabled);

        },
        currentState_Foreground: currentState_Foreground,
    };
};

const asyncTestFunction = (...args) => {
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve(...args);
        }, 3000);
    });
};