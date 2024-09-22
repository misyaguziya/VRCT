import clsx from "clsx";
import styles from "./SidebarCompactModeButton.module.scss";

import { useStore_IsMainPageCompactMode } from "@store";
import ArrowLeftSvg from "@images/arrow_left.svg?react";

export const SidebarCompactModeButton = () => {
    const { updateIsMainPageCompactMode, currentIsMainPageCompactMode } = useStore_IsMainPageCompactMode();

    const toggleCompactMode = () => {
        updateIsMainPageCompactMode(!currentIsMainPageCompactMode.data);
    };

    const class_names = clsx(styles["arrow_left_svg"], {
        [styles["reverse"]]: currentIsMainPageCompactMode.data
    });

    return (
        <div className={styles.container} onClick={toggleCompactMode}>
            <ArrowLeftSvg className={class_names} preserveAspectRatio="none" />
        </div>
    );
};