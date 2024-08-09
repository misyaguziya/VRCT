import { useTranslation } from "react-i18next";

import styles from "./TranslatorSelectorOpenButton.module.scss";
import { TranslatorSelector } from "./translator_selector/TranslatorSelector";
import { useTranslatorListStatus, useSelectedTranslatorIdStatus, useIsOpenedTranslatorSelector } from "@store";

export const TranslatorSelectorOpenButton = () => {
    const { t } = useTranslation();
    const { currentSelectedTranslatorIdStatus } = useSelectedTranslatorIdStatus();
    const { currentTranslatorListStatus } = useTranslatorListStatus();
    const currentTranslator = currentTranslatorListStatus.find(
        translator_data => translator_data.translator_key === currentSelectedTranslatorIdStatus
    );

    const { currentIsOpenedTranslatorSelector, updateIsOpenedTranslatorSelector} = useIsOpenedTranslatorSelector();

    const openTranslatorSelector = () => updateIsOpenedTranslatorSelector(!currentIsOpenedTranslatorSelector);

    return (
        <div className={styles.container}>
            <div className={styles.translator_selector_button} onClick={openTranslatorSelector}>
                <p className={styles.label}>{t("main_page.translator")}</p>
                <p className={styles.label}>{currentTranslator?.translator_name}</p>
            </div>
            {currentIsOpenedTranslatorSelector && <TranslatorSelector />}
        </div>
    );
};