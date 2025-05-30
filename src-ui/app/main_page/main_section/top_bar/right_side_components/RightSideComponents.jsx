import { useTranslation } from "react-i18next";
import styles from "./RightSideComponents.module.scss";
import RefreshSvg from "@images/refresh.svg?react";
import HelpSvg from "@images/help.svg?react";

import { useStore_OpenedQuickSetting } from "@store";
import { useSoftwareVersion } from "@logics_common";
import { useIsEnabledOverlaySmallLog, useIsEnabledOverlayLargeLog, useEnableVrcMicMuteSync } from "@logics_configs";
import { OpenQuickSettingButton } from "./_buttons/OpenQuickSettingButton";

export const RightSideComponents = () => {

    return (
        <div className={styles.container}>

            <PluginsQuickSetting />
            <OpenVrcMicMuteSyncQuickSetting />
            <OpenOverlayQuickSetting />
            <SoftwareUpdateAvailableButton />
            <a
                className={styles.help_and_info_button}
                href="https://docs.google.com/spreadsheets/d/1_L5i-1U6PB1dnaPPTE_5uKMfqOpkLziPyRkiMLi4mqU/edit?usp=sharing"
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
    const { currentIsEnabledOverlayLargeLog } = useIsEnabledOverlayLargeLog();

    const onClickFunction = () => {
        updateOpenedQuickSetting("overlay");
    };

    const is_enable = currentIsEnabledOverlaySmallLog.data === true || currentIsEnabledOverlayLargeLog.data === true;

    return (
        <OpenQuickSettingButton
            label="Overlay(VR)"
            variable={is_enable}
            onClickFunction={onClickFunction}
        />
    );
};
const PluginsQuickSetting = () => {
    const { t } = useTranslation();
    const { updateOpenedQuickSetting } = useStore_OpenedQuickSetting();

    const onClickFunction = () => {
        updateOpenedQuickSetting("plugins");
    };

    return (
        <OpenQuickSettingButton
            label={t("config_page.side_menu_labels.plugins")}
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
            label={t("config_page.others.vrc_mic_mute_sync.label")}
            variable={currentEnableVrcMicMuteSync.data.is_enabled}
            onClickFunction={onClickFunction}
        />
    );
};

const SoftwareUpdateAvailableButton = () => {
    const { currentLatestSoftwareVersionInfo } = useSoftwareVersion();
    const { t } = useTranslation();
    if (currentLatestSoftwareVersionInfo.data.is_update_available === false) return null;

    const { updateOpenedQuickSetting } = useStore_OpenedQuickSetting();

    return (
        <button className={styles.software_update_button} onClick={()=>updateOpenedQuickSetting("update_software")}>
            <RefreshSvg className={styles.refresh_svg}/>
            <p className={styles.software_update_label}>{t("main_page.update_available")}</p>
        </button>
    );
};