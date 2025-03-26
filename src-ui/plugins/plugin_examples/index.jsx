import { initStore, StoreContext } from "./store/store.js";
import { SubtitleSystemContainer } from "./subtitle_system_container/SubtitleSystemContainer";
import { SubtitlesController } from "./subtitle_system_container/_controllers/subtitlesController.jsx";

export const init = (plugin_context) => {
    initStore(plugin_context.createAtomWithHook);
    const { logic_configs } = plugin_context;

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