import { useTranslation } from "react-i18next";

import styles from "./CompactSwitchBox.module.scss";

export const CompactSwitchBox = () => {
    const { t } = useTranslation();
    return (
        <div className={styles.container}>
            <p>{t("config_window.compact_mode")}</p>
        </div>
    );
};