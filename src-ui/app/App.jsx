import { useTranslation } from "react-i18next";

import {
    KeyEventController,
    StartPythonController,
    GlobalHotKeyController,
    UiLanguageController,
    ConfigPageCloseTriggerController,
    UiSizeController,
    FontFamilyController,
    TransparencyController,
    PluginsController,
} from "./_app_controllers/index.js";

import { WindowTitleBar } from "./window_title_bar/WindowTitleBar";
import { MainPage } from "./main_page/MainPage";
import { ConfigPage } from "./config_page/ConfigPage";
import { SplashComponent } from "./splash_component/SplashComponent";
import { UpdatingComponent } from "./updating_component/UpdatingComponent";
import { ModalController } from "./modal_controller/ModalController";
import { SnackbarController } from "./snackbar_controller/SnackbarController";
import styles from "./App.module.scss";
import { useIsBackendReady, useIsSoftwareUpdating, useIsVrctAvailable, useWindow } from "@logics_common";
import { AppErrorBoundary } from "./error_boundary/AppErrorBoundary";

export const App = () => {
    const { currentIsVrctAvailable } = useIsVrctAvailable();
    const { currentIsBackendReady } = useIsBackendReady();
    const { i18n } = useTranslation();

    return (
        <div className={styles.container}>
            <AppErrorBoundary >
                <KeyEventController />
                <StartPythonController />
                <GlobalHotKeyController />
                <UiLanguageController />
                <ConfigPageCloseTriggerController />
                <UiSizeController />
                <FontFamilyController />
                <TransparencyController />

                {(currentIsBackendReady.data === false || currentIsVrctAvailable.data === false)
                    ? <SplashComponent />
                    : <Contents key={i18n.language} />
                }

                <SnackbarController />
            </AppErrorBoundary>
        </div>
    );
};

const Contents = () => {
    const { WindowGeometryController } = useWindow();
    const { currentIsSoftwareUpdating } = useIsSoftwareUpdating();
    return (
        <>
            <WindowGeometryController />
            <PluginsController />

            <WindowTitleBar />
            {currentIsSoftwareUpdating.data === false
            ?
            <div className={styles.pages_wrapper}>
                <ConfigPage />
                <MainPage />
                <ModalController />
            </div>
            :
            <UpdatingComponent />
            }
        </>
    );
};