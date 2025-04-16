import { useEffect } from "react";
import { usePlugins } from "@logics_configs";

export const FetchLatestPluginsDataController = ({ pluginsControllerHasRunRef }) => {
    const {
        asyncFetchPluginsInfo,
    } = usePlugins();

    const asyncInitFetchPluginsInfo = async () => {
        try {
            await asyncFetchPluginsInfo();
        } catch (error) {
            console.error(error);
        }
    };

    useEffect(() => {
        if (!pluginsControllerHasRunRef.current.is_init_fetched_plugins_info) {
            asyncInitFetchPluginsInfo();
            pluginsControllerHasRunRef.current.is_init_fetched_plugins_info = true;
        }
    }, []);

    return null;
};