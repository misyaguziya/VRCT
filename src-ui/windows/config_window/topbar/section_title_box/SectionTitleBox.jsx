import { useTranslation } from "react-i18next";
import styles from "./SectionTitleBox.module.scss";
import { useSelectedConfigTab } from "@store";

export const SectionTitleBox = () => {
    const { t } = useTranslation();
    const { currentSelectedConfigTab } = useSelectedConfigTab();
    return (
        <div className={styles.container}>
            <p className={styles.title}>{t(`config_window.side_menu_labels.${currentSelectedConfigTab}`)}</p>
        </div>
    );
};