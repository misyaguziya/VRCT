import React from "react";
import { SwitchBox } from "../index";
import { _DownloadButton } from "../_atoms/_download_button/_DownloadButton";
import styles from "./PluginsControlComponent.module.scss";

export const PluginsControlComponent = ({
    variable_state,
    plugin_status,
    toggleFunction,
    downloadStartFunction,
}) => {
    const option = {
        id: plugin_status.plugin_id,
        is_pending: plugin_status.is_pending,
        is_downloaded: plugin_status.is_downloaded,
        data: plugin_status.is_enabled,
        update_button: plugin_status.is_downloaded && plugin_status.is_latest_version_available,
        state: variable_state,
        progress: null,
    };

    if (plugin_status.is_downloaded) {
        return (
            <DownloadedPluginControl
                option={option}
                plugin_status={plugin_status}
                toggleFunction={toggleFunction}
                downloadStartFunction={downloadStartFunction}
            />
        );
    } else {
        return (
            <NotDownloadedPluginControl
                option={option}
                plugin_status={plugin_status}
                downloadStartFunction={downloadStartFunction}
            />
        );
    }
};


const DownloadedPluginControl = ({
    option,
    plugin_status,
    toggleFunction,
    downloadStartFunction,
}) => {
    const togglePlugin = () => {
        toggleFunction(plugin_status.plugin_id);
    };

    const latest_version = plugin_status.latest_plugin_info?.plugin_version;

    if (plugin_status.is_latest_version_already) {
        return (
            <div className={styles.container}>
                <p>最新のバージョン: {latest_version}</p>
                <p>最新版を使用中</p>
                <SwitchBox variable={option} toggleFunction={togglePlugin} />
            </div>
        );
    } else if (plugin_status.is_latest_version_available) {
        return (
            <div className={styles.container}>
                <p>最新のバージョン: {latest_version}</p>
                <p>最新版を利用可能</p>
                <_DownloadButton option={option} downloadStartFunction={downloadStartFunction} />
                <SwitchBox variable={option} toggleFunction={togglePlugin} />
            </div>
        );
    } else {
        return (
            <div className={styles.container}>
                <p>最新のバージョン: {latest_version}</p>
                <SwitchBox variable={option} toggleFunction={togglePlugin} />
            </div>
        );
    }
};


const NotDownloadedPluginControl = ({ option, plugin_status, downloadStartFunction }) => {
    const latest_version = plugin_status.latest_plugin_info?.plugin_version;

    if (plugin_status.is_latest_version_available) {
        return (
            <div className={styles.container}>
                <p>最新バージョン: {latest_version}</p>
                <_DownloadButton option={option} downloadStartFunction={downloadStartFunction} />
            </div>
        );
    } else {
        return (
            <div className={styles.container}>
                <p>最新バージョン: {latest_version}</p>
                <p>現在利用不可</p>
            </div>
        );
    }
};
