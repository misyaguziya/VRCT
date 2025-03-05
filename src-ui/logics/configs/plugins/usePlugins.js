    import { invoke } from '@tauri-apps/api/tauri';
    import { createAtomWithHook, useStore_LoadedPluginsList } from "@store";
    import { transform } from "@babel/standalone";
    import { writeFile, createDir, exists, readDir, BaseDirectory, readTextFile } from "@tauri-apps/api/fs";
    const dev_plugin_mapping = import.meta.glob("/src-tauri/plugins/**/index.jsx", { eager: true });
    import JSZip from "jszip";
    import { fetch as tauriFetch, ResponseType } from "@tauri-apps/api/http";

    export const usePlugins = () => {
    const { updateLoadedPluginsList } = useStore_LoadedPluginsList();

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
        console.log("plugin_relative_path",plugin_relative_path);

        try {
            const plugin_code = await readTextFile(plugin_relative_path, { dir: BaseDirectory.Resource, recursive: true });
            const cleanedCode = removeImportStatements(plugin_code);
            const transpiled_code = transform(cleanedCode, {
                presets: [
                    ["env", { modules: false }],
                    "react"
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
            // ホットリロード対応 src-tauri以下にあるpluginsディレクトリから直接読み込み（開発用）
            Object.entries(dev_plugin_mapping).forEach(([key, plugin_module]) => {
                console.log(plugin_module);
                if (plugin_module && plugin_module.init) {
                    plugin_module.init(plugin_context);
                }
            });
        } else {
            try {
                const plugin_files = await readDir("plugins", { dir: BaseDirectory.Resource, recursive: true });
                for (const target_dir of plugin_files) {
                    console.log(target_dir);

                    const target_path = target_dir.name + "\\index.jsx";
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
            console.log("Latest plugin zip URL:", plugin_zip_url);

            // Rust コマンド経由で zip をダウンロード
            const base64Zip = await invoke("download_zip_asset", { url: plugin_zip_url });
            // base64Zip は文字列なので、デコードして Uint8Array に変換
            const binaryString = atob(base64Zip);
            const len = binaryString.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }

            // JSZip で zip を解凍
            const zip = await JSZip.loadAsync(bytes);

            // const plugin_dir_exists = await exists("plugins", { dir: BaseDirectory.Resource, recursive: true });
            await createDir("plugins/" + plugin.asset_name.replace(".zip", ""), { dir: BaseDirectory.Resource, recursive: true });
            // if (!plugin_dir_exists) {
            // }
            const target_plugin_path = "plugins/" + plugin.asset_name.replace(".zip", "");


            const filePromises = [];
            zip.forEach((relativePath, zipEntry) => {
                // .git 以下のファイルはスキップ
                if (relativePath.startsWith(".git") || relativePath.includes("/.git/")) {
                    // console.log("Skipping .git file: " + relativePath);
                    return;
                }


                const filePath = target_plugin_path + "/" + relativePath;

                if (zipEntry.dir) {
                    // フォルダの場合、ディレクトリを作成
                    filePromises.push(
                        createDir(filePath, { dir: BaseDirectory.Resource, recursive: true }).catch((err) => {
                            console.log(err);

                            if (!err.message?.includes("already exists")) {
                                console.error("Failed to create directory:", filePath, err);
                            }
                        })
                    );
                } else {
                    // ファイルの場合、ディレクトリを作成してから書き込む
                    const dirPath = filePath.substring(0, filePath.lastIndexOf("/")); // 親ディレクトリのパス

                    const promise = createDir(dirPath, { dir: BaseDirectory.Resource, recursive: true })
                        .catch((err) => {
                            if (!err.message?.includes("already exists")) {
                                console.error("Failed to create parent directory:", dirPath, err);
                            }
                        })
                        .then(() => zipEntry.async("text"))
                        .then(async (fileData) => {
                            await writeFile(filePath, fileData, { dir: BaseDirectory.Resource, recursive: true });
                        });

                    filePromises.push(promise);
                }
            });

            await Promise.all(filePromises);
            console.log("Plugin downloaded successfully.");

            const index_file_relative_path = plugin.asset_name.replace(".zip", "") + "/" + "index.jsx"
            console.log("index_file_relative_path", index_file_relative_path);

            await asyncLoadPlugin(index_file_relative_path);

            console.log("Plugin loaded successfully.");
        } catch (error) {
            console.error("Error downloading and extracting plugin:", error);
        }
    };

    // JSON内のURLから GitHub API を使って最新リリース情報を取得し、
    // assets 配列から plugin.asset_name に一致するアセットの browser_download_url を返す
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
