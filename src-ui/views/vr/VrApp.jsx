import { useEffect } from "react";
import { emit, listen } from "@tauri-apps/api/event";
import { getDefaultStore } from "jotai";

import { useI18n } from "@useI18n";
import { dynamicStoreRegistry } from "@store";
import { useIsOpenedConfigPage } from "@logics_common";

import {
    UiLanguageController,
    UiSizeController,
    FontFamilyController,
} from "../app/_app_controllers";
import { MainFunctionSwitch } from "../app/main_page/sidebar_section/main_function_switch/MainFunctionSwitch";
import { LogBox } from "../app/main_page/main_section/message_container/log_box/LogBox";

import styles from "./VrApp.module.scss";

export const VrApp = () => {
    const { t } = useI18n();
    const { currentIsOpenedConfigPage } = useIsOpenedConfigPage();

    return (
        <div className={styles.container}>
            <VrStateReceiver />
            <UiLanguageController />
            <UiSizeController />
            <FontFamilyController />

            <div className={styles.sidebar}>
                <MainFunctionSwitch />
            </div>
            <div className={styles.log_box_wrapper}>
                <LogBox />
            </div>

            {currentIsOpenedConfigPage.data === true && (
                <div className={styles.locked}>{t("vr_panel.locked_by_config_page")}</div>
            )}
        </div>
    );
};

// メインウィンドウから送られてくるatomの値を、このウィンドウのatomへそのまま反映する。
const VrStateReceiver = () => {
    useEffect(() => {
        const jotai = getDefaultStore();
        const unlisten = listen("vr-panel-state", ({ payload }) => {
            for (const [name, value] of Object.entries(payload)) {
                const atom = dynamicStoreRegistry[`Atom_${name}`];
                if (atom) jotai.set(atom, value);
            }
        });
        // 受信の準備ができてから全状態を要求する (メインが先に起動していた場合)
        unlisten.then(() => emit("vr-panel-ready"));
        return () => { unlisten.then(f => f()); };
    }, []);
    return null;
};
