import React from "react";
import styles from "./VolumeCheckButton.module.scss";
import clsx from "clsx";

export const VolumeCheckButton = React.memo((props) => {
    const getClassNames = (baseClass) => clsx(baseClass, {
        [styles.is_active]: (props.isChecking?.data === true),
        [styles.is_loading]: (props.isChecking.state === "loading"),
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
                <p className={styles.button_text}>Check Volume</p>
            </div>
        </div>
    );
});


VolumeCheckButton.displayName = "VolumeCheckButton";