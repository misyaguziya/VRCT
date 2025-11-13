import { useStore_SelectedPresetTabNumber, useStore_SelectedYourLanguages, useStore_SelectedTargetLanguages, useStore_TranslationEngines, useStore_SelectedTranslationEngines, useStore_SelectableLanguageList } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";
import { translator_status } from "@ui_configs";

export const useLanguageSettings = () => {
    const { asyncStdoutToPython } = useStdoutToPython();

    const {
        currentSelectedYourLanguages,
        updateSelectedYourLanguages,
        pendingSelectedYourLanguages,
    } = useStore_SelectedYourLanguages();
    const {
        currentSelectedTargetLanguages,
        updateSelectedTargetLanguages,
        pendingSelectedTargetLanguages,
    } = useStore_SelectedTargetLanguages();
    const {
        currentSelectedPresetTabNumber,
        updateSelectedPresetTabNumber,
        pendingSelectedPresetTabNumber,
    } = useStore_SelectedPresetTabNumber();
    const {
        currentTranslationEngines,
        updateTranslationEngines,
        pendingTranslationEngines,
    } = useStore_TranslationEngines();
    const {
        currentSelectedTranslationEngines,
        updateSelectedTranslationEngines,
        pendingSelectedTranslationEngines,
    } = useStore_SelectedTranslationEngines();

    const {
        currentSelectableLanguageList,
        updateSelectableLanguageList,
    } = useStore_SelectableLanguageList();


    const getSelectedPresetTabNumber = () => {
        pendingSelectedPresetTabNumber();
        asyncStdoutToPython("/get/data/selected_tab_no");
    };

    const setSelectedPresetTabNumber = (preset_number) => {
        pendingSelectedPresetTabNumber();

        asyncStdoutToPython("/set/data/selected_tab_no", preset_number);
    };


    const getSelectedYourLanguages = () => {
        pendingSelectedPresetTabNumber();
        asyncStdoutToPython("/get/data/selected_your_languages");
    };

    const setSelectedYourLanguages = (selected_language_data) => {
        pendingSelectedYourLanguages();
        const send_obj = {
            ...currentSelectedYourLanguages.data,
            [currentSelectedPresetTabNumber.data]: {
                1: { // Fixed key 1.
                    language: selected_language_data.language,
                    country: selected_language_data.country,
                    enable: true,
                }
            }
        };
        asyncStdoutToPython("/set/data/selected_your_languages", send_obj);
    };


    const getSelectedTargetLanguages = () => {
        pendingSelectedTargetLanguages();
        asyncStdoutToPython("/get/data/selected_target_languages");
    };

    const setSelectedTargetLanguages = (selected_language_data) => {
        pendingSelectedTargetLanguages();
        let send_obj = currentSelectedTargetLanguages.data;
        send_obj[currentSelectedPresetTabNumber.data][selected_language_data.target_key].language = selected_language_data.language,
        send_obj[currentSelectedPresetTabNumber.data][selected_language_data.target_key].country = selected_language_data.country,
        asyncStdoutToPython("/set/data/selected_target_languages", send_obj);
    };

    const addTargetLanguage = () => {
        pendingSelectedTargetLanguages();
        let send_obj = currentSelectedTargetLanguages.data;
        let target_key = "2";
        if (send_obj[currentSelectedPresetTabNumber.data]["2"].enable === true) {
            target_key = "3";
        }
        send_obj[currentSelectedPresetTabNumber.data][target_key].enable = true,
        asyncStdoutToPython("/set/data/selected_target_languages", send_obj);
    };
    const removeTargetLanguage = () => {
        pendingSelectedTargetLanguages();
        let send_obj = currentSelectedTargetLanguages.data;
        let target_key = "3";
        if (send_obj[currentSelectedPresetTabNumber.data]["3"].enable === false) {
            target_key = "2";
        }
        send_obj[currentSelectedPresetTabNumber.data][target_key].enable = false,
        asyncStdoutToPython("/set/data/selected_target_languages", send_obj);
    };


    const getTranslationEngines = () => {
        pendingTranslationEngines();
        asyncStdoutToPython("/get/data/selectable_translation_engines");
    };

    const updateTranslatorAvailability = (payload) => {
        const keys = payload;
        const updated_list = translator_status.map(translator => ({
            ...translator,
            is_available: keys.includes(translator.id),
        }));
        updateTranslationEngines(updated_list);
    };


    const getSelectedTranslationEngines = () => {
        pendingSelectedTranslationEngines();
        asyncStdoutToPython("/get/data/selected_translation_engines");
    };

    const setSelectedTranslationEngines = (selected_translator) => {
        pendingSelectedTranslationEngines();
        let send_obj = currentSelectedTranslationEngines.data;
        send_obj[currentSelectedPresetTabNumber.data] = selected_translator;
        asyncStdoutToPython("/set/data/selected_translation_engines", send_obj);
    };

    const swapSelectedLanguages = () => {
        pendingSelectedYourLanguages();
        pendingSelectedTargetLanguages();
        asyncStdoutToPython("/run/swap_your_language_and_target_language");
    };

    const updateBothSelectedLanguages = (payload) => {
        updateSelectedYourLanguages(payload.your);
        updateSelectedTargetLanguages(payload.target);
    };


    const getSelectableLanguageList = () => {
        asyncStdoutToPython("/get/data/selectable_language_list");
    };


    return {
        currentSelectedPresetTabNumber,
        getSelectedPresetTabNumber,
        updateSelectedPresetTabNumber,
        setSelectedPresetTabNumber,

        currentSelectedYourLanguages,
        getSelectedYourLanguages,
        updateSelectedYourLanguages,
        setSelectedYourLanguages,

        currentSelectedTargetLanguages,
        getSelectedTargetLanguages,
        updateSelectedTargetLanguages,
        setSelectedTargetLanguages,

        addTargetLanguage,
        removeTargetLanguage,

        currentTranslationEngines,
        getTranslationEngines,
        updateTranslationEngines,
        updateTranslatorAvailability,

        currentSelectedTranslationEngines,
        getSelectedTranslationEngines,
        updateSelectedTranslationEngines,
        setSelectedTranslationEngines,

        swapSelectedLanguages,
        updateBothSelectedLanguages,

        currentSelectableLanguageList,
        getSelectableLanguageList,
        updateSelectableLanguageList,
    };
};