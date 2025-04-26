import { initStore, StoreContext } from "@plugin_store";
import { initI18n } from "@initI18n";
import { SubtitleSystemContainer } from "./subtitle_system_container/SubtitleSystemContainer";
import { SubtitlesController } from "./subtitle_system_container/_controllers/SubtitlesController.jsx";

export const init = (plugin_context) => {
    const { createAtomWithHook, i18n, logics } = plugin_context;

    initStore(createAtomWithHook);
    initI18n(i18n);

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