import styles from "./ConnectionCheckButton.module.scss";
import { useI18n } from "@useI18n";

export const ConnectionCheckButton = (props) => {
    const { t } = useI18n();

    const label = props.state === "pending"
        ? `${t("config_page.common.connection_check.checking")} 🌀`
        : props.variable === true
            ? `${t("config_page.common.connection_check.connected")} ✅`
            : `${t("config_page.common.connection_check.disconnected")} ❌`;

    return (
        <div className={styles.container}>
            <p className={styles.status_label}>{label}</p>
            <button className={styles.button_wrapper} onClick={props.checkFunction}>
                <p className={styles.button_label}>{t("config_page.common.connection_check.button_label")}</p>
            </button>
        </div>
    );
};