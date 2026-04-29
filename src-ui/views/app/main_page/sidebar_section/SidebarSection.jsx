import clsx from "clsx";

import styles from "./SidebarSection.module.scss";
import { useStore_IsOpenedLanguageSelector } from "@store";
import { useIsMainPageCompactMode } from "@logics_main";

import { Logo } from "./logo/Logo";
import { MainFunctionSwitch } from "./main_function_switch/MainFunctionSwitch";
import { LanguageSettings } from "./language_settings/LanguageSettings";
import { OpenSettings } from "./open_settings/OpenSettings";

export const SidebarSection = () => {
    const { currentIsMainPageCompactMode } = useIsMainPageCompactMode();
    const container_class_name = clsx(styles.container, {
        [styles.is_compact_mode]: currentIsMainPageCompactMode.data
    });

    const { currentIsOpenedLanguageSelector } = useStore_IsOpenedLanguageSelector();
    const scroll_container_class_names = clsx(styles.scroll_container, {
        [styles.is_opened]: (currentIsOpenedLanguageSelector.data.your_language === true || currentIsOpenedLanguageSelector.data.target_language === true)
    });

    return (
        <div className={container_class_name}>
            <Logo />
            <div className={scroll_container_class_names}>
                <MainFunctionSwitch />
                {!currentIsMainPageCompactMode.data && <LanguageSettings />}
            </div>
            <OpenSettings />
        </div>
    );
};