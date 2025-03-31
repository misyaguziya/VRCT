import { initStore, StoreContext } from "@plugin_store";
import { SubtitleSystemContainer } from "./subtitle_system_container/SubtitleSystemContainer";
import { SubtitlesController } from "./subtitle_system_container/_controllers/SubtitlesController.jsx";

export const init = (plugin_context) => {
    initStore(plugin_context.createAtomWithHook);
    const { logics } = plugin_context;

    const EntryComponents = () => {
        return (
            <StoreContext.Provider value={logics}>
                <SubtitlesController />

                <SubtitleSystemContainer />
            </StoreContext.Provider>
        );
    };

    plugin_context.registerComponent(EntryComponents);
};

export default init;