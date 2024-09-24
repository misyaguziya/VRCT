import { useStore_SpeakerThreshold, useStore_EnableAutomaticSpeakerThreshold } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSpeakerThreshold = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { updateSpeakerThreshold, currentSpeakerThreshold } = useStore_SpeakerThreshold();
    const { updateEnableAutomaticSpeakerThreshold, currentEnableAutomaticSpeakerThreshold, pendingEnableAutomaticSpeakerThreshold } = useStore_EnableAutomaticSpeakerThreshold();

    const getSpeakerThreshold = () => {
        asyncStdoutToPython("/get/data/speaker_energy_threshold");
    };

    const setSpeakerThreshold = (speaker_threshold) => {
        asyncStdoutToPython("/set/data/speaker_energy_threshold", speaker_threshold);
    };

    const getEnableAutomaticSpeakerThreshold = () => {
        pendingEnableAutomaticSpeakerThreshold();
        asyncStdoutToPython("/get/data/speaker_automatic_threshold");
    };

    const toggleEnableAutomaticSpeakerThreshold = () => {
        pendingEnableAutomaticSpeakerThreshold();
        if (currentEnableAutomaticSpeakerThreshold.data) {
            asyncStdoutToPython("/set/disable/speaker_automatic_threshold");
        } else {
            asyncStdoutToPython("/set/enable/speaker_automatic_threshold");
        }
    };

    return {
        currentSpeakerThreshold,
        getSpeakerThreshold,
        setSpeakerThreshold,
        updateSpeakerThreshold,

        currentEnableAutomaticSpeakerThreshold,
        getEnableAutomaticSpeakerThreshold,
        toggleEnableAutomaticSpeakerThreshold,
        updateEnableAutomaticSpeakerThreshold,
    };
};