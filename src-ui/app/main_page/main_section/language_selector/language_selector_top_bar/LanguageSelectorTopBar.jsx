import { useTranslation } from "react-i18next";
import styles from "./LanguageSelectorTopBar.module.scss";
import { useStore_IsOpenedLanguageSelector } from "@store";

export const LanguageSelectorTopBar = (props) => {
    const { t } = useTranslation();
    const { updateIsOpenedLanguageSelector } = useStore_IsOpenedLanguageSelector();
    const closeLanguageSelector = () => {
        updateIsOpenedLanguageSelector({
            your_language: false,
            target_language: false,
        });
    };

    return (
        <div className={styles.container}>
            <div className={styles.go_back_button_wrapper} onClick={closeLanguageSelector}>
                <p className={styles.go_back_button_label}>{t("common.go_back_button_label")}</p>
            </div>
            <p className={styles.title}>{props.title}</p>
        </div>
    );
};