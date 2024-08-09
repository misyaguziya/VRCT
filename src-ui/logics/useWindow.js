import { WebviewWindow } from "@tauri-apps/api/window";
import { store, useIsOpenedConfigPage } from "@store";
import { getCurrent } from "@tauri-apps/api/window";

export const useWindow = () => {
    const { updateIsOpenedConfigPage } = useIsOpenedConfigPage();

    const createConfigPage = async () => {
        const main_page = getCurrent();
        if (store.config_page === null) {
            const config_page = new WebviewWindow("vrct_config_page",{
                url: "./src-ui/windows/config_page/index.html",
                center: true,
                width: 1080,
                height: 700,
                title: "Settings"
            });

            config_page.once("tauri://created", function () {
                store.config_page = config_page;
                updateIsOpenedConfigPage(true);
            });
            config_page.once("tauri://error", function (e) {
                console.log(e);
            });

            const unlisten_d = config_page.once("tauri://destroyed", (event) => {
                store.config_page = null;
                updateIsOpenedConfigPage(false);
                unlisten_d();
            });

            main_page.onCloseRequested((event) => {
                config_page.close();
            });
        }
    };

    const closeConfigPage = () => {
        store.config_page.close();
    };

    return { createConfigPage, closeConfigPage };
};