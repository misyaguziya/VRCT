import { useStore_MicWordFilterList } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

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

    const updateMicWordFilterList_FromBackend = (payload) => {
        updateMicWordFilterList((prev_list) => {
            const updated_list = [...prev_list.data];
            for (const value of payload) {
                const existing_item = updated_list.find(item => item.value === value);
                if (existing_item) {
                    existing_item.is_redoable = false;
                } else {
                    updated_list.push({ value, is_redoable: false });
                }
            }
            return updated_list;
        });
    };

    return {
        currentMicWordFilterList,
        getMicWordFilterList,
        updateMicWordFilterList,
        setMicWordFilterList,

        updateMicWordFilterList_FromBackend,
    };
};