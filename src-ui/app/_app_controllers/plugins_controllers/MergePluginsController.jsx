import { useEffect, useRef } from "react";
import { usePlugins } from "@logics_configs";
import { useSoftwareVersion } from "@logics_common";

export const MergePluginsController = () => {
    const {
        currentLoadedPlugins,
        updatePluginsData,
        currentPluginsData,
        currentFetchedPluginsInfo,
        currentSavedPluginsStatus,
        downloadAndExtractPlugin,
        toggleSavedPluginStatus,
    } = usePlugins();
    const { checkVrctVerCompatibility } = useSoftwareVersion();

    // downloaded, fetched, saved の各情報をまとめてマージ
    useEffect(() => {
        const mergePluginData = () => {
            updatePluginsData(prev => {
                // downloaded, fetched, 保存済み状態のMapをそれぞれ作成（plugin_id をキー）
                const downloaded_map = new Map(
                    currentLoadedPlugins.data.map(info => [info.plugin_id, info])
                );
                const fetched_map = new Map(
                    currentFetchedPluginsInfo.data.map(info => [info.plugin_id, info])
                );
                const saved_map = new Map(
                    currentSavedPluginsStatus.data.map(saved => [saved.plugin_id, saved])
                );
                const prev_map = new Map(
                    prev.data.map(item => [item.plugin_id, item])
                );

                // union_keys: Saved以外の情報に対して重複なくキーを取得する
                const union_keys = new Set([
                    ...downloaded_map.keys(),
                    ...fetched_map.keys(),
                    ...prev_map.keys(),
                ]);

                const new_data = [];
                for (const id of union_keys) {
                    const downloaded = downloaded_map.get(id);
                    const fetched = fetched_map.get(id);
                    const prev_plugin = prev_map.get(id);
                    let plugin = {};

                    if (downloaded) {
                        // ダウンロード済み情報に対してサポート確認
                        const { is_plugin_supported, is_plugin_supported_latest_vrct } =
                            checkVrctVerCompatibility(
                                downloaded.min_supported_vrct_version,
                                downloaded.max_supported_vrct_version
                            );
                        plugin = {
                            // prevの情報があれば引き継ぎつつ上書き
                            ...(prev_plugin || {}),
                            plugin_id: downloaded.plugin_id,
                            component: downloaded.component,
                            is_downloaded: true,
                            downloaded_plugin_info: {
                                ...downloaded,
                                is_plugin_supported,
                                is_plugin_supported_latest_vrct,
                            },
                        };

                        if (fetched) {
                            const is_latest_version_available =
                                (downloaded.plugin_version !== fetched.plugin_version && fetched.is_plugin_supported);
                            plugin = {
                                ...plugin,
                                is_outdated: false,
                                latest_plugin_info: { ...fetched },
                                is_latest_version_available:
                                    plugin.is_downloaded && is_latest_version_available,
                                is_latest_version_already:
                                    downloaded.plugin_version === fetched.plugin_version,
                            };
                        } else {
                            // フェッチ情報がない場合の初期状態
                            plugin = {
                                ...plugin,
                                is_latest_version_available: false,
                                is_latest_version_already: true,
                            };
                        }
                    } else if (fetched) {
                        // フェッチ情報のみの場合は、ダウンロードしていない初期状態
                        plugin = {
                            ...(prev_plugin || {}),
                            plugin_id: fetched.plugin_id,
                            is_downloaded: false,
                            is_latest_version_available: fetched.is_plugin_supported,
                            is_latest_version_already: false,
                            is_outdated: false,
                            latest_plugin_info: { ...fetched },
                        };
                    } else if (prev_plugin) {
                        // 既存情報のみ存在する場合は outdated フラグを付与
                        plugin = { ...prev_plugin, is_outdated: true };
                    }
                    // いずれかの情報がある場合のみ new_data に追加
                    if (plugin.plugin_id) {
                        new_data.push(plugin);
                    }
                }

                // 保存済み状態（currentSavedPluginsStatus）のマージ
                // ・new_dataに存在する各プラグインに対して、保存済みの is_enabled を上書き
                new_data.forEach(plugin => {
                    if (saved_map.has(plugin.plugin_id)) {
                        plugin.is_enabled = saved_map.get(plugin.plugin_id).is_enabled;
                    }
                });
                // ・prev.data には存在せず、保存済み情報にのみある場合は追加
                for (const [id, saved] of saved_map.entries()) {
                    if (!new_data.some(item => item.plugin_id === id)) {
                        new_data.push({ plugin_id: saved.plugin_id, is_enabled: saved.is_enabled });
                    }
                }


                // ダウンロード済みかつ有効なプラグインで、サポート対象でない場合は無効化
                new_data.forEach(plugin => {
                    if (plugin.is_downloaded && plugin.is_enabled) {
                        if (
                            !plugin.downloaded_plugin_info?.is_plugin_supported &&
                            !plugin.latest_plugin_info?.is_plugin_supported
                        ) {
                            plugin.is_enabled = false;
                            toggleSavedPluginStatus(plugin.plugin_id);
                        }
                    }
                });

                console.log("merged plugin data", new_data);
                return new_data;
            });
        };

        mergePluginData();
    }, [currentFetchedPluginsInfo.data, currentLoadedPlugins.data, currentSavedPluginsStatus]);



    // --- 自動アップデート（ダウンロード処理）---
    // ※downloadAndExtractPlugin の重複実行を防ぐため、実行中の plugin_id を useRef で管理
    const downloadingRef = useRef(new Set());

    useEffect(() => {
        if (!currentPluginsData.data.length) return;
        // マージ結果の currentPluginsData.data を元にダウンロード処理をチェック
        currentPluginsData.data.forEach(plugin => {
            if (plugin.is_downloaded &&
                plugin.is_enabled &&
                !plugin.is_latest_version_already &&
                plugin.is_latest_version_available
            ) {
                console.log(!downloadingRef.current.has(plugin.plugin_id));

                if (!downloadingRef.current.has(plugin.plugin_id)) {
                    downloadingRef.current.add(plugin.plugin_id);
                    downloadAndExtractPlugin(plugin)
                        .then(() => {
                            console.log(`Plugin ${plugin.plugin_id} updated successfully`);
                            downloadingRef.current.delete(plugin.plugin_id);
                        })
                        .catch((error) => {
                            console.error(`Plugin ${plugin.plugin_id} update failed`, error);
                            downloadingRef.current.delete(plugin.plugin_id);
                        });
                }
            }
        });
    }, [currentPluginsData.data]);

    return null;
};