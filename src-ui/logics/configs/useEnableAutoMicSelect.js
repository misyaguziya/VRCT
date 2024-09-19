import { useStore_EnableAutoMicSelect } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useEnableAutoMicSelect = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentEnableAutoMicSelect, updateEnableAutoMicSelect } = useStore_EnableAutoMicSelect();

    const getEnableAutoMicSelect = () => {
        updateEnableAutoMicSelect(() => new Promise(() => {}));
        asyncStdoutToPython("/get/auto_mic_select");
    };

    const toggleEnableAutoMicSelect = () => {
        updateEnableAutoMicSelect(() => new Promise(() => {}));
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