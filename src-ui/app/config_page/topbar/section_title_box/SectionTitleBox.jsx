import { useTranslation } from "react-i18next";
import styles from "./SectionTitleBox.module.scss";
import { useStore_SelectedConfigTabId } from "@store";

export const SectionTitleBox = () => {
    const { t } = useTranslation();
    const { currentSelectedConfigTabId } = useStore_SelectedConfigTabId();
    return (
        <div className={styles.container}>
            <p className={styles.title}>{t(`config_page.side_menu_labels.${currentSelectedConfigTabId.data}`)}</p>
        </div>
    );
};