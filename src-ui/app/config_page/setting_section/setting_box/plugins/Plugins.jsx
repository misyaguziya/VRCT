import React, { useState, useEffect } from "react";
import { usePlugins } from "@logics_configs";
import styles from "./Plugins.module.scss";
import { DownloadPlugins } from "../_components";

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
        currentPluginsInfoList,
        updatePluginsInfoList,
        currentSavedPluginsStatus,
        updateSavedPluginsStatus,
        currentLoadedPluginsList,
        // updateLoadedPluginsList,
    } = usePlugins();

    const downloadStartFunction = async (target_plugin_id) => {
        updatePluginsInfoList((old_value) => {
            const new_value = old_value.data.map(d => {
                if (d.plugin_id === target_plugin_id) {
                    d.is_pending = true;
                }
                return d;
            });
            return new_value;
        });
        const target_plugin_info = currentPluginsInfoList.data.find(d => d.plugin_id === target_plugin_id);
        downloadAndExtractPlugin(target_plugin_info).then(() => {
            updatePluginsInfoList((old_value) => {
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
    // console.log(currentPluginsInfoList.data);


    // const plugin_list = currentPluginsInfoList.data;
    const plugin_list = [...currentPluginsInfoList.data, ...currentLoadedPluginsList.data];
    // const plugin_list = [
    //     {
    //         title: "VRCT Example Plugins 1",
    //         plugin_id: "vrct_plugin_example_1",
    //         asset_name: "vrct_plugin_example_1.zip",
    //         plugin_version: "0.0.6",
    //         min_supported_vrct_version: "3.0.4",
    //         max_supported_vrct_version: "3.0.6",
    //         is_plugin_supported: true,
    //         // url: manifest_url
    //     },
    //     {
    //         title: "VRCT Example Plugins 2",
    //         plugin_id: "vrct_plugin_example_2",
    //         asset_name: "vrct_plugin_example_2.zip",
    //         plugin_version: "0.0.1",
    //         min_supported_vrct_version: "3.0.4",
    //         max_supported_vrct_version: "3.0.7",
    //         is_plugin_supported: true,
    //         // url: manifest_url
    //     },
    // ];

    const getTargetPluginStatus = (target_plugin_id) => {
        let plugin_status = currentSavedPluginsStatus.data.find(d => d.plugin_id === target_plugin_id) ?? {};
        const is_downloaded = currentLoadedPluginsList.data.find(d => d.plugin_id === target_plugin_id) ? true : false;

        plugin_status.toggleFunction = () => {
            updateSavedPluginsStatus((old_value) => {
                const new_value = old_value.data.map(d => {
                    if (d.plugin_id === target_plugin_id) {
                        d.data = !d.data;
                        d.state = "ok";
                    }
                    return d;
                });
                return new_value;
            });
        }
        plugin_status.is_downloaded = is_downloaded;
        plugin_status.is_pending = false;
        return plugin_status;
    };



    return (
        <div className={styles.plugins_list_container}>
            {plugin_list.map((plugin) => (
                <div key={plugin.plugin_id} className={styles.plugin_wrapper}>
                    <p className={styles.title}>{plugin.title}</p>
                    <p className={styles.plugin_id}>{plugin.plugin_id}</p>
                    {plugin.error ? (
                        <p style={{ color: "red" }}>Error: {plugin.error}</p>
                    ) : (
                        <div className={styles.plugin_info_wrapper}>
                            <div className={styles.plugin_info}>
                                <p>Version: {plugin.plugin_version}</p>
                                <p>
                                    Compatible: {plugin.min_supported_vrct_version} ~ {plugin.max_supported_vrct_version}
                                </p>
                            </div>
                            <DownloadPlugins
                                plugin_info={plugin}
                                plugin_status={getTargetPluginStatus(plugin.plugin_id)}
                                downloadStartFunction={downloadStartFunction}
                            />
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
};