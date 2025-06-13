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
    CornerRadiusController,
    PluginsController,
} from "./_app_controllers";

import styles from "./App.module.scss";

import { MainPage } from "./main_page/MainPage";
import { ConfigPage } from "./config_page/ConfigPage";

import {
    WindowTitleBar,
    SplashComponent,
    UpdatingComponent,
    ModalController,
    SnackbarController,
    AppErrorBoundary,
} from "./others";

import { useIsBackendReady, useIsSoftwareUpdating, useIsVrctAvailable, useWindow } from "@logics_common";

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
                <CornerRadiusController />

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