import React from "react";

import { MainContainer } from "./main_container/MainContainer";

export const init = (plugin_context) => {
    const { useHook: useStore_CountPluginState } = plugin_context.createAtomWithHook({ count: 6 }, "CountPluginState");

    const EntryComponents = () => {

        return (
            <MainContainer useStore_CountPluginState={useStore_CountPluginState}/>
        );

    };

    // UI の"main_section"拡張ポイントにコンポーネントを登録
    plugin_context.registerComponent({
        plugin_id: "dev_vrct_plugin_example_1",
        location: "main_section",
        component: EntryComponents,
    });
};