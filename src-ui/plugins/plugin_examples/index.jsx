import { initStore } from "./store/store";
import { MainContainer } from "./main_container/MainContainer";

export const init = (plugin_context) => {
    initStore(plugin_context.createAtomWithHook);

    const EntryComponents = () => {
        return <MainContainer />;
    };

    plugin_context.registerComponent(EntryComponents);
};

export default init;