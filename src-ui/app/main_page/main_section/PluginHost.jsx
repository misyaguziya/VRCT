import React from "react";

export const PluginHost = ({render_components}) => {

    return (
        <>
            {render_components
                .map((plugin, index) => {
                    const PluginComponent = plugin.component;
                    return PluginComponent ? <PluginComponent key={index} /> : null;
                })}
        </>
    );
};