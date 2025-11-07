import { useI18n } from "@useI18n";

import styles from "./TitleBox.module.scss";
import chato_img from "@images/chato_white.png";

export const TitleBox = () => {
    const { t } = useI18n();
    return (
        <div className={styles.container}>
            <img src={chato_img} className={styles.logo_chato} alt="VRCT logo chato" />
            <p className={styles.title}>{t("config_page.config_title")}</p>
        </div>
    );
};