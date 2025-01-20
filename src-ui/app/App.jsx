import { useTranslation } from "react-i18next";

import {
    useWindow,
} from "@logics_common";

import {
    KeyEventController,
    StartPythonController,
    GlobalHotKeyController,
    UiLanguageController,
    ConfigPageCloseTriggerController,
    UiSizeController,
    FontFamilyController,
    TransparencyController,
} from "./_app_controllers/index.js";

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
            <KeyEventController />
            <StartPythonController />
            <GlobalHotKeyController />
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