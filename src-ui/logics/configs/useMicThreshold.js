import { useStore_MicThreshold } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useMicThreshold = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { updateMicThreshold, currentMicThreshold } = useStore_MicThreshold();

    const getMicThreshold = () => {
        asyncStdoutToPython("/config/input_mic_energy_threshold");
    };

    const setMicThreshold = (mic_threshold) => {
        asyncStdoutToPython("/controller/callback_set_mic_energy_threshold", mic_threshold);
    };

    return {
        currentMicThreshold,
        getMicThreshold,
        setMicThreshold,
        updateMicThreshold,
    };
};