import React from "react";
import { useI18n } from "@useI18n";
import clsx from "clsx";
import styles from "./VolumeCheckButton.module.scss";

export const VolumeCheckButton = React.memo((props) => {
    const { t } = useI18n();
    const getClassNames = (baseClass) => clsx(baseClass, {
        [styles.is_active]: (props.isChecking?.data === true),
        [styles.is_pending]: (props.isChecking.state === "pending"),
    });

    const toggleFunction = () => {
        if (props.isChecking?.data === true) {
            props.stopFunction();
        } else if (props.isChecking?.data === false) {
            props.startFunction();
        }
    };


    return (
        <div className={styles.container}>
            <div className={getClassNames(styles.button)} onClick={toggleFunction}>
                <props.SvgComponent className={styles.button_svg} />
                <p className={styles.button_text}>{t("config_page.device.check_volume")}</p>
            </div>
        </div>
    );
});


VolumeCheckButton.displayName = "VolumeCheckButton";