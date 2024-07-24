import clsx from "clsx";
import styles from "./SidebarCompactModeButton.module.scss";

import { useIsCompactMode } from "@store";
import ArrowLeftSvg from "@images/arrow_left.svg?react";

export const SidebarCompactModeButton = () => {
    const { updateIsCompactMode, currentIsCompactMode } = useIsCompactMode();

    const toggleCompactMode = () => {
        updateIsCompactMode(!currentIsCompactMode);
    };

    const class_names = clsx(styles["arrow_left_svg"], {
        [styles["reverse"]]: currentIsCompactMode
    });

    return (
        <div className={styles.container} onClick={toggleCompactMode}>
            <ArrowLeftSvg className={class_names} preserveAspectRatio="none" />
        </div>
    );
};