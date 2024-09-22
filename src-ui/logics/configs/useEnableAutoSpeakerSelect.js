import { useStore_EnableAutoSpeakerSelect } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useEnableAutoSpeakerSelect = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentEnableAutoSpeakerSelect, updateEnableAutoSpeakerSelect, pendingEnableAutoSpeakerSelect } = useStore_EnableAutoSpeakerSelect();

    const getEnableAutoSpeakerSelect = () => {
        pendingEnableAutoSpeakerSelect();
        asyncStdoutToPython("/get/auto_speaker_select");
    };

    const toggleEnableAutoSpeakerSelect = () => {
        pendingEnableAutoSpeakerSelect();
        if (currentEnableAutoSpeakerSelect.data) {
            asyncStdoutToPython("/set/disable_auto_speaker_select");
        } else {
            asyncStdoutToPython("/set/enable_auto_speaker_select");
        }
    };

    return {
        currentEnableAutoSpeakerSelect,
        getEnableAutoSpeakerSelect,
        updateEnableAutoSpeakerSelect,
        toggleEnableAutoSpeakerSelect,
    };
};