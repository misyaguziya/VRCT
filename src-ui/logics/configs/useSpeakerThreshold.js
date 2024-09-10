import { useStore_SpeakerThreshold } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSpeakerThreshold = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { updateSpeakerThreshold, currentSpeakerThreshold } = useStore_SpeakerThreshold();

    const getSpeakerThreshold = () => {
        asyncStdoutToPython("/config/input_speaker_energy_threshold");
    };

    const setSpeakerThreshold = (speaker_threshold) => {
        asyncStdoutToPython("/controller/callback_set_speaker_energy_threshold", speaker_threshold);
    };

    return {
        currentSpeakerThreshold,
        getSpeakerThreshold,
        setSpeakerThreshold,
        updateSpeakerThreshold,
    };
};