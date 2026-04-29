import clsx from "clsx";
import styles from "./SidebarCompactModeButton.module.scss";

import { useIsMainPageCompactMode } from "@logics_main";
import ArrowLeftSvg from "@images/arrow_left.svg?react";

export const SidebarCompactModeButton = () => {
    const { toggleIsMainPageCompactMode, currentIsMainPageCompactMode } = useIsMainPageCompactMode();

    const class_names = clsx(styles["arrow_left_svg"], {
        [styles["reverse"]]: currentIsMainPageCompactMode.data
    });

    return (
        <div className={styles.container} onClick={toggleIsMainPageCompactMode}>
            <ArrowLeftSvg className={class_names} preserveAspectRatio="none" />
        </div>
    );
};