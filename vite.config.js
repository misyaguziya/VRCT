import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import svgr from "vite-plugin-svgr";
import yaml from "@rollup/plugin-yaml";
import path from "path";

const host = process.env.TAURI_DEV_HOST;

// https://vitejs.dev/config/
export default defineConfig(() => {
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
                // 3. keep backend files and large local datasets/environments out of the watcher.
                // Vite does not use .gitignore for watch exclusions.
                ignored: [
                    "**/src-tauri/**",
                    "**/tmp/**",
                    "**/.venv/**",
                    "**/.venv_cuda/**",
                ],
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
                "@useStdoutToPython": path.resolve(__dirname, "src-ui/logics/common/useStdoutToPython.js"),

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
