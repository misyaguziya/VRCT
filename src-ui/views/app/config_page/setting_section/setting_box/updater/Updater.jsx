import { useEffect, useMemo, useState } from "react";
import { useI18n } from "@useI18n";
import clsx from "clsx";
import styles from "./Updater.module.scss";

import {
    useComputeMode,
    useUpdateSoftware,
    useIsSoftwareUpdating,
    useSoftwareVersion,
    useAvailableReleases,
} from "@logics_common";
import { useUpdater } from "@logics_configs";

import {
    SectionLabelComponent,
    LabelComponent,
    RadioButton,
    DropdownMenu,
} from "../_components";

import { store } from "@store";

import WarningSvg from "@images/warning.svg?react";
import CheckMarkSvg from "@images/check_mark.svg?react";
import RefreshSvg from "@images/refresh.svg?react";

const isSemverGreater = (a, b) => {
    if (!a || !b) return false;
    const parse = (v) => v.replace(/^v/, "").split("-")[0].split(".").map((n) => parseInt(n, 10) || 0);
    const [aM, am, ap] = parse(a);
    const [bM, bm, bp] = parse(b);
    if (aM !== bM) return aM > bM;
    if (am !== bm) return am > bm;
    return ap > bp;
};

export const Updater = () => {
    const { t } = useI18n();

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
        if (store.is_fetched_available_releases_already) return;
        store.is_fetched_available_releases_already = true;
        getAvailableReleases();
    }, []);

    const target_channel = tmp_selected_channel ?? currentReleaseChannel.data ?? "stable";
    const target_compute_mode = tmp_selected_compute_mode ?? currentComputeMode.data ?? "cpu";

    const filtered_releases = useMemo(() => {
        const list = Array.isArray(currentAvailableReleases.data) ? currentAvailableReleases.data : [];
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
                parts.push(`(${t("update_modal.channel_beta")})`);
            }
            if (index === 0) {
                parts.push(`- ${t("update_modal.latest_label")}`);
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

    const is_custom = is_channel_changed || is_compute_mode_changed || is_version_customized;

    const is_newer_version_available = Boolean(latest_release_version) && isSemverGreater(latest_release_version, currentSoftwareVersion.data);
    const is_update_available =
        currentLatestSoftwareVersionInfo.data.is_update_available === true || is_newer_version_available;

    const is_latest_newer = Boolean(latest_release_version) && latest_release_version !== currentSoftwareVersion.data;

    const summary_mode = useMemo(() => {
        if (is_custom) return "custom";
        if (is_update_available && is_latest_newer) return "update_available";
        return "up_to_date";
    }, [is_custom, is_update_available, is_latest_newer]);

    const is_ready_to_install = Boolean(target_version) && filtered_releases.length > 0;
    const is_fetching_releases = currentAvailableReleases.state === "pending";

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

    const onClickRefresh = () => {
        if (is_fetching_releases) return;
        getAvailableReleases();
    };

    return (
        <div className={styles.container}>
            <SectionLabelComponent label={t("update_modal.title")} />

            {/* Update Summary */}
            <div className={styles.summary_container}>
                <UpdateSummary
                    summary_mode={summary_mode}
                    current_compute_mode={currentComputeMode.data}
                    target_compute_mode={target_compute_mode}
                    current_channel={currentReleaseChannel.data}
                    target_channel={target_channel}
                    current_version={currentSoftwareVersion.data}
                    target_version={target_version}
                />
                {summary_mode !== "up_to_date" && (
                    <button
                        className={styles.install_button}
                        onClick={onClickInstall}
                        disabled={!is_ready_to_install}
                    >
                        {summary_mode === "update_available"
                            ? t("update_modal.install_latest_button")
                            : t("update_modal.install_button")}
                    </button>
                )}
            </div>

            <div className={styles.subsection_head}>
                <SectionLabelComponent label={t("update_modal.section_pick_variant")} />
                <button
                    className={styles.refresh_button}
                    onClick={onClickRefresh}
                    disabled={is_fetching_releases}
                >
                    <RefreshSvg className={clsx(styles.refresh_svg, is_fetching_releases && styles.is_spinning)} />
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
        </div>
    );
};

/* ===== Subcomponents: UpdateSummary switcher ===== */
const UpdateSummary = ({ summary_mode, ...props }) => {
    switch (summary_mode) {
        case "update_available":
        case "custom":
            return <SummaryCustomDiff {...props} />;
        case "up_to_date":
            return <SummaryUpToDate {...props} />;
        default:
            return null;
    }
};

const SummaryUpToDate = ({ current_version, current_channel }) => {
    const { t } = useI18n();
    return (
        <div className={styles.up_to_date_layout}>
            <CheckMarkSvg className={styles.up_to_date_check_svg} />
            <div className={styles.up_to_date_text}>
                <div className={styles.up_to_date_version}>
                    {current_version}
                    <span className={styles.up_to_date_channel}>
                        {current_channel === "beta"
                            ? t("update_modal.channel_beta")
                            : t("update_modal.channel_stable")}
                    </span>
                </div>
                <div className={styles.up_to_date_desc}>
                    {t("update_modal.summary_up_to_date_desc")}
                </div>
            </div>
        </div>
    );
};

const DiffRow = ({ label, before, after, is_changed, warning, is_warning = false }) => (
    <div className={clsx(styles.diff_group, is_changed && styles.diff_group_changed)}>
        <div className={styles.diff_row}>
            <div className={styles.diff_item_label}>{label}</div>
            <div className={styles.diff_val_before}>{before}</div>
            <div className={styles.diff_arrow_container}>
                <svg
                    className={clsx(
                        styles.diff_arrow_svg,
                        is_changed && (is_warning ? styles.diff_arrow_svg_warning : styles.diff_arrow_svg_changed)
                    )}
                    viewBox="0 0 24 24"
                >
                    <path fill="currentColor" d="M4 11h12.17l-5.59-5.59L12 4l8 8-8 8-1.41-1.41L16.17 13H4v-2z" />
                </svg>
            </div>
            <div
                className={clsx(
                    styles.diff_val_after,
                    is_changed && (is_warning ? styles.diff_val_warning : styles.diff_val_changed)
                )}
            >
                {after}
            </div>
        </div>
        {warning && (
            <div className={styles.diff_row_warning}>
                <WarningSvg className={styles.diff_warning_svg} />
                <p className={styles.diff_warning_text}>{warning}</p>
            </div>
        )}
    </div>
);

const SummaryCustomDiff = ({
    current_compute_mode,
    target_compute_mode,
    current_channel,
    target_channel,
    current_version,
    target_version,
}) => {
    const { t } = useI18n();

    const is_compute_mode_changed = target_compute_mode !== current_compute_mode;
    const is_channel_changed = target_channel !== current_channel;
    const is_version_changed = Boolean(target_version) && target_version !== current_version;

    const is_downgrade =
        is_version_changed && isSemverGreater(current_version, target_version);

    const warning_compute_mode =
        is_compute_mode_changed && target_compute_mode === "cuda"
            ? t("update_modal.warn_cuda_extra_size")
            : null;

    const warning_channel = is_channel_changed
        ? t("update_modal.warn_switch_channel", {
            channel:
                target_channel === "beta"
                    ? t("update_modal.channel_beta")
                    : t("update_modal.channel_stable"),
        })
        : null;

    const warning_version = is_downgrade
        ? t("update_modal.warn_downgrade", {
            from: current_version,
            to: target_version,
        })
        : null;

    return (
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
            <DiffRow
                label={t("update_modal.compute_mode_label")}
                before={
                    current_compute_mode === "cuda"
                        ? t("update_modal.compute_mode_cuda")
                        : t("update_modal.compute_mode_cpu")
                }
                after={
                    target_compute_mode === "cuda"
                        ? t("update_modal.compute_mode_cuda")
                        : t("update_modal.compute_mode_cpu")
                }
                is_changed={is_compute_mode_changed}
                warning={warning_compute_mode}
            />

            {/* Row 2: リリースチャンネル */}
            <DiffRow
                label={t("update_modal.channel_label")}
                before={
                    current_channel === "beta"
                        ? t("update_modal.channel_beta")
                        : t("update_modal.channel_stable")
                }
                after={
                    target_channel === "beta"
                        ? t("update_modal.channel_beta")
                        : t("update_modal.channel_stable")
                }
                is_changed={is_channel_changed}
                warning={warning_channel}
            />

            {/* Row 3: バージョン */}
            <DiffRow
                label={t("update_modal.version_label")}
                before={current_version}
                after={target_version || "—"}
                is_changed={is_version_changed}
                is_warning={is_downgrade}
                warning={warning_version}
            />
        </div>
    );
};
