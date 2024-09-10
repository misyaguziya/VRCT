import { useMicThreshold as useStoreMicThreshold } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useMicThreshold = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { updateMicThreshold, currentMicThreshold } = useStoreMicThreshold();

    const getMicThreshold = () => {
        asyncStdoutToPython("/config/input_mic_energy_threshold");
    };

    const setMicThreshold = (mic_threshold) => {
        asyncStdoutToPython("/controller/callback_set_mic_energy_threshold", mic_threshold);
    };

    return { getMicThreshold, setMicThreshold, currentMicThreshold, updateMicThreshold };
};