import { getCurrent } from "@tauri-apps/api/window";
import { useEffect, useRef } from "react";
import { useStartPython } from "@logics/useStartPython";
// import { useConfig } from "@logics/useConfig";
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


import { useSoftwareVersion } from "@logics_configs/useSoftwareVersion";
import { useSelectedMicHost } from "@logics_configs/useSelectedMicHost";
import { useSelectedMicDevice } from "@logics_configs/useSelectedMicDevice";
import { useSelectedSpeakerDevice } from "@logics_configs/useSelectedSpeakerDevice";
import { useMicThreshold } from "@logics_configs/useMicThreshold";
import { useSpeakerThreshold } from "@logics_configs/useSpeakerThreshold";
import { useEnableAutoClearMessageBox } from "@logics_configs/useEnableAutoClearMessageBox";
import { useSendMessageButtonType } from "@logics_configs/useSendMessageButtonType";

const StartPythonFacadeComponent = () => {
    const { asyncStartPython } = useStartPython();
    const hasRunRef = useRef(false);
    const main_page = getCurrent();

    const { getSoftwareVersion } = useSoftwareVersion();
    const { getSelectedMicHost } = useSelectedMicHost();
    const { getSelectedMicDevice } = useSelectedMicDevice();
    const { getSelectedSpeakerDevice } = useSelectedSpeakerDevice();
    const { getMicThreshold, getEnableAutomaticMicThreshold } = useMicThreshold();
    const { getSpeakerThreshold, getEnableAutomaticSpeakerThreshold } = useSpeakerThreshold();
    const { getEnableAutoClearMessageBox }  = useEnableAutoClearMessageBox();
    const { getSendMessageButtonType } = useSendMessageButtonType();


    useEffect(() => {
        main_page.setDecorations(true);
        if (!hasRunRef.current) {
            asyncStartPython().then((result) => {
                getSoftwareVersion();
                getSelectedMicHost();
                getSelectedMicDevice();
                getSelectedSpeakerDevice();

                getMicThreshold();
                getSpeakerThreshold();
                getEnableAutomaticMicThreshold();
                getEnableAutomaticSpeakerThreshold();

                getEnableAutoClearMessageBox();
                getSendMessageButtonType();
            }).catch((err) => {
                console.error(err);
            });
        }
        return () => hasRunRef.current = true;
    }, []);

    return null;
};