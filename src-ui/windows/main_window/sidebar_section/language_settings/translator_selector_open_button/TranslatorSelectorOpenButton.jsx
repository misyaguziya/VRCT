import { useTranslation } from "react-i18next";

import styles from "./TranslatorSelectorOpenButton.module.scss";
import { TranslatorSelector } from "./translator_selector/TranslatorSelector";
import { useTranslatorList, useSelectedTranslator, useOpenedTranslatorSelector } from "@store";

export const TranslatorSelectorOpenButton = () => {
    const { t } = useTranslation();
    const { currentSelectedTranslator } = useSelectedTranslator();
    const { currentTranslatorList } = useTranslatorList();
    const currentTranslator = currentTranslatorList.find(
        translator_data => translator_data.translator_key === currentSelectedTranslator
    );

    const { currentOpenedTranslatorSelector, updateOpenedTranslatorSelector} = useOpenedTranslatorSelector();

    const openTranslatorSelector = () => updateOpenedTranslatorSelector(!currentOpenedTranslatorSelector);

    return (
        <div className={styles.container}>
            <div className={styles.translator_selector_button} onClick={openTranslatorSelector}>
                <p className={styles.label}>{t("main_window.translator")}</p>
                <p className={styles.label}>{currentTranslator?.translator_name}</p>
            </div>
            {currentOpenedTranslatorSelector && <TranslatorSelector />}
        </div>
    );
};