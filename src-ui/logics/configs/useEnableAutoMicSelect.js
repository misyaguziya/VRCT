import { useStore_EnableAutoMicSelect } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useEnableAutoMicSelect = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentEnableAutoMicSelect, updateEnableAutoMicSelect } = useStore_EnableAutoMicSelect();

    const getEnableAutoMicSelect = () => {
        updateEnableAutoMicSelect(() => new Promise(() => {}));
        asyncStdoutToPython("/config/enable_mic_automatic_selection");
    };

    const toggleEnableAutoMicSelect = () => {
        updateEnableAutoMicSelect(() => new Promise(() => {}));
        if (currentEnableAutoMicSelect.data) {
            asyncStdoutToPython("/controller/callback_disable_mic_automatic_selection");
        } else {
            asyncStdoutToPython("/controller/callback_enable_mic_automatic_selection");
        }
    };

    return {
        currentEnableAutoMicSelect,
        getEnableAutoMicSelect,
        updateEnableAutoMicSelect,
        toggleEnableAutoMicSelect,
    };
};