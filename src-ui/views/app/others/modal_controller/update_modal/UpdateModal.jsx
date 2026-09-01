import { useEffect, useMemo, useState } from "react";
import { useI18n } from "@useI18n";
import clsx from "clsx";
import styles from "./UpdateModal.module.scss";

import {
    useComputeMode,
    useUpdateSoftware,
    useIsSoftwareUpdating,
    useSoftwareVersion,
    useAvailableReleases,
} from "@logics_common";
import { useUpdater } from "@logics_configs";
import { useStore_OpenedQuickSetting } from "@store";

import {
    SectionLabelComponent,
    LabelComponent,
    RadioButton,
    DropdownMenu,
} from "../../../config_page/setting_section/setting_box/_components";

import WarningSvg from "@images/warning.svg?react";
import CheckMarkSvg from "@images/check_mark.svg?react";
import RefreshSvg from "@images/refresh.svg?react";

export const UpdateModal = () => {
    const { t } = useI18n();
    const { updateOpenedQuickSetting } = useStore_OpenedQuickSetting();

    const { currentSoftwareVersion, currentLatestSoftwareVersionInfo } = useSoftwareVersion();
    const { currentComputeMode } = useComputeMode();
    const { currentReleaseChannel, setReleaseChannel } = useUpdater();
    const { currentAvailableReleases, getAvailableReleases } = useAvailableReleases();
    const { updateSoftware, updateSoftware_CUDA } = useUpdateSoftware();
    const { updateIsSoftwareUpdating } = useIsSoftwareUpdating();

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
                parts.push(`(${t("update_modal.beta_suffix")})`);
            }
            if (index === 0) {
                parts.push(`- ${t("update_modal.latest_suffix")}`);
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
        const exists = filtered_releases.some((release) => release.version === pending_version);
        if (exists) return;
        setPendingVersion(filtered_releases[0].version);
    }, [filtered_releases, pending_version]);

    const channel_options = [
        { id: "stable", label: t("update_modal.channel_stable") },
        { id: "beta", label: t("update_modal.channel_beta") },
    ];
    const compute_mode_options = [
        { id: "cpu", label: t("update_modal.compute_mode_cpu") },
        { id: "gpu", label: t("update_modal.compute_mode_gpu") },
    ];

    const selected_release = filtered_releases.find((r) => r.version === pending_version);
    const version_variable = { state: currentAvailableReleases.state, data: pending_version };
    const channel_variable = { state: currentReleaseChannel.state, data: effective_channel };
    const compute_mode_variable = { state: "ok", data: effective_compute_mode };

    const is_channel_changed =
        pending_channel !== null && pending_channel !== currentReleaseChannel.data;
    const is_compute_mode_changed =
        pending_compute_mode !== null && pending_compute_mode !== currentComputeMode.data;
    const is_version_changed =
        selected_release && selected_release.version !== currentSoftwareVersion.data;
    const has_any_pending_change =
        is_channel_changed || is_compute_mode_changed || is_version_changed;

    const is_update_available =
        currentLatestSoftwareVersionInfo.data.is_update_available === true;
    const latest_version = currentLatestSoftwareVersionInfo.data.new_version;

    // Hero mode
    let hero_mode; // "custom" | "update_available" | "up_to_date"
    if (has_any_pending_change) hero_mode = "custom";
    else if (is_update_available) hero_mode = "update_available";
    else hero_mode = "up_to_date";

    const isSemverGreater = (a, b) => {
        // Fallback simple semver compare (major.minor.patch[-pre]) — used only for downgrade badge.
        // The backend already validates supported versions, so this is UI-only sugar.
        if (!a || !b) return false;
        const parse = (v) => v.replace(/^v/, "").split("-")[0].split(".").map((n) => parseInt(n, 10) || 0);
        const [aM, am, ap] = parse(a);
        const [bM, bm, bp] = parse(b);
        if (aM !== bM) return aM > bM;
        if (am !== bm) return am > bm;
        return ap > bp;
    };
    const is_downgrade =
        is_version_changed && isSemverGreater(currentSoftwareVersion.data, selected_release.version);

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

    const onClickInstallLatest = () => {
        // shortcut used by the "update available" hero — apply current channel's latest
        if (!filtered_releases[0]) return;
        setPendingVersion(filtered_releases[0].version);
        // fall through to the same install flow immediately
        updateIsSoftwareUpdating(true);
        if (effective_compute_mode === "cpu") {
            updateSoftware(filtered_releases[0].version);
        } else {
            updateSoftware_CUDA(filtered_releases[0].version);
        }
    };

    const onClickRefresh = () => getAvailableReleases();
    const onClickClose = () => updateOpenedQuickSetting("");

    // Description strings for the summary
    const composeSummary = (version, channel, compute_mode) => {
        const ch = channel === "beta"
            ? t("update_modal.channel_beta")
            : t("update_modal.channel_stable");
        const cm = compute_mode === "gpu"
            ? t("update_modal.compute_mode_gpu")
            : t("update_modal.compute_mode_cpu");
        return `${version} · ${cm} · ${ch}`;
    };

    const current_summary = composeSummary(
        currentSoftwareVersion.data,
        currentReleaseChannel.data,
        currentComputeMode.data,
    );

    const target_summary = selected_release
        ? composeSummary(selected_release.version, effective_channel, effective_compute_mode)
        : "";

    // Warning list for "custom" hero
    const warnings = [];
    if (is_downgrade) {
        warnings.push(
            t("update_modal.warn_downgrade", {
                from: currentSoftwareVersion.data,
                to: selected_release.version,
            })
        );
    }
    if (is_compute_mode_changed && effective_compute_mode === "gpu") {
        warnings.push(t("update_modal.warn_gpu_extra_size"));
    }
    if (is_channel_changed && effective_channel === "beta") {
        warnings.push(t("update_modal.warn_switch_to_beta"));
    }
    if (is_channel_changed && effective_channel === "stable") {
        warnings.push(t("update_modal.warn_switch_to_stable"));
    }

    return (
        <div className={styles.modal_body}>
            <SectionLabelComponent label={t("update_modal.title")} />

            {/* Hero (framed banner) — state-aware */}
            {hero_mode === "update_available" && (
                <div className={styles.hero_frame}>
                    <div className={clsx(styles.hero_caption, styles.hero_caption_primary)}>
                        {t("update_modal.hero_update_available")}
                    </div>
                    <div className={styles.hero_headline}>
                        {latest_version}
                        <span className={styles.hero_headline_sub}>
                            {effective_channel === "beta"
                                ? t("update_modal.channel_beta")
                                : t("update_modal.channel_stable")}
                        </span>
                    </div>
                    <div className={styles.hero_current}>
                        {t("update_modal.current_prefix")}{current_summary}
                    </div>
                    <button
                        className={styles.install_button}
                        onClick={onClickInstallLatest}
                        disabled={!filtered_releases[0]}
                    >
                        {t("update_modal.install_latest_button")}
                    </button>
                </div>
            )}

            {hero_mode === "up_to_date" && (
                <div className={styles.hero_frame}>
                    <div className={clsx(styles.hero_caption, styles.hero_caption_ok)}>
                        <CheckMarkSvg className={styles.hero_caption_svg} />
                        {t("update_modal.hero_up_to_date")}
                    </div>
                    <div className={styles.hero_headline}>
                        {currentSoftwareVersion.data}
                        <span className={styles.hero_headline_sub}>
                            {currentReleaseChannel.data === "beta"
                                ? t("update_modal.channel_beta")
                                : t("update_modal.channel_stable")}
                        </span>
                    </div>
                    <div className={styles.hero_current}>
                        {t("update_modal.hero_up_to_date_desc")}
                    </div>
                </div>
            )}

            {hero_mode === "custom" && (
                <>
                    <div className={styles.hero_frame}>
                        <div className={styles.hero_caption}>
                            {t("update_modal.hero_custom_pending")}
                        </div>
                        <div className={styles.change_row}>
                            <div className={styles.change_col}>
                                <div className={styles.change_col_label}>
                                    {t("update_modal.change_col_current")}
                                </div>
                                <div className={styles.change_col_value}>{current_summary}</div>
                            </div>
                            <div className={styles.change_arrow}>→</div>
                            <div className={styles.change_col}>
                                <div className={styles.change_col_label}>
                                    {t("update_modal.change_col_after")}
                                </div>
                                <div className={styles.change_col_value}>
                                    {target_summary || "—"}
                                </div>
                            </div>
                        </div>
                        <button
                            className={styles.install_button}
                            onClick={onClickInstall}
                            disabled={!is_ready_to_install}
                        >
                            {t("update_modal.install_button")}
                        </button>
                    </div>

                    {warnings.length > 0 && (
                        <div className={styles.warnings_section}>
                            {warnings.map((w, i) => (
                                <div className={styles.warning_item} key={i}>
                                    <WarningSvg className={styles.warning_svg} />
                                    <p className={styles.warning_text}>{w}</p>
                                </div>
                            ))}
                        </div>
                    )}
                </>
            )}

            {/* Section: pick a different version */}
            <div className={styles.subsection_head}>
                <SectionLabelComponent label={t("update_modal.section_pick_variant")} />
                <button
                    className={styles.refresh_button}
                    onClick={onClickRefresh}
                    title={t("update_modal.refresh_button_title")}
                >
                    <RefreshSvg className={styles.refresh_svg} />
                    <span>{t("update_modal.refresh_button")}</span>
                </button>
            </div>

            <div className={styles.rows}>
                <div className={styles.row}>
                    <LabelComponent
                        label={t("update_modal.channel_label")}
                        desc={t("update_modal.channel_desc")}
                    />
                    <RadioButton
                        name="update_modal_channel"
                        options={channel_options}
                        checked_variable={channel_variable}
                        selectFunction={setPendingChannel}
                    />
                </div>
                <div className={styles.row}>
                    <LabelComponent
                        label={t("update_modal.compute_mode_label")}
                        desc={t("update_modal.compute_mode_desc")}
                    />
                    <RadioButton
                        name="update_modal_compute_mode"
                        options={compute_mode_options}
                        checked_variable={compute_mode_variable}
                        selectFunction={setPendingComputeMode}
                    />
                </div>
                <div className={styles.row}>
                    <LabelComponent
                        label={t("update_modal.version_label")}
                        desc={
                            filtered_releases.length === 0 && currentAvailableReleases.state === "ok"
                                ? t("update_modal.no_versions_available")
                                : t("update_modal.version_desc")
                        }
                    />
                    <DropdownMenu
                        dropdown_id="update_modal_version"
                        selected_id={pending_version}
                        list={list_for_ui}
                        selectFunction={(data) => setPendingVersion(data.selected_id)}
                        state={version_variable.state}
                    />
                </div>
            </div>

            {/* Footer actions */}
            <div className={styles.actions}>
                <button className={styles.close_button} onClick={onClickClose}>
                    {t("update_modal.close_button")}
                </button>
            </div>
        </div>
    );
};
