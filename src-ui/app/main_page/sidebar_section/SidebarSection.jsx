import clsx from "clsx";

import styles from "./SidebarSection.module.scss";
import { useStore_IsMainPageCompactMode } from "@store";

import { Logo } from "./logo/Logo";
import { MainFunctionSwitch } from "./main_function_switch/MainFunctionSwitch";
import { LanguageSettings } from "./language_settings/LanguageSettings";
import { OpenSettings } from "./open_settings/OpenSettings";

export const SidebarSection = () => {
    const { currentIsMainPageCompactMode } = useStore_IsMainPageCompactMode();
    const container_class_name = clsx(styles.container, {
        [styles.is_compact_mode]: currentIsMainPageCompactMode
    });

    return (
        <div className={container_class_name}>
            <Logo />
            <div className={styles.scroll_container}>
                <MainFunctionSwitch />
                {!currentIsMainPageCompactMode && <LanguageSettings />}
            </div>
            <OpenSettings />
        </div>
    );
};