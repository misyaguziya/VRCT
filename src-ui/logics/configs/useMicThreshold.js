import { useStore_MicThreshold, useStore_EnableAutomaticMicThreshold } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useMicThreshold = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { updateMicThreshold, currentMicThreshold } = useStore_MicThreshold();
    const { updateEnableAutomaticMicThreshold, currentEnableAutomaticMicThreshold, pendingEnableAutomaticMicThreshold } = useStore_EnableAutomaticMicThreshold();

    const getMicThreshold = () => {
        asyncStdoutToPython("/get/data/mic_threshold");
    };

    const setMicThreshold = (mic_threshold) => {
        asyncStdoutToPython("/set/data/mic_threshold", mic_threshold);
    };

    const getEnableAutomaticMicThreshold = () => {
        pendingEnableAutomaticMicThreshold();
        asyncStdoutToPython("/get/data/mic_automatic_threshold");
    };

    const toggleEnableAutomaticMicThreshold = () => {
        pendingEnableAutomaticMicThreshold();
        if (currentEnableAutomaticMicThreshold.data) {
            asyncStdoutToPython("/set/disable/mic_automatic_threshold");
        } else {
            asyncStdoutToPython("/set/enable/mic_automatic_threshold");
        }
    };

    return {
        currentMicThreshold,
        getMicThreshold,
        setMicThreshold,
        updateMicThreshold,

        currentEnableAutomaticMicThreshold,
        getEnableAutomaticMicThreshold,
        toggleEnableAutomaticMicThreshold,
        updateEnableAutomaticMicThreshold,
    };
};