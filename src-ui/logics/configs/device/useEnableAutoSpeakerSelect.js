import { useStore_EnableAutoSpeakerSelect } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useEnableAutoSpeakerSelect = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentEnableAutoSpeakerSelect, updateEnableAutoSpeakerSelect, pendingEnableAutoSpeakerSelect } = useStore_EnableAutoSpeakerSelect();

    const getEnableAutoSpeakerSelect = () => {
        pendingEnableAutoSpeakerSelect();
        asyncStdoutToPython("/get/data/auto_speaker_select");
    };

    const toggleEnableAutoSpeakerSelect = () => {
        pendingEnableAutoSpeakerSelect();
        if (currentEnableAutoSpeakerSelect.data) {
            asyncStdoutToPython("/set/disable/auto_speaker_select");
        } else {
            asyncStdoutToPython("/set/enable/auto_speaker_select");
        }
    };

    return {
        currentEnableAutoSpeakerSelect,
        getEnableAutoSpeakerSelect,
        updateEnableAutoSpeakerSelect,
        toggleEnableAutoSpeakerSelect,
    };
};