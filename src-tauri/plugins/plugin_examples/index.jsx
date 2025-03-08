import React from "react";
import { initStore } from "./store/store";
import { MainContainer } from "./main_container/MainContainer";

export const init = (plugin_context) => {
    initStore(plugin_context.createAtomWithHook);

    const EntryComponents = () => {
        return <MainContainer />;
    };

    plugin_context.registerComponent({
        plugin_id: "plugin_example_1_my_plugin",
        location: "main_section",
        component: EntryComponents,
    });
};

export default init;