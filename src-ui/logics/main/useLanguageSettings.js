import { useStore_SelectedPresetTabNumber, useStore_EnableMultiTranslation, useStore_SelectedYourLanguages, useStore_SelectedTargetLanguages, useStore_TranslationEngines, useStore_SelectedTranslationEngines } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

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
        asyncStdoutToPython("/get/multi_language_translation");
    };

    const getSelectedPresetTabNumber = () => {
        pendingSelectedPresetTabNumber();
        asyncStdoutToPython("/get/selected_tab_no");
    };

    const setSelectedPresetTabNumber = (preset_number) => {
        pendingSelectedPresetTabNumber();

        asyncStdoutToPython("/set/selected_tab_no", preset_number);
    };


    const getSelectedYourLanguages = () => {
        pendingSelectedPresetTabNumber();
        asyncStdoutToPython("/get/selected_your_languages");
    };

    const setSelectedYourLanguages = (selected_language_data) => {
        pendingSelectedYourLanguages();
        const send_obj = {
            ...currentSelectedYourLanguages.data,
            [currentSelectedPresetTabNumber.data]: {
                primary: {
                    language: selected_language_data.language,
                    country: selected_language_data.country,
                }
            }
        };
        asyncStdoutToPython("/set/selected_your_languages", send_obj);
    };


    const getSelectedTargetLanguages = () => {
        pendingSelectedTargetLanguages();
        asyncStdoutToPython("/get/selected_target_languages");
    };

    const setSelectedTargetLanguages = (selected_language_data) => {
        pendingSelectedTargetLanguages();
        let send_obj = currentSelectedTargetLanguages.data;

        send_obj[currentSelectedPresetTabNumber.data].primary.language = selected_language_data.language,
        send_obj[currentSelectedPresetTabNumber.data].primary.country = selected_language_data.country,

        asyncStdoutToPython("/set/selected_target_languages", send_obj);
    };


    const getTranslationEngines = () => {
        pendingTranslationEngines();
        asyncStdoutToPython("/get/list_translation_engines");
    };

    const getSelectedTranslationEngines = () => {
        pendingSelectedTranslationEngines();
        asyncStdoutToPython("/get/selected_translator_engines");
    };

    const setSelectedTranslationEngines = (selected_translator) => {
        pendingSelectedTranslationEngines();
        let send_obj = currentSelectedTranslationEngines.data;
        send_obj[currentSelectedPresetTabNumber.data] = selected_translator;
        asyncStdoutToPython("/set/selected_translator_engines", send_obj);
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