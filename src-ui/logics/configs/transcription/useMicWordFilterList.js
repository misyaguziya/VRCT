import { useStore_MicWordFilterList } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useMicWordFilterList = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentMicWordFilterList, updateMicWordFilterList, pendingMicWordFilterList } = useStore_MicWordFilterList();

    const getMicWordFilterList = () => {
        pendingMicWordFilterList();
        asyncStdoutToPython("/get/data/mic_word_filter");
    };

    const setMicWordFilterList = (selected_mic_word_filter) => {
        pendingMicWordFilterList();
        asyncStdoutToPython("/set/data/mic_word_filter", selected_mic_word_filter);
    };

    return {
        currentMicWordFilterList,
        getMicWordFilterList,
        updateMicWordFilterList,
        setMicWordFilterList,
    };
};