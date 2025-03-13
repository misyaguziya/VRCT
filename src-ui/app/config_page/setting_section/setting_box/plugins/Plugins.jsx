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
    } = usePlugins();

    const downloadStartFunction = async (plugin) => {
        updatePluginsInfoList((old_value) => {
            const new_value = old_value.data.map(d => {
                if (d.plugin_id === plugin.plugin_id) {
                    d.is_pending = true;
                }
                return d;
            });
            return new_value;
        });
        await downloadAndExtractPlugin(plugin);
        updatePluginsInfoList((old_value) => {
            const new_value = old_value.data.map(d => {
                if (d.plugin_id === plugin.plugin_id) {
                    d.is_pending = false;
                }
                return d;
            });
            return new_value;
        });
    };

    const plugin_list = currentPluginsInfoList.data;
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
                                downloadStartFunction={downloadStartFunction}
                            />
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
};