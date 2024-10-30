import clsx from "clsx";
import styles from "./OpenQuickSettingButton.module.scss";

export const OpenQuickSettingButton = (props) => {
    return (
        <div className={styles.container}>
            <div className={styles.button_wrapper} onClick={props.onClickFunction}>
                <p className={styles.button_label}>{props.label}</p>
                {props.variable === true
                    ? <p className={clsx(styles.button_indicator_label, styles.enabled)}>Enabled</p>
                    : <p className={clsx(styles.button_indicator_label, styles.disabled)}>Disabled</p>
                }
            </div>
        </div>
    );
};