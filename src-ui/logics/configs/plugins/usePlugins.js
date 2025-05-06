import { invoke } from "@tauri-apps/api/core";
import { useTranslation } from "react-i18next";
import { IS_PLUGIN_PATH_DEV_MODE, getPluginsList } from "@ui_configs";
import {
    store,

    createAtomWithHook,
    useStore_SavedPluginsStatus,
    useStore_PluginsData,

    useStore_FetchedPluginsInfo,
    useStore_LoadedPlugins,
} from "@store";
import { useStdoutToPython } from "@logics/useStdoutToPython";

import { transform } from "@babel/standalone";
import { writeFile, mkdir, exists, remove, readDir, BaseDirectory, readTextFile } from "@tauri-apps/plugin-fs";
import { dev_plugins } from "@plugins_index";
const imported_dev_plugins = [];
dev_plugins.forEach(async ({entry_path}) => {
    imported_dev_plugins.push({
        index: await import(`@plugins_path/${entry_path}/index.jsx`),
        downloaded_plugin_info:  await import(`@plugins_path/${entry_path}/plugin_info.json`),
    });
})

import JSZip from "jszip";

import { useFetch, useSoftwareVersion, useNotificationStatus } from "@logics_common";

import * as logics_configs from "@logics_configs";
import * as logics_main from "@logics_main";
import * as logics_common from "@logics_common";

// PLUGIN_LIST_URL は中央リポジトリにある、各プラグインの plugin_info.json への URL の配列を保持する JSON の URL
const PLUGIN_LIST_URL = getPluginsList();

