import React, { useEffect } from "react";
import { usePlugins } from "@logics_configs";
import clsx from "clsx";

if (typeof window !== "undefined") {
    window.React = React;
    window.clsx = clsx;
}

export const LoadPluginsController = () => {

    const {
        asyncLoadAllPlugins,
        currentIsInitializedLoadPlugin,
        updateIsInitializedLoadPlugin,
    } = usePlugins();

    const asyncInitLoadPlugins = async () => {
        try {
            await asyncLoadAllPlugins();
        } catch (error) {
            console.error(error);
        }
    };

    useEffect(() => {

        if (!currentIsInitializedLoadPlugin.data) {
            asyncInitLoadPlugins().then(() => {
                updateIsInitializedLoadPlugin(true);
            });
        }
    }, []);

    return null;
};