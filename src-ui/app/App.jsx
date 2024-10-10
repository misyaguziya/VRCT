import { useEffect, useRef } from "react";
import { useStartPython } from "@logics/useStartPython";
import { WindowTitleBar } from "./window_title_bar/WindowTitleBar";
import { MainPage } from "./main_page/MainPage";
import { ConfigPage } from "./config_page/ConfigPage";
import styles from "./App.module.scss";

export const App = () => {
    return (
        <div className={styles.container}>
            <StartPythonFacadeComponent />
            <UiLanguageController />
            <ConfigPageCloseTrigger />
            <UiSizeController />
            <FontFamilyController />
            <TransparencyController />

            <WindowTitleBar />
            <div className={styles.pages_wrapper}>
                <ConfigPage />
                <MainPage />
            </div>
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
import { useUiScaling } from "@logics_configs/useUiScaling";
import { useMessageLogUiScaling } from "@logics_configs/useMessageLogUiScaling";
import { useSelectedFontFamily } from "@logics_configs/useSelectedFontFamily";
import { useTransparency } from "@logics_configs/useTransparency";

import { useIsMainPageCompactMode } from "@logics_main/useIsMainPageCompactMode";
import { useLanguageSettings } from "@logics_main/useLanguageSettings";
import { useSelectableLanguageList } from "@logics_main/useSelectableLanguageList";
import { useMessageInputBoxRatio } from "@logics_main/useMessageInputBoxRatio";

import { useMicHostList } from "@logics_configs/useMicHostList";
import { useMicDeviceList } from "@logics_configs/useMicDeviceList";
import { useSpeakerDeviceList } from "@logics_configs/useSpeakerDeviceList";

const StartPythonFacadeComponent = () => {
    const { asyncStartPython } = useStartPython();
    const hasRunRef = useRef(false);
    const { asyncFetchFonts } = useAsyncFetchFonts();

    const { getMicHostList } = useMicHostList();
    const { getMicDeviceList } = useMicDeviceList();
    const { getSpeakerDeviceList } = useSpeakerDeviceList();

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
    const { getUiScaling } = useUiScaling();
    const { getMessageLogUiScaling } = useMessageLogUiScaling();
    const { getSelectedFontFamily } = useSelectedFontFamily();
    const { getTransparency } = useTransparency();

    const {
        getSelectedPresetTabNumber,
        getEnableMultiTranslation,
        getSelectedYourLanguages,
        getSelectedTargetLanguages,
        getTranslationEngines,
        getSelectedTranslationEngines,
    } = useLanguageSettings();
    const { getSelectableLanguageList } = useSelectableLanguageList();
    const { getMessageInputBoxRatio } = useMessageInputBoxRatio();


    useEffect(() => {
        if (!hasRunRef.current) {
            asyncStartPython().then((result) => {
                getUiLanguage();
                getUiScaling();
                getMessageLogUiScaling();
                getIsMainPageCompactMode();
                getMessageInputBoxRatio();
                getTransparency();

                asyncFetchFonts();
                getSelectedFontFamily();

                getSoftwareVersion();

                getSelectedPresetTabNumber();
                getEnableMultiTranslation();
                getSelectedYourLanguages();
                getSelectedTargetLanguages();
                getSelectableLanguageList();
                getTranslationEngines();
                getSelectedTranslationEngines();

                getMicHostList();
                getMicDeviceList();
                getSpeakerDeviceList();

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

import { useStore_MainFunctionsStateMemory } from "@store";
import { useVolume } from "@logics_common/useVolume";
import { useIsOpenedConfigPage } from "@logics_common/useIsOpenedConfigPage";
import { useMainFunction } from "@logics_main/useMainFunction";
const ConfigPageCloseTrigger = () => {
    const { currentIsOpenedConfigPage } = useIsOpenedConfigPage();
    const { currentMainFunctionsStateMemory, updateMainFunctionsStateMemory} = useStore_MainFunctionsStateMemory();
    const {
        currentTranscriptionSendStatus,
        setTranscriptionSend,
        currentTranscriptionReceiveStatus,
        setTranscriptionReceive,
    } = useMainFunction();
    const {
        currentMicThresholdCheckStatus,
        volumeCheckStop_Mic,
        currentSpeakerThresholdCheckStatus,
        volumeCheckStop_Speaker,
    } = useVolume();


    const memorizeLatestMainFunctionsState = () => {
        updateMainFunctionsStateMemory({
            transcription_send: currentTranscriptionSendStatus.data,
            transcription_receive: currentTranscriptionReceiveStatus.data,
        });
    };

    const restoreMainFunctionState = () => {
        if (currentMainFunctionsStateMemory.data.transcription_send === true) setTranscriptionSend(true);
        if (currentMainFunctionsStateMemory.data.transcription_receive === true) setTranscriptionReceive(true);
    };

    useEffect(() => {
        if (currentIsOpenedConfigPage.data === true) { // When config page is opened.
            memorizeLatestMainFunctionsState();
            if (currentTranscriptionSendStatus.data === true) setTranscriptionSend(false);
            if (currentTranscriptionReceiveStatus.data === true) setTranscriptionReceive(false);
        } else if (currentIsOpenedConfigPage.data === false) { // When config page is closed.
            if (currentMicThresholdCheckStatus.data === true) volumeCheckStop_Mic();
            if (currentSpeakerThresholdCheckStatus.data === true) volumeCheckStop_Speaker();
            restoreMainFunctionState();
        }
    }, [currentIsOpenedConfigPage.data]);
    return null;
};

import React from "react";
const UiSizeController = () => {
    const { currentUiScaling } = useUiScaling();
    const font_size = 62.5 * currentUiScaling.data / 100;

    useEffect(() => {
        document.documentElement.style.setProperty("font-size", `${font_size}%`);
        document.documentElement.style.setProperty("font-family", `Yu Gothic UI`);
    }, [currentUiScaling.data]);

    return null;
};


const FontFamilyController = () => {
    const { currentSelectedFontFamily } = useSelectedFontFamily();
    useEffect(() => {
        document.documentElement.style.setProperty("font-family", `${currentSelectedFontFamily.data}`);
    }, [currentSelectedFontFamily.data]);

    return null;
};

import { useStore_SelectableFontFamilyList } from "@store";
import { arrayToObject } from "@utils/arrayToObject";

import { invoke } from "@tauri-apps/api/tauri";
const useAsyncFetchFonts = () => {
    const { updateSelectableFontFamilyList } = useStore_SelectableFontFamilyList();
    const asyncFetchFonts = async () => {
        try {
            let fonts = await invoke("get_font_list");
            fonts = fonts.sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
            updateSelectableFontFamilyList(arrayToObject(fonts));
        } catch (error) {
            console.error("Error fetching fonts:", error);
        }
    };
    return { asyncFetchFonts };
};


const TransparencyController = () => {
    const { currentTransparency } = useTransparency();
    useEffect(() => {
        document.documentElement.style.setProperty("opacity", `${currentTransparency.data / 100}`);
    }, [currentTransparency.data]);

    return null;
};