export const usePlugins = () => {
    const { t } = useTranslation();
    const { showNotification_Success, showNotification_Error } = useNotificationStatus();
    const { asyncStdoutToPython } = useStdoutToPython();

    const { currentFetchedPluginsInfo, updateFetchedPluginsInfo, pendingFetchedPluginsInfo, errorFetchedPluginsInfo } = useStore_FetchedPluginsInfo();
    const { currentLoadedPlugins, updateLoadedPlugins, pendingLoadedPlugins } = useStore_LoadedPlugins();

    const { currentSavedPluginsStatus, updateSavedPluginsStatus, pendingSavedPluginsStatus } = useStore_SavedPluginsStatus();
    const { currentPluginsData, updatePluginsData, pendingPluginsData } = useStore_PluginsData();
    const { checkVrctVerCompatibility } = useSoftwareVersion();

    const { asyncTauriFetchGithub } = useFetch();


    const { i18n } = useTranslation();

    const generatePluginContext = (downloaded_plugin_info) => {
        const plugin_context = {
            registerComponent: (component) => {
                if (!downloaded_plugin_info.plugin_id || !downloaded_plugin_info.location || !component) {
                    return console.error("An invalid plugin was detected.", downloaded_plugin_info.plugin_id, downloaded_plugin_info.location, component);
                }

                updateLoadedPlugins(prev => {
                    const prev_map = new Map(prev.data.map(item => [item.plugin_id, item]));
                    prev_map.set(downloaded_plugin_info.plugin_id, {
                        ...downloaded_plugin_info,
                        component: component,
                    });
                    return Array.from(prev_map.values());
                });

            },
            createAtomWithHook: (...args) => createAtomWithHook(...args),
            logics: { ...logics_common, ...logics_configs, ...logics_main },
            i18n: i18n,
        };
        return plugin_context;
    }

    const asyncLoadPlugin = async (plugin_folder_relative_path) => {
        const init_path = "plugins/" + plugin_folder_relative_path + "/index.esm.js";
        const downloaded_plugin_info_path = "plugins/" + plugin_folder_relative_path + "/plugin_info.json";
        const plugin_css_path = "plugins/" + plugin_folder_relative_path + "/main.css";
        try {
            const downloaded_plugin_info_json = await readTextFile(downloaded_plugin_info_path, { baseDir: BaseDirectory.Resource, recursive: true });
            const downloaded_plugin_info = JSON.parse(downloaded_plugin_info_json);

            const plugin_code = await readTextFile(init_path, { baseDir: BaseDirectory.Resource, recursive: true });
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
                plugin_module.init(generatePluginContext(downloaded_plugin_info));
            }
            await loadPluginCSS(plugin_css_path);

        } catch (error) {
            console.error("Failed to load plugin from", plugin_folder_relative_path, error);
        }
    };

    const asyncLoadAllPlugins = async () => {
        if (IS_PLUGIN_PATH_DEV_MODE) {
            imported_dev_plugins.forEach(({ index, downloaded_plugin_info }) => {
                if (!index || !downloaded_plugin_info) {
                    console.error("Invalid development plugin detected", index, downloaded_plugin_info);
                    return;
                }
                const plugin_context = generatePluginContext(downloaded_plugin_info);
                if (index.init) {
                    index.init(plugin_context);
                } else {
                    console.error("Plugin missing init function", downloaded_plugin_info);
                }
            });
        } else {
            const is_plugins_dir_exists = await exists("plugins", { baseDir: BaseDirectory.Resource });
            if (!is_plugins_dir_exists) return;

            try {
                const plugin_entries = await readDir("plugins", { baseDir: BaseDirectory.Resource, recursive: true });
                const plugin_files = plugin_entries.filter(entry => entry.isDirectory === true);

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
        const { latest_plugin_info } = plugin;
        try {
            // 1. ZIP をダウンロード (ブラウザの fetch を使用)
            const pluginZipUrl = await fetchLatestPluginZipUrl(latest_plugin_info);
            console.log('start download', pluginZipUrl);
            const res = await asyncTauriFetchGithub(pluginZipUrl, {return_row: true});
            if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
            const arrayBuffer = await res.arrayBuffer();
            const bytes = new Uint8Array(arrayBuffer);

            // 2. JSZip で ZIP を解凍
            const zip = await JSZip.loadAsync(bytes);

            // 3. 展開先ディレクトリを準備
            const targetPath = `plugins/${latest_plugin_info.plugin_id}`;
            if (await exists(targetPath, { baseDir: BaseDirectory.Resource })) {
                await remove(targetPath, { baseDir: BaseDirectory.Resource, recursive: true });
            }
            await mkdir(targetPath, { baseDir: BaseDirectory.Resource, recursive: true });

            // 4. ZIP 内のエントリをひとつずつ展開 & 書き出し
            const filePromises = [];
            zip.forEach((relativePath, entry) => {
                // .git 以下はスキップ
                if (relativePath.startsWith('.git') || relativePath.includes('/.git/')) {
                    return;
                }
                const filePath = `${targetPath}/${relativePath}`;
                if (entry.dir) {
                    // ディレクトリの場合は mkdir
                    filePromises.push(
                        mkdir(filePath, { baseDir: BaseDirectory.Resource, recursive: true })
                            .catch(err => {
                                if (!err.message.includes('already exists')) {
                                    console.error('Failed to create directory:', filePath, err);
                                }
                            })
                    );
                } else {
                    // ファイルの場合は親ディレクトリを確保してからバイナリ書き込み
                    const dirPath = filePath.substring(0, filePath.lastIndexOf('/'));
                    filePromises.push(
                        mkdir(dirPath, { baseDir: BaseDirectory.Resource, recursive: true })
                            .catch(err => {
                                if (!err.message.includes('already exists')) {
                                    console.error('Failed to create parent directory:', dirPath, err);
                                }
                            })
                            .then(() => entry.async('uint8array'))
                            .then(data =>
                                writeFile(filePath, data, { baseDir: BaseDirectory.Resource })
                            )
                    );
                }
            });
            await Promise.all(filePromises);

            console.log('Plugin downloaded successfully.');
            // 5. プラグインをロード
            await asyncLoadPlugin(latest_plugin_info.plugin_id);
            console.log('Plugin loaded successfully.');
        } catch (error) {
            console.error('Error downloading and extracting plugin:', error);
        }
    };

    const fetchLatestPluginZipUrl = async (plugin) => {
        const api_url = plugin.url;
        const release_info = await asyncTauriFetchGithub(api_url);
        const asset = release_info.assets.find((a) => a.name === plugin.asset_name);
        if (!asset) {
            throw new Error(`Asset ${plugin.asset_name} not found in the latest release`);
        }
        return asset.browser_download_url;
    };


    const asyncFetchPluginsInfo = async () => {
        if (store.is_fetched_plugins_info_already) return;
        store.is_fetched_plugins_info_already = true;

        try {
            const plugins_data = await asyncTauriFetchGithub(PLUGIN_LIST_URL);
            const updated_list = await Promise.all(
                plugins_data.map(async (plugin_data) => {
                    try {
                        const plugin_info = await asyncFetchPluginInfo(plugin_data.url);
                        return {
                            ...plugin_info,
                            homepage_link: plugin_data.homepage_link,
                        };
                    } catch (error) {
                        console.error("Error fetching plugin info for URL: ", plugin_data.url, error);
                        return {
                            title: plugin_data.title,
                            plugin_id: plugin_data.plugin_id || plugin_data.title,
                            is_error: true,
                            error_message: error.message,
                            url: plugin_data.url,
                            homepage_link: plugin_data.homepage_link,
                        };
                    }
                })
            );
            updateFetchedPluginsInfo(updated_list);
        } catch (error) {
            console.error("Error fetching plugin info list: ", error);
            errorFetchedPluginsInfo();
        }

        store.is_initialized_fetched_plugin_info = true;
    }

    const asyncFetchPluginInfo = async (plugin_info_asset_url) => {

        const release_response = await asyncTauriFetchGithub(plugin_info_asset_url);
        const plugin_info_json = release_response.assets.find(asset => asset.name === "plugin_info.json");
        if (!plugin_info_json) {
            throw new Error("plugin_info.json not found in release assets");
        }
        const plugin_info = await asyncTauriFetchGithub(plugin_info_json.browser_download_url);

        const { is_plugin_supported, is_plugin_supported_latest_vrct } = checkVrctVerCompatibility(plugin_info.min_supported_vrct_version, plugin_info.max_supported_vrct_version);

        return {
            ...plugin_info,
            is_plugin_supported: is_plugin_supported,
            is_plugin_supported_latest_vrct: is_plugin_supported_latest_vrct,
            url: plugin_info_asset_url,
        };
    }

    const handlePendingPlugin = (target_plugin_id, is_pending) => {
        updatePluginsData((old_value) => {
            const new_value = old_value.data.map((d) => {
                if (d.plugin_id === target_plugin_id) {
                    d.is_pending = is_pending;
                }
                return d;
            });
            return new_value;
        });
    };

    const toggleSavedPluginsStatus = (target_plugin_id) => {
        const is_exists = currentSavedPluginsStatus.data.some(
            (d) => d.plugin_id === target_plugin_id
        );
        let new_value = [];
        if (is_exists) {
            new_value = currentSavedPluginsStatus.data.map((d) => {
                if (d.plugin_id === target_plugin_id) {
                    d.is_enabled = !d.is_enabled;
                    (d.is_enabled)
                        ? showNotification_Success(t("plugin_notifications.is_enabled"))
                        : showNotification_Success(t("plugin_notifications.is_disabled"));
                }
                return d;
            });
        } else {
            new_value.push(...currentSavedPluginsStatus.data);
            new_value.push({
                plugin_id: target_plugin_id,
                is_enabled: true,
            });
            showNotification_Success(t("plugin_notifications.is_enabled"))
        }

        // 「currentPluginsData.data」でis_downloadedがtrueのものだけ残す
        new_value = new_value.filter((item) =>
            currentPluginsData.data.some(
                (plugin) => plugin.plugin_id === item.plugin_id && plugin.is_downloaded
            )
        );

        setSavedPluginsStatus(new_value);
    };


    // Init時の処理 非対応のものを無効化する際に、savedDPluginsStatusから不要なものを削除する処理が邪魔になるので該当コードを削除したバージョン。Init以外で使用する時にはリファクタが必要になる。
    const setTargetSavedPluginsStatus_Init = (target_plugin_id, is_enabled) => {
        const is_exists = currentSavedPluginsStatus.data.some(
            (d) => d.plugin_id === target_plugin_id
        );
        let new_value = [];
        if (is_exists) {
            new_value = currentSavedPluginsStatus.data.map((d) => {
                if (d.plugin_id === target_plugin_id) {
                    d.is_enabled = is_enabled;
                }
                return d;
            });
        } else {
            new_value.push(...currentSavedPluginsStatus.data);
            new_value.push({
                plugin_id: target_plugin_id,
                is_enabled: is_enabled,
            });
        }

        setSavedPluginsStatus(new_value);
    };


    const setSavedPluginsStatus = (plugins_status) => {
        pendingSavedPluginsStatus();
        asyncStdoutToPython("/set/data/plugins_status", plugins_status);
    };

    // init時、currentPluginsDataからのデータではデータ更新が間に合わないので、currentSavedPluginsStatusから直接取得
    const isAnyPluginEnabled_Init = () => {
        return currentSavedPluginsStatus.data.some(plugin => plugin.is_enabled);
    };

    const isAnyPluginEnabled = () => {
        return currentPluginsData.data.some(plugin => plugin.is_enabled);
    };

    const enabledPluginsList = () => {
        return  currentPluginsData.data.filter(plugin => plugin.is_enabled);
    }

    const updateTargetPluginData = (target_plugin_id, attribute, value) => {
        updatePluginsData(prev => {
            prev.data.forEach(plugin => {
                if (plugin.plugin_id === target_plugin_id) {
                    plugin[attribute] = value;
                }
            });
            return prev.data;
        });
    }



    return {
        asyncFetchPluginsInfo,

        isAnyPluginEnabled_Init,
        isAnyPluginEnabled,
        enabledPluginsList,

        asyncLoadAllPlugins,
        downloadAndExtractPlugin,

        currentSavedPluginsStatus,
        updateSavedPluginsStatus,

        currentPluginsData,
        updatePluginsData,

        updateTargetPluginData,

        currentFetchedPluginsInfo,
        updateFetchedPluginsInfo,

        currentLoadedPlugins,
        updateLoadedPlugins,

        toggleSavedPluginsStatus,
        setTargetSavedPluginsStatus_Init,
        setSavedPluginsStatus,

        handlePendingPlugin,
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
    if (!await exists(plugin_css_path, { baseDir: BaseDirectory.Resource, recursive: true })) return;
    try {
        // プラグインフォルダのルートにある main.css を読み込む
        const css_content = await readTextFile(plugin_css_path, { baseDir: BaseDirectory.Resource });

        // style タグを作成して head に挿入する
        const style_tag = document.createElement("style");
        style_tag.id = `plugin-css-${plugin_css_path.replace(/[^a-zA-Z0-9_-]/g, "")}`;
        style_tag.textContent = css_content;
        document.head.appendChild(style_tag);
    } catch (error) {
        console.error("Failed to load plugin CSS from", plugin_css_path, error);
    }
};

export { loadPluginCSS };
