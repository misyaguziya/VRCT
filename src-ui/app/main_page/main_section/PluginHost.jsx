import React from "react";
import { usePlugins } from "@logics_configs";

export const PluginHost = () => {
    const { currentPluginsData } = usePlugins();

    return (
        <div>
            {currentPluginsData.data
                .filter((plugin) => plugin.is_enabled && plugin.location === "main_section")
                .map((plugin, index) => {
                    const PluginComponent = plugin.component;
                    return PluginComponent ? <PluginComponent key={index} /> : null;
                })}
        </div>
    );
};