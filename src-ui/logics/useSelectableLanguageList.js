import { useStore_SelectableLanguageList } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useSelectableLanguageList = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSelectableLanguageList, updateSelectableLanguageList } = useStore_SelectableLanguageList();

    const getSelectableLanguageList = () => {
        asyncStdoutToPython("/get/list_languages");
    };

    return {
        currentSelectableLanguageList,
        getSelectableLanguageList,
        updateSelectableLanguageList,
    };
};