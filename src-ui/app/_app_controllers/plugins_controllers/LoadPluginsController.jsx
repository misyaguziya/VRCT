import { useEffect } from "react";
import { usePlugins } from "@logics_configs";
import { store } from "@store";

export const LoadPluginsController = () => {
    const {
        asyncLoadAllPlugins,
    } = usePlugins();

    const asyncInitLoadPlugins = async () => {
        try {
            await asyncLoadAllPlugins();
        } catch (error) {
            console.error(error);
        }
    };

    useEffect(() => {
        if (!store.is_initialized_load_plugin) {
            asyncInitLoadPlugins();
            store.is_initialized_load_plugin = true;
        }
    }, []);

    return null;
};