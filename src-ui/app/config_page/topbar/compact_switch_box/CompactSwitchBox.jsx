import { useI18n } from "@useI18n";

import styles from "./CompactSwitchBox.module.scss";

export const CompactSwitchBox = () => {
    const { t } = useI18n();
    return (
        <div className={styles.container}>
            <p>{t("config_page.compact_mode")}</p>
        </div>
    );
};