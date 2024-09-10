import styles from "./LanguageSelectorTopBar.module.scss";

import { useStore_IsOpenedLanguageSelector } from "@store";

export const LanguageSelectorTopBar = (props) => {
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
                <p className={styles.go_back_button_label}>Go Back</p>
            </div>
            <p className={styles.title}>{props.title}</p>
        </div>
    );
};