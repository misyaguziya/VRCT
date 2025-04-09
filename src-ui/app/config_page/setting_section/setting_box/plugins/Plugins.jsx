import React from "react";
import { usePlugins } from "@logics_configs";
import styles from "./Plugins.module.scss";
import { PluginsControlComponent } from "../_components/plugins_control_component/PluginsControlComponent";

export const Plugins = () => {
    const {
        currentIsPluginsInitialized,
    } = usePlugins();

    if (!currentIsPluginsInitialized.data) return null;

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
        updatePluginsData,
        currentSavedPluginsStatus,
        setSavedPluginsStatus,
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
        const is_exists = currentSavedPluginsStatus.data.some(
            (d) => d.plugin_id === target_plugin_id
        );
        let new_value = [];
        if (is_exists) {
            new_value = currentSavedPluginsStatus.data.map((d) => {
                if (d.plugin_id === target_plugin_id) {
                    d.is_enabled = !d.is_enabled;
                }
                return d;
            });
        } else {
            new_value.push(...currentSavedPluginsStatus.data);
            new_value.push({
                plugin_id: target_plugin_id,
                is_enabled: true,
            });
        }

        // 「currentPluginsData.data」でis_downloadedがtrueのものだけ残す
        new_value = new_value.filter((item) =>
            currentPluginsData.data.some(
                (plugin) => plugin.plugin_id === item.plugin_id && plugin.is_downloaded
            )
        );

        setSavedPluginsStatus(new_value);
    };

    const variable_state = currentSavedPluginsStatus.state;

    return (
        <div className={styles.plugins_list_container}>
            {currentPluginsData.data.map((plugin) => (
                <div key={plugin.plugin_id} className={styles.plugin_wrapper}>
                    <p className={styles.title}>
                        {plugin.is_downloaded
                            ? plugin.downloaded_plugin_info?.title || plugin.latest_plugin_info.title
                            : plugin.latest_plugin_info.title}
                    </p>
                    <p className={styles.plugin_id}>{plugin.plugin_id}</p>
                    {plugin.error ? (
                        <p style={{ color: "red" }}>Error: {plugin.error}</p>
                    ) : (
                        <div className={styles.plugin_info_wrapper}>
                            <div className={styles.plugin_info}>
                                {/* 状態に応じた情報表示（例：バージョン等） */}
                                <p>
                                    {plugin.is_downloaded
                                        ? `現在のバージョン: ${plugin.downloaded_plugin_info?.plugin_version}`
                                        : `最新バージョン: ${plugin.latest_plugin_info.plugin_version}`}
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
