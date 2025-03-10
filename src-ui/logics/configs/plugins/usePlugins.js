import { invoke } from '@tauri-apps/api/tauri';
import { createAtomWithHook, useStore_LoadedPluginsList } from "@store";
import { useSoftwareVersion } from "@logics_configs";
import { transform } from "@babel/standalone";
import { writeFile, createDir, exists, removeDir, readDir, BaseDirectory, readTextFile } from "@tauri-apps/api/fs";
const dev_plugin_mapping = import.meta.glob("/src-tauri/plugins/**/index.jsx", { eager: true });
import JSZip from "jszip";
import { fetch as tauriFetch, ResponseType } from "@tauri-apps/api/http";

export const usePlugins = () => {
    const { updateLoadedPluginsList } = useStore_LoadedPluginsList();
    const { currentSoftwareVersion } = useSoftwareVersion();

    const plugin_context = {
        registerComponent: ({ plugin_id, location, component }) => {
            if (!plugin_id || !location || !component) {
                return console.error("An invalid plugin was detected.", plugin_id, location, component);
            }
            updateLoadedPluginsList((prev) => {
                const filtered = prev.data.filter(item => item.plugin_id !== plugin_id);
                return [...filtered, { plugin_id, location, component }];
            });
        },
        createAtomWithHook: (...args) => createAtomWithHook(...args)
    };

    const asyncLoadPlugin = async (plugin_relative_path) => {
        plugin_relative_path = "plugins/" + plugin_relative_path;
        try {
            const plugin_code = await readTextFile(plugin_relative_path, { dir: BaseDirectory.Resource, recursive: true });
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
                plugin_module.init(plugin_context);
            }
        } catch (error) {
            console.error("Failed to load plugin from", plugin_relative_path, error);
        }
    };

    const loadAllPlugins = async () => {
        if (import.meta.env.DEV) {
            // 開発時: ホットリロード対応、src-tauri以下のpluginsから直接読み込み
            Object.entries(dev_plugin_mapping).forEach(([key, plugin_module]) => {
                if (plugin_module && plugin_module.init) {
                    plugin_module.init(plugin_context);
                }
            });
        } else {
            try {
                const plugin_files = await readDir("plugins", { dir: BaseDirectory.Resource, recursive: true });
                for (const target_dir of plugin_files) {
                    const target_path = target_dir.name + "/index.esm.js";
                    await asyncLoadPlugin(target_path, plugin_context);
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
            const target_plugin_path = "plugins/" + plugin.asset_name.replace(".zip", "");
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

            const index_file_relative_path = plugin.asset_name.replace(".zip", "") + "/index.esm.js";
            await asyncLoadPlugin(index_file_relative_path, plugin_context);

            console.log("Plugin loaded successfully.");
        } catch (error) {
            console.error("Error downloading and extracting plugin:", error);
        }
    };

    // GitHub API を使用して、最新リリース情報から asset_name に一致するアセットのブラウザダウンロード URL を返す
    const fetchLatestPluginZipUrl = async (plugin) => {
        const api_url = plugin.url;
        const response = await tauriFetch(api_url, {
            method: "GET",
            responseType: ResponseType.Json,
            headers: {
                "Accept": "application/vnd.github+json",
                "User-Agent": "VRCTPluginApp"
            }
        });
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

    return {
        loadAllPlugins,
        downloadAndExtractPlugin,
    };
};

const removeImportStatements = (code) => {
    return code
        .split("\n")
        .filter(line => !line.match(/^import\s+.*['"]react['"]/))
        .join("\n");
};
