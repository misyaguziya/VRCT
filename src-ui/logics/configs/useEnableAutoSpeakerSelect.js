import { useStore_EnableAutoSpeakerSelect } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useEnableAutoSpeakerSelect = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentEnableAutoSpeakerSelect, updateEnableAutoSpeakerSelect } = useStore_EnableAutoSpeakerSelect();

    const getEnableAutoSpeakerSelect = () => {
        updateEnableAutoSpeakerSelect(() => new Promise(() => {}));
        asyncStdoutToPython("/get/auto_speaker_select");
    };

    const toggleEnableAutoSpeakerSelect = () => {
        updateEnableAutoSpeakerSelect(() => new Promise(() => {}));
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