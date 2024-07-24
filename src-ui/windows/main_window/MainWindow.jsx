import { useEffect, useRef } from "react";
import styles from "./MainWindow.module.scss";
import { SidebarSection } from "./sidebar_section/SidebarSection";
import { MainSection } from "./main_section/MainSection";
import { useStartPython } from "@logics/useStartPython";

export const MainWindow = () => {
    const { asyncStartPython } = useStartPython();
    const hasRunRef = useRef(false);

    useEffect(() => {
        if (!hasRunRef.current) {
            asyncStartPython();
        }
        return () => hasRunRef.current = true;
    }, []);

    return (
        <div className={styles.container}>
            <SidebarSection />
            <MainSection />
            <MainWindowCover />
        </div>
    );
};


import { useTranslation } from "react-i18next";
import { useIsOpenedConfigWindow } from "@store";
import { useWindow } from "@utils/useWindow";

export const MainWindowCover = () => {
    const { t } = useTranslation();
    const { currentIsOpenedConfigWindow } = useIsOpenedConfigWindow();
    const { closeConfigWindow } = useWindow();
    // console.log(currentIsOpenedConfigWindow);
    if ( currentIsOpenedConfigWindow === false) return null;

    const closeSettingsWindow = () => closeConfigWindow();

    return (
        <div className={styles.main_window_cover}>
            <p className={styles.cover_message}>{t("main_window.cover_message")}</p>
            <button
            className={styles.close_settings_window_button}
            onClick={closeSettingsWindow}
            >
                {t("main_window.close_settings_window")}
            </button>
        </div>
    );
};