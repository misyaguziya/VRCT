import { useStore_MicMaxWords } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useMicMaxWords = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentMicMaxWords, updateMicMaxWords, pendingMicMaxWords } = useStore_MicMaxWords();

    const getMicMaxWords = () => {
        pendingMicMaxWords();
        asyncStdoutToPython("/get/data/mic_max_phrases");
    };

    const setMicMaxWords = (selected_mic_max_phrases) => {
        pendingMicMaxWords();
        asyncStdoutToPython("/set/data/mic_max_phrases", selected_mic_max_phrases);
    };

    return {
        currentMicMaxWords,
        getMicMaxWords,
        updateMicMaxWords,
        setMicMaxWords,
    };
};