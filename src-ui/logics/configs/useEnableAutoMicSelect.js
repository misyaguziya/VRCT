import { useStore_EnableAutoMicSelect } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useEnableAutoMicSelect = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentEnableAutoMicSelect, updateEnableAutoMicSelect, pendingEnableAutoMicSelect } = useStore_EnableAutoMicSelect();

    const getEnableAutoMicSelect = () => {
        pendingEnableAutoMicSelect();
        asyncStdoutToPython("/get/auto_mic_select");
    };

    const toggleEnableAutoMicSelect = () => {
        pendingEnableAutoMicSelect();
        if (currentEnableAutoMicSelect.data) {
            asyncStdoutToPython("/set/disable_auto_mic_select");
        } else {
            asyncStdoutToPython("/set/enable_auto_mic_select");
        }
    };

    return {
        currentEnableAutoMicSelect,
        getEnableAutoMicSelect,
        updateEnableAutoMicSelect,
        toggleEnableAutoMicSelect,
    };
};