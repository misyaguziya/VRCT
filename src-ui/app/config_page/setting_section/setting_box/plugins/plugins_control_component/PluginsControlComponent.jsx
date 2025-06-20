import { SwitchBox } from "../../_components";
import { _DownloadButton } from "../../_components/_atoms/_download_button/_DownloadButton";
import styles from "./PluginsControlComponent.module.scss";
import { useI18n } from "@useI18n";

export const PluginsControlComponent = ({
    variable_state,
    plugin_status,
    toggleFunction,
    downloadStartFunction,
}) => {
    const { t } = useI18n();

    const option = {
        id: plugin_status.plugin_id,
        is_pending: plugin_status.is_pending,
        is_downloaded: plugin_status.is_downloaded,
        data: plugin_status.is_enabled,
        update_button: plugin_status.is_downloaded && plugin_status.is_latest_version_available,
        state: variable_state,
        progress: null,
    };

    const downloaded_version = plugin_status.downloaded_plugin_info?.plugin_version;
    const latest_version = plugin_status.latest_plugin_info?.plugin_version;

    const downloaded_version_label = t("config_page.plugins.downloaded_version",
        { downloaded_version: downloaded_version }
    );
    const latest_version_label = t("config_page.plugins.latest_version",
        { latest_version: latest_version }
    );

    if (plugin_status.is_downloaded) {
        return (
            <DownloadedPluginControl
                option={option}
                plugin_status={plugin_status}
                toggleFunction={toggleFunction}
                downloadStartFunction={downloadStartFunction}
                downloaded_version_label={downloaded_version_label}
                latest_version_label={latest_version_label}
            />
        );
    } else {
        return (
            <NotDownloadedPluginControl
                option={option}
                plugin_status={plugin_status}
                downloadStartFunction={downloadStartFunction}
                downloaded_version_label={downloaded_version_label}
                latest_version_label={latest_version_label}
            />
        );
    }
};


const DownloadedPluginControl = ({
    option,
    plugin_status,
    toggleFunction,
    downloadStartFunction,
    downloaded_version_label,
    latest_version_label,
}) => {
    const { t } = useI18n();

    const togglePlugin = () => {
        toggleFunction(plugin_status.plugin_id);
    };

    if (!plugin_status.downloaded_plugin_info.is_plugin_supported) {
        if (plugin_status.is_latest_version_available) {
            return (
                <div className={styles.container}>
                    <p>{downloaded_version_label}</p>
                    <p>{latest_version_label}</p>
                    <p>{t("config_page.plugins.available_after_updating")}</p>
                    <_DownloadButton option={option} downloadStartFunction={downloadStartFunction} />
                </div>
            );
        }
        return (
            <div className={styles.container}>
                <p>{t("config_page.plugins.unavailable_downloaded")}</p>
            </div>
        );
    } else if (plugin_status.is_outdated) {
        return (
            <div className={styles.container}>
                <p>{t("config_page.plugins.no_latest_info")}</p>
                <SwitchBox variable={option} toggleFunction={togglePlugin} />
            </div>
        );
    } else if (plugin_status.is_latest_version_already) {
        return (
            <div className={styles.container}>
                <p>{latest_version_label}</p>
                <p>{t("config_page.plugins.using_latest_version")}</p>
                <SwitchBox variable={option} toggleFunction={togglePlugin} />
            </div>
        );
    } else if (plugin_status.is_latest_version_available) {
        return (
            <div className={styles.container}>
                <p>{latest_version_label}</p>
                <p>{t("config_page.plugins.available_latest_version")}</p>
                <_DownloadButton option={option} downloadStartFunction={downloadStartFunction} />
                <SwitchBox variable={option} toggleFunction={togglePlugin} />
            </div>
        );
    } else {
        return (
            <div className={styles.container}>
                <p>{t("config_page.plugins.available_latest_version")}</p>
                <SwitchBox variable={option} toggleFunction={togglePlugin} />
            </div>
        );
    }
};


const NotDownloadedPluginControl = ({
    option,
    plugin_status,
    downloadStartFunction,
    downloaded_version_label,
    latest_version_label,
}) => {
    const { t } = useI18n();

    if (plugin_status.is_latest_version_available) {
        return (
            <div className={styles.container}>
                <p>{latest_version_label}</p>
                <_DownloadButton option={option} downloadStartFunction={downloadStartFunction} />
            </div>
        );
    } else if (plugin_status.latest_plugin_info?.is_plugin_supported_latest_vrct) {
        return (
            <div className={styles.container}>
                <p>{latest_version_label}</p>
                <p>{t("config_page.plugins.available_in_latest_vrct_version")}</p>
            </div>
        );
    } else {
        return (
            <div className={styles.container}>
                <p>{latest_version_label}</p>
                <p>{t("config_page.plugins.unavailable_not_downloaded")}</p>
            </div>
        );
    }
};
