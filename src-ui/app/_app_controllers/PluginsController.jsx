import React, { useEffect, useRef } from "react";
import { usePlugins } from "@logics_configs";
import clsx from "clsx";

if (typeof window !== "undefined") {
    window.React = React;
    window.clsx = clsx;
}

export const PluginsController = ({ fetchPluginsHasRunRef }) => {
    const {
        asyncLoadAllPlugins,
        asyncFetchPluginsInfo,
        currentPluginsData,
        updatePluginsData,
        currentSavedPluginsStatus,
        updateIsPluginsInitialized,
        downloadAndExtractPlugin,
    } = usePlugins();

    useEffect(() => {
        const loadPlugins = async () => {
            try {
                await asyncLoadAllPlugins();
                const info_array = await asyncFetchPluginsInfo();
                updatePluginsData(prev => {
                    // Map を利用してそれぞれの配列を plugin_id で参照できるようにする
                    const info_map = new Map(info_array.map(info => [info.plugin_id, info]));
                    const prev_map = new Map(prev.data.map(item => [item.plugin_id, item]));

                    const new_data = [];
                    for (const info of info_array) {
                        let new_plugin_info = {};
                        if (prev_map.has(info.plugin_id)) { // plugin_id 登録済み
                            const target_downloaded_plugin = prev_map.get(info.plugin_id);
                            if (target_downloaded_plugin.is_downloaded) { // 既にダウンロード済み
                                const is_latest_version_available = !(target_downloaded_plugin.plugin_version === info.plugin_version);

                                new_plugin_info = {
                                    ...target_downloaded_plugin,
                                    is_downloaded: true,
                                    latest_plugin_info: { ...info },
                                    is_latest_version_available: is_latest_version_available,
                                    is_latest_version_already: (target_downloaded_plugin.downloaded_plugin_info?.plugin_version === info.plugin_version),
                                };
                            } else { // infoにもあり登録済みだがダウンロードされていない
                                new_plugin_info = {
                                    ...target_downloaded_plugin,
                                    is_downloaded: false,
                                    is_latest_version_already: false,
                                    is_latest_version_available: info.is_latest_version_available,
                                    latest_plugin_info: { ...info },
                                }
                            }
                        } else { // 未ダウンロード
                            new_plugin_info = {
                                plugin_id: info.plugin_id,
                                is_downloaded: false,
                                is_latest_version_already: false,
                                latest_plugin_info: { ...info },
                            };
                        }
                        new_data.push(new_plugin_info);
                    }

                    // prev.data にのみ存在するアイテム = latest plugin infoには存在しない
                    // を追加し、is_outdated: true を付与
                    prev.data.forEach(item => {
                        if (!info_map.has(item.plugin_id)) {
                            new_data.push({ ...item, is_outdated: true });
                        }
                    });

                    new_data.forEach(plugin => {
                        if (!plugin.is_outdated) {
                            plugin.is_latest_version_available = (plugin.latest_plugin_info.is_plugin_supported);
                        }
                    });

                    // ダウンロード済みで最新版じゃない場合、自動的にアップデート
                    // is_latest_version_supported: true のみ。
                    // 失敗した場合、現在のバージョンが非対応の場合はdisabledにする。
                    new_data.forEach(async plugin =>  {
                        if (plugin.is_enabled) {
                            if (!plugin.is_latest_version_already && plugin.is_latest_version_available) {
                                await downloadAndExtractPlugin(plugin);
                            }
                        }
                    });

                    new_data.forEach(async plugin =>  {
                        if (plugin.is_enabled) {
                            if (!plugin.downloaded_plugin_info?.is_plugin_supported) {
                                plugin.is_enabled = false
                            }
                        }
                    });

                    return new_data;
                });

            } catch (error) {
                console.error(error);
            }
        };

        if (!fetchPluginsHasRunRef.current) {
            loadPlugins();
            updateIsPluginsInitialized(true);
        }
        return () => fetchPluginsHasRunRef.current = true;
    }, []);


    useEffect(() => {
        updatePluginsData(prev => {
            // currentSavedPluginsStatus.data の各要素を Map 化して plugin_id で参照
            const saved_map = new Map(currentSavedPluginsStatus.data.map(saved => [saved.plugin_id, saved]));
            const prev_map = new Map(prev.data.map(item => [item.plugin_id, item]));
            // prev.data にある各アイテムについて、保存済みの状態情報があればマージ
            const merged = prev.data.map(item => {

                if (saved_map.has(item.plugin_id)) {
                    return { ...item, is_enabled: saved_map.get(item.plugin_id).is_enabled };
                }
                return item;
            });

            // currentSavedPluginsStatus.data にのみ存在する項目があれば追加
            currentSavedPluginsStatus.data.forEach(saved => {
                if (!prev_map.has(saved.plugin_id)) {
                    merged.push({ plugin_id: saved.plugin_id, is_enabled: saved.is_enabled });
                }
            });
            return merged;
        });
    }, [currentSavedPluginsStatus]);



    return null;
};