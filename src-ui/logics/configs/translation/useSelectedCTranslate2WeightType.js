import { useStore_SelectedCTranslate2WeightType } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSelectedCTranslate2WeightType = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSelectedCTranslate2WeightType, updateSelectedCTranslate2WeightType, pendingSelectedCTranslate2WeightType } = useStore_SelectedCTranslate2WeightType();

    const getSelectedCTranslate2WeightType = () => {
        pendingSelectedCTranslate2WeightType();
        asyncStdoutToPython("/get/data/ctranslate2_weight_type");
    };

    const setSelectedCTranslate2WeightType = (selected_ctranslate2_weight_type) => {
        pendingSelectedCTranslate2WeightType();
        asyncStdoutToPython("/set/data/ctranslate2_weight_type", selected_ctranslate2_weight_type);
    };

    return {
        currentSelectedCTranslate2WeightType,
        getSelectedCTranslate2WeightType,
        updateSelectedCTranslate2WeightType,
        setSelectedCTranslate2WeightType,
    };
};