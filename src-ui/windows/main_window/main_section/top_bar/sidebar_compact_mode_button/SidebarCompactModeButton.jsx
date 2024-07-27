import clsx from "clsx";
import styles from "./SidebarCompactModeButton.module.scss";

import { useMainWindowCompactModeStatus } from "@store";
import ArrowLeftSvg from "@images/arrow_left.svg?react";

export const SidebarCompactModeButton = () => {
    const { updateMainWindowCompactModeStatus, currentMainWindowCompactModeStatus } = useMainWindowCompactModeStatus();

    const toggleCompactMode = () => {
        updateMainWindowCompactModeStatus(!currentMainWindowCompactModeStatus);
    };

    const class_names = clsx(styles["arrow_left_svg"], {
        [styles["reverse"]]: currentMainWindowCompactModeStatus
    });

    return (
        <div className={styles.container} onClick={toggleCompactMode}>
            <ArrowLeftSvg className={class_names} preserveAspectRatio="none" />
        </div>
    );
};