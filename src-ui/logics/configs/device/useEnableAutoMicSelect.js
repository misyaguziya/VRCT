import { useStore_EnableAutoMicSelect } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useEnableAutoMicSelect = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentEnableAutoMicSelect, updateEnableAutoMicSelect, pendingEnableAutoMicSelect } = useStore_EnableAutoMicSelect();

    const getEnableAutoMicSelect = () => {
        pendingEnableAutoMicSelect();
        asyncStdoutToPython("/get/data/auto_mic_select");
    };

    const toggleEnableAutoMicSelect = () => {
        pendingEnableAutoMicSelect();
        if (currentEnableAutoMicSelect.data) {
            asyncStdoutToPython("/set/disable/auto_mic_select");
        } else {
            asyncStdoutToPython("/set/enable/auto_mic_select");
        }
    };

    return {
        currentEnableAutoMicSelect,
        getEnableAutoMicSelect,
        updateEnableAutoMicSelect,
        toggleEnableAutoMicSelect,
    };
};