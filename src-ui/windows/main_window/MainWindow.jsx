import { getCurrent } from "@tauri-apps/api/window";
import { useEffect, useRef } from "react";
import styles from "./MainWindow.module.scss";
import { SidebarSection } from "./sidebar_section/SidebarSection";
import { MainSection } from "./main_section/MainSection";
import { useStartPython } from "@logics/useStartPython";
import { useConfig } from "@logics/useConfig";

export const MainWindow = () => {
    const { asyncStartPython } = useStartPython();
    const hasRunRef = useRef(false);
    const main_window = getCurrent();

    const { getSoftwareVersion } = useConfig();

    useEffect(() => {
        main_window.setDecorations(true);
        if (!hasRunRef.current) {
            asyncStartPython().then((result) => {
                getSoftwareVersion();
            }).catch((err) => {

            });
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
import { useWindow } from "@logics/useWindow";

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