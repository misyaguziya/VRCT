import { useI18n } from "@useI18n";
import clsx from "clsx";
import styles from "./OpenQuickSettingButton.module.scss";
import WarningSvg from "@images/warning.svg?react";

export const OpenQuickSettingButton = (props) => {
    const { t } = useI18n();
    const variable = (typeof props.variable === "boolean") ? props.variable : null;
    const is_available = (typeof props.is_available === "boolean") ? props.is_available : true;

    const getIndicatorLabelClassName = (base_classnames = []) => {
        return clsx(...base_classnames, is_available && styles.is_available);
    };

    return (
        <div className={styles.container}>
            <div className={styles.button_wrapper} onClick={props.onClickFunction}>
                <p className={styles.button_label}>{props.label}</p>
                {variable !== null && (
                    props.variable === true ? (
                        <p className={getIndicatorLabelClassName([styles.button_indicator_label, styles.is_enabled])}>
                            {t("main_page.state_text_enabled")}
                            {is_available === false && (
                                <WarningSvg className={styles.warning_svg} />
                            )}
                        </p>
                    ) : (
                        <p className={getIndicatorLabelClassName([styles.button_indicator_label, styles.is_disabled])}>
                            {t("main_page.state_text_disabled")}
                        </p>
                    )
                )}
            </div>
        </div>
    );
};