import semver from "semver";

import { invoke } from "@tauri-apps/api/tauri";
import {
    createAtomWithHook,
    useStore_SavedPluginsStatus,
    useStore_PluginsData,
} from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

import { transform } from "@babel/standalone";
import { writeFile, createDir, exists, removeDir, readDir, BaseDirectory, readTextFile } from "@tauri-apps/api/fs";
import { dev_plugins } from "@plugins_index";
const imported_dev_plugins = [];
dev_plugins.forEach(async ({entry_path}) => {
    imported_dev_plugins.push({
        index: await import(`@plugins_path/${entry_path}/index.jsx`),
        plugin_info:  await import(`@plugins_path/${entry_path}/plugin_info.json`),
    });
})

import JSZip from "jszip";

import { useFetch } from "@logics_common";
import { useSoftwareVersion } from "@logics_configs";

import * as logics_configs from "@logics_configs";
import * as logics_main from "@logics_main";
import * as logics_common from "@logics_common";


// PLUGIN_LIST_URL は中央リポジトリにある、各プラグインの plugin_info.json への URL の配列を保持する JSON の URL
const PLUGIN_LIST_URL = "https://raw.githubusercontent.com/ShiinaSakamoto/vrct_plugins_list/main/vrct_plugins_list.json";

export const usePlugins = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentSavedPluginsStatus, updateSavedPluginsStatus, pendingSavedPluginsStatus } = useStore_SavedPluginsStatus();
    const { currentPluginsData, updatePluginsData, pendingPluginsData } = useStore_PluginsData();
    const { currentSoftwareVersion } = useSoftwareVersion();

    const { asyncTauriFetchGithub } = useFetch();

    const generatePluginContext= (plugin_info) => {
        const plugin_context = {
            registerComponent: (component) => {
                if (!plugin_info.plugin_id || !plugin_info.location || !component) {
                    return console.error("An invalid plugin was detected.", plugin_info.plugin_id, plugin_info.location, component);
                }
                updatePluginsData(prev => {
                    const new_value = prev.data.map(old_value =>
                        old_value.plugin_id === plugin_info.plugin_id
                            ? {
                                ...old_value,
                                ...plugin_info,
                                downloaded_plugin_version: plugin_info.plugin_version,
                                component: component,
                                is_downloaded: true,
                                is_latest_version_available: false,
                            } : old_value
                    );

                    return new_value;
                });
            },
            createAtomWithHook: (...args) => createAtomWithHook(...args),
            logics: { ...logics_common, ...logics_configs, ...logics_main }
        };
        return plugin_context;
    }

    const asyncLoadPlugin = async (plugin_folder_relative_path) => {
        const init_path = "plugins/" + plugin_folder_relative_path + "/index.esm.js";
        const plugin_info_path = "plugins/" + plugin_folder_relative_path + "/plugin_info.json";
        const plugin_css_path = "plugins/" + plugin_folder_relative_path + "/main.css";
        try {
            const plugin_info_json = await readTextFile(plugin_info_path, { dir: BaseDirectory.Resource, recursive: true });
            const plugin_info = JSON.parse(plugin_info_json);

            const plugin_code = await readTextFile(init_path, { dir: BaseDirectory.Resource, recursive: true });
            const cleaned_code = removeImportStatements(plugin_code);
            const transpiled_code = transform(cleaned_code, {
                presets: [
                    ["env", { modules: false }],
                    "react",
                ],
                sourceType: "module"
            }).code;
            const blob = new Blob([transpiled_code], { type: "text/javascript" });
            const blob_url = URL.createObjectURL(blob);
            const plugin_module = await import(/* @vite-ignore */ blob_url);
            URL.revokeObjectURL(blob_url);

            if (plugin_module && plugin_module.init) {
                plugin_module.init(generatePluginContext(plugin_info));
            }
            await loadPluginCSS(plugin_css_path);

        } catch (error) {
            console.error("Failed to load plugin from", plugin_folder_relative_path, error);
        }
    };

    const asyncLoadAllPlugins = async () => {
        if (!import.meta.env.DEV) {
            imported_dev_plugins.forEach(({ index, plugin_info }) => {
                if (!index || !plugin_info) {
                    console.error("Invalid development plugin detected", index, plugin_info);
                    return;
                }
                const plugin_context = generatePluginContext(plugin_info);
                if (index.init) {
                    index.init(plugin_context);
                } else {
                    console.error("Plugin missing init function", plugin_info);
                }
            });
        } else {
            try {
                const plugin_files = await readDir("plugins", { dir: BaseDirectory.Resource, recursive: true });
                for (const target_dir of plugin_files) {
                    const target_path = target_dir.name;
                    await asyncLoadPlugin(target_path);
                }
            } catch (error) {
                console.error("Error loading plugins:", error);
            }
        }
    };

    const downloadAndExtractPlugin = async (plugin) => {
        try {
            const plugin_zip_url = await fetchLatestPluginZipUrl(plugin);
            // Rust コマンド経由で ZIP をダウンロード
            const base64_zip = await invoke("download_zip_asset", { url: plugin_zip_url });
            // base64_zip をデコードして Uint8Array に変換
            const binary_string = atob(base64_zip);
            const len = binary_string.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {
                bytes[i] = binary_string.charCodeAt(i);
            }

            // JSZip で ZIP を解凍
            const zip = await JSZip.loadAsync(bytes);

            // 展開先ディレクトリのパス（例："plugins/<plugin_id>" とする）
            const target_plugin_path = "plugins/" + plugin.plugin_id;
            // 既に存在する場合は削除してから新規作成
            if (await exists(target_plugin_path, { dir: BaseDirectory.Resource, recursive: true })) {
                await removeDir(target_plugin_path, { dir: BaseDirectory.Resource, recursive: true });
            }
            await createDir(target_plugin_path, { dir: BaseDirectory.Resource, recursive: true });

            const file_promises = [];
            zip.forEach((relative_path, zip_entry) => {
                // .git 以下のファイルはスキップ
                if (relative_path.startsWith(".git") || relative_path.includes("/.git/")) {
                    return;
                }
                const file_path = target_plugin_path + "/" + relative_path;
                if (zip_entry.dir) {
                    file_promises.push(
                        createDir(file_path, { dir: BaseDirectory.Resource, recursive: true }).catch((err) => {
                            if (!err.message?.includes("already exists")) {
                                console.error("Failed to create directory:", file_path, err);
                            }
                        })
                    );
                } else {
                    const dir_path = file_path.substring(0, file_path.lastIndexOf("/"));
                    const promise = createDir(dir_path, { dir: BaseDirectory.Resource, recursive: true })
                        .catch((err) => {
                            if (!err.message?.includes("already exists")) {
                                console.error("Failed to create parent directory:", dir_path, err);
                            }
                        })
                        .then(() => zip_entry.async("text"))
                        .then(async (file_data) => {
                            await writeFile(file_path, file_data, { dir: BaseDirectory.Resource, recursive: true });
                        });
                    file_promises.push(promise);
                }
            });

            await Promise.all(file_promises);
            console.log("Plugin downloaded successfully.");

            const index_file_relative_path = plugin.plugin_id;
            await asyncLoadPlugin(index_file_relative_path);

            console.log("Plugin loaded successfully.");
        } catch (error) {
            console.error("Error downloading and extracting plugin:", error);
        }
    };

    const fetchLatestPluginZipUrl = async (plugin) => {
        const api_url = plugin.url;
        const response = await asyncTauriFetchGithub(api_url);
        if (response.status !== 200) {
            throw new Error("Failed to fetch latest release info, status: " + response.status);
        }
        const release_info = response.data;
        const asset = release_info.assets.find((a) => a.name === plugin.asset_name);
        if (!asset) {
            throw new Error(`Asset ${plugin.asset_name} not found in the latest release`);
        }
        return asset.browser_download_url;
    };


    const asyncFetchPluginsInfo = async () => {
        try {
            const response = await asyncTauriFetchGithub(PLUGIN_LIST_URL);
            if (response.status !== 200) {
                throw new Error("Failed to fetch plugin list, status: " + response.status);
            }
            const plugins_data = response.data;
            const updated_list = await Promise.all(
                plugins_data.map(async (plugin_data) => {
                    try {
                        const plugin_info = await asyncFetchPluginInfo(plugin_data.url);
                        return { ...plugin_info };
                    } catch (error) {
                        console.error("Error fetching plugin info for URL:", plugin_data.url, error);
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
            return updated_list;
        } catch (error) {
            console.error("Error fetching plugin info list:", error);
        }
    }

    const asyncFetchPluginInfo = async (plugin_info_asset_url) => {
        const release_response = await asyncTauriFetchGithub(plugin_info_asset_url);
        if (release_response.status !== 200) {
            throw new Error(`Failed to fetch release info from ${plugin_info_asset_url}`);
        }
        const plugin_info_json = release_response.data.assets.find(asset => asset.name === "plugin_info.json");
        if (!plugin_info_json) {
            throw new Error("plugin_info.json not found in release assets");
        }
        const plugin_info_json_response = await asyncTauriFetchGithub(plugin_info_json.browser_download_url);
        if (plugin_info_json_response.status !== 200) {
            throw new Error(`Failed to fetch plugin_info.json from ${plugin_info_json.browser_download_url}`);
        }
        const plugin_info = plugin_info_json_response.data;

        const isPluginCompatible = (main_version, lower_version, upper_version) => {
            console.log(main_version, lower_version, upper_version);

            // lower_version 以上かつ upper_version 以下なら互換性ありと判定
            return semver.gte(main_version, lower_version) && semver.lte(main_version, upper_version);
        };

        const is_plugin_supported = isPluginCompatible(currentSoftwareVersion.data, plugin_info.min_supported_vrct_version, plugin_info.max_supported_vrct_version);

        return {
            title: plugin_info.title,
            plugin_id: plugin_info.plugin_id,
            plugin_version: plugin_info.plugin_version,
            min_supported_vrct_version: plugin_info.min_supported_vrct_version,
            max_supported_vrct_version: plugin_info.max_supported_vrct_version,
            is_plugin_supported: is_plugin_supported,
            asset_name: plugin_info.asset_name,
            url: plugin_info_asset_url
        };
    }

    const setSavedPluginsStatus = (plugins_status) => {
        pendingSavedPluginsStatus();
        asyncStdoutToPython("/set/data/plugins_status", plugins_status);
    };



    return {
        asyncFetchPluginsInfo,

        asyncLoadAllPlugins,
        downloadAndExtractPlugin,

        currentSavedPluginsStatus,
        updateSavedPluginsStatus,

        currentPluginsData,
        updatePluginsData,

        setSavedPluginsStatus,
    };
};

const removeImportStatements = (code) => {
    return code
        .split("\n")
        .filter(line => !line.match(/^import\s+.*['"]react['"]/))
        .join("\n");
};

// import { readTextFile, BaseDirectory } from "@tauri-apps/api/fs";

const loadPluginCSS = async (plugin_css_path) => {
    try {
        // プラグインフォルダのルートにある main.css を読み込む
        const css_content = await readTextFile(plugin_css_path, { dir: BaseDirectory.Resource });
        // style タグを作成して head に挿入する
        const style_tag = document.createElement("style");
        style_tag.id = `plugin-css-${plugin_css_path.replace(/[^a-zA-Z0-9_-]/g, "")}`;
        style_tag.textContent = css_content;
        document.head.appendChild(style_tag);
        console.log("Plugin CSS loaded for:", plugin_css_path);
    } catch (error) {
        console.error("Failed to load plugin CSS from", plugin_css_path, error);
    }
};

export { loadPluginCSS };
