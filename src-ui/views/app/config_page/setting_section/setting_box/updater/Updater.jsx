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
    DropdownMenuContainer,
} from "../_templates/Templates";

import {
    LabelComponent,
    SectionLabelComponent,
} from "../_components";

export const Updater = () => {
    return (
        <div className={styles.container}>
            <InstallPanel />
        </div>
    );
};

const InstallPanel = () => {
    const { t } = useI18n();
    const { currentReleaseChannel, setReleaseChannel } = useUpdater();
    const { currentAvailableReleases, getAvailableReleases } = useAvailableReleases();
    const { updateSoftware, updateSoftware_CUDA } = useUpdateSoftware();
    const { updateIsSoftwareUpdating } = useIsSoftwareUpdating();
    const { currentComputeMode } = useComputeMode();
    const { currentSoftwareVersion } = useSoftwareVersion();

    const [pending_channel, setPendingChannel] = useState(null);
    const [pending_compute_mode, setPendingComputeMode] = useState(null);
    const [pending_version, setPendingVersion] = useState("");

    useEffect(() => {
        getAvailableReleases();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(() => {
        if (pending_channel !== null) return;
        if (!currentReleaseChannel.data) return;
        setPendingChannel(currentReleaseChannel.data);
    }, [currentReleaseChannel.data, pending_channel]);

    useEffect(() => {
        if (pending_compute_mode !== null) return;
        if (!currentComputeMode.data) return;
        setPendingComputeMode(currentComputeMode.data);
    }, [currentComputeMode.data, pending_compute_mode]);

    const effective_channel = pending_channel ?? currentReleaseChannel.data ?? "stable";
    const effective_compute_mode = pending_compute_mode ?? currentComputeMode.data ?? "cpu";

    const filtered_releases = useMemo(() => {
        const list = currentAvailableReleases.data;
        if (effective_channel === "beta") {
            return list.filter((release) => release.is_prerelease);
        }
        return list.filter((release) => !release.is_prerelease);
    }, [currentAvailableReleases.data, effective_channel]);

    const list_for_ui = useMemo(() => {
        const result = {};
        filtered_releases.forEach((release, index) => {
            const parts = [release.version];
            if (release.is_prerelease) {
                parts.push(`(${t("config_page.updater.install_panel.beta_suffix")})`);
            }
            if (index === 0) {
                parts.push(`- ${t("config_page.updater.install_panel.latest_suffix")}`);
            }
            result[release.version] = parts.join(" ");
        });
        return result;
    }, [filtered_releases, t]);

    useEffect(() => {
        if (filtered_releases.length === 0) {
            if (pending_version !== "") setPendingVersion("");
            return;
        }
        const exists_in_filtered = filtered_releases.some((release) => release.version === pending_version);
        if (exists_in_filtered) return;
        setPendingVersion(filtered_releases[0].version);
    }, [filtered_releases, pending_version]);

    const channel_options = [
        { id: "stable", label: t("config_page.updater.install_panel.channel_stable") },
        { id: "beta", label: t("config_page.updater.install_panel.channel_beta") },
    ];

    const compute_mode_options = [
        { id: "cpu", label: t("config_page.updater.install_panel.compute_mode_cpu") },
        { id: "gpu", label: t("config_page.updater.install_panel.compute_mode_gpu") },
    ];

    const channel_variable = { state: currentReleaseChannel.state, data: effective_channel };
    const compute_mode_variable = { state: "ok", data: effective_compute_mode };

    const selected_release = filtered_releases.find((release) => release.version === pending_version);

    const is_same_as_current =
        selected_release &&
        selected_release.version === currentSoftwareVersion.data &&
        effective_compute_mode === currentComputeMode.data;

    const is_ready_to_install = Boolean(selected_release) && filtered_releases.length > 0;

    const onClickInstall = () => {
        if (!is_ready_to_install) return;
        if (pending_channel && pending_channel !== currentReleaseChannel.data) {
            setReleaseChannel(pending_channel);
        }
        updateIsSoftwareUpdating(true);
        if (effective_compute_mode === "cpu") {
            updateSoftware(selected_release.version);
        } else {
            updateSoftware_CUDA(selected_release.version);
        }
    };

    const current_summary_value = t("config_page.updater.install_panel.current_summary_value", {
        version: currentSoftwareVersion.data,
        compute_mode:
            currentComputeMode.data === "cpu"
                ? t("config_page.updater.install_panel.compute_mode_cpu")
                : t("config_page.updater.install_panel.compute_mode_gpu"),
        channel:
            currentReleaseChannel.data === "beta"
                ? t("config_page.updater.install_panel.channel_beta")
                : t("config_page.updater.install_panel.channel_stable"),
    });

    return (
        <div className={styles.panel}>
            <SectionLabelComponent label={t("config_page.updater.install_panel.section_label")} />
            <LabelComponent
                label={t("config_page.updater.install_panel.current_summary_label")}
                desc={current_summary_value}
            />
            <RadioButtonContainer
                label={t("config_page.updater.install_panel.channel_label")}
                selectFunction={setPendingChannel}
                name="updater_channel"
                options={channel_options}
                checked_variable={channel_variable}
            />
            <RadioButtonContainer
                label={t("config_page.updater.install_panel.compute_mode_label")}
                selectFunction={setPendingComputeMode}
                name="updater_compute_mode"
                options={compute_mode_options}
                checked_variable={compute_mode_variable}
            />
            <DropdownMenuContainer
                dropdown_id="updater_version"
                label={t("config_page.updater.install_panel.version_label")}
                desc={
                    filtered_releases.length === 0 && currentAvailableReleases.state === "ok"
                        ? t("config_page.updater.install_panel.no_versions_available")
                        : t("config_page.updater.install_panel.version_desc")
                }
                selected_id={pending_version}
                list={list_for_ui}
                selectFunction={(data) => setPendingVersion(data.selected_id)}
                state={currentAvailableReleases.state}
            />
            <div className={styles.install_button_wrapper}>
                <button
                    className={styles.install_button}
                    onClick={onClickInstall}
                    disabled={!is_ready_to_install}
                >
                    {is_same_as_current
                        ? t("config_page.updater.install_panel.reinstall_button")
                        : t("config_page.updater.install_panel.install_button")}
                </button>
            </div>
        </div>
    );
};
