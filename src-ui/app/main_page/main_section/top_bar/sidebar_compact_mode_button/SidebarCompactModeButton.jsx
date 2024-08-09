import clsx from "clsx";
import styles from "./SidebarCompactModeButton.module.scss";

import { useMainPageCompactModeStatus } from "@store";
import ArrowLeftSvg from "@images/arrow_left.svg?react";

export const SidebarCompactModeButton = () => {
    const { updateMainPageCompactModeStatus, currentMainPageCompactModeStatus } = useMainPageCompactModeStatus();

    const toggleCompactMode = () => {
        updateMainPageCompactModeStatus(!currentMainPageCompactModeStatus);
    };

    const class_names = clsx(styles["arrow_left_svg"], {
        [styles["reverse"]]: currentMainPageCompactModeStatus
    });

    return (
        <div className={styles.container} onClick={toggleCompactMode}>
            <ArrowLeftSvg className={class_names} preserveAspectRatio="none" />
        </div>
    );
};