import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { usePlugins } from "@logics_configs";
import styles from "./Plugins.module.scss";
import { PluginsControlComponent } from "../_components/plugins_control_component/PluginsControlComponent";
import { useNotificationStatus } from "@logics_common";

export const Plugins = () => {
    const {
        asyncFetchPluginsInfo,
    } = usePlugins();
    const hasRunRef = useRef(false);

    useEffect(() => {
        if (!hasRunRef.current) {
            asyncFetchPluginsInfo();
        }
        return () => hasRunRef.current = true;
    }, []);

    return (
        <div className={styles.container}>
            <PluginDownloadContainer />
        </div>
    );
};

const PluginDownloadContainer = () => {
    const { t, i18n } = useTranslation();
    const {
        downloadAndExtractPlugin,
        currentPluginsData,
        currentSavedPluginsStatus,
        toggleSavedPluginsStatus,
        handlePendingPlugin,
        currentFetchedPluginsInfo,
    } = usePlugins();
    const { showNotification_Success, showNotification_Error } = useNotificationStatus();

    // ダウンロード開始時の状態更新処理
    const downloadStartFunction = async (target_plugin_id) => {
        handlePendingPlugin(target_plugin_id, true);
        showNotification_Success(t("plugin_notifications.downloading"));

        const target_plugin_info = currentPluginsData.data.find(
            (d) => d.plugin_id === target_plugin_id
        );
        downloadAndExtractPlugin(target_plugin_info).then(() => {
            handlePendingPlugin(target_plugin_id, false);
            showNotification_Success(t("plugin_notifications.downloaded_success"));
        }).catch(error => {
            console.error(error);
            showNotification_Error(t("plugin_notifications.downloaded_error"));
        });
    };

    // プラグインのオンオフ切り替え処理
    const toggleFunction = (target_plugin_id) => {
        toggleSavedPluginsStatus(target_plugin_id);
    };

    const variable_state = currentSavedPluginsStatus.state;

    // plugin_id で ABC 順にソート
    const sorted_plugins_data = [...currentPluginsData.data].sort((a, b) =>
        a.plugin_id.localeCompare(b.plugin_id)
    );

    // Duplicate
    const is_failed_to_fetch = currentFetchedPluginsInfo.state === "error";
    const is_fetching = currentFetchedPluginsInfo.state === "pending";

    return (
        <div className={styles.plugins_list_container}>
            {is_failed_to_fetch && <p>Failed to fetch plugins data</p>}
            {is_fetching && <p>Fetching plugins data...</p>}
            {sorted_plugins_data.map((plugin) => {
                const target_info = plugin.is_downloaded
                    ? plugin.downloaded_plugin_info
                    : plugin.latest_plugin_info;

                const target_locale = target_info.locales && target_info.locales[i18n.language]
                ? target_info.locales[i18n.language]
                : {
                    title: target_info.title,
                    desc: target_info.desc || null,
                };

                return (
                    <div key={plugin.plugin_id} className={styles.plugin_wrapper}>
                        <p className={styles.title}>
                            {target_locale.title}
                        </p>
                        <p className={styles.plugin_id}>{plugin.plugin_id}</p>
                        <p className={styles.desc}>
                            {target_locale.desc}
                        </p>
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
                );
            })}
        </div>
    );
};