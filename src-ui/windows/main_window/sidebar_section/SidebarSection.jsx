import clsx from "clsx";

import styles from "./SidebarSection.module.scss";
import { useIsCompactMode } from "@store";

import { Logo } from "./logo/Logo";
import { MainFunctionSwitch } from "./main_function_switch/MainFunctionSwitch";
import { LanguageSettings } from "./language_settings/LanguageSettings";
import { OpenSettings } from "./open_settings/OpenSettings";

export const SidebarSection = () => {
    const { currentIsCompactMode } = useIsCompactMode();
    const container_class_name = clsx(styles["container"], {
        [styles["is_compact_mode"]]: currentIsCompactMode
    });

    return (
        <div className={container_class_name}>
            <Logo />
            <MainFunctionSwitch />
            {!currentIsCompactMode && <LanguageSettings />}
            <OpenSettings />
        </div>
    );
};