import { useTranslation } from "react-i18next";

import styles from "./TranslatorSelectorOpenButton.module.scss";
import { TranslatorSelector } from "./translator_selector/TranslatorSelector";
import { useStore_TranslatorList, useStore_SelectedTranslatorId, useStore_IsOpenedTranslatorSelector } from "@store";

export const TranslatorSelectorOpenButton = () => {
    const { t } = useTranslation();
    const { currentSelectedTranslatorId } = useStore_SelectedTranslatorId();
    const { currentTranslatorList } = useStore_TranslatorList();
    const currentTranslator = currentTranslatorList.find(
        translator_data => translator_data.translator_key === currentSelectedTranslatorId
    );

    const { currentIsOpenedTranslatorSelector, updateIsOpenedTranslatorSelector} = useStore_IsOpenedTranslatorSelector();

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