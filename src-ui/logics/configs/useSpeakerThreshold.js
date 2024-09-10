import { useSpeakerThreshold as useStoreSpeakerThreshold } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSpeakerThreshold = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { updateSpeakerThreshold, currentSpeakerThreshold } = useStoreSpeakerThreshold();

    const getSpeakerThreshold = () => {
        asyncStdoutToPython("/config/input_speaker_energy_threshold");
    };

    const setSpeakerThreshold = (speaker_threshold) => {
        asyncStdoutToPython("/controller/callback_set_speaker_energy_threshold", speaker_threshold);
    };

    return { getSpeakerThreshold, setSpeakerThreshold, currentSpeakerThreshold, updateSpeakerThreshold };
};