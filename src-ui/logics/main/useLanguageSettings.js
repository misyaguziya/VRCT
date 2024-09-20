import { useStore_SelectedPresetTabNumber, useStore_EnableMultiTranslation, useStore_SelectedYourLanguages, useStore_SelectedTargetLanguages } from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

export const useLanguageSettings = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentEnableMultiTranslation, updateEnableMultiTranslation } = useStore_EnableMultiTranslation();
    const { currentSelectedYourLanguages, updateSelectedYourLanguages } = useStore_SelectedYourLanguages();
    const { currentSelectedTargetLanguages, updateSelectedTargetLanguages } = useStore_SelectedTargetLanguages();
    const { currentSelectedPresetTabNumber, updateSelectedPresetTabNumber } = useStore_SelectedPresetTabNumber();

    const getEnableMultiTranslation = () => {
        updateEnableMultiTranslation(() => new Promise(() => {}));
        asyncStdoutToPython("/get/multi_language_translation");
    };

    const getSelectedPresetTabNumber = () => {
        updateSelectedPresetTabNumber(() => new Promise(() => {}));
        asyncStdoutToPython("/get/selected_tab_no");
    };

    const setSelectedPresetTabNumber = (preset_number) => {
        updateSelectedPresetTabNumber(() => new Promise(() => {}));

        asyncStdoutToPython("/set/selected_tab_no", preset_number);
    };


    const getSelectedYourLanguages = () => {
        updateSelectedYourLanguages(() => new Promise(() => {}));
        asyncStdoutToPython("/get/selected_your_languages");
    };

    const setSelectedYourLanguages = (selected_language_data) => {
        // updateSelectedYourLanguages(() => new Promise(() => {}));
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
        updateSelectedTargetLanguages(() => new Promise(() => {}));
        asyncStdoutToPython("/get/selected_target_languages");
    };

    const setSelectedTargetLanguages = (selected_language_data) => {
        // updateSelectedTargetLanguages(() => new Promise(() => {}));
        let send_obj = currentSelectedTargetLanguages.data;

        send_obj[currentSelectedPresetTabNumber.data].primary.language = selected_language_data.language,
        send_obj[currentSelectedPresetTabNumber.data].primary.country = selected_language_data.country,

        asyncStdoutToPython("/set/selected_target_languages", send_obj);
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
    };
};