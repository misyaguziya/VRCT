import React from "react";
import { usePlugins } from "@logics_configs";

export const PluginHost = () => {
    const { currentLoadedPluginsList } = usePlugins();
    console.log(currentLoadedPluginsList.data);

    return (
        <div>
            {currentLoadedPluginsList.data
                .filter((plugin) => plugin.location === "main_section")
                .map((plugin, index) => {
                    const PluginComponent = plugin.component;
                    return PluginComponent ? <PluginComponent key={index} /> : null;
                })}
        </div>
    );
};