import styles from "./RightSideComponents.module.scss";
import HelpSvg from "@images/help.svg?react";

import { useStore_OpenedQuickSetting } from "@store";
import { useIsEnabledOverlaySmallLog, useEnableVrcMicMuteSync } from "@logics_configs";
import { OpenQuickSettingButton } from "./_buttons/OpenQuickSettingButton";

export const RightSideComponents = () => {
    return (
        <div className={styles.container}>
            <OpenVrcMicMuteSyncQuickSetting />
            <OpenOverlayQuickSetting />
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
    const { updateOpenedQuickSetting } = useStore_OpenedQuickSetting();
    const { currentEnableVrcMicMuteSync } = useEnableVrcMicMuteSync();

    const onClickFunction = () => {
        updateOpenedQuickSetting("vrc_mic_mute_sync");
    };

    return (
        <OpenQuickSettingButton
            label="VRC mic mute sync"
            variable={currentEnableVrcMicMuteSync.data}
            onClickFunction={onClickFunction}
        />
    );
};