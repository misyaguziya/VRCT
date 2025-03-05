import React, { useState, useEffect } from "react";
import { usePlugins } from "@logics_configs";
import styles from "./Plugins.module.scss";

export const Plugins = () => {
    return (
        <div className={styles.container}>
            <PluginDownloadContainer />
        </div>
    );
};

const PluginDownloadContainer = () => {
    const [plugin_list, set_plugin_list] = useState([]);
    const [download_progress, set_download_progress] = useState({});

    const { downloadAndExtractPlugin } = usePlugins();

    useEffect(() => {
        // GitHub上のJSONファイルからプラグインリストを取得
        const fetchPluginList = async () => {
            try {
                const response = await fetch(
                    "https://raw.githubusercontent.com/ShiinaSakamoto/vrct_plugins_list/main/vrct_plugins_list.json"
                );
                if (!response.ok) {
                    throw new Error("Failed to fetch plugin list");
                }
                const data = await response.json();
                set_plugin_list(data);
            } catch (error) {
                console.error("Error fetching plugin list:", error);
            }
        };
        fetchPluginList();
    }, []);

    const handleDownload = async (plugin) => {
        await downloadAndExtractPlugin(plugin);
    };

    return (
        <div>
            {plugin_list.map((plugin) => (
                <div key={plugin.plugin_id}>
                    <h3>{plugin.title}</h3>
                    <button onClick={() => handleDownload(plugin)}>
                        Download and Load Plugin
                    </button>
                    {download_progress[plugin.plugin_id] !== undefined && (
                        <div>
                            Download Progress: {download_progress[plugin.plugin_id].toFixed(0)}%
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
};

