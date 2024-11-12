import { useTranslation } from "react-i18next";

import styles from "./TranslatorSelectorOpenButton.module.scss";
import { TranslatorSelector } from "./translator_selector/TranslatorSelector";
import { useStore_IsOpenedTranslatorSelector } from "@store";
import { useLanguageSettings } from "@logics_main";

export const TranslatorSelectorOpenButton = () => {
    const { t } = useTranslation();
    const {
        currentSelectedPresetTabNumber,
        currentTranslationEngines,
        currentSelectedTranslationEngines,
    } = useLanguageSettings();

    const selected_label = (currentTranslationEngines.state === "pending")
    ? "Loading..."
    : currentTranslationEngines.data.find(
        translator_data => translator_data.id === currentSelectedTranslationEngines.data[currentSelectedPresetTabNumber.data]
    )?.label;


    const { currentIsOpenedTranslatorSelector, updateIsOpenedTranslatorSelector} = useStore_IsOpenedTranslatorSelector();

    const openTranslatorSelector = () => {
        updateIsOpenedTranslatorSelector(!currentIsOpenedTranslatorSelector.data);
    };

    return (
        <div className={styles.container}>
            <div className={styles.translator_selector_button} onClick={openTranslatorSelector}>
                <p className={styles.label}>{t("main_page.translator")}: </p>
                <p className={styles.label}>{selected_label}</p>
            </div>
            {currentIsOpenedTranslatorSelector.data &&
                <TranslatorSelector
                    selected_id={currentSelectedTranslationEngines}
                    translation_engines={currentTranslationEngines}
                />
            }
        </div>
    );
};