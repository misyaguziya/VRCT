import { useStore_SelectedPresetTabNumber, useStore_EnableMultiTranslation, useStore_SelectedYourLanguages, useStore_SelectedTargetLanguages, useStore_TranslationEngines, useStore_SelectedTranslationEngines } from "@store";
import { useStdoutToPython } from "@useStdoutToPython";

export const useLanguageSettings = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const {
        currentEnableMultiTranslation,
        updateEnableMultiTranslation,
        pendingEnableMultiTranslation,
    } = useStore_EnableMultiTranslation();
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

    const getEnableMultiTranslation = () => {
        pendingEnableMultiTranslation();
        asyncStdoutToPython("/get/data/multi_language_translation");
    };

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
        asyncStdoutToPython("/get/data/translation_engines");
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

    const runLanguageSwap = () => {
        pendingSelectedYourLanguages();
        pendingSelectedTargetLanguages();
        asyncStdoutToPython("/run/swap_your_language_and_target_language");
    };


    return {
        currentSelectedPresetTabNumber,
        getSelectedPresetTabNumber,
        updateSelectedPresetTabNumber,
        setSelectedPresetTabNumber,

        currentEnableMultiTranslation,
        getEnableMultiTranslation,
        updateEnableMultiTranslation,
        // setEnableMultiTranslation,

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

        currentSelectedTranslationEngines,
        getSelectedTranslationEngines,
        updateSelectedTranslationEngines,
        setSelectedTranslationEngines,

        runLanguageSwap,
    };
};