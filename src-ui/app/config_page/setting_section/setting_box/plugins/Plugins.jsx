import React from "react";
import { usePlugins } from "@logics_configs";
import styles from "./Plugins.module.scss";
import { PluginsControlComponent } from "../_components/plugins_control_component/PluginsControlComponent";

export const Plugins = () => {
    const {
        currentIsPluginsInitialized,
    } = usePlugins();

    // if (!currentIsPluginsInitialized.data) return null;

    return (
        <div className={styles.container}>
            <PluginDownloadContainer />
        </div>
    );
};


const PluginDownloadContainer = () => {
    const {
        downloadAndExtractPlugin,
        currentPluginsData,
        currentSavedPluginsStatus,
        toggleSavedPluginStatus,
        handlePendingPlugin,
    } = usePlugins();

    // ダウンロード開始時の状態更新処理
    const downloadStartFunction = async (target_plugin_id) => {
        handlePendingPlugin(target_plugin_id, true);

        const target_plugin_info = currentPluginsData.data.find(
            (d) => d.plugin_id === target_plugin_id
        );
        downloadAndExtractPlugin(target_plugin_info).then(() => {
            handlePendingPlugin(target_plugin_id, false);
        });
    };

    // プラグインのオンオフ切り替え処理
    const toggleFunction = (target_plugin_id) => {
        toggleSavedPluginStatus(target_plugin_id);
    };

    const variable_state = currentSavedPluginsStatus.state;

    return (
        <div className={styles.plugins_list_container}>
            {currentPluginsData.data.map((plugin) => (
                <div key={plugin.plugin_id} className={styles.plugin_wrapper}>
                    <p className={styles.title}>
                        {plugin.is_downloaded
                            ? plugin.downloaded_plugin_info?.title
                            : plugin.latest_plugin_info?.title}
                    </p>
                    <p className={styles.plugin_id}>{plugin.plugin_id}</p>
                    {plugin.is_error ? (
                        <p style={{ color: "red" }}>Error: {plugin.error_message}</p>
                    ) : (
                        <div className={styles.plugin_info_wrapper}>
                            <div className={styles.plugin_info}>
                                <p>
                                    {plugin.is_downloaded
                                        ? `現在のバージョン: ${plugin.downloaded_plugin_info?.plugin_version}`
                                        : null}
                                </p>
                            </div>
                            <PluginsControlComponent
                                variable_state={variable_state}
                                toggleFunction={toggleFunction}
                                downloadStartFunction={downloadStartFunction}
                                plugin_status={plugin}
                            />
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
};
