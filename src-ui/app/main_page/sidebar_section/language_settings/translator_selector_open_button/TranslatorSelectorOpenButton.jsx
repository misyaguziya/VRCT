import { useTranslation } from "react-i18next";

import styles from "./TranslatorSelectorOpenButton.module.scss";
import { TranslatorSelector } from "./translator_selector/TranslatorSelector";
import { useStore_IsOpenedTranslatorSelector } from "@store";
import { useLanguageSettings } from "@logics_main/useLanguageSettings";

export const TranslatorSelectorOpenButton = () => {
    const { t } = useTranslation();
    const {
        currentSelectedPresetTabNumber,
        currentTranslationEngines,
        getTranslationEngines,
        currentSelectedTranslationEngines,
    } = useLanguageSettings();

    // console.log(currentTranslationEngines, currentSelectedTranslationEngines);
    const selected_translator_name = (currentTranslationEngines.state === "loading")
    ? "Loading..."
    : currentTranslationEngines.data.find(
        translator_data => translator_data.translator_id === currentSelectedTranslationEngines[currentSelectedPresetTabNumber.data]
    )?.translator_name;


    const { currentIsOpenedTranslatorSelector, updateIsOpenedTranslatorSelector} = useStore_IsOpenedTranslatorSelector();

    const openTranslatorSelector = () => {
        getTranslationEngines();
        updateIsOpenedTranslatorSelector(!currentIsOpenedTranslatorSelector);
    };

    return (
        <div className={styles.container}>
            <div className={styles.translator_selector_button} onClick={openTranslatorSelector}>
                <p className={styles.label}>{t("main_page.translator")}: </p>
                <p className={styles.label}>{selected_translator_name}</p>
            </div>
            {currentIsOpenedTranslatorSelector &&
                <TranslatorSelector
                    selected_translator_id={currentSelectedTranslationEngines}
                    translation_engines={currentTranslationEngines}
                />
            }
        </div>
    );
};