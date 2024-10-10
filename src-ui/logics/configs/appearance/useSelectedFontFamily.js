import { useStore_SelectedFontFamily } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSelectedFontFamily = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSelectedFontFamily, updateSelectedFontFamily, pendingSelectedFontFamily } = useStore_SelectedFontFamily();

    const getSelectedFontFamily = () => {
        pendingSelectedFontFamily();
        asyncStdoutToPython("/get/data/font_family");
    };

    const setSelectedFontFamily = (selected_font_family) => {
        pendingSelectedFontFamily();
        asyncStdoutToPython("/set/data/font_family", selected_font_family);
    };

    return {
        currentSelectedFontFamily,
        getSelectedFontFamily,
        updateSelectedFontFamily,
        setSelectedFontFamily,
    };
};