import { useIsOpenedConfigPage } from "@store";
import { getCurrent } from "@tauri-apps/api/window";
import { useEffect, useRef } from "react";
import { useStartPython } from "@logics/useStartPython";
import { useConfig } from "@logics/useConfig";
import { MainPage } from "./main_page/MainPage";
import { ConfigPage } from "./config_page/ConfigPage";
import styles from "./App.module.scss";
import clsx from "clsx";

export const App = () => {
    const { asyncStartPython } = useStartPython();
    const hasRunRef = useRef(false);
    const main_page = getCurrent();

    const { currentIsOpenedConfigPage } = useIsOpenedConfigPage();
    const {
        getSoftwareVersion,
        // getMicHostList,
        getSelectedMicHost,
        // getMicDeviceList,
        getSelectedMicDevice,
        getSelectedSpeakerDevice,
    } = useConfig();

    useEffect(() => {
        main_page.setDecorations(true);
        if (!hasRunRef.current) {
            asyncStartPython().then((result) => {
                getSoftwareVersion();
                // getMicHostList();
                getSelectedMicHost();
                // getMicDeviceList();
                getSelectedMicDevice();
                getSelectedSpeakerDevice();
            }).catch((err) => {
                console.error(err);
            });
        }
        return () => hasRunRef.current = true;
    }, []);

    return (
        <div className={styles.container}>
            <div className={clsx(styles.page, styles.config_page)}>
                <ConfigPage />
            </div>
            <div className={clsx(styles.page, styles.main_page, {
                [styles.show_config]: currentIsOpenedConfigPage,
                [styles.show_main]: !currentIsOpenedConfigPage
            })}>
                <MainPage />
            </div>
        </div>
    );
};