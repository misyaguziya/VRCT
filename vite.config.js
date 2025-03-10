import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import svgr from "vite-plugin-svgr";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig(async () => ({
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
            "react": path.resolve(__dirname, "node_modules/react"),
            "react-dom": path.resolve(__dirname, "node_modules/react-dom"),



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
        },
    },

    css: {
        preprocessorOptions: {
            scss: {
                api: "modern-compiler"
            }
        }
    }

}));
