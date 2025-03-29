import { initStore, StoreContext } from "./store/store.js";
import { SubtitleSystemContainer } from "./subtitle_system_container/SubtitleSystemContainer";
import { SubtitlesController } from "./subtitle_system_container/_controllers/SubtitlesController.jsx";

export const init = (plugin_context) => {
    initStore(plugin_context.createAtomWithHook);
    const { logic_configs } = plugin_context;

    loadPluginCSS("./main.css");

    const EntryComponents = () => {
        return (
            <StoreContext.Provider value={logic_configs}>
                <SubtitlesController />

                <SubtitleSystemContainer />
            </StoreContext.Provider>
        );
    };

    plugin_context.registerComponent(EntryComponents);
};

export default init;


// CSS を動的に読み込む関数
const loadPluginCSS = (cssUrl) => {
    if (typeof document === "undefined") return;
    // すでに読み込まれているかチェック
    if (document.getElementById("plugin-main-css")) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = cssUrl;
    link.id = "plugin-main-css";
    document.head.appendChild(link);
};