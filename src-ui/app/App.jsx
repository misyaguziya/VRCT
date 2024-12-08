import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

import { useStartPython } from "@logics/useStartPython";
import { WindowTitleBar } from "./window_title_bar/WindowTitleBar";
import { MainPage } from "./main_page/MainPage";
import { ConfigPage } from "./config_page/ConfigPage";
import { SplashComponent } from "./splash_component/SplashComponent";
import { UpdatingComponent } from "./updating_component/UpdatingComponent";
import { ModalController } from "./modal_controller/ModalController";
import { SnackbarController } from "./snackbar_controller/SnackbarController";
import styles from "./App.module.scss";
import { useIsBackendReady, useIsSoftwareUpdating } from "@logics_common";

export const App = () => {
    const { currentIsBackendReady } = useIsBackendReady();
    const { WindowGeometryController } = useWindow();
    const { i18n } = useTranslation();

    return (
        <div className={styles.container}>
            <StartPythonController />
            <UiLanguageController />
            <ConfigPageCloseTriggerController />
            <UiSizeController />
            <FontFamilyController />
            <TransparencyController />
            <WindowGeometryController />

            {currentIsBackendReady.data === false
            ? <SplashComponent />
            : <Contents  key={i18n.language}/>
            }
        </div>
    );
};

const Contents = () => {
    const { currentIsSoftwareUpdating } = useIsSoftwareUpdating();
    return (
        <>
            <WindowTitleBar />
            {currentIsSoftwareUpdating.data === false
            ?
            <div className={styles.pages_wrapper}>
                <ConfigPage />
                <MainPage />
                <ModalController />
                <SnackbarController />
            </div>
            :
            <UpdatingComponent />
            }
        </>
    );
};

import {
    useWindow,
    useVolume,
    useIsOpenedConfigPage,
} from "@logics_common";

import {
    useUiLanguage,
    useUiScaling,
    useSelectedFontFamily,
    useTransparency,
} from "@logics_configs";

import {
    useMainFunction,
} from "@logics_main";

const StartPythonController = () => {
    const { asyncStartPython } = useStartPython();
    const hasRunRef = useRef(false);
    const { asyncFetchFonts } = useAsyncFetchFonts();

    useEffect(() => {
        if (!hasRunRef.current) {
            asyncStartPython().then(() => {
                startFeedingToWatchDogController();
                asyncFetchFonts();
            }).catch((err) => {
                console.error(err);
            });
        }
        return () => hasRunRef.current = true;
    }, []);

    return null;
};

const UiLanguageController = () => {
    const { currentUiLanguage } = useUiLanguage();
    const { i18n } = useTranslation();

    useEffect(() => {
        i18n.changeLanguage(currentUiLanguage.data);
    }, [currentUiLanguage.data]);
    return null;
};

import { useStore_MainFunctionsStateMemory } from "@store";

const ConfigPageCloseTriggerController = () => {
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
    }, [currentUiScaling.data]);

    return null;
};


const FontFamilyController = () => {
    const { currentSelectedFontFamily } = useSelectedFontFamily();
    useEffect(() => {
        document.documentElement.style.setProperty("--font_family", currentSelectedFontFamily.data);
    }, [currentSelectedFontFamily.data]);

    return null;
};

import { useStore_SelectableFontFamilyList } from "@store";
import { arrayToObject } from "@utils";

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

import { useStdoutToPython } from "@logics/useStdoutToPython";
const startFeedingToWatchDogController = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    setInterval(() => {
        asyncStdoutToPython("/run/feed_watchdog");
    }, 20000); // 20000ミリ秒 = 20秒
};