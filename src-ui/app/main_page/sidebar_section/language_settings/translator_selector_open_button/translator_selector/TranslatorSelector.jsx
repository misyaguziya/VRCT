import clsx from "clsx";
import styles from "./TranslatorSelector.module.scss";
import { useI18n } from "@useI18n";

import { chunkArray } from "@utils";
import { useStore_IsOpenedTranslatorSelector } from "@store";
import { useLanguageSettings } from "@logics_main";

export const TranslatorSelector = ({selected_id, translation_engines, is_selected_same_language}) => {
    const { t } = useI18n();
    const columns = chunkArray(translation_engines, 2);

    return (
        <div className={styles.container}>
            <div className={styles.relative_container}>
                <div className={styles.wrapper}>
                    {columns.map((column, column_index) => (
                        <div className={styles.column_wrapper} key={`column_${column_index}`}>
                            {column.map(({ id, label, is_available, is_default }) => (
                                <TranslatorBox
                                    key={id}
                                    id={id}
                                    label={label}
                                    is_available={is_available}
                                    is_default={is_default}
                                    is_selected={(id === selected_id)}
                                />
                            ))}
                        </div>
                    ))}
                </div>
                {is_selected_same_language ?
                    <div className={styles.is_selected_same_language_wrapper}>
                        <p className={styles.is_selected_same_language_text}>
                            {t("main_page.translator_selector.is_selected_same_language", {
                                your_language: t("main_page.your_language"),
                                target_language: t("main_page.target_language"),
                                ctranslate2: "CTranslate2",
                            })}
                        </p>
                    </div>
                : null
                }
            </div>
        </div>
    );
};

const TranslatorBox = (props) => {
    const { t } = useI18n();
    const { setSelectedTranslationEngines} = useLanguageSettings();
    const { updateIsOpenedTranslatorSelector} = useStore_IsOpenedTranslatorSelector();

    const box_class_name = clsx(
        styles.box,
        { [styles.is_selected]: props.is_selected },
        { [styles.is_available]: props.is_available }
    );
    const label_default_class_name = clsx(
        styles.label_default,
        { [styles.is_selected]: props.is_selected },
    );

    const selectTranslator = () => {
        if (props.is_selected === false) {
            setSelectedTranslationEngines(props.id);
        }
        updateIsOpenedTranslatorSelector(false);
    };

    return (
        <div className={box_class_name} onClick={selectTranslator}>
            <p className={styles.translator_name}>{props.label}</p>
            {props.is_default && <p className={label_default_class_name}>{t("main_page.translator_label_default")}</p>}
        </div>
    );
};