import { useStore_EnableAutoSpeakerSelect } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useEnableAutoSpeakerSelect = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentEnableAutoSpeakerSelect, updateEnableAutoSpeakerSelect } = useStore_EnableAutoSpeakerSelect();

    const getEnableAutoSpeakerSelect = () => {
        updateEnableAutoSpeakerSelect(() => new Promise(() => {}));
        asyncStdoutToPython("/config/enable_speaker_automatic_selection");
    };

    const toggleEnableAutoSpeakerSelect = () => {
        updateEnableAutoSpeakerSelect(() => new Promise(() => {}));
        if (currentEnableAutoSpeakerSelect.data) {
            asyncStdoutToPython("/controller/callback_disable_speaker_automatic_selection");
        } else {
            asyncStdoutToPython("/controller/callback_enable_speaker_automatic_selection");
        }
    };

    return {
        currentEnableAutoSpeakerSelect,
        getEnableAutoSpeakerSelect,
        updateEnableAutoSpeakerSelect,
        toggleEnableAutoSpeakerSelect,
    };
};