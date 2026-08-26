import { useEffect, useMemo, useState } from "react";
import { useI18n } from "@useI18n";
import styles from "./Updater.module.scss";

import {
    useComputeMode,
    useUpdateSoftware,
    useIsSoftwareUpdating,
    useSoftwareVersion,
    useAvailableReleases,
} from "@logics_common";

import {
    useUpdater,
} from "@logics_configs";

import {
    RadioButtonContainer,
    ActionButtonContainer,
    DropdownMenuContainer,
} from "../_templates/Templates";

import {
    SectionLabelComponent,
} from "../_components";

import { useStore_OpenedQuickSetting } from "@store";

import HelpSvg from "@images/help.svg?react";
import RefreshSvg from "@images/refresh.svg?react";
import CheckMarkSvg from "@images/check_mark.svg?react";

export const Updater = () => {
    const { t } = useI18n();

    return (
        <div className={styles.container}>
            <div>
                <ReleaseChannelContainer />
            </div>
            <div>
                <SectionLabelComponent label={t("config_page.updater.section_label_update")} />
                <OpenSwitchComputeDeviceModalContainer />
            </div>
            <div>
                <SectionLabelComponent label={t("config_page.updater.section_label_version_history")} />
                <VersionHistoryContainer />
            </div>
        </div>
    );
};

const ReleaseChannelContainer = () => {
    const { t } = useI18n();
    const { currentReleaseChannel, setReleaseChannel } = useUpdater();

    return (
        <RadioButtonContainer
            label={t("config_page.updater.release_channel.label")}
            desc={t("config_page.updater.release_channel.desc")}
            selectFunction={setReleaseChannel}
            name="release_channel"
            options={[
                { id: "stable", label: t("config_page.updater.release_channel.stable") },
                { id: "beta", label: t("config_page.updater.release_channel.beta") },
            ]}
            checked_variable={currentReleaseChannel}
        />
    );
};

const OpenSwitchComputeDeviceModalContainer = () => {
    const { t } = useI18n();
    const { updateOpenedQuickSetting } = useStore_OpenedQuickSetting();
    const onClickFunction = () => {
        updateOpenedQuickSetting("update_software");
    };

    return (
        <ActionButtonContainer
            label={t("config_page.updater.switch_compute_device.label")}
            IconComponent={HelpSvg}
            onclickFunction={onClickFunction}
        />
    );
};

const VersionHistoryContainer = () => {
    const { t } = useI18n();
    const { currentAvailableReleases, getAvailableReleases } = useAvailableReleases();
    const { updateSoftware, updateSoftware_CUDA } = useUpdateSoftware();
    const { updateIsSoftwareUpdating } = useIsSoftwareUpdating();
    const { currentComputeMode } = useComputeMode();
    const { currentSoftwareVersion } = useSoftwareVersion();
    const [selected_version, setSelectedVersion] = useState("");

    useEffect(() => {
        getAvailableReleases();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const list_for_ui = useMemo(() => {
        const result = {};
        currentAvailableReleases.data.forEach((release) => {
            const suffix = release.is_prerelease ? ` (${t("config_page.updater.version_history.beta_suffix")})` : "";
            result[release.version] = `${release.version}${suffix}`;
        });
        return result;
    }, [currentAvailableReleases.data, t]);

    useEffect(() => {
        if (selected_version || currentAvailableReleases.data.length === 0) return;
        setSelectedVersion(currentAvailableReleases.data[0].version);
    }, [currentAvailableReleases.data, selected_version]);

    const selectFunction = (selected_data) => {
        setSelectedVersion(selected_data.selected_id);
    };

    const onClickInstall = () => {
        if (!selected_version) return;
        updateIsSoftwareUpdating(true);
        if (currentComputeMode.data === "cpu") {
            updateSoftware(selected_version);
        } else {
            updateSoftware_CUDA(selected_version);
        }
    };

    const is_current_version_selected = selected_version && selected_version === currentSoftwareVersion.data;

    return (
        <>
            <DropdownMenuContainer
                dropdown_id="available_release_version"
                label={t("config_page.updater.version_history.label")}
                desc={t("config_page.updater.version_history.desc")}
                selected_id={selected_version}
                list={list_for_ui}
                selectFunction={selectFunction}
                state={currentAvailableReleases.state}
            />
            <ActionButtonContainer
                label={
                    is_current_version_selected
                        ? t("config_page.updater.version_history.is_current_version_already")
                        : t("config_page.updater.version_history.install_button")
                }
                IconComponent={RefreshSvg}
                ClickedIconComponent={CheckMarkSvg}
                clicked_duration={1000}
                onclickFunction={onClickInstall}
            />
        </>
    );
};
