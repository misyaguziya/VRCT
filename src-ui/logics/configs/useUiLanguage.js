import { useStore_UiLanguage } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useUiLanguage = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentUiLanguage, updateUiLanguage } = useStore_UiLanguage();

    const getUiLanguage = () => {
        updateUiLanguage(() => new Promise(() => {}));
        asyncStdoutToPython("/config/ui_language");
    };

    const setUiLanguage = (selected_ui_language) => {
        updateUiLanguage(() => new Promise(() => {}));
        asyncStdoutToPython("/controller/callback_set_ui_language", selected_ui_language);
    };

    return {
        currentUiLanguage,
        getUiLanguage,
        updateUiLanguage,
        setUiLanguage,
    };
};