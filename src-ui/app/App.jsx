import { getCurrent } from "@tauri-apps/api/window";
import { useEffect, useRef } from "react";
import { useStartPython } from "@logics/useStartPython";
import { useConfig } from "@logics/useConfig";
import { MainPage } from "./main_page/MainPage";
import { ConfigPage } from "./config_page/ConfigPage";
import styles from "./App.module.scss";

export const App = () => {
    return (
        <div className={styles.container}>
            <StartPythonFacadeComponent />
            <ConfigPage />
            <MainPage />
        </div>
    );
};


const StartPythonFacadeComponent = () => {
    const { asyncStartPython } = useStartPython();
    const hasRunRef = useRef(false);
    const main_page = getCurrent();

    const {
        getSoftwareVersion,
        // getMicHostList,
        getSelectedMicHost,
        // getMicDeviceList,
        getSelectedMicDevice,
        getSelectedSpeakerDevice,

        getEnableAutoClearMessageBox,
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

                getEnableAutoClearMessageBox();
            }).catch((err) => {
                console.error(err);
            });
        }
        return () => hasRunRef.current = true;
    }, []);

    return null;
};