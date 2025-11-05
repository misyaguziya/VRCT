import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import svgr from "vite-plugin-svgr";
import yaml from "@rollup/plugin-yaml";
import path from "path";
import { globSync } from "node:fs";
import { pathToFileURL } from "url";

import { dev_plugins } from "./src-ui/plugins/plugins_index.js";

const host = process.env.TAURI_DEV_HOST;

// https://vitejs.dev/config/
export default defineConfig(async () => {
    const plugin_aliases = await getPluginAliases();

    return {
        plugins: [
            yaml({ include: ["**/*.yml", "**/*.yaml"] }),
            react(),
            svgr(),
        ],

        // Vite options tailored for Tauri development and only applied in `tauri dev` or `tauri build`
        //
        // 1. prevent vite from obscuring rust errors
        clearScreen: false,
        // 2. tauri expects a fixed port, fail if that port is not available
        server: {
            port: 1420,
            strictPort: true,
            host: host || false,
            hmr: host
                ? {
                    protocol: "ws",
                    host,
                    port: 1421,
                }
                : undefined,
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
            sourcemap: true,
        },

        resolve: {
            alias: {
                "@root": path.resolve(__dirname),

                "@useI18n": path.resolve(__dirname, "locales/useI18n.js"),

                "@useReceiveRoutes": path.resolve(__dirname, "src-ui/logics/useReceiveRoutes.js"),
                "@useStdoutToPython": path.resolve(__dirname, "src-ui/logics/useStdoutToPython.js"),

                "@ui_configs": path.resolve(__dirname, "src-ui/logics/ui_configs.js"),
                "@scss_mixins": path.resolve(__dirname, "src-ui/views/common_css/mixins.scss"),
                "@store": path.resolve(__dirname, "src-ui/logics/store.js"),
                "@images": path.resolve(__dirname, "src-ui/views/assets"),
                "@utils": path.resolve(__dirname, "src-ui/logics/utils.js"),
                "@logics": path.resolve(__dirname, "src-ui/logics"),
                "@logics_common": path.resolve(__dirname, "src-ui/logics/common"),
                "@logics_main": path.resolve(__dirname, "src-ui/logics/main"),
                "@logics_configs": path.resolve(__dirname, "src-ui/logics/configs"),

                "@setting_box": path.resolve(__dirname, "src-ui/views/app/config_page/setting_section/setting_box/index.js"),
                "@common_components": path.resolve(__dirname, "src-ui/views/common_components/index.js"),

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




const getPluginAliases = async () => {
    const aliases = {};
    const raw_config_files = globSync("src-ui/plugins/*/plugin_configs.js"); // [Note] globSync is an experimental feature Node.js. If any error happened, use node.js v22.15.0 that I confirmed it works.
    const config_files = raw_config_files.map(p => p.split(path.sep).join("/"));

    for (const plugin of dev_plugins) {
        const entry_path = plugin.entry_path;
        const relative_config_path = `src-ui/plugins/${entry_path}/plugin_configs.js`;

        if (!config_files.includes(relative_config_path)) {
            continue;
        }

        try {
            const full_path = path.resolve(__dirname, relative_config_path);
            const file_url = pathToFileURL(full_path).href;
            const plugin_config = await import(file_url);

            if (plugin_config.configs?.alias) {
                for (const [alias_key, alias_relative_path] of Object.entries(plugin_config.configs.alias)) {
                    aliases[alias_key] = path.resolve(
                        __dirname,
                        "src-ui/plugins",
                        entry_path,
                        alias_relative_path
                    );
                }
            }
        } catch (error) {
            console.error(
                `Error loading alias config for plugin ${plugin.plugin_id}:`,
                error
            );
        }
    }

    return aliases;
};