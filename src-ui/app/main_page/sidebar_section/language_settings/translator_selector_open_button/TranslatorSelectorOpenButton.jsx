import { useTranslation } from "react-i18next";
import { updateLabelsById } from "@utils";
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

    const new_labels = [
        {id: "CTranslate2", label: t("main_page.translator_ctranslate2")}
    ];

    const translation_engines = updateLabelsById(currentTranslationEngines.data, new_labels);

    const getSelectedLabel = () => {
        const selected_engine_id = currentSelectedTranslationEngines.data[currentSelectedPresetTabNumber.data];
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
                <p className={styles.label}>{t("main_page.translator")}: </p>
                <p className={styles.label}>{selected_label}</p>
            </div>
            {currentIsOpenedTranslatorSelector.data &&
                <TranslatorSelector
                    selected_id={currentSelectedTranslationEngines}
                    translation_engines={translation_engines}
                />
            }
        </div>
    );
};