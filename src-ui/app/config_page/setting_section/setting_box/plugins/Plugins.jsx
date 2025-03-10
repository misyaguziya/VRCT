import React, { useState, useEffect } from "react";
import semver from "semver";
import { usePlugins } from "@logics_configs";
import styles from "./Plugins.module.scss";
import { fetch as tauriFetch, ResponseType } from "@tauri-apps/api/http";

const MAIN_VRCT_VERSION = "3.0.5";
// PLUGIN_LIST_URL は中央リポジトリにある、各プラグインの plugin_info.json への URL の配列を保持する JSON の URL
const PLUGIN_LIST_URL = "https://raw.githubusercontent.com/ShiinaSakamoto/vrct_plugins_list/main/vrct_plugins_list.json";

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
        async function asyncFetchPluginInfoList() {
            try {
                // tauriFetch を使用して vrct_plugins_list.json を取得（CORS 対策）
                const response = await tauriFetch(PLUGIN_LIST_URL, {
                    method: "GET",
                    responseType: ResponseType.Json,
                    headers: { "Cache-Control": "no-cache" }
                });
                if (response.status !== 200) {
                    throw new Error("Failed to fetch plugin list, status: " + response.status);
                }
                // 取得される plugin_list.json は各プラグインの plugin_info.json への raw URL の配列とする
                const plugins_data = response.data;
                const updated_list = await Promise.all(
                    plugins_data.map(async (plugin_data) => {
                        try {
                            const plugin_manifest = await asyncFetchPluginManifest(plugin_data.url);
                            return { ...plugin_manifest };
                        } catch (error) {
                            console.error("Error fetching manifest for URL:", plugin_data.url, error);
                            // エラー発生時は、plugin_data.title とエラーメッセージを返す
                            return {
                                title: plugin_data.title,
                                plugin_id: plugin_data.plugin_id || plugin_data.title,
                                error: error.message,
                                url: plugin_data.url
                            };
                        }
                    })
                );
                set_plugin_list(updated_list);
            } catch (error) {
                console.error("Error fetching plugin info list:", error);
            }
        }
        asyncFetchPluginInfoList();
    }, []);

    const handleDownload = async (plugin) => {
        await downloadAndExtractPlugin(plugin);
    };

    return (
        <div>
            {plugin_list.map((plugin) => (
                <div key={plugin.plugin_id}>
                    <h3>{plugin.title}</h3>
                    <h4>{plugin.plugin_id}</h4>
                    {plugin.error ? (
                        <p style={{ color: "red" }}>Error: {plugin.error}</p>
                    ) : (
                        <>
                            <p>Version: {plugin.plugin_version}</p>
                            <p>
                                Compatible: {plugin.min_compatible_version} ~ {plugin.max_compatible_version}
                            </p>
                            <button onClick={() => handleDownload(plugin)}>
                                Download and Load Plugin
                            </button>
                            {download_progress[plugin.plugin_id] !== undefined && (
                                <div>
                                    Download Progress: {download_progress[plugin.plugin_id].toFixed(0)}%
                                </div>
                            )}
                        </>
                    )}
                </div>
            ))}
        </div>
    );
};

// GitHub Releases の latest 情報から plugin_info.json を取得する（tauriFetch を使用）
async function asyncFetchPluginManifest(manifest_url) {
    // リリース情報を取得
    const release_response = await tauriFetch(manifest_url, {
        method: "GET",
        responseType: ResponseType.Json,
        headers: {
            "Accept": "application/vnd.github+json",
            "User-Agent": "VRCTPluginApp"
        }
    });
    if (release_response.status !== 200) {
        throw new Error(`Failed to fetch release info from ${manifest_url}`);
    }
    const release_data = release_response.data;
    // assets 内に plugin_info.json があるかチェック
    const manifest_asset = release_data.assets.find(asset => asset.name === "plugin_info.json");
    if (!manifest_asset) {
        throw new Error("plugin_info.json not found in release assets");
    }
    // plugin_info.json の内容を取得
    const manifest_response = await tauriFetch(manifest_asset.browser_download_url, {
        method: "GET",
        responseType: ResponseType.Json,
        headers: {
            "Accept": "application/json",
            "User-Agent": "VRCTPluginApp",
            "Cache-Control": "no-cache"
        }
    });
    if (manifest_response.status !== 200) {
        throw new Error(`Failed to fetch plugin_info.json from ${manifest_asset.browser_download_url}`);
    }
    const plugin_manifest = manifest_response.data;
    return {
        title: plugin_manifest.title,
        plugin_id: plugin_manifest.plugin_id,
        plugin_version: plugin_manifest.plugin_version,
        min_compatible_version: plugin_manifest.min_compatible_version,
        max_compatible_version: plugin_manifest.max_compatible_version,
        asset_name: plugin_manifest.asset_name,
        url: manifest_url
    };
}

export { PluginDownloadContainer };



    // // プラグインのマニフェスト（plugin.json から取得した情報の例）
    // const plugin_manifest = {
    //     compatible_lower_version: "3.0.4",
    //     compatible_upper_version: "3.0.6",
    //     // 他の情報...
    // };

    // const isPluginCompatible = (main_version, lower_version, upper_version) => {
    //     // lower_version 以上かつ upper_version 以下なら互換性ありと判定
    //     return semver.gte(main_version, lower_version) && semver.lte(main_version, upper_version);
    // };

    // if (isPluginCompatible(currentSoftwareVersion.data, plugin_manifest.compatible_lower_version, plugin_manifest.compatible_upper_version)) {
    //     console.log("プラグインは互換性があります。");
    // } else {
    //     console.error("プラグインは現在の VRCT バージョンと互換性がありません。");
    // }