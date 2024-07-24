import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import svgr from "vite-plugin-svgr";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig(async () => ({
    plugins: [react(), svgr()],

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
                second: path.resolve(__dirname, "./src-ui/windows/config_window/index.html"),
            },
        },
    },

    resolve: {
        alias: {
            "@data": path.resolve(__dirname, "./data.js"),

            "@scss_mixins": path.resolve(__dirname, "src-ui/utils/mixins.scss"),
            "@store": path.resolve(__dirname, "src-ui/store.js"),
            "@logic": path.resolve(__dirname, "src-ui/logic.js"),
            "@images": path.resolve(__dirname, "src-ui/assets"),
            "@utils": path.resolve(__dirname, "src-ui/utils"),
            "@logics": path.resolve(__dirname, "src-ui/utils/logics"),
        },
    },


}));
