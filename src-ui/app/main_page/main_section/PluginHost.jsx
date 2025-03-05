// PluginHost.jsx
import React from "react";
import { useStore_LoadedPluginsList } from "@store";

// export const PluginHost = ({ location }) => {
export const PluginHost = () => {
    const { currentLoadedPluginsList } = useStore_LoadedPluginsList();
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