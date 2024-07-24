import { useTranslation } from "react-i18next";

import styles from "./TitleBox.module.scss";
import chato_img from "@images/chato_white.png";

export const TitleBox = () => {
    const { t } = useTranslation();
    return (
        <div className={styles.container}>
            <img src={chato_img} className={styles.logo_chato} alt="VRCT logo chato" />
            <p className={styles.title}>{t("config_window.config_title")}</p>
        </div>
    );
};