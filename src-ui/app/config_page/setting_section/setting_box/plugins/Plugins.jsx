import React, { useState, useEffect } from "react";
import { usePlugins } from "@logics_configs";
import styles from "./Plugins.module.scss";
import { PluginsControlComponent } from "../_components";

export const Plugins = () => {
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
    } = usePlugins();


    const downloadStartFunction = async (target_plugin_id) => {
        updatePluginsData((old_value) => {
            const new_value = old_value.data.map(d => {
                if (d.plugin_id === target_plugin_id) {
                    d.is_pending = true;
                }
                return d;
            });
            return new_value;
        });
        const target_plugin_info = currentPluginsData.data.find(d => d.plugin_id === target_plugin_id);
        downloadAndExtractPlugin(target_plugin_info).then(() => {
            updatePluginsData((old_value) => {
                const new_value = old_value.data.map(d => {
                    if (d.plugin_id === target_plugin_id) {
                        d.is_pending = false;
                        d.is_downloaded = true;
                    }
                    return d;
                });
                return new_value;
            });
        })
    };


    const toggleFunction = (target_plugin_id) => {
        const is_exists = currentSavedPluginsStatus.data.some(d => d.plugin_id === target_plugin_id);
        let new_value = [];
        if (is_exists) {
            new_value = currentSavedPluginsStatus.data.map(d => {
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


        // currentPluginsData.data で、is_downloaded が true のものだけ残す
        new_value = new_value.filter(item => {
            return currentPluginsData.data.some(plugin => plugin.plugin_id === item.plugin_id && plugin.is_downloaded);
        });

        setSavedPluginsStatus(new_value);
    }

    const variable_state = currentSavedPluginsStatus.state;


    return (
        <div className={styles.plugins_list_container}>
            {currentPluginsData.data.map((plugin) => (
                <div key={plugin.plugin_id} className={styles.plugin_wrapper}>
                    <p className={styles.title}>{plugin.title}</p>
                    <p className={styles.plugin_id}>{plugin.plugin_id}</p>
                    {plugin.error ? (
                        <p style={{ color: "red" }}>Error: {plugin.error}</p>
                    ) : (
                        <div className={styles.plugin_info_wrapper}>
                            <div className={styles.plugin_info}>
                                <p>Downloaded Version: {plugin.downloaded_plugin_version}</p>
                                <p>Latest Version: {plugin.latest_plugin_version}</p>
                                <p>
                                    Compatible: {plugin.min_supported_vrct_version} ~ {plugin.max_supported_vrct_version}
                                </p>
                            </div>
                            <PluginsControlComponent
                                variable_state={variable_state}
                                toggleFunction={toggleFunction}
                                plugin_status={plugin}
                                downloadStartFunction={downloadStartFunction}
                            />
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
};