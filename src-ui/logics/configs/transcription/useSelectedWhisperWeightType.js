import { useStore_SelectedWhisperWeightType } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useSelectedWhisperWeightType = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSelectedWhisperWeightType, updateSelectedWhisperWeightType, pendingSelectedWhisperWeightType } = useStore_SelectedWhisperWeightType();

    const getSelectedWhisperWeightType = () => {
        pendingSelectedWhisperWeightType();
        asyncStdoutToPython("/get/data/whisper_weight_type");
    };

    const setSelectedWhisperWeightType = (selected_whisper_weight_type) => {
        pendingSelectedWhisperWeightType();
        asyncStdoutToPython("/set/data/whisper_weight_type", selected_whisper_weight_type);
    };

    return {
        currentSelectedWhisperWeightType,
        getSelectedWhisperWeightType,
        updateSelectedWhisperWeightType,
        setSelectedWhisperWeightType,
    };
};