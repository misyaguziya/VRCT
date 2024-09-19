import { useStore_SpeakerThreshold, useStore_EnableAutomaticSpeakerThreshold } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSpeakerThreshold = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { updateSpeakerThreshold, currentSpeakerThreshold } = useStore_SpeakerThreshold();
    const { updateEnableAutomaticSpeakerThreshold, currentEnableAutomaticSpeakerThreshold } = useStore_EnableAutomaticSpeakerThreshold();

    const getSpeakerThreshold = () => {
        asyncStdoutToPython("/get/speaker_energy_threshold");
    };

    const setSpeakerThreshold = (speaker_threshold) => {
        asyncStdoutToPython("/set/speaker_energy_threshold", speaker_threshold);
    };

    const getEnableAutomaticSpeakerThreshold = () => {
        updateEnableAutomaticSpeakerThreshold(() => new Promise(() => {}));
        asyncStdoutToPython("/get/speaker_dynamic_energy_threshold");
    };

    const toggleEnableAutomaticSpeakerThreshold = () => {
        updateEnableAutomaticSpeakerThreshold(() => new Promise(() => {}));
        if (currentEnableAutomaticSpeakerThreshold.data) {
            asyncStdoutToPython("/set/disable_speaker_dynamic_energy_threshold");
        } else {
            asyncStdoutToPython("/set/enable_speaker_dynamic_energy_threshold");
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