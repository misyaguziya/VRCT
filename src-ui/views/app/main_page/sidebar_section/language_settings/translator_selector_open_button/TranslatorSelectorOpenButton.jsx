import { useI18n } from "@useI18n";
import { updateLabelsById } from "@utils";
import styles from "./TranslatorSelectorOpenButton.module.scss";
import { TranslatorSelector } from "./translator_selector/TranslatorSelector";
import { useStore_IsOpenedTranslatorSelector } from "@store";
import { useLanguageSettings } from "@logics_main";
import WarningSvg from "@images/warning.svg?react";

export const TranslatorSelectorOpenButton = () => {
    const { t } = useI18n();
    const {
        currentSelectedYourLanguages,
        currentSelectedTargetLanguages,
        currentSelectedPresetTabNumber,
        currentTranslationEngines,
        currentSelectedTranslationEngines,
    } = useLanguageSettings();

    // const new_labels = [
    //     {id: "CTranslate2", label: "AI\nCTranslate2"}
    // ];

    const translation_engines = currentTranslationEngines.data;
    // const translation_engines = updateLabelsById(currentTranslationEngines.data, new_labels);

    const selected_engine_id = currentSelectedTranslationEngines.data[currentSelectedPresetTabNumber.data];

    const checkIsSelectedSameLanguage = () => {
        const your_language_data = currentSelectedYourLanguages.data[currentSelectedPresetTabNumber.data];
        const target_language_data = currentSelectedTargetLanguages.data[currentSelectedPresetTabNumber.data];

        const yourLanguage = your_language_data["1"];
        const yourLanguageName = yourLanguage.language;
        const yourCountry = yourLanguage.country;

        let is_selected_same_language = false;

        for (const key in target_language_data) {
            const targetLanguage = target_language_data[key];

            if (targetLanguage.enable) {
                const targetLanguageName = targetLanguage.language;
                const targetCountry = targetLanguage.country;

                if (yourLanguageName === targetLanguageName && yourCountry === targetCountry) {
                    is_selected_same_language = true;
                    break;
                }
            }
        }

        return is_selected_same_language;
    };

    const is_selected_same_language = checkIsSelectedSameLanguage();

    const getSelectedLabel = () => {

        const selected_engine = translation_engines.find(
            d => d.id === selected_engine_id
        );
        return selected_engine?.label;
    };

    const is_loading = currentTranslationEngines.state === "pending";
    const selected_label = is_loading ? "Loading..." : getSelectedLabel();


    const { currentIsOpenedTranslatorSelector, updateIsOpenedTranslatorSelector} = useStore_IsOpenedTranslatorSelector();

    const openTranslatorSelector = () => {
        updateIsOpenedTranslatorSelector(!currentIsOpenedTranslatorSelector.data);
    };

    return (
        <div className={styles.container}>
            <div className={styles.translator_selector_button} onClick={openTranslatorSelector}>
                <p className={styles.label}>{t("main_page.translator")}:</p>
                <p className={styles.label}>{selected_label}</p>
                {is_selected_same_language
                    ? <WarningSvg className={styles.warning_svg}/>
                    : null
                }
            </div>
            {currentIsOpenedTranslatorSelector.data &&
                <TranslatorSelector
                    selected_id={selected_engine_id}
                    translation_engines={translation_engines}
                    is_selected_same_language={is_selected_same_language}
                />
            }
        </div>
    );
};