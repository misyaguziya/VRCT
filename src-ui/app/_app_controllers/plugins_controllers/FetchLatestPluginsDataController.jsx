import { useEffect } from "react";
import { usePlugins } from "@logics_configs";

export const FetchLatestPluginsDataController = () => {
    const {
        asyncFetchPluginsInfo,
        updatePluginsData,
        downloadAndExtractPlugin,
        currentIsInitializedLoadPlugin,
        currentIsFetchedPluginsInfo,
        updateIsFetchedPluginsInfo,
    } = usePlugins();

    const asyncUpdateLatestPluginsData = async () => {
        try {
            const info_array = await asyncFetchPluginsInfo();
            updatePluginsData(prev => {
                // Map を利用してそれぞれの配列を plugin_id で参照できるようにする
                const info_map = new Map(info_array.map(info => [info.plugin_id, info]));
                const prev_map = new Map(prev.data.map(item => [item.plugin_id, item]));

                console.log(prev_map);

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
                        console.log(plugin);

                        if (!plugin.is_latest_version_already && plugin.is_latest_version_available) {
                            await downloadAndExtractPlugin(plugin);
                        }
                    }
                });

                new_data.forEach(async plugin => {
                    if (plugin.is_downloaded && plugin.is_enabled) {
                        if (!plugin.downloaded_plugin_info?.is_plugin_supported && !plugin.latest_plugin_info?.is_plugin_supported) {
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

    useEffect(() => {
        console.log(currentIsInitializedLoadPlugin.data);
        if (currentIsInitializedLoadPlugin.data && !currentIsFetchedPluginsInfo.data) {
            asyncUpdateLatestPluginsData().then(() => {
                updateIsFetchedPluginsInfo(true);
            });
        }

    }, [currentIsInitializedLoadPlugin.data]);

    return null;
};