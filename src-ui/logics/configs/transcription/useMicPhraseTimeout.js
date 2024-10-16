import { useStore_MicPhraseTimeout } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useMicPhraseTimeout = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentMicPhraseTimeout, updateMicPhraseTimeout, pendingMicPhraseTimeout } = useStore_MicPhraseTimeout();

    const getMicPhraseTimeout = () => {
        pendingMicPhraseTimeout();
        asyncStdoutToPython("/get/data/mic_phrase_timeout");
    };

    const setMicPhraseTimeout = (selected_mic_phrase_timeout) => {
        pendingMicPhraseTimeout();
        asyncStdoutToPython("/set/data/mic_phrase_timeout", selected_mic_phrase_timeout);
    };

    return {
        currentMicPhraseTimeout,
        getMicPhraseTimeout,
        updateMicPhraseTimeout,
        setMicPhraseTimeout,
    };
};