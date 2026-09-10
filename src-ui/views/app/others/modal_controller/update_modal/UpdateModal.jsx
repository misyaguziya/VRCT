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

    const [tmp_selected_channel, setTmpSelectedChannel] = useState(null);
    const [tmp_selected_compute_mode, setTmpSelectedComputeMode] = useState(null);
    const [tmp_selected_version, setTmpSelectedVersion] = useState(null);

    useEffect(() => {
        getAvailableReleases();
    }, []);

    const target_channel = tmp_selected_channel ?? currentReleaseChannel.data ?? "stable";
    const target_compute_mode = tmp_selected_compute_mode ?? currentComputeMode.data ?? "cpu";

    const filtered_releases = useMemo(() => {
        const list = currentAvailableReleases.data;
        if (target_channel === "beta") {
            return list.filter((release) => release.is_prerelease);
        }
        return list.filter((release) => !release.is_prerelease);
    }, [currentAvailableReleases.data, target_channel]);

    const target_version = tmp_selected_version ?? filtered_releases[0]?.version ?? "";

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
        if (tmp_selected_version === null) return;
        if (!filtered_releases.some((r) => r.version === tmp_selected_version)) {
            setTmpSelectedVersion(null);
        }
    }, [filtered_releases, tmp_selected_version]);

    const channel_options = [
        { id: "stable", label: t("update_modal.channel_stable") },
        { id: "beta", label: t("update_modal.channel_beta") },
    ];
    const compute_mode_options = [
        { id: "cpu", label: t("update_modal.compute_mode_cpu") },
        { id: "cuda", label: t("update_modal.compute_mode_cuda") },
    ];

    const version_variable = { state: currentAvailableReleases.state, data: target_version };
    const channel_variable = { state: currentReleaseChannel.state, data: target_channel };
    const compute_mode_variable = { state: "ok", data: target_compute_mode };

    const latest_release_version = filtered_releases[0]?.version;

    const is_channel_changed = target_channel !== currentReleaseChannel.data;
    const is_compute_mode_changed = target_compute_mode !== currentComputeMode.data;
    const is_version_customized = Boolean(
        target_version &&
        latest_release_version &&
        target_version !== latest_release_version
    );

    const is_version_changed = Boolean(target_version) && target_version !== currentSoftwareVersion.data;

    const is_custom = is_channel_changed || is_compute_mode_changed || is_version_customized;

    const is_update_available =
        currentLatestSoftwareVersionInfo.data.is_update_available === true;
    const latest_version = currentLatestSoftwareVersionInfo.data.new_version;

    // Hero mode
    let hero_mode; // "custom" | "update_available" | "up_to_date"
    if (is_custom) hero_mode = "custom";
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
        is_version_changed && isSemverGreater(currentSoftwareVersion.data, target_version);

    const is_ready_to_install = Boolean(target_version) && filtered_releases.length > 0;

    const onClickInstall = () => {
        if (!is_ready_to_install) return;
        if (target_channel !== currentReleaseChannel.data) {
            setReleaseChannel(target_channel);
        }
        updateIsSoftwareUpdating(true);
        if (target_compute_mode === "cpu") {
            updateSoftware(target_version);
        } else {
            updateSoftware_CUDA(target_version);
        }
    };

    const onClickRefresh = () => getAvailableReleases();
    const onClickClose = () => updateOpenedQuickSetting("");

    // Description strings for the summary
    const composeSummary = (version, channel, compute_mode) => {
        const ch = channel === "beta"
            ? t("update_modal.channel_beta")
            : t("update_modal.channel_stable");
        const cm = compute_mode === "cuda"
            ? t("update_modal.compute_mode_cuda")
            : t("update_modal.compute_mode_cpu");
        return `${version} · ${cm} · ${ch}`;
    };

    const current_summary = composeSummary(
        currentSoftwareVersion.data,
        currentReleaseChannel.data,
        currentComputeMode.data,
    );

    // Warning items for corresponding rows
    const warning_compute_mode =
        is_compute_mode_changed && target_compute_mode === "cuda"
            ? t("update_modal.warn_cuda_extra_size")
            : null;

    const warning_channel = is_channel_changed
        ? target_channel === "beta"
            ? t("update_modal.warn_switch_to_beta")
            : t("update_modal.warn_switch_to_stable")
        : null;

    const warning_version = is_downgrade
        ? t("update_modal.warn_downgrade", {
            from: currentSoftwareVersion.data,
            to: target_version,
        })
        : null;

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
                            {target_channel === "beta"
                                ? t("update_modal.channel_beta")
                                : t("update_modal.channel_stable")}
                        </span>
                    </div>
                    <div className={styles.hero_current}>
                        {t("update_modal.current_prefix")}{current_summary}
                    </div>
                    <button
                        className={styles.install_button}
                        onClick={onClickInstall}
                        disabled={!is_ready_to_install}
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
                <div className={styles.hero_frame}>
                    <div className={styles.hero_caption}>
                        {t("update_modal.hero_custom")}
                    </div>
                    <div className={styles.diff_table}>
                        <div className={styles.diff_header}>
                            <div />
                            <div className={styles.diff_header_cell_before}>
                                {t("update_modal.change_col_current")}
                            </div>
                            <div />
                            <div className={styles.diff_header_cell_after}>
                                {t("update_modal.change_col_after")}
                            </div>
                        </div>

                        {/* Row 1: デバイス構成 */}
                        <div className={clsx(styles.diff_group, is_compute_mode_changed && styles.diff_group_changed)}>
                            <div className={styles.diff_row}>
                                <div className={styles.diff_item_label}>
                                    {t("update_modal.compute_mode_label")}
                                </div>
                                <div className={styles.diff_val_before}>
                                    {currentComputeMode.data === "cuda"
                                        ? t("update_modal.compute_mode_cuda")
                                        : t("update_modal.compute_mode_cpu")}
                                </div>
                                <div className={styles.diff_arrow_container}>
                                    <svg
                                        className={clsx(styles.diff_arrow_svg, is_compute_mode_changed && styles.diff_arrow_svg_changed)}
                                        viewBox="0 0 24 24"
                                    >
                                        <path fill="currentColor" d="M4 11h12.17l-5.59-5.59L12 4l8 8-8 8-1.41-1.41L16.17 13H4v-2z" />
                                    </svg>
                                </div>
                                <div className={clsx(styles.diff_val_after, is_compute_mode_changed && styles.diff_val_changed)}>
                                    {target_compute_mode === "cuda"
                                        ? t("update_modal.compute_mode_cuda")
                                        : t("update_modal.compute_mode_cpu")}
                                </div>
                            </div>
                            {warning_compute_mode && (
                                <div className={styles.diff_row_warning}>
                                    <WarningSvg className={styles.diff_warning_svg} />
                                    <p className={styles.diff_warning_text}>{warning_compute_mode}</p>
                                </div>
                            )}
                        </div>

                        {/* Row 2: リリースチャンネル */}
                        <div className={clsx(styles.diff_group, is_channel_changed && styles.diff_group_changed)}>
                            <div className={styles.diff_row}>
                                <div className={styles.diff_item_label}>
                                    {t("update_modal.channel_label")}
                                </div>
                                <div className={styles.diff_val_before}>
                                    {currentReleaseChannel.data === "beta"
                                        ? t("update_modal.channel_beta")
                                        : t("update_modal.channel_stable")}
                                </div>
                                <div className={styles.diff_arrow_container}>
                                    <svg
                                        className={clsx(styles.diff_arrow_svg, is_channel_changed && styles.diff_arrow_svg_changed)}
                                        viewBox="0 0 24 24"
                                    >
                                        <path fill="currentColor" d="M4 11h12.17l-5.59-5.59L12 4l8 8-8 8-1.41-1.41L16.17 13H4v-2z" />
                                    </svg>
                                </div>
                                <div className={clsx(styles.diff_val_after, is_channel_changed && styles.diff_val_changed)}>
                                    {target_channel === "beta"
                                        ? t("update_modal.channel_beta")
                                        : t("update_modal.channel_stable")}
                                </div>
                            </div>
                            {warning_channel && (
                                <div className={styles.diff_row_warning}>
                                    <WarningSvg className={styles.diff_warning_svg} />
                                    <p className={styles.diff_warning_text}>{warning_channel}</p>
                                </div>
                            )}
                        </div>

                        {/* Row 3: バージョン */}
                        <div className={clsx(styles.diff_group, is_version_changed && styles.diff_group_changed)}>
                            <div className={styles.diff_row}>
                                <div className={styles.diff_item_label}>
                                    {t("update_modal.version_label")}
                                </div>
                                <div className={styles.diff_val_before}>
                                    {currentSoftwareVersion.data}
                                </div>
                                <div className={styles.diff_arrow_container}>
                                    <svg
                                        className={clsx(styles.diff_arrow_svg, is_version_changed && styles.diff_arrow_svg_changed)}
                                        viewBox="0 0 24 24"
                                    >
                                        <path fill="currentColor" d="M4 11h12.17l-5.59-5.59L12 4l8 8-8 8-1.41-1.41L16.17 13H4v-2z" />
                                    </svg>
                                </div>
                                <div className={clsx(styles.diff_val_after, is_version_changed && styles.diff_val_changed)}>
                                    {target_version || "—"}
                                </div>
                            </div>
                            {warning_version && (
                                <div className={styles.diff_row_warning}>
                                    <WarningSvg className={styles.diff_warning_svg} />
                                    <p className={styles.diff_warning_text}>{warning_version}</p>
                                </div>
                            )}
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
                {/* 1. デバイス構成 */}
                <div className={styles.row}>
                    <LabelComponent
                        label={t("update_modal.compute_mode_label")}
                        desc={t("update_modal.compute_mode_desc")}
                    />
                    <RadioButton
                        name="update_modal_compute_mode"
                        options={compute_mode_options}
                        checked_variable={compute_mode_variable}
                        selectFunction={setTmpSelectedComputeMode}
                    />
                </div>
                {/* 2. リリースチャンネル */}
                <div className={styles.row}>
                    <LabelComponent
                        label={t("update_modal.channel_label")}
                        desc={t("update_modal.channel_desc")}
                    />
                    <RadioButton
                        name="update_modal_channel"
                        options={channel_options}
                        checked_variable={channel_variable}
                        selectFunction={setTmpSelectedChannel}
                    />
                </div>
                {/* 3. インストールするバージョン */}
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
                        selected_id={target_version}
                        list={list_for_ui}
                        selectFunction={(data) => setTmpSelectedVersion(data.selected_id)}
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
