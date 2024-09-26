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
            <UiLanguageController />
            <ConfigPageCloseTrigger />
            <ConfigPage />
            <MainPage />
        </div>
    );
};


import { useSoftwareVersion } from "@logics_configs/useSoftwareVersion";
import { useEnableAutoMicSelect } from "@logics_configs/useEnableAutoMicSelect";
import { useEnableAutoSpeakerSelect } from "@logics_configs/useEnableAutoSpeakerSelect";
import { useSelectedMicHost } from "@logics_configs/useSelectedMicHost";
import { useSelectedMicDevice } from "@logics_configs/useSelectedMicDevice";
import { useSelectedSpeakerDevice } from "@logics_configs/useSelectedSpeakerDevice";
import { useMicThreshold } from "@logics_configs/useMicThreshold";
import { useSpeakerThreshold } from "@logics_configs/useSpeakerThreshold";
import { useEnableAutoClearMessageBox } from "@logics_configs/useEnableAutoClearMessageBox";
import { useSendMessageButtonType } from "@logics_configs/useSendMessageButtonType";
import { useUiLanguage } from "@logics_configs/useUiLanguage";

import { useIsMainPageCompactMode } from "@logics_main/useIsMainPageCompactMode";
import { useLanguageSettings } from "@logics_main/useLanguageSettings";
import { useSelectableLanguageList } from "@logics_main/useSelectableLanguageList";

const StartPythonFacadeComponent = () => {
    const { asyncStartPython } = useStartPython();
    const hasRunRef = useRef(false);
    const main_page = getCurrent();

    const { getIsMainPageCompactMode } = useIsMainPageCompactMode();
    const { getSoftwareVersion } = useSoftwareVersion();
    const { getEnableAutoMicSelect } = useEnableAutoMicSelect();
    const { getEnableAutoSpeakerSelect } = useEnableAutoSpeakerSelect();
    const { getSelectedMicHost } = useSelectedMicHost();
    const { getSelectedMicDevice } = useSelectedMicDevice();
    const { getSelectedSpeakerDevice } = useSelectedSpeakerDevice();
    const { getMicThreshold, getEnableAutomaticMicThreshold } = useMicThreshold();
    const { getSpeakerThreshold, getEnableAutomaticSpeakerThreshold } = useSpeakerThreshold();
    const { getEnableAutoClearMessageBox }  = useEnableAutoClearMessageBox();
    const { getSendMessageButtonType } = useSendMessageButtonType();
    const { getUiLanguage } = useUiLanguage();

    const {
        getSelectedPresetTabNumber,
        getEnableMultiTranslation,
        getSelectedYourLanguages,
        getSelectedTargetLanguages,
        getTranslationEngines,
        getSelectedTranslationEngines,
    } = useLanguageSettings();
    const { getSelectableLanguageList } = useSelectableLanguageList();


    useEffect(() => {
        main_page.setDecorations(true);
        if (!hasRunRef.current) {
            asyncStartPython().then((result) => {
                startFeedingToWatchDog();

                getUiLanguage();
                getIsMainPageCompactMode();

                getSoftwareVersion();

                getSelectedPresetTabNumber();
                getEnableMultiTranslation();
                getSelectedYourLanguages();
                getSelectedTargetLanguages();
                getSelectableLanguageList();
                getTranslationEngines();
                getSelectedTranslationEngines();

                getEnableAutoMicSelect();
                getEnableAutoSpeakerSelect();
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

import { useTranslation } from "react-i18next";
const UiLanguageController = () => {
    const { currentUiLanguage } = useUiLanguage();
    const { i18n } = useTranslation();

    useEffect(() => {
        i18n.changeLanguage(currentUiLanguage.data);
    }, [currentUiLanguage.data]);
    return null;
};

import { useVolume } from "@logics_common/useVolume";
import { useStore_IsOpenedConfigPage } from "@store";
const ConfigPageCloseTrigger = () => {
    const { currentIsOpenedConfigPage } = useStore_IsOpenedConfigPage();
    const {
        currentMicThresholdCheckStatus,
        volumeCheckStop_Mic,
        currentSpeakerThresholdCheckStatus,
        volumeCheckStop_Speaker,
    } = useVolume();

    useEffect(() => {
        if (currentIsOpenedConfigPage.data === false) {
            if (currentMicThresholdCheckStatus.data === true) volumeCheckStop_Mic();
            if (currentSpeakerThresholdCheckStatus.data === true) volumeCheckStop_Speaker();
        }
    }, [currentIsOpenedConfigPage]);
    return null;
};

import { useStdoutToPython } from "@logics/useStdoutToPython";
const startFeedingToWatchDog = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    setInterval(() => {
        asyncStdoutToPython("/run/feed_watchdog");
    }, 20000); // 20000ミリ秒 = 20秒
};