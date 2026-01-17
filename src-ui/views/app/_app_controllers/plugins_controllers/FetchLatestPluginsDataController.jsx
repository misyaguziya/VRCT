import { useEffect } from "react";
import { usePlugins } from "@logics_configs";

export const FetchLatestPluginsDataController = () => {
    const {
        asyncFetchPluginsInfo,
        isAnyPluginEnabled_Init,
    } = usePlugins();

    useEffect(() => {
        if (isAnyPluginEnabled_Init()) {
            asyncFetchPluginsInfo();
        }
    }, []);

    return null;
};