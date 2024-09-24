import { useStore_SelectableLanguageList } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSelectableLanguageList = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSelectableLanguageList, updateSelectableLanguageList } = useStore_SelectableLanguageList();

    const getSelectableLanguageList = () => {
        asyncStdoutToPython("/get/data/selectable_language_list");
    };

    return {
        currentSelectableLanguageList,
        getSelectableLanguageList,
        updateSelectableLanguageList,
    };
};