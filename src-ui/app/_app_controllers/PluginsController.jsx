import { usePlugins } from "@logics_configs";


import React, { useEffect } from "react";
if (typeof window !== "undefined") {
    window.React = React;
}

export const PluginsController = () => {
    const { loadAllPlugins } = usePlugins();
    useEffect(() => {
        loadAllPlugins();
    }, []);

    return null;
};