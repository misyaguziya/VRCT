import React from "react";
import styles from "./VolumeCheckButton.module.scss";
import MicSvg from "@images/mic.svg?react";
import HeadphonesSvg from "@images/headphones.svg?react";
import clsx from "clsx";
// import { useVolume } from "@logics/useVolume";

export const VolumeCheckButton = React.memo((props) => {
    const SvgComponent = props.id === "mic_threshold" ? MicSvg : HeadphonesSvg;


    const getClassNames = (baseClass) => clsx(baseClass, {
        // [styles.is_active]: (currentState.data === true),
        // [styles.is_loading]: (currentState.state === "loading"),
        // [styles.is_hovered]: is_hovered,
        // [styles.is_mouse_down]: is_mouse_down,
    });
    // const {
    //     volumeCheckStart_Mic,
    //     volumeCheckStop_Mic,
    // } = useVolume();


    return (
        // <div className={styles.container} onClick={() => volumeCheckStop_Mic()}>
        <div className={styles.container}>
            <div className={getClassNames(styles.button_button)}>
                <SvgComponent className={getClassNames(styles.button_svg)} />
            </div>
        </div>
    );
});


VolumeCheckButton.displayName = "VolumeCheckButton";