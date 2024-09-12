import { useStore_MicThreshold, useStore_EnableAutomaticMicThreshold } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useMicThreshold = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { updateMicThreshold, currentMicThreshold } = useStore_MicThreshold();
    const { updateEnableAutomaticMicThreshold, currentEnableAutomaticMicThreshold } = useStore_EnableAutomaticMicThreshold();

    const getMicThreshold = () => {
        asyncStdoutToPython("/config/input_mic_energy_threshold");
    };

    const setMicThreshold = (mic_threshold) => {
        asyncStdoutToPython("/controller/callback_set_mic_energy_threshold", mic_threshold);
    };

    const getEnableAutomaticMicThreshold = () => {
        updateEnableAutomaticMicThreshold(() => new Promise(() => {}));
        asyncStdoutToPython("/config/input_mic_dynamic_energy_threshold");
    };

    const toggleEnableAutomaticMicThreshold = () => {
        updateEnableAutomaticMicThreshold(() => new Promise(() => {}));
        if (currentEnableAutomaticMicThreshold.data) {
            asyncStdoutToPython("/controller/callback_disable_mic_dynamic_energy_threshold");
        } else {
            asyncStdoutToPython("/controller/callback_enable_mic_dynamic_energy_threshold");
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