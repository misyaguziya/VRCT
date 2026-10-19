import { useI18n } from "@useI18n";
import clsx from "clsx";
import styles from "./OpenQuickSettingButton.module.scss";
import WarningSvg from "@images/warning.svg?react";

export const OpenQuickSettingButton = (props) => {
    const { t } = useI18n();
    const variable = (typeof props.variable === "boolean") ? props.variable : null;
    const is_available = (typeof props.is_available === "boolean") ? props.is_available : true;
    const is_pending = props.is_pending === true || props.state === "pending";

    const getIndicatorLabelClassName = (base_classnames = []) => {
        return clsx(
            ...base_classnames,
            is_available && styles.is_available,
            is_pending && styles.is_pending
        );
    };

    return (
        <div className={styles.container}>
            <div
                className={clsx(styles.button_wrapper, is_pending && styles.is_pending)}
                onClick={is_pending ? undefined : props.onClickFunction}
            >
                {is_pending && <span className={styles.loader}></span>}
                <p className={clsx(styles.button_label, is_pending && styles.is_pending)}>{props.label}</p>
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