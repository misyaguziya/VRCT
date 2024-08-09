import clsx from "clsx";

import styles from "./SidebarSection.module.scss";
import { useMainPageCompactModeStatus } from "@store";

import { Logo } from "./logo/Logo";
import { MainFunctionSwitch } from "./main_function_switch/MainFunctionSwitch";
import { LanguageSettings } from "./language_settings/LanguageSettings";
import { OpenSettings } from "./open_settings/OpenSettings";

export const SidebarSection = () => {
    const { currentMainPageCompactModeStatus } = useMainPageCompactModeStatus();
    const container_class_name = clsx(styles["container"], {
        [styles["is_compact_mode"]]: currentMainPageCompactModeStatus
    });

    return (
        <div className={container_class_name}>
            <Logo />
            <MainFunctionSwitch />
            {!currentMainPageCompactModeStatus && <LanguageSettings />}
            <OpenSettings />
        </div>
    );
};