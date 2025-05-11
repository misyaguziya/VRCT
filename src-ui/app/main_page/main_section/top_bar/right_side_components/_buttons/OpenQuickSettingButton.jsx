import { useTranslation } from "react-i18next";
import clsx from "clsx";
import styles from "./OpenQuickSettingButton.module.scss";

export const OpenQuickSettingButton = (props) => {
    const { t } = useTranslation();
    const variable = (typeof props.variable === "boolean") ? props.variable : null;
    return (
        <div className={styles.container}>
            <div className={styles.button_wrapper} onClick={props.onClickFunction}>
                <p className={styles.button_label}>{props.label}</p>
                {variable !== null && (
                    props.variable === true ? (
                        <p className={clsx(styles.button_indicator_label, styles.enabled)}>
                            {t("main_page.state_text_enabled")}
                        </p>
                    ) : (
                        <p className={clsx(styles.button_indicator_label, styles.disabled)}>
                            {t("main_page.state_text_disabled")}
                        </p>
                    )
                )}
            </div>
        </div>
    );
};