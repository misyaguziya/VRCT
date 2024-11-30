import { useTranslation } from "react-i18next";
import styles from "./RightSideComponents.module.scss";
import RefreshSvg from "@images/refresh.svg?react";
import HelpSvg from "@images/help.svg?react";

import { useStore_OpenedQuickSetting } from "@store";
import { useIsSoftwareUpdateAvailable } from "@logics_common";
import { useIsEnabledOverlaySmallLog, useEnableVrcMicMuteSync } from "@logics_configs";
import { OpenQuickSettingButton } from "./_buttons/OpenQuickSettingButton";

export const RightSideComponents = () => {
    return (
        <div className={styles.container}>
            <OpenVrcMicMuteSyncQuickSetting />
            <OpenOverlayQuickSetting />
            <SoftwareUpdateAvailableButton />
            <a
            className={styles.help_and_info_button}
            href="https://mzsoftware.notion.site/VRCT-Documents-be79b7a165f64442ad8f326d86c22246"
            target="_blank"
            rel="noreferrer"
            >
                <HelpSvg className={styles.help_svg} />
            </a>
        </div>
    );
};

const OpenOverlayQuickSetting = () => {
    // const { t } = useTranslation();
    const { updateOpenedQuickSetting } = useStore_OpenedQuickSetting();
    const { currentIsEnabledOverlaySmallLog } = useIsEnabledOverlaySmallLog();

    const onClickFunction = () => {
        updateOpenedQuickSetting("overlay");
    };

    return (
        <OpenQuickSettingButton
            label="Overlay(VR)"
            variable={currentIsEnabledOverlaySmallLog.data}
            onClickFunction={onClickFunction}
        />
    );
};

const OpenVrcMicMuteSyncQuickSetting = () => {
    const { t } = useTranslation();
    const { updateOpenedQuickSetting } = useStore_OpenedQuickSetting();
    const { currentEnableVrcMicMuteSync } = useEnableVrcMicMuteSync();

    const onClickFunction = () => {
        updateOpenedQuickSetting("vrc_mic_mute_sync");
    };

    return (
        <OpenQuickSettingButton
            label={t("config_page.vrc_mic_mute_sync.label")}
            variable={currentEnableVrcMicMuteSync.data}
            onClickFunction={onClickFunction}
        />
    );
};

const SoftwareUpdateAvailableButton = () => {
    const { currentIsSoftwareUpdateAvailable } = useIsSoftwareUpdateAvailable();
    const { t } = useTranslation();
    if (currentIsSoftwareUpdateAvailable.data === false) return null;

    const { updateOpenedQuickSetting } = useStore_OpenedQuickSetting();

    return (
        <button className={styles.software_update_button} onClick={()=>updateOpenedQuickSetting("update_software")}>
            <RefreshSvg className={styles.refresh_svg}/>
            <p className={styles.software_update_label}>{t("main_page.update_available")}</p>
        </button>
    );
};