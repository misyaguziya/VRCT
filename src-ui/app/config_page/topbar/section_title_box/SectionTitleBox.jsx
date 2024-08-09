import { useTranslation } from "react-i18next";
import styles from "./SectionTitleBox.module.scss";
import { useSelectedConfigTabId } from "@store";

export const SectionTitleBox = () => {
    const { t } = useTranslation();
    const { currentSelectedConfigTabId } = useSelectedConfigTabId();
    return (
        <div className={styles.container}>
            <p className={styles.title}>{t(`config_page.side_menu_labels.${currentSelectedConfigTabId}`)}</p>
        </div>
    );
};