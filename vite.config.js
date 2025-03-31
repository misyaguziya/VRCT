import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import svgr from "vite-plugin-svgr";
import path from "path";

import { dev_plugins } from "./src-ui/plugins/plugins_index.js";


// https://vitejs.dev/config/
export default defineConfig(async () => {
    const plugin_aliases = await getPluginAliases();

    return {
        plugins: [react(), svgr()],
        assetsInclude: ["**/*.yml"],

        // Vite options tailored for Tauri development and only applied in `tauri dev` or `tauri build`
        //
        // 1. prevent vite from obscuring rust errors
        clearScreen: false,
        // 2. tauri expects a fixed port, fail if that port is not available
        server: {
            port: 1420,
            strictPort: true,
            watch: {
                // 3. tell vite to ignore watching `src-tauri`
                ignored: ["**/src-tauri/**"],
            },
        },

        build: {
            outDir: path.resolve(__dirname, "dist"),
            rollupOptions: {
                input: {
                    main: path.resolve(__dirname, "index.html"),
                },
            },
        },

        resolve: {
            alias: {
                "@root": path.resolve(__dirname),
                "@test_data": path.resolve(__dirname, "./test_data.js"),

                "@ui_configs": path.resolve(__dirname, "src-ui/ui_configs.js"),
                "@scss_mixins": path.resolve(__dirname, "src-ui/common_css/mixins.scss"),
                "@store": path.resolve(__dirname, "src-ui/store.js"),
                "@images": path.resolve(__dirname, "src-ui/assets"),
                "@utils": path.resolve(__dirname, "src-ui/utils.js"),
                "@logics": path.resolve(__dirname, "src-ui/logics"),
                "@logics_common": path.resolve(__dirname, "src-ui/logics/common"),
                "@logics_main": path.resolve(__dirname, "src-ui/logics/main"),
                "@logics_configs": path.resolve(__dirname, "src-ui/logics/configs"),

                "@setting_box": path.resolve(__dirname, "src-ui/app/config_page/setting_section/setting_box/index.js"),
                "@common_components": path.resolve(__dirname, "src-ui/common_components/index.js"),

                // Plugins
                "@plugins_path": path.resolve(__dirname, "src-ui/plugins"),
                "@plugins_index": path.resolve(__dirname, "src-ui/plugins/plugins_index.js"),
                ...plugin_aliases,
            },
        },

        css: {
            preprocessorOptions: {
                scss: {
                    api: "modern-compiler"
                }
            }
        }
    };
});



// 各プラグインのエイリアスを動的に読み込む関数
const getPluginAliases = async () => {
    const aliases = {};
    // dev_plugins 配列の各プラグインについて処理する
    for (const plugin of dev_plugins) {
        const entry_path = plugin.entry_path; // 例: "dev_plugin_subtitles"
        try {
            // エイリアス設定ファイルは各プラグインフォルダ内の "configs.js" に記述されている前提
            const pluginConfig = await import(`./src-ui/plugins/${entry_path}/plugin_configs.js`);
            if (pluginConfig.configs && pluginConfig.configs.alias) {
                for (const [alias_key, alias_relative_path] of Object.entries(pluginConfig.configs.alias)) {

                    // ホスト側の絶対パスに変換
                    aliases[alias_key] = path.resolve(__dirname, "src-ui/plugins", entry_path, alias_relative_path);
                }
            }
        } catch (error) {
            console.error(`Error loading alias config for plugin ${plugin.plugin_info.plugin_id}:`, error);
        }
    }
    return aliases;
};