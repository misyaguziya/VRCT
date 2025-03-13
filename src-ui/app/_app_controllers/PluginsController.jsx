import React, { useEffect, useRef } from "react";
import { usePlugins } from "@logics_configs";

if (typeof window !== "undefined") {
    window.React = React;
}

export const PluginsController = () => {
    const hasRunRef = useRef(false);
    const {
        loadAllPlugins,
        asyncUpdatePluginInfoList,
    } = usePlugins();

    useEffect(() => {
        if (!hasRunRef.current) {
            asyncUpdatePluginInfoList().then(() => {
                loadAllPlugins();
            });
        }
        return () => hasRunRef.current = true;
    }, []);

    return null;
};