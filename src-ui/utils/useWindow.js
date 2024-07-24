import { WebviewWindow } from "@tauri-apps/api/window";
import { store, useIsOpenedConfigWindow } from "@store";
import { getCurrent } from "@tauri-apps/api/window";

export const useWindow = () => {
    const { updateIsOpenedConfigWindow } = useIsOpenedConfigWindow();

    const createConfigWindow = async () => {
        const main_window = getCurrent();
        if (store.config_window === null) {
            const config_window = new WebviewWindow("vrct_config_window",{
                url: "./src-ui/windows/config_window/index.html",
                center: true,
                width: 1080,
                height: 700,
            });

            config_window.once("tauri://created", function () {
                store.config_window = config_window;
                updateIsOpenedConfigWindow(true);
            });
            config_window.once("tauri://error", function (e) {
                console.log(e);
            });

            const unlisten_d = config_window.once("tauri://destroyed", (event) => {
                store.config_window = null;
                updateIsOpenedConfigWindow(false);
                unlisten_d();
            });

            main_window.onCloseRequested((event) => {
                config_window.close();
            });
        }
    };

    const closeConfigWindow = () => {
        store.config_window.close();
    };

    return { createConfigWindow, closeConfigWindow };
};