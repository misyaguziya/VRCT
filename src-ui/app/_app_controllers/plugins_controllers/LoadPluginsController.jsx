import { useEffect } from "react";
import { usePlugins } from "@logics_configs";

export const LoadPluginsController = ({ pluginsControllerHasRunRef }) => {
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
        if (!pluginsControllerHasRunRef.current.is_initialized_load_plugin) {
            asyncInitLoadPlugins();
            pluginsControllerHasRunRef.current.is_initialized_load_plugin = true;
        }
    }, []);

    return null;
};